import { COURSE_IMPORT_MAX_BYTES, parseOpenMaicCourse } from "./openmaicCourse";
import type { CourseImportDraft, ImportedTextElement, ImportedTextSlide } from "../presentation/importedCourse";

// OpenMAIC 1.3.0 classroom-zip-types.ts: the upstream manifest is formatVersion 1.
// AAOS v2 below is a separate, narrower adapter contract, not an upstream version claim.
export const OPENMAIC_13_ADAPTER = "openmaic-1.3.0-manifest/v2" as const;
export const OPENMAIC_13_VERSION = "1.3.0" as const;
function fail(path: string, reason: string): never { throw new Error(`${path}：${reason}`); }
function record(value: unknown, path: string): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) fail(path, "需要对象");
  return value as Record<string, unknown>;
}
function text(value: unknown, path: string, max: number): string {
  if (typeof value !== "string" || !value.trim() || value.length > max) fail(path, `需要非空文本，最多 ${max} 字符`);
  return value;
}
function number(value: unknown, path: string, minimum: number, maximum: number): number {
  if (typeof value !== "number" || !Number.isFinite(value) || value < minimum || value > maximum)
    fail(path, `需要 ${minimum}–${maximum} 的有限数值`);
  return value;
}
function list(value: unknown, path: string, max: number): unknown[] {
  if (!Array.isArray(value) || value.length > max) fail(path, `需要数组，最多 ${max} 项`);
  return value;
}
function color(value: unknown, path: string): string {
  const result = text(value, path, 64);
  // Canvas colors are deliberately limited to local, non-URL CSS colors.
  if (!/^#(?:[a-f\d]{3}|[a-f\d]{4}|[a-f\d]{6}|[a-f\d]{8})$/i.test(result) && !/^[a-z]{1,24}$/i.test(result))
    fail(path, "仅支持十六进制或命名颜色");
  return result;
}
function raw(bytes: Uint8Array): Record<string, unknown> {
  if (!bytes.length || bytes.length > COURSE_IMPORT_MAX_BYTES) fail("$", "文件必须为 1 字节至 256 KiB；不会截断");
  try { return record(JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes)), "$"); }
  catch (error) { if (error instanceof Error && error.message.startsWith("$：")) throw error; return fail("$", "需要有效 UTF-8 JSON manifest 文件"); }
}
/** New input only. Upstream export falls back to 0.0.0 when npm_package_version is absent. */
export function isOpenMaic13Manifest(bytes: Uint8Array): boolean {
  return [OPENMAIC_13_VERSION, "0.0.0"].includes(raw(bytes).appVersion as string);
}
function encoded(value: unknown): Uint8Array { return new TextEncoder().encode(JSON.stringify(value)); }

function slide(value: unknown, path: string): ImportedTextSlide {
  const canvas = record(value, path);
  const allowed = ["id", "viewportSize", "viewportRatio", "theme", "elements", "background", "animations", "turningMode", "sectionTag", "type", "script"];
  for (const key of Object.keys(canvas)) if (!allowed.includes(key)) fail(`${path}.${key}`, "未知画布字段；可单独保全原件");
  text(canvas.id, `${path}.id`, 128);
  number(canvas.viewportSize, `${path}.viewportSize`, 1, 10000);
  number(canvas.viewportRatio, `${path}.viewportRatio`, 0.1, 10);
  const theme = record(canvas.theme, `${path}.theme`);
  color(theme.backgroundColor, `${path}.theme.backgroundColor`);
  color(theme.fontColor, `${path}.theme.fontColor`);
  text(theme.fontName, `${path}.theme.fontName`, 240);
  list(theme.themeColors, `${path}.theme.themeColors`, 32).forEach((item, i) => color(item, `${path}.theme.themeColors[${i}]`));
  if (canvas.background !== undefined) {
    const bg = record(canvas.background, `${path}.background`);
    if (bg.type !== "solid") fail(`${path}.background.type`, "仅支持纯色背景；图片与渐变未接入");
    if (bg.color !== undefined) color(bg.color, `${path}.background.color`);
    if (Object.keys(bg).some(key => key !== "type" && key !== "color")) fail(`${path}.background`, "未知背景字段；可单独保全原件");
  }
  if (canvas.animations !== undefined && list(canvas.animations, `${path}.animations`, 100).length)
    fail(`${path}.animations`, "不执行动画；可单独保全原件");
  const elements = list(canvas.elements, `${path}.elements`, 200).map((input, i) => {
    const p = `${path}.elements[${i}]`, element = record(input, p);
    if (element.type !== "text") fail(`${p}.type`, "仅支持文本元素；媒体、图形与未知渲染器未接入");
    text(element.id, `${p}.id`, 128);
    const content = text(element.content, `${p}.content`, 16000);
    if (/<\s*(?:img|video|audio|iframe|object|embed|svg|canvas|script|style|link|base|form)\b/i.test(content))
      fail(`${p}.content`, "文本中含媒体或活动内容；可单独保全原件");
    text(element.defaultFontName, `${p}.defaultFontName`, 240); color(element.defaultColor, `${p}.defaultColor`);
    for (const key of ["left", "top"]) number(element[key], `${p}.${key}`, -10000, 10000);
    for (const key of ["width", "height"]) number(element[key], `${p}.${key}`, 0.01, 10000);
    number(element.rotate, `${p}.rotate`, -3600, 3600);
    return element as ImportedTextElement;
  });
  if (new Set(elements.map(element => element.id)).size !== elements.length) fail(`${path}.elements`, "元素 ID 重复");
  // Keep every canvas field in the candidate; the view only consumes the validated subset.
  return canvas as ImportedTextSlide;
}

