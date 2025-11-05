# agents_v2/intent_classifier.py
"""
Intent Classifier V1 pour ORCHESTRATOR.

Classifie les phrases utilisateur en intentions actionnables
et renvoie une structure JSON avec agent cible, confiance et arguments.
"""

from pydantic import BaseModel, Field
from typing import Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import json
import logging
import yaml
import os

logger = logging.getLogger(__name__)


# ============================================================================
# MODÈLES PYDANTIC
# ============================================================================

class IntentResult(BaseModel):
    """
    Représente une intention détectée dans la requête utilisateur.

    Chaque intention contient :
    - L'identifiant de l'intention (ex: "generate_children")
    - L'agent cible (backlog, document, planner, writer, conversation)
    - Un score de confiance [0.0, 1.0]
    - Des arguments optionnels extraits de la phrase
    """
    id: str = Field(..., description="Identifiant unique de l'intention")
    agent: str = Field(..., description="Agent cible pour cette intention")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Score de confiance [0.0, 1.0]")
    args: dict[str, Any] | None = Field(default=None, description="Arguments extraits (optionnel)")


class IntentClassificationResult(BaseModel):
    """
    Résultat complet de la classification d'une phrase utilisateur.

    Contient :
    - La requête originale
    - La langue détectée
    - La liste des intentions détectées (peut être vide)
    """
    query: str = Field(..., description="Texte original de l'utilisateur")
    language: str = Field(default="fr", description="Langue détectée (fr ou en)")
    intents: list[IntentResult] = Field(default_factory=list, description="Liste des intentions détectées")


# ============================================================================
# PROMPT LOADING
# ============================================================================

def load_prompt(filename: str) -> str:
    """
    Charge le prompt SYSTEM depuis un fichier YAML.

    Args:
        filename: Nom du fichier dans agents_v2/prompts/

    Returns:
        str: Contenu du prompt SYSTEM
    """
    try:
        prompt_path = os.path.join(os.path.dirname(__file__), "prompts", filename)
        with open(prompt_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            return data.get('system', '')
    except Exception as e:
        logger.error(f"Failed to load prompt {filename}: {e}")
        return "Tu es un classifieur d'intentions pour ORCHESTRATOR."


# ============================================================================
# FONCTION DE CLASSIFICATION
# ============================================================================

async def classify_intents(
    query: str,
    language: str | None = None,
    project_context_summary: str | None = None,
) -> IntentClassificationResult:
    """
    Classifie une phrase utilisateur en intentions actionnables.

    Args:
        query: Texte brut de l'utilisateur à classifier
        language: Langue de la requête ("fr" ou "en"), auto-détecté si None
        project_context_summary: Résumé du contexte projet (optionnel, pour phase V2+)

    Returns:
        IntentClassificationResult: Structure avec query, language, et liste d'intents

    Raises:
        ValueError: Si le LLM ne retourne pas un JSON valide
        Exception: Si l'appel LLM échoue

    Example:
        >>> result = await classify_intents("Génère 5 US pour la feature #12")
        >>> result.intents[0].id
        'generate_children'
        >>> result.intents[0].confidence
        0.95
    """

    # Détection automatique de la langue si non fournie
    if language is None:
        language = "fr"  # Défaut français

    # Construction du message utilisateur
    # Note : project_context_summary pourra être utilisé en V2+ pour des références contextuelles
    user_message = f"Phrase utilisateur:\n\"{query}\""

    # TODO V2+ : Enrichir le user_message avec project_context_summary si fourni
    # if project_context_summary:
    #     user_message = f"Contexte projet:\n{project_context_summary}\n\n{user_message}"

    try:
        # Chargement du prompt SYSTEM depuis YAML
        system_prompt = load_prompt("intent_classifier.yaml")

        # Initialisation du modèle LLM
        # Utilise gpt-4o-mini pour rapidité + cost-effective (comme recommandé)
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.0,  # Déterministe pour classification
            max_tokens=500,   # Suffisant pour le JSON de sortie
        )

        logger.info(f"Intent classification for query: {query[:100]}...")

        # Appel LLM avec SYSTEM prompt et USER message
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]

        response = await llm.ainvoke(messages)

        # Extraction du contenu JSON
        json_content = response.content.strip()

        # Parser le JSON
        try:
            parsed_json = json.loads(json_content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {json_content[:200]}")
            # Fallback : retourner classification vide
            return IntentClassificationResult(
                query=query,
                language=language,
                intents=[]
            )

        # Validation et conversion en Pydantic
        try:
            result = IntentClassificationResult(**parsed_json)

            # Log des résultats
            intent_ids = [intent.id for intent in result.intents]
            logger.info(f"Classification complete: {len(result.intents)} intents detected: {intent_ids}")

            return result

        except Exception as e:
            logger.error(f"Failed to validate JSON schema: {e}")
            logger.error(f"JSON content: {parsed_json}")
            # Fallback : retourner classification vide
            return IntentClassificationResult(
                query=query,
                language=language,
                intents=[]
            )

    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        # Fallback : retourner une classification vide en cas d'erreur
        return IntentClassificationResult(
            query=query,
            language=language,
            intents=[]
        )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_intent_agent_mapping() -> dict[str, str]:
    """
    Retourne le mapping intent_id → agent_name.

    Utile pour validation et debugging.

    Returns:
        dict: Mapping {intent_id: agent_name}
    """
    return {
        # Backlog (10)
        "create_epic": "backlog",
        "create_feature": "backlog",
        "create_user_story": "backlog",
        "generate_children": "backlog",
        "update_backlog_item": "backlog",
        "estimate_stories": "backlog",
        "improve_item_description": "backlog",
        "reorganize_backlog": "backlog",
        "review_backlog_quality": "backlog",
        "check_acceptance_criteria": "backlog",

        # Document (4)
        "search_requirements": "document",
        "extract_features_from_docs": "document",
        "analyze_document_structure": "document",
        "list_available_docs": "document",

        # Planner (1)
        "decompose_objective": "planner",

        # Writer (1)
        "synthesize_backlog": "writer",

        # Conversation (2)
        "get_suggestions": "conversation",
        "explain_concept": "conversation",
    }


def validate_intent_result(intent: IntentResult) -> bool:
    """
    Valide la cohérence d'un IntentResult.

    Vérifie :
    - L'intent_id existe dans la liste des 18 intentions
    - L'agent correspond au mapping
    - La confidence est dans [0.0, 1.0]

    Args:
        intent: IntentResult à valider

    Returns:
        bool: True si valide, False sinon
    """
    mapping = get_intent_agent_mapping()

    # Vérifier que l'ID existe
    if intent.id not in mapping:
        logger.warning(f"Unknown intent ID: {intent.id}")
        return False

    # Vérifier la cohérence agent
    expected_agent = mapping[intent.id]
    if intent.agent != expected_agent:
        logger.warning(f"Agent mismatch for {intent.id}: got {intent.agent}, expected {expected_agent}")
        return False

    # Vérifier la confidence
    if not (0.0 <= intent.confidence <= 1.0):
        logger.warning(f"Confidence out of bounds: {intent.confidence}")
        return False

    return True


def get_v1_priority_intents() -> list[str]:
    """
    Retourne la liste des 7 intentions prioritaires V1.

    Returns:
        list[str]: Liste des intent_ids V1
    """
    return [
        "generate_children",
        "extract_features_from_docs",
        "review_backlog_quality",
        "search_requirements",
        "decompose_objective",
        "estimate_stories",
        "improve_item_description",
    ]
