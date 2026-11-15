import { coreCommand } from "../api/core";
import { ApiError } from "../api/client";
import type { DocumentDto } from "../api/generated/core-contract";
import { parseOpenMaicQuestion } from "../adapters/openmaicCourse";
import { parseOpenMaicTextCanvas } from "../adapters/openmaicCourseV2";
import type { ImportedQuestion, ImportedTextSlide } from "./importedCourse";
import { documentRequestIdentity } from "./documentRequestIdentity";
import { object, pinnedDocument, sameValue, sha256 } from "./exchangeProof";

type Snapshot = { document_id: string; version: number; content_sha256: string };
export type SceneStep = { id: string; kind: "speech" | "spotlight" | "laser" | "unsupported"; text: string; elementId?: string };
export type SavedScene = { document: DocumentDto; title: string; order: number; source: Snapshot; sourceStatus: "current" | "historical" | "unavailable";
  slide?: ImportedTextSlide; questions: ImportedQuestion[]; steps: SceneStep[]; limitations: string[]; fallback?: string };
const snapshot = (d: DocumentDto): Snapshot => ({ document_id: d.document_id, version: d.version, content_sha256: d.content_sha256 });
const bounded = (v: unknown, max: number): v is string => typeof v === "string" && v.length > 0 && v.length <= max;
const token = (v: unknown): v is string => typeof v === "string" && /^[A-Za-z0-9_-]{1,128}$/.test(v);
function validSnapshot(v: unknown): v is Snapshot {
  if (!v || typeof v !== "object") return false;
  const s = v as Snapshot;
  return token(s.document_id) && Number.isSafeInteger(s.version) && s.version > 0 && /^[a-f0-9]{64}$/.test(s.content_sha256);
}
function mismatch(): never { throw new Error("场景投影与固定文档版本不一致；未呈现替代内容。"); }

/** Consumes saved scene Documents, never impersonates an imported upstream manifest.
 * Action fields follow the in-repo OpenMAIC 1.3.0 packages/@openmaic/dsl/src/action.ts.
 * Speech is a transcript; spotlight/laser are static focus, not upstream audio/effect execution.
 */
export function sceneView(document: DocumentDto, report: unknown): SavedScene {
  const r = object(report), attrs = object(object(document.editor_json).attrs), saved = object(attrs.archeaxis_openmaic_scene_candidate);
  if (r.document_id !== document.document_id || r.document_version !== document.version || r.document_content_sha256 !== document.content_sha256
    || r.status !== "recorded" || r.contract_version !== "archeaxis.openmaic-scene-document/v2"
    || saved.schema !== r.contract_version || saved.human_review_required !== true || saved.rendering_authorized !== false) mismatch();
  const worker = object(saved.worker_document), scene = object(worker.scene), render = object(saved.render);
  if (worker.status !== "CANDIDATE" || worker.active_content_executed !== false || worker.rendering_authorized !== false
    || worker.human_review_required !== true || !bounded(scene.title, 240) || !Number.isSafeInteger(scene.order) || (scene.order as number) < 0
    || render.schema !== "archeaxis.openmaic-scene-render/v1" || render.scene_type !== scene.type || r.scene_type !== scene.type
    || r.renderer !== render.renderer || r.playability !== (render.playable === true ? "playable" : "not_playable")) mismatch();
  if (!bounded(saved.request_frame, 256000)) mismatch();
  const frame = object(JSON.parse(saved.request_frame));
  if (!validSnapshot(frame.source)) mismatch();
  const result: SavedScene = { document, title: scene.title, order: scene.order as number, source: frame.source,
    sourceStatus: "unavailable", questions: [], steps: [], limitations: ["内容和参考答案仍是待复核候选；本页不将阅读、作答或保存位置视为掌握。"] };
  if (render.playable !== true) { result.fallback = "此场景尚无受支持的呈现方式；原文档仍保留，可返回资料页读取或导出。"; return result; }
  try {
    const content = object(scene.content);
    if (scene.type === "slide" && render.renderer === "openmaic-canvas-text" && content.type === "slide") {
      if (content.schemaVersion !== undefined && content.schemaVersion !== 1) throw new Error("未知画布版本");
      result.slide = parseOpenMaicTextCanvas(content.canvas);
      result.limitations.push("文字按原画布位置呈现；富文本格式、媒体、动画与音频未播放。聚焦只显示静态边框。");
    } else if (scene.type === "quiz" && render.renderer === "openmaic-quiz-objective" && content.type === "quiz") {
      if (!Array.isArray(content.questions) || !content.questions.length || content.questions.length > 200) throw new Error("题目数量无效");
      result.questions = content.questions.map((q, i) => parseOpenMaicQuestion(q, `questions[${i}]`));
      if (new Set(result.questions.map(q => q.id)).size !== result.questions.length) throw new Error("题目身份重复");
    } else throw new Error("未知呈现版本");
  } catch { result.slide = undefined; result.questions = []; result.fallback = "当前视图不能完整读取此画布或题目；原文档保留，未忽略不支持内容并宣称成功。"; return result; }
  if (!Array.isArray(scene.actions) || scene.actions.length > 256) mismatch();
  const seen = new Set<string>();
  result.steps = scene.actions.map((input, index): SceneStep => {
    const a = object(input);
    if (!bounded(a.id, 128) || seen.has(a.id)) mismatch();
    seen.add(a.id);
    if (a.type === "speech" && bounded(a.text, 16000)) return { id: a.id, kind: "speech", text: a.text };
    if ((a.type === "spotlight" || a.type === "laser") && typeof a.elementId === "string"
      && result.slide?.elements.some(e => e.id === a.elementId)) return { id: a.id, kind: a.type, elementId: a.elementId, text: `聚焦课件元素 ${a.elementId}` };
    return { id: a.id, kind: "unsupported", text: `第 ${index + 1} 个讲解动作暂未支持，已保留原记录；未执行。` };
  });
  return result;
}

