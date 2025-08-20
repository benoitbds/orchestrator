import uuid

import uuid
from orchestrator import crud


def setup_module(module):
    """Ensure a clean database for these tests."""
    crud.init_db()
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
    conn = crud.get_db_connection()
    conn.execute("DELETE FROM run_steps")
    conn.execute("DELETE FROM runs")
    conn.commit()
    conn.close()

    r1 = str(uuid.uuid4())
    r2 = str(uuid.uuid4())
    crud.create_run(r1, "obj1", 1)
    crud.create_run(r2, "obj2", 2)

    runs_project1 = crud.get_runs(1)
    assert len(runs_project1) == 1
    assert runs_project1[0]["run_id"] == r1

