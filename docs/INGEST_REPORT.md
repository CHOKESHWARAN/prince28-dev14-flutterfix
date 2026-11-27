# FlutterFix – Background Ingestion & Worker Report

*Generated on: 2026-11-27 09:15:35 UTC*
*Environment: `local` | Concurrency: `2` | Target Pacing: `12.0 RPM`*

---

## 1. System Ingestion Summary

| Metric | Verified Value | Notes |
|---|---|---|
| **Total Ingested Documents** | **20** | Verified in PostgreSQL `documents` table |
| **Total Chunked Pages** | **48** | Verified in PostgreSQL `pages` table |
| **Document Types Breakdown** | `breaking_change`: 20 | Document classifications |
| **Total Ingest Jobs** | **2** | Created via `POST /v1/ingest` |
| **Processed Items (Done)** | **18** | Successfully fetched, parsed, and indexed |
| **Skipped Items** | **10** | Identical SHA-256 hashes skipped idempotently |
| **Dead-Letter Items** | **2** | Permanent failure after 3 tries |
| **Running / Queued** | 0 / 0 | Active Redis queue status |
| **Max Retry Attempts Observed** | **3** | Max retry attempts recorded on items |
| **Manifest Records** | **726** | Total crawled records in manifest |

---

## 2. LLM Gateway & Processing Metrics

| Metric | Value |
|---|---|
| **Total LLM Extractions** | **50** calls |
| **Input Tokens Processed** | **105,505** tokens |
| **Output Tokens Generated** | **7,083** tokens |
| **Total Extraction Cost** | **₹10.0405 INR** |
| **Parse Failures Logged** | **0** |

---

## 3. Worker Architecture & Crash Recovery Verification

- **Queue Engine**: Redis 7 + ARQ async worker with deterministic job IDs (`ingest_{item_id}`).
- **Pacing & Concurrency**: Regulated worker concurrency (`concurrency=2`) with exponential backoff.
- **Remote Raw Retrieval**: Worker resolves GitHub raw URLs using immutable Git commit hashes.
- **Crash Recovery Drill**:
  - 20 documents were queued in a single batch.
  - While 5 documents had completed and 2 were running, the worker process was terminated.
  - The API remained responsive with HTTP 200/202 throughout the event.
  - Upon restarting the worker, ARQ re-polled the in-flight items via visibility timeout.
  - All 20 items reached terminal states with **0 duplicates** and **0 lost items**.

---

## 4. Dead-Letter Queue Inspection

- **Endpoint**: `GET /v1/ingest/dead-letter`
- **Current Dead-Letter Count**: **2**
- **Failure Classification**:
  - Download errors (404 / connection timeout) after 3 attempts.
  - Documents with unparseable or corrupted text layers.
  - Invalid schema extractions that could not be repaired by the LLM gateway.

---

<!-- manual:start -->
## What I Learnt

## What I Learnt
<!-- manual:end -->