export async function readSceneCandidate(id: string): Promise<SavedScene> {
  if (!token(id)) mismatch();
  const pack = object(await coreCommand("course_openmaic_package_projection", { body: { document_ids: [id] } }));
  if (pack.schema !== "archeaxis.openmaic-course-package-projection/v1" || pack.document_count !== 1
    || pack.renderer_executed !== false || pack.rendering_authorized !== false || pack.human_review_required !== true
    || !Array.isArray(pack.scenes) || pack.scenes.length !== 1) mismatch();
  const row = object(pack.scenes[0]);
  if (row.document_id !== id || row.status !== "recorded" || !Number.isSafeInteger(row.document_version) || (row.document_version as number) < 1)
    throw new Error("此文档没有可核对的当前场景报告；原文档未改变，可在资料页继续读取。");
  const doc = pinnedDocument(await coreCommand<DocumentDto>("document_version", { document_id: id, version: row.document_version }), id);
  const view = sceneView(doc, row);
  try {
    const source = pinnedDocument(await coreCommand<DocumentDto>("document_get", { document_id: view.source.document_id }), view.source.document_id);
    view.sourceStatus = sameValue(snapshot(source), view.source) ? "current" : "historical";
  } catch { view.sourceStatus = "unavailable"; }
  return view;
}

/** Ordinary Core Document holding a reading position, with CAS and exact readback.
 * No grades, mastery, provider authorization or automatic generation live here. */
export class ScenePosition {
  private document: DocumentDto | null = null;
  private pending: { editor: Record<string, unknown>; version: number } | null = null;
  private constructor(readonly scene: SavedScene, readonly workspaceId: string, readonly requestId: string, readonly documentId: string) {}
  static async open(scene: SavedScene, workspaceId: string): Promise<ScenePosition> {
    if (!bounded(workspaceId, 128)) mismatch();
    const hash = await sha256(new TextEncoder().encode(JSON.stringify([workspaceId, snapshot(scene.document)])));
    const request = `scene_position_${hash}`;
    return new ScenePosition(scene, workspaceId, request, await documentRequestIdentity(request));
  }
  private editor(step: number) {
    if (!Number.isSafeInteger(step) || step < 0 || step > Math.max(0, this.scene.steps.length - 1)) mismatch();
    return { type: "doc", content: [], attrs: { archeaxis_scene_position: { schema: "archeaxis.scene-position/v1",
      workspace_id: this.workspaceId, scene: snapshot(this.scene.document), step, learning_evidence: "NONE" } } };
  }
  async read(): Promise<number> {
    let d: DocumentDto;
    try { d = pinnedDocument(await coreCommand<DocumentDto>("document_get", { document_id: this.documentId }), this.documentId); }
    catch (error) { if (!this.pending && error instanceof ApiError && error.status === 404) { this.document = null; return 0; } throw error; }
    const position = object(object(object(d.editor_json).attrs).archeaxis_scene_position);
    const step = position.step;
    if (typeof step !== "number" || !sameValue(d.editor_json, this.editor(step))) mismatch();
    if (this.pending && (d.version !== this.pending.version + 1 || !sameValue(d.editor_json, this.pending.editor)))
      throw new Error("位置保存仍未确认；保留当前步骤，不覆盖其他版本。");
    this.document = d; this.pending = null; return step;
  }
  get unresolved() { return this.pending !== null; }
  async save(step: number): Promise<void> {
    if (this.pending) throw new Error("上次位置保存尚未确认；请先读取已保存位置。");
    const editor = this.editor(step), version = this.document?.version ?? 0;
    this.pending = { editor, version };
    const d = await coreCommand<DocumentDto>(version ? "document_draft" : "document_create", version
      ? { document_id: this.documentId, body: { expected_version: version, editor_json: editor } }
      : { body: { create_request_id: this.requestId, title: `课程阅读位置 · ${this.scene.title}`, editor_json: editor } });
    if (d.document_id !== this.documentId || d.version !== version + 1 || !sameValue(d.editor_json, editor)) mismatch();
    await this.read();
  }
}
