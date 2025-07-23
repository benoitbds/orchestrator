# orchestrator/models.py
from pydantic import BaseModel

class Project(BaseModel):
    id: int
    name: str
    description: str | None = None

class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class Item(BaseModel):
    id: int
    project_id: int
    title: str
    type: str
    parent_id: int | None = None


class ItemCreate(BaseModel):
    project_id: int
    title: str
    type: str
    parent_id: int | None = None


class ItemUpdate(BaseModel):
    title: str | None = None
    type: str | None = None
    parent_id: int | None = None
