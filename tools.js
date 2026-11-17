import { analyzeSnippet } from "./analyzer.js";
import { findMigrations } from "./app.js";
import { inspectPubspecPackages } from "./pub-lookup.js";
import { compareFlutterVersions, corpusStatus, searchDocs } from "./retrieval.js";

const VERSION_PATTERN = /^\d+\.\d+(?:\.\d+)?$/;

function validateVersions(fromVersion, targetVersion) {
  if (typeof fromVersion !== "string" || typeof targetVersion !== "string"
    || !VERSION_PATTERN.test(fromVersion) || !VERSION_PATTERN.test(targetVersion)) {
    throw new Error("Provide source and target Flutter versions as major.minor or major.minor.patch values.");
  }
  if (compareFlutterVersions(fromVersion, targetVersion) > 0) {
    throw new Error("The source Flutter version must not be newer than the target version.");
  }
}

export async function askFlutterFix({ question, fromVersion, targetVersion }) {
  if (typeof question !== "string" || !question.trim()) throw new Error("Enter a Flutter or Dart question.");
  if (question.length > 2000) throw new Error("Questions must be 2,000 characters or fewer.");
  validateVersions(fromVersion, targetVersion);
  const indexStatus = await corpusStatus();
  if (!indexStatus.indexed) {
    return {
      sourceVersion: fromVersion,
      targetVersion,
      grounded: false,
      answer: indexStatus.message,
      results: [],
      corpus: indexStatus,
      warning: indexStatus.message
    };
  }
  const retrieved = await searchDocs({
    query: question.trim(),
    fromVersion,
    targetVersion,
    limit: 7
  });
  const confident = retrieved.results.length > 0 && retrieved.tokenCoverage >= 0.35;
  return {
    sourceVersion: fromVersion,
    targetVersion,
    answer: confident
      ? "The following passages are retrieved from official Flutter and Dart documentation relevant to your question. Read the cited pages for full context; the excerpts are not a substitute for checking your app with the target SDK."
      : "I could not find enough matching evidence in the indexed official documents to answer this confidently. Try different wording or check the cited sources directly.",
    grounded: confident,
    results: retrieved.results,
    corpus: retrieved.corpus,
    warning: retrieved.warning
  };
}

export async function migrationMap({ pubspec, widget, fromVersion, targetVersion }) {
  validateVersions(fromVersion, targetVersion);
  if (typeof pubspec !== "string" || typeof widget !== "string") {
    throw new Error("Provide pubspec.yaml and widget source as text.");
  }
  if (pubspec.length + widget.length > 1_000_000) {
    throw new Error("The combined pubspec and widget source must be 1 MB or smaller.");
  }
  const findings = findMigrations(pubspec, widget, fromVersion, targetVersion);
  const indexStatus = await corpusStatus();
  const sourceResults = [];
  for (const finding of indexStatus.indexed ? findings : []) {
    const matches = await searchDocs({
      query: `${finding.title} ${finding.replacement} migration Flutter ${targetVersion}`,
      fromVersion,
      targetVersion,
      limit: 3
    });
    sourceResults.push({
      finding: finding.id,
      sources: matches.results.slice(0, 2).map(({ title, url, stableRelease, passage }) => ({
        title, url, stableRelease, passage
      }))
    });
  }
  return {
    sourceVersion: fromVersion,
    targetVersion,
    findings,
    sources: sourceResults,
    packages: await inspectPubspecPackages(pubspec, targetVersion),
    corpus: indexStatus,
    notice: "This map detects known patterns and retrieves related documentation. It does not replace flutter analyze, package compatibility checks, or tests on the target SDK."
  };
}

export async function validateDartSnippet({ source, targetVersion }) {
  return analyzeSnippet({ source, targetVersion });
}

export { corpusStatus };
