# tests/test_planner.py
from agents import planner as pl
from agents.schemas import Plan
import types
import json
import pytest

@pytest.mark.usefixtures("patch_graph")
def test_make_plan(monkeypatch):
    def fake_invoke(messages):
        json_plan = {
            "objective": "Construire une todo-app React",
            "steps": [
                {"id": 1, "title": "Step 1", "description": "desc", "depends_on": []},
                {"id": 2, "title": "Step 2", "description": "desc", "depends_on": [1]},
                {"id": 3, "title": "Step 3", "description": "desc", "depends_on": [2]},
            ],
        }
        return types.SimpleNamespace(content=json.dumps(json_plan))

    monkeypatch.setattr(pl.ChatOpenAI, "invoke", lambda self, messages: fake_invoke(messages))

    plan = pl.make_plan("Construire une todo-app React")
    assert isinstance(plan, Plan)
    assert 3 <= len(plan.steps) <= 6
    ids = [s.id for s in plan.steps]
    assert ids == sorted(ids)          # ids en ordre croissant
