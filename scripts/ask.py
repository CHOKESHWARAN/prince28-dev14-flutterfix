"""Ask FlutterFix and print server-sent events or a JSON answer."""

import argparse
import json
import time

import httpx


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("message")
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    started = time.perf_counter()
    with httpx.Client(timeout=120) as client:
        response = client.post(
            args.url.rstrip("/") + "/v1/chat",
            json={"message": args.message, "stream": not args.json},
        )
        response.raise_for_status()
        if args.json:
            print(json.dumps(response.json(), ensure_ascii=False, indent=2))
            return
        first = None
        summary = {}
        for line in response.iter_lines():
            if not line:
                continue
            if line.startswith("event: "):
                event = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
                if event == "done":
                    summary = data
                elif event == "error":
                    raise RuntimeError(data.get("detail"))
                else:
                    if first is None:
                        first = time.perf_counter() - started
                    print(data.get("delta", ""), end="", flush=True)
        elapsed = time.perf_counter() - started
        first_delay = first or 0
        print(
            f"\n--- {summary.get('provider')} / {summary.get('model')}: "
            f"first words after {first_delay:.2f} s, total {elapsed:.2f} s"
        )
        fallback = "YES" if summary.get("fallback_used") else "no"
        print(
            f"tokens in={summary.get('tokens_in')} out={summary.get('tokens_out')} "
            f"cost Rs {summary.get('cost_inr')} attempts={summary.get('attempts')} "
            f"fallback={fallback}"
        )


if __name__ == "__main__":
    main()
