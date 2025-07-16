import orchestrator.core_loop as cl
from agents.schemas import ExecResult

def test_todo_e2e():
    state = cl.LoopState(
        objective="Construis une todo-app React",
        mem_obj=cl.Memory()
    )
    out = cl.graph.invoke(state)

    # -------- vérifs fondamentales --------
    assert "render" in out
    assert "exec_result" in out

    exec_res = ExecResult(**out["exec_result"])
    assert exec_res.success, "Exécution du code échouée"

    # un minimum de contenu “todo” dans le HTML généré
    assert "todo" in out["render"]["html"].lower()
