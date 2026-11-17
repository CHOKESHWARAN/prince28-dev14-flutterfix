# FlutterFix

FlutterFix is a version-aware Flutter and Dart mentor prototype. It answers a small set of common questions from curated, paraphrased official documentation and provides a local migration map for known Flutter APIs.

## Run locally

Requires Node.js 18 or later. No third-party npm packages are used.

```powershell
npm test
npm start
```

Open <http://127.0.0.1:4173>.

## Current scope

- Select a source and target Flutter version for mentor answers.
- Ask about widget types, null safety, Material 3, common migrations, state management, or a crash.
- See official Flutter/Dart documentation links with each grounded answer.
- Paste `pubspec.yaml` and Dart widget source to detect known button and back-navigation APIs, a pre-Dart-3 SDK constraint, and dependencies needing manual compatibility checks.
- Pasted code is analyzed in the browser and is not uploaded.

The migration map is not a Flutter analyzer, full package compatibility scanner, or complete migration plan. It reports only indexed patterns, and package null-safety/SDK compatibility must be confirmed from package metadata and changelogs. The prototype intentionally does not generate Dart code: snippets should not be shown until they have been analyzed with the exact target Flutter/Dart SDK. Flutter and Dart are not required to run this prototype, but this means no target-SDK analysis is performed here.

The initial source catalog includes Flutter widget, Material 3, standalone Material/Cupertino package, button, Android predictive-back, state-management, debugging, and Dart null-safety documentation. The interface labels Flutter 3.50 as current stable based on the official Flutter documentation checked on November 17, 2026. Update this version and refresh the source catalog as stable releases change.

## Attribution

Explanations are original paraphrases, not copied documentation. Consult and cite the linked official source pages for the full guidance. Flutter website content is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); Flutter marks are excluded. Dart documentation has its own licensing terms.
