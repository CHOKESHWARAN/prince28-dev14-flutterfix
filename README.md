# FlutterFix

A Flutter and Dart mentor that answers from the official docs and breaking-change pages for the user's Flutter version.

**Status:** Day 1 foundation (FastAPI skeleton, quality gates). Live URL from Day 5.

## Who it's for

Mobile developer at a Coimbatore agency maintaining a Flutter 2 app for a textile shop that must move to the latest Flutter to meet a Play Store target-SDK deadline.

## The problem

Flutter and Dart change fast: null safety, Material 3 defaults, deprecated widgets and new Android build rules. Online tutorials target old versions, and the right fix depends on the exact SDK version. FlutterFix helps mobile developers systematically migrate legacy Flutter codebases, identify deprecated APIs with official breaking-change guides, and ensure code snippets pass analyzer checks on target Flutter versions.

## Data sources

docs.flutter.dev content (flutter/website repository), Flutter breaking-changes and migration guides, Dart language docs (dart.dev), Flutter and Dart release notes.

- https://docs.flutter.dev/
- https://docs.flutter.dev/release/breaking-changes
- https://github.com/flutter/website
- https://dart.dev/
- Terms: Flutter and Dart site content CC BY 4.0 (Flutter marks excluded); attribute and link the source page.

## Hardest problem (my interview story)

Version-aware migration: answers must match the app's Flutter/Dart version, follow the breaking-change page from the old API to the new one, and every code snippet must pass dart analyze on the target SDK before it is shown.

## Signature feature

Migration map: paste pubspec.yaml and a widget file and see each deprecated API with its replacement, the breaking-change page and the Flutter version where it changed.

## Target metric

90%+ of 30 code answers pass dart analyze on the target SDK; correct breaking-change citation for 90%+ of 40 questions.

## Run it locally

```bash
uv sync
copy .env.example .env
uv run uvicorn flutterfix.api.main:create_app --factory --reload
```

Then open http://localhost:8000/docs

## Checks

```bash
uv run pytest
uv run ruff check .
```
