from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from .state import AgentState
from .tools.document_tools import (
    search_documents,
    list_documents,
    get_document_content,
    draft_features_from_documents,
    analyze_document_structure
)
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
        return "Tu es un expert en recherche documentaire et extraction d'informations (RAG)."

async def document_agent_node(state: AgentState) -> AgentState:
    """Agent spécialisé dans la recherche documentaire et extraction d'informations."""
    logger.info(f"DocumentAgent processing: {state['objective']}")
    
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        tools = [
            search_documents,
            list_documents,
            get_document_content,
            draft_features_from_documents,
            analyze_document_structure
        ]
        llm_with_tools = llm.bind_tools(tools)
        
        prompt_template = load_prompt("document.yaml")
        prompt = prompt_template.format(
            project_id=state["project_id"],
            objective=state["objective"]
        )
        
        messages = [
            SystemMessage(content=prompt),
            *state["messages"],
            HumanMessage(content=state["objective"])
        ]
        
        response = await llm_with_tools.ainvoke(messages)
        logger.info(f"DocumentAgent response: {response.content}")
        
        # Collect new messages to add to state
        new_messages = [response]
        
        # Handle tool calls if present
        tool_results = {}
        documents_searched = []
        
        if hasattr(response, 'tool_calls') and response.tool_calls:
            logger.info(f"DocumentAgent executing {len(response.tool_calls)} tool calls")
            
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                
                # Execute the appropriate tool
                if tool_name == "search_documents":
                    result = await search_documents.ainvoke(tool_args)
                    documents_searched.extend([r.get("filename", "unknown") for r in result.get("results", [])])
                elif tool_name == "list_documents":
                    result = await list_documents.ainvoke(tool_args)
                elif tool_name == "get_document_content":
                    result = await get_document_content.ainvoke(tool_args)
                    if result.get("filename"):
                        documents_searched.append(result["filename"])
                elif tool_name == "draft_features_from_documents":
                    result = await draft_features_from_documents.ainvoke(tool_args)
                elif tool_name == "analyze_document_structure":
                    result = await analyze_document_structure.ainvoke(tool_args)
                    if result.get("filename"):
                        documents_searched.append(result["filename"])
                else:
                    result = {"error": f"Unknown tool: {tool_name}"}
                
                tool_results[tool_name] = result
                logger.info(f"Tool {tool_name} result: {result}")
                
                # Add tool message to new_messages (will be added to state)
                tool_msg = ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call.get("id", "unknown")
                )
                new_messages.append(tool_msg)
                
                # Also add to local messages for potential follow-up calls
                messages.append(tool_msg)
        
        return {
            **state,
            "messages": state["messages"] + new_messages,
            "iteration": state["iteration"] + 1,
            "tool_results": {**state["tool_results"], **tool_results},
            "documents_searched": list(set(documents_searched)),  # Unique documents
            "current_agent": "document"
        }
        
    except Exception as e:
        logger.error(f"DocumentAgent failed: {e}")
        return {
            **state,
            "iteration": state["iteration"] + 1,
            "error": f"DocumentAgent error: {str(e)}",
            "current_agent": "document"
        }