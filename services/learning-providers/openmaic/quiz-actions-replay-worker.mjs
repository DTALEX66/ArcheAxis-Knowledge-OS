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
checkManifest(donor, "e9e5396d1676de1bc25e3f9df81f65b5a52724ae9e3bcaf49fb109b82051e9d6", 18,
  "OUTLINE_MANIFEST_IDENTITY_MISMATCH");
checkManifest(quiz, "54499d6b7840d2968a3b02d11a27ee70ceed92d865efe702882015044b597de8", 6,
  "QUIZ_MANIFEST_IDENTITY_MISMATCH");
checkManifest(dsl, "ef4102ca18abefcf0c5956a8caa356236d60d248416b1b666cfc6daa99066dc0", 3,
  "DSL_MANIFEST_IDENTITY_MISMATCH");
const manifest = checkManifest(actions, "8e4b62a07c4daf3085fadd126396e467084a7dd35c9c5e9159f863fb527e655a", 7,
  "ACTIONS_MANIFEST_IDENTITY_MISMATCH");
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

function validRequest(r) {
  if (!obj(r) || Object.keys(r).length !== 6 ||
      ["schema", "request_id", "outline", "content", "language_directive", "reply"].some(k => !Object.hasOwn(r, k)) ||
      r.schema !== "archeaxis.openmaic-quiz-actions-replay/v1" || !id(r.request_id) ||
      !str(r.language_directive, 2_000) || !obj(r.outline) ||
      !keysAre(r.outline, ["id", "type", "title", "description", "keyPoints", "order", "quizConfig"]) ||
      !id(r.outline.id) || r.outline.type !== "quiz" || !str(r.outline.title, 240, true) ||
      !str(r.outline.description, 16_000) || !Array.isArray(r.outline.keyPoints) ||
      r.outline.keyPoints.length > 200 || r.outline.keyPoints.some(p => !str(p, 2_000)) ||
      (Object.hasOwn(r.outline, "order") && (!Number.isSafeInteger(r.outline.order) || r.outline.order < 0)) ||
      (Object.hasOwn(r.outline, "quizConfig") && (!obj(r.outline.quizConfig) ||
        !keysAre(r.outline.quizConfig, ["questionCount", "difficulty", "questionTypes"]) ||
        !Number.isInteger(r.outline.quizConfig.questionCount) || r.outline.quizConfig.questionCount < 1 ||
        r.outline.quizConfig.questionCount > 30 || !["easy", "medium", "hard"].includes(r.outline.quizConfig.difficulty) ||
        !Array.isArray(r.outline.quizConfig.questionTypes) || r.outline.quizConfig.questionTypes.length < 1 ||
        r.outline.quizConfig.questionTypes.length > 3 || r.outline.quizConfig.questionTypes.some(t => !["single", "multiple", "short_answer"].includes(t)))) ||
      !obj(r.content) || !keysAre(r.content, ["questions"]) || !Array.isArray(r.content.questions) ||
      r.content.questions.length < 1 || r.content.questions.length > 30 || r.content.questions.some(q => !validQuestion(q)) ||
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

async function processFrame(raw) {
  let request;
  try {
    const source = new TextDecoder("utf-8", { fatal: true }).decode(raw);
    request = JSON.parse(source); rejectDuplicateKeys(source);
    if (!validRequest(request)) return { ...base("INVALID_REQUEST", "request contract or budget rejected", request), input_sha256: digest(raw) };
  } catch { return { ...base("INVALID_REQUEST", "invalid bounded UTF-8 JSON or duplicate keys"),
    input_sha256: digest(raw), input_raw_base64: raw.toString("base64") }; }
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
    result = base("INVALID_REQUEST", "output exceeds byte budget");
    output = JSON.stringify(result);
  }
  process.stdout.write(output + "\n");
  if (result.status !== "CANDIDATE") process.exitCode = 2;
}
