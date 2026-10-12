import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { Editor } from "@tiptap/core";
import { createHash, webcrypto } from "node:crypto";
import { CanonicalLibrarySpace } from "../spaces/CanonicalLibrarySpace";
import { decodeEditorContent } from "../components/DocumentEditor";
import { CoreWorkingStateProvider } from "../presentation/useCoreWorkingState";
import { CoreWorkingStateSession, type WorkingEditor, type WorkingRead, type WorkingState, type WorkingTransport } from "../presentation/coreWorkingState";

const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
// Keep the Library/Provider/editor/create implementation real. These unrelated
// panels do not participate in journal or document writes in this regression.
vi.mock("../components/CheckPanel",()=>({CheckPanel:()=>null}));
vi.mock("../components/BackupPanel",()=>({BackupPanel:()=>null}));
vi.mock("../templates/TemplateWorkspace",()=>({TemplateLauncher:()=>null}));

const editor=(text:string):WorkingEditor=>({type:"doc",content:[{type:"paragraph",attrs:{block_id:"stable",opaque:{future:[1,null,"保留"]}},content:text?[{type:"text",text}]:[]}]});
const empty=():WorkingState=>({drafts:{},opened_documents:[],active_document:null,page_id:null,pending_original:null});
const digest=(value:unknown)=>createHash("sha256").update(JSON.stringify(value)).digest("hex");
function documentRecord(id:string,title:string,text:string) {
  const content=editor(text);
  return {document_id:id,title,source_id:null,source_revision:null,version:1,editor_json:content,text_projection:text,content_sha256:digest(content),blocks:content.content.map((node,ordinal)=>({block_id:node.attrs!.block_id,kind:node.type,ordinal,node_json:node,text_projection:text,codec_status:"known"}))};
}
function fixture() {
  const records=new Map<string,ReturnType<typeof documentRecord>>([
    ["doc-a",documentRecord("doc-a","甲笔记","甲正文")],["doc-b",documentRecord("doc-b","乙笔记","乙正文")],
  ]);
  let server:WorkingRead={schema:"archeaxis.ui-working-state/v1",workspace_id:"a".repeat(32),restore_epoch:"initial",state_revision:0,state:empty(),draft_digests:{},pending_document_id:null,recovery_candidates:null,recovery_requires_confirmation:false};
  let rejectNextClear=false,loseNextCreate=false;
  let releaseDraft:((value:ReturnType<typeof documentRecord>)=>void)|null=null;
  const publish=(state:WorkingState)=>{
    server={...server,state:structuredClone(state),state_revision:server.state_revision+1,draft_digests:Object.fromEntries(Object.entries(state.drafts).map(([id,draft])=>[id,digest(draft.editor_json)]))};return structuredClone(server);
  };
  const checkBasis=(request:{workspace_id:string;restore_epoch:string;state_revision:number})=>{
    if(request.workspace_id!==server.workspace_id||request.restore_epoch!==server.restore_epoch||request.state_revision!==server.state_revision)throw new Error("409 CAS mismatch");
  };
  const transport:WorkingTransport={
    read:vi.fn(async()=>structuredClone(server)),
    write:vi.fn(async request=>{checkBasis(request);return publish(request.state);}),
    clearSaved:vi.fn(async request=>{
      checkBasis(request);
      if(rejectNextClear){rejectNextClear=false;throw new Error("403 journal cleanup refused");}
      const sent=server.state.drafts[request.document_id],saved=records.get(request.document_id);
      if(!sent||!saved||sent.base_version!==request.base_version||server.draft_digests[request.document_id]!==request.content_sha256
        ||saved?.version!==request.saved_version||request.saved_version!==request.base_version+1||digest(saved.editor_json)!==digest(sent.editor_json))throw new Error("409 conditional clear refused");
      const state=structuredClone(server.state);delete state.drafts[request.document_id];return publish(state);
    }),
    recover:vi.fn(async()=>{throw new Error("No restore candidate in this fixture");}),
  };
  bridge.call.mockImplementation(async(operation:string,payload:Record<string,unknown>={})=>{
    if(operation==="sources_list")return {sources:[]};
    if(operation==="documents_list")return {documents:[...records.values()],next_cursor:null,snapshot_count:records.size};
    if(operation==="document_get"||operation==="document_version") {
      const record=records.get(String(payload.document_id));if(!record)throw new Error("404 missing document");
      return structuredClone(record);
    }
    if(operation==="document_create") {
      const body=payload.body as {create_request_id:string;title:string;editor_json:WorkingEditor};
      if(JSON.stringify(server.state.pending_original)!==JSON.stringify(body))throw new Error("Create POST preceded its frozen journal ACK");
      const id="doc_req_"+createHash("sha256").update(body.create_request_id).digest("hex");
      let saved=records.get(id);
      if(!saved){saved={...documentRecord(id,body.title,""),editor_json:structuredClone(body.editor_json),content_sha256:digest(body.editor_json),blocks:body.editor_json.content.map((node,ordinal)=>({block_id:node.attrs!.block_id,kind:node.type,ordinal,node_json:structuredClone(node),text_projection:"",codec_status:"known"}))};records.set(id,saved);}
      if(loseNextCreate){loseNextCreate=false;throw new Error("document create ACK lost");}
      return structuredClone(saved);
    }
    if(operation==="document_draft") {
      const id=String(payload.document_id),previous=records.get(id)!;
      const body=payload.body as {expected_version:number;editor_json:WorkingEditor};
      if(body.expected_version!==previous.version)throw new Error("409 document version mismatch");
      const saved={...previous,version:previous.version+1,editor_json:structuredClone(body.editor_json),content_sha256:digest(body.editor_json)};
      records.set(id,saved);
      if(releaseDraft)return new Promise(resolve=>{releaseDraft=value=>resolve(value);});
      return structuredClone(saved);
    }
    throw new Error("Unexpected Core operation: "+operation);
  });
  return {transport,records,get:()=>structuredClone(server),session:()=>new CoreWorkingStateSession(transport),
    refuseClear:()=>{rejectNextClear=true;},loseCreate:()=>{loseNextCreate=true;},
    holdDraft:()=>{releaseDraft=()=>{};},releaseDraft:()=>{releaseDraft!(structuredClone(records.get("doc-a")!));releaseDraft=null;},
  };
}
function mount(session:CoreWorkingStateSession,props:Parameters<typeof CanonicalLibrarySpace>[0]={}) {
  return render(<CoreWorkingStateProvider session={session}><CanonicalLibrarySpace {...props}/></CoreWorkingStateProvider>);
}
function edit(box:HTMLElement,text:string) {
  act(()=>{(box as HTMLElement&{editor:Editor}).editor.commands.setContent(decodeEditorContent(editor(text)),{emitUpdate:true});});
}
beforeEach(()=>{
  vi.stubGlobal("crypto",webcrypto);
  vi.stubGlobal("__TAURI__",{core:{invoke:vi.fn()}});
  bridge.call.mockReset();
});
afterEach(()=>{vi.unstubAllGlobals();});

