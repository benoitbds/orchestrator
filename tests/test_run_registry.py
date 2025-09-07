import time

from orchestrator.run_registry import (
    ACTIVE_RUNS,
    RUN_ID_TO_CLIENT,
    get_or_create_run,
    mark_run_done,
)


def setup_function(_):
    ACTIVE_RUNS.clear()
    RUN_ID_TO_CLIENT.clear()


def test_get_or_create_run_reuses_recent_run():
    entry, created = get_or_create_run("client1", 1, "obj", None)
    assert created
    run_id = entry["run_id"]
    # second call within window should reuse
    entry2, created2 = get_or_create_run("client1", 1, "obj", None)
    assert not created2
    assert entry2["run_id"] == run_id


def test_mark_run_done_sets_status():
    entry, _ = get_or_create_run("client2", 2, "obj2", None)
    run_id = entry["run_id"]
    mark_run_done(run_id)
    assert ACTIVE_RUNS["client2"]["status"] == "done"
