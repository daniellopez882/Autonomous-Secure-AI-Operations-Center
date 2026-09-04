"""
core/logging_config.py
One logging setup for the whole service.

Previously every agent built its own handler in ``BaseAgent._setup_logging``,
which attached a fresh ``StreamHandler`` per instance. Constructing an agent
twice produced duplicate log lines, and there was no single place to switch
formats or levels.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

_configured = False


class JsonFormatter(logging.Formatter):
    """Minimal JSON formatter; keeps structured fields passed via ``extra``."""

    RESERVED = frozenset(vars(logging.LogRecord("", 0, "", 0, "", (), None)).keys()) | {
        "message",
        "asctime",
        "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "event": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in self.RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class _EventLogger(logging.LoggerAdapter):
    """Lets callers write ``logger.info("event_name", key=value)``."""

    def process(self, msg: Any, kwargs: dict) -> tuple[Any, dict]:
        extra = {
            k: v for k, v in kwargs.items() if k not in ("exc_info", "stack_info", "stacklevel")
        }
        passthrough = {
            k: v for k, v in kwargs.items() if k in ("exc_info", "stack_info", "stacklevel")
        }
        passthrough["extra"] = {**(self.extra or {}), **extra}
        return msg, passthrough

    def info(self, msg, *args, **kwargs):
        return super().info(msg, *args, **kwargs)


def setup_logging(level: str = "INFO", json_output: bool = False, force: bool = False) -> None:
    """Configure the root logger once."""
    global _configured
    if _configured and not force:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter()
        if json_output
        else logging.Formatter("%(asctime)s %(levelname)-8s %(name)s %(message)s")
    )

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # uvicorn installs its own handlers; route them through ours so output is
    # one consistent format rather than two.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True

    _configured = True


def get_logger(name: str) -> _EventLogger:
    """Return a logger that accepts structured keyword fields."""
    setup_logging()
    return _EventLogger(logging.getLogger(name), {})
