import { readFile, stat } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(fileURLToPath(new URL(".", import.meta.url)));
const INDEX_PATH = resolve(ROOT, process.env.FLUTTERFIX_DOC_INDEX || "data/official-docs.json");
const WORD = /[\p{L}\p{N}_]+/gu;
const STOP_WORDS = new Set([
  "a", "an", "and", "are", "as", "at", "be", "but", "by", "can", "for", "from",
  "how", "in", "into", "is", "it", "of", "on", "or", "that", "the", "this", "to",
  "was", "what", "when", "where", "which", "with", "you", "your"
]);

let corpusPromise;
let corpusMtime;
let searchIndex;

export function tokenize(value) {
  const raw = value.match(WORD) ?? [];
  const tokens = raw.flatMap((token) => [
    token.toLocaleLowerCase(),
    ...(token.match(/[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)/g) ?? []).map((part) => part.toLocaleLowerCase())
  ]);
  return tokens.filter((token) => token.length > 1 && !STOP_WORDS.has(token));
}

function compareVersions(left, right) {
  const a = left.split(".").map(Number);
  const b = right.split(".").map(Number);
  for (let index = 0; index < Math.max(a.length, b.length); index += 1) {
    const difference = (a[index] || 0) - (b[index] || 0);
    if (difference) return difference;
  }
  return 0;
}

async function loadCorpus() {
  const fileStat = await stat(INDEX_PATH);
  if (corpusPromise && fileStat.mtimeMs === corpusMtime) return corpusPromise;
  corpusMtime = fileStat.mtimeMs;
  searchIndex = null;
  corpusPromise = readFile(INDEX_PATH, "utf8").then((raw) => {
    const corpus = JSON.parse(raw);
    if (corpus.schemaVersion !== 1 || !Array.isArray(corpus.documents)) {
      throw new Error("The official documentation index has an unsupported format. Rebuild it with npm run docs:sync.");
    }
    return corpus;
  });
  return corpusPromise;
}

function buildSearchIndex(corpus) {
  const entries = [];
  const documentFrequency = new Map();
  for (const document of corpus.documents) {
    for (const chunk of document.chunks) {
      const terms = tokenize(`${document.title} ${document.url} ${chunk.text}`);
      const frequencies = new Map();
      for (const term of terms) frequencies.set(term, (frequencies.get(term) ?? 0) + 1);
      entries.push({ document, chunk, frequencies, length: terms.length });
      for (const term of frequencies.keys()) {
        documentFrequency.set(term, (documentFrequency.get(term) ?? 0) + 1);
      }
    }
  }
  const averageLength = entries.reduce((sum, entry) => sum + entry.length, 0) / Math.max(entries.length, 1);
  return { entries, documentFrequency, averageLength, count: entries.length };
}

export async function corpusStatus() {
  try {
    const corpus = await loadCorpus();
    return {
      indexed: true,
      generatedAt: corpus.generatedAt,
      counts: corpus.counts,
      sources: corpus.sources,
      failures: corpus.failures ?? []
    };
  } catch (error) {
    if (error?.code === "ENOENT") {
      return {
        indexed: false,
        message: "The documentation index has not been built. Run npm run docs:sync to fetch official pages."
      };
    }
    throw error;
  }
}

export async function searchDocs({ query, fromVersion, targetVersion, limit = 7 }) {
  const terms = [...new Set(tokenize(query))];
  if (!terms.length) return { results: [], corpus: await corpusStatus(), warning: "Enter a question with searchable terms." };
  const corpus = await loadCorpus();
  if (!searchIndex) searchIndex = buildSearchIndex(corpus);
  const { entries, documentFrequency, averageLength, count } = searchIndex;
  const results = [];
  const normalizedQuery = query.toLocaleLowerCase().replace(/[^\p{L}\p{N}_]+/gu, " ").trim();
  for (const entry of entries) {
    const release = entry.document.stableRelease;
    if (release && compareVersions(release, targetVersion) > 0) continue;
    const frequency = entry.frequencies;
    let score = 0;
    for (const term of terms) {
      const termFrequency = frequency.get(term) ?? 0;
      if (!termFrequency) continue;
      const idf = Math.log(1 + (count - (documentFrequency.get(term) ?? 0) + 0.5) / ((documentFrequency.get(term) ?? 0) + 0.5));
      const normalization = termFrequency + 1.2 * (0.25 + 0.75 * entry.length / Math.max(averageLength, 1));
      score += idf * termFrequency * 2.2 / normalization;
    }
    if (score <= 0) continue;
    const titleTerms = new Set(tokenize(entry.document.title));
    const titleBoost = terms.reduce((boost, term) => {
      if (!titleTerms.has(term)) return boost;
      const frequency = documentFrequency.get(term) ?? 0;
      const rarity = Math.log(1 + count / Math.max(frequency, 1));
      return boost + rarity * (term.length > 7 ? 2.5 : 1.25);
    }, 0);
    const normalizedTitle = entry.document.title.toLocaleLowerCase().replace(/[^\p{L}\p{N}_]+/gu, " ").trim();
    const phraseBoost = normalizedQuery.length > 4 && normalizedTitle.includes(normalizedQuery) ? 5 : 0;
    const sourceBoost = /breaking-changes|migration|release-notes|changelog/i.test(entry.document.url) ? 0.25 : 0;
    results.push({
      title: entry.document.title,
      url: entry.document.url,
      source: entry.document.source,
      lastmod: entry.document.lastmod,
      stableRelease: release,
      passage: entry.chunk.text,
      score: score + titleBoost + phraseBoost + sourceBoost
    });
  }
  results.sort((left, right) => right.score - left.score || left.url.localeCompare(right.url));
  const chosen = [];
  const seen = new Set();
  for (const result of results) {
    if (seen.has(result.url)) continue;
    if (fromVersion && result.stableRelease && compareVersions(result.stableRelease, fromVersion) <= 0) {
      result.temporalNote = `This guide is associated with Flutter ${result.stableRelease}, which is not newer than the source version ${fromVersion}.`;
    }
    seen.add(result.url);
    chosen.push(result);
    if (chosen.length >= Math.max(1, Math.min(limit, 10))) break;
  }
  const tokenCoverage = terms.filter((term) => chosen.some((result) => tokenize(result.passage).includes(term))).length / terms.length;
  return {
    results: chosen.map(({ score, ...result }) => result),
    corpus: {
      generatedAt: corpus.generatedAt,
      indexed: corpus.counts.indexed,
      discovered: corpus.counts.discovered,
      failed: corpus.counts.failed,
      passages: corpus.counts.passages
    },
    tokenCoverage,
    warning: chosen.length
      ? "These are retrieved official-document passages, not generated or target-SDK-analyzed code."
      : "No matching passage was found in the indexed official documents. Rephrase the question or refresh the documentation index."
  };
}

export function compareFlutterVersions(left, right) {
  return compareVersions(left, right);
}
