import os
import subprocess
import sys
import logging

SCRIPT = """
import logging
from api.main import setup_logging

{pre_code}
setup_logging()
print(logging.getLogger().level)
print(len(logging.getLogger().handlers))
"""

def run_script(pre_code: str, env: dict[str, str] | None = None):
    code = SCRIPT.format(pre_code=pre_code)
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env
    )
    return result.stdout.strip().splitlines()


def test_setup_logging_debug():
    env = os.environ.copy()
    env["LOGLEVEL"] = "DEBUG"
    level, count = run_script("logging.getLogger().handlers=[]", env)
    assert int(level) == logging.DEBUG
    assert int(count) == 1


def test_setup_logging_invalid_level():
    env = os.environ.copy()
    env["LOGLEVEL"] = "NOPE"
    level, count = run_script("logging.getLogger().handlers=[]", env)
    assert int(level) == logging.INFO
    assert int(count) == 1


def test_setup_logging_existing_handler():
    env = os.environ.copy()
    pre = "l=logging.getLogger(); l.handlers=[logging.NullHandler()]"
    level, count = run_script(pre, env)
    assert int(level) == logging.INFO
    assert int(count) == 1
