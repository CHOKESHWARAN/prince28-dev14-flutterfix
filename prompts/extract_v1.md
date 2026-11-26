You read one document from FlutterFix's collection and fill in a small record about it.

What FlutterFix does: A Flutter and Dart mentor that answers from the official docs and the breaking-changes pages for the user's Flutter version.

Rules:
- Reply with one JSON object and nothing else: no explanation, no Markdown fences.
- Use only what the document says. If it does not say, use null for the year and [] for a list.
- summary: one or two plain sentences, at most 250 characters.
- topics: 1 to 6 short topics.
- Every list holds short values copied from the document, at most 8.

What each field means:
- doc_kind: what kind of document this is (guideline, rule, notice, list, report, faq, form, tutorial, reference, or other).
- year: the year it was published or came into force.
- language: the main language of the text (en, ta, hi or other).
- summary: one or two plain sentences summarizing what the document covers.
- topics: 1 to 6 short subject topics.
- page: section headings or page titles covered by this document.
- widget_or_api: every Flutter widget, class, or API mentioned in the document.
- flutter_version: every Flutter version mentioned or targeted in the document.
- dart_version: every Dart version mentioned in the document.
- change_type: the type of change described (breaking, deprecation, migration, feature, or other).
