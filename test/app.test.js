import test from "node:test";
import assert from "node:assert/strict";
import { findMigrations, getAnswer } from "../app.js";

test("Material 3 answer explains the default boundary and cites its migration guide", () => {
  const answer = getAnswer("What changed when Material 3 became the default?", "3.50");
  assert.match(answer.text, /3\.16/);
  assert.deepEqual(answer.sources, ["material"]);
});

test("Material 3 answer distinguishes targets before the default change", () => {
  const answer = getAnswer("Explain useMaterial3", "3.12");
  assert.match(answer.text, /newer than your selected target/);
});

test("migration answer states the selected source and target SDKs", () => {
  const answer = getAnswer("Our Flutter 2.10 app uses old APIs", "3.50", "2.10");
  assert.match(answer.text, /Flutter 2\.10 → Flutter 3\.50/);
});

test("migration map detects APIs, SDK/package risks, and the Flutter 3.50 design-library change", () => {
  const findings = findMigrations(
    "environment:\n  sdk: '>=2.16.0 <3.0.0'\ndependencies:\n  flutter:\n    sdk: flutter\n  provider: ^5.0.0",
    "import 'package:flutter/material.dart';\nFlatButton(child: Text('Buy'))\nWillPopScope(child: child)",
    "2.10",
    "3.50"
  );
  assert.deepEqual(findings.map(({ id }) => id), [
    "dart-sdk-constraint",
    "flat-button",
    "will-pop-scope",
    "material-library-import",
    "package-compatibility"
  ]);
  assert.equal(findings.find(({ id }) => id === "will-pop-scope").replacement, "PopScope");
});

test("migration map distinguishes changes already present from changes in the upgrade", () => {
  const findings = findMigrations(
    "",
    "WillPopScope(child: child)\nimport 'package:flutter/material.dart';",
    "3.16",
    "3.50"
  );
  assert.equal(findings.find(({ id }) => id === "will-pop-scope").status, "already relevant at source version");
  assert.equal(findings.find(({ id }) => id === "material-library-import").status, "introduced within this upgrade");
});

test("migration map does not report changes newer than the selected target", () => {
  const findings = findMigrations("", "WillPopScope(child: child)", "2.10", "3.10");
  assert.equal(findings.length, 0);
});

test("unsupported questions do not invent an answer or citation", () => {
  const answer = getAnswer("Which textile shop POS should I use?", "3.50");
  assert.match(answer.text, /don’t have a sufficiently grounded answer/);
  assert.deepEqual(answer.sources, ["breaking"]);
});
