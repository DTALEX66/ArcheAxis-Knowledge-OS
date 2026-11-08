/** Unregistered bounded interactive-outline prompt and replay adapter.
 *
 * It renders the donor 1.3.0 `interactive-outlines` prompt with the vendored
 * `@openmaic/generation` 0.3.28 loader, and (on replay) admits a caller-supplied
 * reply into a bounded outline candidate. No model, network, Core task, scene or
 * persistence happen here.
 */
import { createHash } from "node:crypto";
import { lstatSync, readFileSync } from "node:fs";
import { registerHooks } from "node:module";
import { fileURLToPath } from "node:url";

const SCHEMA = "archeaxis.openmaic-interactive-outline/v1";
const RESULT = "archeaxis.openmaic-interactive-outline-result/v1";
const BINDING = "archeaxis.openmaic-interactive-outline-binding/v1";
const MAX_INPUT = 256_000;
const MAX_OUTPUT = 1_000_000;
const outlineDonor = new URL("./vendor/generation-0.3.28-outline/", import.meta.url);
const promptDonor = new URL("./vendor/prompts-1.3.0-interactive-outline/", import.meta.url);
const npm = new URL("./vendor/npm/", import.meta.url);
const sha = value => createHash("sha256").update(value).digest("hex");
const object = value => !!value && typeof value === "object" && !Array.isArray(value);
const id = value => typeof value === "string" && /^[A-Za-z0-9_-]{1,128}$/.test(value);
const exactKeys = (value, keys) => object(value) && Object.keys(value).length === keys.length &&
  keys.every(key => Object.hasOwn(value, key));
const hex = value => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
const text = (value, limit, required = false) => typeof value === "string" && value.isWellFormed() &&
  !value.includes("\0") && Buffer.byteLength(value, "utf8") <= limit && (!required || !!value.trim());
const strings = (value, count, limit) => Array.isArray(value) && value.length <= count &&
  value.every(item => text(item, limit, true));

function member(path, expected, code) {
  const info = lstatSync(path);
  if (!info.isFile() || info.isSymbolicLink() || info.size > 1_000_000)
    throw new Error(code);
  if (sha(readFileSync(path)) !== expected) throw new Error(code);
}

// The generation files this adapter imports, pinned by their original bytes.
const OUTLINE_MEMBERS = {
  "src/prompts/index.ts": "2d71a8c8e261b773562b2d2597d61690fa547a80c7aca9f5cc329b49a6c987ab",
  "src/prompts/loader.ts": "584bd51c71c53c02e058df5209d9bcb1f73ff531677a9d7a3aa168d135a43e50",
  "src/prompts/types.ts": "ed2a00db125fe1057d876dbb5a9212c38c323731bbc7f4df1c74c5d7be27a8da",
  "src/interactive-libraries.ts": "1c9f212d7e2010dd3e1f4889efe22825fcb1f52772b056e5a30fc58753f29de1",
  "src/json-repair.ts": "dd0cfb6b1224e28c0e96ac5437e06074f5159ab5ec2cb93d4c81784bafcbedff",
  "src/logger.ts": "f8fd9136c2d5a31881c7c00d8a1f1804ba04af5f9d76c85888296e2d0b481306",
};
const PROMPT_MEMBERS = [
  "LICENSE", "README.md",
  "templates/interactive-outlines/system.md", "templates/interactive-outlines/user.md",
  "snippets/image-instructions.md", "snippets/video-instructions.md",
  "snippets/media-safety-guidelines.md",
];
const LOCKED_NPM = {
  "jsonrepair-3.13.3/LICENSE.md": "fd50f5abb7eeb614c8d1293b9f239a5238d7536e3a9a9a8929a082c82d12b3fd",
  "jsonrepair-3.13.3/package.json": "34af00e07186a9ca212bd1065572bbc8d961937728f1a32551ed9016e0e01f41",
  "jsonrepair-3.13.3/lib/esm/index.js": "523d175b61d8517fd3ba90cd2f065c6ecd45f4c95ea7ac706a9d87ccaceb7faf",
  "jsonrepair-3.13.3/lib/esm/regular/jsonrepair.js": "9b7d7367a763931855d1c962e998529f06c6e80a4a056dccb8ebdb96e1d68a1d",
  "jsonrepair-3.13.3/lib/esm/utils/JSONRepairError.js": "760bbdf77243afe6da53aad48520423c2b3da2e15838ca89cb118e87067ef130",
  "jsonrepair-3.13.3/lib/esm/utils/stringUtils.js": "d5e1065bc473e1c06c9ae2c70dae048175fe8b96c7749b00c267fe29f5c322c3",
  "nanoid-5.1.14/LICENSE": "4383cb2c3608397ce7a4159502614ed66890f8999c2a9c056dd3b1024d6721f0",
  "nanoid-5.1.14/package.json": "4b450a13e5bd3bc5be8b5f81274bc0beee02987b00575ae55d61f3837d75244c",
  "nanoid-5.1.14/index.js": "6961295e035ccdd079f0f142ca9e4fc81c46074420e2445c68cab84f1d158465",
  "nanoid-5.1.14/url-alphabet/index.js": "0e1e2118e5e5ad7c1895002997cc1b0ec20bff05ac44ce10cdf78596c5c14ea8",
};
const OUTLINE_MANIFEST_SHA256 = "e9e5396d1676de1bc25e3f9df81f65b5a52724ae9e3bcaf49fb109b82051e9d6";
const PROMPT_MANIFEST_SHA256 = "aec7ba194977aefb8ca3ffcd41911915eb20eec4695ab7d944b9d6038873aa52";

