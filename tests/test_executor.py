# tests/test_executor.py
from agents.executor import run_python

def test_run_python_ok():
    code = "print('hello world')"
    res = run_python(code)
    assert res.success
    assert "hello world" in res.stdout

def test_run_python_forbidden():
    res = run_python("import os\nprint(os.listdir())")
    assert not res.success
    assert "Unsafe" in res.stderr
