"""WebSocket endpoint for real-time multi-agent streaming."""
import json
import asyncio
import uuid
from typing import Dict, Any
from datetime import datetime
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
    
    print(f"\n{'='*60}")
    print("✅ WEBSOCKET CONNECTION ATTEMPT")
    print(f"Run ID: {run_id}")
    print(f"Client: {websocket.client}")
    print(f"Headers: {dict(websocket.headers)}")
    print(f"{'='*60}\n")
    
    try:
        await manager.connect(websocket, run_id)
        print(f"✅ WEBSOCKET ACCEPTED: {run_id}")
    except Exception as e:
        print(f"❌ WEBSOCKET ACCEPT FAILED: {e}")
        raise
    
    try:
        print(f"[{run_id}] 🔄 Entering message receive loop...")
        
        # Send initial hello message to confirm connection
        await websocket.send_text(json.dumps({
            "type": "connected",
            "run_id": run_id,
            "message": "WebSocket connection established"
        }))
        print(f"[{run_id}] 📤 Sent connection confirmation")
        
        while True:
            # Wait for client message with timeout to prevent hanging
            print(f"[{run_id}] ⏳ Waiting for client message...")
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                print(f"[{run_id}] 📨 Received raw data: {data[:200]}...")
                message = json.loads(data)
                print(f"[{run_id}] 📦 Parsed message type: {message.get('type')}")
                
                if message["type"] == "start_agents":
                    print(f"[{run_id}] Starting agent execution...")
                    await handle_agent_execution(run_id, message["payload"])
                elif message["type"] == "ping":
                    print(f"[{run_id}] 🏓 Received ping, sending pong")
                    await websocket.send_text(json.dumps({"type": "pong"}))
                else:
                    print(f"[{run_id}] ⚠️ Unknown message type: {message.get('type')}")
                    
            except asyncio.TimeoutError:
                # Send keepalive ping
                print(f"[{run_id}] 💓 Sending keepalive ping")
                await websocket.send_text(json.dumps({"type": "keepalive"}))
                
    except WebSocketDisconnect as e:
        print(f"[{run_id}] 🔴 WebSocket disconnected by client: {e}")
        manager.disconnect(run_id)
        cleanup_stream(run_id)
    except Exception as e:
        print(f"[{run_id}] ❌ WebSocket error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "error": str(e)
            }))
        except Exception as send_error:
            print(f"[{run_id}] ❌ Failed to send error to client: {send_error}")
        manager.disconnect(run_id)
        cleanup_stream(run_id)
    finally:
        print(f"[{run_id}] 🏁 WebSocket handler exiting")

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
        
        # Create Run record with project_id
        from orchestrator.storage.db import get_session
        from orchestrator.storage.models import Run
        print(f"[{run_id}] Creating Run record with project_id={project_id}, user_uid={user_uid}")
        with get_session() as session:
            if session.get(Run, run_id) is None:
                new_run = Run(id=run_id, project_id=project_id, user_uid=user_uid)
                session.add(new_run)
                session.commit()
                print(f"[{run_id}] Run record created successfully")
            else:
                print(f"[{run_id}] Run record already exists")
        
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
            # Use async API with increased recursion limit for approval workflows
            config = {"recursion_limit": 50}
            result = await graph.ainvoke(initial_state, config=config)
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
    
    async def send_keepalive():
        """Send periodic keepalive pings to maintain connection."""
        while True:
            await asyncio.sleep(30)  # Every 30 seconds
            try:
                await manager.send_event(run_id, {
                    "type": "keepalive",
                    "timestamp": datetime.utcnow().isoformat(),
                    "run_id": run_id
                })
            except Exception:
                break  # Connection closed, stop keepalive
    
    keepalive_task = asyncio.create_task(send_keepalive())
    
    try:
        while True:
            # Get next event from stream with timeout
            try:
                event = await asyncio.wait_for(queue.get(), timeout=60.0)
            except asyncio.TimeoutError:
                # No events for 60s, but keepalive should keep connection alive
                continue
            
            # Send to WebSocket
            await manager.send_event(run_id, event)
            
            # Break on completion
            if event["type"] == "complete":
                break
                
    except Exception as e:
        print(f"Error in event streaming for {run_id}: {e}")
    finally:
        keepalive_task.cancel()
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