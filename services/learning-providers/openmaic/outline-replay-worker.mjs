/** Bounded synthetic replay of the upstream outline function. No model, network or Core task. */
import { createHash } from "node:crypto";
import { registerHooks } from "node:module";
import { lstatSync, readFileSync } from "node:fs";

const donor = new URL("./vendor/generation-0.3.28-outline/", import.meta.url);
const npm = new URL("./vendor/npm/", import.meta.url);
const upstreamManifest = new URL("ORIGINALS.json", donor);
const manifestBytes = readFileSync(upstreamManifest);
if (createHash("sha256").update(manifestBytes).digest("hex") !== "e9e5396d1676de1bc25e3f9df81f65b5a52724ae9e3bcaf49fb109b82051e9d6")
  throw new Error("UPSTREAM_MANIFEST_IDENTITY_MISMATCH");
const originalMembers = JSON.parse(manifestBytes.toString("utf8")).originals;
if (!originalMembers || Object.keys(originalMembers).length !== 18) throw new Error("UPSTREAM_MANIFEST_IDENTITY_MISMATCH");
for (const [relative, expected] of Object.entries(originalMembers)) {
  const path = new URL(relative, donor);
  if (!path.href.startsWith(donor.href)) throw new Error("UPSTREAM_MEMBER_IDENTITY_MISMATCH");
  const info = lstatSync(path);
  if (!info.isFile() || info.isSymbolicLink() || info.size > 1_000_000 ||
      createHash("sha256").update(readFileSync(path)).digest("hex") !== expected)
    throw new Error("UPSTREAM_MEMBER_IDENTITY_MISMATCH");
}
const lockedMembers = {
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
for (const [relative, expected] of Object.entries(lockedMembers)) {
  const path = new URL(relative, npm);
  const info = lstatSync(path);
  if (!info.isFile() || info.isSymbolicLink() || info.size > 1_000_000 ||
      createHash("sha256").update(readFileSync(path)).digest("hex") !== expected)
    throw new Error("LOCKED_NPM_MEMBER_IDENTITY_MISMATCH");
}
const nanoid = new URL("nanoid-5.1.14/index.js", npm).href;
const jsonrepair = new URL("jsonrepair-3.13.3/lib/esm/index.js", npm).href;
const guardPath = new URL("./outline-prompt-guard.mjs", import.meta.url);
const guardInfo = lstatSync(guardPath);
if (!guardInfo.isFile() || guardInfo.isSymbolicLink() || guardInfo.size > 1_000_000)
  throw new Error("OUTLINE_GUARD_IDENTITY_MISMATCH");
const guardIdentity = createHash("sha256").update(readFileSync(guardPath)).digest("hex");
if (guardIdentity !== "5691dcaaeaa37e2bde624656a711c82663a8afc21a1d579da14194b516b4c584")
  throw new Error("OUTLINE_GUARD_IDENTITY_MISMATCH");
const { createPromptGuard } = await import(guardPath);

// Upstream's built JS uses .js imports. This local source-only slice keeps the
// original bytes and resolves only its own relative imports to their .ts files.
registerHooks({
  resolve(specifier, context, nextResolve) {
    if (context.parentURL?.startsWith(donor.href)) {
      if (specifier === "nanoid") return { url: nanoid, shortCircuit: true };
      if (specifier === "jsonrepair") return { url: jsonrepair, shortCircuit: true };
      if (specifier.startsWith(".") && specifier.endsWith(".js")) {
        const resolved = new URL(specifier.slice(0, -3) + ".ts", context.parentURL).href;
        if (!resolved.startsWith(donor.href)) throw new Error("OUTLINE_IMPORT_OUTSIDE_DONOR");
        return { url: resolved, shortCircuit: true };
      }
    }
    return nextResolve(specifier, context);
  },
});

const { generateSceneOutlinesFromRequirements } = await import(new URL("src/outline-generator.ts", donor));
const runtime = Object.freeze({ node_version: process.versions.node,
  register_hooks_available: typeof registerHooks === "function",
  original_typescript_imported: typeof generateSceneOutlinesFromRequirements === "function",
  locked_npm_members_checked: true, upstream_members_checked: true });
const MAX_INPUT = 256_000;
const MAX_OUTPUT = 1_000_000;
const id = value => typeof value === "string" && /^[A-Za-z0-9_-]{1,128}$/.test(value);
const object = value => !!value && typeof value === "object" && !Array.isArray(value);
const sha = value => createHash("sha256").update(value).digest("hex");

// JSON.parse accepts duplicate keys, so independently scan decoded key identity.
function rejectDuplicateKeys(source) {
  let p = 0;
  const whitespace = () => { while (p < source.length && /[\x20\t\r\n]/.test(source[p])) p++; };
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
    whitespace();
    if (source[p] === '"') { string(); return; }
    if (source[p] === "{") {
      p++; whitespace();
      const keys = new Set();
      if (source[p] === "}") { p++; return; }
      while (p < source.length) {
        whitespace(); if (source[p] !== '"') throw new Error("INVALID_JSON");
        const key = string(); if (keys.has(key)) throw new Error("DUPLICATE_KEY"); keys.add(key);
        whitespace(); if (source[p++] !== ":") throw new Error("INVALID_JSON");
        value(depth + 1); whitespace();
        if (source[p] === "}") { p++; return; }
        if (source[p++] !== ",") throw new Error("INVALID_JSON");
      }
      throw new Error("INVALID_JSON");
    }
    if (source[p] === "[") {
      p++; whitespace(); if (source[p] === "]") { p++; return; }
      while (p < source.length) {
        value(depth + 1); whitespace();
        if (source[p] === "]") { p++; return; }
        if (source[p++] !== ",") throw new Error("INVALID_JSON");
      }
      throw new Error("INVALID_JSON");
    }
    const start = p;
    while (p < source.length && !/[\x20\t\r\n,\]}]/.test(source[p])) p++;
    if (p === start) throw new Error("INVALID_JSON");
  }
  value(0); whitespace(); if (p !== source.length) throw new Error("INVALID_JSON");
}

