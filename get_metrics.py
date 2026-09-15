#!/usr/bin/env python3
"""Print GET /metrics as a table. Usage: python get_metrics.py [base_url]

Sends LINEUP_ADMIN_TOKEN as X-Admin-Token; without it the route is 404 in
production (see require_ops_access in lineup_backend/routes/system.py).
"""

import os
import sys

import requests


def get_metrics(base_url="http://localhost:5000"):
    try:
        headers = {}
        admin_token = os.environ.get("LINEUP_ADMIN_TOKEN")
        if admin_token:
            headers["X-Admin-Token"] = admin_token
        response = requests.get(f"{base_url}/metrics", timeout=10, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching metrics: {e}")
        print(f"\nMake sure your app is running at {base_url}")
        sys.exit(1)


def print_metrics(metrics_data):
    print("=" * 80)
    print("LineUp performance metrics")
    print("=" * 80)
    print(f"Timestamp: {metrics_data.get('timestamp', 'N/A')}\n")

    summary = metrics_data.get('summary', {})
    print("Summary")
    print("-" * 80)
    print(f"Total requests:     {summary.get('total_requests', 0):,}")
    print(f"Total errors:       {summary.get('total_errors', 0):,}")
    print(f"Success rate:       {summary.get('overall_success_rate', 0):.2f}%")
    print(f"Avg p95 response:   {summary.get('avg_response_time_p95', 0):.2f}ms")
    print()

    cache_summary = metrics_data.get('cache_summary', {})
    if cache_summary:
        print("Cache savings")
        print("-" * 80)
        for cache_name, data in cache_summary.items():
            print(f"\nCache: {cache_name}")
            print(f"  Hit rate:              {data.get('hit_rate', 0):.2f}%")
            print(f"  API calls avoided:     {data.get('api_calls_avoided', 0):,}")
            print(f"  Total time saved:      {data.get('total_time_saved_seconds', 0):.2f} seconds")
            print(f"  Speedup factor:        {data.get('speedup_factor', 0):.2f}x faster")
        print()

    endpoints = metrics_data.get('endpoints', {})
    if endpoints:
        print("Endpoint performance")
        print("-" * 80)
        for endpoint, data in endpoints.items():
            print(f"\n{endpoint}:")
            print(f"  Requests:              {data.get('request_count', 0):,}")
            print(f"  Errors:                {data.get('error_count', 0):,}")
            print(f"  Success rate:          {data.get('success_rate', 0):.2f}%")
            print(f"  Requests/min:          {data.get('requests_per_minute', 0):.2f}")

            rt = data.get('response_time', {})
            if rt.get('count', 0) > 0:
                print("  Response times:")
                print(f"    p50:                {rt.get('p50', 0):.2f}ms")
                print(f"    p95:                {rt.get('p95', 0):.2f}ms")
                print(f"    p99:                {rt.get('p99', 0):.2f}ms")
                print(f"    Average:            {rt.get('avg', 0):.2f}ms")
        print()

    apis = metrics_data.get('external_apis', {})
    if apis:
        print("External API performance")
        print("-" * 80)
        for api_name, data in apis.items():
            if data.get('count', 0) > 0:
                print(f"\n{api_name}:")
                print(f"  Calls:                 {data.get('count', 0):,}")
                print(f"  Avg latency:           {data.get('avg', 0):.2f}ms")
                print(f"  p95 latency:           {data.get('p95', 0):.2f}ms")
                print(f"  Min:                   {data.get('min', 0):.2f}ms")
                print(f"  Max:                   {data.get('max', 0):.2f}ms")
        print()

    print("=" * 80)


if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
    print(f"Fetching metrics from {base_url}/metrics\n")
    print_metrics(get_metrics(base_url))
