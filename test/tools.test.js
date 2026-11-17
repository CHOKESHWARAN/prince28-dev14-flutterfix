import test from "node:test";
import assert from "node:assert/strict";
import { askFlutterFix } from "../tools.js";

test("questions reject a source Flutter version newer than their target", async () => {
  await assert.rejects(
    askFlutterFix({
      question: "What changed?",
      fromVersion: "3.50",
      targetVersion: "3.12"
    }),
    /source Flutter version must not be newer/
  );
});
