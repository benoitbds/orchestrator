from contextvars import ContextVar
from typing import Optional

RUN_ID_CTX: ContextVar[Optional[str]] = ContextVar("RUN_ID_CTX", default=None)


def set_current_run_id(run_id: str) -> None:
    """Set the run identifier for the current context."""
    RUN_ID_CTX.set(run_id)


def get_current_run_id() -> Optional[str]:
    """Return the run identifier for the current context, if any."""
    return RUN_ID_CTX.get()
