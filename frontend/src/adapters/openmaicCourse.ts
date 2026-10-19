import type { CourseImportDraft, ImportedQuestion } from "../presentation/importedCourse";

// Independent adapter to the public export contract, pinned to this revision; no upstream runtime.
export const OPENMAIC_COMMIT = "6b83751a87896df99c47e98c20cea40cec09efb4";
export const COURSE_IMPORT_MAX_BYTES = 256 * 1024;
function fail(path: string, reason: string): never { throw new Error(`${path}：${reason}`); }
function record(value: unknown, path: string): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) fail(path, "需要对象");
  return value as Record<string, unknown>;
}
function fields(value: Record<string, unknown>, allowed: string[], path: string) {
  for (const key of Object.keys(value)) if (!allowed.includes(key)) fail(`${path}.${key}`, "不支持的字段；未静默丢弃");
}
function text(value: unknown, path: string, max = 16000): string {
  if (typeof value !== "string" || !value.trim() || value.length > max) fail(path, `需要非空文本，最多 ${max} 字符`);
  return value;
}
function list(value: unknown, path: string, max: number, min = 0): unknown[] {
  if (!Array.isArray(value) || value.length < min || value.length > max) fail(path, `数量必须为 ${min}–${max}`);
  return value;
}
function empty(value: unknown, path: string, array: boolean) {
  if (value === undefined) return;
  if (array ? !Array.isArray(value) || value.length !== 0 : Object.keys(record(value, path)).length !== 0)
    fail(path, "首批不支持该内容；可另行仅保全原件");
}
function question(input: unknown, path: string): ImportedQuestion {
  const q = record(input, path);
  fields(q, ["id", "type", "question", "options", "answer", "analysis", "commentPrompt", "hasAnswer", "points"], path);
  text(q.id, `${path}.id`, 128); text(q.question, `${path}.question`);
  if (!["single", "multiple", "short_answer"].includes(q.type as string)) fail(`${path}.type`, "不支持的题型");
  if (q.hasAnswer !== undefined && typeof q.hasAnswer !== "boolean") fail(`${path}.hasAnswer`, "需要布尔值");
  if (q.points !== undefined && (typeof q.points !== "number" || !Number.isFinite(q.points) || q.points <= 0)) fail(`${path}.points`, "分值必须为有限正数");
  for (const key of ["analysis", "commentPrompt"]) if (q[key] !== undefined && (typeof q[key] !== "string" || (q[key] as string).length > 16000)) fail(`${path}.${key}`, "文本超预算或类型无效");
  const options = q.options === undefined ? [] : list(q.options, `${path}.options`, 32).map((item, i) => {
    const option = record(item, `${path}.options[${i}]`); fields(option, ["label", "value"], `${path}.options[${i}]`);
    return { label: text(option.label, `${path}.options[${i}].label`, 4000), value: text(option.value, `${path}.options[${i}].value`, 512) };
  });
  if ((q.type !== "short_answer" && options.length < 2) || new Set(options.map(o => o.value)).size !== options.length)
    fail(`${path}.options`, "选择题至少两个选项，选项值不得重复");
  if (q.type === "short_answer" && options.length) fail(`${path}.options`, "短答选项无法呈现，未丢弃");
  const answer = q.answer === undefined ? undefined : list(q.answer, `${path}.answer`, 32).map((a, i) => text(a, `${path}.answer[${i}]`, 16000));
  if (answer && (new Set(answer).size !== answer.length || (q.type === "single" && answer.length > 1)
      || (q.type !== "short_answer" && answer.some(a => !options.some(o => o.value === a))))) fail(`${path}.answer`, "答案数量、去重或选项引用无效");
  if (q.hasAnswer === true && !answer?.length) fail(`${path}.answer`, "声明有参考答案但未提供");
  // Preserve every supported field, including an inactive reference or inert commentPrompt.
  return q as ImportedQuestion;
}
export function parseOpenMaicCourse(bytes: Uint8Array): CourseImportDraft {
  if (bytes.length === 0 || bytes.length > COURSE_IMPORT_MAX_BYTES) fail("$", "文件必须为 1 字节至 256 KiB；不会截断");
  let raw: unknown;
  try { raw = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes)); }
  catch { return fail("$", "需要有效 UTF-8 JSON manifest 文件"); }
  const root = record(raw, "$");
  fields(root, ["formatVersion", "exportedAt", "appVersion", "stage", "agents", "scenes", "mediaIndex"], "$");
  if (root.formatVersion !== 1) fail("$.formatVersion", "仅支持格式 1");
  text(root.exportedAt, "$.exportedAt", 128); text(root.appVersion, "$.appVersion", 128);
  const stage = record(root.stage, "$.stage");
  fields(stage, ["name", "description", "language", "style", "videoManifest", "createdAt", "updatedAt"], "$.stage");
  const title = text(stage.name, "$.stage.name", 240);
  for (const k of ["description", "language", "style"]) if (stage[k] !== undefined && (typeof stage[k] !== "string" || (stage[k] as string).length > 16000)) fail(`$.stage.${k}`, "需要预算内的文本");
  for (const k of ["createdAt", "updatedAt"]) if (typeof stage[k] !== "number" || !Number.isFinite(stage[k])) fail(`$.stage.${k}`, "需要有限时间值");
  empty(stage.videoManifest, "$.stage.videoManifest", false);
  // Role metadata stays in original CAS bytes, never instantiates a model, avatar, prompt or voice.
  const agents = list(root.agents, "$.agents", 32);
  agents.forEach((a, i) => record(a, `$.agents[${i}]`));
  record(root.mediaIndex, "$.mediaIndex"); empty(root.mediaIndex, "$.mediaIndex", false);
  let total = 0;
  const scenes = list(root.scenes, "$.scenes", 64, 1).map((input, i) => {
    const path = `$.scenes[${i}]`, s = record(input, path);
    fields(s, ["type", "title", "order", "content", "actions", "whiteboards", "multiAgent"], path);
    if (s.type !== "quiz") fail(`${path}.type`, "首批仅支持 quiz，完整画布尚未适配");
    const sceneTitle = text(s.title, `${path}.title`, 240);
    if (!Number.isSafeInteger(s.order) || (s.order as number) < 0) fail(`${path}.order`, "需要非负安全整数");
    empty(s.actions, `${path}.actions`, true); empty(s.whiteboards, `${path}.whiteboards`, true);
    if (s.multiAgent !== undefined) {
      const m = record(s.multiAgent, `${path}.multiAgent`);
      fields(m, ["enabled", "agentIndices", "directorPrompt"], `${path}.multiAgent`);
      if (m.enabled !== false) fail(`${path}.multiAgent`, "首批不执行多角色课堂");
      list(m.agentIndices, `${path}.multiAgent.agentIndices`, 32).forEach(index => {
        if (!Number.isSafeInteger(index) || (index as number) < 0 || (index as number) >= agents.length) fail(`${path}.multiAgent.agentIndices`, "角色引用无效");
      });
      if (m.directorPrompt !== undefined && typeof m.directorPrompt !== "string") fail(`${path}.multiAgent.directorPrompt`, "需要文本");
    }
    const content = record(s.content, `${path}.content`); fields(content, ["type", "questions"], `${path}.content`);
    if (content.type !== "quiz") fail(`${path}.content.type`, "场景与内容类型不匹配");
    const questions = list(content.questions, `${path}.content.questions`, 200, 1).map((q, j) => question(q, `${path}.content.questions[${j}]`));
    total += questions.length;
    if (total > 200 || new Set(questions.map(q => q.id)).size !== questions.length) fail(`${path}.content.questions`, "总题数超过 200 或同场景题 ID 重复");
    return { title: sceneTitle, order: s.order as number, questions };
  });
  if (new Set(scenes.map(s => s.order)).size !== scenes.length) fail("$.scenes.order", "场景顺序重复");
  return { title, scenes, report: ["参考答案由外部课件提供，尚未核验。", "题目与解析按文本呈现；未执行脚本、模型或网络请求。",
    "课堂时间、风格与角色等元数据保留在原件；本视图不渲染或执行。", ...(agents.length ? [`已保全 ${agents.length} 个角色的原始元数据，未启用课堂角色。`] : [])] };
}
