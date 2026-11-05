/** Synthetic quiz-helper replay. No model, network, Core task or content execution. */
import { createHash } from "node:crypto";
import { registerHooks } from "node:module";
import { lstatSync, readFileSync } from "node:fs";

const donor = new URL("./vendor/generation-0.3.28-outline/", import.meta.url);
const quiz = new URL("./vendor/generation-0.3.28-quiz/", import.meta.url);
const npm = new URL("./vendor/npm/", import.meta.url);
const digest = data => createHash("sha256").update(data).digest("hex");
const OUTLINE_MANIFEST_SHA = "e9e5396d1676de1bc25e3f9df81f65b5a52724ae9e3bcaf49fb109b82051e9d6";
const QUIZ_MANIFEST_SHA = "54499d6b7840d2968a3b02d11a27ee70ceed92d865efe702882015044b597de8";
const QUIZ_EXCERPT_SHA = "4d051a9365509bcedfd10ac7a66e9e5ed4ba58e19d46909e7e8d2b8489a3dfa6";
const GUARD_SHA = "5691dcaaeaa37e2bde624656a711c82663a8afc21a1d579da14194b516b4c584";

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
  for (const [relative, expectedMember] of Object.entries(manifest.originals)) {
    checkFile(root, relative, expectedMember, "UPSTREAM_MEMBER_IDENTITY_MISMATCH");
  }
  return manifest;
}

checkManifest(donor, OUTLINE_MANIFEST_SHA, 18,
  "OUTLINE_MANIFEST_IDENTITY_MISMATCH");
const quizManifest = checkManifest(quiz, QUIZ_MANIFEST_SHA, 6,
  "QUIZ_MANIFEST_IDENTITY_MISMATCH");
if (quizManifest.excerpt?.adapted_file !== "quiz-functions.ts" || quizManifest.excerpt?.adapted_sha256 !== QUIZ_EXCERPT_SHA)
  throw new Error("QUIZ_ADAPTER_IDENTITY_MISMATCH");
checkFile(quiz, quizManifest.excerpt.adapted_file, quizManifest.excerpt.adapted_sha256,
  "QUIZ_ADAPTER_IDENTITY_MISMATCH");
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
for (const [relative, expected] of Object.entries(lockedMembers))
  checkFile(npm, relative, expected, "LOCKED_NPM_MEMBER_IDENTITY_MISMATCH");
const guardPath = new URL("./outline-prompt-guard.mjs", import.meta.url);
const guardInfo = lstatSync(guardPath);
if (!guardInfo.isFile() || guardInfo.isSymbolicLink() || guardInfo.size > 1_000_000 ||
    digest(readFileSync(guardPath)) !== GUARD_SHA) throw new Error("QUIZ_GUARD_IDENTITY_MISMATCH");
const { createPromptGuard } = await import(guardPath);
const workerPath = new URL(import.meta.url);
const workerInfo = lstatSync(workerPath);
if (!workerInfo.isFile() || workerInfo.isSymbolicLink() || workerInfo.size > 1_000_000)
  throw new Error("QUIZ_WORKER_IDENTITY_UNAVAILABLE");
const workerIdentity = digest(readFileSync(workerPath));
const npmIdentity = digest(JSON.stringify(lockedMembers));

const nanoid = new URL("nanoid-5.1.14/index.js", npm).href;
const jsonrepair = new URL("jsonrepair-3.13.3/lib/esm/index.js", npm).href;
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

const { generateQuizContent } = await import(new URL("quiz-functions.ts", quiz));
const runtime = Object.freeze({ node_version: process.versions.node,
  register_hooks_available: typeof registerHooks === "function",
  upstream_excerpt_imported: typeof generateQuizContent === "function",
  upstream_members_checked: true, locked_npm_members_checked: true });
const MAX_INPUT = 256_000, MAX_OUTPUT = 1_000_000;
const obj = value => !!value && typeof value === "object" && !Array.isArray(value);
const id = value => typeof value === "string" && /^[A-Za-z0-9_-]{1,128}$/.test(value);
const str = (value, limit, required = false) => typeof value === "string" &&
  value.length <= limit && (!required || !!value.trim());