function verifyDonors() {
  const outlineManifest = readFileSync(new URL("ORIGINALS.json", outlineDonor));
  if (sha(outlineManifest) !== OUTLINE_MANIFEST_SHA256) throw new Error("UPSTREAM_MANIFEST_IDENTITY_MISMATCH");
  const originals = JSON.parse(outlineManifest.toString("utf8")).originals;
  if (!object(originals) || Object.keys(originals).length !== 18) throw new Error("UPSTREAM_MANIFEST_IDENTITY_MISMATCH");
  for (const [relative, expected] of Object.entries(OUTLINE_MEMBERS)) member(new URL(relative, outlineDonor), expected, "UPSTREAM_IDENTITY_MISMATCH");
  const promptManifest = readFileSync(new URL("ORIGINALS.json", promptDonor));
  if (sha(promptManifest) !== PROMPT_MANIFEST_SHA256) throw new Error("PROMPT_MANIFEST_IDENTITY_MISMATCH");
  const declared = JSON.parse(promptManifest.toString("utf8")).originals;
  if (!object(declared)) throw new Error("PROMPT_MANIFEST_IDENTITY_MISMATCH");
  for (const relative of PROMPT_MEMBERS) {
    const path = new URL(relative, promptDonor);
    const info = lstatSync(path);
    if (!info.isFile() || info.isSymbolicLink() || info.size > 1_000_000) throw new Error("PROMPT_MEMBER_IDENTITY_MISMATCH");
    const bytes = readFileSync(path);
    if (declared[relative] !== sha(bytes)) throw new Error("PROMPT_MEMBER_IDENTITY_MISMATCH");
  }
  for (const [relative, expected] of Object.entries(LOCKED_NPM)) member(new URL(relative, npm), expected, "LOCKED_NPM_MEMBER_IDENTITY_MISMATCH");
  return { manifest: sha(outlineManifest), promptManifest: PROMPT_MANIFEST_SHA256 };
}

registerHooks({
  resolve(specifier, context, nextResolve) {
    if (context.parentURL?.startsWith(outlineDonor.href)) {
      if (specifier === "nanoid") return { url: new URL("nanoid-5.1.14/index.js", npm).href, shortCircuit: true };
      if (specifier === "jsonrepair") return { url: new URL("jsonrepair-3.13.3/lib/esm/index.js", npm).href, shortCircuit: true };
      if (specifier.startsWith(".") && specifier.endsWith(".js")) {
        const resolved = new URL(specifier.slice(0, -3) + ".ts", context.parentURL).href;
        if (!resolved.startsWith(outlineDonor.href)) throw new Error("OUTLINE_IMPORT_OUTSIDE_DONOR");
        return { url: resolved, shortCircuit: true };
      }
    }
    return nextResolve(specifier, context);
  },
});

const { buildPrompt } = await import(new URL("src/prompts/index.ts", outlineDonor));
const { parseJsonResponse } = await import(new URL("src/json-repair.ts", outlineDonor));
const { nanoid } = await import(new URL("nanoid-5.1.14/index.js", npm));
if (typeof buildPrompt !== "function" || typeof parseJsonResponse !== "function" || typeof nanoid !== "function")
  throw new Error("UNEXPECTED_UPSTREAM_RESULT");