function requestValid(r) {
  if (!object(r) || Object.keys(r).length !== 5 ||
      ["schema", "request_id", "requirement", "source_text", "reply"].some(k => !Object.hasOwn(r, k)) ||
      r.schema !== "archeaxis.openmaic-outline-replay/v1" || !id(r.request_id) ||
      typeof r.requirement !== "string" || !r.requirement.trim() || r.requirement.length > 8_000 ||
      typeof r.source_text !== "string" || r.source_text.length > 50_000 || !object(r.reply)) return false;
  if (r.reply.kind === "synthetic_error") return Object.keys(r.reply).length === 1;
  return r.reply.kind === "synthetic_response" && Object.keys(r.reply).length === 2 &&
    typeof r.reply.value === "string" && Buffer.byteLength(r.reply.value, "utf8") <= 120_000;
}

function base(status, reason, input = null) {
  return { schema: "archeaxis.openmaic-outline-replay-result/v1", status, reason,
    input, upstream_generation: "0.3.28", upstream_entry: "generateSceneOutlinesFromRequirements",
    // SYNTHETIC_REPLAY is the caller's declaration, not verified provenance.
    // The legacy input and observed results may contain material or answers.
    response_origin: "SYNTHETIC_REPLAY", response_origin_verification: "CALLER_DECLARED_UNVERIFIED",
    returned_content_may_include_source_material: true, output_privacy_filter: "NOT_APPLIED",
    logging_safety: "NOT_ESTABLISHED", model_call: "NOT_INVOKED", network_performed: false,
    core_task: "NOT_CONNECTED", canonical_bindings_verified: false, full_generation_chain: false,
    jsonrepair_dependency: "LOCKED_3.13.3", nanoid_dependency: "LOCKED_5.1.14",
    retry_bytes_stable: false, runtime, data: null };
}

const PROMPT_SCHEMA = "archeaxis.openmaic-outline-prompt/v1";
const BINDING_SCHEMA = "archeaxis.openmaic-outline-prompt-binding/v1";
const memberIdentity = sha(JSON.stringify(lockedMembers));
const manifestIdentity = sha(manifestBytes);
const workerPath = new URL(import.meta.url);
const workerInfo = lstatSync(workerPath);
if (!workerInfo.isFile() || workerInfo.isSymbolicLink() || workerInfo.size > 1_000_000)
  throw new Error("OUTLINE_WORKER_IDENTITY_UNAVAILABLE");
const workerIdentity = sha(readFileSync(workerPath));
const exactKeys = (value, keys) => object(value) && Object.keys(value).length === keys.length &&
  keys.every(key => Object.hasOwn(value, key));
const wellFormedText = (value, chars, required = false) => typeof value === "string" &&
  value.isWellFormed() && value.length <= chars && !value.includes("\0") && (!required || !!value.trim());
