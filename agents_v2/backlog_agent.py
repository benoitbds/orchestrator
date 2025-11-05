from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from .state import AgentState
from .streaming import get_stream_manager
from .tools.backlog_tools import (
    create_backlog_item_tool,
    update_backlog_item_tool,
    get_backlog_item_tool,
    list_backlog_items,
    delete_backlog_item,
    move_backlog_item,
    summarize_project_backlog,
    bulk_create_features,
    generate_children_items,
    set_current_run_id
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
            return data.get('prompt', '')
    except Exception as e:
        logger.error(f"Failed to load prompt {filename}: {e}")
        return "Tu es un expert backlog SAFe/Agile."

BACKLOG_PROMPT_TEMPLATE = load_prompt("backlog_prompt.yaml")

async def backlog_agent_node(state: AgentState) -> AgentState:
    """Agent spécialisé dans la gestion du backlog."""
    logger.info(f"BacklogAgent processing: {state['objective']}")
    
    # Get streaming manager for this run
    run_id = state.get("run_id", "default")
    stream_manager = get_stream_manager(run_id)
    
    # Extract metadata if present
    meta = state.get("meta")
    if meta:
        logger.info(f"BacklogAgent received metadata: {meta}")
    
    try:
        # Validate parent-child compatibility if metadata specifies generation
        if meta and meta.get("action") == "generate_children":
            target_type = meta.get("target_type")
            parent_type = meta.get("parent_type")
            
            # Validate type compatibility
            if target_type == "UC" and parent_type != "US":
                error_msg = f"Use Cases (UC) must be created under a User Story (US), not {parent_type}. Please select a US first."
                logger.error(error_msg)
                await stream_manager.emit_agent_end("backlog", error_msg, state["iteration"], success=False)
                return {
                    **state,
                    "iteration": state["iteration"] + 1,
                    "current_agent": "backlog",
                    "error": error_msg
                }
            
            if target_type == "US" and parent_type not in ["Feature", "Capability"]:
                error_msg = f"User Stories (US) must be created under a Feature or Capability, not {parent_type}. Please select a Feature first."
                logger.error(error_msg)
                await stream_manager.emit_agent_end("backlog", error_msg, state["iteration"], success=False)
                return {
                    **state,
                    "iteration": state["iteration"] + 1,
                    "current_agent": "backlog",
                    "error": error_msg
                }
            
            if target_type == "Feature" and parent_type not in ["Epic", "Capability"]:
                error_msg = f"Features must be created under an Epic or Capability, not {parent_type}."
                logger.error(error_msg)
                await stream_manager.emit_agent_end("backlog", error_msg, state["iteration"], success=False)
                return {
                    **state,
                    "iteration": state["iteration"] + 1,
                    "current_agent": "backlog",
                    "error": error_msg
                }
        
        # Set run_id for real-time item creation events
        set_current_run_id(run_id)
        
        # Emit agent start event with workflow context if available
        workflow_context = state.get("workflow_context")
        await stream_manager.emit_agent_start(
            "backlog", 
            state["objective"], 
            state["iteration"],
            step_info=workflow_context
        )
        
        # Emit initial narration based on action type
        if meta and meta.get("action") == "generate_children":
            target_type = meta.get("target_type", "US")
            type_labels = {
                "US": "User Stories",
                "UC": "Use Cases",
                "Feature": "Features",
                "Epic": "Epics"
            }
            item_label = type_labels.get(target_type, target_type)
            await stream_manager.emit_agent_narration(
                "backlog",
                f"Je vais créer les {item_label} dans le backlog",
                state["iteration"]
            )
        else:
            await stream_manager.emit_agent_narration(
                "backlog",
                "Je vais gérer les éléments du backlog",
                state["iteration"]
            )
        
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        tools = [
            create_backlog_item_tool,
            update_backlog_item_tool,
            get_backlog_item_tool,
            list_backlog_items,
            delete_backlog_item,
            move_backlog_item,
            summarize_project_backlog,
            bulk_create_features,
            generate_children_items
        ]
        llm_with_tools = llm.bind_tools(tools)
        
        # Enrich prompt with metadata if available
        prompt_vars = {
            "project_id": state["project_id"],
            "objective": state["objective"]
        }
        
        if meta:
            if meta.get("action") == "generate_children":
                prompt_vars["action"] = "generate_children"
                prompt_vars["target_type"] = meta.get("target_type", "US")
                prompt_vars["parent_id"] = meta.get("parent_id")
                prompt_vars["parent_type"] = meta.get("parent_type", "Feature")
            else:
                prompt_vars["action"] = meta.get("action", "")
        
        prompt = BACKLOG_PROMPT_TEMPLATE.format(**prompt_vars)
        
        # Emit thinking event
        await stream_manager.emit_agent_thinking("backlog", prompt, state["iteration"])
        
        messages = [
            SystemMessage(content=prompt),
            *state["messages"],
            HumanMessage(content=state["objective"])
        ]
        
        response = await llm_with_tools.ainvoke(messages)
        logger.info(f"BacklogAgent response: {response.content}")
        
        # Collect new messages to add to state
        new_messages = [response]
        
        # Handle tool calls if present
        tool_results = {}
        if hasattr(response, 'tool_calls') and response.tool_calls:
            logger.info(f"BacklogAgent executing {len(response.tool_calls)} tool calls")
            
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                
                try:
                    # Execute the tool
                    if tool_name == "create_backlog_item_tool":
                        result = await create_backlog_item_tool.ainvoke(tool_args)
                    elif tool_name == "update_backlog_item_tool":
                        result = await update_backlog_item_tool.ainvoke(tool_args)
                    elif tool_name == "get_backlog_item_tool":
                        result = await get_backlog_item_tool.ainvoke(tool_args)
                    elif tool_name == "list_backlog_items":
                        result = await list_backlog_items.ainvoke(tool_args)
                    elif tool_name == "delete_backlog_item":
                        result = await delete_backlog_item.ainvoke(tool_args)
                    elif tool_name == "move_backlog_item":
                        result = await move_backlog_item.ainvoke(tool_args)
                    elif tool_name == "summarize_project_backlog":
                        result = await summarize_project_backlog.ainvoke(tool_args)
                    elif tool_name == "bulk_create_features":
                        result = await bulk_create_features.ainvoke(tool_args)
                    elif tool_name == "generate_children_items":
                        result = await generate_children_items.ainvoke(tool_args)
                    else:
                        result = {"error": f"Unknown tool: {tool_name}"}
                    
                    tool_results[tool_name] = result
                    logger.info(f"Tool {tool_name} result: {result}")
                    
                    # Check for validation failures
                    if isinstance(result, dict):
                        if result.get("validation_failed"):
                            error_msg = result.get("error", "Validation failed")
                            logger.error(f"Tool {tool_name} validation failed: {error_msg}")
                            await stream_manager.emit_tool_call(
                                "backlog", tool_name, tool_args, state["iteration"],
                                error=error_msg
                            )
                            await stream_manager.emit_agent_end(
                                "backlog",
                                error_msg,
                                state["iteration"],
                                success=False
                            )
                            return {
                                **state,
                                "iteration": state["iteration"] + 1,
                                "current_agent": "backlog",
                                "error": error_msg
                            }
                        
                        if result.get("error") and not result.get("success", True):
                            error_msg = result.get("error", "Tool execution failed")
                            logger.error(f"Tool {tool_name} failed: {error_msg}")
                            await stream_manager.emit_tool_call(
                                "backlog", tool_name, tool_args, state["iteration"],
                                error=error_msg
                            )
                            await stream_manager.emit_agent_end(
                                "backlog",
                                error_msg,
                                state["iteration"],
                                success=False
                            )
                            return {
                                **state,
                                "iteration": state["iteration"] + 1,
                                "current_agent": "backlog",
                                "error": error_msg
                            }
                    
                    await stream_manager.emit_tool_call(
                        "backlog", tool_name, tool_args, state["iteration"], 
                        result=result
                    )
                    
                    # Add tool message to new_messages (will be added to state)
                    tool_msg = ToolMessage(
                        content=str(result),
                        tool_call_id=tool_call.get("id", "unknown")
                    )
                    new_messages.append(tool_msg)
                    
                    # Also add to local messages for potential follow-up calls
                    messages.append(tool_msg)
                    
                except Exception as tool_error:
                    error_msg = f"Tool {tool_name} failed: {str(tool_error)}"
                    logger.error(error_msg)
                    
                    # Emit tool call end with error
                    await stream_manager.emit_tool_call(
                        "backlog", tool_name, tool_args, state["iteration"], 
                        error=error_msg
                    )
                    
                    # Add error as tool message
                    tool_msg = ToolMessage(
                        content=error_msg,
                        tool_call_id=tool_call.get("id", "unknown")
                    )
                    new_messages.append(tool_msg)
                    messages.append(tool_msg)
        
        # Emit agent completion with items_created count
        tool_count = len(tool_results)
        items_created = 0
        parent_title = None
        item_type = None
        
        # Count items created from tool results
        for tool_name, result in tool_results.items():
            if isinstance(result, dict):
                if tool_name == "generate_children_items":
                    items_created += len(result.get("children_created", []))
                    parent_title = result.get("parent_title")
                    item_type = result.get("target_type", "items")
                elif tool_name == "bulk_create_features":
                    items_created += result.get("count", 0)
                    item_type = "Features"
                elif tool_name == "create_backlog_item_tool" and result.get("success"):
                    items_created += 1
                    item_type = result.get("type", "item")
        
        # Emit final narration with summary
        if items_created > 0:
            type_labels = {
                "US": "User Stories",
                "UC": "Use Cases",
                "Feature": "Features",
                "Epic": "Epics"
            }
            item_label = type_labels.get(item_type, item_type or "items")
            
            if parent_title:
                narration = f"{items_created} {item_label} créées sous '{parent_title}'"
            else:
                narration = f"{items_created} {item_label} créées dans le backlog"
            
            await stream_manager.emit_agent_narration(
                "backlog",
                narration,
                state["iteration"]
            )
        
        await stream_manager.emit_agent_end(
            "backlog", 
            f"Completed backlog operations with {tool_count} tools", 
            state["iteration"], 
            success=True,
            extra_data={"items_created": items_created}
        )
        
        return {
            **state,
            "messages": state["messages"] + new_messages,
            "iteration": state["iteration"] + 1,
            "current_agent": "backlog",
            "tool_results": {**state["tool_results"], **tool_results}
        }
        
    except Exception as e:
        logger.error(f"BacklogAgent failed: {e}")
        
        # Emit error
        await stream_manager.emit_agent_end(
            "backlog", 
            f"BacklogAgent error: {str(e)}", 
            state["iteration"], 
            success=False
        )
        
        return {
            **state,
            "iteration": state["iteration"] + 1,
            "current_agent": "backlog",
            "error": f"BacklogAgent error: {str(e)}"
        }