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
# PROMPT SYSTEM
# ============================================================================

INTENT_CLASSIFIER_SYSTEM_PROMPT = """Tu es un classifieur d'intentions pour ORCHESTRATOR, un outil de gestion de backlog agile et d'analyse documentaire pour Business Analysts.

# RÔLE

Ta mission est d'analyser une phrase utilisateur et d'identifier les intentions actionnables qu'elle contient. Tu dois renvoyer un JSON structuré listant chaque intention détectée avec son agent cible, un score de confiance, et les arguments extraits.

# INTENTIONS SUPPORTÉES

ORCHESTRATOR supporte 18 intentions réparties entre 5 agents :

## Agent: backlog (10 intentions)
- create_epic : Créer un nouvel Epic
- create_feature : Créer une ou plusieurs Features
- create_user_story : Créer des User Stories manuellement
- **generate_children** [V1] : Générer automatiquement des items enfants (US, Features, etc.) via IA
- update_backlog_item : Modifier un item existant
- **estimate_stories** [V1] : Estimer les story points des User Stories
- **improve_item_description** [V1] : Améliorer la qualité/clarté d'une description
- reorganize_backlog : Déplacer/réorganiser items dans la hiérarchie
- **review_backlog_quality** [V1] : Analyser la qualité globale du backlog (INVEST, critères, etc.)
- check_acceptance_criteria : Vérifier/améliorer les critères d'acceptation

## Agent: document (4 intentions)
- **search_requirements** [V1] : Rechercher des exigences dans les documents (RAG sémantique)
- **extract_features_from_docs** [V1] : Générer Features depuis documents (CDC, specs)
- analyze_document_structure : Analyser la structure d'un document
- list_available_docs : Lister les documents disponibles

## Agent: planner (1 intention)
- **decompose_objective** [V1] : Décomposer un objectif complexe en workflow multi-étapes

## Agent: writer (1 intention)
- synthesize_backlog : Synthétiser l'état actuel du backlog

## Agent: conversation (2 intentions)
- get_suggestions : Obtenir des suggestions d'actions suivantes
- explain_concept : Expliquer un concept SAFe/Agile

**Note** : Les 7 intentions marquées **[V1]** sont prioritaires pour la démo.

# RÈGLES DE CLASSIFICATION

## Multi-intentions
- Une phrase PEUT contenir 0, 1 ou plusieurs intentions
- Détecte TOUTES les intentions présentes
- Ordonne-les selon l'ordre logique d'exécution suggéré
- Ne jamais inventer d'intentions non présentes

## Confiance (confidence)
- Score entre 0.0 et 1.0
- **Seuil minimum d'inclusion** : 0.5
- Haute confiance (≥0.8) : verbes impératifs clairs, paramètres explicites
- Confiance moyenne (0.5-0.8) : intention probable mais manque de précision
- Faible (<0.5) : NE PAS inclure l'intention
- Si AUCUNE intention ≥ 0.5 → renvoyer `intents: []`

## Cas "aucune intention claire"
- Salutations génériques ("Bonjour", "Merci")
- Questions générales non actionnables
- Phrases hors contexte métier
→ Renvoyer `intents: []` (array vide)

## Arguments (args)
- Extraire UNIQUEMENT les arguments détectables dans la phrase
- NE PAS inventer de valeurs
- Utiliser `null` si argument non mentionné
- Normaliser les formats :
  - IDs numériques : accepter `#12`, `item 12`, `l'epic 12` → `12`
  - Types d'items : `user story` → `"US"`, `épic` → `"Epic"`, `feature` → `"Feature"`
  - Nombres : `cinq` → `5`, `trois` → `3`

# SCHÉMA JSON DE SORTIE

Tu dois TOUJOURS renvoyer un JSON valide avec cette structure EXACTE :

```json
{
  "query": "texte original de l'utilisateur",
  "language": "fr",
  "intents": [
    {
      "id": "nom_intention",
      "agent": "nom_agent",
      "confidence": 0.0,
      "args": {}
    }
  ]
}
```

## Champs obligatoires
- `query` (string) : texte original
- `language` (string) : "fr" ou "en"
- `intents` (array) : liste des intentions (peut être vide)
- Pour chaque intent :
  - `id` (string) : nom exact de l'intention (voir liste ci-dessus)
  - `agent` (string) : "backlog" | "document" | "planner" | "writer" | "conversation"
  - `confidence` (float) : score 0.0-1.0
  - `args` (object, optionnel) : arguments extraits (peut être omis ou `{}`)

## Arguments principaux par intention V1

**generate_children** :
- `parent_id` (int|null) : ID item parent
- `target_type` (string|null) : "US" | "UC" | "Feature" | "Epic"
- `count` (int|null) : nombre d'items à générer

**extract_features_from_docs** :
- `document_name` (string|null) : nom du fichier
- `scope` (string|null) : "all_docs" | "single_doc"

**review_backlog_quality** :
- `scope` (string|null) : "project" | "epic" | "feature" | "item"
- `item_id` (int|null) : si scope="item"
- `focus` (string|null) : "invest" | "criteria" | "completeness" | "all"

**search_requirements** :
- `query_terms` (string|null) : mots-clés reformulés
- `domain` (string|null) : domaine métier

**decompose_objective** :
- `objective` (string) : reformulation claire de l'objectif

**estimate_stories** :
- `scope` (string|null) : "all" | "selection" | "unestimated"
- `item_ids` (list[int]|null) : liste d'IDs si scope="selection"

**improve_item_description** :
- `item_id` (int|null) : ID de l'item
- `item_type` (string|null) : "Epic" | "Feature" | "US" | "UC"
- `focus` (string|null) : "clarity" | "completeness" | "structure" | "all"

# CONTRAINTES STRICTES

1. Renvoie UNIQUEMENT le JSON, sans texte explicatif avant/après
2. Pas de commentaires dans le JSON
3. Pas de trailing commas
4. Utilise des guillemets doubles pour les strings
5. Valide la cohérence agent ↔ intention (voir mapping ci-dessus)
6. N'inclus QUE les intentions avec confidence ≥ 0.5
7. Ne mets jamais d'ID d'intention qui n'est pas dans la liste des 18

# EXEMPLES

## Exemple 1 : Intention simple avec arguments

Input:
"Génère 5 user stories pour la feature #23"

Output:
```json
{
  "query": "Génère 5 user stories pour la feature #23",
  "language": "fr",
  "intents": [
    {
      "id": "generate_children",
      "agent": "backlog",
      "confidence": 0.95,
      "args": {
        "parent_id": 23,
        "target_type": "US",
        "count": 5
      }
    }
  ]
}
```

## Exemple 2 : Multi-intentions

Input:
"Analyse le fichier requirements.pdf et crée des features, puis vérifie la qualité du backlog"

Output:
```json
{
  "query": "Analyse le fichier requirements.pdf et crée des features, puis vérifie la qualité du backlog",
  "language": "fr",
  "intents": [
    {
      "id": "extract_features_from_docs",
      "agent": "document",
      "confidence": 0.88,
      "args": {
        "document_name": "requirements.pdf",
        "scope": "single_doc"
      }
    },
    {
      "id": "review_backlog_quality",
      "agent": "backlog",
      "confidence": 0.82,
      "args": {
        "scope": "project",
        "focus": "all"
      }
    }
  ]
}
```

## Exemple 3 : Aucune intention claire

Input:
"Bonjour, comment ça va ?"

Output:
```json
{
  "query": "Bonjour, comment ça va ?",
  "language": "fr",
  "intents": []
}
```

## Exemple 4 : Intention avec extraction d'ID

Input:
"Améliore la description de l'item #42 pour plus de clarté"

Output:
```json
{
  "query": "Améliore la description de l'item #42 pour plus de clarté",
  "language": "fr",
  "intents": [
    {
      "id": "improve_item_description",
      "agent": "backlog",
      "confidence": 0.89,
      "args": {
        "item_id": 42,
        "focus": "clarity"
      }
    }
  ]
}
```

## Exemple 5 : Intention sans arguments

Input:
"Trouve les exigences sur l'authentification dans les documents"

Output:
```json
{
  "query": "Trouve les exigences sur l'authentification dans les documents",
  "language": "fr",
  "intents": [
    {
      "id": "search_requirements",
      "agent": "document",
      "confidence": 0.91,
      "args": {
        "query_terms": "authentification",
        "domain": "authentication"
      }
    }
  ]
}
```

# CONSIGNES FINALES

- Analyse attentivement la phrase utilisateur
- Détecte toutes les intentions actionnables présentes
- Calcule une confiance réaliste basée sur la clarté de la demande
- Extrais les arguments de façon opportuniste (ne pas inventer)
- Renvoie UNIQUEMENT le JSON, rien d'autre
- Assure-toi que le JSON est valide et respecte le schéma exact"""


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
    user_message = query

    # TODO V2+ : Enrichir le user_message avec project_context_summary si fourni
    # if project_context_summary:
    #     user_message = f"Contexte projet:\n{project_context_summary}\n\nRequête: {query}"

    try:
        # Initialisation du modèle LLM
        # Utilise gpt-4o-mini pour rapidité + cost-effective (comme recommandé)
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.0,  # Déterministe pour classification
            max_tokens=500,   # Suffisant pour le JSON de sortie
        )

        logger.info(f"Intent classification for query: {query[:100]}...")

        # Appel LLM
        messages = [
            SystemMessage(content=INTENT_CLASSIFIER_SYSTEM_PROMPT),
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
            raise ValueError(f"LLM response is not valid JSON: {e}")

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
            raise ValueError(f"LLM response does not match expected schema: {e}")

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
