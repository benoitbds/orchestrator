"""WebSocket endpoint for real-time multi-agent streaming."""
import json
import asyncio
import uuid
from typing import Dict, Any
from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from langchain_core.messages import HumanMessage

from agents_v2.graph import build_agent_graph
from agents_v2.state import AgentState
from agents_v2.streaming import get_stream_manager, cleanup_stream
from api.auth import verify_id_token

class ConnectionManager:
    """Manages WebSocket connections for streaming."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, run_id: str):
        """Accept WebSocket connection."""
        await websocket.accept()
        self.active_connections[run_id] = websocket
    
    def disconnect(self, run_id: str):
        """Remove connection."""
        if run_id in self.active_connections:
            del self.active_connections[run_id]
    
    async def send_event(self, run_id: str, event: Dict[str, Any]):
        """Send event to specific connection."""
        if run_id in self.active_connections:
            websocket = self.active_connections[run_id]
            try:
                await websocket.send_text(json.dumps(event))
            except Exception as e:
                print(f"Error sending event to {run_id}: {e}")
                self.disconnect(run_id)

manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket, run_id: str = None):
    """WebSocket endpoint for real-time agent streaming."""
    if not run_id:
        run_id = str(uuid.uuid4())
    
    print(f"=== WEBSOCKET CONNECTING: {run_id} ===")
    await manager.connect(websocket, run_id)
    print(f"=== WEBSOCKET CONNECTED: {run_id} ===")
    
    try:
        while True:
            # Wait for client message
            print(f"[{run_id}] Waiting for client message...")
            data = await websocket.receive_text()
            message = json.loads(data)
            print(f"[{run_id}] Received message: {message.get('type')}")
            
            if message["type"] == "start_agents":
                print(f"[{run_id}] Starting agent execution...")
                await handle_agent_execution(run_id, message["payload"])
            elif message["type"] == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
                
    except WebSocketDisconnect:
        manager.disconnect(run_id)
        cleanup_stream(run_id)
    except Exception as e:
        await websocket.send_text(json.dumps({
            "type": "error",
            "error": str(e)
        }))
        manager.disconnect(run_id)
        cleanup_stream(run_id)

async def handle_agent_execution(run_id: str, payload: Dict[str, Any]):
    """Execute agents with real-time streaming."""
    print(f"=== HANDLE_AGENT_EXECUTION CALLED for {run_id} ===")
    print(f"Payload: {payload}")
    try:
        # Validate payload
        project_id = payload.get("project_id")
        objective = payload.get("objective")
        user_token = payload.get("token")
        meta = payload.get("meta")
        
        print(f"Project ID: {project_id}, Objective: {objective[:50]}..., Token present: {bool(user_token)}")
        
        if not all([project_id, objective, user_token]):
            print("ERROR: Missing required fields!")
            raise ValueError("Missing required fields: project_id, objective, token")
        
        # Verify Firebase token
        try:
            user_info = await verify_id_token(user_token)
            user_uid = user_info["uid"]
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
        
        # Build graph with Redis checkpointer (will fallback gracefully)
        try:
            from config.redis import get_checkpointer
            print(f"[{run_id}] Getting Redis checkpointer...")
            checkpointer = await get_checkpointer()
            print(f"[{run_id}] Redis checkpointer obtained")
        except Exception as e:
            print(f"[{run_id}] Redis unavailable, using memory checkpointer: {e}")
            checkpointer = None
        
        print(f"[{run_id}] Building agent graph...")
        graph = build_agent_graph(checkpointer=checkpointer)
        print(f"[{run_id}] Graph built successfully")
        
        # Set up streaming manager
        stream_manager = get_stream_manager(run_id)
        
        # Create event listener task
        asyncio.create_task(stream_events_to_websocket(run_id, stream_manager))
        
        # Initial state with all required fields
        initial_state: AgentState = {
            "messages": [HumanMessage(content=objective)],
            "project_id": project_id,
            "user_uid": user_uid,
            "objective": objective,
            "meta": meta,
            "next_agent": "",
            "current_agent": None,
            "iteration": 0,
            "max_iterations": 10,
            "tool_results": {},
            "items_created": None,
            "documents_searched": None,
            "error": None,
            "run_id": run_id,
            "status_message": None,
            "progress_steps": None,
            "synthesis_complete": None,
            "final_response": None,
            "is_stub": None,
            "workflow_steps": None,
            "current_step_index": None,
            "is_paused": None,
            "pending_approval": None
        }
        
        if meta:
            print(f"[{run_id}] Metadata received: {meta}")
        
        print(f"[{run_id}] Initial state prepared with {len(initial_state)} fields")
        
        # Start status
        print(f"[{run_id}] Emitting start status...")
        await stream_manager.emit_status("Starting multi-agent execution...", 0.0)
        
        print(f"[{run_id}] Starting graph execution with ainvoke...")
        
        try:
            # Use async API since nodes are async functions
            result = await graph.ainvoke(initial_state)
            print(f"[{run_id}] Graph.ainvoke() completed. Result type: {type(result)}")
            print(f"[{run_id}] Result keys: {list(result.keys()) if result else 'None'}")
            if result:
                print(f"[{run_id}] Iteration: {result.get('iteration')}, Error: {result.get('error')}")
        except Exception as e:
            print(f"[{run_id}] ERROR in graph.ainvoke(): {e}")
            import traceback
            traceback.print_exc()
            raise
        
        print(f"[{run_id}] Graph execution complete")
        
        # Final completion
        await stream_manager.emit_complete(
            "Multi-agent execution completed successfully",
            {
                "total_iterations": result.get("iteration", 0) if result else 0,
                "run_id": run_id,
                "final_response": result.get("final_response") if result else None
            }
        )
        
        # Clean up after a delay
        await asyncio.sleep(2)
        cleanup_stream(run_id)
        
    except Exception as e:
        # Send error to client
        if run_id in manager.active_connections:
            await manager.active_connections[run_id].send_text(json.dumps({
                "type": "error", 
                "error": str(e),
                "run_id": run_id
            }))
        cleanup_stream(run_id)

async def stream_events_to_websocket(run_id: str, stream_manager):
    """Stream events from AgentStreamManager to WebSocket."""
    queue = stream_manager.subscribe()
    
    try:
        while True:
            # Get next event from stream
            event = await queue.get()
            
            # Send to WebSocket
            await manager.send_event(run_id, event)
            
            # Break on completion
            if event["type"] == "complete":
                break
                
    except Exception as e:
        print(f"Error in event streaming for {run_id}: {e}")
    finally:
        stream_manager.unsubscribe(queue)

# Integration with existing FastAPI app
def register_websocket_routes(app):
    """Register WebSocket routes with FastAPI app."""
    
    @app.websocket("/ws/agents/{run_id}")
    async def websocket_agents_endpoint(websocket: WebSocket, run_id: str):
        await websocket_endpoint(websocket, run_id)
    
    @app.websocket("/ws/agents")
    async def websocket_agents_auto_endpoint(websocket: WebSocket):
        await websocket_endpoint(websocket)