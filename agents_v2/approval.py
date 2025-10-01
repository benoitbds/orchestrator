"""Human-in-the-Loop approval system."""
import asyncio
from typing import Literal
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

ApprovalDecision = Literal["approve", "reject", "modify"]

class ApprovalRequest:
    """Represents a pending approval request."""
    
    def __init__(
        self,
        run_id: str,
        step_index: int,
        agent: str,
        objective: str,
        context: dict
    ):
        self.run_id = run_id
        self.step_index = step_index
        self.agent = agent
        self.objective = objective
        self.context = context
        self.created_at = datetime.utcnow()
        self.decision: ApprovalDecision | None = None
        self.decision_reason: str | None = None
        self.future: asyncio.Future = asyncio.Future()
    
    async def wait_for_decision(self, timeout_seconds: int = 300) -> ApprovalDecision:
        """Wait for human decision with timeout."""
        try:
            decision = await asyncio.wait_for(self.future, timeout=timeout_seconds)
            logger.info(f"Approval decision received: {decision} for run {self.run_id}, step {self.step_index}")
            return decision
        except asyncio.TimeoutError:
            logger.warning(f"Approval timeout for run {self.run_id}, step {self.step_index}")
            return "reject"  # Auto-reject after timeout
    
    def decide(self, decision: ApprovalDecision, reason: str = ""):
        """Record human decision."""
        self.decision = decision
        self.decision_reason = reason
        logger.info(f"Approval decision set: {decision} for run {self.run_id}, step {self.step_index}")
        if not self.future.done():
            self.future.set_result(decision)

# Global registry of pending approvals
_pending_approvals: dict[str, ApprovalRequest] = {}

def create_approval_request(
    run_id: str,
    step_index: int,
    agent: str,
    objective: str,
    context: dict
) -> ApprovalRequest:
    """Create and register approval request."""
    request = ApprovalRequest(run_id, step_index, agent, objective, context)
    approval_key = f"{run_id}_{step_index}"
    _pending_approvals[approval_key] = request
    logger.info(f"Created approval request: {approval_key}")
    return request

def get_approval_request(run_id: str, step_index: int = None) -> ApprovalRequest | None:
    """Get pending approval request."""
    if step_index is not None:
        approval_key = f"{run_id}_{step_index}"
        return _pending_approvals.get(approval_key)
    
    # If no step_index provided, return first pending approval for this run
    for key, request in _pending_approvals.items():
        if request.run_id == run_id:
            return request
    return None

def get_pending_approvals_for_run(run_id: str) -> list[ApprovalRequest]:
    """Get all pending approvals for a run."""
    return [
        request for request in _pending_approvals.values()
        if request.run_id == run_id
    ]

def submit_decision(
    run_id: str,
    step_index: int,
    decision: ApprovalDecision,
    reason: str = ""
):
    """Submit human decision for approval."""
    request = get_approval_request(run_id, step_index)
    if request:
        request.decide(decision, reason)
        # Cleanup
        approval_key = f"{run_id}_{step_index}"
        del _pending_approvals[approval_key]
        logger.info(f"Cleaned up approval request: {approval_key}")

async def approval_node(state):
    """Node that pauses workflow for human approval."""
    
    from .streaming import get_stream_manager
    
    run_id = state.get("run_id", "unknown")
    stream = get_stream_manager(run_id)
    
    pending_approval = state.get("pending_approval")
    if not pending_approval:
        logger.error("No pending approval found in state")
        return {"next_agent": "end", "error": "No pending approval found"}
    
    step_index = pending_approval["step_index"]
    
    logger.info(f"Approval node processing: run {run_id}, step {step_index}")
    
    # Create approval request
    request = create_approval_request(
        run_id=run_id,
        step_index=step_index,
        agent=pending_approval["agent"],
        objective=pending_approval["objective"],
        context=pending_approval.get("context", {})
    )
    
    await stream.emit_status(
        f"⏸ Paused - Awaiting approval for: {pending_approval['objective']}",
        0
    )
    
    # Wait for human decision (5 min timeout)
    decision = await request.wait_for_decision(timeout_seconds=300)
    
    if decision == "approve":
        await stream.emit_status("✅ Approved - Continuing workflow", 0)
        
        # Mark step as approved in workflow
        workflow_steps = state.get("workflow_steps", [])
        if step_index < len(workflow_steps):
            workflow_steps[step_index]["status"] = "pending"  # Ready to execute
        
        return {
            "is_paused": False,
            "pending_approval": None,
            "next_agent": "workflow_executor",
            "status_message": "✅ Approved - Resuming",
            "workflow_steps": workflow_steps
        }
        
    elif decision == "reject":
        await stream.emit_status("❌ Rejected - Workflow cancelled", 0)
        return {
            "is_paused": False,
            "pending_approval": None,
            "next_agent": "end",
            "error": f"Workflow rejected: {request.decision_reason}",
            "status_message": "❌ Workflow cancelled by user"
        }
        
    else:  # modify
        await stream.emit_status("✏️ Modified - Adjusting workflow", 0)
        # TODO: Handle modification (Phase 3)
        logger.info("Modification requested - treating as approved for now")
        
        workflow_steps = state.get("workflow_steps", [])
        if step_index < len(workflow_steps):
            workflow_steps[step_index]["status"] = "pending"
        
        return {
            "is_paused": False,
            "pending_approval": None,
            "next_agent": "workflow_executor",
            "status_message": "✏️ Modified - Continuing",
            "workflow_steps": workflow_steps
        }