const keysAre = (value, permitted) => Object.keys(value).every(k => permitted.includes(k));
const types = ["single", "multiple", "short_answer"];

// JSON.parse alone accepts duplicate keys, including equivalent escaped names.
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

function validOutline(outline) {
  if (!obj(outline) || !keysAre(outline, ["id", "type", "title", "description", "keyPoints", "quizConfig"]) ||
      !id(outline.id) || outline.type !== "quiz" || !str(outline.title, 240, true) ||
      !str(outline.description, 16_000) || !Array.isArray(outline.keyPoints) ||
      outline.keyPoints.length > 200 || outline.keyPoints.some(p => !str(p, 2_000))) return false;
  if (!Object.hasOwn(outline, "quizConfig")) return true;
  const c = outline.quizConfig;
  return obj(c) && keysAre(c, ["questionCount", "difficulty", "questionTypes"]) &&
    Number.isInteger(c.questionCount) && c.questionCount >= 1 && c.questionCount <= 30 &&
    ["easy", "medium", "hard"].includes(c.difficulty) && Array.isArray(c.questionTypes) &&
    c.questionTypes.length >= 1 && c.questionTypes.length <= 3 &&
    c.questionTypes.every(t => types.includes(t)) && new Set(c.questionTypes).size === c.questionTypes.length;
}

function validRequest(r) {
  if (!obj(r) || Object.keys(r).length !== 5 ||
      ["schema", "request_id", "outline", "language_directive", "reply"].some(k => !Object.hasOwn(r, k)) ||
      r.schema !== "archeaxis.openmaic-quiz-replay/v1" || !id(r.request_id) ||
      !validOutline(r.outline) || !str(r.language_directive, 2_000) || !obj(r.reply)) return false;
  if (r.reply.kind === "synthetic_error") return Object.keys(r.reply).length === 1;
  return r.reply.kind === "synthetic_response" && Object.keys(r.reply).length === 2 &&
    typeof r.reply.value === "string" && Buffer.byteLength(r.reply.value, "utf8") <= 120_000;
}

function validInputQuestion(q) {
  const allowed = ["id", "type", "question", "options", "answer", "correctAnswer", "correct_answer",
    "analysis", "points", "commentPrompt"];
  if (!obj(q) || !keysAre(q, allowed) || !types.includes(q.type) || !str(q.question, 8_000, true) ||
      (Object.hasOwn(q, "id") && !id(q.id)) ||
      (Object.hasOwn(q, "analysis") && !str(q.analysis, 8_000)) ||
      (Object.hasOwn(q, "commentPrompt") && !str(q.commentPrompt, 8_000)) ||
      (Object.hasOwn(q, "points") && (!Number.isInteger(q.points) || q.points < 0 || q.points > 1_000))) return false;
  const answerKeys = ["answer", "correctAnswer", "correct_answer"].filter(k => Object.hasOwn(q, k));
  if (answerKeys.length > 1) return false;
  if (q.type === "short_answer") return !Object.hasOwn(q, "options") && answerKeys.length === 0;
  if (Object.hasOwn(q, "options")) {
    if (!Array.isArray(q.options) || q.options.length > 26 || q.options.some(option => {
      if (typeof option === "string") return !str(option, 4_000, true);
      return !obj(option) || !keysAre(option, ["value", "label", "text"]) ||
        Object.keys(option).length === 0 || Object.values(option).some(v => !str(v, 4_000, true));
    })) return false;
  }
  if (answerKeys.length) {
    const answer = q[answerKeys[0]];
    if (!(str(answer, 4_000, true) || (Array.isArray(answer) && answer.length <= 26 &&
      answer.every(a => str(a, 4_000, true))))) return false;
  }
  return true;
}

