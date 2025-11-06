from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from .state import AgentState, AgentRunMetadata
from .streaming import get_stream_manager
from .intent_classifier import classify_intents, IntentClassificationResult
import yaml
import os
import logging

logger = logging.getLogger(__name__)

def load_prompt(filename: str) -> str:
    """Load prompt from YAML file."""
    try:
        prompt_path = os.path.join(os.path.dirname(__file__), "prompts", filename)
        with open(prompt_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            return data.get('prompt', '')
    except Exception as e:
        logger.error(f"Failed to load prompt {filename}: {e}")
        return "Tu es un routeur intelligent. Route vers 'backlog'."

ROUTER_PROMPT_TEMPLATE = load_prompt("router_prompt.yaml")


def extract_user_query(state: AgentState) -> str:
    """
    Extrait la requête utilisateur depuis le state.

    Priorité :
    1. Dernier message HumanMessage dans state["messages"]
    2. Fallback sur state["objective"]

    Args:
        state: AgentState courant

    Returns:
        str: Requête utilisateur à classifier
    """
    messages = state.get("messages", [])

    # Chercher le dernier HumanMessage
    for msg in reversed(messages):
        if hasattr(msg, 'type') and msg.type == "human":
            return msg.content
        # Fallback si pas de .type (vérifier content directement)
        if hasattr(msg, 'content') and isinstance(msg.content, str):
            # Simple heuristique : si c'est un HumanMessage il n'a pas de "role" système
            return msg.content

    # Fallback : utiliser objective
    return state.get("objective", "")


def map_intent_to_agent_and_meta(intent_result, state: AgentState) -> tuple[str, dict]:
    """
    Mappe une intention vers un agent et construit le dict meta.

    Args:
        intent_result: IntentResult du classifier
        state: AgentState pour fallbacks

    Returns:
        tuple: (agent_name, meta_dict)
    """
    intent_id = intent_result.id
    agent = intent_result.agent
    args = intent_result.args or {}

    # Mapping explicite pour les 7 intentions V1 prioritaires
    if intent_id == "generate_children":
        meta = {
            "action": "generate_children",
            "target_type": args.get("target_type", "US"),
            "parent_id": args.get("parent_id"),
            "parent_type": args.get("parent_type", "Feature")  # Défaut Feature
        }

    elif intent_id == "extract_features_from_docs":
        meta = {
            "action": "extract_features_from_docs",
            "document_name": args.get("document_name"),
            "scope": args.get("scope", "all_docs")
        }

    elif intent_id == "review_backlog_quality":
        meta = {
            "action": "review_backlog_quality",
            "scope": args.get("scope", "project"),
            "focus": args.get("focus", "all"),
            "item_id": args.get("item_id")  # Optionnel
        }

    elif intent_id == "search_requirements":
        meta = {
            "action": "search_requirements",
            "query_terms": args.get("query_terms"),
            "domain": args.get("domain")
        }

    elif intent_id == "decompose_objective":
        meta = {
            "action": "decompose_objective",
            "objective": args.get("objective", state.get("objective", ""))
        }

    elif intent_id == "estimate_stories":
        meta = {
            "action": "estimate_stories",
            "scope": args.get("scope", "unestimated"),
            "item_ids": args.get("item_ids")
        }

    elif intent_id == "improve_item_description":
        meta = {
            "action": "improve_item_description",
            "item_id": args.get("item_id"),
            "item_type": args.get("item_type"),
            "focus": args.get("focus", "all")
        }

    else:
        # Intentions non-V1 : mapping générique
        # Utilise l'agent suggéré par le classifier + action = intent_id
        meta = {
            "action": intent_id,
            **args  # Inclure tous les args tels quels
        }

    return agent, meta


async def router_node(state: AgentState) -> AgentState:
    """
    Route vers l'agent approprié selon l'intention détectée.

    Intègre le Intent Classifier V1 pour un routing intelligent basé
    sur les intentions utilisateur (18 intentions, 7 V1 prioritaires).

    Fallback sur LLM routing si aucune intention détectée ou erreur.
    """
    print("=== ROUTER_NODE CALLED ===")
    logger.info(f"Router analyzing objective: {state['objective']}")

    # Get streaming manager for this run
    run_id = state.get("run_id", "default")
    print(f"[ROUTER] Run ID: {run_id}")
    stream_manager = get_stream_manager(run_id)

    try:
        # Emit agent start event
        print("[ROUTER] Emitting agent_start event...")
        workflow_context = state.get("workflow_context")
        await stream_manager.emit_agent_start(
            "router",
            state["objective"],
            state["iteration"],
            step_info=workflow_context
        )

        # Emit initial narration
        await stream_manager.emit_agent_narration(
            "router",
            "J'analyse votre demande pour déterminer le workflow optimal",
            state["iteration"]
        )

        # ========================================================================
        # PHASE 1 : INTENT CLASSIFICATION (V1)
        # ========================================================================

        classification_result = None
        use_intent_routing = False

        try:
            # Extraire la query utilisateur
            user_query = extract_user_query(state)

            if user_query:
                logger.info(f"Intent classification: analyzing query '{user_query[:100]}...'")

                # Appel du classifier avec contexte projet optionnel
                classification_result = await classify_intents(
                    query=user_query,
                    language=None,  # Auto-détection
                    project_context_summary=state.get("project_context_summary")
                )

                # Log des résultats
                if classification_result.intents:
                    intent_ids = [i.id for i in classification_result.intents]
                    confidences = [f"{i.confidence:.2f}" for i in classification_result.intents]
                    logger.info(
                        f"Intent classification detected {len(classification_result.intents)} intents: "
                        f"{list(zip(intent_ids, confidences))}"
                    )

                    # Activer le routing par intention
                    use_intent_routing = True
                else:
                    logger.info("Intent classification: no intents detected (empty list)")
            else:
                logger.info("Intent classification skipped: no user query available")

        except Exception as e:
            logger.error(f"Intent classification failed: {e}, falling back to LLM routing")
            classification_result = None
            use_intent_routing = False

        # ========================================================================
        # PHASE 2 : ROUTING DECISION
        # ========================================================================

        next_agent = None
        meta_dict = None

        if use_intent_routing and classification_result and classification_result.intents:
            # INTENT-BASED ROUTING (V1)

            # Sélectionner l'intention principale (confidence max)
            sorted_intents = sorted(
                classification_result.intents,
                key=lambda x: x.confidence,
                reverse=True
            )
            main_intent = sorted_intents[0]

            logger.info(
                f"Intent routing: main intent = {main_intent.id} "
                f"(agent={main_intent.agent}, confidence={main_intent.confidence:.2f})"
            )

            # Mapper intention → agent + meta
            next_agent, meta_dict = map_intent_to_agent_and_meta(main_intent, state)

            # Validation de l'agent
            valid_agents = ["backlog", "document", "planner", "writer", "integration", "conversation"]
            if next_agent not in valid_agents:
                logger.warning(
                    f"Intent routing resulted in invalid agent '{next_agent}', "
                    f"falling back to LLM routing"
                )
                use_intent_routing = False
            else:
                # Narration spécifique pour intent routing
                await stream_manager.emit_agent_narration(
                    "router",
                    f"✨ Intention détectée : {main_intent.id} (confiance: {main_intent.confidence:.0%})",
                    state["iteration"]
                )

        if not use_intent_routing:
            # FALLBACK : LLM-BASED ROUTING (comportement historique)

            logger.info("Using LLM-based routing (fallback)")

            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

            prompt = ROUTER_PROMPT_TEMPLATE.format(
                objective=state["objective"],
                project_id=state["project_id"]
            )

            # Emit thinking event
            await stream_manager.emit_agent_thinking("router", prompt, state["iteration"])

            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content=state["objective"])
            ]

            response = await llm.ainvoke(messages)
            next_agent = response.content.strip().lower()

            # Validation routing
            valid_agents = ["backlog", "document", "planner", "writer", "integration", "conversation"]
            if next_agent not in valid_agents:
                logger.warning(f"Invalid routing decision: {next_agent}, defaulting to 'backlog'")
                next_agent = "backlog"

            # Pas de meta spécifique pour LLM routing
            meta_dict = None

        # ========================================================================
        # PHASE 3 : FINALIZATION
        # ========================================================================

        logger.info(f"Router decision: {next_agent}" + (f" (meta: {meta_dict})" if meta_dict else ""))

        # Emit routing decision narration
        agent_names = {
            "backlog": "BacklogAgent",
            "document": "DocumentAgent",
            "planner": "PlannerAgent",
            "writer": "WriterAgent",
            "integration": "IntegrationAgent",
            "conversation": "ConversationAgent"
        }
        agent_display_name = agent_names.get(next_agent, next_agent.capitalize() + "Agent")

        await stream_manager.emit_agent_narration(
            "router",
            f"→ Routage vers {agent_display_name}",
            state["iteration"]
        )

        # Emit completion event
        await stream_manager.emit_agent_end(
            "router",
            f"Routing to {next_agent} based on " +
            ("intent classification" if use_intent_routing else "LLM analysis"),
            state["iteration"],
            success=True
        )

        # Construire le state de retour
        result_state = {
            **state,
            "next_agent": next_agent,
            "current_agent": "router",
        }

        # Ajouter meta si disponible (intent routing)
        if meta_dict is not None:
            result_state["meta"] = meta_dict

        # Ajouter all_intents pour debugging/V2
        if classification_result:
            result_state["all_intents"] = classification_result.model_dump()

        # Ajouter response message si LLM utilisé
        if not use_intent_routing:
            result_state["messages"] = state["messages"] + [response]

        return result_state

    except Exception as e:
        logger.error(f"Router failed: {e}")

        # Emit error
        await stream_manager.emit_agent_end(
            "router",
            f"Router error: {str(e)}",
            state["iteration"],
            success=False
        )

        # Fallback to backlog agent
        return {
            **state,
            "next_agent": "backlog",
            "current_agent": "router",
            "error": f"Router error: {str(e)}"
        }
