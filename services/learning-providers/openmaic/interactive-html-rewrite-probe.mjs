/** Fixed synthetic HTML rewrite probe; not a Core route, sandbox or sanitizer. 
 * Loader adapted from the pinned interactive-url-map worker; original mapper is unchanged. 
 */
import { createHash } from "node:crypto";
import { closeSync, lstatSync, openSync, readFileSync, readSync } from "node:fs";
import { registerHooks } from "node:module";
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const SCHEMA = "archeaxis.openmaic-interactive-html-probe/v1";
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

// Only these constant fixtures can be selected; no caller-supplied HTML is
// parsed. The sentinel file is created and identity-checked by the harness.
const SENTINEL_SHA256 = "8b993d109374915bc45c805deb02b9a4ce695dd912f511efd67833f4c51d58fd";
const SORT_TEMPLATE_SHA256 = "8f0039413e6feed51fa7ac4093658fda70d90fb5877ca2343b0ed4be7a3dafe0";
const INLINE_MAP = "eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbImlucHV0LmNzcyJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiQUFBQSIsInNvdXJjZXNDb250ZW50IjpbIlNZTlRIRVRJQ19NQVAiXX0=";
const FIXTURES = {
  attributes: `<script SRC='https://unpkg.com/chart.js@4' integrity='sha384-old' crossorigin='use-credentials'></script>`,
  crlf: `<p>outside\r\nkeep</p><style>\r\n@import "https://unpkg.com/chart.js@4";\r\n</style>`,
  unscanned: `<img src="https://outside.invalid/p.png"><script src="https://unpkg.com/chart.js@4" src="https://hidden.invalid/a.js"></script>`,
  broken_css: `<style>@import "https://outside.invalid/x.css";a{</style>`,
  external_map: `<style>/*# sourceMappingURL=fixture.css.map */\n@import "https://unpkg.com/chart.js@4";</style>`,
  inline_valid: `<style>/*# sourceMappingURL=data:application/json;base64,${INLINE_MAP} */\n@import "https://unpkg.com/chart.js@4";</style>`,
  inline_invalid: `<style>/*# sourceMappingURL=data:application/json;base64,bm90LWpzb24= */\n@import "https://unpkg.com/chart.js@4";</style>`,
  inline_broken_css: `<style>/*# sourceMappingURL=data:application/json;base64,${INLINE_MAP} */\na{</style>`,
  input_script: `<script>globalThis.__AAOS_HTML_SCRIPT_EXECUTED=true;</script><script type="module">globalThis.__AAOS_HTML_SCRIPT_EXECUTED=true;</script>`,
  unicode: `<p>😀before</p><script src="https://unpkg.com/chart.js@4"></script><p>字后</p>`,
  marker_red: `<p>SYNTHETIC_MARKER_CONTROL</p>`,
};

async function readFixtureName() {
  const chunks = [];
  let length = 0;
  const timer = setTimeout(() => process.stdin.destroy(new Rejection("INPUT_TIMEOUT")), 10_000);
  try {
    for await (const chunk of process.stdin) {
      length += chunk.length;
      if (length > 128) reject("INPUT_TOO_LARGE");
      chunks.push(chunk);
    }
  } finally {
    clearTimeout(timer);
  }
  let text;
  try { text = new TextDecoder("utf-8", { fatal: true }).decode(Buffer.concat(chunks, length)); }
  catch { reject("INVALID_FIXTURE"); }
  if (!/^[a-z_]+\n$/.test(text)) reject("INVALID_FIXTURE");
  const name = text.slice(0, -1);
  if (!Object.hasOwn(FIXTURES, name)) reject("INVALID_FIXTURE");
  return name;
}
function output(data) {
  const encoded = JSON.stringify({ schema: SCHEMA, ...data, scope: "FIXED_SYNTHETIC_UNVERIFIED",
    expected_source_sha256: ORIGINALS["src/interactive-library-mapper.ts"],
    source_verification: data.status === "OBSERVED" ? "VERIFIED_SELECTED_MEMBERS" : "NOT_ASSERTED",
    node_version: process.versions.node,
    recorded_owner_archive_sha256: "7cea2a5850083bdc261114d8433daa6ea24c1c0157beae3939a2e9fac3a98f40",
    owner_archive_reverified_in_probe: false,
    synthetic_marker_observed: syntheticMarkerObservation,
    synthetic_marker_control: markerForcedByProbe ? "FORCED_BY_PROBE" : "NONE",
    resource_availability: "NOT_VERIFIED",
    network_isolation: "NOT_ESTABLISHED", security_sanitizer: false, core_authorization: "NOT_ESTABLISHED" });
  if (Buffer.byteLength(encoded, "utf8") > MAX_STDOUT) reject("OUTPUT_TOO_LARGE");
  process.stdout.write(encoded + "\n");
}

// Diagnostic metadata only: unmatched bodies are never emitted or executed.
let blockedDynamicObservation = null;
let trustedDynamicObservation = null;
let syntheticMarkerObservation = "NOT_OBSERVED";
let markerForcedByProbe = false;
function observeBlockedDynamic(kind, args) {
  const value = args.length === 1 && typeof args[0] === "string" ? args[0] : null;
  const bytes = value === null ? null : Buffer.byteLength(value, "utf8");
  blockedDynamicObservation = { kind, argument_count: args.length,
    argument_type: args.length === 1 ? typeof args[0] : null,
    utf8_bytes: bytes, sha256: bytes !== null && bytes <= 1_000_000 ? sha256(value) : null };
}