// The upstream resolver deliberately leaves an ambiguous answer unchanged. A
// later choice-contract check may still accept that unchanged value, so compare
// each original answer against *both* the original value and label projections.
// Retain the upstream observation separately when it cannot be admitted.
function inspectQuizDifferences(original, questions) {
  const differences = [], transformations = new Set();
  for (let questionIndex = 0; questionIndex < original.length; questionIndex++) {
    const source = original[questionIndex], observed = questions[questionIndex];
    if (source.type === "short_answer") continue;
    const expectedOptions = source.options.map((option, optionIndex) => {
      const letter = String.fromCharCode(65 + optionIndex);
      if (typeof option === "string") return { value: letter, label: option };
      if (Object.hasOwn(option, "text")) {
        if (Object.hasOwn(option, "label") || Object.hasOwn(option, "value")) {
          differences.push({ kind: "OPTION_TEXT_DISCARDED", question_index: questionIndex,
            option_index: optionIndex, original_text: option.text });
        } else {
          transformations.add("OPTION_TEXT_NORMALIZED_TO_LABEL");
        }
      }
      return { value: typeof option.value === "string" ? option.value : letter,
        label: typeof option.label === "string" ? option.label : String(option.value || option.text || letter) };
    });
    if (observed.options.length !== expectedOptions.length || observed.options.some((option, index) =>
      !keysAre(option, ["value", "label"]) || option.value !== expectedOptions[index].value ||
      option.label !== expectedOptions[index].label)) {
      differences.push({ kind: "OPTION_PROJECTION_MISMATCH", question_index: questionIndex });
      continue;
    }
    const supplied = source.answer ?? source.correctAnswer ?? source.correct_answer;
    const answers = Array.isArray(supplied) ? supplied : [supplied];
    for (let answerIndex = 0; answerIndex < answers.length; answerIndex++) {
      const rawAnswer = answers[answerIndex];
      const candidates = new Set();
      for (const option of expectedOptions)
        if (option.value === rawAnswer || option.label === rawAnswer) candidates.add(option.value);
      const values = [...candidates].sort();
      if (values.length !== 1 || observed.answer[answerIndex] !== values[0]) {
        differences.push({ kind: values.length === 1 ? "ANSWER_PROJECTION_MISMATCH" : "ANSWER_NOT_UNIQUE",
          question_index: questionIndex, answer_index: answerIndex, original_answer: rawAnswer,
          candidate_values: values, upstream_answer: observed.answer[answerIndex] });
      }
    }
    if (observed.answer.length !== answers.length)
      differences.push({ kind: "ANSWER_COUNT_MISMATCH", question_index: questionIndex });
  }
  return { differences, transformations: [...transformations] };
}

// Only these already-validated fields are compared. Array answer aliases are
// separate parses, so compare bounded string values rather than references.
function samePreservedField(expected, observed) {
  if (Array.isArray(expected)) return Array.isArray(observed) && expected.length <= 26 &&
    observed.length === expected.length && expected.every((value, index) =>
      typeof value === "string" && value.length <= 4_000 && observed[index] === value);
  return typeof expected === typeof observed &&
    (typeof expected === "string" || (typeof expected === "number" && Number.isFinite(expected))) && expected === observed;
}

