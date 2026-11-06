/** Synthetic quiz action observation. Returned data is never executed or rendered. */
import { createHash } from "node:crypto";
import { registerHooks } from "node:module";
import { lstatSync, readFileSync } from "node:fs";

const donor = new URL("./vendor/generation-0.3.28-outline/", import.meta.url);
const quiz = new URL("./vendor/generation-0.3.28-quiz/", import.meta.url);
const actions = new URL("./vendor/generation-0.3.28-quiz-actions/", import.meta.url);
const dsl = new URL("./vendor/dsl-0.12.0-actions/", import.meta.url);
const npm = new URL("./vendor/npm/", import.meta.url);
const digest = data => createHash("sha256").update(data).digest("hex");
function checkFile(root, relative, expected, reason) {
  const path = new URL(relative, root);
  if (!path.href.startsWith(root.href)) throw new Error(reason);
  const info = lstatSync(path);
  if (!info.isFile() || info.isSymbolicLink() || info.size > 1_000_000 ||
      digest(readFileSync(path)) !== expected) throw new Error(reason);
}
function checkManifest(root, expected, count, reason) {
  const bytes = readFileSync(new URL("ORIGINALS.json", root));
  if (digest(bytes) !== expected) throw new Error(reason);
  const manifest = JSON.parse(bytes.toString("utf8"));
  if (!manifest.originals || Object.keys(manifest.originals).length !== count) throw new Error(reason);
  for (const [relative, expectedMember] of Object.entries(manifest.originals))
    checkFile(root, relative, expectedMember, "UPSTREAM_MEMBER_IDENTITY_MISMATCH");
  return manifest;
}
const OUTLINE_MANIFEST_SHA = "e9e5396d1676de1bc25e3f9df81f65b5a52724ae9e3bcaf49fb109b82051e9d6";
const QUIZ_MANIFEST_SHA = "54499d6b7840d2968a3b02d11a27ee70ceed92d865efe702882015044b597de8";
const ACTIONS_MANIFEST_SHA = "8e4b62a07c4daf3085fadd126396e467084a7dd35c9c5e9159f863fb527e655a";
const DSL_MANIFEST_SHA = "ef4102ca18abefcf0c5956a8caa356236d60d248416b1b666cfc6daa99066dc0";
checkManifest(donor, OUTLINE_MANIFEST_SHA, 18, "OUTLINE_MANIFEST_IDENTITY_MISMATCH");
checkManifest(quiz, QUIZ_MANIFEST_SHA, 6, "QUIZ_MANIFEST_IDENTITY_MISMATCH");
checkManifest(dsl, DSL_MANIFEST_SHA, 3, "DSL_MANIFEST_IDENTITY_MISMATCH");
const manifest = checkManifest(actions, ACTIONS_MANIFEST_SHA, 7, "ACTIONS_MANIFEST_IDENTITY_MISMATCH");
checkFile(actions, manifest.adapted_file, manifest.adapted_sha256, "ACTIONS_ADAPTER_IDENTITY_MISMATCH");
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
  "partial-json-0.1.7/LICENSE": "cd519ad3d7e012427f978dfb2e3b92ee403d189d7b859ba6bf68fd7e12ca456f",
  "partial-json-0.1.7/package.json": "42b3ae6c99ec959249f8eb4d3da7fdb44ec1f96ec627fa7f9ca5487a4e80963f",
  "partial-json-0.1.7/dist/index.js": "23f750aa1170c830b7ef180135852317886cc58ce7d2597e5eeee044539072c7",
  "partial-json-0.1.7/dist/options.js": "779b2aded6d4e2ec6171ea9d5d5d97551e8c3258b6e78a01d2e9fc6235865b36",
};
for (const [relative, expected] of Object.entries(lockedMembers))
  checkFile(npm, relative, expected, "LOCKED_NPM_MEMBER_IDENTITY_MISMATCH");
const workerPath = new URL(import.meta.url);
const workerInfo = lstatSync(workerPath);
if (!workerInfo.isFile() || workerInfo.isSymbolicLink() || workerInfo.size > 1_000_000)
  throw new Error("ACTIONS_WORKER_IDENTITY_UNAVAILABLE");
