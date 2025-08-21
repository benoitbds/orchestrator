import orchestrator.core_loop as cl
from orchestrator import crud
from agents.schemas import Plan, PlanStep
import types
from uuid import uuid4

crud.init_db()

def test_loop():
    mem = cl.Memory()
    run_id = str(uuid4())
    objective = "Dire bonjour en français"
    crud.create_run(run_id, objective, None)
    state = cl.LoopState(objective=objective, mem_obj=mem, run_id=run_id)
    out = cl.graph.invoke(state)
    assert "réussie" in out["result"].lower()


def test_record_run_step_counts(monkeypatch):
    run_id = str(uuid4())
    crud.create_run(run_id, "obj", None)

    plan = Plan(objective="obj", steps=[
        PlanStep(id=1, title="A", description="d"),
        PlanStep(id=2, title="B", description="d"),
    ])
    monkeypatch.setattr(cl, "make_plan", lambda objective: plan)
    monkeypatch.setattr(
        cl.llm_step,
        "invoke",
        lambda prompt: types.SimpleNamespace(content="out"),
    )

    state = cl.LoopState(objective="obj", mem_obj=cl.Memory(), run_id=run_id)
    out = cl.planner(state)
    state.plan = out["plan"]
    exec_out = cl.executor(state)
    state.exec_result = exec_out["exec_result"]
    cl.writer(state)

    steps = crud.get_run(run_id)["steps"]
    assert [s["node"] for s in steps] == ["plan", "execute", "execute", "write"]
    assert steps[1]["content"].count("A") == 1