// Shared by the legacy synthetic replay and the two-stage prompt replay.
// Both check cross-question IDs; the latter also checks preserved fields.
function assessQuiz(parsed, upstream, outline, strict = false) {
  if (strict && (!obj(upstream) || Object.keys(upstream).length !== 1 || !Object.hasOwn(upstream, "questions")))
    return { status: "UNSUPPORTED_OUTPUT", reason: "upstream result has unknown top-level fields" };
  const questions = upstream?.questions;
  if (!Array.isArray(questions) || questions.length !== parsed.length || questions.some(q => {
    if (!obj(q) || !id(q.id) || !types.includes(q.type) || !str(q.question, 8_000, true)) return true;
    if (q.type === "short_answer") return q.hasAnswer !== false || q.answer !== undefined || q.options !== undefined;
    if (q.hasAnswer !== true || !Array.isArray(q.options) || q.options.length < 1 ||
        q.options.some(o => !obj(o) || !str(o.label, 4_000, true)) || !Array.isArray(q.answer) ||
        new Set(q.answer).size !== q.answer.length) return true;
    return q.type === "single" ? q.answer.length !== 1 : q.answer.length < 2;
  })) return { status: "UNSUPPORTED_OUTPUT", reason: "upstream result exceeds the bounded quiz slice" };

  const inspection = inspectQuizDifferences(parsed, questions);
  const seen = new Map();
  for (let index = 0; index < questions.length; index++) {
    const source = parsed[index], result = questions[index];
    if (seen.has(result.id)) inspection.differences.push({ kind: "DUPLICATE_QUESTION_ID",
      question_index: index, first_question_index: seen.get(result.id), id: result.id });
    else seen.set(result.id, index);
    if (strict) {
      for (const field of ["type", "question", "analysis", "points", "commentPrompt", "correctAnswer", "correct_answer"])
        if (Object.hasOwn(source, field) && !samePreservedField(source[field], result[field]))
          inspection.differences.push({ kind: "QUESTION_FIELD_CHANGED", question_index: index, field });
      if (Object.hasOwn(source, "id") && result.id !== source.id)
        inspection.differences.push({ kind: "QUESTION_ID_CHANGED", question_index: index });
      const allowed = ["id", "type", "question", "options", "answer", "correctAnswer", "correct_answer",
        "analysis", "points", "commentPrompt", "hasAnswer"];
      if (Object.keys(result).some(field => !allowed.includes(field)))
        inspection.differences.push({ kind: "UPSTREAM_QUESTION_FIELD_UNSUPPORTED", question_index: index });
    }
  }
  if (inspection.differences.length) return {
    status: "UPSTREAM_RESULT_NOT_ADMITTED", reason: "upstream result has ambiguous or discarded input",
    differences: inspection.differences, observed_upstream: upstream,
  };
  const transformations = inspection.transformations;
  if (parsed.some(q => !q.id)) transformations.push("UNSTABLE_GENERATED_QUESTION_IDS");
  if (parsed.some(q => Array.isArray(q.options) && q.options.some(o => typeof o === "string")))
    transformations.push("PLAIN_OPTIONS_NORMALIZED");
  if (parsed.some((q, i) => q.type !== "short_answer" &&
      JSON.stringify(q.answer ?? q.correctAnswer ?? q.correct_answer) !== JSON.stringify(questions[i].answer)))
    transformations.push("ANSWER_REFERENCE_NORMALIZED");
  if (parsed.some(q => q.type === "short_answer")) transformations.push("SHORT_ANSWER_NOT_GRADED");
  const config = outline.quizConfig ?? { questionCount: 3, questionTypes: ["single"] };
  if (questions.length !== config.questionCount) transformations.push("QUESTION_COUNT_DIFFERS_FROM_REQUEST");
  if (questions.some(q => !config.questionTypes.includes(q.type))) transformations.push("QUESTION_TYPE_DIFFERS_FROM_REQUEST");
  return { status: "CANDIDATE", reason: null, transformations, data: upstream, human_review_required: true };
}

