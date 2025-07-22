# orchestrator/models.py
from pydantic import BaseModel

class Project(BaseModel):
    id: int
    name: str
    description: str | None = None

class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


# ----- Item models -----

class ItemBase(BaseModel):
    project_id: int
    type: str
    title: str
    description: str | None = None
    status: str
    parent_id: int | None = None
    acceptance_criteria: dict | None = None


class ItemCreate(ItemBase):
    expected_result: str | None = None


class Item(ItemBase):
    id: int
    created_at: str
    updated_at: str
    expected_result: str | None = None
