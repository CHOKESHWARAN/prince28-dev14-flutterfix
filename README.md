# FlutterFix

FlutterFix retrieves passages from the official Flutter, Dart, and API documentation for a selected Flutter target version. Its migration map detects a bounded set of known API changes in pasted `pubspec.yaml` and Dart source, links findings to official guidance, and can look up latest package metadata on pub.dev.

## Requirements

- Node.js 18.17 or newer.
- Internet access when refreshing the documentation index or checking package metadata.
- A local Flutter SDK for the exact target version when analyzing Dart source.

## Run locally

```powershell
npm test
npm run docs:sync
npm start
```

Open <http://127.0.0.1:4173>. The documentation index is generated at `data/official-docs.json` and is intentionally gitignored; refresh it with `npm run docs:sync`. The app reports when the index is missing rather than silently presenting stale or fixed answers.

## Target-SDK analysis

Configure each installed SDK using an environment variable whose suffix matches the target version's major and minor numbers. For example, in PowerShell:

```powershell
$env:FLUTTER_SDK_3_50 = 'D:\flutter-sdk\flutter'
npm start
```

The analyzer checks the configured SDK version before running `dart analyze` in a temporary Flutter package. It analyzes only the supplied widget file in that isolated package; it does not analyze the complete app, resolve its dependencies, run tests, or certify package compatibility. Snippets are not generated from retrieved documentation passages. Do not treat this feature as a project-wide build check.

## HTTP API

- `GET /api/status` — documentation index and analyzer configuration status.
- `POST /api/ask` — retrieve version-filtered passages and citations. JSON fields: `question`, `fromVersion`, `targetVersion`.
- `POST /api/migration-map` — map known API patterns and check latest pub.dev package metadata. JSON fields: `pubspec`, `widget`, `fromVersion`, `targetVersion`.
- `POST /api/analyze` — run target-SDK analysis on supplied Dart source. JSON fields: `source`, `targetVersion`.

The server binds to `127.0.0.1` by default. `PORT` and `HOST` can be set for a deployment. Do not expose an unauthenticated instance to the public internet: pasted source is sent to the server, and the analyzer runs SDK commands on its host.

## MCP server

Run `node mcp-server.mjs` as an MCP stdio server. For a VS Code workspace configuration, add this to `.vscode/mcp.json`:

```json
{
  "servers": {
    "flutterfix": {
      "type": "stdio",
      "command": "node",
      "args": ["${workspaceFolder}/mcp-server.mjs"]
    }
  }
}
```

The server exposes `flutterfix.ask`, `flutterfix.migration_map`, `flutterfix.analyze_snippet`, and `flutterfix.docs_status`. Set the documentation-index and SDK environment variables in the MCP server process as needed.

## Scope and limitations

- Search is local BM25 retrieval, not a generative model. Answers show retrieved passages with links to their source pages and are version-filtered when the source page identifies a stable release.
- The migration map is a checklist for recognized patterns, not a complete migration plan or Flutter analyzer. It cannot infer app behavior from a widget in isolation.
- Package checks query the latest pub.dev package metadata, not the app's lockfile-resolved versions. SDK-constraint compatibility is an estimate and must be confirmed against each package's release notes and the target SDK.
- Flutter stable version options and the Dart-version mapping in `pub-lookup.js` must be refreshed when Flutter changes its releases.
- `npm run evaluate:citations` tests 40 representative retrieval queries against expected official pages. This local benchmark is evidence about retrieval on this corpus, not a guarantee of citation accuracy for every question.

## Documentation attribution

Each retrieved passage is displayed with its title and a link to the original page. Flutter website content is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); Flutter marks are excluded. Dart documentation and API reference content are subject to their own terms; consult the linked page. The full generated index is local-only and is not included in this repository.
