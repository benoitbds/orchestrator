from typing import Any, Iterable, List

from fastapi import APIRouter, Depends, Request

from backend.app.security import get_current_user_optional
from orchestrator import crud

router = APIRouter(prefix="/projects", tags=["projects"])


def _filter_projects_for_user(projects: Iterable[Any], user_uid: str) -> list[Any]:
    filtered: list[Any] = []
    for project in projects:
        owner = None
        if isinstance(project, dict):
            owner = project.get("user_uid")
        else:
            owner = getattr(project, "user_uid", None)

        if owner is None or owner == user_uid:
            filtered.append(project)
    return filtered


@router.get("", response_model=List[Any])
def list_projects(request: Request, user=Depends(get_current_user_optional)):
    projects: list[Any] = []

    get_for_user = getattr(crud, "get_projects_for_user", None)
    if callable(get_for_user):
        projects = list(get_for_user(user["uid"]) or [])

    if not projects and hasattr(crud, "get_projects"):
        projects = _filter_projects_for_user(crud.get_projects() or [], user["uid"])

    return projects
