from typing import TypedDict, Annotated, Sequence, Literal, Any
from langchain_core.messages import BaseMessage
from operator import add

AgentType = Literal["router", "backlog", "document", "planner", "writer", "integration", "conversation", "end"]
ItemType = Literal["Epic", "Feature", "US", "UC", "Capability"]
ActionType = Literal["generate_children", "create_item", "update_item", "analyze"]

class AgentRunMetadata(TypedDict, total=False):
    """Structured metadata for agent runs."""
    action: ActionType
    target_type: ItemType
    parent_id: int
    parent_type: ItemType

class WorkflowStep(TypedDict):
    """Single step in a multi-step workflow."""
    agent: AgentType
    objective: str
    status: Literal["pending", "running", "done", "error", "awaiting_approval"]
    result: dict | None
    requires_approval: bool

class AgentState(TypedDict):
    """État partagé entre tous les agents LangGraph."""
    
    # Messages conversation
    messages: Annotated[Sequence[BaseMessage], add]
    
    # Context utilisateur
    project_id: int | None
    user_uid: str
    objective: str
    meta: AgentRunMetadata | None  # Structured metadata from frontend
    
    # Routing
    next_agent: str  # Pour routing
    current_agent: str | None  # Currently active agent
    
    # Execution control
    iteration: int
    max_iterations: int
    
    # Results accumulation
    tool_results: dict[str, Any]  # Résultats outils accumulés
    items_created: list[int] | None  # For BacklogAgent tracking
    documents_searched: list[str] | None  # For DocumentAgent tracking
    
    # Error handling
    error: str | None
    
    # UI streaming
    run_id: str | None  # For streaming identification
    status_message: str | None  # General status updates
    progress_steps: list[dict] | None  # For PlannerAgent steps tracking
    synthesis_complete: bool | None  # WriterAgent completion flag
    final_response: str | None  # WriterAgent final output
    is_stub: bool | None  # For IntegrationAgent stub indication
    
    # Phase 2C - Workflow orchestration
    workflow_steps: list[WorkflowStep] | None  # NOUVEAU: Plan d'exécution multi-étapes
    current_step_index: int | None             # NOUVEAU: Étape actuelle
    is_paused: bool | None                     # NOUVEAU: Workflow en pause (HITL)
    pending_approval: dict | None              # NOUVEAU: Action en attente d'approbation
    workflow_context: dict | None              # NOUVEAU: Contexte workflow step (step_index, total_steps, description)

    # Phase 2D - Project Context (ProjectContextLoader V1)
    project_context: dict | None               # NOUVEAU: Contexte projet structuré (backlog + docs)
    project_context_summary: str | None        # NOUVEAU: Résumé markdown pour injection prompts