/**
 * Bounded, unregistered OpenMAIC 1.3.0 URL-mapping prototype.
 * It calls the retained upstream function, never renders or executes input HTML.
 * Hash checks and resolver restrictions are not an OS sandbox or Core authority.
 */
import { createHash } from "node:crypto";
import { closeSync, lstatSync, openSync, readFileSync, readSync } from "node:fs";
import { registerHooks } from "node:module";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const SCHEMA = "archeaxis.openmaic-interactive-url-map/v1";
const NODE_SHA256 = "ba4e6d110e8c1592a1ecd390f6b05f3da124b13871a5be62b341a07a853c6c32";
const ORIGINALS_SHA256 = "5679a80166d41114448ab35a1e2128a56baca7c9611218af590c81f3889d1ce3";
const ORIGINALS = {
  "package.json": "5308b268d06dd27e592de00f02d57b046588df0d6e160f4179788388d5a806d1",
  "LICENSE": "ba252563743227138231604c9138dd400faca5a10c3cf206b466e5466c565a19",
  "src/interactive-library-mapper.ts": "fe4637cc0e32cd557dcdc285017008cfe741e7799478a9c9ec102cc97194b1fe",
  "src/interactive-libraries.ts": "1c9f212d7e2010dd3e1f4889efe22825fcb1f52772b056e5a30fc58753f29de1",
};
const SOURCES = {
  "parse5-8.0.1": ["fb5a2c507c9c2d2c59073df562e2131ada5860b3370ebc9508762bc4be1cad30", 33],
  "entities-8.0.0": ["91fd19349c025f903464fe8d0e4ab5464708db4386024dbd9957c273c91a422c", 58],
  "es-module-lexer-2.0.0": ["2c222673e20d94f84a03d8a277df5a91c842053a6e991a44cec6b62e8aa45d71", 8],
  "postcss-8.5.23": ["b0e2faa80c9539b2f9b5d5e8e67b328dbf421130a02cd1695a5da659447ca61f", 55],
  "postcss-value-parser-4.2.0": ["d7b344a5bd2494aea12255918bf24e4dd4a34ba80a06d9bb399ea5469e145607", 9],
  "nanoid-3.3.19": ["3495da1b2b7f1c42952fc5090cd0eb818f207eb70a9f2083837ffedfa6dbdcf4", 25],
  "picocolors-1.1.1": ["04718da4913e9256b832a9227dc9ee4a875e5f7f7b57c44592caadcc612bb057", 7],
  "source-map-js-1.2.1": ["20eaf7236bed35a6bb8a316852680637c369ea7a3c0ec6aabc3fb51eb47c7bbe", 18],
};
const BASE = "/vendor/interactive";
const MAX_STDIN = 16_384;
const MAX_URL = 4_096;
const MAX_STDOUT = 8_192;
const DONOR = fileURLToPath(new URL("./vendor/scene-content-0.3.28-original/generation/", import.meta.url));
const NPM = fileURLToPath(new URL("./vendor/npm/", import.meta.url));
const WORKER = fileURLToPath(import.meta.url);
const sha256 = data => createHash("sha256").update(data).digest("hex");

