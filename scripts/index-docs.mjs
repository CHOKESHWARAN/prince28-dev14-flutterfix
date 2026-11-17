import { mkdir, rename, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const OUTPUT = resolve(ROOT, "data", "official-docs.json");
const SITEMAPS = [
  { name: "Flutter documentation", url: "https://docs.flutter.dev/sitemap.xml", include: () => true },
  { name: "Dart documentation", url: "https://dart.dev/sitemap.xml", include: (url) => new URL(url).pathname !== "/robots.txt" },
  {
    name: "Flutter release notes",
    url: "https://flutter.dev/sitemap.xml",
    include: (url) => !new URL(url).pathname.startsWith("/showcase/notebooklm")
      && new URL(url).pathname !== "/create"
  }
];
const USER_AGENT = "FlutterFix-Documentation-Indexer/1.0";
const CONCURRENCY = 8;
const MAX_ATTEMPTS = 3;
const MAX_FAILURES = 15;
const API_REFERENCE_PAGES = [
  "https://api.flutter.dev/flutter/widgets/Widget-class.html",
  "https://api.flutter.dev/flutter/widgets/StatelessWidget-class.html",
  "https://api.flutter.dev/flutter/widgets/StatefulWidget-class.html",
  "https://api.flutter.dev/flutter/widgets/State-class.html",
  "https://api.flutter.dev/flutter/widgets/BuildContext-class.html",
  "https://api.flutter.dev/flutter/widgets/InheritedWidget-class.html",
  "https://api.flutter.dev/flutter/widgets/PopScope-class.html",
  "https://api.flutter.dev/flutter/widgets/WillPopScope-class.html",
  "https://api.flutter.dev/flutter/widgets/Navigator-class.html",
  "https://api.flutter.dev/flutter/widgets/Form-class.html",
  "https://api.flutter.dev/flutter/widgets/StatefulBuilder-class.html",
  "https://api.flutter.dev/flutter/material/MaterialApp-class.html",
  "https://api.flutter.dev/flutter/material/Scaffold-class.html",
  "https://api.flutter.dev/flutter/material/ThemeData-class.html",
  "https://api.flutter.dev/flutter/material/ColorScheme-class.html",
  "https://api.flutter.dev/flutter/material/TextButton-class.html",
  "https://api.flutter.dev/flutter/material/ElevatedButton-class.html",
  "https://api.flutter.dev/flutter/material/OutlinedButton-class.html",
  "https://api.flutter.dev/flutter/material/FilledButton-class.html",
  "https://api.flutter.dev/flutter/material/AppBar-class.html",
  "https://api.flutter.dev/flutter/material/NavigationBar-class.html",
  "https://api.flutter.dev/flutter/material/BottomNavigationBar-class.html",
  "https://api.flutter.dev/flutter/material/TextField-class.html",
  "https://api.flutter.dev/flutter/material/Theme-class.html",
  "https://api.flutter.dev/flutter/widgets/WidgetStateProperty-class.html",
  "https://api.flutter.dev/flutter/material/ButtonStyle-class.html",
  "https://api.flutter.dev/flutter/foundation/Key-class.html",
  "https://api.flutter.dev/flutter/services/MethodChannel-class.html",
  "https://api.flutter.dev/flutter/animation/AnimationController-class.html",
  "https://api.flutter.dev/flutter/rendering/RenderObject-class.html",
  "https://api.flutter.dev/flutter/painting/BoxDecoration-class.html",
  "https://api.flutter.dev/flutter/widgets/FutureBuilder-class.html",
  "https://api.flutter.dev/flutter/widgets/StreamBuilder-class.html",
  "https://api.dart.dev/dart-core/Object-class.html",
  "https://api.dart.dev/dart-core/String-class.html",
  "https://api.dart.dev/dart-core/num-class.html",
  "https://api.dart.dev/dart-core/int-class.html",
  "https://api.dart.dev/dart-core/List-class.html",
  "https://api.dart.dev/dart-core/Iterable-class.html",
  "https://api.dart.dev/dart-core/Map-class.html",
  "https://api.dart.dev/dart-async/Future-class.html",
  "https://api.dart.dev/dart-async/Stream-class.html",
  "https://api.dart.dev/dart-async/Timer-class.html",
  "https://api.dart.dev/dart-collection/Queue-class.html",
  "https://api.dart.dev/dart-convert/json-constant.html"
];

function decodeEntities(value) {
  const named = { amp: "&", apos: "'", gt: ">", lt: "<", nbsp: " ", quot: '"' };
  return value
    .replace(/&(#x[\da-f]+|#\d+|[a-z]+);/gi, (whole, entity) => {
      if (entity[0] !== "#") return named[entity.toLowerCase()] ?? whole;
      const codePoint = entity[1].toLowerCase() === "x"
        ? Number.parseInt(entity.slice(2), 16)
        : Number.parseInt(entity.slice(1), 10);
      return Number.isFinite(codePoint) && codePoint <= 0x10ffff
        ? String.fromCodePoint(codePoint)
        : whole;
    });
}

function extractContent(html) {
  const title = decodeEntities(
    html.match(/<h1\b[^>]*>([\s\S]*?)<\/h1>/i)?.[1]
      ?.replace(/<[^>]+>/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      ?? html.match(/<title\b[^>]*>([\s\S]*?)<\/title>/i)?.[1]
        ?.replace(/<[^>]+>/g, " ")
        .replace(/\s+/g, " ")
        .trim()
      ?? ""
  );
  const main = html.match(/<main\b[^>]*>([\s\S]*?)<\/main>/i)?.[1]
    ?? html.match(/<article\b[^>]*>([\s\S]*?)<\/article>/i)?.[1]
    ?? html;
  const text = decodeEntities(
    main
      .replace(/<(script|style|noscript|svg|iframe|pre)\b[^>]*>[\s\S]*?<\/\1>/gi, " ")
      .replace(/<(nav|footer)\b[^>]*>[\s\S]*?<\/\1>/gi, " ")
      .replace(/<(h[1-6]|p|li|tr|blockquote|pre)\b[^>]*>/gi, "\n")
      .replace(/<\/(h[1-6]|p|li|tr|blockquote|pre|section|article|div|table)>/gi, "\n")
      .replace(/<br\s*\/?>/gi, "\n")
      .replace(/<[^>]+>/g, " ")
      .replace(/[\t \u00a0]+/g, " ")
      .replace(/\n\s+/g, "\n")
      .replace(/\n{3,}/g, "\n\n")
      .trim()
  );
  return { title, text };
}

function getChunks(title, text) {
  const paragraphs = text.split(/\n+/).map((part) => part.trim()).filter(Boolean);
  const chunks = [];
  let current = "";
  for (const paragraph of paragraphs) {
    if (paragraph.length > 1500) {
      if (current) chunks.push(current);
      current = "";
      for (let offset = 0; offset < paragraph.length; offset += 1200) {
        chunks.push(paragraph.slice(offset, offset + 1200));
      }
      continue;
    }
    if (current && current.length + paragraph.length + 1 > 1200) {
      chunks.push(current);
      current = "";
    }
    current = current ? `${current}\n${paragraph}` : paragraph;
  }
  if (current) chunks.push(current);
  return chunks.filter((chunk) => chunk.length > 80).map((textPart, index) => ({
    id: `${title.toLowerCase().replace(/[^a-z0-9]+/g, "-").slice(0, 40)}-${index + 1}`,
    text: textPart
  }));
}

function stableVersion(text) {
  const matches = [
    /in stable release\s*:\s*v?(\d+\.\d+(?:\.\d+)?)/i,
    /stable release\s*:\s*v?(\d+\.\d+(?:\.\d+)?)/i
  ];
  for (const pattern of matches) {
    const version = text.match(pattern)?.[1];
    if (version) return version;
  }
  return null;
}

async function fetchText(url) {
  let lastError;
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt += 1) {
    try {
      const response = await fetch(url, {
        headers: { "User-Agent": USER_AGENT },
        signal: AbortSignal.timeout(20000),
        redirect: "follow"
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.text();
    } catch (error) {
      lastError = error;
      if (attempt < MAX_ATTEMPTS) {
        await new Promise((resolveWait) => setTimeout(resolveWait, attempt * 500));
      }
    }
  }
  throw new Error(`${url}: ${lastError instanceof Error ? lastError.message : String(lastError)}`);
}

async function getSitemapPages(sitemap) {
  const xml = await fetchText(sitemap.url);
  const pages = [];
  for (const block of xml.matchAll(/<url\b[^>]*>([\s\S]*?)<\/url>/gi)) {
    const url = decodeEntities(block[1].match(/<loc>([\s\S]*?)<\/loc>/i)?.[1]?.trim() ?? "");
    if (!url || !sitemap.include(url)) continue;
    const lastmod = block[1].match(/<lastmod>([\s\S]*?)<\/lastmod>/i)?.[1]?.trim() ?? null;
    pages.push({ url: new URL(url).href, source: sitemap.name, lastmod });
  }
  return pages;
}

async function indexPage(page) {
  const html = await fetchText(page.url);
  const { title, text } = extractContent(html);
  if (!title || text.length < 100) throw new Error(`${page.url}: no usable article content`);
  const chunks = getChunks(title, text);
  if (!chunks.length) throw new Error(`${page.url}: no searchable passages`);
  return {
    id: page.url,
    url: page.url,
    title,
    source: page.source,
    lastmod: page.lastmod,
    stableRelease: stableVersion(text),
    content: text,
    chunks
  };
}

async function main() {
  const sitemapResults = await Promise.all(SITEMAPS.map(async (sitemap) => ({
    name: sitemap.name,
    pages: await getSitemapPages(sitemap)
  })));
  const uniquePages = new Map();
  for (const result of sitemapResults) {
    for (const page of result.pages) uniquePages.set(page.url, page);
  }
  for (const url of API_REFERENCE_PAGES) {
    const source = url.includes("api.dart.dev") ? "Dart API reference" : "Flutter API reference";
    uniquePages.set(url, { url, source, lastmod: null, stableRelease: "3.50" });
  }
  const pages = [...uniquePages.values()];
  if (!pages.length) throw new Error("Official documentation sitemaps contained no eligible pages.");
  console.log(`Indexing ${pages.length} official pages (concurrency ${CONCURRENCY}).`);

  const documents = [];
  const failures = [];
  let next = 0;
  let completed = 0;
  async function worker() {
    while (true) {
      const index = next;
      next += 1;
      if (index >= pages.length) return;
      const page = pages[index];
      try {
        documents.push(await indexPage(page));
      } catch (error) {
        failures.push(error instanceof Error ? error.message : String(error));
      }
      completed += 1;
      if (completed % 100 === 0 || completed === pages.length) {
        console.log(`${completed}/${pages.length} fetched; ${documents.length} indexed; ${failures.length} failed.`);
      }
    }
  }
  await Promise.all(Array.from({ length: CONCURRENCY }, () => worker()));
  const failureReport = failures.slice(0, 20);
  if (failures.length > MAX_FAILURES) {
    throw new Error(
      `Index incomplete: ${failures.length} pages failed (limit ${MAX_FAILURES}). First failures:\n${failureReport.join("\n")}`
    );
  }
  const corpus = {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    counts: {
      discovered: pages.length,
      indexed: documents.length,
      failed: failures.length,
      passages: documents.reduce((sum, document) => sum + document.chunks.length, 0)
    },
    sources: SITEMAPS.map(({ name, url }) => ({ name, url })),
    failures: failureReport,
    documents: documents.sort((a, b) => a.url.localeCompare(b.url))
  };
  await mkdir(dirname(OUTPUT), { recursive: true });
  const temporary = `${OUTPUT}.tmp`;
  await writeFile(temporary, JSON.stringify(corpus));
  await rename(temporary, OUTPUT);
  console.log(`Saved ${corpus.counts.indexed} pages and ${corpus.counts.passages} passages to ${OUTPUT}.`);
  if (failures.length) console.warn(`Skipped ${failures.length} unavailable pages; rerun npm run docs:sync to retry.`);
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
});
