import {useDiagnostics, resetDiagnostics} from "../presentation/diagnostics";
import {renderHook} from "@testing-library/react";
import type { Editor } from "@tiptap/core";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createHash, webcrypto } from "node:crypto";
import { assertCoreDto } from "../api/generated/core-contract";
import { CanonicalLibrarySpace } from "../spaces/CanonicalLibrarySpace";
import { SpaceView } from "../spaces/SpaceView";
import { ApiError } from "../api/client";

const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));
const hash = createHash("sha256").update("原文样板").digest("hex");
const source = { source_id: "src_test", source_revision: hash, sha256: hash, original_name: "样板.txt", imported_at: "2026-10-05" };
const createdNotes=new Map<string,unknown>();
function noteAck(payload:Record<string,unknown>) {
  const body=payload.body as {create_request_id:string;title:string;editor_json:typeof doc.editor_json};
  const id="doc_req_"+createHash("sha256").update(body.create_request_id).digest("hex");
  const node=body.editor_json.content[0];
  const saved={...doc,document_id:id,source_id:null,source_revision:null,title:body.title,version:1,
    editor_json:structuredClone(body.editor_json),text_projection:"",blocks:[{block_id:node.attrs.block_id,kind:"paragraph",ordinal:0,node_json:node,text_projection:"",codec_status:"known"}]};
  createdNotes.set(id,saved);return saved;
}
let doc = { document_id: "doc_test", source_id: source.source_id, source_revision: hash, title: source.original_name, version: 1,
  editor_json: { type: "doc", content: [{ type: "paragraph", attrs: { block_id: "p1" }, content: [{ type: "text", text: "已保存笔记" }] }] }, text_projection: "已保存笔记", content_sha256: hash, blocks: [] };