class Rejection extends Error {
  constructor(code) { super(code); this.code = code; }
}
function reject(code) { throw new Rejection(code); }
function inside(root, candidate) {
  const rel = path.relative(root, candidate);
  return rel !== "" && rel !== ".." && !rel.startsWith(".." + path.sep) && !path.isAbsolute(rel);
}
function safeMember(root, name, code) {
  if (typeof name !== "string" || !name || name.includes("\\") || name.includes(":") ||
      name.split("/").some(part => !part || part === "." || part === "..")) reject(code);
  const candidate = path.resolve(root, ...name.split("/"));
  if (!inside(root, candidate)) reject(code);
  return candidate;
}
function readRegular(root, candidate, limit, code) {
  try {
    if (!inside(root, candidate)) reject(code);
    let parent = path.dirname(candidate);
    while (inside(root, parent)) {
      const info = lstatSync(parent);
      if (!info.isDirectory() || info.isSymbolicLink()) reject(code);
      parent = path.dirname(parent);
    }
    const rootInfo = lstatSync(root);
    const info = lstatSync(candidate);
    if (!rootInfo.isDirectory() || rootInfo.isSymbolicLink() || !info.isFile() ||
        info.isSymbolicLink() || info.size > limit) reject(code);
    const data = readFileSync(candidate);
    if (data.length !== info.size) reject(code);
    return data;
  } catch (error) {
    if (error instanceof Rejection) throw error;
    reject(code);
  }
}
function verifyNode() {
  if (process.versions.node !== "24.21.0" || process.execArgv.length !== 0 || process.argv.length !== 2)
    reject("NODE_IDENTITY_MISMATCH");
  for (const name of ["NODE_OPTIONS", "NODE_PATH", "INTERACTIVE_ASSET_BASE_URL"]) {
    if (Object.hasOwn(process.env, name)) reject("ENVIRONMENT_OVERRIDE");
  }
  let fd;
  try {
    const info = lstatSync(process.execPath);
    if (!info.isFile() || info.isSymbolicLink()) reject("NODE_IDENTITY_MISMATCH");
    fd = openSync(process.execPath, "r");
    const digest = createHash("sha256");
    const buffer = Buffer.allocUnsafe(1024 * 1024);
    for (;;) {
      const count = readSync(fd, buffer, 0, buffer.length, null);
      if (!count) break;
      digest.update(buffer.subarray(0, count));
    }
    if (digest.digest("hex") !== NODE_SHA256) reject("NODE_IDENTITY_MISMATCH");
  } catch (error) {
    if (error instanceof Rejection) throw error;
    reject("NODE_IDENTITY_MISMATCH");
  } finally {
    if (fd !== undefined) closeSync(fd);
  }
}