const promptText = value => typeof value === "string" && value.isWellFormed() &&
  Buffer.byteLength(value, "utf8") <= 200_000;
const hashText = value => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);

function promptInputIdentity(request) {
  // This is an unkeyed identity comparison, not authentication or a Core grant.
  // For example, an empty source and the literal "None" yield the same upstream
  // prompt. A caller can recompute this hash; Core must bind its own retained
  // original snapshot and result before any trusted use.
  return sha(JSON.stringify({ request_id: request.request_id, requirement: request.requirement,
    source_text: request.source_text }));
}

function promptRequestValid(request) {
  const common = ["schema", "stage", "request_id", "requirement", "source_text"];
  if (!object(request) || request.schema !== PROMPT_SCHEMA || !id(request.request_id) ||
      !wellFormedText(request.requirement, 8_000, true) || !wellFormedText(request.source_text, 50_000)) return false;
  if (request.stage === "capture") return exactKeys(request, common);
  if (request.stage !== "replay" || !exactKeys(request, [...common, "binding", "reply"]) ||
      !exactKeys(request.reply, ["kind", "value"]) || request.reply.kind !== "caller_supplied" ||
      typeof request.reply.value !== "string" || !request.reply.value.isWellFormed() ||
      Buffer.byteLength(request.reply.value, "utf8") > 120_000) return false;
  const binding = request.binding;
  return exactKeys(binding, ["schema", "request_id", "input_sha256", "upstream_manifest_sha256",
    "npm_members_sha256", "worker_sha256", "guard_sha256", "system", "user", "system_sha256", "user_sha256"]) &&
    binding.schema === BINDING_SCHEMA && id(binding.request_id) && promptText(binding.system) &&
    promptText(binding.user) && [binding.input_sha256, binding.upstream_manifest_sha256,
      binding.npm_members_sha256, binding.worker_sha256, binding.guard_sha256,
      binding.system_sha256, binding.user_sha256].every(hashText);
}

function promptBase(status, reason, request) {
  // Never reflect unvalidated requests or whole materials, prompts and replies
  // into routine receipts. Explicit observations below are bounded but can
  // still contain source material; this worker does not filter private data.
  const validated = ["PROMPT_CAPTURED", "BINDING_MISMATCH", "CALLBACK_REJECTED", "UPSTREAM_FAILURE",
    "INVALID_RESPONSE", "UPSTREAM_RECOVERY_NOT_ADMITTED", "UPSTREAM_RESULT_NOT_ADMITTED", "CANDIDATE"].includes(status);
  const stage = validated && ["capture", "replay"].includes(request?.stage) ? request.stage : null;
  return { schema: "archeaxis.openmaic-outline-prompt-result/v1", status, reason,
    request_id: stage && id(request?.request_id) ? request.request_id : null, stage,
    response_origin: stage === "replay" ? "CALLER_SUPPLIED_UNVERIFIED" : "NOT_AVAILABLE",
    model_call: "NOT_INVOKED", network_performed: false, core_task: "NOT_CONNECTED",
    core_authorization: "NOT_ESTABLISHED", canonical_bindings_verified: false,
    identity_scope: "UNKEYED_COMPARISON_ONLY", binding_authentication: "NOT_PROVIDED",
    source_snapshot_authority: "CALLER_DECLARED_ONLY", persisted: false, active_content_executed: false,
    sandbox: "NOT_ESTABLISHED", full_generation_chain: false, retry_bytes_stable: false,
    returned_content_may_include_source_material: true, output_privacy_filter: "NOT_APPLIED",
    logging_safety: "NOT_ESTABLISHED",
    upstream_generation: "0.3.28", runtime, data: null };
}

// The ordinary interactive widgets this adapter admits. `procedural-skill` needs
// the donor's explicit allow flag upstream; this slice refuses it instead of
// silently turning it into a diagram outline.
const INTERACTIVE_WIDGET_FIELDS = {
  simulation: ["concept", "keyVariables"], diagram: ["diagramType", "nodeCount", "nodes"],
  code: ["language"], game: ["gameType"],
  visualization3d: ["visualizationType", "objects", "interactions"],
};
const WIDGET_ARRAYS = ["keyVariables", "nodes", "objects", "interactions"];

