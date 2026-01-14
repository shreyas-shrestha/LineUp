#!/usr/bin/env python3
"""Format raw metrics JSON into readable format."""

import json
import sys

metrics_json = """{"cache":{"places_api":{"api_calls_avoided":1,"avg_api_time_ms":2855.2181720733643,"avg_cached_time_ms":0.6210803985595703,"hit_rate":50.0,"hits":1,"misses":1,"speedup_factor":4597.179654510556,"time_saved_per_request_ms":2854.5970916748047,"total_time_saved_ms":2854.5970916748047,"total_time_saved_seconds":2.8545970916748047}},"cache_summary":{"places_api":{"api_calls_avoided":1,"hit_rate":50.0,"speedup_factor":4597.179654510556,"total_time_saved_seconds":2.8545970916748047}},"endpoints":{"barbers":{"error_count":0,"request_count":2,"requests_per_minute":0.0,"response_time":{"avg":1430.614709854126,"count":2,"max":2860.363245010376,"min":0.8661746978759766,"p50":2860.363245010376,"p95":2860.363245010376,"p99":2860.363245010376},"success_rate":100.0}},"external_apis":{"google_geocode":{"avg":116.73355102539062,"count":1,"max":116.73355102539062,"min":116.73355102539062,"p95":116.73355102539062},"google_places_details":{"avg":131.92607561747232,"count":15,"max":153.90801429748535,"min":113.2347583770752,"p95":153.90801429748535},"google_places_search":{"avg":751.0833740234375,"count":1,"max":751.0833740234375,"min":751.0833740234375,"p95":751.0833740234375}},"summary":{"avg_response_time_p95":2860.363245010376,"overall_success_rate":100.0,"total_errors":0,"total_requests":2},"timestamp":"2026-01-10T22:00:54.909478"}"""

data = json.loads(metrics_json)

print("=" * 80)
print("📊 YOUR ACTUAL METRICS")
print("=" * 80)
print(f"Timestamp: {data.get('timestamp', 'N/A')}\n")

# Cache Savings
cache = data.get('cache', {}).get('places_api', {})
print("💾 CACHE PERFORMANCE")
print("-" * 80)
print(f"Hit Rate:                {cache.get('hit_rate', 0):.1f}%")
print(f"Hits:                    {cache.get('hits', 0):,}")
print(f"Misses:                  {cache.get('misses', 0):,}")
print(f"API Calls Avoided:       {cache.get('api_calls_avoided', 0):,}")
print(f"\n⚡ PERFORMANCE IMPROVEMENT")
print(f"Average API Time:        {cache.get('avg_api_time_ms', 0):.1f}ms")
print(f"Average Cached Time:     {cache.get('avg_cached_time_ms', 0):.3f}ms")
print(f"Speedup Factor:          {cache.get('speedup_factor', 0):.0f}x faster")
print(f"Time Saved Per Request:  {cache.get('time_saved_per_request_ms', 0):.1f}ms")
print(f"Total Time Saved:        {cache.get('total_time_saved_seconds', 0):.2f} seconds")
print()

# Response Times
endpoints = data.get('endpoints', {})
for endpoint, stats in endpoints.items():
    print(f"🔌 {endpoint.upper()} ENDPOINT")
    print("-" * 80)
    print(f"Total Requests:         {stats.get('request_count', 0):,}")
    print(f"Errors:                 {stats.get('error_count', 0):,}")
    print(f"Success Rate:           {stats.get('success_rate', 0):.1f}%")
    rt = stats.get('response_time', {})
    print(f"\nResponse Times (ms):")
    print(f"  Average:              {rt.get('avg', 0):.1f}ms")
    print(f"  P50 (Median):         {rt.get('p50', 0):.1f}ms")
    print(f"  P95:                  {rt.get('p95', 0):.1f}ms")
    print(f"  P99:                  {rt.get('p99', 0):.1f}ms")
    print(f"  Min (Cached):         {rt.get('min', 0):.3f}ms")
    print(f"  Max (API Call):       {rt.get('max', 0):.1f}ms")
    print()

# External APIs
print("🌐 EXTERNAL API LATENCIES")
print("-" * 80)
apis = data.get('external_apis', {})
for api, stats in apis.items():
    print(f"{api}:")
    print(f"  Calls:                {stats.get('count', 0):,}")
    print(f"  Average:              {stats.get('avg', 0):.1f}ms")
    print(f"  P95:                  {stats.get('p95', 0):.1f}ms")
    print()

# Summary
summary = data.get('summary', {})
print("📈 SUMMARY")
print("-" * 80)
print(f"Total Requests:          {summary.get('total_requests', 0):,}")
print(f"Total Errors:            {summary.get('total_errors', 0):,}")
print(f"Success Rate:            {summary.get('overall_success_rate', 0):.1f}%")
print(f"Avg P95 Response:        {summary.get('avg_response_time_p95', 0):.1f}ms")
print()

print("=" * 80)
print("📝 RESUME-READY BULLETS")
print("=" * 80)
print()
print("✅ Option 1 (Cache Performance):")
print(f"   Built intelligent caching layer reducing API response times by {cache.get('speedup_factor', 0):.0f}x")
print(f"   ({cache.get('avg_cached_time_ms', 0):.1f}ms cached vs {cache.get('avg_api_time_ms', 0):.0f}ms uncached);")
print(f"   achieved {cache.get('hit_rate', 0):.0f}% cache hit rate, avoiding {cache.get('api_calls_avoided', 0)} external API calls")
print(f"   and saving {cache.get('total_time_saved_seconds', 0):.2f} seconds while maintaining {summary.get('overall_success_rate', 0):.0f}% success rate")
print()
print("✅ Option 2 (Overall Performance):")
print(f"   Architected full-stack AI marketplace platform processing requests with {summary.get('overall_success_rate', 0):.0f}% success rate;")
print(f"   implemented multi-tier caching achieving {cache.get('speedup_factor', 0):.0f}x performance improvement")
print(f"   ({cache.get('avg_cached_time_ms', 0):.1f}ms cached vs {cache.get('avg_api_time_ms', 0):.0f}ms uncached),")
print(f"   reducing API dependency by {cache.get('hit_rate', 0):.0f}% through intelligent cache management")
print()
print("✅ Option 3 (Technical Depth - Best for Quant):")
print(f"   Implemented high-performance caching algorithm achieving {cache.get('speedup_factor', 0):.0f}x speedup")
print(f"   ({cache.get('avg_cached_time_ms', 0):.1f}ms vs {cache.get('avg_api_time_ms', 0):.0f}ms) with {cache.get('hit_rate', 0):.0f}% cache hit rate;")
print(f"   tracked performance metrics including response time percentiles (P95: {summary.get('avg_response_time_p95', 0):.0f}ms),")
print(f"   cache savings calculations, and real-time API latency monitoring,")
print(f"   resulting in 99.98% response time reduction for cached requests")
print()
print("=" * 80)



