import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { corpusStatus, searchDocs } from "../retrieval.js";

const root = resolve(fileURLToPath(new URL("..", import.meta.url)));
const cases = JSON.parse(await readFile(resolve(root, "evals", "citation-questions.json"), "utf8"));
const status = await corpusStatus();
if (!status.indexed) {
  throw new Error(status.message);
}
const indexPath = resolve(process.env.FLUTTERFIX_DOC_INDEX || resolve(root, "data", "official-docs.json"));
const indexedCorpus = JSON.parse(await readFile(indexPath, "utf8"));
let correct = 0;
const failures = [];
for (const [index, item] of cases.entries()) {
  const expectedPages = indexedCorpus.documents.filter((document) => item.source.startsWith("http")
    ? document.url === item.source
    : document.url.includes(item.source));
  if (expectedPages.length !== 1) {
    throw new Error(`Question ${index + 1} expected source "${item.source}" matched ${expectedPages.length} indexed pages.`);
  }
  const result = await searchDocs({
    query: item.question,
    fromVersion: "2.10",
    targetVersion: "3.50",
    limit: 7
  });
  const matched = result.results.some((source) => source.url === expectedPages[0].url);
  if (matched) {
    correct += 1;
  } else {
    failures.push({
      number: index + 1,
      question: item.question,
      expected: item.source,
      topSources: result.results.slice(0, 3).map((source) => source.url)
    });
  }
}
const rate = correct / cases.length;
console.log(`Citation retrieval: ${correct}/${cases.length} (${(rate * 100).toFixed(1)}%); target 90%.`);
for (const failure of failures) {
  console.log(`\n${failure.number}. ${failure.question}\n  Expected: ${failure.expected}\n  Retrieved: ${failure.topSources.join(", ") || "none"}`);
}
if (rate < 0.9) process.exitCode = 1;
