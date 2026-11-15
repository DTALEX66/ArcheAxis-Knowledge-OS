import type { JSONContent } from "@tiptap/core";
import { coreCommand } from "../api/core";
import { ApiError } from "../api/client";
import type { DocumentDto, OriginalDto, SourceDto } from "../api/generated/core-contract";
import type { PendingOriginal, WorkingState } from "./coreWorkingState";
import { documentRequestIdentity } from "./documentRequestIdentity";
import { object, sameValue, sha256 } from "./exchangeProof";
import { OriginalNoteRefused, type OriginalNoteAttempt } from "./originalNoteWrite";

export const CANVAS_ORIGINAL_LIMIT = 8 * 1024 * 1024;
export const CANVAS_EDITOR_LIMIT = 262_144;
const namespace = "archeaxis.canvas-document/v1";
const encodedSize = (value: unknown) => new TextEncoder().encode(JSON.stringify(value)).length;
function refuse(message: string): never { throw new Error(message); }
export type CanvasNode = Record<string, unknown> & { id: string; type: "text"|"file"|"link"|"group"; x: number; y: number; width: number; height: number };
export type CanvasEdge = Record<string, unknown> & { id: string; fromNode: string; toNode: string };
export type CanvasSource = { raw: Record<string, unknown>; nodes: CanvasNode[]; edges: CanvasEdge[] };
export function isCanvasSource(source: SourceDto | null) { return Boolean(source && /\.canvas$/i.test(source.original_name)); }
/** Guard before base64 allocation in shared source readers; other formats retain their limits. */
export function assertCanvasOriginalSize(source: SourceDto, original: OriginalDto, decoded?: Uint8Array): void {
  if (!isCanvasSource(source)) return;
  if (typeof original.content_base64 !== "string" || original.content_base64.length > 4 * Math.ceil(CANVAS_ORIGINAL_LIMIT / 3) || (decoded && decoded.length > CANVAS_ORIGINAL_LIMIT)) refuse("画布原件超过 8 MiB；原件保留，未呈现超限内容。");
}
export function isCanvasEditor(editor: unknown): boolean {
  if (!editor || typeof editor !== "object") return false;
  const attrs = (editor as JSONContent).attrs;
  return Boolean(attrs && Object.hasOwn(attrs, "archeaxis_canvas_document"));
}
function string(value: unknown, label: string): string {
  if (typeof value !== "string") refuse(`${label}不是文字；原件仍保留。`);
  return value as string;
}
function choice(row: Record<string, unknown>, key: string, values: string[]) {
  if (Object.hasOwn(row, key) && !values.includes(row[key] as string)) refuse(`画布 ${key} 声明不受支持。`);
}
function color(row: Record<string, unknown>) {
  if (Object.hasOwn(row, "color") && (typeof row.color !== "string" || !/^([1-6]|#[a-fA-F0-9]{6})$/.test(row.color))) refuse("画布颜色声明无效。");
}
/** Validate the supported Core export shape; unknown fields stay in immutable source bytes. */
export function parseCanvas(bytes: Uint8Array): CanvasSource {
  if (bytes.length > CANVAS_ORIGINAL_LIMIT) refuse("画布原件超过 8 MiB；原件保留，暂不建立编辑映射。");
  const raw = object(JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes)));
  const nodes = raw.nodes === undefined ? [] : raw.nodes, edges = raw.edges === undefined ? [] : raw.edges;
  if (!Array.isArray(nodes) || !Array.isArray(edges) || nodes.length > 5000 || edges.length > 10000) refuse("画布节点或连线数量／格式超出范围。");
  const ids = new Set<string>();
  for (const value of nodes as unknown[]) {
    const node = object(value), id = string(node.id, "节点编号");
    if (!id || ids.has(id)) refuse("画布节点编号为空或重复。"); ids.add(id);
    for (const key of ["x", "y", "width", "height"]) {
      if (!Number.isSafeInteger(node[key]) || (["width", "height"].includes(key) && (node[key] as number) < 1)) refuse("画布几何无法准确呈现；未改写原值。");
    }
    if (!Number.isSafeInteger((node.x as number) + (node.width as number)) || !Number.isSafeInteger((node.y as number) + (node.height as number))) refuse("画布范围超过可准确呈现的数值范围。");
    color(node);
    if (node.type === "text") string(node.text, "节点文字");
    else if (node.type === "file") { string(node.file, "文件声明"); if (node.subpath !== undefined && !string(node.subpath, "文件位置").startsWith("#")) refuse("文件位置声明无效。"); }
    else if (node.type === "link") string(node.url, "链接声明");
    else if (node.type === "group") { for (const key of ["label", "background"]) if (node[key] !== undefined) string(node[key], "分组声明"); choice(node, "backgroundStyle", ["cover", "ratio", "repeat"]); }
    else refuse("画布包含未知节点类型；未跳过内容并宣称成功。");
  }
  const edgeIds = new Set<string>();
  for (const value of edges as unknown[]) {
    const edge = object(value), id = string(edge.id, "连线编号");
    if (!id || edgeIds.has(id) || !ids.has(string(edge.fromNode, "起点")) || !ids.has(string(edge.toNode, "终点"))) refuse("画布连线编号或端点无法核对。");
    edgeIds.add(id); color(edge);
    for (const key of ["fromSide", "toSide"]) choice(edge, key, ["top", "right", "bottom", "left"]);
    for (const key of ["fromEnd", "toEnd"]) choice(edge, key, ["none", "arrow"]);
    if (edge.label !== undefined) string(edge.label, "连线说明");
  }
  return { raw, nodes: nodes as CanvasNode[], edges: edges as CanvasEdge[] };
}
export async function verifiedCanvas(source: SourceDto, original: OriginalDto, provided?: Uint8Array): Promise<CanvasSource> {
  if (!isCanvasSource(source) || source.source_revision !== source.sha256 || original.source_id !== source.source_id || original.sha256 !== source.sha256 || original.name !== source.original_name || !/^[a-f0-9]{64}$/.test(source.sha256)) refuse("画布原件身份与所选来源不一致。");
  assertCanvasOriginalSize(source, original);
  const bytes = provided ?? Uint8Array.from(atob(original.content_base64), char => char.charCodeAt(0));
  assertCanvasOriginalSize(source, original, bytes);
  if (bytes.length > CANVAS_ORIGINAL_LIMIT || await sha256(bytes) !== source.sha256) refuse("画布原件字节或大小无法核对。");
  return parseCanvas(bytes);
}
export function assertCanvasBudget(editor: unknown, state?: WorkingState, pending?: PendingOriginal, draft?: { id: string; baseVersion: number }) {
  if (encodedSize(editor) > CANVAS_EDITOR_LIMIT) refuse("画布编辑内容超过 256 KiB 工作草稿上限；原件保留，未截断内容或发送保存。");
  if (state) {
    const next = structuredClone(state);
    if (pending) next.pending_original = pending;
    if (draft) next.drafts[draft.id] = { base_version: draft.baseVersion, editor_json: editor as PendingOriginal["editor_json"] };
    if (encodedSize(next) > 1_048_576) refuse("工作草稿总量超过 1 MiB；请先处理已有草稿，原件与本次内容仍保留。");
  }
}
function marker(source: Pick<SourceDto, "source_id"|"source_revision">) {
  return { schema: namespace, source_id: source.source_id, source_revision: source.source_revision, scope: "TEXT_NODE_PLAIN_TEXT_ONLY" };
}
function blockText(node: JSONContent): string {
  if (!["paragraph", "codeBlock"].includes(node.type ?? "") || (node.content !== undefined && !Array.isArray(node.content))) refuse("画布文本映射已改变；普通文档仍可保存，暂不能重建画布。");
  return (node.content ?? []).map(child => child.type === "hardBreak" ? "\n" : child.type === "text" ? string(child.text, "映射文字") : refuse("映射包含非文字内容；未回填原文。")).join("");
}
export function mappedCanvasTexts(canvas: CanvasSource, source: Pick<SourceDto, "source_id"|"source_revision">, document: Pick<DocumentDto, "editor_json"|"source_id"|"source_revision">): Map<string, string> {
  if (document.source_id !== source.source_id || document.source_revision !== source.source_revision) refuse("文档未绑定此固定画布原件。");
  const editor = object(document.editor_json);
  if (editor.type !== "doc" || !Array.isArray(editor.content)) refuse("画布文档正文无法核对。");
  if (isCanvasEditor(editor) && !sameValue(object(editor.attrs).archeaxis_canvas_document, marker(source))) refuse("画布映射版本或来源声明无法核对。");
  const expected = new Set(canvas.nodes.filter(n => n.type === "text").map(n => n.id)), texts = new Map<string, string>(), blocks = new Set<string>();
  for (const input of editor.content) {
    const node = object(input) as JSONContent, attrs = object(node.attrs);
    const id = string(attrs.canvas_node_id, "画布映射编号"), block = string(attrs.block_id, "正文块编号");
    if (!expected.has(id) || texts.has(id) || !block || new TextEncoder().encode(block).length > 128 || blocks.has(block)) refuse("画布文本映射缺失、重复或指向其他节点；普通文档保存不受此限制。");
    blocks.add(block); texts.set(id, blockText(node));
  }
  if (texts.size !== expected.size) refuse("画布原文本节点没有完整映射；未使用旧文本补齐。");
  return texts;
}
export async function prepareCanvasDocument(source: SourceDto, original: OriginalDto, bytes: Uint8Array): Promise<OriginalNoteAttempt> {
  const canvas = await verifiedCanvas(source, original, bytes), request = `canvas_${crypto.randomUUID()}`;
  const editor: PendingOriginal["editor_json"] = { type: "doc", attrs: { archeaxis_canvas_document: marker(source) }, content: canvas.nodes.filter(n => n.type === "text").map(node => ({ type: "paragraph", attrs: { block_id: crypto.randomUUID(), canvas_node_id: node.id }, content: node.text ? [{ type: "text", text: node.text as string }] : [] })) };
  assertCanvasBudget(editor);
  if (new TextEncoder().encode(source.original_name).length > 1024) refuse("画布标题超过保存范围；原件仍保留。");
  return { id: await documentRequestIdentity(request), body: { create_request_id: request, title: source.original_name, source_id: source.source_id, source_revision: source.source_revision, editor_json: editor } };
}
export async function confirmCanvasDocument(attempt: OriginalNoteAttempt, readOnly: boolean, onDispatch?: () => void): Promise<DocumentDto> {
  if (await documentRequestIdentity(attempt.body.create_request_id) !== attempt.id || !attempt.body.source_id || !attempt.body.source_revision || !isCanvasEditor(attempt.body.editor_json)) refuse("冻结画布创建请求身份不完整。");
  assertCanvasBudget(attempt.body.editor_json);
  const source = await coreCommand<SourceDto>("source_get", { source_id: attempt.body.source_id });
  if (source.source_id !== attempt.body.source_id || source.source_revision !== attempt.body.source_revision || source.original_name !== attempt.body.title) refuse("恢复的画布请求与原件身份不一致。");
  const canvas = await verifiedCanvas(source, await coreCommand<OriginalDto>("source_original", { source_id: source.source_id }));
  const texts = mappedCanvasTexts(canvas, source, { ...attempt.body, source_id: source.source_id, source_revision: source.source_revision });
  if (canvas.nodes.some(n => n.type === "text" && texts.get(n.id) !== n.text)) refuse("冻结创建请求不再对应原画布文字；未重新创建。");
  const validate = (saved: DocumentDto) => {
    const content = attempt.body.editor_json.content!;
    if (saved.document_id !== attempt.id || saved.version !== 1 || saved.title !== attempt.body.title || saved.source_id !== source.source_id || saved.source_revision !== source.source_revision || !/^[a-f0-9]{64}$/.test(saved.content_sha256) || !sameValue(saved.editor_json, attempt.body.editor_json) || saved.blocks?.length !== content.length || saved.text_projection !== content.map(blockText).filter(Boolean).join("\n")) refuse("画布保存身份或完整正文读回不一致；冻结请求仍保留。");
    content.forEach((node, i) => { const block = saved.blocks[i]; if (block.block_id !== node.attrs!.block_id || block.ordinal !== i || block.kind !== node.type || block.text_projection !== blockText(node) || !sameValue(block.node_json, node)) refuse("画布正文块身份读回不一致；冻结请求仍保留。"); });
  };
  let ack: DocumentDto | undefined;
  if (!readOnly) {
    try { onDispatch?.(); ack = await coreCommand<DocumentDto>("document_create", { body: structuredClone(attempt.body) }); }
    catch (error) { if (error instanceof ApiError && [400, 401, 403, 422].includes(error.status)) throw new OriginalNoteRefused("画布创建被明确拒绝。"); throw error; }
    validate(ack);
  }
  const saved = await coreCommand<DocumentDto>("document_version", { document_id: attempt.id, version: 1 });
  validate(saved);
  if (ack && ack.content_sha256 !== saved.content_sha256) refuse("画布创建回执与读回指纹不同；请求仍保留。");
  return saved;
}
export async function verifyCanvasExport(saved: DocumentDto, input: unknown): Promise<void> {
  const proof = object(input);
  if (proof.document_id !== saved.document_id || proof.version !== saved.version || proof.format !== "canvas" || proof.source_revision !== saved.source_revision || !saved.source_revision || !Array.isArray(proof.files) || proof.files.length !== 2) refuse("画布导出不是所选已保存版本。");
  const files = proof.files.map(object);
  if (files.filter(f => f.path === "document.canvas").length !== 1 || files.filter(f => f.path === "manifest.json").length !== 1 || files.some(f => f.media_type !== "application/json" || typeof f.content !== "string" || new TextEncoder().encode(f.content).length > 24 * 1024 * 1024)) refuse("画布导出文件或格式无法核对。");
  const canvas = files.find(f => f.path === "document.canvas")!, manifest = object(JSON.parse(files.find(f => f.path === "manifest.json")!.content as string));
  if (manifest.schema !== "archeaxis-canvas-export/v1" || manifest.reconstruction_scope !== "TEXT_NODE_PLAIN_TEXT_ONLY" || !sameValue(manifest.document, saved) || !Array.isArray(manifest.loss) || !["json_serialization", "text_node_plain_projection", "references_only"].every(code => (manifest.loss as unknown[]).some(v => { const loss = object(v); return loss.code === code && typeof loss.message === "string" && loss.message.length > 0; }))) refuse("画布导出快照或内容损失说明不完整。");
  if (await sha256(new TextEncoder().encode(canvas.content as string)) !== manifest.canvas_sha256) refuse("画布导出内容指纹不符。");
}
