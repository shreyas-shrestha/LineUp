"""Performance metrics collection and tracking."""

from __future__ import annotations

import time
import statistics
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import threading


class MetricsCollector:
    """Collects and aggregates performance metrics."""
    
    _instance: Optional['MetricsCollector'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Cache metrics
        self.cache_hits: Dict[str, int] = defaultdict(int)
        self.cache_misses: Dict[str, int] = defaultdict(int)
        
        # Cache savings tracking
        self.cache_time_saved_ms: Dict[str, float] = defaultdict(float)  # Total time saved
        self.api_call_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))  # Track API call durations
        self.cached_response_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))  # Track cached response times
        
        # Response time tracking (store last 1000 requests per endpoint)
        self.response_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Request counts
        self.request_counts: Dict[str, int] = defaultdict(int)
        self.error_counts: Dict[str, int] = defaultdict(int)
        
        # API call latencies
        self.api_latencies: Dict[str, deque] = defaultdict(lambda: deque(maxlen=500))
        
        # API calls avoided (due to cache)
        self.api_calls_avoided: Dict[str, int] = defaultdict(int)
        
        # Timestamps for request tracking
        self.request_timestamps: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        
        self._initialized = True
    
    def record_cache_hit(self, cache_name: str = "default", response_time_ms: Optional[float] = None):
        """Record a cache hit and track savings."""
        self.cache_hits[cache_name] += 1
        if response_time_ms is not None:
            self.cached_response_times[cache_name].append(response_time_ms)
        
        # Calculate savings: average API call time - cached response time
        if cache_name in self.api_call_times and len(self.api_call_times[cache_name]) > 0:
            avg_api_time = statistics.mean(self.api_call_times[cache_name])
            cached_time = response_time_ms or 0
            time_saved = max(0, avg_api_time - cached_time)
            self.cache_time_saved_ms[cache_name] += time_saved
            self.api_calls_avoided[cache_name] += 1
    
    def record_cache_miss(self, cache_name: str = "default"):
        """Record a cache miss."""
        self.cache_misses[cache_name] += 1
    
    def record_api_call_time(self, cache_name: str, duration_ms: float):
        """Record the time taken for an actual API call (used to calculate cache savings)."""
        self.api_call_times[cache_name].append(duration_ms)
    
    def record_response_time(self, endpoint: str, duration_ms: float):
        """Record response time in milliseconds."""
        self.response_times[endpoint].append(duration_ms)
        self.request_timestamps[endpoint].append(time.time())
    
    def record_request(self, endpoint: str, success: bool = True):
        """Record a request."""
        self.request_counts[endpoint] += 1
        if not success:
            self.error_counts[endpoint] += 1
    
    def record_api_latency(self, api_name: str, duration_ms: float):
        """Record external API call latency."""
        self.api_latencies[api_name].append(duration_ms)
    
    def get_cache_hit_rate(self, cache_name: str = "default") -> float:
        """Get cache hit rate as percentage."""
        hits = self.cache_hits.get(cache_name, 0)
        misses = self.cache_misses.get(cache_name, 0)
        total = hits + misses
        if total == 0:
            return 0.0
        return (hits / total) * 100.0
    
    def get_cache_savings(self, cache_name: str = "default") -> Dict[str, Any]:
        """Get cache savings metrics."""
        hits = self.cache_hits.get(cache_name, 0)
        misses = self.cache_misses.get(cache_name, 0)
        total_time_saved_ms = self.cache_time_saved_ms.get(cache_name, 0.0)
        api_calls_avoided = self.api_calls_avoided.get(cache_name, 0)
        
        avg_api_time = 0.0
        avg_cached_time = 0.0
        if cache_name in self.api_call_times and len(self.api_call_times[cache_name]) > 0:
            avg_api_time = statistics.mean(self.api_call_times[cache_name])
        if cache_name in self.cached_response_times and len(self.cached_response_times[cache_name]) > 0:
            avg_cached_time = statistics.mean(self.cached_response_times[cache_name])
        
        time_saved_per_request = avg_api_time - avg_cached_time if avg_api_time > 0 else 0.0
        speedup_factor = avg_api_time / avg_cached_time if avg_cached_time > 0 and avg_api_time > 0 else 0.0
        
        return {
            "hits": hits,
            "misses": misses,
            "hit_rate": self.get_cache_hit_rate(cache_name),
            "total_time_saved_ms": total_time_saved_ms,
            "total_time_saved_seconds": total_time_saved_ms / 1000.0,
            "api_calls_avoided": api_calls_avoided,
            "avg_api_time_ms": avg_api_time,
            "avg_cached_time_ms": avg_cached_time,
            "time_saved_per_request_ms": max(0, time_saved_per_request),
            "speedup_factor": speedup_factor if speedup_factor > 0 else 0.0
        }
    
    def get_response_time_stats(self, endpoint: str) -> Dict[str, float]:
        """Get response time statistics (p50, p95, p99, avg, min, max)."""
        times = list(self.response_times.get(endpoint, []))
        if not times:
            return {
                "count": 0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
                "avg": 0.0,
                "min": 0.0,
                "max": 0.0
            }
        
        times_sorted = sorted(times)
        n = len(times_sorted)
        
        return {
            "count": n,
            "p50": times_sorted[int(n * 0.50)],
            "p95": times_sorted[int(n * 0.95)] if n > 1 else times_sorted[0],
            "p99": times_sorted[int(n * 0.99)] if n > 2 else times_sorted[-1],
            "avg": statistics.mean(times),
            "min": min(times),
            "max": max(times)
        }
    
    def get_api_latency_stats(self, api_name: str) -> Dict[str, float]:
        """Get API latency statistics."""
        latencies = list(self.api_latencies.get(api_name, []))
        if not latencies:
            return {
                "count": 0,
                "avg": 0.0,
                "p95": 0.0,
                "min": 0.0,
                "max": 0.0
            }
        
        latencies_sorted = sorted(latencies)
        n = len(latencies_sorted)
        
        return {
            "count": n,
            "avg": statistics.mean(latencies),
            "p95": latencies_sorted[int(n * 0.95)] if n > 1 else latencies_sorted[0],
            "min": min(latencies),
            "max": max(latencies)
        }
    
    def get_success_rate(self, endpoint: str) -> float:
        """Get success rate as percentage."""
        total = self.request_counts.get(endpoint, 0)
        errors = self.error_counts.get(endpoint, 0)
        if total == 0:
            return 100.0
        return ((total - errors) / total) * 100.0
    
    def get_requests_per_minute(self, endpoint: str, minutes: int = 1) -> float:
        """Get requests per minute for the last N minutes."""
        timestamps = list(self.request_timestamps.get(endpoint, []))
        if not timestamps:
            return 0.0
        
        cutoff_time = time.time() - (minutes * 60)
        recent_requests = [ts for ts in timestamps if ts >= cutoff_time]
        return len(recent_requests) / minutes
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics in a structured format."""
        endpoints = set(self.request_counts.keys()) | set(self.response_times.keys())
        
        endpoint_metrics = {}
        for endpoint in endpoints:
            endpoint_metrics[endpoint] = {
                "request_count": self.request_counts.get(endpoint, 0),
                "error_count": self.error_counts.get(endpoint, 0),
                "success_rate": self.get_success_rate(endpoint),
                "response_time": self.get_response_time_stats(endpoint),
                "requests_per_minute": self.get_requests_per_minute(endpoint)
            }
        
        cache_names = set(self.cache_hits.keys()) | set(self.cache_misses.keys())
        cache_metrics = {}
        for cache_name in cache_names:
            cache_metrics[cache_name] = self.get_cache_savings(cache_name)
        
        api_names = set(self.api_latencies.keys())
        api_metrics = {}
        for api_name in api_names:
            api_metrics[api_name] = self.get_api_latency_stats(api_name)
        
        return {
            "endpoints": endpoint_metrics,
            "cache": cache_metrics,
            "external_apis": api_metrics,
            "timestamp": datetime.now().isoformat()
        }
    
    def reset(self):
        """Reset all metrics (useful for testing)."""
        self.cache_hits.clear()
        self.cache_misses.clear()
        self.cache_time_saved_ms.clear()
        self.api_call_times.clear()
        self.cached_response_times.clear()
        self.response_times.clear()
        self.request_counts.clear()
        self.error_counts.clear()
        self.api_latencies.clear()
        self.api_calls_avoided.clear()
        self.request_timestamps.clear()


# Global metrics collector instance
metrics = MetricsCollector()


# Decorator for tracking endpoint performance
def track_performance(endpoint_name: Optional[str] = None):
    """Decorator to track endpoint performance metrics."""
    def decorator(func):
        endpoint = endpoint_name or func.__name__
        
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                success = False
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                metrics.record_response_time(endpoint, duration_ms)
                metrics.record_request(endpoint, success=success)
        
        return wrapper
    return decorator

