"""Writer agent - Formats responses and synthesizes information."""
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from .state import AgentState
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
            return data.get('system', '')
    except Exception as e:
        logger.error(f"Failed to load prompt {filename}: {e}")
        return "Tu es un rédacteur expert qui synthétise et formate les résultats."

async def writer_agent_node(state: AgentState) -> AgentState:
    """Specialized agent for response formatting and synthesis."""
    logger.info(f"WriterAgent synthesizing results for: {state['objective']}")
    
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0.3)  # Slightly creative for writing
        
        prompt_template = load_prompt("writer.yaml")
        
        # Gather context from state for synthesis
        tool_results = state.get("tool_results", {})
        documents_searched = state.get("documents_searched", [])
        progress_steps = state.get("progress_steps", [])
        current_agent = state.get("current_agent", "unknown")
        status_message = state.get("status_message", "")
        
        # Extract items created from tool results
        items_created = []
        for tool_name, result in tool_results.items():
            if isinstance(result, dict):
                if "features_created" in result:
                    items_created.extend(result["features_created"])
                elif "item_id" in result:
                    items_created.append(result["item_id"])
                elif "created_ids" in result:
                    items_created.extend(result["created_ids"])
        
        # Build rich context for the writer
        context = f"""
Objectif initial: {state['objective']}
Agent précédent: {current_agent}
Status: {status_message}

Items backlog créés: {len(items_created)} items (IDs: {items_created})
Documents consultés: {len(documents_searched)} docs ({', '.join(documents_searched[:3])})
Outils utilisés: {len(tool_results)} outils ({', '.join(tool_results.keys())})
Plan étapes: {len(progress_steps)} étapes définies

Résultats détaillés outils:
{str(tool_results)[:500]}...
"""
        
        prompt = prompt_template.format(
            project_id=state["project_id"],
            objective=state["objective"],
            context=context
        )
        
        messages = [
            SystemMessage(content=prompt),
            *state["messages"],
            HumanMessage(content="Synthétise les résultats de manière claire et structurée.")
        ]
        
        response = await llm.ainvoke(messages)
        logger.info(f"WriterAgent generated synthesis: {len(response.content)} characters")
        
        # Create comprehensive final status
        final_steps = progress_steps + [
            {"description": "Response synthesis completed", "status": "completed"}
        ]
        
        return {
            **state,
            "messages": state["messages"] + [response],
            "current_agent": "writer",
            "next_agent": "end",
            "iteration": state["iteration"] + 1,
            "status_message": "✅ Response formatted and synthesized",
            "progress_steps": final_steps,
            "synthesis_complete": True,
            "final_response": response.content
        }
        
    except Exception as e:
        logger.error(f"WriterAgent failed: {e}")
        return {
            **state,
            "iteration": state["iteration"] + 1,
            "error": f"WriterAgent error: {str(e)}",
            "current_agent": "writer",
            "next_agent": "end"
        }