import test from "node:test";
import assert from "node:assert/strict";
import { inspectPubspecPackages } from "../pub-lookup.js";

test("package compatibility respects caret upper bounds and skips the Flutter SDK dependency", async () => {
  const originalFetch = globalThis.fetch;
  const requests = [];
  globalThis.fetch = async (url) => {
    const name = new URL(url).pathname.split("/").pop();
    requests.push(name);
    const constraint = {
      legacy_package: "^2.7.0",
      null_safe_old_package: "^2.12.0",
      current_package: "^3.0.0",
      unconstrained_package: "any"
    }[name];
    return new Response(JSON.stringify({
      latest: {
        version: "1.2.3",
        pubspec: { environment: { sdk: constraint } }
      }
    }), { status: 200, headers: { "Content-Type": "application/json" } });
  };
  try {
    const result = await inspectPubspecPackages(
      [
        "dependencies:",
        "  flutter:",
        "    sdk: flutter",
        "  legacy_package: ^1.0.0",
        "  null_safe_old_package: ^1.0.0",
        "  current_package: ^1.0.0",
        "  unconstrained_package: ^1.0.0"
      ].join("\n"),
      "3.50"
    );
    assert.equal(result.targetDartVersion, "3.14.0");
    assert.equal(result.checked, 4);
    assert.deepEqual(requests.sort(), ["current_package", "legacy_package", "null_safe_old_package", "unconstrained_package"]);
    assert.equal(result.packages.find((item) => item.name === "legacy_package").nullSafety, "needs-review");
    assert.equal(result.packages.find((item) => item.name === "null_safe_old_package").nullSafety, "sound-null-safe");
    assert.equal(result.packages.find((item) => item.name === "null_safe_old_package").compatibleWithTargetDart, false);
    assert.equal(result.packages.find((item) => item.name === "current_package").compatibleWithTargetDart, true);
    assert.equal(result.packages.find((item) => item.name === "unconstrained_package").compatibleWithTargetDart, null);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
