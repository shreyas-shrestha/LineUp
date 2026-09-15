"""Daily call budget for paid/free-tier external APIs."""

from __future__ import annotations

import threading
from datetime import date
from typing import Any, Dict, Optional


class DailyQuota:
    """Counts calls per UTC-agnostic local day. ``limit <= 0`` means unlimited."""

    def __init__(self, limit: int, name: str = "api") -> None:
        self.limit = limit
        self.name = name
        self.used = 0
        self.reset_date = date.today()
        self._lock = threading.Lock()

    def _roll(self) -> None:
        today = date.today()
        if today != self.reset_date:
            self.used = 0
            self.reset_date = today

    def can_call(self) -> bool:
        with self._lock:
            self._roll()
            return self.limit <= 0 or self.used < self.limit

    def record(self, count: int = 1) -> None:
        with self._lock:
            self._roll()
            self.used += count

    @property
    def remaining(self) -> Optional[int]:
        with self._lock:
            self._roll()
            return None if self.limit <= 0 else max(0, self.limit - self.used)

    def snapshot(self) -> Dict[str, Any]:
        return {"used": self.used, "limit": self.limit, "remaining": self.remaining, "reset_date": self.reset_date.isoformat()}
