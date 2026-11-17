import { createReadStream, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { askFlutterFix, corpusStatus, migrationMap, validateDartSnippet } from "./tools.js";

const root = resolve(fileURLToPath(new URL(".", import.meta.url)));
const maxRequestBytes = 1_100_000;
const staticFiles = new Set(["index.html", "app.js", "styles.css"]);
const mimeTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8"
};

function respondJson(response, status, value) {
  response.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store"
  });
  response.end(JSON.stringify(value));
}

async function readJsonBody(request) {
  if (!request.headers["content-type"]?.includes("application/json")) {
    throw Object.assign(new Error("Send a JSON request body."), { status: 415 });
  }
  const chunks = [];
  let bytes = 0;
  for await (const chunk of request) {
    bytes += chunk.length;
    if (bytes > maxRequestBytes) {
      request.resume();
      throw Object.assign(new Error("Request body exceeds the 1.1 MB limit."), { status: 413 });
    }
    chunks.push(chunk);
  }
  try {
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    throw Object.assign(new Error("Request body is not valid JSON."), { status: 400 });
  }
}

function isSdkConfigurationError(error) {
  return error instanceof Error && (
    error.message.startsWith("No Flutter ") ||
    error.message.startsWith("Configured SDK version") ||
    error.message.startsWith("Could not read the configured Flutter SDK")
  );
}

async function handleApi(request, response, pathname) {
  if (request.method === "GET" && pathname === "/api/status") {
    respondJson(response, 200, {
      corpus: await corpusStatus(),
      analyzerConfigured: Object.keys(process.env).some((key) => /^FLUTTER_SDK_\d+_\d+/.test(key))
    });
    return true;
  }
  const routes = {
    "/api/ask": (body) => askFlutterFix(body),
    "/api/migration-map": (body) => migrationMap(body),
    "/api/analyze": (body) => validateDartSnippet(body)
  };
  const action = routes[pathname];
  if (!action) return false;
  if (request.method !== "POST") {
    response.writeHead(405, { Allow: "POST" }).end("Method not allowed.");
    return true;
  }
  try {
    const body = await readJsonBody(request);
    const result = await action(body);
    if (pathname === "/api/analyze" && !result.passed) {
      respondJson(response, 422, result);
      return true;
    }
    respondJson(response, 200, result);
  } catch (error) {
    const status = error?.status ?? (isSdkConfigurationError(error) ? 503 : 400);
    respondJson(response, status, {
      error: error instanceof Error ? error.message : String(error)
    });
  }
  return true;
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url, "http://localhost");
  if (url.pathname.startsWith("/api/")) {
    try {
      if (await handleApi(request, response, url.pathname)) return;
      respondJson(response, 404, { error: "API endpoint not found." });
    } catch (error) {
      console.error(error instanceof Error ? error.message : String(error));
      respondJson(response, 500, { error: "The request could not be completed." });
    }
    return;
  }

  let relativePath;
  try {
    relativePath = url.pathname === "/" ? "index.html" : decodeURIComponent(url.pathname.slice(1));
  } catch {
    response.writeHead(400).end("Invalid URL.");
    return;
  }
  if (!staticFiles.has(relativePath)) {
    response.writeHead(404).end("Not found.");
    return;
  }
  const file = resolve(root, relativePath);
  if (file !== root && !file.startsWith(`${root}${sep}`)) {
    response.writeHead(403).end("Forbidden.");
    return;
  }
  try {
    const stats = statSync(file);
    if (!stats.isFile()) throw new Error("Not a file.");
    response.writeHead(200, {
      "Content-Type": mimeTypes[extname(file)] || "application/octet-stream",
      "X-Content-Type-Options": "nosniff"
    });
    createReadStream(file).pipe(response);
  } catch (error) {
    if (error?.code !== "ENOENT" && error?.code !== "ENOTDIR") {
      console.error(error instanceof Error ? error.message : String(error));
      response.writeHead(500).end("Could not read this file.");
      return;
    }
    response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" }).end("Not found.");
  }
});

const port = Number(process.env.PORT ?? 4173);
const host = process.env.HOST ?? "127.0.0.1";
server.listen(port, host, () => {
  console.log(`FlutterFix is available at http://${host}:${port}`);
});