const workerIdentity = sha(readFileSync(new URL(import.meta.url)));
const runtime = Object.freeze({ node_version: process.versions.node, register_hooks_available: typeof registerHooks === "function",
  prompt_template: "interactive-outlines", prompt_loader: "generation-0.3.28", locked_npm_members_checked: true });

// The interactive template's variables. Media remains disabled because this
// adapter has no workspace capability facts; declaring false is not a promise.
const TEMPLATE_VARIABLES = (requirement, source) => ({ requirement, userProfile: "",
  pdfContent: source || "None", availableImages: "No images available", researchContext: "None",
  teacherContext: "", imageEnabled: false, videoEnabled: false, mediaEnabled: false });

const WIDGET_FIELDS = {
  simulation: ["concept", "keyVariables"], diagram: ["diagramType", "nodeCount", "nodes"],
  code: ["language", "challengeType"], game: ["challenge", "gameType", "playerControls", "physicsConcept"],
  visualization3d: ["visualizationType", "objects", "interactions"],
};
const WIDGET_ARRAYS = ["keyVariables", "nodes", "objects", "interactions", "playerControls"];
const ALLOWED_BASE = ["id", "type", "title", "description", "keyPoints", "order"];
// The unmodified donor asks for fixed widget quotas even for a much shorter
// user request. State this adapter's admitted shape and user-first scope in a
// separate, hash-bound host instruction; never rewrite the donor templates.
const OUTPUT_COMPATIBILITY_CONTRACT = [
  "## AAOS output compatibility contract",
  "These rules take precedence over conflicting generic widget distribution rules above or in the user template.",
  "Honor the user's requested scope and scene count when compatible with the output limits. " +
    "Do not impose a minimum number of simulation or game scenes, or a maximum of one diagram.",
  'Scene type must be "slide" or "interactive". Never put the widget name in the scene type.',
  'For an interactive scene set "type" to "interactive" and put the widget name in "widgetType". ' +
    'Supply its "widgetOutline" object. Slides must omit both widget fields.',
  `Scene fields are limited to ${ALLOWED_BASE.join(", ")}, plus widgetType and widgetOutline only for interactive scenes. ` +
    "Do not add languageNote, media fields, or other scene keys.",
  "Allowed widgetOutline fields by widgetType:",
  ...Object.entries(WIDGET_FIELDS).map(([type, fields]) => `- ${type}: ${fields.join(", ")}`),
  `The fields ${WIDGET_ARRAYS.join(", ")} are arrays of strings; nodeCount is an integer from 0 to 200. ` +
    "Other widgetOutline values are strings.",
  "Every scene needs a title, description and keyPoints array. If supplied, IDs must be unique and " +
    "orders must start at 1 and increase by 1. Return 1 to 30 scenes.",
].join("\n");

function rejectDuplicateKeys(source) {
  let p = 0;
  const ws = () => { while (p < source.length && /[\x20\t\r\n]/.test(source[p])) p++; };
  function string() {
    const start = p++;
    while (p < source.length) {
      if (source[p] === "\\") { p += 2; continue; }
      if (source[p++] === '"') return JSON.parse(source.slice(start, p));
    }
    throw new Error("INVALID_JSON");
  }
  function value(depth) {
    if (depth > 64) throw new Error("DEPTH_EXCEEDED");
    ws();
    if (source[p] === '"') { string(); return; }
    if (source[p] === "{") {
      p++; ws(); const keys = new Set();
      if (source[p] === "}") { p++; return; }
      while (p < source.length) {
        ws(); if (source[p] !== '"') throw new Error("INVALID_JSON");
        const key = string(); if (keys.has(key)) throw new Error("DUPLICATE_KEY"); keys.add(key);
        ws(); if (source[p++] !== ":") throw new Error("INVALID_JSON");
        value(depth + 1); ws();
        if (source[p] === "}") { p++; return; }
        if (source[p++] !== ",") throw new Error("INVALID_JSON");
      }
      throw new Error("INVALID_JSON");
    }
    if (source[p] === "[") {
      p++; ws(); if (source[p] === "]") { p++; return; }
      while (p < source.length) {
        value(depth + 1); ws();
        if (source[p] === "]") { p++; return; }
        if (source[p++] !== ",") throw new Error("INVALID_JSON");
      }
      throw new Error("INVALID_JSON");
    }
    const start = p;
    while (p < source.length && !/[\x20\t\r\n,\]}]/.test(source[p])) p++;
    if (p === start) throw new Error("INVALID_JSON");
  }
  value(0); ws(); if (p !== source.length) throw new Error("INVALID_JSON");
}

