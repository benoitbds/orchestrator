import orchestrator.core_loop as cl

def test_loop():
    mem = cl.Memory(project_id=1)
    state = cl.LoopState(objective="Dire bonjour en français", mem_obj=mem)
    out = cl.graph.invoke(state)
    assert "réussie" in out["result"].lower()
