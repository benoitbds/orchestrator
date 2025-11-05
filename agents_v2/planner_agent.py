"""Planner agent - Decomposes complex objectives into sequential workflow."""
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from .state import AgentState, WorkflowStep
from .streaming import get_stream_manager
import yaml
import os
import re
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
        return "Tu es un planificateur expert qui décompose des objectifs complexes."

def parse_workflow_plan(plan_text: str) -> list[WorkflowStep]:
    """Parse LLM response into structured workflow steps.
    
    Expected format:
    Step 1: [Description] → Agent: [agent_name] [APPROVAL_REQUIRED]
    Step 2: [Description] → Agent: [agent_name]
    """
    steps: list[WorkflowStep] = []
    
    for line in plan_text.split('\n'):
        if not line.strip().startswith('Step '):
            continue
        
        # Extract agent name
        agent_match = re.search(r'Agent:\s*(\w+)', line, re.IGNORECASE)
        if not agent_match:
            continue
        
        agent_name = agent_match.group(1).lower()
        
        # Validate agent name
        valid_agents = ["backlog", "document", "planner", "writer", "integration", "conversation"]
        if agent_name not in valid_agents:
            agent_name = "backlog"  # Default fallback
        
        # Extract objective (text before →)
        objective_match = re.search(r'Step \d+:\s*(.+?)\s*→', line)
        objective = objective_match.group(1).strip() if objective_match else line.strip()
        
        # Check if approval required
        requires_approval = 'APPROVAL' in line.upper() or 'VALIDATE' in line.upper() or 'VALIDATION' in line.upper()
        
        steps.append(WorkflowStep(
            agent=agent_name,
            objective=objective,
            status="pending",
            result=None,
            requires_approval=requires_approval
        ))
    
    return steps

async def planner_agent_node(state: AgentState) -> dict:
    """Specialized agent for planning and task decomposition.
    
    Creates a sequential workflow plan that will be executed step-by-step.
    """
    
    run_id = state.get("run_id", "unknown")
    stream = get_stream_manager(run_id)
    
    # Define todos for planner execution
    todos = [
        "Analyser l'objectif utilisateur",
        "Identifier les agents nécessaires",
        "Créer le workflow en étapes"
    ]
    
    workflow_context = state.get("workflow_context")
    await stream.emit_agent_start(
        "planner", 
        state["objective"], 
        state["iteration"],
        step_info=workflow_context,
        todos=todos
    )
    
    # Emit initial narration
    await stream.emit_agent_narration(
        "planner",
        "Je crée un plan d'exécution structuré",
        state["iteration"]
    )
    
    try:
        # Todo 1: Analyze objective
        await stream.emit_todo_update(
            "planner",
            "planner-todo-0",
            todos[0],
            "in_progress",
            state["iteration"]
        )
        
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        
        prompt_template = load_prompt("planner.yaml")
        prompt = prompt_template.format(
            project_id=state["project_id"],
            objective=state["objective"],
            iteration=state["iteration"]
        )
        
        await stream.emit_agent_thinking("planner", prompt, state["iteration"])
        
        messages = [
            SystemMessage(content=prompt),
            *state["messages"],
            HumanMessage(content=state["objective"])
        ]
        
        response = await llm.ainvoke(messages)
        plan_text = response.content
        
        # Todo 1: Complete
        await stream.emit_todo_update(
            "planner",
            "planner-todo-0",
            todos[0],
            "completed",
            state["iteration"]
        )
        
        # Todo 2: Identify agents
        await stream.emit_todo_update(
            "planner",
            "planner-todo-1",
            todos[1],
            "in_progress",
            state["iteration"]
        )
        
        # Parse structured workflow
        workflow_steps = parse_workflow_plan(plan_text)
        
        logger.info(f"PlannerAgent created {len(workflow_steps)} workflow steps")
        
        # Todo 2: Complete
        await stream.emit_todo_update(
            "planner",
            "planner-todo-1",
            todos[1],
            "completed",
            state["iteration"]
        )
        
        # Todo 3: Create workflow
        await stream.emit_todo_update(
            "planner",
            "planner-todo-2",
            todos[2].replace("X", str(len(workflow_steps))),
            "in_progress",
            state["iteration"]
        )
        
        # Small delay for visual effect
        import asyncio
        await asyncio.sleep(0.5)
        
        # Todo 3: Complete
        await stream.emit_todo_update(
            "planner",
            "planner-todo-2",
            todos[2].replace("X", str(len(workflow_steps))),
            "completed",
            state["iteration"]
        )
        
        # Emit final narration
        await stream.emit_agent_narration(
            "planner",
            f"Plan créé avec {len(workflow_steps)} étapes",
            state["iteration"]
        )
        
        await stream.emit_agent_end(
            "planner",
            f"Created workflow plan with {len(workflow_steps)} steps",
            state["iteration"],
            success=True,
            extra_data={"workflow_steps": workflow_steps}
        )
        
        # Set next agent to workflow executor
        next_agent = "workflow_executor" if workflow_steps else "end"
        
        return {
            **state,  # Preserve existing state
            "messages": state["messages"] + [response],
            "current_agent": "planner",
            "next_agent": next_agent,
            "iteration": state["iteration"] + 1,
            "workflow_steps": workflow_steps,
            "current_step_index": 0,
            "status_message": f"📋 Workflow plan created: {len(workflow_steps)} steps",
            "progress_steps": [
                {
                    "step": f"{step['agent']}: {step['objective']}",
                    "status": "pending",
                    "requires_approval": step['requires_approval']
                }
                for step in workflow_steps
            ]
        }
        
    except Exception as e:
        logger.error(f"PlannerAgent failed: {e}")
        
        await stream.emit_agent_end(
            "planner",
            f"PlannerAgent error: {str(e)}",
            state["iteration"],
            success=False
        )
        
        return {
            **state,  # Preserve existing state
            "iteration": state["iteration"] + 1,
            "error": f"PlannerAgent error: {str(e)}",
            "current_agent": "planner",
            "next_agent": "end"
        }