try {
  verifyNode();
  const name = await readFixtureName();
  const html = FIXTURES[name];
  if (Buffer.byteLength(html, "utf8") > 2_048) reject("FIXTURE_TOO_LARGE");
  readDonor();
  const packages = readPackages();

  // This preflight intentionally reads only the synthetic sentinel. Counters
  // below measure the upstream call and a separate explicit positive control.
  const sentinel = path.resolve(process.cwd(), "fixture.css.map");
  let stat;
  try { stat = lstatSync(sentinel); } catch { reject("SENTINEL_IDENTITY_MISMATCH"); }
  if (!stat.isFile() || stat.isSymbolicLink() || stat.size > 1_024 ||
      sha256(readFileSync(sentinel)) !== SENTINEL_SHA256) reject("SENTINEL_IDENTITY_MISMATCH");
  let phase = "load";
  const observations = { mapper_exists: 0, mapper_read: 0, control_exists: 0, control_read: 0 };
  const originalExists = fs.existsSync;
  const originalRead = fs.readFileSync;
  function isSentinel(candidate) {
    return typeof candidate === "string" && path.resolve(candidate) === sentinel;
  }
  fs.existsSync = function(candidate, ...rest) {
    if (isSentinel(candidate) && phase === "mapper") observations.mapper_exists++;
    if (isSentinel(candidate) && phase === "control") observations.control_exists++;
    return originalExists.call(this, candidate, ...rest);
  };
  fs.readFileSync = function(candidate, ...rest) {
    if (isSentinel(candidate) && phase === "mapper") observations.mapper_read++;
    if (isSentinel(candidate) && phase === "control") observations.control_read++;
    return originalRead.call(this, candidate, ...rest);
  };

  const mapper = installResolver(packages);
  const upstream = await import(pathToFileURL(mapper).href);
  const originalFunction = globalThis.Function;
  let templateCompilations = 0;
  let blockedDynamicCode = false;
  // This proxy observes direct globalThis.Function calls/constructs during
  // this invocation only. Earlier imports, captured aliases, and eval are not
  // covered. It is a fixed-fixture observation, not a code-generation sandbox.
  globalThis.Function = new Proxy(originalFunction, {
    construct(target, args) {
      if (args.length !== 1 || typeof args[0] !== "string" || sha256(args[0]) !== SORT_TEMPLATE_SHA256) {
        blockedDynamicCode = true;
        observeBlockedDynamic("construct", args);
        throw new Error("UNLISTED_DYNAMIC_CODE");
      }
      templateCompilations++;
      trustedDynamicObservation = { kind: "construct", argument_count: 1, argument_type: "string",
        utf8_bytes: Buffer.byteLength(args[0], "utf8"), sha256: sha256(args[0]) };
      return Reflect.construct(target, args);
    },
    apply(target, receiver, args) {
      blockedDynamicCode = true;
      observeBlockedDynamic("apply", args);
      throw new Error("UNLISTED_DYNAMIC_CODE");
    },
  });
  globalThis.__AAOS_HTML_SCRIPT_EXECUTED = false;
  let rewritten;
  try {
    phase = "mapper";
    rewritten = upstream.rewriteInteractiveLibraries(html, BASE);
  } finally {
    phase = "after";
    globalThis.Function = originalFunction;
  }
  if (blockedDynamicCode) reject("UNLISTED_DYNAMIC_CODE");
  if (name === "marker_red") {
    // Exercise the red branch without executing any input script.
    globalThis.__AAOS_HTML_SCRIPT_EXECUTED = true;
    markerForcedByProbe = true;
  }
  syntheticMarkerObservation = globalThis.__AAOS_HTML_SCRIPT_EXECUTED !== false;
  delete globalThis.__AAOS_HTML_SCRIPT_EXECUTED;
  if (syntheticMarkerObservation) reject("SYNTHETIC_MARKER_TRIGGERED");
  if (!rewritten || typeof rewritten.html !== "string" || !rewritten.unmatchedExternalHosts ||
      typeof rewritten.unmatchedExternalHosts !== "object" || Array.isArray(rewritten.unmatchedExternalHosts))
    reject("UPSTREAM_UNEXPECTED_RESULT");
  if (Buffer.byteLength(rewritten.html, "utf8") > 4_096) reject("OUTPUT_TOO_LARGE");

  let positiveControl = "NOT_RUN";
  if (name === "external_map") {
    // Unlike the upstream call, this explicitly supplies `from` to demonstrate
    // that the instrumentation sees reads of the known synthetic sentinel.
    const anchor = pathToFileURL(path.join(packages.get("postcss-8.5.23").root, "lib", "postcss.js"));
    const requireFromPostcss = createRequire(anchor);
    const postcss = requireFromPostcss("./postcss.js");
    phase = "control";
    const css = `/*# sourceMappingURL=fixture.css.map */\na{color:red}`;
    try {
      postcss.parse(css, { from: path.resolve(process.cwd(), "fixture.css") });
      positiveControl = "COMPLETED";
    } catch {
      positiveControl = "FAILED";
    } finally {
      phase = "after";
    }
  }
  fs.existsSync = originalExists;
  fs.readFileSync = originalRead;
  output({ status: "OBSERVED", fixture: name, input_html: html, output_html: rewritten.html,
    input_sha256: sha256(html), output_sha256: sha256(rewritten.html),
    unmatched_external_hosts: rewritten.unmatchedExternalHosts,
    sentinel_preflight_read: true, sentinel_calls: observations,
    source_map_positive_control: positiveControl, trusted_template_compilations: templateCompilations,
    trusted_dynamic_observation: trustedDynamicObservation });
} catch (error) {
  const code = error instanceof Rejection ? error.code : "INTERNAL_FAILURE";
  output({ status: "REJECTED", error_code: code,
    ...(code === "UNLISTED_DYNAMIC_CODE" ? { blocked_dynamic_observation: blockedDynamicObservation } : {}) });
}
