"""Workflow executor - Manages sequential execution of planned steps."""
from .state import AgentState
from .streaming import get_stream_manager
from .context_loader import get_context_loader
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
    logger.info(f"WorkflowExecutor: workflow_steps = {workflow_steps}")
    logger.info(f"WorkflowExecutor: State keys = {list(state.keys())}")
    
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
    logger.info(f"Step {current_step_index} status: {current_step['status']}, requires_approval: {current_step['requires_approval']}")
    
    # Check if step requires approval and hasn't been approved yet
    if current_step["requires_approval"] and current_step["status"] == "pending":
        logger.info(f"Step {current_step_index} requires approval, sending to approval node")
        
        await stream.emit_status(
            f"⏸ Awaiting approval for: {current_step['objective']}",
            (current_step_index + 1) / len(workflow_steps)
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
            "next_agent": "approval",
            "status_message": f"⏸ Awaiting approval (Step {current_step_index + 1})",
            "workflow_steps": workflow_steps
        }
    
    # Execute current step (only if approved or doesn't require approval)
    workflow_steps[current_step_index]["status"] = "running"
    
    # Calculate progress: step 1/10 = 10%, step 5/10 = 50%, etc.
    progress = (current_step_index + 1) / len(workflow_steps)
    await stream.emit_status(
        f"▶ Executing step {current_step_index + 1}/{len(workflow_steps)}: {current_step['objective']}",
        progress
    )
    
    # Route to appropriate agent
    next_agent = current_step["agent"]
    
    logger.info(f"Routing to {next_agent} agent for step {current_step_index}")
    
    # Add workflow context to state for agents to use
    workflow_context = {
        "step_index": current_step_index,
        "total_steps": len(workflow_steps),
        "step_description": current_step['objective']
    }

    # Load project context if project_id present (Phase 2D - ProjectContextLoader V1)
    project_context_dict = None
    project_context_summary = None

    project_id = state.get("project_id")
    if project_id is not None:
        try:
            logger.info(f"Loading project context for project_id={project_id}")
            loader = get_context_loader()
            context = await loader.load_context(
                project_id=project_id,
                user_uid=state.get("user_uid", "unknown")
            )

            # Convert to dict and generate summary
            project_context_dict = context.model_dump()
            project_context_summary = loader.get_summary(context)

            # Log stats
            stats = context.backlog_stats
            doc_stats = context.document_stats
            logger.info(
                f"Project context loaded: {stats.total_items} backlog items, "
                f"{doc_stats.total_documents} documents ({doc_stats.analyzed_documents} analyzed)"
            )

        except Exception as e:
            # Non-blocking: log warning and continue without context
            logger.warning(f"Failed to load project context for project_id={project_id}: {e}")
            project_context_dict = None
            project_context_summary = None

    return {
        "next_agent": next_agent,
        "current_step_index": current_step_index,
        "workflow_steps": workflow_steps,
        "workflow_context": workflow_context,
        "project_context": project_context_dict,
        "project_context_summary": project_context_summary,
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
    
    # Check if workflow is complete - if so, add conversation step for suggestions (only once!)
    if next_index >= len(workflow_steps):
        # Check if we haven't already added a conversation step
        has_conversation_step = any(
            step.get("agent") == "conversation" and step.get("objective") == "suggest next steps"
            for step in workflow_steps
        )
        
        if not has_conversation_step:
            logger.info("Workflow complete - adding conversation step for next suggestions")
            
            # Add final conversation step to suggest next actions
            conversation_step = {
                "agent": "conversation",
                "objective": "suggest next steps",
                "status": "pending",
                "result": None,
                "requires_approval": False
            }
            workflow_steps.append(conversation_step)
            
            return {
                "current_step_index": next_index,
                "workflow_steps": workflow_steps,
                "next_agent": "workflow_executor",
                "current_agent": "advance_workflow"
            }
        else:
            logger.info("Conversation step already exists, skipping")
    
    return {
        "current_step_index": next_index,
        "workflow_steps": workflow_steps,
        "next_agent": "workflow_executor",  # Route back to executor
        "current_agent": "advance_workflow"
    }