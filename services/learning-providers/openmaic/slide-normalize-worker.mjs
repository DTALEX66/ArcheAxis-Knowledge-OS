/** Unregistered bounded DSL candidate; it neither renders nor persists. */
import { createHash } from "node:crypto";
import { closeSync, lstatSync, openSync, readFileSync, readSync } from "node:fs";
import { registerHooks } from "node:module";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const SCHEMA = "archeaxis.openmaic-slide-normalize/v1";
const RESULT = "archeaxis.openmaic-slide-normalize-result/v1";
const MAX_FRAME = 32_768, MAX_SCENE = 16_384, MAX_OUTPUT = 196_608, MAX_NORMALIZED = 32_768;
const NODE_SHA256 = "ba4e6d110e8c1592a1ecd390f6b05f3da124b13871a5be62b341a07a853c6c32";
const MANIFEST_SHA256 = "c7564a5741c0807834ebcf77779a50590b927fa8b7e93f49494d1ef8eac6c317";
const ORIGINALS = {
  "package.json": "847c2f4054034aab29586171872cb64a0f0b4e39db8dd9b8c50cff5e67014c98",
  "LICENSE": "ba252563743227138231604c9138dd400faca5a10c3cf206b466e5466c565a19",
  "src/normalize.ts": "e4f21f3273d9d65dadd53768afc5049b5473d087d1c525ea804c3d057b5ecf06",
  "src/stage.ts": "b8ce1ac2cff5a37e7fee7b23a1eb4df59499f0357366d80166163d7b32a9fc6a",
};
const DONOR = path.resolve(fileURLToPath(new URL("./vendor/scene-content-0.3.28-original/dsl/", import.meta.url)));
const WORKER = fileURLToPath(import.meta.url);
const sha256 = data => createHash("sha256").update(data).digest("hex");

class Rejection extends Error { constructor(code) { super(code); this.code = code; } }
const reject = code => { throw new Rejection(code); };
function readRegular(name, code) {
  try {
    if (!name || name.includes("\\") || name.includes(":") ||
        name.split("/").some(part => !part || part === "." || part === "..")) reject(code);
    const rootInfo = lstatSync(DONOR);
    if (!rootInfo.isDirectory() || rootInfo.isSymbolicLink()) reject(code);
    const target = path.resolve(DONOR, ...name.split("/"));
    const rel = path.relative(DONOR, target);
    if (!rel || rel === ".." || rel.startsWith(".." + path.sep) || path.isAbsolute(rel)) reject(code);
    let parent = path.dirname(target);
    while (parent !== DONOR) {
      const info = lstatSync(parent);
      if (!info.isDirectory() || info.isSymbolicLink()) reject(code);
      parent = path.dirname(parent);
    }
    const info = lstatSync(target);
    if (!info.isFile() || info.isSymbolicLink() || info.size > 1_000_000) reject(code);
    const bytes = readFileSync(target);
    if (bytes.length !== info.size) reject(code);
    return bytes;
  } catch (error) {
    if (error instanceof Rejection) throw error;
    reject(code);
  }
}
function verifyNode() {
  if (process.versions.node !== "24.21.0" || process.execArgv.length !== 0 || process.argv.length !== 2)
    reject("NODE_IDENTITY_MISMATCH");
  if (Object.hasOwn(process.env, "NODE_OPTIONS") || Object.hasOwn(process.env, "NODE_PATH"))
    reject("ENVIRONMENT_OVERRIDE");
  let fd;
  try {
    const info = lstatSync(process.execPath);
    if (!info.isFile() || info.isSymbolicLink() || info.size !== 93_580_104) reject("NODE_IDENTITY_MISMATCH");
    fd = openSync(process.execPath, "r");
    const hash = createHash("sha256"), buffer = Buffer.allocUnsafe(1024 * 1024);
    let total = 0;
    for (;;) {
      const count = readSync(fd, buffer, 0, buffer.length, null);
      if (!count) break;
      total += count;
      if (total > 93_580_104) reject("NODE_IDENTITY_MISMATCH");
      hash.update(buffer.subarray(0, count));
    }
    if (total !== 93_580_104 || hash.digest("hex") !== NODE_SHA256) reject("NODE_IDENTITY_MISMATCH");
  } catch (error) {
    if (error instanceof Rejection) throw error;
    reject("NODE_IDENTITY_MISMATCH");
  } finally { if (fd !== undefined) closeSync(fd); }
}
function verifyDonor() {
  const code = "UPSTREAM_IDENTITY_MISMATCH";
  const raw = readRegular("ORIGINALS.json", code);
  if (sha256(raw) !== MANIFEST_SHA256) reject(code);
  let manifest;
  try { manifest = JSON.parse(raw.toString("utf8")); } catch { reject(code); }
  for (const [name, expected] of Object.entries(ORIGINALS)) {
    if (manifest?.originals?.[name] !== expected || sha256(readRegular(name, code)) !== expected) reject(code);
  }
}
function installResolver() {
  const normalize = path.join(DONOR, "src", "normalize.ts");
  const stage = path.join(DONOR, "src", "stage.ts");
  registerHooks({ resolve(specifier, context) {
    const parent = context.parentURL?.startsWith("file:") ? fileURLToPath(context.parentURL) : "";
    let name;
    if (parent === WORKER && specifier === pathToFileURL(normalize).href) name = "src/normalize.ts";
    else if (parent === normalize && specifier === "./stage.js") name = "src/stage.ts";
    else reject("UNLISTED_IMPORT");
    if (sha256(readRegular(name, "UPSTREAM_IDENTITY_MISMATCH")) !== ORIGINALS[name])
      reject("UPSTREAM_IDENTITY_MISMATCH");
    return { url: pathToFileURL(name === "src/normalize.ts" ? normalize : stage).href, shortCircuit: true };
  } });
  return normalize;
}