export function parseOpenMaicCourseV2(bytes: Uint8Array): CourseImportDraft {
  const root = raw(bytes);
  if (root.formatVersion !== 1) fail("$.formatVersion", "上游仅支持格式 1；未知格式未转换");
  if (root.appVersion !== OPENMAIC_13_VERSION && root.appVersion !== "0.0.0")
    fail("$.appVersion", "仅接受 1.3.0 或上游导出器的 0.0.0 回退声明");
  const scenes = list(root.scenes, "$.scenes", 64);
  if (!scenes.length) fail("$.scenes", "至少需要一个场景");
  const sceneRows = scenes.map((item, i) => {
    const path = `$.scenes[${i}]`, row = record(item, path);
    if (row.type !== "quiz" && row.type !== "slide") fail(`${path}.type`, "仅支持 quiz 和文本 slide；可单独保全原件");
    return row;
  });
  const quizzes = sceneRows.filter(row => row.type === "quiz");
  // Reuse the existing strict v1 validation for the manifest envelope, quiz fields,
  // aggregate question budget, empty media, action and multi-agent boundaries.
  const dummyQuiz = { type: "quiz", title: "validation", order: 0,
    content: { type: "quiz", questions: [{ id: "validation", type: "short_answer", question: "validation" }] } };
  const base = parseOpenMaicCourse(encoded({ ...root, scenes: quizzes.length ? quizzes : [dummyQuiz] }));
  const quizByOrder = new Map(base.scenes.map(scene => [scene.order, scene]));
  const converted = sceneRows.map((row, i) => {
    const path = `$.scenes[${i}]`;
    if (row.type === "quiz") {
      const result = quizByOrder.get(row.order as number);
      if (!result) fail(`${path}.order`, "无法核对题目场景");
      return { ...result, kind: "quiz" as const };
    }
    const content = record(row.content, `${path}.content`);
    for (const key of Object.keys(content)) if (!["type", "schemaVersion", "canvas"].includes(key))
      fail(`${path}.content.${key}`, "未知内容字段；可单独保全原件");
    if (content.type !== "slide") fail(`${path}.content.type`, "场景与内容类型不匹配");
    if (content.schemaVersion !== undefined && content.schemaVersion !== 1)
      fail(`${path}.content.schemaVersion`, "未知幻灯片版本；可单独保全原件");
    const checked = parseOpenMaicCourse(encoded({ ...root, scenes: [{ ...row, type: "quiz", content: dummyQuiz.content }] }));
    return { title: checked.scenes[0].title, order: checked.scenes[0].order, kind: "slide" as const,
      questions: [], slide: slide(content.canvas, `${path}.content.canvas`) };
  });
  if (new Set(converted.map(scene => scene.order)).size !== converted.length) fail("$.scenes.order", "场景顺序重复");
  return { title: base.title, scenes: converted, report: [
    "参考答案由外部课件提供，尚未核验；作答记录不代表掌握或复习成绩。",
    "文本幻灯片仅按画布位置呈现纯文本；字体、富文本格式、链接、转场及讲稿不执行，原始画布保存在原件和候选中。",
    "媒体、图形、互动、动画、讲解动作及非纯色背景尚未接入；遇到时可单独保全原件。",
    "课件所填 appVersion 是输入声明；适配器版本不证明课件来源或内容真实性。",
  ] };
}