it("SIMULATED: mounted formal Library reloads two independent Core-journal drafts into a new Provider session",async()=>{
  const f=fixture(),session=f.session();await session.load();
  const first=mount(session);const user=userEvent.setup();
  await user.click(await screen.findByRole("button",{name:"甲笔记 · 文档"}));
  const a=await screen.findByRole("textbox",{name:"文档草稿"});fireEvent.compositionStart(a);edit(a,"甲独立草稿");
  await user.click(screen.getByRole("button",{name:"乙笔记 · 文档"}));
  const b=await screen.findByRole("textbox",{name:"文档草稿"});fireEvent.compositionStart(b);edit(b,"乙独立草稿");
  await act(async()=>{await session.flush();});
  expect(f.get().state.drafts["doc-a"].editor_json.content[0].attrs?.opaque).toEqual({future:[1,null,"保留"]});
  expect(Object.keys(f.get().state.drafts)).toEqual(["doc-a","doc-b"]);
  first.unmount();
  const reopened=f.session();await reopened.load();mount(reopened,{initialDocumentId:"doc-a"});
  expect(await screen.findByRole("textbox",{name:"文档草稿"})).toHaveTextContent("甲独立草稿");
  const tabs=await screen.findByRole("tablist",{name:"已打开文档标签"});
  await user.click(within(tabs).getByRole("tab",{name:/乙笔记/}));
  expect(await screen.findByRole("textbox",{name:"文档草稿"})).toHaveTextContent("乙独立草稿");
  expect(bridge.call.mock.calls.filter(([op])=>op==="document_draft")).toHaveLength(0);
  expect(f.records.get("doc-a")?.version).toBe(1);expect(f.records.get("doc-b")?.version).toBe(1);
});

