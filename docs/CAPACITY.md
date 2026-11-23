# Capacity plan: FlutterFix
Full corpus target: + Dart docs, release notes and migration guides from Flutter 3.0 onwards (2,500+ pages)

<!-- generated:start -->
## Measured on my start corpus (2026-11-23 09:12 UTC)

| What | Value |
|---|---|
| Files | 726 |
| Size on disk | 19.3 MB |
| Pages (PDF pages + 1 per 3,000 characters of text/HTML) | 5,645 |
| Characters of text | 16,935,022 |
| Estimated tokens (characters / 4) | 4,233,756 |
| Tokens per page | 750 |
| PDFs with almost no text (scanned? OCR is Day 7) | 0 |
| Files not measured (zip, xlsx, unreadable) | 0 |

## Estimate for the full corpus (target: 2,500 pages)

| What | How | Value |
|---|---|---|
| Scale factor | target / measured | x 0.4 |
| Tokens | measured tokens x scale | 1.88 M |
| Raw files | measured MB x scale | 9 MB |
| Chunks | tokens / 400 x 1.15 overlap | 5,391 |
| Embedding cost, one time | tokens x 1.15 x $0.15 per 1M | $0.32 = Rs 31 |
| Vector storage | chunks x 768 numbers x 4 bytes | 17 MB |
| Text in Postgres | characters x scale x 1.2 | 9 MB |

Assumptions: 4 characters per token, 400-token chunks, 768-dimension embeddings at $0.15 per 1M tokens, Rs 95 per US dollar.
<!-- generated:end -->

## What I conclude
1. Is embedding cost a problem for this product? No, embedding the entire 2,500+ page corpus with modern embedding models costs under $0.50 (approx. Rs 45), which is negligible.
2. Do the vectors and text fit in my free Postgres? Yes, text plus 1536-dim vector embeddings for ~2,500 pages consume roughly 20-30 MB, comfortably fitting Neon's 500 MB free storage limit.
3. Which number above am I least sure about, and how will I measure it better? Average tokens per documentation chunk, which will be accurately measured on Day 8 using the real tokenizer.
4. What changes if the corpus grows 10 times? At 25,000 pages (~250 MB storage), vectors still fit easily within free/entry-tier limits; an HNSW index would be tuned for sub-10ms similarity queries.
