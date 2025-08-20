import orchestrator.core_loop as cl
from orchestrator import crud

crud.init_db()

def test_loop():
    mem = cl.Memory()
    from uuid import uuid4
    run_id = str(uuid4())
    objective = "Dire bonjour en français"
    crud.create_run(run_id, objective, None)
    state = cl.LoopState(objective=objective, mem_obj=mem, run_id=run_id)
    out = cl.graph.invoke(state)
    assert "réussie" in out["result"].lower()
