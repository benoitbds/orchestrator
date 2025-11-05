"""API endpoints for Human-in-the-Loop approvals."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import timedelta
from agents_v2.approval import (
    get_approval_request, 
    submit_decision, 
    ApprovalDecision,
    get_pending_approvals_for_run
)
from backend.app.security import get_current_user_optional

router = APIRouter(prefix="/approvals", tags=["approvals"])

class ApprovalDecisionRequest(BaseModel):
    decision: ApprovalDecision
    reason: str = ""

@router.get("/{run_id}")
async def get_pending_approvals(
    run_id: str,
    user=Depends(get_current_user_optional)
):
    """Get all pending approvals for a run."""
    
    # Get all pending approvals for this run
    requests = get_pending_approvals_for_run(run_id)
    
    if not requests:
        return {"pending_approvals": []}
    
    return {
        "pending_approvals": [{
            "run_id": request.run_id,
            "step_index": request.step_index,
            "agent": request.agent,
            "objective": request.objective,
            "created_at": request.created_at.isoformat(),
            "timeout_at": (request.created_at + timedelta(minutes=5)).isoformat(),
            "context": request.context
        } for request in requests]
    }

@router.post("/{run_id}/{step_index}")
async def submit_approval_decision(
    run_id: str,
    step_index: int,
    decision_request: ApprovalDecisionRequest,
    user=Depends(get_current_user_optional)
):
    """Submit approval decision (approve/reject/modify)."""
    
    request = get_approval_request(run_id, step_index)
    if not request:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    # Validate decision
    if decision_request.decision not in ["approve", "reject", "modify"]:
        raise HTTPException(status_code=400, detail="Invalid decision")
    
    submit_decision(
        run_id=run_id,
        step_index=step_index,
        decision=decision_request.decision,
        reason=decision_request.reason
    )
    
    return {
        "success": True,
        "decision": decision_request.decision,
        "reason": decision_request.reason,
        "message": f"Decision '{decision_request.decision}' recorded successfully"
    }

@router.get("/{run_id}/status")
async def get_approval_status(
    run_id: str,
    user=Depends(get_current_user_optional)
):
    """Get overall approval status for a run."""
    
    requests = get_pending_approvals_for_run(run_id)
    
    return {
        "run_id": run_id,
        "has_pending_approvals": len(requests) > 0,
        "pending_count": len(requests),
        "requests": [{
            "step_index": req.step_index,
            "agent": req.agent,
            "objective": req.objective[:100] + ("..." if len(req.objective) > 100 else ""),
            "status": "pending"
        } for req in requests]
    }