function requestValid(request) {
  const common = ["schema", "stage", "request_id", "requirement", "source_text"];
  if (!object(request) || request.schema !== SCHEMA || !id(request.request_id) ||
      !text(request.requirement, 8_000, true) || !text(request.source_text, 50_000)) return false;
  if (request.stage === "capture") return exactKeys(request, common);
  if (request.stage !== "replay" || !exactKeys(request, [...common, "binding", "reply"]) ||
      !exactKeys(request.reply, ["kind", "value"]) || request.reply.kind !== "caller_supplied" ||
      !text(request.reply.value, 120_000, true)) return false;
  const binding = request.binding;
  return exactKeys(binding, ["schema", "request_id", "input_sha256", "templates_manifest_sha256",
    "worker_sha256", "system", "user", "system_sha256", "user_sha256"]) &&
    binding.schema === BINDING && id(binding.request_id) && text(binding.system, 200_000) &&
    text(binding.user, 200_000) && [binding.input_sha256, binding.templates_manifest_sha256,
      binding.worker_sha256, binding.system_sha256, binding.user_sha256].every(hex);
}

const inputIdentity = request => sha(JSON.stringify({ request_id: request.request_id,
  requirement: request.requirement, source_text: request.source_text }));

function base(status, reason, request = null) {
  const stage = request && ["capture", "replay"].includes(request.stage) ? request.stage : null;
  return { schema: RESULT, status, reason, request_id: stage && id(request.request_id) ? request.request_id : null,
    stage, response_origin: stage === "replay" ? "CALLER_SUPPLIED_UNVERIFIED" : "NOT_AVAILABLE",
    model_call: "NOT_INVOKED", network_performed: false, core_task: "NOT_CONNECTED",
    core_authorization: "NOT_ESTABLISHED", canonical_bindings_verified: false,
    identity_scope: "UNKEYED_COMPARISON_ONLY", binding_authentication: "NOT_PROVIDED",
    source_snapshot_authority: "CALLER_DECLARED_ONLY", persisted: false, active_content_executed: false,
    sandbox: "NOT_ESTABLISHED", full_generation_chain: false, retry_bytes_stable: false,
    returned_content_may_include_source_material: true, output_privacy_filter: "NOT_APPLIED",
    logging_safety: "NOT_ESTABLISHED", upstream_provider: "openmaic", upstream_version: "1.3.0",
    upstream_generation: "0.3.28", prompt_template: "interactive-outlines", runtime, data: null };
}

function widgetOutlineOk(type, outline) {
  const fields = WIDGET_FIELDS[type];
  if (!fields || !object(outline)) return false;
  for (const key of Object.keys(outline)) {
    if (!fields.includes(key)) return false;
    const value = outline[key];
    if (key === "nodeCount") {
      if (!Number.isInteger(value) || value < 0 || value > 200) return false;
    } else if (WIDGET_ARRAYS.includes(key)) {
      if (!strings(value, 64, 512)) return false;
    } else if (!text(value, 512)) return false;
  }
  return true;
}
const interactiveOk = outline => outline.type === "interactive" && typeof outline.widgetType === "string" &&
  widgetOutlineOk(outline.widgetType, outline.widgetOutline);
const flatOk = outline => outline.type === "slide" && !Object.hasOwn(outline, "widgetType") &&
  !Object.hasOwn(outline, "widgetOutline");

