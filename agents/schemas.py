# agents/schemas.py
from typing import List, Optional, Union
from pydantic import BaseModel, Field, model_validator
import re

_AC_FALLBACKS = [
    "Cas nominal : valider le comportement attendu.",
    "Cas alternatif : gérer les erreurs ou scénarios limites.",
]

_BULLET_RE = re.compile(r"^\s*(?:[-\*•]|\d+[.)])\s*")


def ensure_acceptance_list(values: Optional[Union[str, List[str]]]) -> List[str]:
    if values is None:
        collected: List[str] = []
    elif isinstance(values, str):
        parts = re.split(r"[\r\n]+", values)
        collected = [part.strip() for part in parts]
    else:
        collected = [str(item).strip() for item in values]

    normalized: List[str] = []
    seen = set()
    for entry in collected:
        cleaned = _BULLET_RE.sub("", entry).strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(cleaned)

    fallback_iter = iter(_AC_FALLBACKS)
    while len(normalized) < 2:
        try:
            candidate = next(fallback_iter)
        except StopIteration:
            candidate = "Définir un scénario supplémentaire."  # safety net
        key = candidate.casefold()
        if key not in seen:
            seen.add(key)
            normalized.append(candidate)

    return normalized

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


class FeatureInput(BaseModel):
    title: str
    description: Optional[str] = None
    type: str = "Feature"
    acceptance_criteria: Optional[Union[str, List[str]]] = None

    @model_validator(mode="after")
    def _normalize_acceptance_criteria(self) -> "FeatureInput":
        lines = ensure_acceptance_list(self.acceptance_criteria)
        self.acceptance_criteria = "\n".join(f"- {line}" for line in lines)
        return self

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
