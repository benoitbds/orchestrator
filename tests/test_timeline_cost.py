import json
import pytest
from httpx import AsyncClient, ASGITransport

from api.main import app
from orchestrator import crud


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    yield


@pytest.mark.asyncio
async def test_timeline_events_order_and_limit():
    run_id = "r1"
    crud.create_run(run_id, "obj", 1)
    conn = crud.get_conn()
    conn.execute(
        "INSERT INTO agent_spans(run_id, agent_name, label, start_ts, end_ts, ref, meta) VALUES (?,?,?,?,?,?,?)",
        (
            run_id,
            "planner",
            "plan",
            "2024-01-01T00:00:00",
            "2024-01-01T00:00:10",
            json.dumps({"r": 1}),
            json.dumps({"m": 1}),
        ),
    )
    conn.execute(
        "INSERT INTO messages(run_id, agent_name, label, ts, ref, meta, token_count, cost_eur) VALUES (?,?,?,?,?,?,?,?)",
        (
            run_id,
            "planner",
            "msg",
            "2024-01-01T00:00:01",
            "{}",
            "{}",
            10,
            0.1,
        ),
    )
    conn.execute(
        "INSERT INTO tool_calls(run_id, agent_name, label, ts, ref, meta) VALUES (?,?,?,?,?,?)",
        (
            run_id,
            "planner",
            "tool",
            "2024-01-01T00:00:02",
            "{}",
            "{}",
        ),
    )
    conn.execute(
        "INSERT INTO tool_results(run_id, agent_name, label, ts, ref, meta) VALUES (?,?,?,?,?,?)",
        (
            run_id,
            "planner",
            "tool",
            "2024-01-01T00:00:03",
            "{}",
            "{}",
        ),
    )
    conn.commit()
    conn.close()

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
    crud.create_run(run_id, "obj", 1)
    conn = crud.get_conn()
    conn.executemany(
        "INSERT INTO messages(run_id, agent_name, label, ts, ref, meta, token_count, cost_eur) VALUES (?,?,?,?,?,?,?,?)",
        [
            (
                run_id,
                "planner",
                "m1",
                "2024-01-01T00:00:00",
                "{}",
                "{}",
                10,
                0.1,
            ),
            (
                run_id,
                "writer",
                "m2",
                "2024-01-01T00:00:01",
                "{}",
                "{}",
                5,
                0.05,
            ),
            (
                run_id,
                "planner",
                "m3",
                "2024-01-01T00:00:02",
                "{}",
                "{}",
                3,
                0.02,
            ),
        ],
    )
    conn.commit()
    conn.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get(f"/runs/{run_id}/cost")
    data = resp.json()
    assert resp.status_code == 200
    assert data["total"]["tokens"] == 18
    assert pytest.approx(data["total"]["cost_eur"], 0.001) == 0.17
    by_agent = {d["agent"]: d for d in data["by_agent"]}
    assert by_agent["planner"]["tokens"] == 13
    assert by_agent["writer"]["cost_eur"] == 0.05

    run_id_empty = "r3"
    crud.create_run(run_id_empty, "obj", 1)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        empty_resp = await ac.get(f"/runs/{run_id_empty}/cost")
        missing_resp = await ac.get("/runs/missing/cost")
    assert empty_resp.json()["total"]["tokens"] == 0
    assert missing_resp.status_code == 404
