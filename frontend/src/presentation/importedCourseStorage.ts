import { coreCommand } from "../api/core";
import type { DocumentDto, OriginalDto } from "../api/generated/core-contract";
import { parseOpenMaicCourse, OPENMAIC_COMMIT, COURSE_IMPORT_MAX_BYTES } from "../adapters/openmaicCourse";
import { isOpenMaic13Manifest, OPENMAIC_13_ADAPTER, OPENMAIC_13_VERSION, parseOpenMaicCourseV2 } from "../adapters/openmaicCourseV2";
import { documentRequestIdentity } from "./documentRequestIdentity";
import { confirmedImport } from "./importReceipt";
import { object, pinnedDocument, sameValue, sha256 } from "./exchangeProof";
import { slideText, type AnyImportedCourse, type CourseImportDraft, type ImportedCourse, type ImportedCourseV2 } from "./importedCourse";

export type PreparedCourseImport = { bytes: Uint8Array; fileName: string; sha256: string;
  adapter: "openmaic-manifest/v1" | typeof OPENMAIC_13_ADAPTER;
  draft: CourseImportDraft; requestId: string; documentId: string };
export type StoredCourseImport = { document: DocumentDto; course: AnyImportedCourse };
export class CourseImportFailure extends Error {
  constructor(message: string, public originalConfirmed: boolean, public sourceId?: string) { super(message); }
}
export async function prepareCourseImport(selected: Uint8Array, fileName: string): Promise<PreparedCourseImport> {
  if (!fileName.trim() || fileName.length > 240 || /[\u0000-\u001f/\\]/.test(fileName)) throw new Error("文件名无效。");
  const bytes = selected.slice(), v2 = isOpenMaic13Manifest(bytes);
  const adapter = v2 ? OPENMAIC_13_ADAPTER : "openmaic-manifest/v1";
  const draft = v2 ? parseOpenMaicCourseV2(bytes) : parseOpenMaicCourse(bytes), hash = await sha256(bytes);
  // Stable across reselect/restart; never reuse a request identity for changed input or adapter version.
  const requestId = "course_import_" + await sha256(new TextEncoder().encode(JSON.stringify([adapter, hash, fileName])));
  return { bytes, fileName, sha256: hash, adapter, draft, requestId, documentId: await documentRequestIdentity(requestId) };
}
function candidate(draft: CourseImportDraft, provenance: ImportedCourse["provenance"] | ImportedCourseV2["provenance"]): AnyImportedCourse {
  const common = { ...draft, status: "candidate" as const, grounding: "external_unverified" as const, human_review_required: true as const };
  return provenance.adapter === "openmaic-manifest/v1"
    ? { ...common, schema: "archeaxis.imported-course/v1", provenance }
    : { ...common, schema: "archeaxis.imported-course/v2", provenance };
}
export function importedCourseEditor(course: AnyImportedCourse) {
  const lines = [course.title, "外部课程候选 · 参考答案未核验 · 不记录掌握", ...course.report];
  for (const scene of [...course.scenes].sort((a, b) => a.order - b.order)) {
    lines.push(scene.title);
    if (scene.slide) for (const element of scene.slide.elements) lines.push(slideText(element.content) || "（空文本）");
    for (const q of scene.questions) {
      lines.push(q.question);
      if (q.options?.length) lines.push(q.options.map(o => o.label).join("\n"));
      if (q.answer?.length) lines.push(`课件提供的参考答案：${q.answer.join("；")}`);
      if (q.analysis) lines.push(`课件解析：${q.analysis}`);
    }
  }
  const editor = { type: "doc", attrs: { archeaxis_imported_course: course },
    content: lines.map((text, i) => ({ type: "paragraph", attrs: { block_id: `course_${i}` }, content: [{ type: "text", text }] })) };
  if (lines.length > 5000 || new TextEncoder().encode(JSON.stringify(editor)).length > 1024 * 1024)
    throw new Error("课程文档超过 Core 5000 块或 1 MiB 限额；未写入或截断。");
  return editor;
}
async function originalBytes(id: string, hash: string, length: number): Promise<Uint8Array> {
  const original = await coreCommand<OriginalDto>("source_original", { source_id: id });
  if (original.source_id !== id || original.sha256 !== hash || typeof original.content_base64 !== "string"
    || original.content_base64.length > Math.ceil(COURSE_IMPORT_MAX_BYTES / 3) * 4) throw new Error("原件身份或长度无法核对。");
  const bytes = Uint8Array.from(atob(original.content_base64), c => c.charCodeAt(0));
  if (bytes.length !== length || await sha256(bytes) !== hash) throw new Error("原件实际字节与 SHA 不符。");
  return bytes;
}
function provenance(value: unknown): ImportedCourse["provenance"] | ImportedCourseV2["provenance"] {
  const p = object(value);
  if (!((p.adapter === "openmaic-manifest/v1" && p.upstream_commit === OPENMAIC_COMMIT)
      || (p.adapter === OPENMAIC_13_ADAPTER && p.adapter_upstream_version === OPENMAIC_13_VERSION))
    || typeof p.file_name !== "string" || !p.file_name.trim() || p.file_name.length > 240
    || /[\u0000-\u001f/\\]/.test(p.file_name) || typeof p.source_id !== "string" || !p.source_id.trim()
    || typeof p.sha256 !== "string" || !/^[a-f0-9]{64}$/.test(p.sha256)
    || !Number.isSafeInteger(p.byte_length) || (p.byte_length as number) < 1 || (p.byte_length as number) > COURSE_IMPORT_MAX_BYTES)
    throw new Error("候选原件身份无效。");
  const common = { file_name: p.file_name, source_id: p.source_id, sha256: p.sha256, byte_length: p.byte_length as number };
  return p.adapter === "openmaic-manifest/v1" ? { ...common, adapter: "openmaic-manifest/v1", upstream_commit: OPENMAIC_COMMIT }
    : { ...common, adapter: OPENMAIC_13_ADAPTER, adapter_upstream_version: OPENMAIC_13_VERSION };
}
/** Explicitly preserve an unsupported manifest as a source, without creating a course. */
export async function preserveCourseOriginal(selected: Uint8Array, fileName: string): Promise<{ sourceId: string; sha256: string }> {
  if (!fileName.trim() || fileName.length > 240 || /[\u0000-\u001f/\\]/.test(fileName)) throw new Error("文件名无效。");
  if (!selected.length || selected.length > COURSE_IMPORT_MAX_BYTES) throw new Error("原件超过 256 KiB 或为空；未截断或保存。");
  const bytes = selected.slice(), hash = await sha256(bytes);
  const receipt = confirmedImport(await coreCommand("source_import", { body: { name: fileName,
    content_base64: btoa(Array.from(bytes, b => String.fromCharCode(b)).join("")) } }), hash);
  const readback = await originalBytes(receipt.source_id, hash, bytes.length);
  if (!readback.every((byte, index) => byte === bytes[index])) throw new Error("原件读回与选择的字节不一致；保全结果待核对。");
  return { sourceId: receipt.source_id, sha256: hash };
}
export async function saveCourseImport(prepared: PreparedCourseImport,
  checkpoint?: (phase: "original_confirmed" | "document_submitted") => void): Promise<StoredCourseImport> {
  // Validate the frozen payload before even the custody write, including a caller-mutated preview.
  if (await sha256(prepared.bytes) !== prepared.sha256) throw new Error("冻结的导入请求已变化；请重新选择文件。");
  const checked = await prepareCourseImport(prepared.bytes, prepared.fileName);
  if (!sameValue(checked, prepared)) throw new Error("冻结的导入请求已变化；请重新选择文件。");
  let sourceId: string | undefined, originalConfirmed = false, submitted = false;
  try {
    const receipt = confirmedImport(await coreCommand("source_import", { body: { name: prepared.fileName,
      content_base64: btoa(Array.from(prepared.bytes, b => String.fromCharCode(b)).join("")) } }), prepared.sha256);
    sourceId = receipt.source_id;
    const raw = await originalBytes(sourceId, prepared.sha256, prepared.bytes.length);
    if (!raw.every((b, i) => b === prepared.bytes[i])) throw new Error("原件与冻结字节不同。");
    originalConfirmed = true; checkpoint?.("original_confirmed");
    const shared = { file_name: prepared.fileName, source_id: sourceId, sha256: prepared.sha256, byte_length: prepared.bytes.length };
    const course = candidate(prepared.draft, prepared.adapter === "openmaic-manifest/v1"
      ? { ...shared, adapter: "openmaic-manifest/v1", upstream_commit: OPENMAIC_COMMIT }
      : { ...shared, adapter: OPENMAIC_13_ADAPTER, adapter_upstream_version: OPENMAIC_13_VERSION });
    const editor = importedCourseEditor(course);
    submitted = true; checkpoint?.("document_submitted");
    const created = pinnedDocument(await coreCommand<DocumentDto>("document_create", { body: { create_request_id: prepared.requestId,
      source_id: sourceId, source_revision: prepared.sha256, title: `外部课程候选 · ${course.title}`, editor_json: editor } }), prepared.documentId);
    if (created.version !== 1 || created.source_id !== sourceId || created.source_revision !== prepared.sha256
      || created.title !== `外部课程候选 · ${course.title}` || !sameValue(created.editor_json, editor)) throw new Error("创建回执不一致。");
    const saved = pinnedDocument(await coreCommand<DocumentDto>("document_get", { document_id: created.document_id }), created.document_id);
    if (!sameValue(created, saved)) throw new Error("创建与读回不一致。");
    return { document: saved, course };
  } catch {
    throw new CourseImportFailure(submitted ? "原件已保全；课程保存结果待核对。请保留原请求，重新核对或同请求重试。"
      : originalConfirmed ? "原件已保全；课程尚未保存。请保留原请求。"
      : "原件保全结果尚未确认；未提交课程文档。请保留文件并重新核对。", originalConfirmed, sourceId);
  }
}
export async function reopenCourseImport(id: string): Promise<StoredCourseImport> {
  const document = pinnedDocument(await coreCommand<DocumentDto>("document_get", { document_id: id }), id);
  const editor = object(document.editor_json), attrs = object(editor.attrs), stored = object(attrs.archeaxis_imported_course);
  const origin = provenance(stored.provenance);
  if (document.source_id !== origin.source_id || document.source_revision !== origin.sha256) throw new Error("文档来源与课程原件不匹配。");
  const raw = await originalBytes(origin.source_id, origin.sha256, origin.byte_length);
  // The stored schema/adapter selects its original reader, even if a legacy v1
  // document's input happened to declare appVersion 1.3.0.
  const course = candidate(origin.adapter === "openmaic-manifest/v1" ? parseOpenMaicCourse(raw) : parseOpenMaicCourseV2(raw), origin);
  if (!sameValue(stored, course) || !sameValue(editor, importedCourseEditor(course))
    || document.title !== `外部课程候选 · ${course.title}`) throw new Error("课程候选与原件不一致，未展示或替换内容。原件仍保全。");
  return { document, course };
}
