# agents/executor.py
import subprocess
import os
import textwrap
import uuid
import signal
from pathlib import Path
from .schemas import ExecResult

SANDBOX_DIR = Path("/tmp/orchestrator_runs")  # nettoyé par cron éventuellement
SANDBOX_DIR.mkdir(exist_ok=True)

WHITELIST = {"math", "json", "datetime", "re", "random"}  # modules autorisés

FORBIDDEN_IMPORTS = {"os", "sys", "subprocess", "socket"}


def _is_safe(code: str) -> bool:
    """Parse the code AST and reject dangerous imports."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in FORBIDDEN_IMPORTS:
                    return False
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] in FORBIDDEN_IMPORTS:
                return False
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "__import__":
                if node.args and isinstance(node.args[0], (ast.Str, ast.Constant)):
                    mod_name = node.args[0].s if isinstance(node.args[0], ast.Str) else node.args[0].value
                    if isinstance(mod_name, str) and mod_name.split(".")[0] in FORBIDDEN_IMPORTS:
                        return False

    # fallback simple check for open()
    if "open(" in code:
        return False

    return True

def run_python(code: str, timeout: int = 15) -> ExecResult:
    if not _is_safe(code):
        return ExecResult(success=False, stdout="", stderr="Unsafe code detected")
    run_id = uuid.uuid4().hex
    workdir = SANDBOX_DIR / run_id
    workdir.mkdir()
    script = workdir / "script.py"
    script.write_text(textwrap.dedent(code))

    try:
        proc = subprocess.run(
            ["python", str(script)],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=timeout,
            preexec_fn=lambda: os.setsid()  # permet de tuer le groupe si timeout
        )
        success = proc.returncode == 0
        return ExecResult(
            success=success,
            stdout=proc.stdout,
            stderr=proc.stderr,
            artifacts=[str(p) for p in workdir.iterdir() if p != script],
        )
    except subprocess.TimeoutExpired:
        os.killpg(0, signal.SIGKILL)
        return ExecResult(success=False, stdout="", stderr="Timeout")
    finally:
        # ⚠️ on garde le dossier pour inspecter les artefacts / debug
        pass
