from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from .state import AgentState
from .streaming import get_stream_manager
import yaml
import os
import logging

logger = logging.getLogger(__name__)

def load_prompt(filename: str) -> str:
    """Load prompt from YAML file."""
    try:
        prompt_path = os.path.join(os.path.dirname(__file__), "prompts", filename)
        with open(prompt_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            return data.get('prompt', '')
    except Exception as e:
        logger.error(f"Failed to load prompt {filename}: {e}")
        return "Tu es un routeur intelligent. Route vers 'backlog'."

ROUTER_PROMPT_TEMPLATE = load_prompt("router_prompt.yaml")

async def router_node(state: AgentState) -> AgentState:
    """Route vers l'agent approprié selon l'intention."""
    print(f"=== ROUTER_NODE CALLED ===")
    logger.info(f"Router analyzing objective: {state['objective']}")
    
    # Get streaming manager for this run
    run_id = state.get("run_id", "default")
    print(f"[ROUTER] Run ID: {run_id}")
    stream_manager = get_stream_manager(run_id)
    
    try:
        # Emit agent start event
        print(f"[ROUTER] Emitting agent_start event...")
        await stream_manager.emit_agent_start("router", state["objective"], state["iteration"])
        
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        prompt = ROUTER_PROMPT_TEMPLATE.format(
            objective=state["objective"],
            project_id=state["project_id"]
        )
        
        # Emit thinking event
        await stream_manager.emit_agent_thinking("router", prompt, state["iteration"])
        
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=state["objective"])
        ]
        
        response = await llm.ainvoke(messages)
        next_agent = response.content.strip().lower()
        
        # Validation routing (Phase 2A - tous agents disponibles)
        valid_agents = ["backlog", "document", "planner", "writer", "integration"]
        if next_agent not in valid_agents:
            logger.warning(f"Invalid routing decision: {next_agent}, defaulting to 'backlog'")
            next_agent = "backlog"
        
        logger.info(f"Router decision: {next_agent}")
        
        # Emit completion event
        await stream_manager.emit_agent_end(
            "router", 
            f"Routing to {next_agent}Agent based on objective analysis", 
            state["iteration"], 
            success=True
        )
        
        return {
            **state, 
            "next_agent": next_agent,
            "current_agent": "router",
            "messages": state["messages"] + [response]
        }
        
    except Exception as e:
        logger.error(f"Router failed: {e}")
        
        # Emit error
        await stream_manager.emit_agent_end(
            "router", 
            f"Router error: {str(e)}", 
            state["iteration"], 
            success=False
        )
        
        # Fallback to backlog agent
        return {
            **state, 
            "next_agent": "backlog",
            "current_agent": "router",
            "error": f"Router error: {str(e)}"
        }