/// Bounded admission of one reply. Only these ordinary widgets and one slide
/// shape are admitted; `procedural-skill`, quiz/pbl and media fields are refused.
function admitted(data, reply) {
  const differences = [], transformations = [];
  const exact = typeof reply === "string" && (() => { try { JSON.parse(reply); return true; } catch { return false; } })();
  if (!exact) transformations.push("UPSTREAM_JSON_REPAIRED");
  if (!object(data)) return { differences: [{ kind: "UPSTREAM_RESULT_SHAPE_UNSUPPORTED" }], transformations };
  if (Object.keys(data).some(key => !["languageDirective", "courseTitle", "outlines"].includes(key))
      || !text(data.languageDirective, 2_000, true)
      || (data.courseTitle !== undefined && !text(data.courseTitle, 120))) {
    differences.push({ kind: "UPSTREAM_RESULT_SHAPE_UNSUPPORTED" });
  }
  if (data.courseTitle !== undefined && typeof data.courseTitle === "string" &&
      data.courseTitle !== data.courseTitle.trim()) differences.push({ kind: "COURSE_TITLE_NORMALIZED" });
  const outlines = data.outlines;
  if (!Array.isArray(outlines) || outlines.length < 1 || outlines.length > 30)
    return { differences: [...differences, { kind: "OUTLINE_COUNT_OR_SHAPE_UNSUPPORTED" }], transformations };
  const seen = new Set();
  const normalized = [];
  for (let index = 0; index < outlines.length; index++) {
    const outline = outlines[index];
    if (!object(outline)) { differences.push({ kind: "OUTLINE_SHAPE_UNSUPPORTED", outline_index: index }); continue; }
    const allowed = ALLOWED_BASE.concat(outline.type === "interactive" ? ["widgetType", "widgetOutline"] : []);
    const unknown = Object.keys(outline).filter(key => !allowed.includes(key));
    if (unknown.length) differences.push({ kind: "UNKNOWN_OUTLINE_FIELDS", outline_index: index, fields: unknown.sort() });
    if (!(flatOk(outline) || interactiveOk(outline)) || !text(outline.title, 240, true) ||
        !text(outline.description, 16_000) || !Array.isArray(outline.keyPoints) ||
        outline.keyPoints.length > 200 || outline.keyPoints.some(point => !text(point, 2_000, true)))
      differences.push({ kind: "OUTLINE_CONTENT_UNSUPPORTED", outline_index: index });
    if (outline.id !== undefined && !id(outline.id)) differences.push({ kind: "OUTLINE_ID_INVALID", outline_index: index });
    if (outline.order !== undefined && (!Number.isSafeInteger(outline.order) || outline.order !== index + 1))
      differences.push({ kind: "OUTLINE_ORDER_OVERWRITTEN", outline_index: index, declared: outline.order });
  }
  if (differences.length) return { differences, transformations };
  for (let index = 0; index < outlines.length; index++) {
    const outline = outlines[index];
    let outlineId = outline.id;
    if (!outlineId) { outlineId = nanoid(); transformations.push("UNSTABLE_GENERATED_OUTLINE_IDS"); }
    if (seen.has(outlineId)) return { differences: [{ kind: "DUPLICATE_OUTLINE_ID", outline_index: index, id: outlineId }], transformations };
    seen.add(outlineId);
    if (outline.order === undefined) transformations.push("OUTLINE_ORDER_ASSIGNED");
    const entry = { id: outlineId, type: outline.type, title: outline.title,
      description: outline.description, keyPoints: outline.keyPoints, order: index + 1 };
    if (outline.type === "interactive") {
      entry.widgetType = outline.widgetType;
      // The mapper keeps only admitted fields, in a stable key order.
      entry.widgetOutline = {};
      for (const key of Object.keys(outline.widgetOutline).sort()) entry.widgetOutline[key] = outline.widgetOutline[key];
    }
    normalized.push(entry);
  }
  const unique = [...new Set(transformations)];
  return { data: { languageDirective: data.languageDirective,
    ...(data.courseTitle !== undefined ? { courseTitle: data.courseTitle } : {}), outlines: normalized },
    transformations: unique };
}

function runtimeWarnings(warnings) { return { warnings }; }

