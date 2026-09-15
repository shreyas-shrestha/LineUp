"""Logging setup: level and format from config, one handler, no duplicates."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

_HANDLER_FLAG = "_lineup_handler"


class JsonFormatter(logging.Formatter):
    """Minimal structured formatter (one JSON object per line)."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level: str = "INFO", fmt: str = "text") -> None:
    root = logging.getLogger()
    numeric = getattr(logging, level.upper(), logging.INFO)
    root.setLevel(numeric)

    for handler in list(root.handlers):
        if getattr(handler, _HANDLER_FLAG, False):
            root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    setattr(handler, _HANDLER_FLAG, True)
    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(handler)

    # Third-party noise
    for noisy in ("urllib3", "google", "PIL", "httpx"):
        logging.getLogger(noisy).setLevel(max(numeric, logging.WARNING))
