"""CLI script to trigger background document ingestion via API."""

import argparse
import sys
import time

import httpx

from flutterfix.config import get_settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Trigger background document ingestion")
    parser.add_argument("--limit", type=int, default=10, help="Number of documents to queue")
    parser.add_argument("--source", type=str, default=None, help="Filter by source")
    parser.add_argument("--retry-failed", action="store_true", help="Retry failed items")
    parser.add_argument(
        "--base-url", type=str, default="http://localhost:8000", help="API base URL"
    )
    parser.add_argument("--token", type=str, default="", help="Admin token for X-Admin-Token")
    parser.add_argument(
        "--poll", action="store_true", default=True, help="Poll until job completes"
    )
    args = parser.parse_args()

    settings = get_settings()
    token = args.token or settings.admin_token.get_secret_value()

    print("=" * 60)
    print("FlutterFix Document Ingestion Trigger")
    print(f"Target:     {args.base_url}")
    print(f"Limit:      {args.limit}")
    print(f"Source:     {args.source or 'all'}")
    print("=" * 60)

    headers = {"X-Admin-Token": token}
    payload = {
        "limit": args.limit,
        "source": args.source,
        "retry_failed": args.retry_failed,
    }

    try:
        with httpx.Client(base_url=args.base_url, timeout=30.0) as client:
            resp = client.post("/v1/ingest", json=payload, headers=headers)
            if resp.status_code != 202:
                print(f"[ERROR] Ingest request rejected: HTTP {resp.status_code} - {resp.text}")
                return 1

            data = resp.json()
            job_id = data["job_id"]
            queued = data.get("queued", 0)
            print(f"[OK] Ingest job accepted: ID={job_id}, Queued={queued}")

            if not args.poll or queued == 0:
                return 0

            print("\nPolling job progress...")
            while True:
                prog_resp = client.get(f"/v1/ingest/{job_id}", headers=headers)
                if prog_resp.status_code != 200:
                    print(f"[ERROR] Could not fetch job progress: HTTP {prog_resp.status_code}")
                    break

                prog = prog_resp.json()
                total = prog["total_requested"]
                done = prog["done"]
                skipped = prog["skipped"]
                failed = prog["failed"]
                running = prog["running"]
                queued_now = prog["queued"]
                pages = prog["pages"]

                finished = done + skipped + failed
                print(
                    f"Progress: [{finished}/{total}] done={done} skipped={skipped} "
                    f"failed={failed} running={running} queued={queued_now} pages={pages}",
                    flush=True,
                )

                if finished >= total:
                    print(f"\n[DONE] Ingest job {job_id} completed successfully!")
                    print(
                        f"Summary: {done} done, {skipped} skipped, "
                        f"{failed} failed across {pages} pages."
                    )
                    break

                time.sleep(2.0)

    except Exception as exc:
        print(f"[ERROR] Failed to communicate with API: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
