# agents/schemas.py
from typing import List, Optional
from pydantic import BaseModel, Field

class PlanStep(BaseModel):
    id: int
    title: str
    description: str
    depends_on: Optional[List[int]] = Field(
        default_factory=list, description="IDs des étapes préalables"
    )

class Plan(BaseModel):
    objective: str
    steps: List[PlanStep]

class ExecResult(BaseModel):
    success: bool
    stdout: str
    stderr: str
    artifacts: List[str] = Field(default_factory=list, description="Paths of files produced")

class RenderResult(BaseModel):
    """Sortie du Writer : un HTML prêt à afficher + un résumé texte court."""
    html: str
    summary: str
    artifacts: List[str] = Field(default_factory=list, description="Chemins de fichiers joints")

class FeatureProposal(BaseModel):
    """Représente une proposition de feature avec titre et description."""
    title: str
    description: str

class FeatureProposals(BaseModel):
    """Liste de propositions de features pour un épic donné."""
    project_id: int
    parent_id: int
    parent_title: str
    proposals: List[FeatureProposal]
