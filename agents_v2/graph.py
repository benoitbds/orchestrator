"""LangGraph StateGraph construction with sequential workflow orchestration."""
from langgraph.graph import StateGraph, END
from .state import AgentState
from .router import router_node
from .backlog_agent import backlog_agent_node
from .document_agent import document_agent_node
from .planner_agent import planner_agent_node
from .writer_agent import writer_agent_node
from .integration_agent import integration_agent_node
from .conversation_agent import conversation_agent_node
from .workflow_executor import workflow_executor_node, advance_workflow_node
from .approval import approval_node
import logging

logger = logging.getLogger(__name__)

def build_agent_graph(checkpointer=None):
    """Construct the multi-agent StateGraph with sequential workflow support.
    
    Args:
        checkpointer: Redis checkpointer pour persistence (optionnel pour tests)
        
    Returns:
        Compiled StateGraph ready for execution
    """
    logger.info("Building LangGraph agent graph with workflow orchestration")
    
    workflow = StateGraph(AgentState)
    
    # Add all agent nodes
    workflow.add_node("router", router_node)
    workflow.add_node("backlog", backlog_agent_node)
    workflow.add_node("document", document_agent_node)
    workflow.add_node("planner", planner_agent_node)
    workflow.add_node("writer", writer_agent_node)
    workflow.add_node("integration", integration_agent_node)
    workflow.add_node("conversation", conversation_agent_node)
    
    # Phase 2C: Workflow orchestration nodes
    workflow.add_node("workflow_executor", workflow_executor_node)
    workflow.add_node("advance_workflow", advance_workflow_node)
    workflow.add_node("approval", approval_node)
    
    # Set entry point
    workflow.set_entry_point("router")
    
    # Router routes to planner
    workflow.add_edge("router", "planner")
    
    # Planner creates workflow → goes to executor
    workflow.add_edge("planner", "workflow_executor")
    
    # Workflow executor uses conditional routing based on next_agent
    def route_from_executor(state: AgentState) -> str:
        next_agent = state.get("next_agent", "")
        if next_agent == "end":
            return END
        return next_agent
    
    workflow.add_conditional_edges(
        "workflow_executor",
        route_from_executor,
        {
            "backlog": "backlog",
            "document": "document", 
            "writer": "writer",
            "integration": "integration",
            "conversation": "conversation",
            "approval": "approval",
            END: END
        }
    )
    
    # Agents complete → advance workflow
    workflow.add_edge("backlog", "advance_workflow")
    workflow.add_edge("document", "advance_workflow")
    workflow.add_edge("writer", "advance_workflow")
    workflow.add_edge("conversation", "advance_workflow")
    
    # Integration ends directly
    workflow.add_edge("integration", END)
    
    # Advance workflow → back to executor
    workflow.add_edge("advance_workflow", "workflow_executor")
    
    # Approval → back to executor
    workflow.add_edge("approval", "workflow_executor")
    
    # Compile with optional checkpointer
    if checkpointer:
        graph = workflow.compile(checkpointer=checkpointer)
        logger.info("Graph compiled with Redis checkpointer")
    else:
        graph = workflow.compile()
        logger.info("Graph compiled without checkpointer")
    
    return graph