# tests/test_planner.py
from agents.planner import make_plan
from agents.schemas import Plan

def test_make_plan():
    plan = make_plan("Construire une todo-app React")
    assert isinstance(plan, Plan)
    assert 3 <= len(plan.steps) <= 6
    ids = [s.id for s in plan.steps]
    assert ids == sorted(ids)          # ids en ordre croissant
