from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from .state import AgentState
from .streaming import get_stream_manager
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
    
    run_id = state.get("run_id", "default")
    stream_manager = get_stream_manager(run_id)
    
    try:
        workflow_context = state.get("workflow_context")
        await stream_manager.emit_agent_start(
            "document", 
            state["objective"], 
            state["iteration"],
            step_info=workflow_context
        )
        
        await stream_manager.emit_agent_narration(
            "document",
            "Je vais analyser les documents pour identifier les exigences",
            state["iteration"]
        )
        
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
        
        await stream_manager.emit_agent_thinking("document", prompt, state["iteration"])
        
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
        todo_index = 0
        
        if hasattr(response, 'tool_calls') and response.tool_calls:
            logger.info(f"DocumentAgent executing {len(response.tool_calls)} tool calls")
            
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                
                # Update todo based on tool being executed
                if tool_name == "list_documents" and todo_index == 0:
                    await stream_manager.emit_todo_update(
                        "document",
                        "document-todo-0",
                        todos[0],
                        "in_progress",
                        state["iteration"]
                    )
                elif tool_name == "search_documents" and todo_index <= 1:
                    await stream_manager.emit_todo_update(
                        "document",
                        "document-todo-1",
                        todos[1],
                        "in_progress",
                        state["iteration"]
                    )
                elif tool_name == "draft_features_from_documents" and todo_index <= 2:
                    await stream_manager.emit_todo_update(
                        "document",
                        "document-todo-2",
                        todos[2],
                        "in_progress",
                        state["iteration"]
                    )
                
                try:
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
                    
                    await stream_manager.emit_tool_call(
                        "document", tool_name, tool_args, state["iteration"], 
                        result=result
                    )
                    
                    # Mark todo as completed after successful tool execution
                    if tool_name == "list_documents" and todo_index == 0:
                        await stream_manager.emit_todo_update(
                            "document",
                            "document-todo-0",
                            todos[0],
                            "completed",
                            state["iteration"]
                        )
                        todo_index = 1
                    elif tool_name == "search_documents" and todo_index <= 1:
                        await stream_manager.emit_todo_update(
                            "document",
                            "document-todo-1",
                            todos[1],
                            "completed",
                            state["iteration"]
                        )
                        todo_index = 2
                    elif tool_name == "draft_features_from_documents" and todo_index <= 2:
                        await stream_manager.emit_todo_update(
                            "document",
                            "document-todo-2",
                            todos[2],
                            "completed",
                            state["iteration"]
                        )
                        todo_index = 3
                    
                except Exception as tool_error:
                    error_msg = str(tool_error)
                    logger.error(f"Tool {tool_name} failed: {error_msg}")
                    result = {"error": error_msg}
                    tool_results[tool_name] = result
                    
                    await stream_manager.emit_tool_call(
                        "document", tool_name, tool_args, state["iteration"],
                        error=error_msg
                    )
                
                # Add tool message to new_messages (will be added to state)
                tool_msg = ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call.get("id", "unknown")
                )
                new_messages.append(tool_msg)
                
                # Also add to local messages for potential follow-up calls
                messages.append(tool_msg)
        
        features_count = 0
        for tool_name, result in tool_results.items():
            if isinstance(result, dict) and tool_name == "draft_features_from_documents":
                features_count = len(result.get("features_created", []))
        
        if features_count > 0:
            narration = f"Analyse terminée: {features_count} features identifiées à partir de {len(documents_searched)} documents"
        elif len(documents_searched) > 0:
            narration = f"Analyse terminée: {len(documents_searched)} documents analysés"
        else:
            narration = f"Analyse terminée: {len(tool_results)} opérations documentaires effectuées"
        
        await stream_manager.emit_agent_narration(
            "document",
            narration,
            state["iteration"]
        )
        
        await stream_manager.emit_agent_end(
            "document",
            f"Processed {len(tool_results)} document operations. Found {len(documents_searched)} documents.",
            state["iteration"],
            success=True
        )
        
        return {
            **state,
            "messages": state["messages"] + new_messages,
            "iteration": state["iteration"] + 1,
            "tool_results": {**state["tool_results"], **tool_results},
            "documents_searched": list(set(documents_searched)),
            "current_agent": "document"
        }
        
    except Exception as e:
        logger.error(f"DocumentAgent failed: {e}")
        
        await stream_manager.emit_agent_end(
            "document",
            f"DocumentAgent error: {str(e)}",
            state["iteration"],
            success=False
        )
        
        return {
            **state,
            "iteration": state["iteration"] + 1,
            "error": f"DocumentAgent error: {str(e)}",
            "current_agent": "document"
        }