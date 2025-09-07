from __future__ import annotations

from time import time
from typing import Any, Dict, Tuple
from uuid import uuid4

ACTIVE_RUNS: Dict[str, Dict[str, Any]] = {}
RUN_ID_TO_CLIENT: Dict[str, str] = {}
REUSE_WINDOW_SEC = 10


def generate_run_id() -> str:
    return str(uuid4())


def get_or_create_run(
    client_id: str,
    project_id: int | None,
    objective: str | None,
    run_id: str | None,
) -> Tuple[Dict[str, Any] | None, bool]:
    """Get existing run or create a new one.

    Returns (entry, created_new).
    """
    now_ts = time()
    entry = ACTIVE_RUNS.get(client_id)

    # Case 1: explicit run_id -> reuse/attach
    if run_id:
        if entry and entry.get("run_id") == run_id:
            return entry, False
        ACTIVE_RUNS[client_id] = {
            "run_id": run_id,
            "project_id": project_id,
            "objective": objective,
            "started_at": now_ts,
            "status": "resuming",
        }
        RUN_ID_TO_CLIENT[run_id] = client_id
        return ACTIVE_RUNS[client_id], False

    # Case 3: neither run_id nor objective
    if objective is None:
        if (
            entry
            and now_ts - entry.get("started_at", 0) <= REUSE_WINDOW_SEC
            and entry.get("status") in ("running", "resuming")
        ):
            return entry, False
        return None, False

    # Case 2: objective provided; dedupe within window
    if (
        entry
        and entry.get("objective") == objective
        and entry.get("project_id") == project_id
        and now_ts - entry.get("started_at", 0) <= REUSE_WINDOW_SEC
        and entry.get("status") in ("running", "resuming", "done")
    ):
        return entry, False

    new_run_id = generate_run_id()
    ACTIVE_RUNS[client_id] = {
        "run_id": new_run_id,
        "project_id": project_id,
        "objective": objective,
        "started_at": now_ts,
        "status": "running",
    }
    RUN_ID_TO_CLIENT[new_run_id] = client_id
    return ACTIVE_RUNS[client_id], True


def mark_run_done(run_id: str) -> None:
    client_id = RUN_ID_TO_CLIENT.get(run_id)
    if not client_id:
        return
    entry = ACTIVE_RUNS.get(client_id)
    if entry and entry.get("run_id") == run_id:
        entry["status"] = "done"