// Structural admission for a reply the donor already repaired. There is no raw
// parse to reconcile against, so only the bounded shape the text-only slice
// also requires is checked; the reply is never presented as exact JSON.
function repairedQuizDifferences(data) {
  if (!obj(data) || Object.keys(data).length !== 1 || !Object.hasOwn(data, "questions"))
    return [{ kind: "UPSTREAM_RESULT_SHAPE_UNSUPPORTED" }];
  const questions = data.questions;
  if (!Array.isArray(questions) || questions.length < 1 || questions.length > 30)
    return [{ kind: "UPSTREAM_QUESTION_COUNT_UNSUPPORTED" }];
  const differences = [], seen = new Map();
  for (let index = 0; index < questions.length; index++) {
    const question = questions[index];
    if (!obj(question) || !id(question.id) || !types.includes(question.type) ||
        !str(question.question, 8_000, true)) {
      differences.push({ kind: "UPSTREAM_QUESTION_SHAPE_UNSUPPORTED", question_index: index });
      continue;
    }
    const allowed = ["id", "type", "question", "options", "answer", "correctAnswer", "correct_answer",
      "analysis", "points", "commentPrompt", "hasAnswer"];
    const unknown = Object.keys(question).filter(field => !allowed.includes(field));
    if (unknown.length)
      differences.push({ kind: "UPSTREAM_QUESTION_FIELDS_UNSUPPORTED", question_index: index,
        fields: unknown.sort() });
    if (question.type === "short_answer") {
      if (question.hasAnswer !== false || question.answer !== undefined || question.options !== undefined)
        differences.push({ kind: "UPSTREAM_SHORT_ANSWER_CONTRACT", question_index: index });
    } else if (question.hasAnswer !== true || !Array.isArray(question.options) ||
        question.options.length < 1 ||
        question.options.some(option => !obj(option) || !str(option.label, 4_000, true)) ||
        !Array.isArray(question.answer) || new Set(question.answer).size !== question.answer.length ||
        (question.type === "single" ? question.answer.length !== 1 : question.answer.length < 2)) {
      differences.push({ kind: "UPSTREAM_CHOICE_CONTRACT", question_index: index });
    }
    if (seen.has(question.id))
      differences.push({ kind: "DUPLICATE_QUESTION_ID", question_index: index,
        first_question_index: seen.get(question.id), id: question.id });
    else seen.set(question.id, index);
  }
  return differences;
}

function base(status, reason, input = null) {
  return { schema: "archeaxis.openmaic-quiz-replay-result/v1", status, reason, input,
    upstream_generation: "0.3.28", upstream_entry: "generateQuizContent excerpt",
    response_origin: "SYNTHETIC_REPLAY", response_origin_verification: "CALLER_DECLARED_UNVERIFIED",
    returned_content_may_include_material_or_answers: true, output_privacy_filter: "NOT_APPLIED",
    logging_safety: "NOT_ESTABLISHED", model_call: "NOT_INVOKED", network_performed: false,
    core_task: "NOT_CONNECTED", full_generate_scene_content: false, full_generation_chain: false,
    canonical_bindings_verified: false, provider_result_verification: "not_established",
    independent_mastery: "not_established", retry_bytes_stable: false,
    active_content_executed: false, runtime, data: null };
}