// JSON.parse by itself silently accepts duplicate keys and rounds some numbers.
// A numeric token is accepted only when its ECMAScript serialization matches
// the original token, preserving the source alongside the derived output.
function strictJson(bytes, code) {
  if (bytes.length >= 3 && bytes[0] === 0xef && bytes[1] === 0xbb && bytes[2] === 0xbf) reject(code);
  let source, parsed;
  try { source = new TextDecoder("utf-8", { fatal: true }).decode(bytes); parsed = JSON.parse(source); }
  catch { reject(code); }
  let p = 0;
  const whitespace = () => { while (p < source.length && /[\x20\t\r\n]/.test(source[p])) p++; };
  function string() {
    const start = p++;
    while (p < source.length) {
      if (source[p] === "\\") { p += 2; continue; }
      if (source[p++] === '"') return JSON.parse(source.slice(start, p));
    }
    reject(code);
  }
  function value(depth) {
    if (depth > 64) reject(code);
    whitespace();
    if (source[p] === '"') { string(); return; }
    if (source[p] === "{") {
      p++; whitespace(); const keys = new Set();
      if (source[p] === "}") { p++; return; }
      while (p < source.length) {
        whitespace(); if (source[p] !== '"') reject(code);
        const key = string(); if (keys.has(key)) reject(code); keys.add(key);
        whitespace(); if (source[p++] !== ":") reject(code);
        value(depth + 1); whitespace();
        if (source[p] === "}") { p++; return; }
        if (source[p++] !== ",") reject(code);
      }
      reject(code);
    }
    if (source[p] === "[") {
      p++; whitespace(); if (source[p] === "]") { p++; return; }
      while (p < source.length) {
        value(depth + 1); whitespace();
        if (source[p] === "]") { p++; return; }
        if (source[p++] !== ",") reject(code);
      }
      reject(code);
    }
    const start = p;
    while (p < source.length && !/[\x20\t\r\n,\]}]/.test(source[p])) p++;
    const token = source.slice(start, p);
    if (!token) reject(code);
    if (/^-?\d/.test(token) && (!Number.isFinite(Number(token)) || JSON.stringify(Number(token)) !== token)) reject(code);
  }
  value(0); whitespace(); if (p !== source.length) reject(code);
  return parsed;
}
const object = value => value !== null && typeof value === "object" && !Array.isArray(value);
function keys(value, required, optional = []) {
  return object(value) && required.every(key => Object.hasOwn(value, key)) &&
    Object.keys(value).every(key => required.includes(key) || optional.includes(key));
}
const id = value => typeof value === "string" && /^[A-Za-z0-9_-]{1,128}$/.test(value);
const text = (value, max) => typeof value === "string" && value.isWellFormed() &&
  value.length <= max && !!value.trim() && !value.includes("\0");