const workerIdentity = digest(readFileSync(workerPath));
const npmIdentity = digest(JSON.stringify(lockedMembers));
const nanoid = new URL("nanoid-5.1.14/index.js", npm).href;
const jsonrepair = new URL("jsonrepair-3.13.3/lib/esm/index.js", npm).href;
const partialJson = new URL("partial-json-0.1.7/dist/index.js", npm).href;
registerHooks({
  resolve(specifier, context, nextResolve) {
    if (context.parentURL?.startsWith(actions.href)) {
      if (specifier === "@openmaic/dsl") return { url: new URL("src/action.ts", dsl).href, shortCircuit: true };
      if (specifier === "nanoid") return { url: nanoid, shortCircuit: true };
      if (specifier === "jsonrepair") return { url: jsonrepair, shortCircuit: true };
      if (specifier === "partial-json") return { url: partialJson, shortCircuit: true };
      if (specifier === "./logger.js") return { url: new URL("src/logger.ts", donor).href, shortCircuit: true };
    }
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

const { replayQuizActionsBranch, resetParserObservation, getParserObservation } =
  await import(new URL("quiz-actions-functions.ts", actions));
const runtime = Object.freeze({ node_version: process.versions.node,
  register_hooks_available: typeof registerHooks === "function",
  upstream_quiz_branch_imported: typeof replayQuizActionsBranch === "function",
  upstream_members_checked: true, locked_npm_members_checked: true });
const MAX_INPUT = 256_000, MAX_OUTPUT = 1_000_000;
const obj = value => !!value && typeof value === "object" && !Array.isArray(value);
const id = value => typeof value === "string" && /^[A-Za-z0-9_-]{1,128}$/.test(value);
const str = (value, limit, required = false) => typeof value === "string" && value.length <= limit &&
  (!required || !!value.trim());
const keysAre = (value, allowed) => Object.keys(value).every(key => allowed.includes(key));

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
      p++; whitespace(); const keys = new Set();
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

function validQuestion(q) {
  const allowed = ["id", "type", "question", "options", "answer", "correctAnswer", "correct_answer",
    "analysis", "points", "commentPrompt", "hasAnswer"];
  if (!obj(q) || !keysAre(q, allowed) || !id(q.id) || !["single", "multiple", "short_answer"].includes(q.type) ||
      !str(q.question, 8_000, true)) return false;
  for (const key of ["analysis", "commentPrompt"]) if (Object.hasOwn(q, key) && !str(q[key], 8_000)) return false;
  if (Object.hasOwn(q, "hasAnswer") && typeof q.hasAnswer !== "boolean") return false;
  if (Object.hasOwn(q, "points") && (!Number.isInteger(q.points) || q.points < 0 || q.points > 1_000)) return false;
  if (Object.hasOwn(q, "options") && (!Array.isArray(q.options) || q.options.length > 26 ||
      q.options.some(o => !obj(o) || !keysAre(o, ["value", "label"]) ||
        !str(o.value, 32, true) || !str(o.label, 4_000, true)))) return false;
  for (const key of ["answer", "correctAnswer", "correct_answer"]) {
    if (!Object.hasOwn(q, key)) continue;
    const answer = q[key];
    if (!(str(answer, 4_000, true) || (Array.isArray(answer) && answer.length <= 26 &&
      answer.every(a => str(a, 4_000, true))))) return false;
  }
  return true;
}

function validOutline(outline) {
  if (!obj(outline) ||
      !keysAre(outline, ["id", "type", "title", "description", "keyPoints", "order", "quizConfig"]) ||
      !id(outline.id) || outline.type !== "quiz" || !str(outline.title, 240, true) ||
      !str(outline.description, 16_000) || !Array.isArray(outline.keyPoints) ||
      outline.keyPoints.length > 200 || outline.keyPoints.some(p => !str(p, 2_000))) return false;
  if (Object.hasOwn(outline, "order") &&
      (!Number.isSafeInteger(outline.order) || outline.order < 0)) return false;
  if (!Object.hasOwn(outline, "quizConfig")) return true;
  const config = outline.quizConfig;
  return obj(config) && keysAre(config, ["questionCount", "difficulty", "questionTypes"]) &&
    Number.isInteger(config.questionCount) && config.questionCount >= 1 && config.questionCount <= 30 &&
    ["easy", "medium", "hard"].includes(config.difficulty) &&
    Array.isArray(config.questionTypes) && config.questionTypes.length >= 1 &&
    config.questionTypes.length <= 3 &&
    config.questionTypes.every(t => ["single", "multiple", "short_answer"].includes(t));
}

function validContent(content) {
  return obj(content) && keysAre(content, ["questions"]) && Array.isArray(content.questions) &&
    content.questions.length >= 1 && content.questions.length <= 30 &&
    content.questions.every(q => validQuestion(q));
}

function validRequest(r) {
  if (!obj(r) || Object.keys(r).length !== 6 ||
      ["schema", "request_id", "outline", "content", "language_directive", "reply"].some(k => !Object.hasOwn(r, k)) ||
      r.schema !== "archeaxis.openmaic-quiz-actions-replay/v1" || !id(r.request_id) ||
      !str(r.language_directive, 2_000) || !validOutline(r.outline) || !validContent(r.content) ||
      !obj(r.reply)) return false;
  if (r.reply.kind === "synthetic_error") return Object.keys(r.reply).length === 1;
  return r.reply.kind === "synthetic_response" && Object.keys(r.reply).length === 2 &&
    typeof r.reply.value === "string" && Buffer.byteLength(r.reply.value, "utf8") <= 120_000;
}

function base(status, reason, input = null) {
  return { schema: "archeaxis.openmaic-quiz-actions-replay-result/v1", status, reason, input,
    upstream_generation: "0.3.28", upstream_entry: "generateSceneActions quiz branch excerpt",
    response_origin: "SYNTHETIC_REPLAY", model_call: "NOT_INVOKED", network_performed: false,
    core_task: "NOT_CONNECTED", full_generate_scene_actions: false, full_generation_chain: false,
    canonical_bindings_verified: false, independent_mastery: "not_established",
    action_execution: "NOT_PERFORMED", rendering_authorized: false, retry_bytes_stable: false,
    runtime, data: null };
}

// ---------------------------------------------------------------------------
// Prompt contract: capture the donor's quiz-action prompt, then replay the
// model's reply through the same original branch. The synthetic frame above
// stays untouched; this is the frame Core drives with a real local model.
// ---------------------------------------------------------------------------
const PROMPT_SCHEMA = "archeaxis.openmaic-quiz-actions-prompt/v1";
const BINDING_SCHEMA = "archeaxis.openmaic-quiz-actions-prompt-binding/v1";
const PROMPT_RESULT_SCHEMA = "archeaxis.openmaic-quiz-actions-prompt-result/v1";
const CAPTURE_SENTINEL = "QUIZ_ACTIONS_PROMPT_CAPTURE_ONLY";
const BINDING_FIELDS = ["schema", "request_id", "input_sha256", "outline_manifest_sha256",
  "quiz_manifest_sha256", "actions_manifest_sha256", "dsl_manifest_sha256", "npm_members_sha256",
  "worker_sha256", "system", "user", "system_sha256", "user_sha256"];
const HASHES = ["input_sha256", "outline_manifest_sha256", "quiz_manifest_sha256",
  "actions_manifest_sha256", "dsl_manifest_sha256", "npm_members_sha256", "worker_sha256",
  "system_sha256", "user_sha256"];
const exactKeys = (value, keys) => obj(value) && Object.keys(value).length === keys.length &&
  keys.every(key => Object.hasOwn(value, key));
const textSafe = value => typeof value === "string" && value.isWellFormed() && !value.includes("\0");
const hashText = value => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
function safeJson(value) {
  if (typeof value === "string") return textSafe(value);
  if (typeof value === "number") return Number.isFinite(value);
  if (Array.isArray(value)) return value.every(safeJson);
  if (obj(value)) return Object.entries(value).every(([key, item]) => textSafe(key) && safeJson(item));
  return value === null || typeof value === "boolean";
}
function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (obj(value)) return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}
// An unkeyed comparison, never proof of the selected source or model call.
function promptIdentity(request) {
  return digest(canonical({ request_id: request.request_id, outline: request.outline,
    content: request.content, language_directive: request.language_directive }));
}
function promptRequestValid(request) {
  const common = ["schema", "stage", "request_id", "outline", "content", "language_directive"];
  if (!obj(request) || request.schema !== PROMPT_SCHEMA || !id(request.request_id) ||
      !validOutline(request.outline) || !validContent(request.content) ||
      !str(request.language_directive, 2_000) || !textSafe(request.language_directive) ||
      !safeJson(request.outline) || !safeJson(request.content)) return false;
  if (request.stage === "capture") return exactKeys(request, common);
  if (request.stage !== "replay" || !exactKeys(request, [...common, "binding", "reply"]) ||
      !exactKeys(request.reply, ["kind", "value"]) || request.reply.kind !== "caller_supplied" ||
      !textSafe(request.reply.value) ||
      Buffer.byteLength(request.reply.value, "utf8") > 120_000) return false;
  const binding = request.binding;
  return exactKeys(binding, BINDING_FIELDS) && binding.schema === BINDING_SCHEMA &&
    binding.request_id === request.request_id && textSafe(binding.system) && textSafe(binding.user) &&
    Buffer.byteLength(binding.system, "utf8") <= 200_000 &&
    Buffer.byteLength(binding.user, "utf8") <= 200_000 &&
    HASHES.every(key => hashText(binding[key]));
}
function promptBase(status, reason, request) {
  const stage = ["capture", "replay"].includes(request?.stage) ? request.stage : null;
  return { schema: PROMPT_RESULT_SCHEMA, status, reason,
    request_id: stage && id(request?.request_id) ? request.request_id : null, stage,
    response_origin: stage === "replay" ? "CALLER_SUPPLIED_UNVERIFIED" : "NOT_AVAILABLE",
    model_call: "NOT_INVOKED", network_performed: false, core_task: "NOT_CONNECTED",
    core_authorization: "NOT_ESTABLISHED", canonical_bindings_verified: false,
    identity_scope: "UNKEYED_COMPARISON_ONLY", binding_authentication: "NOT_PROVIDED",
    source_snapshot_authority: "CALLER_DECLARED_ONLY", persisted: false,
    active_content_executed: false, rendering_authorized: false, action_execution: "NOT_PERFORMED",
    answer_non_disclosure_verified: false, retry_bytes_stable: false,
    upstream_generation: "0.3.28", upstream_entry: "generateSceneActions quiz branch excerpt",
    runtime, data: null };
}
const SPEECH_KEYS = ["id", "type", "text"];
const speechShaped = action => obj(action) && id(action.id) && action.type === "speech" &&
  str(action.text, 8_000, true) && keysAre(action, SPEECH_KEYS);

async function processPromptFrame(request) {
  if (!promptRequestValid(request))
    return promptBase("INVALID_REQUEST", "prompt request contract or budget rejected", request);
  const inputIdentity = promptIdentity(request), binding = request.binding;
  if (request.stage === "replay" &&
      (binding.request_id !== request.request_id || binding.input_sha256 !== inputIdentity ||
        binding.outline_manifest_sha256 !== OUTLINE_MANIFEST_SHA ||
        binding.quiz_manifest_sha256 !== QUIZ_MANIFEST_SHA ||
        binding.actions_manifest_sha256 !== ACTIONS_MANIFEST_SHA ||
        binding.dsl_manifest_sha256 !== DSL_MANIFEST_SHA ||
        binding.npm_members_sha256 !== npmIdentity || binding.worker_sha256 !== workerIdentity ||
        binding.system_sha256 !== digest(binding.system) ||
        binding.user_sha256 !== digest(binding.user)))
    return promptBase("BINDING_MISMATCH", "input, prompt or donor identity differs", request);
  let parsed, exact = false, responseError = null;
  if (request.stage === "replay") {
    try { parsed = JSON.parse(request.reply.value); exact = true; } catch { /* donor may repair */ }
    if (exact) {
      try { rejectDuplicateKeys(request.reply.value); }
      catch { responseError = "INVALID_RESPONSE"; }
      if (!responseError && (!Array.isArray(parsed) || parsed.length < 1 || parsed.length > 2 ||
          parsed.some(item => !obj(item) || Object.keys(item).length !== 2 || item.type !== "text" ||
            !str(item.content, 8_000, true))))
        responseError = "UNSUPPORTED_OUTPUT";
    }
  }
  const calls = [], notices = [];
  let capturedSystem = null, capturedUser = null;
  const replayCall = async (system, user, images) => {
    if (typeof system !== "string" || typeof user !== "string" ||
        Buffer.byteLength(system, "utf8") > 200_000 || Buffer.byteLength(user, "utf8") > 200_000 ||
        (images && images.length)) throw new Error("PROMPT_BUDGET_OR_IMAGES_UNSUPPORTED");
    calls.push({ system_sha256: digest(system), user_sha256: digest(user),
      system_bytes: Buffer.byteLength(system, "utf8"), user_bytes: Buffer.byteLength(user, "utf8") });
    capturedSystem = system; capturedUser = user;
    if (request.stage === "capture") throw new Error(CAPTURE_SENTINEL);
    if (responseError) throw new Error(responseError);
    return request.reply.value;
  };
  const logger = { debug() {}, info() {}, warn() { notices.push("UPSTREAM_WARNING"); },
    error() { notices.push("UPSTREAM_ERROR"); } };
  let upstream;
  resetParserObservation();
  try {
    upstream = await replayQuizActionsBranch(request.outline, request.content, replayCall,
      { languageDirective: request.language_directive, logger });
  } catch (error) {
    if (calls.length !== 1)
      return { ...promptBase("CALLBACK_REJECTED", "callback count differs", request),
        callback_count: calls.length, calls, notices };
    if (request.stage === "capture" && error instanceof Error && error.message === CAPTURE_SENTINEL) {
      const captured = { schema: BINDING_SCHEMA, request_id: request.request_id,
        input_sha256: inputIdentity, outline_manifest_sha256: OUTLINE_MANIFEST_SHA,
        quiz_manifest_sha256: QUIZ_MANIFEST_SHA, actions_manifest_sha256: ACTIONS_MANIFEST_SHA,
        dsl_manifest_sha256: DSL_MANIFEST_SHA, npm_members_sha256: npmIdentity,
        worker_sha256: workerIdentity, system: capturedSystem, user: capturedUser,
        system_sha256: digest(capturedSystem), user_sha256: digest(capturedUser) };
      return { ...promptBase("PROMPT_CAPTURED", null, request), binding: captured,
        callback_count: calls.length, calls, notices };
    }
    const reason = responseError === "INVALID_RESPONSE"
      ? "ambiguous duplicate keys or excessive nesting"
      : responseError === "UNSUPPORTED_OUTPUT"
        ? "response outside the bounded text-only slice"
        : "upstream quiz-action branch raised";
    return { ...promptBase(responseError || "UPSTREAM_FAILURE", reason, request),
      callback_count: calls.length, calls, notices };
  }
  if (calls.length !== 1)
    return { ...promptBase("CALLBACK_REJECTED", "callback count differs", request),
      callback_count: calls.length, calls, notices };
  if (request.stage === "capture")
    return { ...promptBase("UPSTREAM_FAILURE", "capture sentinel was not observed", request),
      callback_count: calls.length, calls, notices };
  if (!Array.isArray(upstream))
    return { ...promptBase("UPSTREAM_FAILURE", "upstream branch returned no action array", request),
      callback_count: calls.length, calls, notices };
  const parser = getParserObservation();
  const observation = { parser_called: parser !== null, parser_action_count: parser?.count ?? null,
    callback_count: calls.length,
    input_item_count: exact && Array.isArray(parsed) ? parsed.length : null,
    fallback: parser === null || parser.count === 0 };
  if (observation.fallback)
    return { ...promptBase("UPSTREAM_FALLBACK_NOT_ADMITTED",
      "upstream supplied fallback after no parsed actions", request), calls, notices, observation };
  // A reply the donor repaired has no raw parse to reconcile against. Only the
  // bounded text-only speech shape is admitted, and the receipt says the bytes
  // were not exact JSON and the donor's normalisations cannot be reconstructed.
  if (!exact) {
    if (upstream.length < 1 || upstream.length > 2 || upstream.some(action => !speechShaped(action)))
      return { ...promptBase("UPSTREAM_RESULT_NOT_ADMITTED",
        "repaired actions exceed the bounded speech slice", request), calls, notices, observation,
        original_reply: request.reply.value, observed_upstream: upstream };
    return { ...promptBase("CANDIDATE", null, request), calls, notices, observation,
      transformations: ["UPSTREAM_JSON_REPAIRED", "UPSTREAM_NORMALIZATIONS_UNRECONSTRUCTED",
        "UNSTABLE_GENERATED_ACTION_IDS"],
      exact_json_output: false, data: { actions: upstream }, human_review_required: true };
  }
  if (upstream.length !== parsed.length || upstream.some((action, index) => !speechShaped(action) ||
      action.text !== parsed[index].content.trim()))
    return { ...promptBase("UNSUPPORTED_OR_FILTERED_NOT_ADMITTED", "unexpected transformed action", request),
      calls, notices, observation };
  const transformations = ["UNSTABLE_GENERATED_ACTION_IDS"];
  if (parsed.some(item => item.content !== item.content.trim())) transformations.push("SPEECH_TRIMMED");
  return { ...promptBase("CANDIDATE", null, request), calls, notices, observation, transformations,
    exact_json_output: true, data: { actions: upstream }, human_review_required: true };
}

async function processFrame(raw) {
  let request;
  try {
    const source = new TextDecoder("utf-8", { fatal: true }).decode(raw);
    request = JSON.parse(source); rejectDuplicateKeys(source);
  } catch { return { ...base("INVALID_REQUEST", "invalid bounded UTF-8 JSON or duplicate keys"),
    input_sha256: digest(raw), input_raw_base64: raw.toString("base64") }; }
  if (request?.schema === PROMPT_SCHEMA) {
    try { return await processPromptFrame(request); }
    catch { return promptBase("PROCESSING_FAILURE", "quiz-action prompt processing failed", null); }
  }
  return processLegacyFrame(request, raw);
}

async function processLegacyFrame(request, raw) {
  if (!validRequest(request)) return { ...base("INVALID_REQUEST", "request contract or budget rejected", request), input_sha256: digest(raw) };
  // These fields remain in the original frame but the upstream prompt formatter
  // does not interpolate them. This reports the projection rather than hiding it.
  const promptProjection = {
    outline_fields_not_interpolated: Object.keys(request.outline).filter(k => !["title", "description", "keyPoints"].includes(k)).sort(),
    question_fields_not_interpolated: [...new Set(request.content.questions.flatMap(q =>
      Object.keys(q).filter(k => !["type", "question", "options"].includes(k))))].sort(),
  };
  const resultBase = (status, reason) => ({ ...base(status, reason, request), input_sha256: digest(raw),
    prompt_projection: promptProjection });
  let parsed, exact = false;
  if (request.reply.kind === "synthetic_response") {
    try { parsed = JSON.parse(request.reply.value); exact = true; } catch { /* upstream may repair */ }
    if (exact) {
      try { rejectDuplicateKeys(request.reply.value); }
      catch { return resultBase("INVALID_RESPONSE", "ambiguous duplicate keys or excessive nesting"); }
    }
  }
  const safeText = exact && Array.isArray(parsed) && parsed.length >= 1 && parsed.length <= 2 &&
    parsed.every(item => obj(item) && Object.keys(item).length === 2 &&
      item.type === "text" && str(item.content, 8_000, true));
  const calls = [], notices = [];
  const logger = { debug() {}, warn() { notices.push("UPSTREAM_WARNING"); }, error() { notices.push("UPSTREAM_ERROR"); },
    info(message) {
      if (typeof message !== "string") return;
      if (message.startsWith("Recovered malformed JSON via jsonrepair")) notices.push("JSONREPAIR_USED");
      if (message.includes("slide-only action(s)")) notices.push("SLIDE_ACTIONS_FILTERED");
    } };
  const replayCall = async (system, user, images) => {
    if (typeof system !== "string" || typeof user !== "string" ||
        Buffer.byteLength(system, "utf8") > 200_000 || Buffer.byteLength(user, "utf8") > 200_000 ||
        (images && images.length)) throw new Error("PROMPT_BUDGET_OR_IMAGES_UNSUPPORTED");
    calls.push({ system_sha256: digest(system), user_sha256: digest(user),
      system_bytes: Buffer.byteLength(system, "utf8"), user_bytes: Buffer.byteLength(user, "utf8") });
    if (request.reply.kind === "synthetic_error") throw new Error("SYNTHETIC_REPLAY_FAILURE");
    return request.reply.value;
  };
  let upstream;
  resetParserObservation();
  try {
    upstream = await replayQuizActionsBranch(request.outline, request.content, replayCall,
      { languageDirective: request.language_directive, logger });
  } catch {
    return { ...resultBase("UPSTREAM_FAILURE", "quiz action branch or synthetic callback raised"), calls, notices };
  }
  const parser = getParserObservation();
  const inputCount = exact && Array.isArray(parsed) ? parsed.length : null;
  const discussion = exact && Array.isArray(parsed) ? parsed.findIndex(item => obj(item) && item.type === "action" &&
    (item.name === "discussion" || item.tool_name === "discussion")) : -1;
  const observation = { parser_called: parser !== null, parser_action_count: parser?.count ?? null,
    input_item_count: inputCount,
    dropped_item_count: inputCount !== null && parser !== null ? Math.max(0, inputCount - parser.count) : null,
    discussion_may_truncate: discussion >= 0 && discussion < parsed.length - 1,
    fallback: parser === null || parser.count === 0,
    recovery_path: notices.includes("JSONREPAIR_USED") ? "jsonrepair" : (!exact ? "unverified" : "none") };
  if (!Array.isArray(upstream)) return { ...resultBase("UPSTREAM_FAILURE", "upstream result was not an array"), calls, notices, observation };
  if (observation.fallback) {
    const speech = upstream.length === 1 && upstream[0]?.type === "speech" &&
      upstream[0]?.title === "测验引导" && typeof upstream[0]?.text === "string" ? upstream[0].text : null;
    return { ...resultBase("UPSTREAM_FALLBACK_NOT_ADMITTED", "upstream supplied fallback after no parsed actions"),
      calls, notices, observation, fallback_origin: "UPSTREAM_DEFAULT", fallback_speech: speech };
  }
  if (!exact) return { ...resultBase("UPSTREAM_RECOVERY_NOT_ADMITTED", "non-exact response was recovered upstream"),
    calls, notices, observation };
  if (!safeText) return { ...resultBase("UNSUPPORTED_OR_FILTERED_NOT_ADMITTED", "unknown, active or lossy output"),
    calls, notices, observation };
  if (upstream.length !== parsed.length || upstream.some((action, i) => !obj(action) || !id(action.id) ||
      action.type !== "speech" || action.text !== parsed[i].content.trim() ||
      !keysAre(action, ["id", "type", "text"])))
    return { ...resultBase("UNSUPPORTED_OR_FILTERED_NOT_ADMITTED", "unexpected transformed action"), calls, notices, observation };
  const transformations = ["UNSTABLE_GENERATED_ACTION_IDS"];
  if (parsed.some(item => item.content !== item.content.trim())) transformations.push("SPEECH_TRIMMED");
  return { ...resultBase("CANDIDATE", null), calls, notices, observation, transformations,
    data: { actions: upstream }, human_review_required: true, answer_non_disclosure_verified: false };
}

if (process.argv.length === 3 && process.argv[2] === "--hello") {
  process.stdout.write(JSON.stringify({ schema: "archeaxis.openmaic-quiz-actions-replay-hello/v1",
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
    result = result.schema === PROMPT_RESULT_SCHEMA
      ? promptBase("INVALID_REQUEST", "output exceeds byte budget", null)
      : base("INVALID_REQUEST", "output exceeds byte budget");
    output = JSON.stringify(result);
  }
  process.stdout.write(output + "\n");
  if (!["CANDIDATE", "PROMPT_CAPTURED"].includes(result.status)) process.exitCode = 2;
}