/// The donor `WidgetOutline` shape, narrowed to the fields the interactive prompt
/// adapter accepts. The names are the outline (camelCase) form; Core maps them to
/// the adapter's snake_case prompt frame. Unknown fields and over-budget values
/// are refused rather than trimmed.
function widgetOutlineSupported(type, outline) {
  if (!Object.hasOwn(INTERACTIVE_WIDGET_FIELDS, type) || !object(outline)) return false;
  for (const key of Object.keys(outline)) {
    if (!INTERACTIVE_WIDGET_FIELDS[type].includes(key)) return false;
    const value = outline[key];
    if (key === "nodeCount") {
      if (!Number.isInteger(value) || value < 0 || value > 200) return false;
    } else if (WIDGET_ARRAYS.includes(key)) {
      if (!Array.isArray(value) || value.length > 64 ||
          value.some(item => typeof item !== "string" || item.length > 512)) return false;
    } else if (typeof value !== "string" || value.length > 512) return false;
  }
  return true;
}

/// An `interactive` outline carries exactly one ordinary widget and its outline.
function interactiveOutlineSupported(outline) {
  return outline.type === "interactive" && typeof outline.widgetType === "string" &&
    widgetOutlineSupported(outline.widgetType, outline.widgetOutline);
}

/// A slide/quiz outline carries no widget fields in this slice.
function flatOutlineSupported(outline) {
  return ["slide", "quiz"].includes(outline.type) && !Object.hasOwn(outline, "widgetType") &&
    !Object.hasOwn(outline, "widgetOutline");
}

/// Structural checks for a reply the donor already repaired. They mirror the
/// text-only slice: a candidate is a course title, one language directive and
/// 1-30 slide/quiz/interactive outlines with bounded text and no media references.
function repairedOutlineDifferences(data) {
  if (!object(data) || Object.keys(data).some(k => !["languageDirective", "courseTitle", "outlines"].includes(k)) ||
      !wellFormedText(data.languageDirective, 2_000, true) ||
      (data.courseTitle !== undefined && !wellFormedText(data.courseTitle, 120, true)))
    return [{ kind: "UPSTREAM_RESULT_SHAPE_UNSUPPORTED" }];
  const outlines = data.outlines;
  if (!Array.isArray(outlines) || outlines.length < 1 || outlines.length > 30)
    return [{ kind: "OUTLINE_COUNT_OR_SHAPE_UNSUPPORTED" }];
  const differences = [];
  for (let index = 0; index < outlines.length; index++) {
    const outline = outlines[index];
    if (!object(outline) || !id(outline.id) ||
        !(flatOutlineSupported(outline) || interactiveOutlineSupported(outline)) ||
        typeof outline.title !== "string" || !outline.title.trim() || outline.title.length > 240 ||
        typeof outline.description !== "string" || outline.description.length > 16_000 ||
        !Array.isArray(outline.keyPoints) || outline.keyPoints.length > 200 ||
        outline.keyPoints.some(point => typeof point !== "string" || point.length > 2_000) ||
        (Array.isArray(outline.mediaGenerations) && outline.mediaGenerations.length) ||
        (Array.isArray(outline.suggestedImageIds) && outline.suggestedImageIds.length))
      differences.push({ kind: "OUTLINE_SHAPE_UNSUPPORTED", outline_index: index });
  }
  return differences;
}

