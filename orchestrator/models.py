# orchestrator/models.py
from pydantic import BaseModel

class Project(BaseModel):
    id: int
    name: str
    description: str | None = None

class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class BacklogItemBase(BaseModel):
    title: str
    description: str | None = None
    type: str
    project_id: int
    parent_id: int | None = None


class BacklogItemCreate(BacklogItemBase):
    pass


class BacklogItem(BacklogItemBase):
    id: int


class BacklogItemUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    type: str | None = None
    parent_id: int | None = None
