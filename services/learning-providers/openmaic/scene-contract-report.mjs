/** Unregistered reference derivation of the AAOS scene contract report.
 *
 * The canonical implementation is Rust Core (`crates/archeaxis-domain/src/course.rs`,
 * `openmaic_refusal` / `openmaic_projection` / `openmaic_render_contract`). This module
 * re-derives the same rules from one already-built request and the worker reply it got,
 * so a test can check the rules against the real donor projection without compiling
 * Rust. It builds no scene, calls no model, opens no network, writes no Core record and
 * renders nothing; `authority_effect` stays "none_reference_only". A divergence between
 * this module and the Rust implementation is a defect, not a second contract.
 */
import { createHash } from "node:crypto";

const INPUT = "archeaxis.openmaic-scene-contract-input/v1";
const REPORT = "archeaxis.openmaic-scene-contract-report/v1";
const PROJECTION = "archeaxis.openmaic-scene-projection/v2";
const RENDER = "archeaxis.openmaic-scene-render/v1";
const REQUEST_SCHEMA = "archeaxis.openmaic-scene-build/v1";
const RESULT_SCHEMA = "archeaxis.openmaic-scene-build-result/v1";
const SCENE_TYPES = ["slide", "quiz"];
const QUESTION_TYPES = ["single", "multiple", "short_answer"];
const MAX_INPUT = 512_000;
const MAX_OUTPUT = 1_000_000;
const MAX_OMITTED = 64;

const object = value => value !== null && typeof value === "object" && !Array.isArray(value);
const text = (value, max) =>
  typeof value === "string" && value.trim().length > 0 && value.length <= max && !value.includes("\0");
const number = (value, min, max) =>
  typeof value === "number" && Number.isFinite(value) && value >= min && value <= max;
const sha256 = bytes => createHash("sha256").update(bytes).digest("hex");

/** Content fields `buildCompleteScene` copies into each scene kind. */
const CARRIED = Object.freeze({
  outline: Object.freeze(["id", "type", "title", "order"]),
  content: Object.freeze({
    slide: Object.freeze(["elements", "background"]),
    quiz: Object.freeze(["questions"]),
    interactive: Object.freeze(["html", "widgetType", "widgetConfig"]),
    pbl: Object.freeze(["projectV2"]),
  }),
});

/** Mirrors `openmaic_refusal`: name what this slice cannot build. */
function refusal(request) {
  if (typeof request.schema === "string" && request.schema !== REQUEST_SCHEMA)
    return { reason: "UNSUPPORTED_REQUEST_VERSION", declared: request.schema, supported: [REQUEST_SCHEMA] };
  if (!object(request.outline)) return null;
  const kind = request.outline.type;
  if (typeof kind !== "string") return null;
  if (!SCENE_TYPES.includes(kind))
    return { reason: "UNSUPPORTED_SCENE", scene_type: kind, supported_scene_types: SCENE_TYPES };
  if (!object(request.content)) return null;
  const declared = request.content.schemaVersion;
  if (declared !== undefined && declared !== 1)
    return { reason: "UNSUPPORTED_SCENE_VERSION", scene_type: kind, declared, supported_scene_versions: [1] };
  return null;
}

/** Mirrors `openmaic_projection`: every request field the scene does not carry. */
export function projection(request) {
  const kind = object(request.outline) && typeof request.outline.type === "string" ? request.outline.type : "";
  const carried = CARRIED.content[kind] || [];
  const omitted = [];
  if (object(request.outline))
    for (const key of Object.keys(request.outline)) if (!CARRIED.outline.includes(key)) omitted.push(`outline.${key}`);
  if (object(request.content))
    for (const key of Object.keys(request.content)) if (!carried.includes(key)) omitted.push(`content.${key}`);
  if (omitted.length > MAX_OMITTED) omitted.length = MAX_OMITTED;
  omitted.sort();
  return {
    contract: PROJECTION,
    lossless: omitted.length === 0,
    scene_type: kind,
    omitted,
    basis:
      "Compared the stored request with the persisted scene projection; every request field " +
      "the projection does not carry is listed, never silently dropped",
  };
}

/** Mirrors `openmaic_text_element_defect`. */
function textElementDefect(element) {
  if (!object(element)) return "element is not an object";
  if (element.type !== "text") return "only text elements are rendered";
  if (!text(element.id, 128)) return "element needs a bounded ID";
  const content = typeof element.content === "string" ? element.content : "";
  if (!text(element.content, 16_000)) return "element needs bounded text content";
  for (const tag of ["img", "video", "audio", "iframe", "object", "embed", "svg", "canvas"])
    if (content.includes(`<${tag}`)) return "active content is not executed";
  if (
    !number(element.left, -10_000, 10_000) ||
    !number(element.top, -10_000, 10_000) ||
    !number(element.width, 0.01, 10_000) ||
    !number(element.height, 0.01, 10_000) ||
    !number(element.rotate, -3_600, 3_600)
  )
    return "element needs bounded canvas geometry";
  return null;
}

/** Mirrors `openmaic_question_defect`. */
function questionDefect(question) {
  if (!object(question)) return "question is not an object";
  if (!text(question.id, 128)) return "question needs a bounded ID";
  if (typeof question.type !== "string" || !QUESTION_TYPES.includes(question.type))
    return "only single/multiple/short_answer questions are scored";
  if (!text(question.question, 16_000)) return "question needs bounded text";
  if (question.options !== undefined) {
    if (!Array.isArray(question.options)) return "options must be a list";
    if (
      question.options.length > 32 ||
      question.options.some(option => !object(option) || !text(option.label, 4_000) || !text(option.value, 512))
    )
      return "options need bounded label/value pairs";
  }
  if (question.answer !== undefined) {
    if (!Array.isArray(question.answer)) return "answer must be a list of option values";
    if (question.answer.length > 32 || question.answer.some(item => !text(item, 16_000)))
      return "answer references must be bounded text";
  }
  return null;
}