const PROMPT_SCHEMA = "archeaxis.openmaic-quiz-prompt/v1";
const BINDING_SCHEMA = "archeaxis.openmaic-quiz-prompt-binding/v1";
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
function promptIdentity(request) {
  // An unkeyed comparison, never proof of the selected source or model call.
  // Different outline keyPoints can generate the same numbered prompt, so Core
  // must independently retain the exact selected snapshot and result identity.
  return digest(canonical({ request_id: request.request_id, outline: request.outline,
    language_directive: request.language_directive }));
}
function promptRequestValid(request) {
  const common = ["schema", "stage", "request_id", "outline", "language_directive"];
  if (!obj(request) || request.schema !== PROMPT_SCHEMA || !id(request.request_id) ||
      !validOutline(request.outline) || !safeJson(request.outline) ||
      !str(request.language_directive, 2_000) || !textSafe(request.language_directive)) return false;
  if (request.stage === "capture") return exactKeys(request, common);
  if (request.stage !== "replay" || !exactKeys(request, [...common, "binding", "reply"]) ||
      !exactKeys(request.reply, ["kind", "value"]) || request.reply.kind !== "caller_supplied" ||
      !textSafe(request.reply.value) || Buffer.byteLength(request.reply.value, "utf8") > 120_000) return false;
  const binding = request.binding;
  return exactKeys(binding, ["schema", "request_id", "input_sha256", "outline_manifest_sha256",
    "quiz_manifest_sha256", "quiz_excerpt_sha256", "npm_members_sha256", "worker_sha256", "guard_sha256",
    "system", "user", "system_sha256", "user_sha256"]) && binding.schema === BINDING_SCHEMA &&
    id(binding.request_id) && textSafe(binding.system) && textSafe(binding.user) &&
    Buffer.byteLength(binding.system, "utf8") <= 200_000 && Buffer.byteLength(binding.user, "utf8") <= 200_000 &&
    [binding.input_sha256, binding.outline_manifest_sha256, binding.quiz_manifest_sha256,
      binding.quiz_excerpt_sha256, binding.npm_members_sha256, binding.worker_sha256, binding.guard_sha256,
      binding.system_sha256, binding.user_sha256].every(hashText);
}
function promptBase(status, reason, request) {
  const validated = ["PROMPT_CAPTURED", "BINDING_MISMATCH", "CALLBACK_REJECTED", "UPSTREAM_FAILURE",
    "INVALID_RESPONSE", "UNSUPPORTED_OUTPUT", "UPSTREAM_RECOVERY_NOT_ADMITTED", "UPSTREAM_RESULT_NOT_ADMITTED",
    "CANDIDATE"].includes(status);
  const stage = validated && ["capture", "replay"].includes(request?.stage) ? request.stage : null;
  return { schema: "archeaxis.openmaic-quiz-prompt-result/v1", status, reason,
    request_id: stage && id(request?.request_id) ? request.request_id : null, stage,
    response_origin: stage === "replay" ? "CALLER_SUPPLIED_UNVERIFIED" : "NOT_AVAILABLE",
    model_call: "NOT_INVOKED", network_performed: false, core_task: "NOT_CONNECTED",
    core_authorization: "NOT_ESTABLISHED", canonical_bindings_verified: false,
    identity_scope: "UNKEYED_COMPARISON_ONLY", binding_authentication: "NOT_PROVIDED",
    source_snapshot_authority: "CALLER_DECLARED_ONLY", persisted: false,
    full_generate_scene_content: false, full_generation_chain: false, active_content_executed: false,
    provider_result_verification: "not_established", independent_mastery: "not_established",
    retry_bytes_stable: false, sandbox: "NOT_ESTABLISHED", file_identity_scope: "CHECKED_NOT_HELD_TOCTOU_UNRESOLVED",
    returned_content_may_include_source_material: true, output_privacy_filter: "NOT_APPLIED",
    logging_safety: "NOT_ESTABLISHED", upstream_generation: "0.3.28", runtime, data: null };
}

