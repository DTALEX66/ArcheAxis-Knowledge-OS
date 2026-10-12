import type { Editor } from "@tiptap/core";
import { createHash, webcrypto } from "node:crypto";
import { act, cleanup, fireEvent, render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../app/App";
import { SpaceView } from "../spaces/SpaceView";
import { CanonicalLibrarySpace } from "../spaces/CanonicalLibrarySpace";
import { assertCoreDto } from "../api/generated/core-contract";
const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call,verifyCanonicalCore:vi.fn(async()=>{})}));
const doc={document_id:"doc_real_identity",title:"中文普通笔记",version:2,source_id:null,source_revision:null,content_sha256:"a".repeat(64),text_projection:"真实返回正文",editor_json:{type:"doc",content:[{type:"paragraph",attrs:{block_id:"p1"},content:[{type:"text",text:"真实返回正文"}]},{type:"ownerFutureBlock",attrs:{block_id:"future1"},payload:{keep:"未知内容"}}]},blocks:[],revision_basis:null};
const summary={document_id:doc.document_id,title:doc.title,version:doc.version,source_id:doc.source_id,source_revision:doc.source_revision,content_sha256:doc.content_sha256};
beforeEach(()=>{
  window.history.replaceState(null,"","#page=02");
  bridge.call.mockReset();
  bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>={})=>{
    if(op==="sources_list") return {sources:[]};
    if(op==="learning_items") return {items:[],count:0};
    if(op==="documents_list") return assertCoreDto("DocumentsListDto",{documents:[summary],next_cursor:null,snapshot_count:1});
    if(op==="document_get") return assertCoreDto("DocumentDto",doc);
    if(op==="document_checks") return assertCoreDto("DocumentChecksDto",{document_id:doc.document_id,version:doc.version,content_sha256:doc.content_sha256,historical:false,default_status:"unverified",checks:[],checks_capped:false,next_offset:null});
    if(op==="document_draft") return assertCoreDto("DocumentDto",{...doc,version:3,editor_json:(payload.body as Record<string,unknown>).editor_json});
    if(op==="document_create") return assertCoreDto("DocumentDto",{...doc,document_id:"doc_new",title:"原创笔记",version:1});
    throw new Error(`unconfigured fixture operation ${op}`);
  });
});
afterEach(()=>{cleanup();vi.restoreAllMocks();vi.unstubAllGlobals();window.history.replaceState(null,"","#page=01");delete window.__TAURI__;});
describe("semantic 02 and 03 layouts",()=>{
  it("SIMULATED: new workspace shortcut opens semantic 02 while the old hash retains its compatibility surface",async()=>{
    window.history.replaceState(null,"","#page=01");
    const user=userEvent.setup();const view=render(<App/>);
    await user.click(screen.getByRole("button",{name:"新建笔记与阅读"}));
    expect(screen.getByRole("region",{name:"知识库文档视图"})).toBeInTheDocument();
    expect(window.location.hash).toBe("#page=02");
    view.unmount();window.history.replaceState(null,"","#space=library");
    render(<App/>);
    expect(screen.getByRole("heading",{name:"资料库",level:2})).toBeInTheDocument();
    expect(screen.getByLabelText("导入原件")).toBeInTheDocument();
    expect(screen.queryByRole("region",{name:"知识库文档视图"})).toBeNull();
  });
  it("SIMULATED: 02 opens the actual Core document ID in 03 and keeps tools on their intended surfaces",async()=>{
    const user=userEvent.setup();render(<App/>);
    const library=screen.getByRole("region",{name:"知识库文档视图"});
    await user.click(await within(library).findByRole("button",{name:"打开文档 中文普通笔记"}));
    const reader=screen.getByRole("region",{name:"阅读与编辑文档视图"});
    expect(await within(reader).findByRole("textbox",{name:"文档草稿"})).toHaveTextContent("真实返回正文");
    expect(bridge.call).toHaveBeenCalledWith("document_get",{document_id:"doc_real_identity"});
    expect(within(reader).getByRole("complementary",{name:"内容详情"})).toBeInTheDocument();
    expect(within(reader).queryByLabelText("导入原件")).toBeNull();
    expect(within(reader).queryByLabelText("目录批量导入")).toBeNull();
    expect(within(reader).queryByRole("button",{name:/创建备份/})).toBeNull();
    expect(bridge.call.mock.calls.some(([op])=>op==="source_import"||op==="document_draft")).toBe(false);
  });
  it("SIMULATED: App refuses navigation away from a composing dirty 03 draft and saves unknown payload intact",async()=>{
    const confirm=vi.spyOn(window,"confirm").mockReturnValue(false);
    const user=userEvent.setup();render(<App/>);
    await user.click(await screen.findByRole("button",{name:"打开文档 中文普通笔记"}));
    const textbox=await screen.findByRole("textbox",{name:"文档草稿"});
    fireEvent.compositionStart(textbox);
    act(()=>{(textbox as HTMLElement & {editor:Editor}).editor.commands.insertContent(" 未保存中文");});
    await user.click(screen.getByRole("button",{name:"知识"}));
    expect(confirm).not.toHaveBeenCalled();
    expect(screen.getByRole("region",{name:"阅读与编辑文档视图"})).toBeInTheDocument();
    expect(textbox).toHaveTextContent("未保存中文");
    expect(bridge.call.mock.calls.some(([op])=>op==="document_draft")).toBe(false);
    fireEvent.compositionEnd(textbox);
    await user.click(screen.getByRole("button",{name:"知识"}));
    expect(confirm).toHaveBeenCalledWith(expect.stringContaining("草稿尚未保存"));
    expect(textbox).toHaveTextContent("未保存中文");
    await user.click(screen.getByRole("button",{name:"保存草稿"}));
    const save=bridge.call.mock.calls.find(([op])=>op==="document_draft");
    expect(save?.[1]).toMatchObject({document_id:doc.document_id,body:{expected_version:2}});
    expect(JSON.stringify(save?.[1])).toContain("ownerFutureBlock");
    expect(JSON.stringify(save?.[1])).toContain("未知内容");
  });
  it("SIMULATED: same reader page is a no-op and the selected real Document survives another daily workflow",async()=>{
    const user=userEvent.setup();render(<App/>);
    await user.click(await screen.findByRole("button",{name:"打开文档 中文普通笔记"}));
    const editor=await screen.findByRole("textbox",{name:"文档草稿"});
    const before=bridge.call.mock.calls.filter(([op])=>op==="document_get").length;
    await user.click(screen.getByRole("button",{name:"阅读与编辑"}));
    expect(screen.getByRole("textbox",{name:"文档草稿"})).toBe(editor);
    expect(bridge.call.mock.calls.filter(([op])=>op==="document_get")).toHaveLength(before);
    await user.click(screen.getByRole("button",{name:"工作台"}));
    await user.click(screen.getByRole("button",{name:"知识"}));
    await user.click(screen.getByRole("button",{name:"阅读与编辑"}));
    expect(await screen.findByRole("textbox",{name:"文档草稿"})).toHaveTextContent("真实返回正文");
    expect(bridge.call.mock.calls.filter(([op])=>op==="document_get").every(([,body])=>body.document_id===doc.document_id)).toBe(true);
    expect(window.location.hash).toBe("#page=03");
  });
  it("SIMULATED: a refused document read presents failure without inventing an editor or substituting another document",async()=>{
    const previous=bridge.call.getMockImplementation()!;
    bridge.call.mockImplementation((op:string,payload:Record<string,unknown>={})=>op==="document_get"?Promise.reject(new Error("missing document")):previous(op,payload));
    render(<SpaceView spaceId="library" uiPageId="03" initialDocumentId="doc_missing" onInspect={vi.fn()} onNavigate={vi.fn()}/>);
    expect(await screen.findByRole("alert")).toHaveTextContent("文档读取未完成");
    expect(screen.queryByRole("textbox",{name:"文档草稿"})).toBeNull();
    expect(bridge.call).toHaveBeenCalledWith("document_get",{document_id:"doc_missing"});
    expect(bridge.call.mock.calls.some(([op])=>op==="document_create"||op==="document_draft")).toBe(false);
  });
  it("SIMULATED: search filters loaded summaries and paging failure retains existing document rows",async()=>{
    const previous=bridge.call.getMockImplementation()!;
    bridge.call.mockImplementation((op:string,payload:Record<string,unknown>={})=>op==="documents_list" ? payload.cursor ? Promise.reject(new Error("page offline")) : Promise.resolve(assertCoreDto("DocumentsListDto",{documents:[summary],next_cursor:"actual-snapshot-cursor",snapshot_count:2})) : previous(op,payload));
    const open=vi.fn();render(<CanonicalLibrarySpace purpose="library" onOpenDocument={open}/>);
    const user=userEvent.setup();await screen.findByRole("button",{name:"打开文档 中文普通笔记"});
    await user.type(screen.getByRole("searchbox"),"无匹配标题");
    expect(screen.queryByRole("button",{name:"打开文档 中文普通笔记"})).toBeNull();
    await user.clear(screen.getByRole("searchbox"));
    await user.click(screen.getByRole("button",{name:"加载更多文档"}));
    expect(await screen.findByRole("alert")).toHaveTextContent("更多文档读取失败");
    await user.click(screen.getByRole("button",{name:"打开文档 中文普通笔记"}));
    expect(open).toHaveBeenCalledWith(doc.document_id);
    expect(bridge.call).toHaveBeenCalledWith("documents_list",{cursor:"actual-snapshot-cursor"});
  });
  it("SIMULATED: successful ordinary creation enters 03 with the returned ID",async()=>{
    vi.stubGlobal("crypto",webcrypto);
    const previous=bridge.call.getMockImplementation()!;
    let created:typeof doc|null=null;
    bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>={})=>{
      if(op==="document_create") {
        const body=payload.body as {create_request_id:string;title:string;editor_json:typeof doc.editor_json};
        const node=body.editor_json.content[0];
        created={...doc,document_id:`doc_req_${createHash("sha256").update(body.create_request_id).digest("hex")}`,title:body.title,version:1,text_projection:"",editor_json:body.editor_json,
          blocks:[{block_id:node.attrs.block_id,ordinal:0,kind:"paragraph",text_projection:"",node_json:node,codec_status:"known"}] as never};
        return assertCoreDto("DocumentDto",created);
      }
      if(op==="document_version") {
        expect(payload).toEqual({document_id:created!.document_id,version:1});
        return assertCoreDto("DocumentDto",created);
      }
      return previous(op,payload);
    });
    const open=vi.fn();render(<CanonicalLibrarySpace purpose="library" onOpenDocument={open}/>);
    await userEvent.setup().click(screen.getByRole("button",{name:"新建笔记"}));
    await waitFor(()=>expect(open).toHaveBeenCalledWith(created!.document_id));
    expect(bridge.call.mock.calls.filter(([op])=>op==="document_create")).toHaveLength(1);
    expect(bridge.call.mock.calls.filter(([op])=>op==="document_version")).toHaveLength(1);
    expect(bridge.call.mock.calls.some(([op])=>op==="document_check_record"||op==="source_import")).toBe(false);
  });
  it.each(["sources_list","documents_list"])("SIMULATED: initial reader ID hydrates verified CAS after delayed %s without reopening a draft",async(delayed)=>{
    vi.stubGlobal("crypto",webcrypto);
    const original="中文来源原件\r\n原始字节";
    const digest=createHash("sha256").update(original).digest("hex");
    const source={source_id:"src_deep",source_revision:digest,sha256:digest,original_name:"中文源.txt",imported_at:"2026-10-09"};
    const linked={...doc,source_id:source.source_id,source_revision:digest};
    let release!:()=>void;
    const delay=new Promise<void>(resolve=>{release=resolve;});
    bridge.call.mockImplementation(async(op:string)=>{
      if(op===delayed) await delay;
      if(op==="sources_list") return assertCoreDto("SourcesListDto",{sources:[source]});
      if(op==="documents_list") return assertCoreDto("DocumentsListDto",{documents:[{...summary,source_id:source.source_id,source_revision:digest}],next_cursor:null,snapshot_count:1});
      if(op==="document_get") return assertCoreDto("DocumentDto",linked);
      if(op==="source_original") return assertCoreDto("OriginalDto",{source_id:source.source_id,name:source.original_name,media_type:"text/plain",sha256:digest,content_base64:Buffer.from(original).toString("base64")});
      if(op==="anchors_list") return {anchors:[]};
      if(op==="document_checks") return {document_id:doc.document_id,version:doc.version,content_sha256:doc.content_sha256,historical:false,default_status:"unverified",checks:[],checks_capped:false,next_offset:null};
      throw new Error(op);
    });
    render(<CanonicalLibrarySpace purpose="reader" initialDocumentId={doc.document_id}/>);
    expect(bridge.call.mock.calls.some(([op])=>op==="document_get")).toBe(false);
    await act(async()=>{release();});
    const editor=await screen.findByRole("textbox",{name:"文档草稿"});
    await userEvent.setup().click(screen.getByRole("button",{name:"原件"}));
    expect(await screen.findByLabelText("并排原件正文")).toHaveTextContent("中文来源原件");
    expect(screen.getByRole("complementary",{name:"内容详情"})).toHaveTextContent("原件身份、版本与字节已核对");
    fireEvent.compositionStart(editor);
    act(()=>{(editor as HTMLElement & {editor:Editor}).editor.commands.insertContent("仍保留未保存中文");});
    expect(bridge.call.mock.calls.filter(([op])=>op==="document_get")).toHaveLength(1);
    expect(editor).toHaveTextContent("仍保留未保存中文");
    expect(bridge.call.mock.calls.some(([op])=>op==="document_draft")).toBe(false);
  });
});
