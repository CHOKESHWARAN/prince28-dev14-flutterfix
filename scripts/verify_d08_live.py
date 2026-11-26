#!/usr/bin/env python3
"""Verification script for D08 live deployment and usage tracking.

Usage:
    uv run python scripts/verify_d08_live.py [--wait]
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

import httpx

EXPECTED_SHA = "987b59e6d04eea9405270661a12cfc75b9869dbd"
BASE_URL = "https://prince28-dev14-flutterfix.onrender.com"


def get_health() -> dict:
    url = f"{BASE_URL}/health"
    req = urllib.request.Request(url, headers={"User-Agent": "D08-Verifier"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def get_usage() -> dict:
    url = f"{BASE_URL}/v1/usage"
    req = urllib.request.Request(url, headers={"User-Agent": "D08-Verifier"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def test_chat(question: str) -> httpx.Response:
    url = f"{BASE_URL}/v1/chat"
    payload = {"message": question, "stream": False}
    return httpx.post(url, json=payload, timeout=60.0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait", action="store_true", help="Wait for expected SHA to deploy")
    parser.add_argument("--max-retries", type=int, default=30)
    parser.add_argument("--delay", type=int, default=10)
    args = parser.parse_args()

    print("=" * 60)
    print("FlutterFix D08 Live Deployment & Usage Verifier")
    print(f"Target URL:     {BASE_URL}")
    print(f"Expected SHA:   {EXPECTED_SHA[:7]}")
    print("=" * 60)

    # 1. Health check
    if args.wait:
        print("Polling /health until expected commit is live...")
        deployed = False
        for attempt in range(1, args.max_retries + 1):
            try:
                h = get_health()
                actual_sha = h.get("commit") or h.get("version") or ""
                short_actual = actual_sha[:7] if actual_sha else "None"
                print(f"Attempt {attempt}/{args.max_retries}: Live SHA = {short_actual}")
                if actual_sha.startswith(EXPECTED_SHA[:7]) or actual_sha == EXPECTED_SHA:
                    deployed = True
                    break
            except Exception as e:
                print(f"Attempt {attempt}/{args.max_retries}: Error {e}")
            time.sleep(args.delay)

        if not deployed:
            print(f"[FAIL] Expected commit {EXPECTED_SHA[:7]} not deployed within timeout.")
            return 1
    else:
        try:
            h = get_health()
            actual_sha = h.get("commit") or h.get("version") or ""
            print(f"Live /health commit SHA: {actual_sha}")
            if not actual_sha.startswith(EXPECTED_SHA[:7]):
                print(f"[WARN] Live SHA {actual_sha[:7]} != expected {EXPECTED_SHA[:7]}")
        except Exception as e:
            print(f"[ERROR] /health probe failed: {e}")
            return 1

    # 2. Check /v1/usage
    print("\nChecking /v1/usage...")
    try:
        u_before = get_usage()
        print(f"[PASS] /v1/usage responded: {u_before}")
    except urllib.error.HTTPError as e:
        print(f"[FAIL] /v1/usage returned HTTP {e.code}: {e.reason}")
        if e.code == 404:
            print("       -> The deployed version on Render does not have D08 routes yet.")
        return 1

    # 3. Call /v1/chat
    question = "How do I migrate FlatButton in Flutter 3.24?"
    print(f"\nSending real question to /v1/chat: '{question}'...")
    try:
        resp = test_chat(question)
        print(f"Response status: HTTP {resp.status_code}")
        if resp.status_code == 200:
            chat_data = resp.json()
            ans = chat_data.get("answer", "")[:150]
            print(f"Answer: {ans}...")
            print(f"Provider: {chat_data.get('provider')} | Model: {chat_data.get('model')}")
            tok_in = chat_data.get("tokens_in")
            tok_out = chat_data.get("tokens_out")
            print(f"Tokens in: {tok_in} | Tokens out: {tok_out}")
            print(f"Cost INR: Rs {chat_data.get('cost_inr')}")
        else:
            print(f"Error detail: {resp.text}")
    except Exception as e:
        print(f"Chat request failed: {e}")

    # 4. Check /v1/usage after call
    print("\nChecking /v1/usage after call...")
    try:
        u_after = get_usage()
        print(f"[PASS] /v1/usage: {u_after}")
    except Exception as e:
        print(f"Usage check error: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