async function processPromptFrame(request) {
  if (!promptRequestValid(request)) return promptBase("INVALID_REQUEST", "prompt request contract or budget rejected", request);
  const inputIdentity = promptIdentity(request), binding = request.binding;
  if (request.stage === "replay" && (binding.request_id !== request.request_id || binding.input_sha256 !== inputIdentity ||
      binding.outline_manifest_sha256 !== OUTLINE_MANIFEST_SHA || binding.quiz_manifest_sha256 !== QUIZ_MANIFEST_SHA ||
      binding.quiz_excerpt_sha256 !== QUIZ_EXCERPT_SHA || binding.npm_members_sha256 !== npmIdentity ||
      binding.worker_sha256 !== workerIdentity || binding.guard_sha256 !== GUARD_SHA ||
      binding.system_sha256 !== digest(binding.system) || binding.user_sha256 !== digest(binding.user)))
    return promptBase("BINDING_MISMATCH", "input, prompt or donor identity differs", request);
  const warnings = [], failures = [];
  const logger = { debug() {}, info() {}, warn() { warnings.push("UPSTREAM_WARNING"); },
    error() { warnings.push("UPSTREAM_ERROR"); } };
  let parsed, exact = false, responseError = null;
  const guard = createPromptGuard(request.stage === "replay" ? binding : null, () => {
    if (request.stage === "capture") throw new Error("QUIZ_PROMPT_CAPTURE_ONLY");
    try { parsed = JSON.parse(request.reply.value); exact = true; } catch { /* quarantine upstream repair */ }
    if (exact) {
      try {
        rejectDuplicateKeys(request.reply.value);
        if (!safeJson(parsed)) throw new Error("INVALID_RESPONSE");
      } catch { responseError = "INVALID_RESPONSE"; throw new Error("INVALID_RESPONSE"); }
      if (!Array.isArray(parsed) || parsed.length < 1 || parsed.length > 30 ||
          parsed.some(q => !validInputQuestion(q))) {
        responseError = "UNSUPPORTED_OUTPUT"; throw new Error("UNSUPPORTED_OUTPUT");
      }
    }
    return request.reply.value;
  });
  let upstream;
  try {
    upstream = await generateQuizContent(request.outline, guard.callback, request.language_directive, logger,
      failure => failures.push(["prompt-unavailable", "invalid-model-output"].includes(failure?.code)
        ? failure.code : "unknown-upstream-failure"));
  } catch (error) {
    if (guard.state.failure || guard.state.calls !== 1)
      return { ...promptBase("CALLBACK_REJECTED", guard.state.failure || "CALLBACK_COUNT_MISMATCH", request),
        callback_count: guard.state.calls, warnings, failures };
    if (request.stage === "capture" && error instanceof Error && error.message === "QUIZ_PROMPT_CAPTURE_ONLY") {
      const captured = { schema: BINDING_SCHEMA, request_id: request.request_id, input_sha256: inputIdentity,
        outline_manifest_sha256: OUTLINE_MANIFEST_SHA, quiz_manifest_sha256: QUIZ_MANIFEST_SHA,
        quiz_excerpt_sha256: QUIZ_EXCERPT_SHA, npm_members_sha256: npmIdentity,
        worker_sha256: workerIdentity, guard_sha256: GUARD_SHA, system: guard.state.system, user: guard.state.user,
        system_sha256: digest(guard.state.system), user_sha256: digest(guard.state.user) };
      return { ...promptBase("PROMPT_CAPTURED", null, request), binding: captured,
        callback_count: guard.state.calls, warnings, failures };
    }
    if (responseError) return { ...promptBase(responseError, "response outside strict bounded quiz contract", request),
      callback_count: guard.state.calls, warnings, failures };
    return { ...promptBase("UPSTREAM_FAILURE", "upstream quiz helper raised", request),
      callback_count: guard.state.calls, warnings, failures };
  }
  if (guard.state.failure || guard.state.calls !== 1)
    return { ...promptBase("CALLBACK_REJECTED", guard.state.failure || "CALLBACK_COUNT_MISMATCH", request),
      callback_count: guard.state.calls, warnings, failures };
  if (request.stage === "capture")
    return { ...promptBase("UPSTREAM_FAILURE", "capture sentinel was not observed", request),
      callback_count: guard.state.calls, warnings, failures };
  if (upstream === null || upstream === undefined)
    return { ...promptBase("UPSTREAM_FAILURE", "upstream quiz helper returned no result", request),
      callback_count: guard.state.calls, warnings, failures };
  // When the reply was not exact JSON, `parsed` never materialised and the donor
  // already repaired and normalised the text, so there is nothing left to
  // reconcile against a raw parse. The repaired candidate is admitted only after
  // the same bounded structural checks the exact slice applies, and it says out
  // loud that the model bytes were not exact JSON and that the donor's own
  // normalisations cannot be reconstructed one by one.
  if (!exact) {
    const transformations = ["UPSTREAM_JSON_REPAIRED", "UPSTREAM_NORMALIZATIONS_UNRECONSTRUCTED"];
    const differences = repairedQuizDifferences(upstream);
    if (differences.length) return { ...promptBase("UPSTREAM_RESULT_NOT_ADMITTED",
      "unknown, unsupported or altered data", request), callback_count: guard.state.calls,
      warnings, failures, original_reply: request.reply.value, differences, transformations,
      observed_upstream: upstream };
    return { ...promptBase("CANDIDATE", null, request), callback_count: guard.state.calls,
      warnings, failures, transformations, exact_json_output: false, data: upstream,
      human_review_required: true };
  }
  const assessment = assessQuiz(parsed, upstream, request.outline, true);
  const retained = assessment.status === "UPSTREAM_RESULT_NOT_ADMITTED" ? { original_reply: request.reply.value } : {};
  return { ...promptBase(assessment.status, assessment.reason, request), callback_count: guard.state.calls,
    warnings, failures, ...assessment, ...retained,
    ...(assessment.status === "CANDIDATE" ? { exact_json_output: exact } : {}) };
}

