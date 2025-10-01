"""Workflow executor - Manages sequential execution of planned steps."""
from .state import AgentState, WorkflowStep
from .streaming import get_stream_manager
from typing import Literal
import logging

logger = logging.getLogger(__name__)

async def workflow_executor_node(state: AgentState) -> dict:
    """Execute next step in workflow or complete if done.
    
    This node acts as a coordinator between planned steps.
    """
    
    run_id = state.get("run_id", "unknown")
    stream = get_stream_manager(run_id)
    
    workflow_steps = state.get("workflow_steps", [])
    current_step_index = state.get("current_step_index", 0)
    
    logger.info(f"WorkflowExecutor: step {current_step_index} of {len(workflow_steps)}")
    
    # Check if workflow complete
    if not workflow_steps or current_step_index >= len(workflow_steps):
        await stream.emit_status("✅ Workflow complete", 1.0)
        logger.info("Workflow execution completed")
        return {
            "next_agent": "end",
            "status_message": "✅ All workflow steps completed"
        }
    
    # Get current step
    current_step = workflow_steps[current_step_index]
    
    logger.info(f"Processing step {current_step_index}: {current_step['objective']}")
    
    # Check if step requires approval and hasn't been approved
    if current_step["requires_approval"] and current_step["status"] == "pending":
        logger.info(f"Step {current_step_index} requires approval")
        
        await stream.emit_status(
            f"⏸ Awaiting approval for: {current_step['objective']}",
            current_step_index / len(workflow_steps)
        )
        
        return {
            "is_paused": True,
            "pending_approval": {
                "step_index": current_step_index,
                "agent": current_step["agent"],
                "objective": current_step["objective"],
                "message": f"Approve: {current_step['objective']}?",
                "context": {
                    "workflow_steps": workflow_steps,
                    "current_step_index": current_step_index
                }
            },
            "next_agent": "approval",  # Special state for HITL
            "status_message": f"⏸ Awaiting approval (Step {current_step_index + 1})"
        }
    
    # Execute current step
    workflow_steps[current_step_index]["status"] = "running"
    
    progress = current_step_index / len(workflow_steps)
    await stream.emit_status(
        f"▶ Executing step {current_step_index + 1}/{len(workflow_steps)}: {current_step['objective']}",
        progress
    )
    
    # Route to appropriate agent
    next_agent = current_step["agent"]
    
    logger.info(f"Routing to {next_agent} agent for step {current_step_index}")
    
    return {
        "next_agent": next_agent,
        "current_step_index": current_step_index,
        "workflow_steps": workflow_steps,
        "status_message": f"▶ Executing: {current_step['objective']}",
        "current_agent": "workflow_executor"
    }

async def advance_workflow_node(state: AgentState) -> dict:
    """Advance to next workflow step after agent completion."""
    
    run_id = state.get("run_id", "unknown")
    stream = get_stream_manager(run_id)
    
    workflow_steps = state.get("workflow_steps", [])
    current_step_index = state.get("current_step_index", 0)
    
    logger.info(f"AdvanceWorkflow: completing step {current_step_index}")
    
    # Mark current step as done
    if current_step_index < len(workflow_steps):
        workflow_steps[current_step_index]["status"] = "done"
        workflow_steps[current_step_index]["result"] = {
            "items_created": state.get("items_created", []),
            "documents_searched": state.get("documents_searched", []),
            "tool_results": state.get("tool_results", {}),
            "status_message": state.get("status_message", "")
        }
        
        logger.info(f"Step {current_step_index} marked as done")
        
        await stream.emit_status(
            f"✅ Step {current_step_index + 1} completed: {workflow_steps[current_step_index]['objective']}",
            (current_step_index + 1) / len(workflow_steps)
        )
    
    # Move to next step
    next_index = current_step_index + 1
    
    return {
        "current_step_index": next_index,
        "workflow_steps": workflow_steps,
        "next_agent": "workflow_executor",  # Route back to executor
        "current_agent": "advance_workflow"
    }