function inspectPromptOutline(parsed, upstream) {
  const differences = [], transformations = [];
  const rawOutlines = Array.isArray(parsed) ? parsed : parsed?.outlines;
  const observed = upstream?.data?.outlines;
  if (!object(upstream?.data) || Object.keys(upstream.data).some(k => !["languageDirective", "courseTitle", "outlines"].includes(k)) ||
      !wellFormedText(upstream.data.languageDirective, 2_000, true) ||
      (upstream.data.courseTitle !== undefined && !wellFormedText(upstream.data.courseTitle, 120, true)))
    differences.push({ kind: "UPSTREAM_RESULT_SHAPE_UNSUPPORTED" });
  if (!Array.isArray(parsed)) {
    if (!object(parsed)) return { differences: [{ kind: "UNKNOWN_RESPONSE_SHAPE" }], transformations };
    const unknown = Object.keys(parsed).filter(k => !["languageDirective", "courseTitle", "outlines"].includes(k));
    if (unknown.length) differences.push({ kind: "UNKNOWN_RESPONSE_FIELDS", fields: unknown.sort() });
    if (Object.hasOwn(parsed, "languageDirective") && !wellFormedText(parsed.languageDirective, 2_000, true))
      differences.push({ kind: "INVALID_LANGUAGE_DIRECTIVE" });
    if (Object.hasOwn(parsed, "courseTitle") && !wellFormedText(parsed.courseTitle, 1_000, true))
      differences.push({ kind: "INVALID_COURSE_TITLE" });
    else if (Object.hasOwn(parsed, "courseTitle") && parsed.courseTitle !== upstream?.data?.courseTitle)
      differences.push({ kind: "COURSE_TITLE_NORMALIZED", original: parsed.courseTitle,
        observed: upstream?.data?.courseTitle ?? null });
  }
  if (!Array.isArray(rawOutlines) || !Array.isArray(observed) || rawOutlines.length < 1 ||
      rawOutlines.length > 30 || rawOutlines.length !== observed.length) {
    differences.push({ kind: "OUTLINE_COUNT_OR_SHAPE_UNSUPPORTED" });
    return { differences, transformations };
  }
  if (Array.isArray(parsed) || !Object.hasOwn(parsed, "languageDirective")) transformations.push("DEFAULT_LANGUAGE_DIRECTIVE");
  const seenIds = new Map();
  for (let index = 0; index < rawOutlines.length; index++) {
    const source = rawOutlines[index], result = observed[index];
    if (!object(source) || !object(result)) {
      differences.push({ kind: "OUTLINE_SHAPE_UNSUPPORTED", outline_index: index });
      continue;
    }
    const allowed = ["id", "type", "title", "description", "keyPoints", "order", "quizConfig",
      "mediaGenerations", "suggestedImageIds"].concat(
      source.type === "interactive" ? ["widgetType", "widgetOutline"] : []);
    const unknown = Object.keys(source).filter(key => !allowed.includes(key));
    if (unknown.length) differences.push({ kind: "UNKNOWN_OUTLINE_FIELDS", outline_index: index, fields: unknown.sort() });
    if (!(source.type === "interactive"
      ? interactiveOutlineSupported(source)
      : flatOutlineSupported(source)) || !wellFormedText(source.title, 240, true) ||
        !wellFormedText(source.description, 16_000) || !Array.isArray(source.keyPoints) ||
        source.keyPoints.length > 200 || source.keyPoints.some(p => !wellFormedText(p, 2_000)))
      differences.push({ kind: "OUTLINE_CONTENT_UNSUPPORTED", outline_index: index });
    if (Object.hasOwn(source, "id")) {
      if (!id(source.id) || result.id !== source.id) differences.push({ kind: "OUTLINE_ID_MISMATCH", outline_index: index });
    } else if (id(result.id)) {
      if (!transformations.includes("UNSTABLE_GENERATED_OUTLINE_IDS")) transformations.push("UNSTABLE_GENERATED_OUTLINE_IDS");
    } else differences.push({ kind: "OUTLINE_ID_MISMATCH", outline_index: index });
    if (id(result.id)) {
      if (seenIds.has(result.id)) differences.push({ kind: "DUPLICATE_OUTLINE_ID", outline_index: index,
        first_outline_index: seenIds.get(result.id), id: result.id });
      else seenIds.set(result.id, index);
    }
    if (Object.hasOwn(source, "order")) {
      if (!Number.isSafeInteger(source.order) || source.order !== result.order)
        differences.push({ kind: "OUTLINE_ORDER_OVERWRITTEN", outline_index: index,
          original: source.order, observed: result.order });
    } else if (!transformations.includes("OUTLINE_ORDER_ASSIGNED")) transformations.push("OUTLINE_ORDER_ASSIGNED");
    if (result.order !== index + 1) differences.push({ kind: "OUTLINE_ORDER_MISMATCH", outline_index: index });
    if (Object.hasOwn(source, "mediaGenerations")) {
      if (!Array.isArray(source.mediaGenerations))
        differences.push({ kind: "INVALID_MEDIA_GENERATIONS_DROPPED", outline_index: index });
      else if (source.mediaGenerations.length) differences.push({ kind: "MEDIA_UNSUPPORTED", outline_index: index });
    }
    if (Object.hasOwn(source, "suggestedImageIds") &&
        (!Array.isArray(source.suggestedImageIds) || source.suggestedImageIds.length))
      differences.push({ kind: "IMAGES_UNSUPPORTED", outline_index: index });
    if (Object.hasOwn(source, "quizConfig")) {
      const c = source.quizConfig;
      if (source.type !== "quiz" || !exactKeys(c, ["questionCount", "difficulty", "questionTypes"]) ||
          !Number.isInteger(c.questionCount) || c.questionCount < 1 || c.questionCount > 30 ||
          !["easy", "medium", "hard"].includes(c.difficulty) || !Array.isArray(c.questionTypes) ||
          c.questionTypes.length < 1 || c.questionTypes.length > 3 ||
          c.questionTypes.some(t => !["single", "multiple", "short_answer"].includes(t)) ||
          new Set(c.questionTypes).size !== c.questionTypes.length)
        differences.push({ kind: "QUIZ_CONFIG_UNSUPPORTED", outline_index: index });
    }
    if (result.type !== source.type || result.title !== source.title || result.description !== source.description ||
        JSON.stringify(result.keyPoints) !== JSON.stringify(source.keyPoints) ||
        (Object.hasOwn(source, "quizConfig") && JSON.stringify(result.quizConfig) !== JSON.stringify(source.quizConfig)) ||
        (Object.hasOwn(source, "widgetType") && JSON.stringify(result.widgetType) !== JSON.stringify(source.widgetType)) ||
        (Object.hasOwn(source, "widgetOutline") && JSON.stringify(result.widgetOutline) !== JSON.stringify(source.widgetOutline)))
      differences.push({ kind: "OUTLINE_PROJECTION_MISMATCH", outline_index: index });
  }
  return { differences, transformations };
}