async function processFrame(raw) {
  let request;
  try {
    const source = new TextDecoder("utf-8", { fatal: true }).decode(raw);
    request = JSON.parse(source); rejectDuplicateKeys(source);
  } catch {
    // A malformed or duplicate-key frame cannot be safely assigned a schema.
    // Unlike the older error receipt, omit its original bytes AND digest.
    // The caller owns any retention of its original input; this worker does not.
    return base("INVALID_REQUEST", "invalid bounded UTF-8 JSON or duplicate keys");
  }
  if (request?.schema === PROMPT_SCHEMA) {
    try { return await processPromptFrame(request); }
    catch { return promptBase("PROCESSING_FAILURE", "quiz prompt processing failed", null); }
  }
  if (!validRequest(request)) return { ...base("INVALID_REQUEST", "request contract or budget rejected"),
    input_sha256: digest(raw) };
  const resultBase = (status, reason) => ({ ...base(status, reason, request), input_sha256: digest(raw) });

  let parsed, exact = false;
  if (request.reply.kind === "synthetic_response") {
    try { parsed = JSON.parse(request.reply.value); exact = true; } catch { /* upstream may repair */ }
    if (exact) {
      try { rejectDuplicateKeys(request.reply.value); }
      catch { return resultBase("INVALID_RESPONSE", "ambiguous duplicate keys or excessive nesting"); }
      if (!Array.isArray(parsed) || parsed.length < 1 || parsed.length > 30 ||
          parsed.some(q => !validInputQuestion(q)))
        return resultBase("UNSUPPORTED_OUTPUT", "response is outside the bounded quiz slice");
    }
  }
  const calls = [], warnings = [], failures = [];
  const logger = { debug() {}, info() {}, warn() { warnings.push("UPSTREAM_WARNING"); },
    error() { warnings.push("UPSTREAM_ERROR"); } };
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
  try {
    upstream = await generateQuizContent(request.outline, replayCall, request.language_directive, logger,
      failure => failures.push(["prompt-unavailable", "invalid-model-output"].includes(failure?.code)
        ? failure.code : "unknown-upstream-failure"));
  } catch {
    return { ...resultBase("UPSTREAM_FAILURE", "upstream quiz helper or synthetic callback raised"), calls, warnings, failures };
  }
  if (upstream === null) return { ...resultBase("UPSTREAM_FAILURE", "upstream quiz helper returned null"), calls, warnings, failures };
  if (!exact) return { ...resultBase("UPSTREAM_RECOVERY_NOT_ADMITTED", "non-exact response was recovered upstream"),
    calls, warnings, failures, upstream_reported_success: true };

  const assessment = assessQuiz(parsed, upstream, request.outline);
  return { ...resultBase(assessment.status, assessment.reason), calls, warnings, failures, ...assessment };
}

if (process.argv.length === 3 && process.argv[2] === "--hello") {
  process.stdout.write(JSON.stringify({ schema: "archeaxis.openmaic-quiz-replay-hello/v1",
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
    result = result.schema === "archeaxis.openmaic-quiz-prompt-result/v1"
      ? promptBase("INVALID_REQUEST", "output exceeds byte budget", null)
      : base("INVALID_REQUEST", "output exceeds byte budget");
    output = JSON.stringify(result);
  }
  process.stdout.write(output + "\n");
  if (!["CANDIDATE", "PROMPT_CAPTURED"].includes(result.status)) process.exitCode = 2;
}
