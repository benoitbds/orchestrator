from langchain_core.tools import tool
from orchestrator import crud
import logging

logger = logging.getLogger(__name__)

@tool
async def search_documents(
    project_id: int,
    query: str,
    limit: int = 5,
    similarity_threshold: float = 0.3
) -> dict:
    """Recherche sémantique dans les documents du projet.
    
    Args:
        project_id: ID du projet
        query: Requête de recherche
        limit: Nombre max de résultats
        similarity_threshold: Seuil de similarité (0.0-1.0)
        
    Returns:
        Dict avec results (list) et metadata
    """
    try:
        logger.info(f"Searching documents in project {project_id} for: {query}")
        
        # TODO: Utiliser vraie logique search existante
        # Pour l'instant, mock response pour tests
        results = [
            {
                "document_id": 1,
                "filename": "specifications.pdf",
                "content": "Mock search result for: " + query,
                "similarity": 0.85,
                "page": 1
            }
        ]
        
        return {
            "project_id": project_id,
            "query": query,
            "results": results,
            "total_found": len(results)
        }
        
    except Exception as e:
        logger.error(f"Search documents failed: {e}")
        return {"error": str(e), "results": []}

@tool
async def list_documents(project_id: int) -> dict:
    """Lister tous les documents disponibles dans le projet.
    
    Args:
        project_id: ID du projet
        
    Returns:
        Dict avec documents (list) et metadata
    """
    try:
        logger.info(f"Listing documents in project {project_id}")
        
        # TODO: Utiliser vraie logique CRUD
        documents = [
            {
                "id": 1,
                "filename": "specifications.pdf",
                "status": "ANALYZED",
                "size_kb": 2048,
                "pages": 25
            },
            {
                "id": 2,
                "filename": "requirements.docx",
                "status": "UPLOADED",
                "size_kb": 512,
                "pages": 10
            }
        ]
        
        return {
            "project_id": project_id,
            "documents": documents,
            "total_count": len(documents)
        }
        
    except Exception as e:
        logger.error(f"List documents failed: {e}")
        return {"error": str(e), "documents": []}

@tool
async def get_document_content(document_id: int) -> dict:
    """Récupérer le contenu complet d'un document.
    
    Args:
        document_id: ID du document
        
    Returns:
        Dict avec content, filename et metadata
    """
    try:
        logger.info(f"Getting content for document {document_id}")
        
        # TODO: Utiliser vraie logique CRUD
        content = f"Mock content for document {document_id}. This would contain the full document text..."
        
        return {
            "document_id": document_id,
            "filename": f"document_{document_id}.pdf",
            "content": content,
            "word_count": len(content.split()),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Get document content failed: {e}")
        return {"error": str(e), "content": ""}

@tool
async def draft_features_from_documents(
    project_id: int,
    parent_epic_id: int | None = None
) -> dict:
    """Analyser documents projet et générer Features automatiquement (IA).
    
    Utilise RAG pour extraire exigences fonctionnelles depuis CDC/specs
    et créer Features correspondantes dans le backlog.
    
    Args:
        project_id: ID du projet
        parent_epic_id: Epic parent optionnel pour les Features
        
    Returns:
        Dict avec features_created (list[int]) et summary
    """
    try:
        logger.info(f"Drafting features from documents for project {project_id}")
        
        # TODO: Utiliser logique existante draft_features_from_matches
        # Pour l'instant, mock response
        features_created = [101, 102, 103]
        
        return {
            "project_id": project_id,
            "parent_epic_id": parent_epic_id,
            "features_created": features_created,
            "summary": f"Generated {len(features_created)} features from project documents",
            "source_documents": ["specifications.pdf", "requirements.docx"]
        }
        
    except Exception as e:
        logger.error(f"Draft features failed: {e}")
        return {"error": str(e), "features_created": []}

@tool
async def analyze_document_structure(document_id: int) -> dict:
    """Analyser la structure d'un document (sections, chapitres, etc.).
    
    Utile pour comprendre l'organisation d'un CDC ou spec technique.
    
    Args:
        document_id: ID du document à analyser
        
    Returns:
        Dict avec structure (sections), word_count, key_topics
    """
    try:
        logger.info(f"Analyzing structure for document {document_id}")
        
        # Mock analysis for now
        sections = [
            "1. Introduction",
            "2. Functional Requirements", 
            "3. Technical Specifications",
            "4. User Stories",
            "5. Acceptance Criteria"
        ]
        
        return {
            "document_id": document_id,
            "filename": f"document_{document_id}.pdf",
            "sections": sections,
            "word_count": 5420,
            "line_count": 245,
            "key_topics": ["authentication", "payment", "user management", "notifications"],
            "estimated_features": len(sections) - 1  # Excluding intro
        }
        
    except Exception as e:
        logger.error(f"Analyze document structure failed: {e}")
        return {"error": str(e), "sections": []}