# agents_v2/context_loader.py
"""
ProjectContextLoader V1 : Chargement et mise en cache du contexte projet.

Fournit une vue structurée du projet (backlog + documents) pour injection
dans les prompts des agents LangGraph.
"""

from datetime import datetime
from collections import Counter
from typing import Dict

# TODO: Ajuster les imports si la structure du projet diffère
from orchestrator import crud
from agents_v2.models.context import (
    ProjectContext,
    BacklogNode,
    BacklogStats,
    DocumentInfo,
    DocumentStats,
)


class ProjectContextLoader:
    """
    Charge et met en cache le contexte complet d'un projet.

    Cache simple in-memory (dict) sans TTL automatique.
    Invalidation manuelle via invalidate_cache().
    """

    def __init__(self) -> None:
        """Initialise le loader avec un cache vide."""
        self._cache: Dict[int, ProjectContext] = {}

    async def load_context(self, project_id: int, user_uid: str) -> ProjectContext:
        """
        Charge le contexte complet d'un projet.

        Args:
            project_id: ID du projet à charger
            user_uid: UID utilisateur (pour audit/logging, pas de vérif permissions V1)

        Returns:
            ProjectContext: Structure complète avec backlog + documents

        Raises:
            ValueError: Si le projet n'existe pas
        """
        # 1. Vérifier cache
        if project_id in self._cache:
            return self._cache[project_id]

        # 2. Charger depuis DB
        conn = crud.get_db_connection()
        try:
            # 3. Charger métadonnées projet
            project = crud.get_project(conn, project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")

            # 4. Charger tous les backlog items
            items_rows = crud.list_items(
                conn=conn,
                project_id=project_id,
                item_type=None,  # Tous types
                parent_id=None,  # Tous parents
                status=None      # Tous statuts
            )

            # 5. Construire arbre backlog
            backlog_tree, backlog_stats = self._build_backlog_tree(items_rows)

            # 6. Charger documents
            docs_rows = crud.list_documents(conn, project_id)

            # 7. Enrichir documents avec stats chunks
            documents = []
            for doc_row in docs_rows:
                doc_info = self._load_document_info(conn, doc_row)
                documents.append(doc_info)

            # 8. Calculer stats documents
            document_stats = self._calculate_document_stats(documents)

            # 9. Construire ProjectContext
            context = ProjectContext(
                project_id=project_id,
                project_name=project.get("name", "Unknown"),
                project_description=project.get("description"),
                backlog_tree=backlog_tree,
                backlog_stats=backlog_stats,
                documents=documents,
                document_stats=document_stats,
                loaded_at=datetime.utcnow().isoformat() + "Z"
            )

            # 10. Mettre en cache
            self._cache[project_id] = context

            return context

        finally:
            conn.close()

    def get_summary(self, context: ProjectContext) -> str:
        """
        Génère un résumé texte markdown du contexte projet.

        Args:
            context: ProjectContext à résumer

        Returns:
            str: Résumé markdown (~300-500 tokens)
        """
        lines = []

        # Header
        lines.append(f'## Contexte Projet: "{context.project_name}"')
        lines.append("")

        if context.project_description:
            lines.append(context.project_description)
            lines.append("")

        # Section Backlog
        stats = context.backlog_stats
        lines.append(f"### Backlog ({stats.total_items} items)")
        lines.append("")

        # Epics
        epics = [node for node in context.backlog_tree if node.type == "Epic"]
        if epics:
            epic_count = len(epics)
            lines.append(f"**Epics** ({epic_count}):")
            for epic in epics:
                feature_count = len([c for c in epic.children if c.type in ["Feature", "Capability"]])
                story_count = self._count_stories_recursive(epic)
                lines.append(f"- {epic.title} ({feature_count} features, {story_count} stories)")
            lines.append("")

        # Features (max 5)
        features = self._collect_nodes_by_type(context.backlog_tree, "Feature")
        if features:
            feature_count = len(features)
            lines.append(f"**Features** ({feature_count}):")
            feature_titles = [f.title for f in features[:5]]
            if len(features) > 5:
                feature_titles.append(f"... et {len(features) - 5} autres")
            lines.append(", ".join(feature_titles))
            lines.append("")

        # User Stories
        us_count = stats.by_type.get("US", 0)
        if us_count > 0:
            lines.append(
                f"**User Stories** ({us_count}): "
                f"{stats.estimated_stories}/{stats.unestimated_stories} estimées"
            )
            lines.append("")

        # Section Documents
        doc_stats = context.document_stats
        lines.append(
            f"### Documents ({doc_stats.analyzed_documents}/{doc_stats.total_documents} analysés)"
        )
        lines.append("")

        if context.documents:
            for doc in context.documents:
                lines.append(
                    f"- {doc.filename} ({doc.chunk_count} chunks, {doc.total_tokens} tokens)"
                )
            lines.append("")
        else:
            lines.append("*Aucun document disponible*")
            lines.append("")

        # Footer
        lines.append("---")
        lines.append(f"*Contexte chargé le {context.loaded_at}*")

        return "\n".join(lines)

    def invalidate_cache(self, project_id: int) -> None:
        """
        Invalide le cache pour un projet.

        Args:
            project_id: ID du projet à invalider
        """
        self._cache.pop(project_id, None)

    # --- Méthodes privées ---

    def _build_backlog_tree(self, items_rows) -> tuple[list[BacklogNode], BacklogStats]:
        """
        Construit l'arbre backlog et calcule les stats.

        Args:
            items_rows: Liste de rows SQLite (dict-like)

        Returns:
            tuple: (backlog_tree racines, BacklogStats)
        """
        if not items_rows:
            empty_stats = BacklogStats(
                total_items=0,
                by_type={},
                estimated_stories=0,
                unestimated_stories=0
            )
            return ([], empty_stats)

        # Créer dict de tous les nodes
        nodes: Dict[int, BacklogNode] = {}
        for row in items_rows:
            node = BacklogNode(
                id=row["id"],
                type=row["type"],
                title=row["title"],
                description=row.get("description"),
                parent_id=row.get("parent_id"),
                story_points=row.get("story_points"),
                ia_review_status=row.get("ia_review_status", "approved"),
                children=[]
            )
            nodes[node.id] = node

        # Construire relations parent-enfant
        roots = []
        for node in nodes.values():
            if node.parent_id is None:
                roots.append(node)
            else:
                parent = nodes.get(node.parent_id)
                if parent:
                    parent.children.append(node)

        # Calculer stats
        total_items = len(items_rows)
        by_type = Counter(row["type"] for row in items_rows)

        estimated_stories = sum(
            1 for row in items_rows
            if row["type"] == "US" and row.get("story_points") is not None
        )
        unestimated_stories = sum(
            1 for row in items_rows
            if row["type"] == "US" and row.get("story_points") is None
        )

        stats = BacklogStats(
            total_items=total_items,
            by_type=dict(by_type),
            estimated_stories=estimated_stories,
            unestimated_stories=unestimated_stories
        )

        return (roots, stats)

    def _load_document_info(self, conn, doc_row) -> DocumentInfo:
        """
        Charge info document avec stats chunks depuis DB.

        Args:
            conn: Connexion SQLite
            doc_row: Row document depuis crud.list_documents()

        Returns:
            DocumentInfo avec chunk_count et total_tokens
        """
        doc_id = doc_row["id"]

        # Query stats chunks
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                COUNT(*) as chunk_count,
                COALESCE(SUM(token_count), 0) as total_tokens
            FROM document_chunks
            WHERE doc_id = ?
            """,
            (doc_id,)
        )
        row = cursor.fetchone()

        chunk_count = row["chunk_count"] if row else 0
        total_tokens = row["total_tokens"] if row else 0

        return DocumentInfo(
            id=doc_id,
            filename=doc_row["filename"],
            status=doc_row.get("status", "UPLOADED"),
            chunk_count=chunk_count,
            total_tokens=total_tokens
        )

    def _calculate_document_stats(self, documents: list[DocumentInfo]) -> DocumentStats:
        """
        Calcule statistiques agrégées des documents.

        Args:
            documents: Liste DocumentInfo

        Returns:
            DocumentStats
        """
        total_documents = len(documents)
        analyzed_documents = sum(1 for doc in documents if doc.status == "ANALYZED")
        total_chunks = sum(doc.chunk_count for doc in documents)
        total_tokens = sum(doc.total_tokens for doc in documents)

        return DocumentStats(
            total_documents=total_documents,
            analyzed_documents=analyzed_documents,
            total_chunks=total_chunks,
            total_tokens=total_tokens
        )

    def _count_stories_recursive(self, node: BacklogNode) -> int:
        """Compte récursivement les US sous un node."""
        count = 1 if node.type == "US" else 0
        for child in node.children:
            count += self._count_stories_recursive(child)
        return count

    def _collect_nodes_by_type(
        self,
        nodes: list[BacklogNode],
        node_type: str
    ) -> list[BacklogNode]:
        """Collecte tous les nodes d'un type donné (récursif)."""
        result = []
        for node in nodes:
            if node.type == node_type:
                result.append(node)
            result.extend(self._collect_nodes_by_type(node.children, node_type))
        return result


# --- Singleton global ---

_loader_instance: ProjectContextLoader | None = None


def get_context_loader() -> ProjectContextLoader:
    """
    Retourne l'instance singleton du ProjectContextLoader.

    Returns:
        ProjectContextLoader: Instance globale (créée si nécessaire)
    """
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = ProjectContextLoader()
    return _loader_instance
