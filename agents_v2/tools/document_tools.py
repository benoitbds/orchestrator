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
        
        # Utiliser la logique de recherche sémantique existante
        from agents.embeddings import embed_text, cosine_similarity
        
        # Générer l'embedding de la requête
        query_embedding = await embed_text(query)
        
        # Récupérer tous les chunks du projet
        chunks = crud.get_all_chunks_for_project(project_id)
        
        if not chunks:
            logger.info(f"No indexed chunks found for project {project_id}")
            return {
                "project_id": project_id,
                "query": query,
                "results": [],
                "total_found": 0,
                "message": "No indexed documents found. Please analyze documents first."
            }
        
        # Calculer la similarité pour chaque chunk
        scored_chunks = []
        for chunk in chunks:
            if chunk.get("embedding"):
                similarity = cosine_similarity(query_embedding, chunk["embedding"])
                if similarity >= similarity_threshold:
                    scored_chunks.append({
                        "document_id": chunk["doc_id"],
                        "chunk_id": chunk["id"],
                        "filename": chunk.get("filename", "unknown"),
                        "content": chunk["text"],
                        "similarity": float(similarity),
                        "chunk_index": chunk.get("chunk_index", 0)
                    })
        
        # Trier par similarité décroissante et limiter
        scored_chunks.sort(key=lambda x: x["similarity"], reverse=True)
        results = scored_chunks[:limit]
        
        logger.info(f"Found {len(results)} results (from {len(scored_chunks)} matches above threshold)")
        
        return {
            "project_id": project_id,
            "query": query,
            "results": results,
            "total_found": len(scored_chunks),
            "total_chunks": len(chunks)
        }
        
    except Exception as e:
        logger.error(f"Search documents failed: {e}", exc_info=True)
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
        
        # Récupérer les documents depuis la base de données
        docs = crud.get_documents(project_id)
        
        documents = []
        for doc in docs:
            # Obtenir les stats des chunks pour ce document
            total_chunks, chunks_with_embeddings = crud.document_chunk_stats(doc.id)
            
            # Calculer la taille approximative en KB
            content_size = len(doc.content or "") if hasattr(doc, "content") and doc.content else 0
            
            documents.append({
                "id": doc.id,
                "filename": doc.filename,
                "status": getattr(doc, "status", "UPLOADED"),
                "size_kb": content_size // 1024 if content_size > 0 else 0,
                "chunks": total_chunks,
                "chunks_with_embeddings": chunks_with_embeddings,
                "filepath": getattr(doc, "filepath", None)
            })
        
        logger.info(f"Found {len(documents)} documents in project {project_id}")
        
        return {
            "project_id": project_id,
            "documents": documents,
            "total_count": len(documents)
        }
        
    except Exception as e:
        logger.error(f"List documents failed: {e}", exc_info=True)
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
        
        # Récupérer le document depuis la base de données
        doc_data = crud.get_document(document_id)
        
        if not doc_data:
            logger.warning(f"Document {document_id} not found")
            return {
                "error": "Document not found",
                "document_id": document_id,
                "content": ""
            }
        
        content = doc_data.get("content", "")
        word_count = len(content.split()) if content else 0
        
        return {
            "document_id": document_id,
            "filename": doc_data.get("filename", "unknown"),
            "content": content,
            "word_count": word_count,
            "status": doc_data.get("status", "UPLOADED"),
            "project_id": doc_data.get("project_id")
        }
        
    except Exception as e:
        logger.error(f"Get document content failed: {e}", exc_info=True)
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
        
        from ..streaming import get_stream_manager
        from .backlog_tools import get_current_run_id
        
        # Utiliser la logique existante draft_features_from_matches
        from agents.handlers import draft_features_from_matches_handler
        
        # Appeler le handler avec les paramètres appropriés
        result = await draft_features_from_matches_handler({
            "project_id": project_id,
            "doc_query": "functional requirements features",
            "k": 5,
            "fallback_parse_full_doc": True
        })
        
        if not result.get("ok", False):
            error_msg = result.get("message", result.get("error", "Unknown error"))
            logger.error(f"Draft features failed: {error_msg}")
            return {
                "error": error_msg,
                "features_created": [],
                "project_id": project_id
            }
        
        # Extraire les IDs créés
        items = result.get("items", [])
        features_created = [item["id"] for item in items]
        
        # Emit real-time event for each feature created
        run_id = get_current_run_id()
        if run_id:
            import asyncio
            stream = get_stream_manager(run_id)
            for item in items:
                try:
                    item_data = {
                        "id": item.get("id"),
                        "title": item.get("title"),
                        "type": item.get("type", "Feature"),
                        "project_id": project_id,
                        "parent_id": parent_epic_id,
                        "description": item.get("description", "")
                    }
                    asyncio.create_task(stream.emit_item_created(item_data))
                except Exception as e:
                    logger.warning(f"Failed to emit item_created event: {e}")
        
        # Obtenir les noms des documents sources
        documents = crud.get_documents(project_id)
        source_documents = [doc.filename for doc in documents if getattr(doc, "status", None) == "ANALYZED"]
        
        logger.info(f"Successfully created {len(features_created)} features: {features_created}")
        
        return {
            "project_id": project_id,
            "parent_epic_id": parent_epic_id,
            "features_created": features_created,
            "summary": f"Generated {len(features_created)} features from project documents",
            "source_documents": source_documents or ["project documents"],
            "source": result.get("source", "rag")
        }
        
    except Exception as e:
        logger.error(f"Draft features failed: {e}", exc_info=True)
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
        
        # Récupérer le document
        doc_data = crud.get_document(document_id)
        
        if not doc_data:
            logger.warning(f"Document {document_id} not found")
            return {
                "error": "Document not found",
                "document_id": document_id,
                "sections": []
            }
        
        content = doc_data.get("content", "")
        
        # Extraire les sections en cherchant des patterns de titres
        import re
        sections = []
        
        # Patterns pour détecter les titres (numérotés ou en majuscules)
        title_patterns = [
            r'^#+\s+(.+)$',  # Markdown headers
            r'^(\d+\.?\s+.+)$',  # Numbered sections
            r'^([A-Z][A-Z\s]+)$',  # ALL CAPS titles
            r'^([A-Z].{0,80}:)$'  # Capitalized titles ending with :
        ]
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            for pattern in title_patterns:
                match = re.match(pattern, line)
                if match and len(line) < 120:  # Avoid false positives
                    sections.append(line)
                    break
        
        # Limiter aux 20 premières sections trouvées
        sections = sections[:20]
        
        # Calculer des métriques
        word_count = len(content.split()) if content else 0
        line_count = len([l for l in lines if l.strip()])
        
        # Obtenir les chunks pour une analyse plus précise
        chunks = crud.get_document_chunks(document_id)
        
        logger.info(f"Analyzed document {document_id}: {len(sections)} sections, {word_count} words, {len(chunks)} chunks")
        
        return {
            "document_id": document_id,
            "filename": doc_data.get("filename", "unknown"),
            "sections": sections if sections else ["No clear sections detected"],
            "word_count": word_count,
            "line_count": line_count,
            "chunk_count": len(chunks),
            "status": doc_data.get("status", "UPLOADED"),
            "estimated_features": max(1, len(sections) // 2) if sections else 0
        }
        
    except Exception as e:
        logger.error(f"Analyze document structure failed: {e}", exc_info=True)
        return {"error": str(e), "sections": []}