async function processPromptFrame(request) {
  if (!promptRequestValid(request)) return promptBase("INVALID_REQUEST", "prompt request contract or budget rejected", request);
  const inputIdentity = promptInputIdentity(request);
  const binding = request.binding;
  if (request.stage === "replay" && (binding.request_id !== request.request_id || binding.input_sha256 !== inputIdentity ||
      binding.upstream_manifest_sha256 !== manifestIdentity || binding.npm_members_sha256 !== memberIdentity ||
      binding.worker_sha256 !== workerIdentity || binding.guard_sha256 !== guardIdentity ||
      binding.system_sha256 !== sha(binding.system) || binding.user_sha256 !== sha(binding.user)))
    return promptBase("BINDING_MISMATCH", "input, prompt or donor identity differs", request);

  const warnings = [];
  const logger = { debug() {}, info() {}, warn() { warnings.push("UPSTREAM_WARNING"); },
    error() { warnings.push("UPSTREAM_ERROR"); } };
  let parsed, exact = false, invalidResponse = false;
  const guard = createPromptGuard(request.stage === "replay" ? binding : null, () => {
    if (request.stage === "capture") throw new Error("OUTLINE_PROMPT_CAPTURE_ONLY");
    try { parsed = JSON.parse(request.reply.value); exact = true; } catch { /* allow observation, not admission */ }
    if (exact) {
      try { rejectDuplicateKeys(request.reply.value); } catch { invalidResponse = true; throw new Error("INVALID_RESPONSE"); }
    }
    return request.reply.value;
  });
  let upstream;
  try {
    upstream = await generateSceneOutlinesFromRequirements({ requirement: request.requirement },
      request.source_text || undefined, undefined, guard.callback, { logger });
  } catch {
    return { ...promptBase("UPSTREAM_FAILURE", "upstream outline function raised", request), callback_count: guard.state.calls, warnings };
  }
  if (guard.state.failure || guard.state.calls !== 1)
    return { ...promptBase("CALLBACK_REJECTED", guard.state.failure || "CALLBACK_COUNT_MISMATCH", request),
      callback_count: guard.state.calls, warnings };
  if (request.stage === "capture") {
    if (upstream?.success !== false || upstream?.error !== "Error: OUTLINE_PROMPT_CAPTURE_ONLY")
      return { ...promptBase("UPSTREAM_FAILURE", "capture sentinel was not observed", request), callback_count: guard.state.calls, warnings };
    const captured = { schema: BINDING_SCHEMA, request_id: request.request_id, input_sha256: inputIdentity,
      upstream_manifest_sha256: manifestIdentity, npm_members_sha256: memberIdentity,
      worker_sha256: workerIdentity, guard_sha256: guardIdentity,
      system: guard.state.system, user: guard.state.user,
      system_sha256: sha(guard.state.system), user_sha256: sha(guard.state.user) };
    return { ...promptBase("PROMPT_CAPTURED", null, request), binding: captured, callback_count: guard.state.calls, warnings };
  }
  if (invalidResponse) return { ...promptBase("INVALID_RESPONSE", "duplicate keys or excessive nesting", request), callback_count: guard.state.calls, warnings };
  if (!upstream?.success) return { ...promptBase("UPSTREAM_FAILURE", "upstream reported failure", request), callback_count: guard.state.calls, warnings };
  // When the reply was not exact JSON, `parsed` never materialised and the donor
  // already repaired and normalised the text, so there is nothing left to
  // reconcile against a raw parse. The repaired candidate is admitted only after
  // the same structural checks the text-only slice applies, and it says out loud
  // that the model bytes were not exact JSON.
  if (!exact) {
    // A raw parse never materialised, so the donor's own normalisations (default
    // language directive, title normalisation, dropped media fields) cannot be
    // reconstructed or listed one by one. Say that instead of implying the reply
    // was reviewed verbatim.
    const transformations = ["UPSTREAM_JSON_REPAIRED", "UPSTREAM_NORMALIZATIONS_UNRECONSTRUCTED"];
    const differences = repairedOutlineDifferences(upstream?.data);
    if (differences.length) return { ...promptBase("UPSTREAM_RESULT_NOT_ADMITTED", "unknown, unsupported or altered data", request),
      callback_count: guard.state.calls, warnings, original_reply: request.reply.value, differences,
      transformations, observed_upstream: upstream.data };
    return { ...promptBase("CANDIDATE", null, request), callback_count: guard.state.calls, warnings,
      transformations, exact_json_output: false, data: upstream.data, human_review_required: true };
  }
  const inspection = inspectPromptOutline(parsed, upstream);
  if (inspection.differences.length) return { ...promptBase("UPSTREAM_RESULT_NOT_ADMITTED", "unknown, unsupported or altered data", request),
    callback_count: guard.state.calls, warnings, original_reply: request.reply.value, differences: inspection.differences,
    transformations: inspection.transformations, observed_upstream: upstream.data };
  return { ...promptBase("CANDIDATE", null, request), callback_count: guard.state.calls, warnings,
    transformations: inspection.transformations, exact_json_output: exact, data: upstream.data, human_review_required: true };
}

