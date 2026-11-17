import { createInterface } from "node:readline";
import { askFlutterFix, corpusStatus, migrationMap, validateDartSnippet } from "./tools.js";

const serverInfo = { name: "flutterfix", version: "1.0.0" };
const tools = [
  {
    name: "flutterfix.ask",
    description: "Retrieve version-aware Flutter/Dart documentation passages with source links.",
    inputSchema: {
      type: "object",
      properties: {
        question: { type: "string", description: "Question about Flutter or Dart." },
        fromVersion: { type: "string", description: "Source Flutter version, such as 2.10." },
        targetVersion: { type: "string", description: "Target Flutter version, such as 3.50." }
      },
      required: ["question", "fromVersion", "targetVersion"],
      additionalProperties: false
    }
  },
  {
    name: "flutterfix.migration_map",
    description: "Map known deprecated Flutter APIs in a pubspec and widget source to replacements and official migration citations.",
    inputSchema: {
      type: "object",
      properties: {
        pubspec: { type: "string" },
        widget: { type: "string" },
        fromVersion: { type: "string" },
        targetVersion: { type: "string" }
      },
      required: ["pubspec", "widget", "fromVersion", "targetVersion"],
      additionalProperties: false
    }
  },
  {
    name: "flutterfix.analyze_snippet",
    description: "Run dart analyze on a temporary Flutter package using a locally configured SDK that matches the requested target version.",
    inputSchema: {
      type: "object",
      properties: {
        source: { type: "string", description: "Dart source to analyze in an isolated temporary package." },
        targetVersion: { type: "string", description: "Flutter SDK version, such as 3.50." }
      },
      required: ["source", "targetVersion"],
      additionalProperties: false
    }
  },
  {
    name: "flutterfix.docs_status",
    description: "Report the official-document corpus indexing status and indexed-page counts.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false }
  }
];

function reply(id, result) {
  process.stdout.write(`${JSON.stringify({ jsonrpc: "2.0", id, result })}\n`);
}

function errorReply(id, code, message) {
  process.stdout.write(`${JSON.stringify({ jsonrpc: "2.0", id, error: { code, message } })}\n`);
}

async function callTool(name, args) {
  switch (name) {
    case "flutterfix.ask": return askFlutterFix(args);
    case "flutterfix.migration_map": return migrationMap(args);
    case "flutterfix.analyze_snippet": return validateDartSnippet(args);
    case "flutterfix.docs_status": return corpusStatus();
    default: throw Object.assign(new Error(`Unknown tool: ${name}`), { code: -32602 });
  }
}

async function handleMessage(message) {
  const { id, method, params = {} } = message;
  if (method === "notifications/initialized" || method === "notifications/cancelled") return;
  if (method === "initialize") {
    reply(id, {
      protocolVersion: params.protocolVersion ?? "2025-03-26",
      capabilities: { tools: {} },
      serverInfo
    });
    return;
  }
  if (method === "ping") {
    reply(id, {});
    return;
  }
  if (method === "tools/list") {
    reply(id, { tools });
    return;
  }
  if (method === "tools/call") {
    try {
      const output = await callTool(params.name, params.arguments ?? {});
      reply(id, {
        content: [{ type: "text", text: JSON.stringify(output, null, 2) }],
        structuredContent: output,
        isError: false
      });
    } catch (error) {
      const messageText = error instanceof Error ? error.message : String(error);
      reply(id, {
        content: [{ type: "text", text: messageText }],
        isError: true
      });
    }
    return;
  }
  if (id !== undefined) errorReply(id, -32601, `Method not found: ${method}`);
}

const input = createInterface({ input: process.stdin, crlfDelay: Infinity });
input.on("line", (line) => {
  try {
    const message = JSON.parse(line);
    void handleMessage(message).catch((error) => {
      console.error(error instanceof Error ? error.message : String(error));
      if (message.id !== undefined) errorReply(message.id, -32603, "Internal server error.");
    });
  } catch {
    errorReply(null, -32700, "Parse error.");
  }
});
