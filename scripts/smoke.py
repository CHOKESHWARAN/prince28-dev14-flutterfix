#!/usr/bin/env python3
"""Smoke test script for FlutterFix live deployment verification.

Verifies:
1. /health returns HTTP 200 and matches expected commit SHA.
2. /ready returns HTTP 200 and indicates status 'ready' with database connected.
3. /v1/documents?limit=1 returns HTTP 200 with valid document items.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request


def check_health(base_url: str, expected_sha: str | None = None) -> tuple[bool, str]:
    url = f"{base_url.rstrip('/')}/health"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FlutterFix-SmokeTest/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != 200:
                return False, f"Expected HTTP 200 from /health, got {resp.status}"
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") != "ok":
                return False, f"Expected status 'ok' in /health, got {data.get('status')}"
            actual_sha = data.get("commit") or data.get("version")
            if expected_sha and actual_sha != expected_sha:
                return False, f"SHA mismatch: expected '{expected_sha}', got '{actual_sha}'"
            app_name = data.get("app")
            env_name = data.get("env")
            return (
                True,
                f"HTTP 200 OK (commit: {actual_sha}, app: {app_name}, env: {env_name})",
            )
    except Exception as e:
        return False, f"Request failed: {type(e).__name__}: {e}"


def check_ready(base_url: str) -> tuple[bool, str]:
    url = f"{base_url.rstrip('/')}/ready"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FlutterFix-SmokeTest/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != 200:
                return False, f"Expected HTTP 200 from /ready, got {resp.status}"
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") != "ready":
                return False, f"Expected status 'ready' in /ready, got {data.get('status')}"
            checks = data.get("checks", {})
            if not checks.get("database"):
                return False, "Database check failed in /ready"
            if not checks.get("records_loaded"):
                return False, "Records loaded check failed in /ready"
            return True, f"HTTP 200 OK (status: ready, checks: {checks})"
    except Exception as e:
        return False, f"Request failed: {type(e).__name__}: {e}"


def check_documents(base_url: str) -> tuple[bool, str]:
    url = f"{base_url.rstrip('/')}/v1/documents?limit=1"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FlutterFix-SmokeTest/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != 200:
                return False, f"Expected HTTP 200 from /v1/documents, got {resp.status}"
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("items", [])
            total = data.get("total", 0)
            if not isinstance(items, list) or len(items) == 0:
                return False, f"Expected at least 1 item in /v1/documents, got {len(items)}"
            return (
                True,
                f"HTTP 200 OK (total records: {total}, first item ID: '{items[0].get('id')}')",
            )
    except Exception as e:
        return False, f"Request failed: {type(e).__name__}: {e}"


def main() -> int:
    parser = argparse.ArgumentParser(description="FlutterFix smoke test suite")
    parser.add_argument(
        "--url",
        default=os.getenv("LIVE_URL", "https://prince28-dev14-flutterfix.onrender.com"),
        help="Base service URL to test",
    )
    parser.add_argument(
        "--expected-sha",
        default=os.getenv("EXPECTED_SHA"),
        help="Expected commit SHA for /health",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Poll /health until expected SHA is reported or timeout is reached",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=36,
        help="Maximum retry attempts when waiting (default: 36)",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=10,
        help="Seconds between retries when waiting (default: 10)",
    )
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    print("=" * 60)
    print("FlutterFix Deployment Smoke Test")
    print(f"Target URL:    {base_url}")
    print(f"Expected SHA:  {args.expected_sha or 'Any'}")
    print("=" * 60)

    # 1. Health check with optional polling
    if args.wait and args.expected_sha:
        print(f"Waiting for deployment of commit {args.expected_sha}...")
        healthy = False
        health_msg = ""
        for attempt in range(1, args.max_retries + 1):
            healthy, health_msg = check_health(base_url, args.expected_sha)
            if healthy:
                print(f"[OK] Attempt {attempt}: {health_msg}")
                break
            print(f"[RETRY {attempt}/{args.max_retries}] {health_msg} — waiting {args.delay}s...")
            time.sleep(args.delay)

        if not healthy:
            print(
                f"[FAIL] /health verification failed after {args.max_retries} attempts:\n"
                f"       {health_msg}",
                file=sys.stderr,
            )
            return 1
    else:
        ok, msg = check_health(base_url, args.expected_sha)
        if not ok:
            print(f"[FAIL] /health: {msg}", file=sys.stderr)
            return 1
        print(f"[PASS] /health: {msg}")

    # 2. Readiness check
    ready_ok, ready_msg = check_ready(base_url)
    if not ready_ok:
        print(f"[FAIL] /ready: {ready_msg}", file=sys.stderr)
        return 1
    print(f"[PASS] /ready: {ready_msg}")

    # 3. Documents API check
    docs_ok, docs_msg = check_documents(base_url)
    if not docs_ok:
        print(f"[FAIL] /v1/documents: {docs_msg}", file=sys.stderr)
        return 1
    print(f"[PASS] /v1/documents: {docs_msg}")

    print("=" * 60)
    print("All smoke test checks PASSED successfully.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