// The wire contract is one object containing only string-valued fields. Parse
// keys individually so duplicate decoded names are rejected before JSON.parse
// could silently select one. Invalid input is never reflected into the reply.
function parseRequest(raw) {
  let text;
  try { text = new TextDecoder("utf-8", { fatal: true }).decode(raw); }
  catch { reject("INVALID_REQUEST"); }
  let cursor = 0;
  const whitespace = () => { while (cursor < text.length && /[\x20\t\r\n]/.test(text[cursor])) cursor++; };
  const string = () => {
    if (text[cursor] !== '"') reject("INVALID_REQUEST");
    const start = cursor++;
    while (cursor < text.length) {
      const ch = text[cursor++];
      if (ch === "\\") { if (cursor >= text.length) reject("INVALID_REQUEST"); cursor++; continue; }
      if (ch === '"') {
        try { return JSON.parse(text.slice(start, cursor)); }
        catch { reject("INVALID_REQUEST"); }
      }
      if (ch.charCodeAt(0) < 0x20) reject("INVALID_REQUEST");
    }
    reject("INVALID_REQUEST");
  };
  whitespace();
  if (text[cursor++] !== "{") reject("INVALID_REQUEST");
  const result = Object.create(null);
  whitespace();
  if (text[cursor] !== "}") {
    for (;;) {
      whitespace();
      const key = string();
      if (Object.hasOwn(result, key)) reject("INVALID_REQUEST");
      whitespace();
      if (text[cursor++] !== ":") reject("INVALID_REQUEST");
      whitespace();
      result[key] = string();
      whitespace();
      if (text[cursor] === "}") break;
      if (text[cursor++] !== ",") reject("INVALID_REQUEST");
    }
  }
  cursor++; whitespace();
  if (cursor !== text.length || Object.keys(result).length !== 3 ||
      !["schema", "request_id", "url"].every(key => Object.hasOwn(result, key)) ||
      result.schema !== SCHEMA || !/^[A-Za-z0-9_-]{1,128}$/.test(result.request_id) ||
      typeof result.url !== "string" || !/^[\x21-\x7e]+$/.test(result.url) ||
      Buffer.byteLength(result.url, "utf8") > MAX_URL ||
      !/^(?:https?:\/\/|\/\/|\/vendor\/interactive\/)/.test(result.url)) reject("INVALID_REQUEST");
  return result;
}
async function stdinBytes() {
  const chunks = [];
  let total = 0;
  const timer = setTimeout(() => process.stdin.destroy(new Rejection("INPUT_TIMEOUT")), 10_000);
  try {
    for await (const chunk of process.stdin) {
      total += chunk.length;
      if (total > MAX_STDIN) reject("INPUT_TOO_LARGE");
      chunks.push(chunk);
    }
    return Buffer.concat(chunks, total);
  } finally {
    clearTimeout(timer);
  }
}
function readDonor() {
  const code = "UPSTREAM_IDENTITY_MISMATCH";
  const raw = readRegular(DONOR, path.join(DONOR, "ORIGINALS.json"), 1_000_000, code);
  if (sha256(raw) !== ORIGINALS_SHA256) reject(code);
  let manifest;
  try { manifest = JSON.parse(raw.toString("utf8")); } catch { reject(code); }
  if (!manifest || typeof manifest.originals !== "object" || !manifest.originals) reject(code);
  for (const [name, expected] of Object.entries(ORIGINALS)) {
    const candidate = safeMember(DONOR, name, code);
    if (manifest.originals[name] !== expected || sha256(readRegular(DONOR, candidate, 1_000_000, code)) !== expected)
      reject(code);
  }
}
function readPackages() {
  const result = new Map();
  for (const [stem, [expected, count]] of Object.entries(SOURCES)) {
    const code = "DEPENDENCY_IDENTITY_MISMATCH";
    const root = path.join(NPM, stem);
    const raw = readRegular(root, path.join(root, "SOURCE.json"), 1_000_000, code);
    if (sha256(raw) !== expected) reject(code);
    let manifest;
    try { manifest = JSON.parse(raw.toString("utf8")); } catch { reject(code); }
    if (!manifest || !manifest.files || typeof manifest.files !== "object" ||
        Array.isArray(manifest.files) || Object.keys(manifest.files).length !== count) reject(code);
    for (const [name, identity] of Object.entries(manifest.files)) {
      const candidate = safeMember(root, name, code);
      const bytes = readRegular(root, candidate, 1_000_000, code);
      if (!identity || !Number.isInteger(identity.bytes) || identity.bytes !== bytes.length ||
          !/^[0-9a-f]{64}$/.test(identity.sha256) || sha256(bytes) !== identity.sha256) reject(code);
    }
    result.set(stem, { root, files: manifest.files });
  }
  return result;
}
function verifiedPackageMember(pkg, candidate) {
  if (!inside(pkg.root, candidate)) reject("UNLISTED_IMPORT");
  const name = path.relative(pkg.root, candidate).split(path.sep).join("/");
  if (!Object.hasOwn(pkg.files, name)) reject("UNLISTED_IMPORT");
  const identity = pkg.files[name];
  if (!identity) reject("UNLISTED_IMPORT");
  const bytes = readRegular(pkg.root, candidate, 1_000_000, "DEPENDENCY_IDENTITY_MISMATCH");
  if (bytes.length !== identity.bytes || sha256(bytes) !== identity.sha256) reject("DEPENDENCY_IDENTITY_MISMATCH");
  return candidate;
}
function installResolver(packages) {
  const mapper = path.join(DONOR, "src", "interactive-library-mapper.ts");
  const library = path.join(DONOR, "src", "interactive-libraries.ts");
  const exact = (stem, name) => {
    const pkg = packages.get(stem);
    const target = safeMember(pkg.root, name, "UNLISTED_IMPORT");
    verifiedPackageMember(pkg, target);
    return { url: pathToFileURL(target).href, shortCircuit: true };
  };
  const donor = (candidate, name) => {
    if (sha256(readRegular(DONOR, candidate, 1_000_000, "UPSTREAM_IDENTITY_MISMATCH")) !== ORIGINALS[name])
      reject("UPSTREAM_IDENTITY_MISMATCH");
    return { url: pathToFileURL(candidate).href, shortCircuit: true };
  };
  const builtins = new Set(["fs", "node:fs", "path", "node:path", "url", "node:url"]);
  registerHooks({
    resolve(specifier, context, nextResolve) {
      const parent = context.parentURL?.startsWith("file:") ? fileURLToPath(context.parentURL) : "";
      if (parent === WORKER && specifier === pathToFileURL(mapper).href)
        return donor(mapper, "src/interactive-library-mapper.ts");
      if (parent === WORKER && specifier === pathToFileURL(library).href)
        return donor(library, "src/interactive-libraries.ts");
      if (parent === mapper) {
        if (specifier === "./interactive-libraries.js") return donor(library, "src/interactive-libraries.ts");
        if (specifier === "parse5") return exact("parse5-8.0.1", "dist/index.js");
        if (specifier === "es-module-lexer/js") return exact("es-module-lexer-2.0.0", "dist/lexer.asm.js");
        if (specifier === "postcss") return exact("postcss-8.5.23", "lib/postcss.mjs");
        if (specifier === "postcss-value-parser") return exact("postcss-value-parser-4.2.0", "lib/index.js");
        reject("UNLISTED_IMPORT");
      }
      if (parent === library) reject("UNLISTED_IMPORT");
      const owner = [...packages.entries()].find(([, pkg]) => inside(pkg.root, parent));
      if (!owner) reject("UNLISTED_IMPORT");
      const [stem, pkg] = owner;
      if (stem === "postcss-8.5.23") {
        if (builtins.has(specifier)) return nextResolve(specifier, context);
        if (specifier === "nanoid/non-secure") return exact("nanoid-3.3.19", "non-secure/index.cjs");
        if (specifier === "picocolors") return exact("picocolors-1.1.1", "picocolors.js");
        if (specifier === "source-map-js") return exact("source-map-js-1.2.1", "source-map.js");
      }
      if (stem === "parse5-8.0.1") {
        if (specifier === "entities/decode") return exact("entities-8.0.0", "dist/decode.js");
        if (specifier === "entities/escape") return exact("entities-8.0.0", "dist/escape.js");
      }
      if (!specifier.startsWith(".")) reject("UNLISTED_IMPORT");
      const resolved = nextResolve(specifier, context);
      if (!resolved.url?.startsWith("file:")) reject("UNLISTED_IMPORT");
      verifiedPackageMember(pkg, fileURLToPath(resolved.url));
      return resolved;
    },
  });
  return mapper;
}
function safeOutput(value, libraries) {
  if (typeof value !== "string" || !value.startsWith(BASE + "/") ||
      !/^\/vendor\/interactive\/[A-Za-z0-9._@/-]+$/.test(value)) return false;
  const rest = value.slice(BASE.length + 1);
  if (rest.split("/").some((part, index, parts) => part === "." || part === ".." || (!part && index !== parts.length - 1)))
    return false;
  const entry = libraries.find(item => rest.startsWith(`${item.package}@${item.version}/`));
  if (!entry) return false;
  const file = rest.slice(`${entry.package}@${entry.version}/`.length);
  if (!file) return false;
  return entry.files.some(item => file === item ||
    (["build", "examples/jsm", "dist/fonts"].includes(item) && file.startsWith(item + "/") &&
      (file.endsWith(".js") || /\.(?:woff2?|ttf)$/.test(file) || file.endsWith("/"))));
}
function reply(status, extra = {}) {
  const verified = status === "MAPPED" || status === "UNMAPPED" ||
    (status === "REJECTED" && extra.error_code === "UNSAFE_UPSTREAM_PATH");
  return { schema: SCHEMA, status, ...extra, source: "CALLER_SUPPLIED_UNVERIFIED",
    provider: "openmaic", provider_version: "1.3.0", generation_version: "0.3.28",
    expected_source_sha256: ORIGINALS["src/interactive-library-mapper.ts"],
    source_verification: verified ? "VERIFIED_SELECTED_MEMBERS" : "NOT_ASSERTED",
    resource_availability: "NOT_VERIFIED", network_isolation: "NOT_ESTABLISHED",
    security_sanitizer: false, input_script_executed: false, core_authorization: "NOT_ESTABLISHED" };
}
function emit(data) {
  const encoded = JSON.stringify(data);
  if (Buffer.byteLength(encoded, "utf8") > MAX_STDOUT) reject("OUTPUT_TOO_LARGE");
  process.stdout.write(encoded + "\n");
}