const finite = (value, min, max) => typeof value === "number" && Number.isFinite(value) && value >= min && value <= max;
const color = value => typeof value === "string" && (/^#(?:[a-f\d]{3}|[a-f\d]{4}|[a-f\d]{6}|[a-f\d]{8})$/i.test(value) || /^[a-z]{1,24}$/i.test(value));
function validScene(scene) {
  if (!keys(scene, ["id", "stageId", "type", "title", "order", "content", "actions"], ["outlineId", "createdAt", "updatedAt"]) ||
      !id(scene.id) || !id(scene.stageId) || scene.type !== "slide" || !text(scene.title, 240) ||
      !Number.isSafeInteger(scene.order) || scene.order < 0 || !Array.isArray(scene.actions) || scene.actions.length !== 0)
    return false;
  if (Object.hasOwn(scene, "outlineId") && !id(scene.outlineId)) return false;
  for (const key of ["createdAt", "updatedAt"]) if (Object.hasOwn(scene, key) &&
      (!Number.isSafeInteger(scene[key]) || scene[key] < 0)) return false;
  if (!keys(scene.content, ["type", "canvas"], ["schemaVersion"]) || scene.content.type !== "slide" ||
      (Object.hasOwn(scene.content, "schemaVersion") && scene.content.schemaVersion !== 1)) return false;
  const canvas = scene.content.canvas;
  if (!keys(canvas, ["id", "viewportSize", "viewportRatio", "theme", "elements"], ["background"]) ||
      !id(canvas.id) || !finite(canvas.viewportSize, 1, 10000) || !finite(canvas.viewportRatio, 0.1, 10)) return false;
  const theme = canvas.theme;
  if (!keys(theme, ["backgroundColor", "themeColors", "fontColor", "fontName"], ["outline", "shadow"]) ||
      !color(theme.backgroundColor) || !color(theme.fontColor) || !text(theme.fontName, 240) ||
      !Array.isArray(theme.themeColors) || theme.themeColors.length > 32 || !theme.themeColors.every(color)) return false;
  if (Object.hasOwn(theme, "outline")) {
    const o = theme.outline;
    if (!keys(o, [], ["color", "width", "style"]) ||
        (Object.hasOwn(o, "color") && !color(o.color)) ||
        (Object.hasOwn(o, "width") && !finite(o.width, 0, 10000)) ||
        (Object.hasOwn(o, "style") && !["solid", "dashed", "dotted"].includes(o.style))) return false;
  }
  if (Object.hasOwn(theme, "shadow")) {
    const s = theme.shadow;
    if (!keys(s, ["h", "v", "blur", "color"]) || !finite(s.h, -10000, 10000) ||
        !finite(s.v, -10000, 10000) || !finite(s.blur, 0, 10000) || !color(s.color)) return false;
  }
  if (Object.hasOwn(canvas, "background")) {
    const b = canvas.background;
    if (!keys(b, ["type"], ["color"]) || b.type !== "solid" ||
        (Object.hasOwn(b, "color") && !color(b.color))) return false;
  }
  if (!Array.isArray(canvas.elements) || canvas.elements.length > 200) return false;
  const ids = new Set();
  for (const element of canvas.elements) {
    if (!keys(element, ["type", "id", "left", "top", "width", "height", "rotate", "content"], ["defaultFontName", "defaultColor"]) ||
        element.type !== "text" || !id(element.id) || ids.has(element.id) || !text(element.content, 16000) ||
        /<\s*(?:img|video|audio|iframe|object|embed|svg|canvas|script|style|link|base|form)\b/i.test(element.content) ||
        !finite(element.left, -10000, 10000) || !finite(element.top, -10000, 10000) ||
        !finite(element.width, 0.01, 10000) || !finite(element.height, 0.01, 10000) ||
        !finite(element.rotate, -3600, 3600)) return false;
    if (Object.hasOwn(element, "defaultFontName") && element.defaultFontName !== "" && !text(element.defaultFontName, 240)) return false;
    if (Object.hasOwn(element, "defaultColor") && element.defaultColor !== "" && !color(element.defaultColor)) return false;
    ids.add(element.id);
  }
  return true;
}
function sameJson(a, b) {
  if (Object.is(a, b)) return true;
  if (Array.isArray(a) || Array.isArray(b)) return Array.isArray(a) && Array.isArray(b) &&
    a.length === b.length && a.every((item, index) => sameJson(item, b[index]));
  if (!object(a) || !object(b)) return false;
  const ka = Object.keys(a), kb = Object.keys(b);
  return ka.length === kb.length && ka.every(key => Object.hasOwn(b, key) && sameJson(a[key], b[key]));
}
function allowedChanges(original, normalized) {
  const expected = structuredClone(original), changes = [];
  expected.content.canvas.elements.forEach((element, index) => {
    for (const [field, fallback] of [["defaultFontName", "Microsoft YaHei"], ["defaultColor", "#333333"]]) {
      if (!Object.hasOwn(element, field) || element[field] === "") {
        changes.push({ path: `/content/canvas/elements/${index}/${field}`,
          kind: Object.hasOwn(element, field) ? "EMPTY_REPLACED_WITH_DEFAULT" : "ABSENT_FILLED_WITH_DEFAULT" });
        element[field] = fallback;
      }
    }
  });
  if (!sameJson(expected, normalized)) reject("UNEXPECTED_UPSTREAM_CHANGE");
  return changes;
}
function patch(original, output) {
  let prefix = 0, suffix = 0;
  while (prefix < original.length && prefix < output.length && original[prefix] === output[prefix]) prefix++;
  while (suffix < original.length - prefix && suffix < output.length - prefix &&
         original[original.length - 1 - suffix] === output[output.length - 1 - suffix]) suffix++;
  const deleted = original.length - prefix - suffix, insert = output.subarray(prefix, output.length - suffix);
  if (!Buffer.concat([original.subarray(0, prefix), insert, original.subarray(prefix + deleted)]).equals(output))
    reject("PATCH_MISMATCH");
  return { unit: "bytes", start: prefix, delete_bytes: deleted, insert_base64: insert.toString("base64") };
}
function envelope(status, extra = {}) {
  return { schema: RESULT, status, ...extra, scope: "CALLER_SUPPLIED_UNVERIFIED", privacy: "PRIVATE_INPUT_AND_OUTPUT",
    provider: "openmaic", provider_version: "1.3.0", dsl_package_version: "0.12.0",
    expected_normalize_sha256: ORIGINALS["src/normalize.ts"],
    source_verification: status === "CANDIDATE" ? "VERIFIED_SELECTED_MEMBERS" : "NOT_ASSERTED",
    node_version: process.versions.node, full_scene_generation: false, rendering_authorized: false,
    security_sanitizer: false, core_authorization: "NOT_ESTABLISHED", canonical_persistence: "NOT_PERFORMED",
    network_isolation: "NOT_ESTABLISHED", original_preservation: "CALLER_RESPONSIBILITY" };
}
function emit(value) {
  const encoded = JSON.stringify(value) + "\n";
  if (Buffer.byteLength(encoded, "utf8") > MAX_OUTPUT) reject("OUTPUT_TOO_LARGE");
  process.stdout.write(encoded);
}
async function stdinBytes() {
  const chunks = []; let total = 0;
  const timer = setTimeout(() => process.stdin.destroy(new Rejection("INPUT_TIMEOUT")), 10_000);
  try {
    for await (const chunk of process.stdin) {
      total += chunk.length; if (total > MAX_FRAME) reject("INPUT_TOO_LARGE"); chunks.push(chunk);
    }
    return Buffer.concat(chunks, total);
  } finally { clearTimeout(timer); }
}
try {
  verifyNode();
  const frame = strictJson(await stdinBytes(), "INVALID_REQUEST");
  if (!keys(frame, ["schema", "request_id", "scene_utf8_base64"]) || frame.schema !== SCHEMA ||
      !id(frame.request_id) || typeof frame.scene_utf8_base64 !== "string" ||
      frame.scene_utf8_base64.length > 4 * Math.ceil(MAX_SCENE / 3) ||
      !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(frame.scene_utf8_base64))
    reject("INVALID_REQUEST");
  const input = Buffer.from(frame.scene_utf8_base64, "base64");
  if (!input.length || input.length > MAX_SCENE || input.toString("base64") !== frame.scene_utf8_base64)
    reject("INVALID_REQUEST");
  const original = strictJson(input, "INVALID_SCENE");
  if (!validScene(original)) reject("UNSUPPORTED_SCENE");
  const frozenOriginal = strictJson(input, "INVALID_SCENE");
  verifyDonor();
  const modulePath = installResolver();
  const upstream = await import(pathToFileURL(modulePath).href);
  const normalized = upstream.normalizeScene(original);
  if (!sameJson(original, frozenOriginal)) reject("UPSTREAM_MUTATED_INPUT");
  if (!validScene(normalized)) reject("UNEXPECTED_UPSTREAM_RESULT");
  const changes = allowedChanges(frozenOriginal, normalized);
  const output = Buffer.from(JSON.stringify(normalized), "utf8");
  if (output.length > MAX_NORMALIZED) reject("OUTPUT_TOO_LARGE");
  emit(envelope("CANDIDATE", { request_id: frame.request_id,
    input_sha256: sha256(input), input_bytes: input.length, input_utf8_base64: input.toString("base64"),
    output_sha256: sha256(output), output_bytes: output.length, output_utf8_base64: output.toString("base64"),
    byte_patch: patch(input, output), semantic_changes: changes, serialization: "ECMASCRIPT_JSON_RESERIALIZED" }));
} catch (error) {
  emit(envelope("REJECTED", { error_code: error instanceof Rejection ? error.code : "INTERNAL_FAILURE" }));
}
