import orchestrator.core_loop as cl

def test_loop():
    mem = cl.Memory()
    state = cl.LoopState(objective="Dire bonjour en français", mem_obj=mem)
    out = cl.graph.invoke(state)
    assert "réussie" in out["result"].lower()
