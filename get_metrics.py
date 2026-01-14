#!/usr/bin/env python3
"""Helper script to fetch and display metrics in a readable format."""

import json
import sys
import requests
from datetime import datetime

def get_metrics(base_url="http://localhost:5000"):
    """Fetch metrics from the API."""
    try:
        response = requests.get(f"{base_url}/metrics", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching metrics: {e}")
        print(f"\nMake sure your app is running at {base_url}")
        sys.exit(1)

def print_metrics(metrics_data):
    """Print metrics in a readable format."""
    print("=" * 80)
    print("📊 LINEUP PERFORMANCE METRICS")
    print("=" * 80)
    print(f"Timestamp: {metrics_data.get('timestamp', 'N/A')}\n")
    
    # Summary
    summary = metrics_data.get('summary', {})
    print("📈 SUMMARY")
    print("-" * 80)
    print(f"Total Requests:     {summary.get('total_requests', 0):,}")
    print(f"Total Errors:       {summary.get('total_errors', 0):,}")
    print(f"Success Rate:       {summary.get('overall_success_rate', 0):.2f}%")
    print(f"Avg P95 Response:   {summary.get('avg_response_time_p95', 0):.2f}ms")
    print()
    
    # Cache Savings
    cache_summary = metrics_data.get('cache_summary', {})
    if cache_summary:
        print("💾 CACHE SAVINGS")
        print("-" * 80)
        for cache_name, data in cache_summary.items():
            print(f"\nCache: {cache_name}")
            print(f"  Hit Rate:              {data.get('hit_rate', 0):.2f}%")
            print(f"  API Calls Avoided:     {data.get('api_calls_avoided', 0):,}")
            print(f"  Total Time Saved:      {data.get('total_time_saved_seconds', 0):.2f} seconds")
            print(f"  Speedup Factor:        {data.get('speedup_factor', 0):.2f}x faster")
        print()
    
    # Endpoint Performance
    endpoints = metrics_data.get('endpoints', {})
    if endpoints:
        print("🔌 ENDPOINT PERFORMANCE")
        print("-" * 80)
        for endpoint, data in endpoints.items():
            print(f"\n{endpoint}:")
            print(f"  Requests:              {data.get('request_count', 0):,}")
            print(f"  Errors:                {data.get('error_count', 0):,}")
            print(f"  Success Rate:          {data.get('success_rate', 0):.2f}%")
            print(f"  Requests/min:          {data.get('requests_per_minute', 0):.2f}")
            
            rt = data.get('response_time', {})
            if rt.get('count', 0) > 0:
                print(f"  Response Times:")
                print(f"    P50:                {rt.get('p50', 0):.2f}ms")
                print(f"    P95:                {rt.get('p95', 0):.2f}ms")
                print(f"    P99:                {rt.get('p99', 0):.2f}ms")
                print(f"    Average:            {rt.get('avg', 0):.2f}ms")
        print()
    
    # External API Performance
    apis = metrics_data.get('external_apis', {})
    if apis:
        print("🌐 EXTERNAL API PERFORMANCE")
        print("-" * 80)
        for api_name, data in apis.items():
            if data.get('count', 0) > 0:
                print(f"\n{api_name}:")
                print(f"  Calls:                 {data.get('count', 0):,}")
                print(f"  Avg Latency:           {data.get('avg', 0):.2f}ms")
                print(f"  P95 Latency:           {data.get('p95', 0):.2f}ms")
                print(f"  Min:                   {data.get('min', 0):.2f}ms")
                print(f"  Max:                   {data.get('max', 0):.2f}ms")
        print()
    
    # Resume-Ready Metrics
    print("=" * 80)
    print("📝 RESUME-READY METRICS")
    print("=" * 80)
    
    if cache_summary:
        for cache_name, data in cache_summary.items():
            if data.get('api_calls_avoided', 0) > 0:
                print(f"\n✅ Cache Performance ({cache_name}):")
                print(f"   • Hit Rate: {data.get('hit_rate', 0):.1f}%")
                print(f"   • {data.get('api_calls_avoided', 0):,} API calls avoided")
                print(f"   • {data.get('total_time_saved_seconds', 0):.1f}s total time saved")
                if data.get('speedup_factor', 0) > 0:
                    print(f"   • {data.get('speedup_factor', 0):.1f}x faster than API calls")
    
    best_p95 = 0
    best_endpoint = None
    for endpoint, data in endpoints.items():
        p95 = data.get('response_time', {}).get('p95', 0)
        if p95 > 0 and (best_p95 == 0 or p95 < best_p95):
            best_p95 = p95
            best_endpoint = endpoint
    
    if best_endpoint and best_p95 > 0:
        print(f"\n✅ Response Time Performance:")
        print(f"   • Best P95: {best_p95:.0f}ms ({best_endpoint})")
        print(f"   • Overall Avg P95: {summary.get('avg_response_time_p95', 0):.0f}ms")
    
    if summary.get('overall_success_rate', 0) > 0:
        print(f"\n✅ Reliability:")
        print(f"   • Success Rate: {summary.get('overall_success_rate', 0):.1f}%")
        print(f"   • Total Requests: {summary.get('total_requests', 0):,}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    # Allow passing URL as argument
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
    
    print(f"🔍 Fetching metrics from {base_url}/metrics...\n")
    metrics = get_metrics(base_url)
    print_metrics(metrics)



