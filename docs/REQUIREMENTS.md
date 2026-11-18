# Requirements: FlutterFix

## Functional (what it does)

1. A user can ask a question in plain English and get an answer drawn from official Flutter and Dart documentation and breaking-changes guides.
2. Every answer cites the document and page (or breaking-change URL) it came from.
3. If the documents do not contain the answer (such as app crash triage without logs), the product says "I don't know" instead of guessing.
4. Signature feature: Migration map: paste pubspec.yaml and a widget file and see each deprecated API with its replacement, the breaking-change page, and the Flutter version where it changed.
5. A user can browse and search the underlying records through GET /v1/documents.

## Non-functional (how well, with numbers)

| # | Quality | Target | How I will measure it |
|---|---|---|---|
| 1 | Speed: record lookups | p95 under 500 ms for GET /v1/documents | load test (Week 6) |
| 2 | Speed: answers | p95 under 4 s for a full answer; first token under 1.5 s | traces (Week 5) |
| 3 | Accuracy | 90%+ of 30 code answers pass dart analyze on the target SDK; correct breaking-change citation for 90%+ of 40 questions. | golden question set (Weeks 4 and 5) |
| 4 | Cost | under Rs 1.00 per answered question | llm_calls table (Week 2) |
| 5 | Availability | 99% monthly uptime of the live URL | uptime monitor from Day 5 |
