import test from "node:test";
import assert from "node:assert/strict";
import { analyzeSnippet } from "../analyzer.js";

test("analyzer rejects empty source instead of returning a success-shaped result", async () => {
  await assert.rejects(
    analyzeSnippet({ source: "  ", targetVersion: "3.50" }),
    /Provide Dart source code/
  );
});

test("analyzer refuses to run when the requested SDK is not configured", {
  skip: Boolean(process.env.FLUTTER_SDK_99_99)
}, async () => {
  await assert.rejects(
    analyzeSnippet({ source: "void main() {}", targetVersion: "99.99" }),
    /No Flutter 99\.99 SDK is configured/
  );
});