beforeEach(resetDiagnostics);
describe("canonical content sample", () => {
  it("SIMULATED: a verified first original explains conversion, ordinary notes and where they are saved", async () => {
    const previous=bridge.call.getMockImplementation()!;
    bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>op==="documents_list"?{documents:[]}:previous(op,payload));
    render(<CanonicalLibrarySpace purpose="reader" initialSourceTarget={{source_id:source.source_id,source_revision:hash,sha256:hash}}/>);
    await screen.findByRole("button",{name:"建立版本化草稿"});
    expect(screen.getByText(/需要提取文字时，点“整理此来源为知识候选”/)).toHaveTextContent("草稿保存在本地知识库");
    expect(screen.getByRole("button",{name:"整理此来源为知识候选"})).toBeEnabled();
    expect(bridge.call.mock.calls.some(([op])=>op==="document_create"||op==="job_enqueue")).toBe(false);
    expect(screen.getByRole("region",{name:"阅读与编辑文档视图"})).not.toHaveAttribute("data-reader-layout");
  });
  it("SIMULATED: an empty reader opens the actual import action without changing the URL directly", async () => {
    const previous=bridge.call.getMockImplementation()!,onImport=vi.fn();
    bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>op==="documents_list"?{documents:[]}:op==="sources_list"?{sources:[]}:previous(op,payload));
    const hashBefore=window.location.hash;
    render(<CanonicalLibrarySpace purpose="reader" onOpenImport={onImport}/>);
    const button=await screen.findByRole("button",{name:"导入第一份资料"}); fireEvent.click(button);
    expect(onImport).toHaveBeenCalledOnce(); expect(window.location.hash).toBe(hashBefore);
    expect(bridge.call.mock.calls.some(([op])=>op==="document_create")).toBe(false);
  });

  it("SIMULATED: a failed initial reader list offers retry and never reports an empty library", async () => {
    bridge.call.mockRejectedValue(new Error("not connected"));
    render(<CanonicalLibrarySpace purpose="reader" onOpenImport={vi.fn()}/>);
    expect(await screen.findByRole("heading",{name:"资料列表暂时无法读取"})).toBeInTheDocument();
    expect(screen.getByText(/读取失败时无法判断资料是否为空/)).toBeInTheDocument();
    expect(screen.queryByRole("button",{name:"导入第一份资料"})).not.toBeInTheDocument();
    expect(screen.queryByRole("button",{name:"新建原创笔记"})).not.toBeInTheDocument();
    const calls=bridge.call.mock.calls.length; fireEvent.click(screen.getByRole("button",{name:"刷新资料列表"}));
    await waitFor(()=>expect(bridge.call.mock.calls.length).toBeGreaterThan(calls));
  });
  it.each(["CURRENT","STALE","UNSUPPORTED","MISSING"])("SIMULATED: %s locator must be independently revalidated before navigation", async(status)=>{
    const position=JSON.stringify({type:"text",start:0,end:12,checksum:hash});
    const previous=bridge.call.getMockImplementation()!;
    bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>op==="anchors_list"
      ? {anchors:[{anchor_id:"anchor_recheck",source_id:source.source_id,source_revision:hash,position,location_status:"located"}]}
      : op==="anchor_resolve" ? assertCoreDto("AnchorResolutionDto",{source_id:source.source_id,anchor_id:"anchor_recheck",status,reason:"fixture",source_revision:hash,current_source_revision:hash,position,scope:"locator_provenance_only"})
      : previous(op,payload));
    render(<CanonicalLibrarySpace/>);
    const user=userEvent.setup();
    await user.click(await screen.findByRole("button",{name:"样板.txt"}));
    await user.click(await screen.findByRole("button",{name:"来源引用"}));
    await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("anchor_resolve",{source_id:source.source_id,anchor_id:"anchor_recheck"}));
    if(status==="CURRENT") await waitFor(()=>expect(screen.getByLabelText("原件正文")).toHaveFocus());
    else {await screen.findByText(/引用定位未通过当前核验/);expect(screen.getByLabelText("原件正文")).not.toHaveFocus();}
    expect(bridge.call.mock.calls.some(([op])=>op==="anchor_create"||op==="document_draft")).toBe(false);
  });
  beforeEach(() => {
    vi.stubGlobal("crypto", webcrypto);
    bridge.call.mockReset();
    createdNotes.clear();
    doc = { ...doc, version: 1 };
    bridge.call.mockImplementation(async (operation: string, payload: Record<string, unknown>) => {
      switch (operation) {
        case "sources_list": return { sources: [source] };
        case "documents_list": return { documents: [doc] };
        case "source_original": return { source_id: source.source_id, name: source.original_name, media_type: "text/plain", sha256: hash, content_base64: Buffer.from("原文样板").toString("base64") };
        case "anchors_list": return { anchors: [] };
        case "document_get": return doc;
        case "document_version": return createdNotes.get(payload.document_id as string)??{ ...doc, version: payload.version };
        case "document_restore": return { ...doc, version: doc.version + 1 };
        case "anchor_create": return { anchor_id: "anchor_test", source_id: source.source_id, source_revision: hash, position: (payload.body as Record<string, unknown>).position, location_status: "bound_revision" };
        case "document_draft": return { ...doc, editor_json: (payload.body as Record<string, unknown>).editor_json, version: doc.version + 1 };
        case "document_export": return {document_id:doc.document_id,version:doc.version,format:payload.format,source_revision:hash,projection_sha256:hash,files:[{path:"document.md",media_type:"text/markdown",content:"已保存笔记"}]};
        case "document_export_save": return {directory:"exports/doc_test/markdown/version-1",version:doc.version,files:["document.md","manifest.json"]};
        default: throw new Error(operation);
      }
    });
  });
  it("SIMULATED: an opened reader exposes separate keyboard focus regions without changing the saved document",async()=>{
    render(<CanonicalLibrarySpace purpose="reader" initialDocumentId={doc.document_id}/>);
    const editor=await screen.findByRole("textbox",{name:"文档草稿"});
    expect(editor).toHaveTextContent("已保存笔记");
    const reader=screen.getByRole("region",{name:"阅读与编辑文档视图"});
    expect(reader).toHaveAttribute("data-reader-layout","split");
    const body=screen.getByRole("region",{name:"正文与原件滚动区"}),details=screen.getByRole("complementary",{name:"内容详情"});
    expect(body).toHaveAttribute("tabindex","0");expect(details).toHaveAttribute("tabindex","0");
    body.focus();expect(body).toHaveFocus();details.focus();expect(details).toHaveFocus();
    expect(within(body).getByRole("textbox",{name:"文档草稿"})).toBe(editor);
    expect(bridge.call.mock.calls.some(([op])=>["document_draft","document_create","model_configuration_put"].includes(op))).toBe(false);
  });
  it("SIMULATED: page20 keeps the history reader and runtime footer reachable while reading an immutable version",async()=>{
    render(<SpaceView spaceId="settings" uiPageId="20" initialDocumentId={doc.document_id} onInspect={vi.fn()} onNavigate={vi.fn()}/>);
    const current=await screen.findByRole("heading",{name:"当前保存正文"});
    const wrapper=screen.getByRole("region",{name:"历史与来源"}),reader=screen.getByRole("region",{name:"文档版本视图"});
    expect(reader.parentElement).toBe(wrapper);
    expect(wrapper.matches('.stitch-history-page:has(> .stitch-reader-page[data-reader-layout="split"])')).toBe(true);
    const body=screen.getByRole("region",{name:"正文与原件滚动区"}),details=screen.getByRole("complementary",{name:"内容详情"});
    expect(body).toContainElement(current);expect(body).toHaveTextContent(doc.text_projection);
    expect(screen.queryByRole("textbox",{name:"文档草稿"})).not.toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button",{name:"只读查看历史版本"}));
    expect(await screen.findByRole("region",{name:"历史版本详情"})).toHaveTextContent("历史版本 1");
    expect(bridge.call).toHaveBeenCalledWith("document_version",{document_id:doc.document_id,version:1});
    body.focus();expect(body).toHaveFocus();details.focus();expect(details).toHaveFocus();
    const runtime=within(wrapper).getByText("当前运行身份与来源",{selector:"summary"});
    runtime.focus();expect(runtime).toHaveFocus();expect(runtime.closest("details")?.parentElement).toBe(wrapper);
    expect(bridge.call.mock.calls.some(([op])=>["document_draft","document_restore","document_create","model_configuration_put","material_question"].includes(op))).toBe(false);
  });
  it("SIMULATED: a source hash stays in diagnostics instead of the inspector version", async () => {
    const previous = bridge.call.getMockImplementation()!;
    bridge.call.mockImplementation((operation:string, payload:Record<string,unknown>) => operation === "documents_list"
      ? Promise.resolve({documents:[]}) : previous(operation,payload));
    const onInspect = vi.fn();
    render(<CanonicalLibrarySpace onInspect={onInspect} />);
    await userEvent.setup().click(await screen.findByRole("button", {name:source.original_name}));
    await waitFor(() => expect(onInspect).toHaveBeenCalled());
    const target = onInspect.mock.calls.at(-1)![0];
    expect(target.version).toBeUndefined();
    expect(target.identityDetails).toEqual({source_id:source.source_id,source_revision:hash,raw_sha256:hash,anchor_count:0});
    expect(target.title).toBe(source.original_name);
    expect(target.lifecycle).toBe("原件已保存");
  });
  it("SIMULATED: a source draft retries the identical frozen request after a lost ACK", async () => {
    const previous=bridge.call.getMockImplementation()!;
    let saved: typeof doc | null=null;
    let first=true;
    bridge.call.mockImplementation(async(operation:string,payload:Record<string,unknown>)=>{
      if(operation==="documents_list")return {documents:[]};
      if(operation==="document_create") {
        const body=payload.body as {create_request_id:string;source_id:string;source_revision:string;title:string;editor_json:typeof doc.editor_json};
        expect(body.create_request_id).toMatch(/^note_/);
        const node=body.editor_json.content[0];
        saved={...doc,document_id:"doc_req_"+createHash("sha256").update(body.create_request_id).digest("hex"),
          source_id:body.source_id,source_revision:body.source_revision,title:body.title,editor_json:structuredClone(body.editor_json),text_projection:"原文样板",
          blocks:[{block_id:node.attrs.block_id,kind:"paragraph",ordinal:0,node_json:node,text_projection:"原文样板",codec_status:"known"}] as typeof doc.blocks};
        if(first){first=false;throw new Error("lost ACK");}return saved;
      }
      if(operation==="document_version"&&saved&&payload.document_id===saved.document_id)return saved;
      if(operation==="document_get"&&saved&&payload.document_id===saved.document_id)return saved;
      return previous(operation,payload);
    });
    render(<CanonicalLibrarySpace/>);
    const user=userEvent.setup();
    await user.click(await screen.findByRole("button",{name:"样板.txt"}));
    await user.click(await screen.findByRole("button",{name:"建立版本化草稿"}));
    await screen.findByLabelText("待确认的笔记创建");
    await user.click(screen.getByRole("button",{name:"刷新资料列表"}));
    await waitFor(()=>expect(screen.getByRole("button",{name:"刷新资料列表"})).toBeEnabled());
    expect(screen.getByLabelText("待确认的笔记创建")).toBeInTheDocument();
    await user.click(screen.getByRole("button",{name:"重试同一次笔记创建"}));
    await waitFor(()=>expect(screen.getByRole("textbox",{name:"文档草稿"})).toHaveTextContent("原文样板"));
    const sent=bridge.call.mock.calls.filter(([operation])=>operation==="document_create").map(([,payload])=>payload);
    expect(sent).toHaveLength(2);expect(sent[1]).toEqual(sent[0]);
  });
  it("SIMULATED: same-space object navigation preserves dirty text and focuses actual version controls without writes", async () => {
    const onDirtyChange = vi.fn();
    const {rerender} = render(<CanonicalLibrarySpace onDirtyChange={onDirtyChange} />);
    await userEvent.setup().click(await screen.findByRole("button", {name:"样板.txt · 文档"}));
    const textbox = await screen.findByRole("textbox", {name:"文档草稿"});
    fireEvent.compositionStart(textbox);
    act(() => {(textbox as HTMLElement & {editor:Editor}).editor.commands.setContent({type:"doc",content:[{type:"paragraph",content:[{type:"text",text:"导航仍保留未保存正文"}]}]},{emitUpdate:true});});
    await screen.findByText(/尚未保存 · 当前已保存版本/);
    bridge.call.mockClear(); onDirtyChange.mockClear();
    rerender(<CanonicalLibrarySpace onDirtyChange={onDirtyChange} navigation={{section:"versions",sequence:1}} />);
    expect(screen.getByLabelText("文档版本导航")).toHaveFocus();
    expect(screen.getByRole("textbox", {name:"文档草稿"})).toBe(textbox);
    expect(textbox).toHaveTextContent("导航仍保留未保存正文");
    expect(onDirtyChange).not.toHaveBeenCalled(); expect(bridge.call).not.toHaveBeenCalled();
  });
  it("SIMULATED: refreshed metadata does not replace the selected original or remount a dirty editor",async()=>{
    render(<CanonicalLibrarySpace/>);const user=userEvent.setup();await user.click(await screen.findByRole("button",{name:"样板.txt"}));
    const original=await screen.findByLabelText("原件正文");const textbox=await screen.findByRole("textbox",{name:"文档草稿"});
    fireEvent.compositionStart(textbox);act(()=>{(textbox as HTMLElement&{editor:Editor}).editor.commands.setContent({type:"doc",content:[{type:"paragraph",content:[{type:"text",text:"未保存，刷新必须保留"}]}]},{emitUpdate:true});});
    const served=bridge.call.getMockImplementation()!;bridge.call.mockImplementation(async(op,payload)=>op==="documents_list"?{documents:[{...doc,title:"新列表标题",version:2}],next_cursor:null,snapshot_count:1}:served(op,payload));
    bridge.call.mockClear();act(()=>window.dispatchEvent(new Event("archeaxis-job-changed")));
    await screen.findByRole("button",{name:"新列表标题 · 文档"});
    expect(screen.getByRole("textbox",{name:"文档草稿"})).toBe(textbox);expect(textbox).toHaveTextContent("未保存，刷新必须保留");expect(screen.getByLabelText("原件正文")).toBe(original);
    expect(bridge.call.mock.calls.map(([op])=>op).sort()).toEqual(["documents_list","sources_list"]);
  });
  it("SIMULATED: a delayed list snapshot cannot downgrade a document save acknowledged during refresh",async()=>{
    render(<CanonicalLibrarySpace/>);const user=userEvent.setup();await user.click(await screen.findByRole("button",{name:"样板.txt · 文档"}));
    const textbox=await screen.findByRole("textbox",{name:"文档草稿"});fireEvent.compositionStart(textbox);
    act(()=>{(textbox as HTMLElement&{editor:Editor}).editor.commands.setContent({type:"doc",content:[{type:"paragraph",content:[{type:"text",text:"保存中的新正文"}]}]},{emitUpdate:true});});
    const served=bridge.call.getMockImplementation()!;let release!:(value:unknown)=>void,first=true;let latest=doc;
    bridge.call.mockImplementation(async(op,payload)=>{
      if(op==="documents_list"){if(first){first=false;return new Promise(resolve=>{release=resolve;});}return {documents:[latest],next_cursor:null,snapshot_count:1};}
      if(op==="document_draft"){latest={...doc,title:"刚保存的标题",version:2,editor_json:payload.body.editor_json};return latest;}
      return served(op,payload);
    });
    await user.click(screen.getByRole("button",{name:"刷新资料列表"}));fireEvent.compositionEnd(textbox);await user.click(screen.getByRole("button",{name:"保存草稿"}));
    await screen.findByRole("button",{name:"刚保存的标题 · 文档"});
    await act(async()=>release({documents:[doc],next_cursor:null,snapshot_count:1}));
    expect(screen.getByRole("button",{name:"刚保存的标题 · 文档"})).toBeInTheDocument();expect(textbox).toHaveTextContent("保存中的新正文");
  });
  it("SIMULATED: object navigation does not invent a selected source or document", async () => {
    const {rerender} = render(<CanonicalLibrarySpace navigation={{section:"anchors",sequence:1}} />);
    expect(screen.getByText(/请先选择实际来源原件/)).toBeInTheDocument();
    rerender(<CanonicalLibrarySpace navigation={{section:"versions",sequence:2}} />);
    expect(screen.getByLabelText("文档版本导航")).toHaveFocus();
    expect(screen.getByText(/请先选择已保存文档/)).toBeInTheDocument();
    expect(bridge.call.mock.calls.some(([operation])=>operation==="document_get" || operation==="document_version" || operation==="document_restore")).toBe(false);
    await screen.findByRole("button", {name:"样板.txt · 文档"});
  });
  it("SIMULATED: keeps independent dirty drafts when switching between document tabs", async () => {
    const other = { ...doc, document_id: "doc_other", title: "第二份笔记", source_id: null, source_revision: null,
      editor_json: { type: "doc", content: [{ type: "paragraph", content: [{ type: "text", text: "第二份正文" }] }] },
      text_projection: "第二份正文" };
    const records = new Map<string, Record<string, unknown>>([[doc.document_id, doc], [other.document_id, other]]);
    bridge.call.mockImplementation(async (operation: string, payload: Record<string, unknown>) => {
      if (operation === "sources_list") return { sources: [source] };
      if (operation === "documents_list") return { documents: [...records.values()] };
      if (operation === "document_get") return records.get(String(payload.document_id));
      if (operation === "document_draft") {
        const id = String(payload.document_id), current = records.get(id)!;
        const saved = { ...current, version: Number(current.version) + 1, editor_json: (payload.body as Record<string, unknown>).editor_json };
        records.set(id, saved); return saved;
      }
      if (operation === "anchors_list") return { anchors: [] };
      if (operation === "source_original") return { source_id: source.source_id, name: source.original_name, media_type: "text/plain", sha256: hash, content_base64: Buffer.from("原文样板").toString("base64") };
      throw new Error(operation);
    });
    const user = userEvent.setup();
    render(<CanonicalLibrarySpace />);
    await user.click(await screen.findByRole("button", { name: "样板.txt · 文档" }));
    await user.click(await screen.findByRole("button", { name: "第二份笔记 · 文档" }));
    const tabs = screen.getByRole("tablist", { name: "已打开文档标签" });
    expect(within(tabs).getAllByRole("tab")).toHaveLength(2);
    const secondTab = within(tabs).getByRole("tab", { name: /第二份笔记/ });
    expect(secondTab).toHaveAttribute("aria-selected", "true");
    const editor = screen.getByRole("textbox", { name: "文档草稿" });
    fireEvent.compositionStart(editor);
    act(() => { (editor as HTMLElement & { editor: Editor }).editor.commands.setContent({ type: "doc", content: [{ type: "paragraph", content: [{ type: "text", text: "第二份未保存正文" }] }] }, { emitUpdate: true }); });
    const firstTab = within(tabs).getByRole("tab", { name: /样板.txt/ });
    await user.click(firstTab);
    expect(firstTab).toHaveAttribute("aria-selected", "true");
    expect(await screen.findByRole("textbox", { name: "文档草稿" })).toHaveTextContent("已保存笔记");
    expect(secondTab).toHaveTextContent("未保存");
    await user.click(secondTab);
    expect(secondTab).toHaveAttribute("aria-selected", "true");
    expect(await screen.findByRole("textbox", { name: "文档草稿" })).toHaveTextContent("第二份未保存正文");
    expect(bridge.call.mock.calls.filter(([operation]) => operation === "document_get")).toHaveLength(4);
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    await user.click(within(tabs).getByRole("button", { name: "关闭文档标签 第二份笔记" }));
    expect(confirm).toHaveBeenCalledWith(expect.stringContaining("关闭标签将丢弃仅保存在内存中的草稿"));
    expect(within(tabs).queryByRole("tab", { name: /第二份笔记/ })).not.toBeInTheDocument();
    expect(records.get("doc_other")?.text_projection).toBe("第二份正文");
    confirm.mockRestore();
  });
  it("SIMULATED: shows an identity-bound original and derived draft side by side with separate hashes", async () => {
    render(<CanonicalLibrarySpace />);
    await userEvent.setup().click(await screen.findByRole("button", {name:"样板.txt · 文档"}));
    const split = screen.getByRole("region", {name:"原件与派生文档并排阅读"});
    const reader = within(split);
    // The pair renders from two fetches that land in different commits: the derived document
    // arrives with the click, the identity block only once the original's own read resolves.
    // Every one of these therefore awaits its own element; the assertions themselves are
    // unchanged. CI's desktop-build job runs this suite on slower scheduling and was failing
    // here on `来源版本` while the same file was green locally.
    expect(await reader.findByRole("article", {name:"不可变原件"})).toBeInTheDocument();
    expect(await reader.findByRole("textbox", {name:"文档草稿"})).toHaveTextContent("已保存笔记");
    expect(await reader.findByText(/来源：样板.txt · 文档第 1 版/)).toBeInTheDocument();
    expect(await reader.findByRole("button",{name:"查看诊断详情：关联原件身份"})).toBeInTheDocument();
    const diagnostics = renderHook(useDiagnostics);
    await userEvent.setup().click(reader.getByRole("button",{name:"查看诊断详情：关联原件身份"}));
    expect(diagnostics.result.current[0].payload).toEqual({source_id:doc.source_id,source_revision:hash,sha256:hash});
    expect(await within(reader.getByRole("article",{name:"派生文档与版本核验"})).findByText(`文档第 ${doc.version} 版`)).toBeInTheDocument();
    await userEvent.setup().click(reader.getByRole("button",{name:"查看诊断详情：文档内容详细信息"}));
    expect(diagnostics.result.current[0].payload).toEqual({document_id:doc.document_id,version:doc.version,content_sha256:doc.content_sha256});
    expect(reader.queryByText(doc.content_sha256)).not.toBeInTheDocument();
    expect(await reader.findByLabelText("并排原件正文")).toHaveTextContent("原文样板");
  });
  it("SIMULATED: refuses to pair an original when the document source revision differs", async () => {
    doc = {...doc, source_revision:"f".repeat(64)};
    const user = userEvent.setup();
    render(<CanonicalLibrarySpace />);
    await user.click(await screen.findByRole("button", {name:"样板.txt · 文档"}));
    const split = screen.getByRole("region", {name:"原件与派生文档并排阅读"});
    expect(await within(split).findByText(/原件读取失败、身份不匹配或未绑定/)).toBeInTheDocument();
    expect(within(split).queryByLabelText("并排原件正文")).not.toBeInTheDocument();
    expect(within(split).getByRole("textbox", {name:"文档草稿"})).toHaveTextContent("已保存笔记");
  });
  it("SIMULATED: reads historical text and revision basis without restoring or replacing the current draft", async () => {
    const previous = bridge.call.getMockImplementation()!;
    bridge.call.mockImplementation((operation: string, payload: Record<string, unknown>) => operation === "document_version" ? Promise.resolve({ ...doc, version: 1, text_projection: "历史正文独立保存", revision_basis: { rationale: "核对原件后修正年份", reference_version: 1 } }) : previous(operation, payload));
    render(<CanonicalLibrarySpace />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "样板.txt · 文档" }));
    await user.click(screen.getByRole("button", { name: "只读查看历史版本" }));
    expect(await screen.findByText("历史正文独立保存")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "文档草稿" })).toHaveTextContent("已保存笔记");
    // The revision basis is reachable verbatim through diagnostics instead of being printed inline.
    const debug = vi.spyOn(console, "debug").mockImplementation(() => {}); const diagnostics = renderHook(useDiagnostics);
    await user.click(screen.getByRole("button", { name: /历史修订依据/ }));
    expect(diagnostics.result.current.map(entry => [null, entry.label, entry.payload]).some(([, label, payload]) => label === "历史修订依据" && JSON.stringify(payload).includes("核对原件后修正年份"))).toBe(true);
    expect(screen.queryByText(/核对原件后修正年份/)).not.toBeInTheDocument();
    expect(debug).not.toHaveBeenCalled(); debug.mockRestore();
    expect(bridge.call.mock.calls.some(([operation]) => operation === "document_restore" || operation === "document_draft")).toBe(false);
  });
  it("SIMULATED: historical Inspector preserves dirty editor and only uses the actual returned hash", async () => {
    const previous = bridge.call.getMockImplementation()!;
    const historicalHash = "b".repeat(64);
    bridge.call.mockImplementation((op: string, payload: Record<string, unknown>) => op === "document_version"
      ? Promise.resolve({...doc, content_sha256: historicalHash, source_id: null, source_revision: null}) : previous(op, payload));
    const onInspect = vi.fn(); render(<CanonicalLibrarySpace onInspect={onInspect} />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", {name:"样板.txt · 文档"}));
    const textbox = screen.getByRole("textbox", {name:"文档草稿"});
    fireEvent.compositionStart(textbox);
    act(() => {(textbox as HTMLElement & {editor:Editor}).editor.commands.setContent({type:"doc",content:[{type:"paragraph",content:[{type:"text",text:"历史检查保持未保存草稿"}]}]},{emitUpdate:true});});
    await screen.findByText(/尚未保存 · 当前已保存版本/);
    onInspect.mockClear(); bridge.call.mockClear();
    await user.click(screen.getByRole("button", {name:"只读查看历史版本"}));
    await waitFor(() => expect(onInspect).toHaveBeenCalledWith(expect.objectContaining({version:"1", lifecycle:expect.stringContaining("历史版本"), identityDetails:{document_id:doc.document_id,version:1,content_sha256:historicalHash,source_id:null,source_revision:null,raw_sha256:null}})));
    expect(onInspect.mock.calls.at(-1)![0].detail).not.toContain(historicalHash);
    expect(onInspect.mock.calls.at(-1)![0].rawSha256).toBeUndefined();
    expect(onInspect.mock.calls.at(-1)![0].review).toBeUndefined();
    expect(screen.getByRole("textbox", {name:"文档草稿"})).toBe(textbox);
    expect(textbox).toHaveTextContent("历史检查保持未保存草稿");
    expect(bridge.call.mock.calls.some(([op]) => op === "document_draft" || op === "document_restore")).toBe(false);
  });
  it("SIMULATED: late historical response cannot replace a new document Inspector", async () => {
    const previous = bridge.call.getMockImplementation()!;
    let complete!: (value: unknown) => void;
    const other = {...doc, document_id:"other_history_doc", title:"其他历史目标"};
    bridge.call.mockImplementation((op: string, payload: Record<string, unknown>) => {
      if (op === "documents_list") return Promise.resolve({documents:[doc, other]});
      if (op === "document_get" && payload.document_id === other.document_id) return Promise.resolve(other);
      if (op === "document_version") return new Promise(resolve => {complete = resolve;});
      return previous(op, payload);
    });
    const onInspect = vi.fn(); render(<CanonicalLibrarySpace onInspect={onInspect} />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", {name:"样板.txt · 文档"}));
    await user.click(screen.getByRole("button", {name:"只读查看历史版本"}));
    await user.click(screen.getByRole("button", {name:"其他历史目标 · 文档"}));
    await waitFor(() => expect(onInspect.mock.calls.at(-1)![0].identityDetails).toMatchObject({document_id:other.document_id,version:other.version,content_sha256:other.content_sha256,source_id:other.source_id,source_revision:other.source_revision}));
    const count = onInspect.mock.calls.length;
    await act(async () => {complete({...doc, text_projection:"不得覆盖的新旧回包"});});
    expect(onInspect).toHaveBeenCalledTimes(count);
    expect(screen.queryByText("不得覆盖的新旧回包")).not.toBeInTheDocument();
  });
  it("SIMULATED: mismatched historical identity leaves the current Inspector intact", async () => {
    const previous = bridge.call.getMockImplementation()!;
    bridge.call.mockImplementation((op: string, payload: Record<string, unknown>) => op === "document_version"
      ? Promise.resolve({...doc, document_id:"wrong-history-id"}) : previous(op, payload));
    const onInspect = vi.fn(); render(<CanonicalLibrarySpace onInspect={onInspect} />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", {name:"样板.txt · 文档"}));
    await waitFor(() => expect(onInspect).toHaveBeenCalled());
    onInspect.mockClear();
    await user.click(screen.getByRole("button", {name:"只读查看历史版本"}));
    await screen.findByText("历史版本未读取，请重试。");
    expect(onInspect).not.toHaveBeenCalled();
    expect(screen.getByRole("textbox", {name:"文档草稿"})).toHaveTextContent("已保存笔记");
  });
  it("SIMULATED: a failed superseded document read cannot stamp the newly opened document", async () => {
    const previous = bridge.call.getMockImplementation()!;
    const slow = { ...doc, document_id: "slow_doc", source_id: null, source_revision: null, title: "慢读取文档" };
    let reject!: (error: unknown) => void;
    bridge.call.mockImplementation((op: string, payload: Record<string, unknown>) => {
      if (op === "documents_list") return Promise.resolve({ documents: [slow, doc] });
      if (op === "document_get" && payload.document_id === slow.document_id) return new Promise((_, fail) => { reject = fail; });
      return previous(op, payload);
    });
    render(<CanonicalLibrarySpace />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "慢读取文档 · 文档" }));
    await user.click(screen.getByRole("button", { name: "样板.txt · 文档" }));
    await screen.findByText("文档已读取；保存不要求来源引用或审核。");
    await act(async () => { reject(new Error("superseded read")); });
    expect(screen.queryByText("文档读取未完成；当前内容仍保留。")).not.toBeInTheDocument();
    expect(screen.getByText("文档已读取；保存不要求来源引用或审核。")).toBeInTheDocument();
  });
  it("SIMULATED: a second click during an in-flight note creation issues exactly one write", async () => {
    const previous = bridge.call.getMockImplementation()!;
    let resolveCreate!: (value: unknown) => void;let request!:Record<string,unknown>;
    bridge.call.mockImplementation((op: string, payload: Record<string, unknown>) =>
      op === "document_create" ? new Promise((done) => { request=payload;resolveCreate = done; }) : previous(op, payload));
    render(<CanonicalLibrarySpace />);
    const user = userEvent.setup();
    const button = await screen.findByRole("button", { name: "新建原创笔记" });
    await user.click(button);
    expect(button).toBeDisabled();
    fireEvent.click(button);
    await act(async () => { resolveCreate(noteAck(request)); });
    expect(bridge.call.mock.calls.filter(([op]) => op === "document_create")).toHaveLength(1);
  });
  it("does not let a late original creation discard newly edited text",async()=>{
    let complete!:(value:unknown)=>void;let request!:Record<string,unknown>;
    const previous=bridge.call.getMockImplementation()!;
    bridge.call.mockImplementation((op:string,payload:Record<string,unknown>)=>op==="document_create"?new Promise(resolve=>{request=payload;complete=resolve;}):previous(op,payload));
    render(<CanonicalLibrarySpace/>);const user=userEvent.setup();
    await user.click(await screen.findByRole("button",{name:"样板.txt · 文档"}));
    const textbox=await screen.findByRole("textbox",{name:"文档草稿"});
    await user.click(screen.getByRole("button",{name:"新建原创笔记"}));
    fireEvent.compositionStart(textbox);act(()=>{(textbox as HTMLElement & {editor:Editor}).editor.commands.setContent({type:"doc",content:[{type:"paragraph",content:[{type:"text",text:"New unsaved text during request"}]}]},{emitUpdate:true});});
    await screen.findByText(/尚未保存 · 当前已保存版本/);
    await act(async()=>{complete(noteAck(request));});
    expect(screen.getByRole("textbox",{name:"文档草稿"})).toHaveTextContent("New unsaved text during request");
    expect(screen.getByRole("button",{name:"原创笔记 · 文档"})).toBeInTheDocument();
  });
  it("SIMULATED: retries the frozen request after a persisted create loses its ACK without duplicating the note",async()=>{
    const previous=bridge.call.getMockImplementation()!;let calls=0;
    bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>{
      if(op!=="document_create")return previous(op,payload);
      const saved=noteAck(payload);if(++calls===1)throw new Error("ACK lost after persistence");return saved;
    });
    render(<CanonicalLibrarySpace/>);const user=userEvent.setup();
    await user.click(screen.getByRole("button",{name:"新建原创笔记"}));
    await screen.findByText(/笔记创建结果尚未确认/);
    expect(screen.getByRole("button",{name:"新建原创笔记"})).toBeDisabled();
    const sent=structuredClone(bridge.call.mock.calls.find(([op])=>op==="document_create")![1]);
    await user.click(screen.getByRole("button",{name:"重试同一次笔记创建"}));
    await screen.findByText("原创笔记已建立。");
    expect(createdNotes.size).toBe(1);
    expect(bridge.call.mock.calls.filter(([op])=>op==="document_create").map(([,payload])=>payload)).toEqual([sent,sent]);
    expect(screen.queryByRole("button",{name:"重试同一次笔记创建"})).not.toBeInTheDocument();
  });
  it("SIMULATED: confirms a lost ACK by complete read-only version lookup without another create",async()=>{
    const previous=bridge.call.getMockImplementation()!;
    bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>{
      if(op!=="document_create")return previous(op,payload);
      noteAck(payload);throw new Error("lost ACK");
    });
    render(<CanonicalLibrarySpace/>);const user=userEvent.setup();
    await user.click(screen.getByRole("button",{name:"新建原创笔记"}));await screen.findByText(/笔记创建结果尚未确认/);
    await user.click(screen.getByRole("button",{name:"检查笔记创建结果"}));await screen.findByText("原创笔记已建立。");
    expect(bridge.call.mock.calls.filter(([op])=>op==="document_create")).toHaveLength(1);
  });
  it("keeps the frozen request when ACK identity, content or readback fails",async()=>{
    const previous=bridge.call.getMockImplementation()!;
    bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>{
      if(op==="document_create")return noteAck(payload);
      if(op==="document_version")throw new ApiError(403,"read forbidden","unauthorized");
      return previous(op,payload);
    });
    render(<CanonicalLibrarySpace/>);const user=userEvent.setup();
    await user.click(screen.getByRole("button",{name:"新建原创笔记"}));await screen.findByText(/笔记创建结果尚未确认/);
    expect(screen.getByRole("button",{name:"新建原创笔记"})).toBeDisabled();
    bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>{
      if(op==="document_version")return {...(createdNotes.get(payload.document_id as string) as object),title:"unexpected"};
      return previous(op,payload);
    });
    await user.click(screen.getByRole("button",{name:"检查笔记创建结果"}));
    await waitFor(()=>expect(screen.getByRole("button",{name:"检查笔记创建结果"})).toBeEnabled());
    expect(screen.getByRole("button",{name:"新建原创笔记"})).toBeDisabled();
    expect(screen.queryByText("原创笔记已建立。")).not.toBeInTheDocument();
  });
  it("releases only a definitively refused create, allowing a distinct new request",async()=>{
    const previous=bridge.call.getMockImplementation()!;let calls=0;
    bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>{
      if(op!=="document_create")return previous(op,payload);
      if(++calls===1)throw new ApiError(403,"forbidden","unauthorized");return noteAck(payload);
    });
    render(<CanonicalLibrarySpace/>);const user=userEvent.setup();
    await user.click(screen.getByRole("button",{name:"新建原创笔记"}));await screen.findByText(/原创笔记创建被明确拒绝/);
    expect(screen.queryByRole("button",{name:"重试同一次笔记创建"})).not.toBeInTheDocument();
    await user.click(screen.getByRole("button",{name:"新建原创笔记"}));await screen.findByText("原创笔记已建立。");
    const ids=bridge.call.mock.calls.filter(([op])=>op==="document_create").map(([,payload])=>payload.body.create_request_id);
    expect(new Set(ids).size).toBe(2);expect(createdNotes.size).toBe(1);
  });
  it("reuses the inspector with the actual saved version and source fingerprint without inventing review", async () => {
    doc = {...doc, source_revision:hash};
    const onInspect = vi.fn(); render(<CanonicalLibrarySpace onInspect={onInspect} />);
    await userEvent.setup().click(await screen.findByRole("button", { name: "样板.txt · 文档" }));
    await waitFor(() => expect(onInspect).toHaveBeenCalledWith(expect.objectContaining({ version: "1", rawSha256: undefined }), { reveal: false }));
    const target = onInspect.mock.calls.at(-1)![0];
    expect(target.identityDetails).toEqual({document_id:doc.document_id,version:doc.version,content_sha256:doc.content_sha256,source_id:source.source_id,source_revision:hash});
    expect(target.detail).not.toContain(doc.document_id);
    expect(target.detail).not.toContain(hash);
    expect(target.detail).toContain("已关联原件；原件和文档版本分别保留");
    expect(target.detail).toContain("保存不代表内容已被证实");
    expect(target.lifecycle).toContain("内容审核需另行确认");
    expect(target.review).toBeUndefined();
  });
  it.each(["document_get","document_restore"])("preserves edits begun while %s is pending",async(operation)=>{
    let complete!:(value:unknown)=>void;
    const previous=bridge.call.getMockImplementation()!;
    const other={...doc,document_id:"late-read",title:"late reader"};
    bridge.call.mockImplementation((op:string,payload:Record<string,unknown>)=>{
      if(op==="documents_list")return Promise.resolve({documents:[doc,other]});
      if(op===operation&&(op!=="document_get"||payload.document_id==="late-read"))return new Promise(resolve=>{complete=resolve;});
      return previous(op,payload);
    });
    render(<CanonicalLibrarySpace/>);const user=userEvent.setup();
    await user.click(await screen.findByRole("button",{name:"样板.txt · 文档"}));
    const textbox=await screen.findByRole("textbox",{name:"文档草稿"});
    await user.click(screen.getByRole("button",{name:operation==="document_get"?"late reader · 文档":"读取并恢复版本"}));
    fireEvent.compositionStart(textbox);act(()=>{(textbox as HTMLElement & {editor:Editor}).editor.commands.setContent({type:"doc",content:[{type:"paragraph",content:[{type:"text",text:"Preserved while read pending"}]}]},{emitUpdate:true});});
    await screen.findByText(/尚未保存 · 当前已保存版本/);
    await act(async()=>{complete(operation==="document_get"?other:{...doc,version:2});});
    expect(screen.getByRole("textbox",{name:"文档草稿"})).toHaveTextContent("Preserved while read pending");
  });
  it("saves an explicitly selected revision basis without requiring check execution",async()=>{
    const base=bridge.call.getMockImplementation();
    bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>{
      if(op==="document_checks")return {document_id:doc.document_id,version:1,content_sha256:hash,historical:false,default_status:"unverified",checks_capped:false,next_offset:null,checks:[{check_id:"check1",document_id:doc.document_id,version:1,content_sha256:hash,dimension:"recognition_fidelity",provider_mode:"manual",status:"uncertain",actor:"human",execution_verified:false,execution_state:"recorded"}]};
      return base?.(op,payload);
    });
    render(<CanonicalLibrarySpace/>);const user=userEvent.setup();
    await user.click(await screen.findByRole("button",{name:"样板.txt · 文档"}));
    await screen.findByText(/不确定 · 手动记录/);
    await user.type(screen.getByLabelText("下一次修订理由"),"修订说明");await user.click(screen.getByRole("button",{name:"用于下一次修订"}));
    await user.click(screen.getByRole("button",{name:"保存草稿"}));
    await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("document_draft",{document_id:doc.document_id,body:{expected_version:1,editor_json:expect.anything(),revision_basis:{rationale:"修订说明",reference_version:1,check_id:"check1"}}}));
  });
  it("creates and edits an original note without source or review prerequisites", async()=>{
    const originalDoc={...doc,source_id:null,source_revision:null,title:"原创笔记"};
    const base=bridge.call.getMockImplementation();
    bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>{
      if(op==="sources_list")return {sources:[]};
      if(op==="documents_list")return {documents:[]};
      if(op==="document_create")return noteAck(payload);
      if(op==="document_draft")return {...originalDoc,version:2,editor_json:(payload.body as Record<string,unknown>).editor_json};
      return base?.(op,payload);
    });
    render(<CanonicalLibrarySpace/>);
    await userEvent.setup().click(screen.getByRole("button",{name:"新建原创笔记"}));
    expect(await screen.findByLabelText("版本化草稿编辑器")).toBeInTheDocument();
    expect(screen.queryByRole("button",{name:"引用当前页"})).not.toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button",{name:"保存草稿"}));
    await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("document_draft",expect.anything()));
    expect(bridge.call).toHaveBeenCalledWith("document_create",{body:{create_request_id:expect.stringMatching(/^note_/),title:"原创笔记",editor_json:{type:"doc",content:[{type:"paragraph",attrs:{block_id:expect.any(String)}}]}}});
    expect(bridge.call.mock.calls.some(([op])=>op==="anchor_create"||op==="machine_answer")).toBe(false);
  });
  it("keeps the readback provenance folded and never upgrades an unverified locator",async()=>{
    const previous=bridge.call.getMockImplementation()!;
    bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>op==="anchors_list"?{anchors:[{anchor_id:"anchor_unverified",source_id:source.source_id,source_revision:hash,position:JSON.stringify({type:"text",start:0,end:12}),location_status:"unverified"}]}:previous(op,payload));
    render(<CanonicalLibrarySpace/>);
    await userEvent.setup().click(await screen.findByRole("button",{name:"样板.txt"}));
    expect(await screen.findByRole("button",{name:"来源引用 · 定位未核实"})).toBeInTheDocument();
    const evidence=screen.getByRole("complementary",{name:"来源版本证据"});
    expect(evidence).toHaveTextContent("原件内容与保存记录一致");
    expect(evidence).not.toHaveTextContent(hash);
    const diagnostics=renderHook(useDiagnostics);
    await userEvent.setup().click(within(evidence).getByRole("button",{name:"查看诊断详情：原件与来源详细信息"}));
    expect(diagnostics.result.current[0].payload).toEqual({source_id:source.source_id,source_revision:source.source_revision,sha256:hash});
    expect(screen.getByRole("button",{name:"来源引用 · 定位未核实"})).toBeEnabled();
  });
  it.each([6,26])("SIMULATED: imports a %i MiB original without invoking conversion",async(size)=>{
    const previous=bridge.call.getMockImplementation()!;
    bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>op==="source_import"?{source_id:"fixture-import",sha256:createHash("sha256").update(Buffer.from((payload.body as {content_base64:string}).content_base64,"base64")).digest("hex"),duplicate:false}:previous(op,payload));
    render(<CanonicalLibrarySpace/>);
    const raw=new Uint8Array(size*1024*1024);
    const file=new File([raw],"fixture.mp3");
    Object.defineProperty(file,"arrayBuffer",{value:async()=>raw.buffer});
    await userEvent.setup().upload(screen.getByLabelText("导入原件"),file);
    await waitFor(()=>expect(screen.getByLabelText("导入结果")).toHaveTextContent("原件已保留；转换尚未执行"),{timeout:12000});
    const call=bridge.call.mock.calls.find(([op])=>op==="source_import")!;
    expect(atob(call[1].body.content_base64).length).toBe(raw.byteLength);
    expect(bridge.call.mock.calls.some(([op])=>op==="job_enqueue"||op==="job_execute")).toBe(false);
  },15000);
  it.each(["wrong hash","missing duplicate","blank source"])("SIMULATED rejects an unverified import receipt: %s",async(reason)=>{
    const previous=bridge.call.getMockImplementation()!;
    bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>op==="source_import"
      ? {source_id:reason==="blank source"?"   ":"fixture-import",sha256:reason==="wrong hash"?"0".repeat(64):hash,...(reason==="missing duplicate"?{}:{duplicate:false})}
      : previous(op,payload));
    render(<CanonicalLibrarySpace/>);
    const file=new File(["原文样板"],"fixture.txt");Object.defineProperty(file,"arrayBuffer",{value:async()=>new TextEncoder().encode("原文样板").buffer});
    await userEvent.setup().upload(screen.getByLabelText("导入原件"),file);
    await waitFor(()=>expect(screen.getByLabelText("导入结果")).toHaveTextContent(/未确认，请保留原件/));
    expect(screen.getByLabelText("导入结果")).not.toHaveTextContent("原件已保留");
    expect(bridge.call.mock.calls.filter(([op])=>op==="sources_list")).toHaveLength(1);
  });
  it("SIMULATED preserves confirmed custody when the following list refresh fails",async()=>{
    const previous=bridge.call.getMockImplementation()!;let imported=false;
    bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>{
      if(op==="source_import"){imported=true;return {source_id:"fixture-import",sha256:hash,duplicate:true};}
      if(imported&&op==="sources_list")throw new Error("SIMULATED refresh failed");
      return previous(op,payload);
    });
    render(<CanonicalLibrarySpace/>);
    const file=new File(["原文样板"],"fixture.txt");Object.defineProperty(file,"arrayBuffer",{value:async()=>new TextEncoder().encode("原文样板").buffer});
    await userEvent.setup().upload(screen.getByLabelText("导入原件"),file);
    await waitFor(()=>expect(screen.getByLabelText("导入结果")).toHaveTextContent("原件已保留；转换尚未执行"));
    expect(await screen.findByText(/列表刷新失败/)).toBeInTheDocument();
  });
  it("reports oversized import as not imported instead of conversion success",async()=>{
    render(<CanonicalLibrarySpace/>);
    const file=new File([new Uint8Array(64*1024*1024+1)],"large.xlsx");
    await userEvent.setup().upload(screen.getByLabelText("导入原件"),file);
    expect(await screen.findByLabelText("导入结果")).toHaveTextContent("未导入：超过大小上限");
    expect(bridge.call.mock.calls.some(([operation])=>operation==="source_import")).toBe(false);
  });
  it("rejects original source identity mismatch even when returned bytes and SHA match",async()=>{
    const previous=bridge.call.getMockImplementation()!;
    bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>{
      const result=await previous(op,payload);
      return op==="source_original"?{...result,source_id:"another-source"}:result;
    });
    render(<CanonicalLibrarySpace/>);
    await userEvent.setup().click(await screen.findByRole("button",{name:"样板.txt"}));
    expect(await screen.findByRole("alert")).toHaveTextContent("原件版本核对未完成");
    expect(screen.queryByLabelText("原件正文")).not.toBeInTheDocument();
  });
  it("fails closed with a specific stage when WebView has no Web Crypto",async()=>{
    vi.stubGlobal("crypto",{});
    render(<CanonicalLibrarySpace/>);
    await userEvent.setup().click(await screen.findByRole("button",{name:"样板.txt"}));
    expect(await screen.findByRole("alert")).toHaveTextContent("原件字节核验未完成");
    expect(screen.queryByLabelText("原件正文")).not.toBeInTheDocument();
  });
  it("reads the exact real WebDriver source/original/empty-anchor DTO shapes through generated validation",async()=>{
    const realSource={source_id:"src_0c797d79499de2016ce7eceb",source_revision:"b9fe434a61ec006d638253664b058b05eda6ecec1e4a7ec4964da04138785d14",sha256:"b9fe434a61ec006d638253664b058b05eda6ecec1e4a7ec4964da04138785d14",original_name:"WebDriver证据.txt",imported_at:"2026-10-05 10:19:34"};
    const realOriginal={source_id:realSource.source_id,name:realSource.original_name,sha256:realSource.sha256,media_type:"text/plain",content_base64:"5Lit5paHIFdlYkRyaXZlciDljp/mlofor4Hmja4gR29sZGVuIG5hdGl2ZSB3aW5kb3cgNDIuCg=="};
    bridge.call.mockImplementation(async(op:string)=>{
      if(op==="sources_list")return assertCoreDto("SourcesListDto",{sources:[realSource]});
      if(op==="documents_list")return assertCoreDto("DocumentsListDto",{documents:[],next_cursor:null,snapshot_count:0});
      if(op==="source_original")return assertCoreDto("OriginalDto",realOriginal);
      if(op==="anchors_list")return assertCoreDto("AnchorsListDto",{anchors:[]});
      if(op==="capabilities_list")return {};
      if(op==="workspace_backups")return {backups:[]};
      throw new Error(op);
    });
    render(<CanonicalLibrarySpace/>);
    await userEvent.setup().click(await screen.findByRole("button",{name:"WebDriver证据.txt"}));
    expect(await screen.findByLabelText("原件正文")).toHaveTextContent("中文 WebDriver 原文证据 Golden native window 42.");
    expect(screen.getByText("此来源尚无引用记录。")).toBeInTheDocument();
  });
  it("exports only to the product-owned directory and reports its real save receipt", async () => {
    render(<CanonicalLibrarySpace />);
    const user=userEvent.setup();
    await user.click(await screen.findByRole("button",{name:"样板.txt"}));
    await user.click(await screen.findByRole("button",{name:"Markdown 导出到产品资料目录"}));
    await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("document_export_save",{document_id:"doc_test",format:"markdown"}));
    expect(await screen.findByText(/已导出到产品资料目录/)).toHaveTextContent("外部应用读取仍需单独验证");
  });
  it("refuses an export whose save receipt does not agree with the export it just proved", async () => {
    // The save receipt is a second, independent answer about the same bytes. A directory that
    // cannot be named, or a version that is not the exported one, means the product has not
    // exported what it claimed - so nothing may be presented as exported.
    for (const broken of [{files:["document.md"]}, {directory:"exports/doc_test/markdown/version-1",files:["document.md"]}]) {
      const served = bridge.call.getMockImplementation()!;
      bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>
        op==="document_export_save" ? broken : served(op,payload));
      const view = render(<CanonicalLibrarySpace />);
      const user = userEvent.setup();
      await user.click(await screen.findByRole("button",{name:"样板.txt"}));
      await user.click(await screen.findByRole("button",{name:"Markdown 导出到产品资料目录"}));
      expect(await screen.findByText(/导出未确认/)).toBeInTheDocument();
      expect(screen.queryByText(/已导出到产品资料目录/)).not.toBeInTheDocument();
      view.unmount();
    }
  });
  it("bounds the source navigation DOM while allowing later originals to be reached", async () => {
    const sources=Array.from({length:501},(_,index)=>({...source,source_id:`src_${index}`,original_name:`source-${index}.txt`}));
    bridge.call.mockImplementation(async(operation:string)=>operation==="sources_list"?{sources}:{documents:[]});
    render(<CanonicalLibrarySpace/>);
    await screen.findByRole("button",{name:"source-0.txt"});
    expect(screen.queryByRole("button",{name:"source-30.txt"})).not.toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button",{name:"下一组原件"}));
    expect(screen.getByRole("button",{name:"source-30.txt"})).toBeInTheDocument();
    expect(screen.queryByRole("button",{name:"source-0.txt"})).not.toBeInTheDocument();
  });
  it("reads hashed original, records a canonical reference and restores by optimistic version", async () => {
    render(<CanonicalLibrarySpace />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "样板.txt" }));
    expect(await screen.findByLabelText("原件正文")).toHaveTextContent("原文样板");
    expect(await screen.findByRole("textbox", { name: "文档草稿" })).toHaveTextContent("已保存笔记");
    await user.click(screen.getByRole("button", { name: "引用当前页" }));
    await waitFor(() => expect(bridge.call).toHaveBeenCalledWith("anchor_create", expect.objectContaining({ source_id: "src_test", body: expect.objectContaining({ revision: hash }) })));
    await user.click(screen.getByRole("button", { name: "保存草稿" }));
    await waitFor(() => expect(bridge.call).toHaveBeenCalledWith("document_draft", expect.objectContaining({ document_id: "doc_test", body: expect.objectContaining({ expected_version: 1 }) })));
    await user.click(screen.getByRole("button", { name: "读取并恢复版本" }));
    await waitFor(() => expect(bridge.call).toHaveBeenCalledWith("document_restore", expect.objectContaining({ body: expect.objectContaining({ expected_version: 2, restore_version: 1 }) })));
    expect(await screen.findByText(/恢复为新版本/)).toBeInTheDocument();
  });
  it("rejects altered original bytes instead of displaying false provenance", async () => {
    bridge.call.mockImplementation(async (operation: string) => operation === "sources_list" ? { sources: [source] }
      : operation === "documents_list" ? { documents: [] }
      : operation === "anchors_list" ? { anchors: [] }
      : { source_id:source.source_id,name:source.original_name,sha256: hash, content_base64: btoa("altered"), media_type: "text/plain" });
    render(<CanonicalLibrarySpace />);
    await userEvent.setup().click(await screen.findByRole("button", { name: "样板.txt" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("原件字节核验未完成");
    expect(screen.queryByLabelText("原件正文")).not.toBeInTheDocument();
  });
});