async function processFrame(raw) {
  let request;
  try {
    const source = new TextDecoder("utf-8", { fatal: true }).decode(raw);
    request = JSON.parse(source);
    rejectDuplicateKeys(source);
  } catch {
    return base("INVALID_REQUEST", "invalid bounded UTF-8 JSON or duplicate keys");
  }
  if (request?.schema === PROMPT_SCHEMA) {
    try { return await processPromptFrame(request); }
    catch { return promptBase("PROCESSING_FAILURE", "outline prompt processing failed", request); }
  }
  if (!requestValid(request)) return base("INVALID_REQUEST", "request contract or budget rejected");
  let parsed = null;
  let exact = false;
  if (request.reply.kind === "synthetic_response") {
    try {
      parsed = JSON.parse(request.reply.value);
      try { rejectDuplicateKeys(request.reply.value); }
      catch { return base("INVALID_RESPONSE", "ambiguous duplicate keys or excessive nesting", request); }
      exact = true;
    } catch {
      // Let the actual upstream parser observe malformed data, then quarantine
      // any upstream recovery instead of treating it as an admitted candidate.
    }
  }
  const warnings = [];
  const calls = [];
  const logger = {
    debug() {}, info() {},
    warn() { warnings.push("UPSTREAM_WARNING"); },
    error() { warnings.push("UPSTREAM_ERROR"); },
  };
  const replayCall = async (system, user, images) => {
    if (typeof system !== "string" || typeof user !== "string" ||
        Buffer.byteLength(system, "utf8") > 200_000 || Buffer.byteLength(user, "utf8") > 200_000 ||
        (images && images.length)) throw new Error("REPLAY_PROMPT_BUDGET_OR_IMAGES_UNSUPPORTED");
    calls.push({ system_sha256: sha(system), user_sha256: sha(user),
      system_bytes: Buffer.byteLength(system, "utf8"), user_bytes: Buffer.byteLength(user, "utf8") });
    if (request.reply.kind === "synthetic_error") throw new Error("SYNTHETIC_REPLAY_FAILURE");
    return request.reply.value;
  };
  let upstream;
  try {
    upstream = await generateSceneOutlinesFromRequirements(
      { requirement: request.requirement }, request.source_text || undefined, undefined, replayCall, { logger },
    );
  } catch {
    return { ...base("UPSTREAM_FAILURE", "upstream outline function raised", request), calls, warnings };
  }
  if (!upstream?.success) {
    return { ...base("UPSTREAM_FAILURE", "upstream reported failure", request), calls, warnings,
      upstream_reported_error: typeof upstream?.error === "string" ? upstream.error.slice(0, 1000) : null };
  }
  if (!exact) {
    return { ...base("UPSTREAM_RECOVERY_NOT_ADMITTED", "non-exact response was recovered upstream", request),
      calls, warnings, upstream_reported_success: true };
  }
  const inputOutlines = Array.isArray(parsed) ? parsed : parsed?.outlines;
  const outlines = upstream.data?.outlines;
  if (!Array.isArray(inputOutlines) || !Array.isArray(outlines) || inputOutlines.length < 1 || inputOutlines.length > 30 ||
      outlines.length !== inputOutlines.length || outlines.some(x => !object(x) || !id(x.id) ||
        !(flatOutlineSupported(x) || interactiveOutlineSupported(x)) ||
        typeof x.title !== "string" || !x.title.trim() || x.title.length > 240 ||
        typeof x.description !== "string" || x.description.length > 16_000 || !Array.isArray(x.keyPoints) ||
        x.keyPoints.length > 200 || x.keyPoints.some(p => typeof p !== "string" || p.length > 2_000) ||
        (Array.isArray(x.mediaGenerations) && x.mediaGenerations.length) ||
        (Array.isArray(x.suggestedImageIds) && x.suggestedImageIds.length))) {
    return { ...base("UNSUPPORTED_OUTPUT", "outline output is outside the text-only replay slice", request), calls, warnings };
  }
  const seenIds = new Map(), duplicateIds = [];
  for (let index = 0; index < outlines.length; index++) {
    const outlineId = outlines[index].id;
    if (seenIds.has(outlineId)) duplicateIds.push({ kind: "DUPLICATE_OUTLINE_ID", outline_index: index,
      first_outline_index: seenIds.get(outlineId), id: outlineId });
    else seenIds.set(outlineId, index);
  }
  if (duplicateIds.length) return { ...base("UNSUPPORTED_OUTPUT", "duplicate outline identity", request),
    calls, warnings, differences: duplicateIds, observed_upstream: upstream.data };
  const transformations = [];
  if (Array.isArray(parsed) || !parsed?.languageDirective) transformations.push("DEFAULT_LANGUAGE_DIRECTIVE");
  if (inputOutlines.some(x => !x?.id)) transformations.push("UNSTABLE_GENERATED_OUTLINE_IDS");
  if (inputOutlines.some((x, i) => x?.order !== i + 1)) transformations.push("OUTLINE_ORDER_ASSIGNED");
  if (inputOutlines.some(x => object(x) && Object.hasOwn(x, "mediaGenerations") && !Array.isArray(x.mediaGenerations)))
    transformations.push("INVALID_MEDIA_GENERATIONS_DROPPED");
  if (!Array.isArray(parsed) && typeof parsed?.courseTitle === "string" && parsed.courseTitle !== upstream.data?.courseTitle)
    transformations.push("COURSE_TITLE_NORMALIZED");
  return { ...base("CANDIDATE", null, request), input_sha256: sha(raw), calls, warnings, transformations,
    data: upstream.data, active_content_executed: false, human_review_required: true };
}

