/** One bounded offline build; no model, network, canonical storage, or scheduler. */
import { createHash } from "node:crypto";
import { buildCompleteScene } from "./vendor/generation-0.3.28/scene-builder.ts";

const SCHEMA = "archeaxis.openmaic-scene-build/v1";
const RESULT = "archeaxis.openmaic-scene-build-result/v1";
const MAX_INPUT = 256_000;
const MAX_OUTPUT = 1_000_000;
const id = value => typeof value === "string" && /^[A-Za-z0-9_-]{1,128}$/.test(value);
const object = value => !!value && typeof value === "object" && !Array.isArray(value);
const text = (value, max) => typeof value === "string" && value.trim().length > 0 && value.length <= max && !value.includes("\0");

// JSON.parse alone silently accepts duplicate keys, including escaped aliases.
// Check the already parsed frame again while preserving decoded key identity.
function rejectDuplicateKeys(source) {
  let p = 0;
  const whitespace = () => { while (p < source.length && /[\x20\t\r\n]/.test(source[p])) p++; };
  function string() {
    const start = p++;
    while (p < source.length) {
      if (source[p] === "\\") { p += 2; continue; }
      if (source[p++] === '"') return JSON.parse(source.slice(start, p));
    }
    throw new Error("invalid string");
  }
  function value(depth) {
    if (depth > 64) throw new Error("depth exceeded");
    whitespace();
    if (source[p] === '"') { string(); return; }
    if (source[p] === "{") {
      p++; whitespace();
      const keys = new Set();
      if (source[p] === "}") { p++; return; }
      while (p < source.length) {
        whitespace(); if (source[p] !== '"') throw new Error("object key required");
        const key = string(); if (keys.has(key)) throw new Error("duplicate key"); keys.add(key);
        whitespace(); if (source[p++] !== ":") throw new Error("colon required");
        value(depth + 1); whitespace();
        if (source[p] === "}") { p++; return; }
        if (source[p++] !== ",") throw new Error("comma required");
      }
      throw new Error("unclosed object");
    }
    if (source[p] === "[") {
      p++; whitespace(); if (source[p] === "]") { p++; return; }
      while (p < source.length) {
        value(depth + 1); whitespace();
        if (source[p] === "]") { p++; return; }
        if (source[p++] !== ",") throw new Error("comma required");
      }
      throw new Error("unclosed array");
    }
    const start = p;
    while (p < source.length && !/[\x20\t\r\n,\]}]/.test(source[p])) p++;
    if (p === start) throw new Error("value required");
  }
  value(0); whitespace(); if (p !== source.length) throw new Error("trailing input");
}

function validRequest(request) {
  const fields = ["schema", "request_id", "attempt", "source", "stage_id", "scene_id", "outline", "content", "actions"];
  if (!object(request) || Object.keys(request).length !== fields.length || fields.some(k => !Object.hasOwn(request, k))
      || request.schema !== SCHEMA || !id(request.request_id) || !id(request.stage_id) || !id(request.scene_id)
      || !Number.isSafeInteger(request.attempt) || request.attempt < 1 || !object(request.source)) return false;
  const source = request.source;
  if (Object.keys(source).length !== 3 || !id(source.document_id) || !Number.isSafeInteger(source.version) || source.version < 1
      || typeof source.content_sha256 !== "string" || !/^[a-f0-9]{64}$/.test(source.content_sha256)) return false;
  const outline = request.outline;
  if (!object(outline) || !id(outline.id) || !["slide", "quiz", "interactive", "pbl"].includes(outline.type)
      || !text(outline.title, 240) || typeof outline.description !== "string" || outline.description.length > 16_000
      || !Number.isSafeInteger(outline.order) || outline.order < 0 || outline.order > 1_000_000
      || !Array.isArray(outline.keyPoints) || outline.keyPoints.length > 200
      || outline.keyPoints.some(point => !text(point, 2000))) return false;
  if (!object(request.content) || !Array.isArray(request.actions) || request.actions.length > 100
      || request.actions.some(action => !object(action) || !text(action.type, 128))) return false;
  const content = request.content;
  if (outline.type === "slide" && Object.hasOwn(content, "elements")
      && (!Array.isArray(content.elements) || content.elements.length > 200)) return false;
  if (outline.type === "quiz" && Object.hasOwn(content, "questions")
      && (!Array.isArray(content.questions) || content.questions.length < 1 || content.questions.length > 200)) return false;
  if (outline.type === "interactive" && Object.hasOwn(content, "html") && !text(content.html, 200_000)) return false;
  if (outline.type === "pbl" && Object.hasOwn(content, "projectV2") && !object(content.projectV2)) return false;
  return true;
}

function failure(status, reason) {
  return { schema: RESULT, status, reason, scene: null, model_call: "NOT_INVOKED", canonical_bindings_verified: false,
    human_review_required: true, active_content_executed: false };
}
function processFrame(raw) {
  try {
    const source = new TextDecoder("utf-8", { fatal: true }).decode(raw);
    const request = JSON.parse(source);
    rejectDuplicateKeys(source);
    if (!validRequest(request)) return failure("INVALID_REQUEST", "request contract or budget rejected");
    const scene = buildCompleteScene(request.outline, request.content, request.actions, request.stage_id, { sceneId: request.scene_id });
    if (scene === null) return failure("UPSTREAM_NULL", "upstream builder returned null");
    return { schema: RESULT, status: "CANDIDATE", request_id: request.request_id, attempt: request.attempt,
      input_sha256: createHash("sha256").update(raw).digest("hex"), source: request.source,
      source_binding: "client_declared_unverified", provider: "openmaic", provider_version: "1.3.0",
      generation_version: "0.3.28", scene, authority_effect: "candidate_only", model_call: "NOT_INVOKED",
      canonical_bindings_verified: false, human_review_required: true, active_content_executed: false,
      rendering_authorized: false, retry_bytes_stable: false };
  } catch {
    return failure("INVALID_REQUEST", "invalid bounded UTF-8 JSON or duplicate keys");
  }
}

if (process.argv.slice(2).length === 1 && process.argv[2] === "--hello") {
  process.stdout.write(JSON.stringify({ schema: "archeaxis.derived-worker-hello/v1", capability: "course.openmaic.scene-build",
    version: 1, upstream_generation: "0.3.28", core_transport: "NOT_CONNECTED" }) + "\n");
} else if (process.argv.length !== 2) {
  process.stdout.write(JSON.stringify(failure("INVALID_REQUEST", "unsupported worker arguments")) + "\n");
  process.exitCode = 2;
} else {
  let length = 0, overflow = false;
  const chunks = [];
  for await (const chunk of process.stdin) {
    length += chunk.length;
    if (length > MAX_INPUT) overflow = true;
    if (!overflow) chunks.push(chunk);
  }
  let result = overflow || !length ? failure("INVALID_REQUEST", "input exceeds byte budget or is empty") : processFrame(Buffer.concat(chunks));
  let output = JSON.stringify(result);
  if (Buffer.byteLength(output, "utf8") > MAX_OUTPUT) {
    result = failure("INVALID_REQUEST", "candidate exceeds output byte budget");
    output = JSON.stringify(result);
  }
  process.stdout.write(output + "\n");
  if (result.status !== "CANDIDATE") process.exitCode = 2;
}