async function processFrame(raw) {
  let request;
  try {
    const source = new TextDecoder("utf-8", { fatal: true }).decode(raw);
    request = JSON.parse(source);
    rejectDuplicateKeys(source);
  } catch {
    return base("INVALID_REQUEST", "invalid bounded UTF-8 JSON or duplicate keys");
  }
  if (!requestValid(request)) return base("INVALID_REQUEST", "request contract or budget rejected", request);
  const identity = inputIdentity(request);
  let prompt;
  try {
    const variables = TEMPLATE_VARIABLES(request.requirement, request.source_text);
    prompt = buildPrompt("interactive-outlines", variables, fileURLToPath(promptDonor));
  } catch {
    return base("PROMPT_UNAVAILABLE", "the interactive-outline template could not be rendered", request);
  }
  if (!exactKeys(prompt, ["system", "user"]) || typeof prompt.system !== "string" || typeof prompt.user !== "string" ||
      Buffer.byteLength(prompt.system, "utf8") > 200_000 || Buffer.byteLength(prompt.user, "utf8") > 200_000)
    return base("UNEXPECTED_UPSTREAM_RESULT", "prompt shape or budget rejected", request);
  prompt = { system: `${prompt.system}\n\n${OUTPUT_COMPATIBILITY_CONTRACT}`, user: prompt.user };
  if (Buffer.byteLength(prompt.system, "utf8") > 200_000)
    return base("UNEXPECTED_UPSTREAM_RESULT", "host prompt exceeds budget", request);
  const binding = { schema: BINDING, request_id: request.request_id, input_sha256: identity,
    templates_manifest_sha256: PROMPT_MANIFEST_SHA256, worker_sha256: workerIdentity,
    system: prompt.system, user: prompt.user,
    system_sha256: sha(prompt.system), user_sha256: sha(prompt.user) };
  if (request.stage === "capture") return { ...base("PROMPT_CAPTURED", null, request), binding };

  const declared = request.binding;
  if (declared.request_id !== request.request_id || declared.input_sha256 !== identity ||
      declared.templates_manifest_sha256 !== PROMPT_MANIFEST_SHA256 || declared.worker_sha256 !== workerIdentity ||
      declared.system !== prompt.system || declared.user !== prompt.user ||
      declared.system_sha256 !== sha(prompt.system) || declared.user_sha256 !== sha(prompt.user))
    return base("BINDING_MISMATCH", "input, prompt or identity differs", request);
  const warnings = [];
  const logger = { debug() {}, info() {}, warn() { warnings.push("UPSTREAM_WARNING"); },
    error() { warnings.push("UPSTREAM_ERROR"); } };
  let parsed;
  try {
    parsed = parseJsonResponse(request.reply.value, { logger });
  } catch {
    return base("INVALID_RESPONSE", "the reply could not be parsed", request);
  }
  if (parsed === null) return base("INVALID_RESPONSE", "the reply could not be parsed", request);
  const result = admitted(parsed, request.reply.value);
  if (result.differences?.length) return { ...base("UNSUPPORTED_OUTPUT", "outline output is outside the interactive slice", request),
    ...runtimeWarnings(warnings), differences: result.differences, transformations: result.transformations };
  return { ...base("CANDIDATE", null, request), ...runtimeWarnings(warnings),
    input_sha256: identity, exact_json_output: typeof request.reply.value === "string" &&
      (() => { try { JSON.parse(request.reply.value); return true; } catch { return false; } })(),
    transformations: result.transformations, data: result.data, human_review_required: true };
}

let output;
if (process.argv.length === 3 && process.argv[2] === "--hello") {
  output = JSON.stringify({ schema: "archeaxis.openmaic-interactive-outline-hello/v1",
    upstream_version: "1.3.0", upstream_generation: "0.3.28", prompt_template: "interactive-outlines",
    model_call: "NOT_INVOKED", runtime }) + "\n";
} else if (process.argv.length !== 2) {
  output = JSON.stringify(base("INVALID_REQUEST", "unsupported arguments")) + "\n";
  process.exitCode = 2;
} else {
  let verified = true;
  try { verifyDonors(); } catch { verified = false; }
  if (!verified) {
    output = JSON.stringify(base("ADAPTER_IDENTITY_MISMATCH", "a pinned donor member changed")) + "\n";
    process.exitCode = 2;
  } else {
    let length = 0, overflow = false;
    const chunks = [];
    for await (const chunk of process.stdin) {
      length += chunk.length;
      if (length > MAX_INPUT) overflow = true;
      if (!overflow) chunks.push(chunk);
    }
    const result = overflow || !length
      ? base("INVALID_REQUEST", "input exceeds byte budget or is empty")
      : await processFrame(Buffer.concat(chunks));
    output = JSON.stringify(result);
    if (Buffer.byteLength(output, "utf8") > MAX_OUTPUT) {
      output = JSON.stringify(base("OUTPUT_TOO_LARGE", "result exceeds the output budget"));
      process.exitCode = 2;
    } else if (result.status !== "PROMPT_CAPTURED" && result.status !== "CANDIDATE") process.exitCode = 2;
  }
}
process.stdout.write(output + "\n");
