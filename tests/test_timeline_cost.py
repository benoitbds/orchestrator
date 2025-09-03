import json
import pytest
from datetime import datetime, timedelta
from contextlib import contextmanager
from httpx import AsyncClient, ASGITransport
from sqlmodel import Session, create_engine, SQLModel

from api.main import app
from orchestrator import crud
from orchestrator.storage import models, services, db


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    # Setup old database for backward compatibility
    old_db = tmp_path / "old_db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(old_db))
    crud.init_db()
    
    # Setup new SQLModel database
    new_db = tmp_path / "new_db.sqlite"
    engine = create_engine(f"sqlite:///{new_db}")
    SQLModel.metadata.create_all(engine)
    
    # Monkey patch the get_session to use our test database
    @contextmanager
    def test_get_session():
        with Session(engine) as session:
            yield session
    
    monkeypatch.setattr(db, "get_session", test_get_session)
    yield


@pytest.mark.asyncio
async def test_timeline_events_order_and_limit():
    run_id = "r1"
    
    # Create test data using the new SQLModel system
    with db.get_session() as session:
        # Create run
        run = models.Run(id=run_id, project_id=1, status="running")
        session.add(run)
        session.commit()
        
        # Create test timeline data
        base_time = datetime(2024, 1, 1, 0, 0, 0)
        
        # Agent span (will create start/end events)
        span = models.AgentSpan(
            id="span1",
            run_id=run_id,
            agent_name="planner", 
            start_ts=base_time,
            end_ts=base_time + timedelta(seconds=10),
            status="ok",
            meta={"m": 1}
        )
        session.add(span)
        
        # Message
        msg = models.Message(
            id="msg1",
            run_id=run_id,
            agent_name="planner",
            role="assistant",
            ts=base_time + timedelta(seconds=1),
            total_tokens=10,
            cost_eur=0.1
        )
        session.add(msg)
        
        # Tool call
        tool_call = models.ToolCall(
            id="call1",
            run_id=run_id,
            agent_name="planner",
            tool_name="test_tool",
            ts=base_time + timedelta(seconds=2)
        )
        session.add(tool_call)
        
        # Tool result
        tool_result = models.ToolResult(
            id="result1",
            run_id=run_id,
            tool_call_id="call1",
            status="ok",
            ts=base_time + timedelta(seconds=3)
        )
        session.add(tool_result)
        
        session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get(f"/runs/{run_id}/timeline")
    assert resp.status_code == 200
    events = resp.json()
    types = [e["type"] for e in events]
    assert types == [
        "agent.span.start",
        "message",
        "tool.call",
        "tool.result",
        "agent.span.end",
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp2 = await ac.get(f"/runs/{run_id}/timeline", params={"limit": 2})
    assert len(resp2.json()) == 2


@pytest.mark.asyncio
async def test_timeline_run_not_found():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/runs/missing/timeline")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cost_aggregation_and_edges():
    run_id = "r2"
    
    # Create test data using the new SQLModel system
    with db.get_session() as session:
        # Create run
        run = models.Run(id=run_id, project_id=1, status="running")
        session.add(run)
        session.commit()
        
        # Create messages with different agents and costs
        base_time = datetime(2024, 1, 1, 0, 0, 0)
        
        messages = [
            models.Message(
                id="msg1",
                run_id=run_id,
                agent_name="planner",
                role="assistant",
                ts=base_time,
                total_tokens=10,
                cost_eur=0.1
            ),
            models.Message(
                id="msg2",
                run_id=run_id,
                agent_name="writer",
                role="assistant", 
                ts=base_time + timedelta(seconds=1),
                total_tokens=5,
                cost_eur=0.05
            ),
            models.Message(
                id="msg3",
                run_id=run_id,
                agent_name="planner",
                role="assistant",
                ts=base_time + timedelta(seconds=2),
                total_tokens=3,
                cost_eur=0.02
            ),
        ]
        
        for msg in messages:
            session.add(msg)
        session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get(f"/runs/{run_id}/cost")
    data = resp.json()
    assert resp.status_code == 200
    assert data["total"]["tokens"] == 18
    assert pytest.approx(data["total"]["cost_eur"], 0.001) == 0.17
    by_agent = {d["agent"]: d for d in data["by_agent"]}
    assert by_agent["planner"]["tokens"] == 13
    assert by_agent["writer"]["cost_eur"] == 0.05

    # Test empty run
    run_id_empty = "r3"
    with db.get_session() as session:
        run_empty = models.Run(id=run_id_empty, project_id=1, status="running")
        session.add(run_empty)
        session.commit()
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        empty_resp = await ac.get(f"/runs/{run_id_empty}/cost")
        missing_resp = await ac.get("/runs/missing/cost")
    assert empty_resp.json()["total"]["tokens"] == 0
    assert missing_resp.status_code == 404


@pytest.mark.asyncio
async def test_service_layer_functions():
    """Test the service layer functions directly."""
    run_id = "service_test"
    
    with db.get_session() as session:
        # Create a run first
        run = models.Run(id=run_id, project_id=1, status="running")
        session.add(run)
        session.commit()
        
        # Test save_blob
        blob_id = services.save_blob("test", {"test": "data"}, session=session)
        blob = session.get(models.BlobRef, blob_id)
        assert blob.data == {"test": "data"}
        assert blob.kind == "test"
        assert len(blob.sha256) == 64  # SHA256 hash length
        
        # Test span lifecycle
        span_id = services.start_span(run_id, "test_agent", session=session)
        assert span_id is not None
        
        span = session.get(models.AgentSpan, span_id)
        assert span.agent_name == "test_agent"
        assert span.run_id == run_id
        assert span.end_ts is None
        
        services.end_span(span_id, status="completed", session=session)
        session.refresh(span)
        assert span.status == "completed"
        assert span.end_ts is not None
        
        # Test save_message
        msg_id = services.save_message(
            run_id, 
            "assistant",
            content="Test message",
            agent_name="test_agent",
            model="gpt-4",
            tokens={"total": 100, "prompt": 80, "completion": 20},
            cost_eur=0.001,
            session=session
        )
        
        msg = session.get(models.Message, msg_id)
        assert msg.role == "assistant"
        assert msg.agent_name == "test_agent"
        assert msg.model == "gpt-4"
        assert msg.total_tokens == 100
        assert msg.prompt_tokens == 80
        assert msg.completion_tokens == 20
        assert msg.cost_eur == 0.001
        
        # Test tool call and result
        call_id = services.save_tool_call(
            run_id, "test_agent", "test_tool", session=session
        )
        
        tool_call = session.get(models.ToolCall, call_id)
        assert tool_call.tool_name == "test_tool"
        assert tool_call.agent_name == "test_agent"
        
        result_id = services.save_tool_result(
            call_id, "success", session=session
        )
        
        tool_result = session.get(models.ToolResult, result_id)
        assert tool_result.status == "success"
        assert tool_result.tool_call_id == call_id
        
        # Test timeline and cost functions
        timeline = services.get_run_timeline(run_id, session=session)
        assert len(timeline) >= 3  # span start, span end, message, tool call, tool result
        
        cost_data = services.get_run_cost(run_id, session=session)
        assert cost_data["total"]["tokens"] == 100
        assert cost_data["total"]["cost_eur"] == 0.001
        assert len(cost_data["by_agent"]) == 1
        assert cost_data["by_agent"][0]["agent"] == "test_agent"
