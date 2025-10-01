"""Real-time streaming infrastructure for multi-agent UI."""
from typing import Literal, TypedDict, Any
from enum import Enum
import json
import asyncio
from datetime import datetime

class EventType(str, Enum):
    """Types d'événements streamés vers l'UI."""
    AGENT_START = "agent_start"           # Agent commence son travail
    AGENT_THINKING = "agent_thinking"     # Agent réfléchit (LLM call)
    TOOL_CALL_START = "tool_call_start"   # Début appel outil
    TOOL_CALL_END = "tool_call_end"       # Fin appel outil (+ résultat)
    AGENT_END = "agent_end"               # Agent termine
    TOKEN_STREAM = "token_stream"         # Token LLM individuel (streaming)
    STATUS_UPDATE = "status_update"       # Mise à jour statut général
    ERROR = "error"                       # Erreur
    COMPLETE = "complete"                 # Workflow terminé

class StreamEvent(TypedDict):
    """Structure d'un événement streamé."""
    type: EventType
    agent: str                    # Nom de l'agent (router, backlog, etc.)
    timestamp: str                # ISO format
    data: dict[str, Any]          # Payload spécifique à l'événement
    run_id: str                   # ID du run
    iteration: int                # Numéro d'itération

class AgentStreamManager:
    """Manages real-time event streaming for agent execution."""
    
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.events: list[StreamEvent] = []
        self.subscribers: list[asyncio.Queue] = []
    
    async def emit(
        self,
        event_type: EventType,
        agent: str,
        data: dict[str, Any],
        iteration: int = 0
    ):
        """Emit event to all subscribers."""
        event: StreamEvent = {
            "type": event_type,
            "agent": agent,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
            "run_id": self.run_id,
            "iteration": iteration
        }
        
        self.events.append(event)
        
        # Broadcast to subscribers
        for queue in self.subscribers:
            try:
                await queue.put(event)
            except Exception as e:
                print(f"Error broadcasting event: {e}")
    
    def subscribe(self) -> asyncio.Queue:
        """Subscribe to event stream."""
        queue: asyncio.Queue = asyncio.Queue()
        self.subscribers.append(queue)
        return queue
    
    def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe from event stream."""
        if queue in self.subscribers:
            self.subscribers.remove(queue)
    
    async def emit_agent_start(self, agent: str, objective: str, iteration: int):
        """Emit agent start event."""
        await self.emit(
            EventType.AGENT_START,
            agent,
            {"message": f"Starting {agent}Agent", "objective": objective},
            iteration
        )
    
    async def emit_agent_thinking(self, agent: str, prompt_preview: str, iteration: int):
        """Emit agent thinking event (LLM call)."""
        await self.emit(
            EventType.AGENT_THINKING,
            agent,
            {"message": "Analyzing request...", "prompt_preview": prompt_preview[:100]},
            iteration
        )
    
    async def emit_tool_call(
        self,
        agent: str,
        tool_name: str,
        tool_args: dict,
        iteration: int,
        result: Any = None,
        error: str | None = None
    ):
        """Emit tool call event."""
        event_type = EventType.TOOL_CALL_START if result is None else EventType.TOOL_CALL_END
        
        data = {
            "tool_name": tool_name,
            "args": tool_args,
        }
        
        if result is not None:
            data["result"] = str(result)[:200]  # Truncate long results
            data["success"] = error is None
        
        if error:
            data["error"] = error
        
        await self.emit(event_type, agent, data, iteration)
    
    async def emit_agent_end(
        self,
        agent: str,
        summary: str,
        iteration: int,
        success: bool = True
    ):
        """Emit agent end event."""
        await self.emit(
            EventType.AGENT_END,
            agent,
            {"message": summary, "success": success},
            iteration
        )
    
    async def emit_token(self, agent: str, token: str, iteration: int):
        """Emit individual token (for LLM streaming)."""
        await self.emit(
            EventType.TOKEN_STREAM,
            agent,
            {"token": token},
            iteration
        )
    
    async def emit_status(self, message: str, progress: float = 0):
        """Emit general status update."""
        await self.emit(
            EventType.STATUS_UPDATE,
            "system",
            {"message": message, "progress": progress},
            0
        )
    
    async def emit_complete(self, summary: str, stats: dict):
        """Emit workflow completion."""
        await self.emit(
            EventType.COMPLETE,
            "system",
            {"summary": summary, "stats": stats},
            0
        )

# Global registry for active streams
_active_streams: dict[str, AgentStreamManager] = {}

def get_stream_manager(run_id: str) -> AgentStreamManager:
    """Get or create stream manager for run."""
    if run_id not in _active_streams:
        _active_streams[run_id] = AgentStreamManager(run_id)
    return _active_streams[run_id]

def cleanup_stream(run_id: str):
    """Cleanup stream manager after completion."""
    if run_id in _active_streams:
        del _active_streams[run_id]