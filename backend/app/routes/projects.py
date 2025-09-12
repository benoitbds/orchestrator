from fastapi import APIRouter, Depends
from typing import Any, List
from backend.app.security import get_current_user
from orchestrator import crud

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=List[Any])
def list_projects(user=Depends(get_current_user)):
    if hasattr(crud, "get_projects_for_user"):
        projects = crud.get_projects_for_user(user["uid"])
    else:
        projects = crud.get_projects()
    return projects or []