if (process.argv.length === 3 && process.argv[2] === "--hello") {
  process.stdout.write(JSON.stringify({ schema: "archeaxis.openmaic-outline-replay-hello/v1",
    upstream_generation: "0.3.28", model_call: "NOT_INVOKED", core_task: "NOT_CONNECTED", runtime }) + "\n");
} else if (process.argv.length !== 2) {
  process.stdout.write(JSON.stringify(base("INVALID_REQUEST", "unsupported arguments")) + "\n");
  process.exitCode = 2;
} else {
  let length = 0, overflow = false;
  const chunks = [];
  for await (const chunk of process.stdin) {
    length += chunk.length;
    if (length > MAX_INPUT) overflow = true;
    if (!overflow) chunks.push(chunk);
  }
  let result = overflow || !length ? base("INVALID_REQUEST", "input exceeds byte budget or is empty") : await processFrame(Buffer.concat(chunks));
  let output = JSON.stringify(result);
  if (Buffer.byteLength(output, "utf8") > MAX_OUTPUT) {
    result = result.schema === "archeaxis.openmaic-outline-prompt-result/v1"
      ? promptBase("INVALID_REQUEST", "output exceeds byte budget", null)
      : base("INVALID_REQUEST", "output exceeds byte budget");
    output = JSON.stringify(result);
  }
  process.stdout.write(output + "\n");
  if (!["CANDIDATE", "PROMPT_CAPTURED"].includes(result.status)) process.exitCode = 2;
}
