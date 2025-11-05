from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from .state import AgentState
from .streaming import get_stream_manager
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
        return "Tu es un assistant conversationnel proactif et engageant."

CONVERSATION_PROMPT_TEMPLATE = load_prompt("conversation.yaml")


class ConversationAgent:
    """Agent conversationnel pour guider l'utilisateur de manière proactive."""
    
    def __init__(self, state: AgentState):
        self.state = state
        self.project_id = state.get("project_id")
        self.tool_results = state.get("tool_results", {})
        self.current_agent = state.get("current_agent")
        self.error = state.get("error")
        
    async def suggest_next_steps(self) -> dict:
        """Suggérer les prochaines actions basées sur le contexte actuel.
        
        Returns:
            Dict avec:
            - suggestions: list[str] - Liste de suggestions d'actions
            - context: str - Contexte expliquant pourquoi ces suggestions
            - priority: str - high/medium/low
        """
        logger.info(f"ConversationAgent suggesting next steps based on context: {self.current_agent}")
        
        suggestions = []
        context = ""
        priority = "medium"
        
        # Cas 1: Après analyse de document
        if self.current_agent == "document":
            doc_results = self._extract_document_results()
            
            # Prioriser les features créées sur les documents analysés
            if doc_results.get("features_created"):
                feature_ids = doc_results.get("features_created", [])
                suggestions = [
                    f"📝 Générer les User Stories pour ces {len(feature_ids)} features",
                    "🎯 Ajouter des critères d'acceptation détaillés",
                    "🏗️ Organiser sous des Epics thématiques"
                ]
                context = f"{len(feature_ids)} features créées avec succès !"
                priority = "high"
            
            elif doc_results.get("documents_analyzed"):
                analyzed_count = len(doc_results.get("documents_analyzed", []))
                suggestions = [
                    "🚀 Extraire automatiquement les features de ces documents",
                    "🔍 Rechercher des exigences spécifiques",
                    "📊 Générer un résumé structuré"
                ]
                context = f"{analyzed_count} document{'s' if analyzed_count > 1 else ''} analysé{'s' if analyzed_count > 1 else ''} - prêt pour l'extraction"
                priority = "high"
            
            else:
                suggestions = [
                    "📤 Uploader un document (CDC, spécifications)",
                    "🔎 Analyser les documents du projet",
                    "📄 Consulter les documents disponibles"
                ]
                context = "Aucun document analysé pour le moment"
                priority = "medium"
        
        # Cas 2: Après création de features
        elif self.current_agent == "backlog":
            backlog_results = self._extract_backlog_results()
            
            if backlog_results.get("features_created"):
                feature_count = len(backlog_results.get("features_created", []))
                suggestions = [
                    f"✍️ Générer les User Stories pour ces {feature_count} features",
                    "🎨 Ajouter des critères d'acceptation",
                    "📊 Consulter le backlog complet"
                ]
                context = f"{feature_count} feature{'s' if feature_count > 1 else ''} ajoutée{'s' if feature_count > 1 else ''} au backlog"
                priority = "high"
            
            elif backlog_results.get("user_stories_created"):
                us_count = len(backlog_results.get("user_stories_created", []))
                suggestions = [
                    f"🧪 Générer les Use Cases pour ces {us_count} User Stories",
                    "📊 Estimer les story points",
                    "🚀 Planifier le prochain Sprint"
                ]
                context = f"{us_count} User Stor{'ies' if us_count > 1 else 'y'} prête{'s' if us_count > 1 else ''}"
                priority = "high"
            
            else:
                suggestions = [
                    "🆕 Créer un Epic structurant",
                    "📚 Extraire depuis vos documents",
                    "👀 Explorer le backlog"
                ]
                context = "Backlog vide - structurons votre projet"
                priority = "medium"
        
        # Cas 3: Erreur détectée
        elif self.error:
            suggestions = [
                "🔄 Réessayer l'opération",
                "💬 Obtenir de l'aide",
                "🏠 Retour à l'accueil"
            ]
            context = f"⚠️ Erreur: {self.error[:80]}"
            priority = "high"
        
        # Cas 4: Début de session (pas encore d'agent exécuté)
        else:
            suggestions = [
                "📚 Analyser vos documents",
                "🆕 Créer un Epic ou une Feature",
                "💬 Expliquer votre besoin"
            ]
            context = "Bienvenue ! Comment puis-je vous aider ?"
            priority = "medium"
        
        return {
            "suggestions": suggestions,
            "context": context,
            "priority": priority,
            "emoji": self._get_context_emoji(priority)
        }
    
    def format_response(self, data: dict) -> str:
        """Formater une réponse de manière naturelle et engageante.
        
        Args:
            data: Données brutes à formater
            
        Returns:
            str: Réponse formatée en markdown avec emojis
        """
        logger.info("ConversationAgent formatting response")
        
        # En-tête basé sur le succès
        if data.get("error"):
            header = "❌ **Oups, quelque chose n'a pas fonctionné**\n\n"
        elif data.get("success", True):
            header = "✅ **Opération terminée !**\n\n"
        else:
            header = "ℹ️ **Voici ce que j'ai trouvé**\n\n"
        
        # Corps du message
        body_parts = []
        
        # Features créées
        if data.get("features_created"):
            count = len(data["features_created"])
            body_parts.append(f"🎉 **{count} feature{'s' if count > 1 else ''}** créée{'s' if count > 1 else ''} dans votre backlog")
            
            # Liste les IDs si peu nombreux
            if count <= 5:
                ids = ", ".join([f"#{id}" for id in data["features_created"]])
                body_parts.append(f"_IDs: {ids}_")
        
        # Documents traités
        if data.get("documents_analyzed"):
            docs = data["documents_analyzed"]
            if isinstance(docs, list):
                doc_list = ', '.join([f"**{doc}**" for doc in docs[:3]])
                body_parts.append(f"📄 Documents analysés: {doc_list}")
                if len(docs) > 3:
                    body_parts.append(f"_et {len(docs) - 3} autre{'s' if len(docs) - 3 > 1 else ''}_")
        
        # Résultats de recherche
        if data.get("results"):
            results_count = len(data["results"])
            body_parts.append(f"🔍 **{results_count} résultat{'s' if results_count > 1 else ''}** pertinent{'s' if results_count > 1 else ''}")
        
        # Erreur
        if data.get("error"):
            error_msg = str(data["error"])[:200]
            body_parts.append(f"```\n{error_msg}\n```")
        
        # Message personnalisé
        if data.get("message"):
            body_parts.append(data["message"])
        
        # Assemblage avec espacement amélioré
        if not body_parts:
            body = "Opération terminée avec succès."
        else:
            body = "\n".join(body_parts)
        
        return header + body
    
    async def ask_clarification(self, ambiguity: str) -> str:
        """Poser des questions de clarification quand l'objectif est ambigu.
        
        Args:
            ambiguity: Description de l'ambiguïté détectée
            
        Returns:
            str: Question de clarification formatée
        """
        logger.info(f"ConversationAgent asking clarification for: {ambiguity}")
        
        # Utiliser le LLM pour générer une question contextuelle
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        
        prompt = f"""Tu es un assistant proactif qui aide les utilisateurs à clarifier leurs demandes.

L'utilisateur a dit: "{self.state.get('objective', '')}"

Ambiguïté détectée: {ambiguity}

Génère UNE question de clarification concise et naturelle pour résoudre cette ambiguïté.
La question doit:
- Être courte (max 2 phrases)
- Proposer 2-3 options concrètes si pertinent
- Utiliser un emoji pertinent au début
- Être en français

Exemples:
- "🤔 Je vois plusieurs façons de faire. Voulez-vous créer un nouvel Epic ou ajouter à un existant ?"
- "📋 D'accord ! Pour quelle feature voulez-vous générer les User Stories ?"

Génère uniquement la question, sans préambule."""

        messages = [
            SystemMessage(content=prompt)
        ]
        
        response = await llm.ainvoke(messages)
        question = response.content.strip()
        
        return question
    
    def _extract_document_results(self) -> dict:
        """Extraire les résultats liés aux documents."""
        results = {}
        
        # Chercher dans tool_results
        if "draft_features_from_documents" in self.tool_results:
            result = self.tool_results["draft_features_from_documents"]
            if isinstance(result, dict):
                results["features_created"] = result.get("features_created", [])
                results["documents_analyzed"] = result.get("source_documents", [])
        
        if "list_documents" in self.tool_results:
            result = self.tool_results["list_documents"]
            if isinstance(result, dict):
                results["documents_list"] = result.get("documents", [])
        
        # Chercher dans state.documents_searched
        if self.state.get("documents_searched"):
            results["documents_analyzed"] = self.state["documents_searched"]
        
        return results
    
    def _extract_backlog_results(self) -> dict:
        """Extraire les résultats liés au backlog."""
        results = {}
        
        # Chercher dans tool_results
        if "bulk_create_features" in self.tool_results:
            result = self.tool_results["bulk_create_features"]
            if isinstance(result, dict):
                results["features_created"] = result.get("features_created", [])
        
        if "generate_children_items" in self.tool_results:
            result = self.tool_results["generate_children_items"]
            if isinstance(result, dict):
                items = result.get("items_created", [])
                # Déterminer le type
                if items and isinstance(items[0], dict):
                    item_type = items[0].get("type", "")
                    if item_type == "US":
                        results["user_stories_created"] = [i.get("id") for i in items]
                    elif item_type == "UC":
                        results["use_cases_created"] = [i.get("id") for i in items]
        
        # Chercher dans state.items_created
        if self.state.get("items_created"):
            results["items_created"] = self.state["items_created"]
        
        return results
    
    def _get_context_emoji(self, priority: str) -> str:
        """Retourner un emoji basé sur la priorité."""
        emoji_map = {
            "high": "🔥",
            "medium": "💡",
            "low": "💭"
        }
        return emoji_map.get(priority, "💬")


