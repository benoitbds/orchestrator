import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app
from orchestrator import crud


def setup_module(module):
    """Ensure a clean database for these tests."""
    crud.init_db()
    conn = crud.get_db_connection()
    conn.execute("DELETE FROM run_steps")
    conn.execute("DELETE FROM runs")
    conn.commit()
    conn.close()


def _reset_runs():
    conn = crud.get_db_connection()
    conn.execute("DELETE FROM run_steps")
    conn.execute("DELETE FROM runs")
    conn.commit()
    conn.close()


def test_run_creation_and_retrieval():
    run_id = str(uuid.uuid4())
    crud.create_run(run_id, "objective", 1)
    run = crud.get_run(run_id)
    assert run["run_id"] == run_id
    assert run["objective"] == "objective"
    assert run["status"] == "running"
    assert run["steps"] == []


def test_record_steps_in_order():
    run_id = str(uuid.uuid4())
    crud.create_run(run_id, "test order", 1)
    crud.record_run_step(run_id, "first", "one")
    crud.record_run_step(run_id, "second", "two")
    steps = crud.get_run(run_id)["steps"]
    assert [s["node"] for s in steps] == ["first", "second"]


def test_finish_run_updates_status_and_render():
    run_id = str(uuid.uuid4())
    crud.create_run(run_id, "finish", 1)
    crud.finish_run(run_id, "<p>hi</p>", "done")
    run = crud.get_run(run_id)
    assert run["status"] == "done"
    assert run["html"] == "<p>hi</p>"
    assert run["summary"] == "done"
    assert run["completed_at"] is not None


def test_get_runs_filters_by_project():
    _reset_runs()
    r1 = str(uuid.uuid4())
    r2 = str(uuid.uuid4())
    crud.create_run(r1, "obj1", 1)
    crud.create_run(r2, "obj2", 2)

    runs_project1 = crud.get_runs(1)
    assert len(runs_project1) == 1
    assert runs_project1[0]["run_id"] == r1


@pytest.mark.asyncio
async def test_get_run_endpoint_and_steps_order():
    _reset_runs()
    run_id = str(uuid.uuid4())
    crud.create_run(run_id, "api test", 1)
    crud.record_run_step(run_id, "first", "one")
    crud.record_run_step(run_id, "second", "two")
    crud.finish_run(run_id, "<p>done</p>", "summary")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(f"/runs/{run_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["run_id"] == run_id
    assert [s["order"] for s in data["steps"]] == [1, 2]
    assert [s["node"] for s in data["steps"]] == ["first", "second"]


@pytest.mark.asyncio
async def test_get_run_endpoint_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/runs/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_runs_endpoint_filters_by_project():
    _reset_runs()
    r1 = str(uuid.uuid4())
    r2 = str(uuid.uuid4())
    crud.create_run(r1, "obj1", 1)
    crud.create_run(r2, "obj2", 2)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res_all = await ac.get("/runs")
        assert res_all.status_code == 200
        ids = {r["run_id"] for r in res_all.json()}
        assert ids == {r1, r2}

        res_proj1 = await ac.get("/runs", params={"project_id": 1})
        assert res_proj1.status_code == 200
        data_proj1 = res_proj1.json()
        assert len(data_proj1) == 1 and data_proj1[0]["run_id"] == r1

        res_none = await ac.get("/runs", params={"project_id": 999})
        assert res_none.status_code == 200
        assert res_none.json() == []