/** Mirrors `openmaic_render_contract`. */
export function renderContract(scene) {
  const sceneType = object(scene) && typeof scene.type === "string" ? scene.type : "";
  const unsupported = [];
  let elements = 0;
  let questions = 0;
  let renderer = null;
  if (sceneType === "slide") {
    renderer = "openmaic-canvas-text";
    const canvas = object(scene.content) && object(scene.content.canvas) ? scene.content.canvas : null;
    if (!canvas) unsupported.push({ path: "content.canvas", reason: "canvas is missing" });
    const list = canvas && Array.isArray(canvas.elements) ? canvas.elements : [];
    elements = list.length;
    list.forEach((element, index) => {
      const defect = textElementDefect(element);
      if (defect) unsupported.push({ path: `content.canvas.elements[${index}]`, reason: defect });
    });
    if (canvas && Array.isArray(canvas.animations) && canvas.animations.length)
      unsupported.push({ path: "content.canvas.animations", reason: "animation is not played" });
  } else if (sceneType === "quiz") {
    renderer = "openmaic-quiz-objective";
    const list = object(scene.content) && Array.isArray(scene.content.questions) ? scene.content.questions : [];
    questions = list.length;
    const seen = new Set();
    list.forEach((question, index) => {
      const defect = questionDefect(question);
      if (defect) {
        unsupported.push({ path: `content.questions[${index}]`, reason: defect });
        return;
      }
      if (seen.has(question.id))
        unsupported.push({ path: `content.questions[${index}]`, reason: "duplicate question ID" });
      seen.add(question.id);
    });
  } else {
    unsupported.push({ path: "type", reason: "scene type is not playable here" });
  }
  return {
    schema: RENDER,
    playable: SCENE_TYPES.includes(sceneType) && unsupported.length === 0,
    renderer,
    scene_type: sceneType,
    supported_scene_types: SCENE_TYPES,
    counts: { elements, questions, unsupported: unsupported.length },
    unsupported,
    basis:
      "Derived from the persisted inert scene; playable means the stored content has the shape a " +
      "renderer needs, not that rendering is authorized or scored",
  };
}

function failure(status, reason) {
  return {
    schema: REPORT,
    status,
    reason,
    refusal: null,
    projection: null,
    render: null,
    authority_effect: "none_reference_only",
    canonical_implementation: "crates/archeaxis-domain/src/course.rs",
  };
}

function processFrame(raw) {
  try {
    const source = new TextDecoder("utf-8", { fatal: true }).decode(raw);
    const input = JSON.parse(source);
    const keys = ["schema", "request", "worker_document"];
    if (
      !object(input) ||
      Object.keys(input).length !== keys.length ||
      keys.some(key => !Object.hasOwn(input, key)) ||
      input.schema !== INPUT ||
      !object(input.request) ||
      !object(input.request.outline) ||
      !object(input.request.content)
    )
      return failure("INVALID_REQUEST", "input contract or budget rejected");
    const inputSha = sha256(raw);
    const refused = refusal(input.request);
    const worker = input.worker_document;
    const workerScene =
      object(worker) && worker.schema === RESULT_SCHEMA && worker.status === "CANDIDATE" && object(worker.scene)
        ? worker.scene
        : null;
    const base = {
      schema: REPORT,
      input_sha256: inputSha,
      refusal: refused,
      scene_type: object(input.request.outline) ? (input.request.outline.type ?? null) : null,
      worker_candidate_observed: workerScene !== null,
      authority_effect: "none_reference_only",
      canonical_implementation: "crates/archeaxis-domain/src/course.rs",
    };
    if (refused)
      return { ...base, status: "REFUSED", projection: null, render: null, reason: "the request names a contract this slice cannot build" };
    if (!workerScene)
      return { ...base, status: "NO_CANDIDATE", projection: projection(input.request), render: null, reason: "the reply is not a candidate scene" };
    return {
      ...base,
      status: "REPORT",
      projection: projection(input.request),
      render: renderContract(workerScene),
      reason: null,
    };
  } catch {
    return failure("INVALID_REQUEST", "invalid bounded UTF-8 JSON input");
  }
}

if (process.argv.slice(2).length === 1 && process.argv[2] === "--hello") {
  process.stdout.write(
    JSON.stringify({
      schema: "archeaxis.derived-worker-hello/v1",
      capability: "course.openmaic.scene-contract",
      version: 1,
      canonical_implementation: "crates/archeaxis-domain/src/course.rs",
      registered: false,
      core_transport: "NOT_CONNECTED",
    }) + "\n",
  );
} else if (process.argv.length !== 2) {
  process.stdout.write(JSON.stringify(failure("INVALID_REQUEST", "unsupported arguments")) + "\n");
  process.exitCode = 2;
} else {
  let length = 0;
  let overflow = false;
  const chunks = [];
  for await (const chunk of process.stdin) {
    length += chunk.length;
    if (length > MAX_INPUT) overflow = true;
    if (!overflow) chunks.push(chunk);
  }
  let result =
    overflow || !length
      ? failure("INVALID_REQUEST", "input exceeds byte budget or is empty")
      : processFrame(Buffer.concat(chunks));
  let output = JSON.stringify(result);
  if (Buffer.byteLength(output, "utf8") > MAX_OUTPUT) {
    result = failure("INVALID_REQUEST", "report exceeds output byte budget");
    output = JSON.stringify(result);
  }
  process.stdout.write(output + "\n");
  if (result.status === "INVALID_REQUEST") process.exitCode = 2;
}
