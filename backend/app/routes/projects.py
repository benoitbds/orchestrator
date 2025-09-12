from fastapi import APIRouter, Depends
from backend.app.security import get_current_user
from orchestrator import crud

router = APIRouter(prefix="/projects", tags=["projects"])

@router.get("")
def list_projects(user=Depends(get_current_user)):
    return crud.get_projects_for_user(user["uid"]) if hasattr(crud, "get_projects_for_user") else crud.get_projects()
