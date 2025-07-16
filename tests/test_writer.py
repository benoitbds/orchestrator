# tests/test_writer.py
from agents.schemas import ExecResult
from agents.writer import render_exec

def test_render_success():
    exec_res = ExecResult(success=True, stdout="hello", stderr="")
    render = render_exec(exec_res, "Dire bonjour")
    assert "hello" in render.html
    assert "Exécution réussie" in render.summary

def test_render_error():
    exec_res = ExecResult(success=False, stdout="", stderr="Boom")
    render = render_exec(exec_res, "Tester l'erreur")
    assert "Boom" in render.html
    assert "Erreur" in render.summary
