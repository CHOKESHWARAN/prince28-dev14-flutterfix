import { spawn } from "node:child_process";
import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const MAX_SOURCE_LENGTH = 16_000;
const PROCESS_TIMEOUT_MS = 120_000;
const MAX_OUTPUT_LENGTH = 128_000;

function getSdkLocation(targetVersion) {
  const key = `FLUTTER_SDK_${targetVersion.split(".").slice(0, 2).join("_")}`;
  const sdkRoot = process.env[key];
  if (!sdkRoot) {
    throw new Error(
      `No Flutter ${targetVersion} SDK is configured. Install that SDK and set ${key} to its installation folder to enable target-version analysis.`
    );
  }
  const executable = join(sdkRoot, "bin", process.platform === "win32" ? "flutter.bat" : "flutter");
  return { executable, sdkRoot };
}

function run(executable, args, cwd, timeoutMs = PROCESS_TIMEOUT_MS) {
  return new Promise((resolve, reject) => {
    const child = spawn(executable, args, {
      cwd,
      windowsHide: true,
      shell: process.platform === "win32"
    });
    let stdout = "";
    let stderr = "";
    const append = (current, chunk) => `${current}${chunk.toString()}`.slice(-MAX_OUTPUT_LENGTH);
    child.stdout.on("data", (chunk) => { stdout = append(stdout, chunk); });
    child.stderr.on("data", (chunk) => { stderr = append(stderr, chunk); });
    const timer = setTimeout(() => {
      child.kill();
      reject(new Error(`Analyzer command timed out after ${timeoutMs / 1000} seconds.`));
    }, timeoutMs);
    child.once("error", (error) => {
      clearTimeout(timer);
      reject(error);
    });
    child.once("close", (code, signal) => {
      clearTimeout(timer);
      resolve({ code, signal, stdout, stderr });
    });
  });
}

function readFrameworkVersion(raw) {
  try {
    const value = JSON.parse(raw);
    return typeof value.frameworkVersion === "string" ? value.frameworkVersion : null;
  } catch {
    return null;
  }
}

export async function analyzeSnippet({ source, targetVersion }) {
  if (typeof source !== "string" || !source.trim()) {
    throw new Error("Provide Dart source code to analyze.");
  }
  if (source.length > MAX_SOURCE_LENGTH) {
    throw new Error(`Dart source must be ${MAX_SOURCE_LENGTH} characters or fewer.`);
  }
  if (source.includes("\u0000")) throw new Error("Dart source cannot contain NUL characters.");
  if (typeof targetVersion !== "string" || !/^\d+\.\d+(?:\.\d+)?$/.test(targetVersion)) {
    throw new Error("Target Flutter version must be a major.minor or major.minor.patch version.");
  }
  const { executable, sdkRoot } = getSdkLocation(targetVersion);
  const versionResult = await run(executable, ["--version", "--machine"], process.cwd(), 20_000);
  if (versionResult.code !== 0) {
    throw new Error(`Could not read the configured Flutter SDK version: ${versionResult.stderr || versionResult.stdout}`);
  }
  const frameworkVersion = readFrameworkVersion(versionResult.stdout);
  if (!frameworkVersion || !frameworkVersion.startsWith(`${targetVersion.split(".").slice(0, 2).join(".")}.`)) {
    throw new Error(`Configured SDK version ${frameworkVersion ?? "unknown"} does not match the requested Flutter ${targetVersion}.`);
  }

  const project = await mkdtemp(join(tmpdir(), "flutterfix-analyze-"));
  try {
    await mkdir(join(project, "lib"));
    await writeFile(join(project, "pubspec.yaml"), [
      "name: flutterfix_snippet_validation",
      "publish_to: none",
      "environment:",
      "  sdk: '>=2.12.0 <4.0.0'",
      "dependencies:",
      "  flutter:",
      "    sdk: flutter",
      ""
    ].join("\n"));
    await writeFile(join(project, "lib", "snippet.dart"), source);
    const pubResult = await run(executable, ["pub", "get", "--offline"], project);
    if (pubResult.code !== 0) {
      throw new Error(`Flutter SDK package setup failed: ${pubResult.stderr || pubResult.stdout}`);
    }
    const dart = join(sdkRoot, "bin", process.platform === "win32" ? "dart.exe" : "dart");
    const analysis = await run(dart, ["analyze", "--fatal-infos", "--fatal-warnings", "lib/snippet.dart"], project);
    return {
      analyzed: true,
      passed: analysis.code === 0,
      targetVersion: frameworkVersion,
      command: "dart analyze --fatal-infos --fatal-warnings lib/snippet.dart",
      output: `${analysis.stdout}${analysis.stderr}`.trim(),
      exitCode: analysis.code
    };
  } finally {
    await rm(project, { recursive: true, force: true });
  }
}
