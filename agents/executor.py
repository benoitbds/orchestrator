# agents/executor.py
import subprocess, tempfile, shutil, os, textwrap, uuid, json, signal
from pathlib import Path
from typing import List
from .schemas import ExecResult

SANDBOX_DIR = Path("/tmp/orchestrator_runs")  # nettoyé par cron éventuellement
SANDBOX_DIR.mkdir(exist_ok=True)

WHITELIST = {"math", "json", "datetime", "re", "random"}  # modules autorisés

def _is_safe(code: str) -> bool:
    """Empêche import os, sys, socket, etc. Ultra-basique pour MVP."""
    forbidden = ["import os", "import subprocess", "import socket", "open("]
    return not any(tok in code for tok in forbidden)

def run_python(code: str, timeout: int = 5) -> ExecResult:
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