try {
  verifyNode();
  const request = parseRequest(await stdinBytes());
  readDonor();
  const packages = readPackages();
  const mapper = installResolver(packages);
  const upstream = await import(pathToFileURL(mapper).href);
  const librariesModule = await import(pathToFileURL(path.join(DONOR, "src", "interactive-libraries.ts")).href);
  const result = upstream.mapInteractiveLibraryUrl(request.url, BASE);
  if (result !== undefined && typeof result !== "string") reject("UPSTREAM_UNEXPECTED_RESULT");
  const detail = { request_id: request.request_id, input_sha256: sha256(request.url),
    upstream_returned: result !== undefined,
    upstream_result_sha256: result === undefined ? null : sha256(result) };
  if (result === undefined) emit(reply("UNMAPPED", { ...detail, path: null }));
  else if (!safeOutput(result, librariesModule.INTERACTIVE_LIBRARIES))
    emit(reply("REJECTED", { ...detail, error_code: "UNSAFE_UPSTREAM_PATH", path: null }));
  else emit(reply("MAPPED", { ...detail, path: result, changed: result !== request.url }));
} catch (error) {
  const code = error instanceof Rejection ? error.code : "INTERNAL_FAILURE";
  emit(reply("REJECTED", { error_code: code, path: null }));
}
