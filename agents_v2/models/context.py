# agents_v2/models/context.py
"""
Modèles Pydantic pour le contexte projet (ProjectContextLoader V1).

Ces modèles représentent une vue structurée et agrégée d'un projet,
incluant la hiérarchie backlog et l'inventaire documents.
"""

from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Dict


class BacklogNode(BaseModel):
    """
    Représente un item backlog dans l'arbre hiérarchique.

    Supporte la récursivité via le champ `children` pour construire
    l'arbre complet Epic → Capability → Feature → US → UC.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str  # "Epic" | "Capability" | "Feature" | "US" | "UC"
    title: str
    description: str | None = None
    parent_id: int | None = None
    story_points: int | None = None
    ia_review_status: str = "approved"  # "approved" | "pending" | "modified"
    children: list[BacklogNode] = []


class DocumentInfo(BaseModel):
    """
    Information simplifiée sur un document avec statistiques de chunks.
    """
    id: int
    filename: str
    status: str  # "UPLOADED" | "ANALYZING" | "ANALYZED" | "ERROR"
    chunk_count: int
    total_tokens: int


class BacklogStats(BaseModel):
    """
    Statistiques agrégées du backlog projet.
    """
    total_items: int
    by_type: Dict[str, int]  # {"Epic": 2, "Feature": 8, ...}
    estimated_stories: int  # Nombre US avec story_points
    unestimated_stories: int  # Nombre US sans story_points


class DocumentStats(BaseModel):
    """
    Statistiques agrégées des documents projet.
    """
    total_documents: int
    analyzed_documents: int  # status == "ANALYZED"
    total_chunks: int  # Somme chunk_count
    total_tokens: int  # Somme total_tokens


class ProjectContext(BaseModel):
    """
    Structure complète du contexte projet.

    Contient la hiérarchie backlog, l'inventaire documents,
    et les statistiques agrégées pour injection dans les prompts agents.
    """
    project_id: int
    project_name: str
    project_description: str | None = None
    backlog_tree: list[BacklogNode] = []  # Racines (Epics)
    backlog_stats: BacklogStats
    documents: list[DocumentInfo] = []
    document_stats: DocumentStats
    loaded_at: str  # ISO timestamp
