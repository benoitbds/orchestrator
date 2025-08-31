# orchestrator/models.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal, Union

class Project(BaseModel):
    id: int
    name: str
    description: str | None = None

class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class Document(BaseModel):
    """File uploaded to a project."""

    id: int
    project_id: int
    filename: str
    content: str | None = None
    embedding: list[float] | None = None
    filepath: str | None = None


class DocumentCreate(BaseModel):
    project_id: int
    filename: str
    content: str | None = None
    embedding: list[float] | None = None
    filepath: str | None = None


# For symmetry with other models
DocumentOut = Document


class LayoutNode(BaseModel):
    item_id: int
    x: float
    y: float
    pinned: bool = False


class LayoutUpdate(BaseModel):
    nodes: list[LayoutNode] = Field(default_factory=list)


class RunStep(BaseModel):
    """Timeline entry for a run."""

    order: int
    node: str
    timestamp: datetime
    content: str


class RunDetail(BaseModel):
    """Detailed representation of an orchestrator run."""

    run_id: str
    project_id: int | None = None
    objective: str
    status: Literal["running", "done"]
    created_at: datetime
    completed_at: datetime | None = None
    html: str | None = None
    summary: str | None = None
    artifacts: dict | None = None
    steps: list[RunStep] = Field(default_factory=list)


class RunSummary(BaseModel):
    """Lightweight run metadata for listings."""

    run_id: str
    project_id: int | None = None
    objective: str
    status: Literal["running", "done"]
    created_at: datetime
    completed_at: datetime | None = None


# Backward compatibility for existing imports
Run = RunDetail


# Base item model
class ItemBase(BaseModel):
    title: str
    description: str | None = None
    type: Literal["Epic", "Capability", "Feature", "US", "UC"]
    project_id: int
    parent_id: int | None = None

# Extra fields per type
# Base extras for creation (more flexible)
class EpicExtrasBase(BaseModel):
    state: Literal["Funnel","Reviewing","Analyzing","Backlog","Implementing","Done"] = "Funnel"
    benefit_hypothesis: str | None = None
    leading_indicators: str | None = None
    mvp_definition: str | None = None
    wsjf: float | None = None

class FeatureExtrasBase(BaseModel):
    benefit_hypothesis: str | None = None
    acceptance_criteria: str | None = None
    wsjf: float | None = None
    program_increment: str | None = None
    owner: str | None = None

class StoryExtrasBase(BaseModel):
    story_points: int | None = None
    acceptance_criteria: str | None = None
    invest_compliant: bool = False
    iteration: str | None = None
    status: Literal["Todo","Doing","Done"] = "Todo"

# Strict extras for output (with required fields)
class EpicExtras(BaseModel):
    state: Literal["Funnel","Reviewing","Analyzing","Backlog","Implementing","Done"] = "Funnel"
    benefit_hypothesis: str | None = None
    leading_indicators: str | None = None
    mvp_definition: str | None = None
    wsjf: float | None = None

class CapabilityExtras(BaseModel):
    state: Literal["Funnel","Reviewing","Analyzing","Backlog","Implementing","Done"] = "Funnel"
    benefit_hypothesis: str | None = None
    leading_indicators: str | None = None
    mvp_definition: str | None = None
    wsjf: float | None = None

class FeatureExtras(BaseModel):
    benefit_hypothesis: str | None = None
    acceptance_criteria: str | None = None
    wsjf: float | None = None
    program_increment: str | None = None
    owner: str | None = None

class StoryExtras(BaseModel):
    story_points: int | None = None
    acceptance_criteria: str | None = None
    invest_compliant: bool = False
    iteration: str | None = None
    status: Literal["Todo","Doing","Done"] = "Todo"

# Composite models for creation
class EpicCreate(ItemBase, EpicExtrasBase):
    type: Literal["Epic"] = "Epic"

class CapabilityCreate(ItemBase, EpicExtrasBase):
    type: Literal["Capability"] = "Capability"

class FeatureCreate(ItemBase, FeatureExtrasBase):
    type: Literal["Feature"] = "Feature"

class USCreate(ItemBase, StoryExtrasBase):
    type: Literal["US"] = "US"

class UCCreate(ItemBase, StoryExtrasBase):
    type: Literal["UC"] = "UC"

# Union type for creation
BacklogItemCreate = Union[EpicCreate, CapabilityCreate, FeatureCreate, USCreate, UCCreate]

# Output models with ID and timestamps
class EpicOut(ItemBase, EpicExtras):
    id: int
    type: Literal["Epic"] = "Epic"
    created_at: datetime | None = None
    updated_at: datetime | None = None

class CapabilityOut(ItemBase, CapabilityExtras):
    id: int
    type: Literal["Capability"] = "Capability"
    created_at: datetime | None = None
    updated_at: datetime | None = None

class FeatureOut(ItemBase, FeatureExtras):
    id: int
    type: Literal["Feature"] = "Feature"
    created_at: datetime | None = None
    updated_at: datetime | None = None

class USOut(ItemBase, StoryExtras):
    id: int
    type: Literal["US"] = "US"
    created_at: datetime | None = None
    updated_at: datetime | None = None

class UCOut(ItemBase, StoryExtras):
    id: int
    type: Literal["UC"] = "UC"
    created_at: datetime | None = None
    updated_at: datetime | None = None

# Union type for output
ItemOut = Union[EpicOut, CapabilityOut, FeatureOut, USOut, UCOut]

# For backward compatibility
BacklogItem = ItemOut

# Update model
class BacklogItemUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    type: Literal["Epic", "Capability", "Feature", "US", "UC"] | None = None
    parent_id: int | None = None
    # Epic/Capability fields
    state: str | None = None
    benefit_hypothesis: str | None = None
    leading_indicators: str | None = None
    mvp_definition: str | None = None
    wsjf: float | None = None
    # Feature fields
    acceptance_criteria: str | None = None
    program_increment: str | None = None
    owner: str | None = None
    # Story fields (US/UC)
    story_points: int | None = None
    invest_compliant: bool | None = None
    iteration: str | None = None
    status: str | None = None
