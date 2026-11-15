import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { createHash, webcrypto } from "node:crypto";
import type { Editor, JSONContent } from "@tiptap/core";
import type { DocumentDto, OriginalDto, SourceDto } from "../api/generated/core-contract";
import { CanvasDocumentPanel } from "../components/CanvasDocumentPanel";
import { CanonicalLibrarySpace } from "../spaces/CanonicalLibrarySpace";
import { decodeEditorContent } from "../components/DocumentEditor";
import { CoreWorkingStateProvider } from "../presentation/useCoreWorkingState";
import { CoreWorkingStateSession, type WorkingRead, type WorkingState, type WorkingTransport } from "../presentation/coreWorkingState";
import { assertCanvasBudget, assertCanvasOriginalSize, CANVAS_ORIGINAL_LIMIT, confirmCanvasDocument, mappedCanvasTexts, parseCanvas, prepareCanvasDocument, verifiedCanvas, verifyCanvasExport } from "../presentation/canvasDocument";
import type { OriginalNoteAttempt } from "../presentation/originalNoteWrite";

const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));
vi.mock("../components/CheckPanel", () => ({ CheckPanel: () => null }));
vi.mock("../components/BackupPanel", () => ({ BackupPanel: () => null }));
vi.mock("../components/JobContent", () => ({ JobContent: () => null }));
vi.mock("../components/DocumentBacklinks", () => ({ DocumentBacklinks: () => null }));
vi.mock("../templates/TemplateWorkspace", () => ({ TemplateLauncher: () => null }));
const digest = (value: unknown) => createHash("sha256").update(JSON.stringify(value)).digest("hex");
function fixture() {
  const raw = { "plugin:root": { keep: [true, "扩展"] }, nodes: [
    { id: "t1", type: "text", x: -10, y: 0, width: 200, height: 100, text: "中文🙂\n第二行", "plugin:node": { opaque: 3 } },
    { id: "g", type: "group", x: 0, y: 0, width: 500, height: 400, label: "分组", background: "file:///private/image.png" },
    { id: "empty", type: "text", x: 220, y: 0, width: 200, height: 100, text: "" },
    { id: "f", type: "file", x: 0, y: 150, width: 100, height: 40, file: "../../private.pdf", subpath: "#^block" },
    { id: "l", type: "link", x: 150, y: 150, width: 100, height: 40, url: "javascript:window.SHOULD_NOT_RUN=true" },
  ], edges: [{ id: "e", fromNode: "t1", toNode: "f", toEnd: "arrow", label: "引用", "plugin:edge": [1, 2] }] };
  const bytes = new TextEncoder().encode(JSON.stringify(raw)), hash = createHash("sha256").update(bytes).digest("hex");
  const source: SourceDto = { source_id: "src_canvas", source_revision: hash, sha256: hash, original_name: "固定.canvas", imported_at: "2026-11-12" };
  const original: OriginalDto = { source_id: source.source_id, name: source.original_name, sha256: hash, media_type: "application/octet-stream", content_base64: Buffer.from(bytes).toString("base64") };
  return { raw, bytes, source, original };
}
function ack(attempt: OriginalNoteAttempt, version = 1): DocumentDto {
  const editor = structuredClone(attempt.body.editor_json), nodes = editor.content!;
  const text = (node: JSONContent) => (node.content ?? []).map(n => n.type === "hardBreak" ? "\n" : n.text ?? "").join("");
  return { document_id: attempt.id, version, title: attempt.body.title, source_id: attempt.body.source_id!, source_revision: attempt.body.source_revision!, editor_json: editor, content_sha256: digest(editor), text_projection: nodes.map(text).filter(Boolean).join("\n"), blocks: nodes.map((node, ordinal) => ({ block_id: node.attrs!.block_id, kind: node.type!, ordinal, node_json: node, text_projection: text(node), codec_status: "known" })) };
}
function exportProof(saved: DocumentDto, raw: ReturnType<typeof fixture>["raw"]) {
  const mapped = mappedCanvasTexts(parseCanvas(new TextEncoder().encode(JSON.stringify(raw))), { source_id: saved.source_id!, source_revision: saved.source_revision! }, saved);
  const rebuilt = structuredClone(raw);
  rebuilt.nodes.forEach(node => { if (node.type === "text") node.text = mapped.get(node.id)!; });
  const content = JSON.stringify(rebuilt), manifest = { schema: "archeaxis-canvas-export/v1", document: saved, canvas_sha256: createHash("sha256").update(content).digest("hex"), reconstruction_scope: "TEXT_NODE_PLAIN_TEXT_ONLY", loss: ["json_serialization", "text_node_plain_projection", "references_only"].map(code => ({ code, message: code })) };
  return { document_id: saved.document_id, version: saved.version, format: "canvas", source_revision: saved.source_revision, files: [{ path: "document.canvas", media_type: "application/json", content }, { path: "manifest.json", media_type: "application/json", content: JSON.stringify(manifest) }] };
}
let previousScroll: typeof HTMLElement.prototype.scrollIntoView;
beforeEach(() => { bridge.call.mockReset(); vi.stubGlobal("crypto", webcrypto); vi.stubGlobal("__TAURI__", { core: { invoke: vi.fn() } }); previousScroll=HTMLElement.prototype.scrollIntoView;HTMLElement.prototype.scrollIntoView=vi.fn(); });
afterEach(() => { vi.restoreAllMocks();vi.unstubAllGlobals();HTMLElement.prototype.scrollIntoView=previousScroll; });

