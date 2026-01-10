"""Base service class with common functionality."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class BaseService(ABC):
    """Base class for external service integrations."""

    def __init__(self):
        self._usage_tracker: Dict[str, int] = {}
        self._daily_reset: date = datetime.now().date()

    def _reset_daily_counters(self) -> None:
        """Reset usage counters if it's a new day."""
        today = datetime.now().date()
        if self._daily_reset != today:
            self._usage_tracker = {}
            self._daily_reset = today
            logger.info(f"{self.__class__.__name__}: Daily counters reset")

    def _increment_usage(self, operation: str = "calls") -> None:
        """Increment usage counter for an operation."""
        self._reset_daily_counters()
        self._usage_tracker[operation] = self._usage_tracker.get(operation, 0) + 1

    def _get_usage(self, operation: str = "calls") -> int:
        """Get current usage count for an operation."""
        self._reset_daily_counters()
        return self._usage_tracker.get(operation, 0)

    def _can_make_call(self, operation: str = "calls", limit: int = 100) -> bool:
        """Check if we can make another API call within the limit."""
        self._reset_daily_counters()
        return self._get_usage(operation) < limit

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the service is properly configured."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Return health/status information about the service."""
        pass


class CachedService(BaseService):
    """Base class for services with caching support."""

    def __init__(self, cache_duration: int = 3600, max_cache_size: int = 100):
        super().__init__()
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_duration = cache_duration
        self._max_cache_size = max_cache_size

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        import time
        
        if key not in self._cache:
            return None
        
        cached = self._cache[key]
        if time.time() - cached["timestamp"] >= self._cache_duration:
            del self._cache[key]
            return None
        
        return cached["data"]

    def _set_cache(self, key: str, data: Any) -> None:
        """Set cache value, respecting max size."""
        import time
        
        # Clean expired entries first
        self._clean_cache()
        
        # If still too large, remove oldest
        if len(self._cache) >= self._max_cache_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]["timestamp"])
            del self._cache[oldest_key]
        
        self._cache[key] = {
            "data": data,
            "timestamp": time.time(),
        }

    def _clean_cache(self) -> int:
        """Remove expired cache entries. Returns number of entries removed."""
        import time
        
        current_time = time.time()
        expired_keys = [
            key for key, value in self._cache.items()
            if current_time - value["timestamp"] >= self._cache_duration
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        return len(expired_keys)

    def clear_cache(self) -> int:
        """Clear all cache entries. Returns number of entries removed."""
        count = len(self._cache)
        self._cache.clear()
        return count

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self._max_cache_size,
            "duration_seconds": self._cache_duration,
        }