it("SIMULATED: a lost create ACK survives Library unmount and retries the frozen Core request ID and body",async()=>{
  const f=fixture(),session=f.session();await session.load();f.loseCreate();
  const first=mount(session,{purpose:"library",onOpenDocument:vi.fn()});const user=userEvent.setup();
  await user.click(await screen.findByRole("button",{name:"新建笔记"}));
  await screen.findByLabelText("待确认的笔记创建");
  await waitFor(()=>expect(bridge.call.mock.calls.filter(([op])=>op==="document_create")).toHaveLength(1));
  const sent=structuredClone((bridge.call.mock.calls.find(([op])=>op==="document_create")![1] as {body:unknown}).body);
  expect(f.get().state.pending_original).toEqual(sent);first.unmount();
  const reopened=f.session();await reopened.load();mount(reopened,{purpose:"library",onOpenDocument:vi.fn()});
  await user.click(await screen.findByRole("button",{name:"重试同一笔记请求"}));
  await waitFor(()=>expect(bridge.call.mock.calls.filter(([op])=>op==="document_create")).toHaveLength(2));
  const attempts=bridge.call.mock.calls.filter(([op])=>op==="document_create").map(([,payload])=>(payload as {body:unknown}).body);
  expect(attempts[1]).toEqual(sent);
  await waitFor(()=>expect(f.get().state.pending_original).toBeNull());
  expect([...f.records.keys()].filter(id=>id.startsWith("doc_req_"))).toHaveLength(1);
  expect(bridge.call.mock.calls.filter(([op])=>op==="document_version")).toHaveLength(1);
});

it("SIMULATED: known document ACK plus refused journal clear retries only the journal without a second body version",async()=>{
  const f=fixture(),session=f.session();await session.load();f.refuseClear();
  mount(session,{purpose:"reader",initialDocumentId:"doc-a"});
  const box=await screen.findByRole("textbox",{name:"文档草稿"});edit(box,"正文已确认保存");
  fireEvent.click(screen.getByRole("button",{name:"保存草稿"}));
  await screen.findByText(/正文已保存；工作草稿保全尚未确认/);
  expect(f.records.get("doc-a")?.version).toBe(2);
  expect(screen.getByRole("button",{name:"保存草稿"})).toBeDisabled();
  expect(session.getSnapshot().state.drafts["doc-a"]).toBeDefined();
  fireEvent.click(screen.getByRole("button",{name:"仅核对工作草稿保全"}));
  await waitFor(()=>expect(f.get().state.drafts["doc-a"]).toBeUndefined());
  expect(await screen.findByText(/已保存 · 当前持久化版本 2/)).toBeInTheDocument();
  await act(async()=>{await new Promise(resolve=>window.setTimeout(resolve,1000));});
  expect(bridge.call.mock.calls.filter(([op])=>op==="document_draft")).toHaveLength(1);
  expect(f.records.get("doc-a")?.version).toBe(2);
});

it("SIMULATED: input arriving after body submission is not cleared and is rebased to its confirmed document version",async()=>{
  const f=fixture(),session=f.session();await session.load();f.holdDraft();
  mount(session,{purpose:"reader",initialDocumentId:"doc-a"});
  const box=await screen.findByRole("textbox",{name:"文档草稿"});edit(box,"已发送正文");
  fireEvent.click(screen.getByRole("button",{name:"保存草稿"}));
  await waitFor(()=>expect(bridge.call.mock.calls.filter(([op])=>op==="document_draft")).toHaveLength(1));
  fireEvent.compositionStart(box);edit(box,"正文 ACK 期间晚输入");
  await act(async()=>{f.releaseDraft();});
  await waitFor(()=>expect(session.getSnapshot().state.drafts["doc-a"]?.base_version).toBe(2));
  expect(box).toHaveTextContent("正文 ACK 期间晚输入");
  expect(f.get().state.drafts["doc-a"].editor_json).toEqual(session.getSnapshot().state.drafts["doc-a"].editor_json);
  expect(f.transport.clearSaved).not.toHaveBeenCalled();
  expect(f.records.get("doc-a")?.editor_json).toEqual(editor("已发送正文"));
  expect(f.records.get("doc-a")?.version).toBe(2);
});