it("maps every text node including empty text without copying or mutating opaque original fields", async () => {
  const f = fixture(), original = structuredClone(f.raw), attempt = await prepareCanvasDocument(f.source, f.original, f.bytes);
  expect(attempt.body.editor_json.content!.map(n => n.attrs?.canvas_node_id)).toEqual(["t1", "empty"]);
  expect(new Set(attempt.body.editor_json.content!.map(n => n.attrs?.block_id)).size).toBe(2);
  expect(mappedCanvasTexts(parseCanvas(f.bytes), f.source, ack(attempt))).toEqual(new Map([["t1", "中文🙂\n第二行"], ["empty", ""]]));
  expect(f.raw).toEqual(original); expect(attempt.body.editor_json).not.toHaveProperty("nodes");
  expect(bridge.call).not.toHaveBeenCalled();
});
it("refuses source substitution and the independent original, editor and whole-journal budgets before writes", async () => {
  const f = fixture();
  await expect(verifiedCanvas({ ...f.source, source_revision: "f".repeat(64) }, f.original)).rejects.toThrow("身份");
  await expect(verifiedCanvas(f.source, { ...f.original, content_base64: "A".repeat(4 * Math.ceil(CANVAS_ORIGINAL_LIMIT / 3) + 4) })).rejects.toThrow("8 MiB");
  expect(() => parseCanvas(new Uint8Array(CANVAS_ORIGINAL_LIMIT + 1))).toThrow("8 MiB");
  expect(() => assertCanvasOriginalSize(f.source,f.original,new Uint8Array(CANVAS_ORIGINAL_LIMIT+1))).toThrow("8 MiB");
  expect(() => assertCanvasOriginalSize({...f.source,original_name:"large.txt"},f.original,new Uint8Array(CANVAS_ORIGINAL_LIMIT+1))).not.toThrow();
  expect(() => assertCanvasBudget({ content: "中".repeat(100000) })).toThrow("256 KiB");
  const state: WorkingState = { drafts: {}, opened_documents: [], active_document: null, page_id: "03", pending_original: null };
  for (let i = 0; i < 5; i++) state.drafts[`doc${i}`] = { base_version: 1, editor_json: { type: "doc", content: [{ type: "text", text: "x".repeat(220000) }] } };
  expect(() => assertCanvasBudget({ type: "doc", content: [] }, state)).toThrow("1 MiB");
  expect(bridge.call).not.toHaveBeenCalled();
});
it.each(["duplicate-node", "unknown-type", "missing-endpoint", "duplicate-edge", "unsafe-geometry"])("refuses %s without dropping source declarations", kind => {
  const f = fixture();
  if (kind === "duplicate-node") f.raw.nodes[1].id = "t1";
  if (kind === "unknown-type") f.raw.nodes[1].type = "interactive";
  if (kind === "missing-endpoint") f.raw.edges[0].toNode = "absent";
  if (kind === "duplicate-edge") f.raw.edges.push(structuredClone(f.raw.edges[0]));
  if (kind === "unsafe-geometry") f.raw.nodes[0].x = Number.MAX_SAFE_INTEGER + 1;
  expect(() => parseCanvas(new TextEncoder().encode(JSON.stringify(f.raw)))).toThrow();
});
it("renders references and markup as inert text with no external fetch or editing controls", async () => {
  const f = fixture(), fetch = vi.fn(); vi.stubGlobal("fetch", fetch);
  render(<CanvasDocumentPanel source={f.source} original={f.original} bytes={f.bytes}/>);
  await screen.findByText(/javascript:window.SHOULD_NOT_RUN/);
  expect(screen.getByText(/\.\.\/\.\.\/private.pdf/)).toBeInTheDocument();
  expect(document.querySelector("iframe,img,a,script[src],textarea,input")).toBeNull();
  expect(screen.queryByRole("button")).not.toBeInTheDocument(); expect(fetch).not.toHaveBeenCalled(); expect(bridge.call).not.toHaveBeenCalled();
});
it("leaves empty Canvas without invented text nodes and refuses edited mappings without reverting old text", async () => {
  const f = fixture(), attempt = await prepareCanvasDocument(f.source, f.original, f.bytes), saved = ack(attempt);
  (saved.editor_json as JSONContent).content!.pop();
  expect(() => mappedCanvasTexts(parseCanvas(f.bytes), f.source, saved)).toThrow("完整映射");
  expect(parseCanvas(new TextEncoder().encode("{}"))).toEqual({ raw: {}, nodes: [], edges: [] });
  expect(f.raw.nodes[0].text).toBe("中文🙂\n第二行");
});
it("recovers a lost create ACK by fixed V1 readback and rejects a mismatched block identity", async () => {
  const f = fixture(), attempt = await prepareCanvasDocument(f.source, f.original, f.bytes); let saved = ack(attempt);
  bridge.call.mockImplementation(async op => { if (op === "source_get") return f.source; if (op === "source_original") return f.original; if (op === "document_create") throw new Error("ACK lost"); if (op === "document_version") return structuredClone(saved); throw new Error(op); });
  await expect(confirmCanvasDocument(attempt, false)).rejects.toThrow("ACK lost");
  expect(await confirmCanvasDocument(structuredClone(attempt), true)).toEqual(saved);
  expect(bridge.call.mock.calls.filter(([op]) => op === "document_create")).toHaveLength(1);
  saved = structuredClone(saved); saved.blocks[0].block_id = "other";
  await expect(confirmCanvasDocument(attempt, true)).rejects.toThrow("块身份");
  expect(bridge.call).toHaveBeenLastCalledWith("document_version", { document_id: attempt.id, version: 1 });
});
it("verifies fixed export files, actual string hash, selected snapshot and loss scope", async () => {
  const f = fixture(), saved = ack(await prepareCanvasDocument(f.source, f.original, f.bytes)), proof = exportProof(saved, f.raw);
  await expect(verifyCanvasExport(saved, proof)).resolves.toBeUndefined();
  for (const mutate of [
    (p: typeof proof) => { p.files[0].path = "../escape.canvas"; },
    (p: typeof proof) => { p.files[0].content += " "; },
    (p: typeof proof) => { p.version++; },
    (p: typeof proof) => { const m = JSON.parse(p.files[1].content); m.document.content_sha256 = "0".repeat(64); p.files[1].content = JSON.stringify(m); },
    (p: typeof proof) => { const m = JSON.parse(p.files[1].content); m.loss = []; p.files[1].content = JSON.stringify(m); },
  ]) { const changed = structuredClone(proof); mutate(changed); await expect(verifyCanvasExport(saved, changed)).rejects.toThrow(); }
});

