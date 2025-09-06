import os
import json
import logging
from datetime import datetime
from typing import Any, Optional


class JSONLHandler(logging.Handler):
    """Write logs as JSON lines with daily rotation."""

    def __init__(self, directory: str = "logs") -> None:
        super().__init__()
        self.directory = directory
        os.makedirs(directory, exist_ok=True)
        self._current_date: Optional[str] = None
        self._stream: Optional[Any] = None

    def _update_stream(self) -> None:
        date = datetime.utcnow().strftime("%Y%m%d")
        if self._current_date != date:
            if self._stream:
                self._stream.close()
            self._current_date = date
            path = os.path.join(self.directory, f"app-{date}.jsonl")
            self._stream = open(path, "a", encoding="utf-8")

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - used in tests
        try:
            self.acquire()
            self._update_stream()
            payload = {
                "ts": datetime.utcnow().isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "area": getattr(record, "area", None),
                "run_id": getattr(record, "run_id", None),
                "agent": getattr(record, "agent", None),
                "tool": getattr(record, "tool", None),
                "payload": getattr(record, "payload", None),
            }
            assert self._stream is not None  # for type checkers
            json.dump(payload, self._stream, default=str)
            self._stream.write("\n")
            self._stream.flush()
        except Exception:
            self.handleError(record)
        finally:
            self.release()

    def close(self) -> None:
        try:
            if self._stream:
                self._stream.close()
        finally:
            super().close()


def log_extra(
    *,
    area: str | None = None,
    run_id: str | None = None,
    agent: str | None = None,
    tool: str | None = None,
    payload: Any | None = None,
) -> dict[str, Any]:
    """Return an extra dict for structured logging."""
    return {
        "area": area,
        "run_id": run_id,
        "agent": agent,
        "tool": tool,
        "payload": payload,
    }
