import test, { after } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const directory = await mkdtemp(join(tmpdir(), "flutterfix-retrieval-test-"));
process.env.FLUTTERFIX_DOC_INDEX = join(directory, "docs.json");

const corpus = {
  schemaVersion: 1,
  generatedAt: "2026-01-01T00:00:00.000Z",
  counts: { discovered: 3, indexed: 3, failed: 0, passages: 3 },
  sources: [],
  documents: [
    {
      title: "Android predictive back",
      url: "https://docs.flutter.dev/release/breaking-changes/android-predictive-back",
      source: "Flutter documentation",
      stableRelease: "3.12",
      chunks: [{ id: "pop-scope", text: "PopScope canPop callback predictive back gesture." }]
    },
    {
      title: "Material 3 future API",
      url: "https://docs.flutter.dev/release/breaking-changes/material-3-future-api",
      source: "Flutter documentation",
      stableRelease: "3.50",
      chunks: [{ id: "material-api", text: "PopScope predictive back Material 3 future API." }]
    },
    {
      title: "List",
      url: "https://api.dart.dev/dart-core/List-class.html",
      source: "Dart API reference",
      stableRelease: null,
      chunks: [{ id: "list-api", text: "An indexable collection with length and element access." }]
    }
  ]
};

await writeFile(process.env.FLUTTERFIX_DOC_INDEX, JSON.stringify(corpus));
const { searchDocs } = await import("../retrieval.js?retrieval-test");

after(async () => {
  await rm(directory, { recursive: true, force: true });
});

test("target version excludes documentation for a later stable release", async () => {
  const result = await searchDocs({
    query: "PopScope predictive back",
    fromVersion: "2.10",
    targetVersion: "3.12"
  });
  assert.ok(result.results.some((item) => item.url.endsWith("android-predictive-back")));
  assert.ok(result.results.every((item) => !item.url.endsWith("material-3-future-api")));
});

test("API-reference path terms are searchable and not assigned a false release version", async () => {
  const result = await searchDocs({
    query: "Dart core List API reference",
    fromVersion: "2.10",
    targetVersion: "3.12"
  });
  assert.ok(result.results.some((item) => item.url.endsWith("/dart-core/List-class.html")));
});