// Real Library, editor and working-state session with a mock Core transport.
// This does not claim installed-host, real CAS or external application acceptance.
function productFixture() {
  const f = fixture(), records = new Map<string, DocumentDto>(), versions = new Map<string, DocumentDto>();
  let lostAck = false;
  let delayed:{entered:()=>void;wait:Promise<void>}|null=null;
  let server: WorkingRead = { schema: "archeaxis.ui-working-state/v1", workspace_id: "a".repeat(32), restore_epoch: "initial", state_revision: 0, state: { drafts: {}, opened_documents: [], active_document: null, page_id: null, pending_original: null }, draft_digests: {}, pending_document_id: null, recovery_candidates: null, recovery_requires_confirmation: false };
  const publish = (state: WorkingState) => { server = { ...server, state: structuredClone(state), state_revision: server.state_revision + 1, draft_digests: Object.fromEntries(Object.entries(state.drafts).map(([id, draft]) => [id, digest(draft.editor_json)])) }; return structuredClone(server); };
  const transport: WorkingTransport = {
    read: async () => structuredClone(server), write: async request => {const pause=delayed;delayed=null;if(pause){pause.entered();await pause.wait;}return publish(request.state);},
    clearSaved: async request => { const pending = server.state.drafts[request.document_id], saved = records.get(request.document_id)!; expect(pending.base_version + 1).toBe(request.saved_version); expect(saved.editor_json).toEqual(pending.editor_json); const state = structuredClone(server.state); delete state.drafts[request.document_id]; return publish(state); },
    recover: async () => { throw new Error("No restore candidate"); },
  };
  bridge.call.mockImplementation(async (op: string, p: Record<string, any> = {}) => {
    if (op === "sources_list") return { sources: [f.source] };
    if (op === "source_get") return f.source;
    if (op === "source_original") return f.original;
    if (op === "anchors_list") return { anchors: [] };
    if (op === "documents_list") return { documents: [...records.values()], next_cursor: null, snapshot_count: records.size };
    if (op === "document_get") return structuredClone(records.get(p.document_id));
    if (op === "document_version") return structuredClone(versions.get(`${p.document_id}:${p.version}`));
    if (op === "document_create") {
      expect(server.state.pending_original).toEqual(p.body);
      const id = `doc_req_${createHash("sha256").update(p.body.create_request_id).digest("hex")}`;
      const saved = ack({ id, body: p.body }); records.set(id, saved); versions.set(`${id}:1`, saved);
      if (lostAck) { lostAck = false; throw new Error("ACK lost"); } return structuredClone(saved);
    }
    if (op === "document_draft") {
      const before = records.get(p.document_id)!; expect(p.body.expected_version).toBe(before.version); expect(server.state.drafts[p.document_id].editor_json).toEqual(p.body.editor_json);
      const saved = ack({ id: before.document_id, body: { create_request_id: "unused", title: before.title, source_id: before.source_id!, source_revision: before.source_revision!, editor_json: p.body.editor_json } }, before.version + 1);
      records.set(saved.document_id, saved); versions.set(`${saved.document_id}:${saved.version}`, saved); return structuredClone(saved);
    }
    if (op === "document_export") return exportProof(records.get(p.document_id)!, f.raw);
    if (op === "document_export_save") { const saved = records.get(p.document_id)!; expect(p.expected_version).toBe(saved.version); expect(p.expected_content_sha256).toBe(saved.content_sha256); return { document_id: saved.document_id, version: saved.version, directory: "exports/canvas", format: "canvas", files: ["document.canvas", "manifest.json"] }; }
    if (op === "capabilities_list") return {};
    throw new Error(`Unexpected ${op}`);
  });
  return { ...f, records, session: () => new CoreWorkingStateSession(transport), loseAck: () => { lostAck = true; },
    delayNextJournal:()=>{let entered!:()=>void,release!:()=>void;const began=new Promise<void>(resolve=>{entered=resolve;});const wait=new Promise<void>(resolve=>{release=resolve;});delayed={entered,wait};return {entered:began,release};},
    otherSession:()=>{const other={...structuredClone(server),workspace_id:"b".repeat(32),restore_epoch:"c".repeat(32)};return new CoreWorkingStateSession({...transport,read:async()=>structuredClone(other)});},
  };
}
function mount(session: CoreWorkingStateSession) { return render(<CoreWorkingStateProvider session={session}><CanonicalLibrarySpace purpose="reader" initialSourceTarget={{ source_id: "src_canvas", source_revision: fixture().source.sha256, sha256: fixture().source.sha256 }}/></CoreWorkingStateProvider>); }
it("SIMULATED: the formal reader creates, edits, exports and reopens a mapped Canvas with exact snapshot fences", async () => {
  const f = productFixture(), session = f.session(); await session.load(); const view = mount(session);
  fireEvent.click(await screen.findByRole("button", { name: "创建可编辑草稿" }));
  const box = await screen.findByRole("textbox", { name: "文档草稿" });
  const saved = [...f.records.values()][0], edited = structuredClone(saved.editor_json) as JSONContent;
  edited.content![0].content = [{ type: "text", text: "编辑后中文🙂" }];
  act(() => { (box as HTMLElement & { editor: Editor }).editor.commands.setContent(decodeEditorContent(edited), { emitUpdate: true }); });
  fireEvent.click(screen.getByRole("button", { name: "保存草稿" }));
  await waitFor(() => expect(f.records.get(saved.document_id)?.version).toBe(2));
  await waitFor(() => expect(session.getSnapshot().state.drafts[saved.document_id]).toBeUndefined());
  fireEvent.click(screen.getByRole("button", { name: "属性与引用" }));
  fireEvent.click(screen.getByText("导出已保存文档", { selector: "summary" }));
  fireEvent.click(screen.getByRole("button", { name: "Canvas 已保存版导出到产品资料目录" }));
  await waitFor(() => expect(bridge.call).toHaveBeenCalledWith("document_export_save", { document_id: saved.document_id, format: "canvas", expected_version: 2, expected_content_sha256: f.records.get(saved.document_id)!.content_sha256 }));
  view.unmount(); const next = f.session(); await next.load(); mount(next);
  expect(await screen.findByRole("textbox", { name: "文档草稿" })).toHaveTextContent("编辑后中文🙂");
  expect(f.raw.nodes[0].text).toBe("中文🙂\n第二行");
});
it("SIMULATED: remount after a lost Canvas create ACK only reads the frozen request even when Retry is clicked", async () => {
  const f = productFixture(), session = f.session(); await session.load(); f.loseAck(); const view = mount(session);
  fireEvent.click(await screen.findByRole("button", { name: "创建可编辑草稿" }));
  await screen.findByText(/笔记是否创建成功尚未确认/); view.unmount();
  const restored = f.session(); await restored.load(); mount(restored);
  fireEvent.click(await screen.findByRole("button", { name: "重试同一次笔记创建" }));
  await waitFor(() => expect(restored.getSnapshot().state.pending_original).toBeNull());
  expect(bridge.call.mock.calls.filter(([op]) => op === "document_create")).toHaveLength(1);
});
it.each(["source","document"])("SIMULATED: the %s reader rejects an oversized Canvas envelope before base64 allocation",async reader=>{
  const f=productFixture(),session=f.session();await session.load();
  const saved=ack(await prepareCanvasDocument(f.source,f.original,f.bytes));
  if(reader==="document")f.records.set(saved.document_id,saved);
  f.original.content_base64="A".repeat(4*Math.ceil(CANVAS_ORIGINAL_LIMIT/3)+4);
  const decode=vi.spyOn(globalThis,"atob");
  if(reader==="source")mount(session);
  else render(<CoreWorkingStateProvider session={session}><CanonicalLibrarySpace purpose="reader" initialDocumentId={saved.document_id}/></CoreWorkingStateProvider>);
  await screen.findByText(reader==="source"?/原件版本核对未完成/:/关联原件未完成核验/);
  expect(decode).not.toHaveBeenCalled();expect(bridge.call.mock.calls.some(([op])=>op==="document_create"||op==="document_draft"||op==="document_export_save")).toBe(false);
  expect(f.source.original_name).toBe("固定.canvas");
  if(reader==="document")expect(await screen.findByRole("textbox",{name:"文档草稿"})).toHaveTextContent("中文🙂");
});
it.each([["create","unmount"],["create","workspace"],["draft","unmount"],["draft","workspace"]])("SIMULATED: delayed %s journal followed by %s never dispatches the old document write",async(operation,change)=>{
  const f=productFixture(),session=f.session();await session.load();const view=mount(session);
  const create=await screen.findByRole("button",{name:"创建可编辑草稿"});
  let box:HTMLElement|undefined;
  if(operation==="draft"){
    fireEvent.click(create);
    // Creation opens the saved document and replaces the first editor mount.
    await screen.findByText("文档已读取；保存不要求来源引用或审核。");
    await act(async()=>{await session.flush();});
    await waitFor(()=>{
      const current=screen.getByRole("textbox",{name:"文档草稿"}) as HTMLElement&{editor?:Editor};
      expect(current.isConnected).toBe(true);expect(current.editor).toBeDefined();expect(current.editor?.isDestroyed).toBe(false);
      box=current;
    });
  }
  const previousWrites=bridge.call.mock.calls.filter(([op])=>op==="document_create"||op==="document_draft").length;
  const delayed=f.delayNextJournal();
  if(operation==="create")fireEvent.click(create);
  else {
    const edited=structuredClone([...f.records.values()][0].editor_json) as JSONContent;
    edited.content![0].content=[{type:"text",text:"保留待提交文字"}];
    act(()=>{(box as HTMLElement&{editor:Editor}).editor.commands.setContent(decodeEditorContent(edited),{emitUpdate:true});});
    fireEvent.click(screen.getByRole("button",{name:"保存草稿"}));
  }
  await act(async()=>{await delayed.entered;});
  if(change==="unmount")view.unmount();
  else {const other=f.otherSession();await other.load();view.rerender(<CoreWorkingStateProvider session={other}><CanonicalLibrarySpace purpose="reader" initialSourceTarget={{source_id:f.source.source_id,source_revision:f.source.sha256,sha256:f.source.sha256}}/></CoreWorkingStateProvider>);}
  await act(async()=>{delayed.release();await session.flush();});
  expect(bridge.call.mock.calls.filter(([op])=>op==="document_create"||op==="document_draft")).toHaveLength(previousWrites);
  if(operation==="create")expect(session.getSnapshot().state.pending_original).not.toBeNull();
  else expect(Object.values(session.getSnapshot().state.drafts)[0].editor_json.content[0].content?.[0].text).toBe("保留待提交文字");
});
