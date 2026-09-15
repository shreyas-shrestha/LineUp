"""Small TTL + size bounded cache used for Google Places results."""

from __future__ import annotations

import threading
import time
from copy import deepcopy
from typing import Any, Dict, Optional


class TTLCache:
    def __init__(self, ttl_seconds: int = 3600, max_size: int = 50) -> None:
        self.ttl = ttl_seconds
        self.max_size = max_size
        self._items: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def _expired(self, entry: Dict[str, Any], now: float) -> bool:
        return now - entry["timestamp"] >= self.ttl

    def get(self, key: str) -> Optional[Any]:
        now = time.time()
        with self._lock:
            entry = self._items.get(key)
            if entry is None:
                return None
            if self._expired(entry, now):
                del self._items[key]
                return None
            return deepcopy(entry["value"])

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._items[key] = {"value": deepcopy(value), "timestamp": time.time()}
            self._prune_locked()

    def _prune_locked(self) -> None:
        now = time.time()
        for key in [k for k, v in self._items.items() if self._expired(v, now)]:
            del self._items[key]
        if len(self._items) > self.max_size:
            oldest = sorted(self._items.items(), key=lambda kv: kv[1]["timestamp"])
            for key, _ in oldest[: len(self._items) - self.max_size]:
                del self._items[key]

    def prune(self) -> None:
        with self._lock:
            self._prune_locked()

    def clear(self) -> int:
        with self._lock:
            removed = len(self._items)
            self._items.clear()
            return removed

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)

    def stats(self) -> Dict[str, Any]:
        now = time.time()
        with self._lock:
            expired = sum(1 for v in self._items.values() if self._expired(v, now))
            return {
                "cache_size": len(self._items),
                "max_cache_size": self.max_size,
                "cache_duration_seconds": self.ttl,
                "expired_entries": expired,
            }