async def conversation_agent_node(state: AgentState) -> AgentState:
    """Node LangGraph pour l'agent conversationnel."""
    logger.info(f"ConversationAgent processing: {state['objective']}")
    
    # Get streaming manager for this run
    run_id = state.get("run_id", "default")
    stream_manager = get_stream_manager(run_id)
    
    try:
        # Emit agent start event with workflow context if available
        workflow_context = state.get("workflow_context")
        await stream_manager.emit_agent_start(
            "conversation", 
            state["objective"], 
            state["iteration"],
            step_info=workflow_context
        )
        
        # Emit initial narration
        await stream_manager.emit_agent_narration(
            "conversation",
            "Je prépare mes recommandations pour la suite",
            state["iteration"]
        )
        
        # Créer l'agent
        agent = ConversationAgent(state)
        
        # Déterminer l'action à prendre
        objective_lower = state["objective"].lower()
        
        # Action: Suggérer les prochaines étapes
        if any(keyword in objective_lower for keyword in ["suggest", "next", "what now", "maintenant", "ensuite", "quoi faire"]):
            logger.info("ConversationAgent: Suggesting next steps")
            
            suggestions = await agent.suggest_next_steps()
            
            # Emit narration with suggestions
            await stream_manager.emit_agent_narration(
                "conversation",
                "Voici ce que vous pouvez faire maintenant",
                state["iteration"]
            )
            
            # Formater la réponse avec markdown amélioré
            response_text = f"{suggestions['emoji']} **{suggestions['context']}**\n\n"
            response_text += "👉 **Que souhaitez-vous faire ?**\n\n"
            for suggestion in suggestions['suggestions']:
                response_text += f"- {suggestion}\n"
            
            await stream_manager.emit_agent_end(
                "conversation",
                response_text,
                state["iteration"],
                success=True,
                extra_data={"suggestions": suggestions['suggestions']}
            )
            
            return {
                **state,
                "messages": state["messages"],
                "iteration": state["iteration"] + 1,
                "current_agent": "conversation",
                "final_response": response_text,
                "tool_results": {**state["tool_results"], "suggestions": suggestions}
            }
        
        # Action: Demander clarification
        elif any(keyword in objective_lower for keyword in ["clarify", "unclear", "ambigu", "préciser"]):
            logger.info("ConversationAgent: Asking for clarification")
            
            ambiguity = state.get("error", "L'objectif n'est pas clair")
            question = await agent.ask_clarification(ambiguity)
            
            await stream_manager.emit_agent_end(
                "conversation",
                question,
                state["iteration"],
                success=True
            )
            
            return {
                **state,
                "messages": state["messages"],
                "iteration": state["iteration"] + 1,
                "current_agent": "conversation",
                "final_response": question
            }
        
        # Par défaut: Formater la dernière réponse
        else:
            logger.info("ConversationAgent: Formatting response")
            
            # Récupérer les résultats du dernier agent
            last_results = state.get("tool_results", {})
            
            formatted = agent.format_response(last_results)
            
            # Ajouter automatiquement des suggestions
            suggestions = await agent.suggest_next_steps()
            
            # Emit narration with suggestions
            await stream_manager.emit_agent_narration(
                "conversation",
                "Voici ce que vous pouvez faire maintenant",
                state["iteration"]
            )
            
            formatted += f"\n\n{suggestions['emoji']} **Que souhaitez-vous faire maintenant ?**\n\n"
            for suggestion in suggestions['suggestions']:
                formatted += f"- {suggestion}\n"
            
            await stream_manager.emit_agent_end(
                "conversation",
                formatted,
                state["iteration"],
                success=True,
                extra_data={"suggestions": suggestions['suggestions']}
            )
            
            return {
                **state,
                "messages": state["messages"],
                "iteration": state["iteration"] + 1,
                "current_agent": "conversation",
                "final_response": formatted
            }
    
    except Exception as e:
        logger.error(f"ConversationAgent failed: {e}", exc_info=True)
        
        # Emit error
        await stream_manager.emit_agent_end(
            "conversation",
            f"ConversationAgent error: {str(e)}",
            state["iteration"],
            success=False
        )
        
        return {
            **state,
            "iteration": state["iteration"] + 1,
            "current_agent": "conversation",
            "error": f"ConversationAgent error: {str(e)}"
        }
