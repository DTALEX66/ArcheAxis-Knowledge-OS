import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
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
  const history=new Map([...records].map(([id,row])=>[id,structuredClone(row)]));
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
      const record=(operation==="document_version"?history:records).get(String(payload.document_id));if(!record)throw new Error("404 missing document");
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
      if(body.expected_version!==previous.version)throw new ApiError(409,"document version mismatch");
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

function advance(f:ReturnType<typeof fixture>,text="另一份已保存正文") {
  const previous=f.records.get("doc-a")!;
  const next={...previous,version:previous.version+1,editor_json:editor(text),content_sha256:digest(editor(text)),text_projection:text};
  f.records.set("doc-a",next);return next;
}
async function conflict(f:ReturnType<typeof fixture>,session:CoreWorkingStateSession) {
  mount(session,{purpose:"reader",initialDocumentId:"doc-a"});
  const box=await screen.findByRole("textbox",{name:"文档草稿"});
  edit(box,"我的独立原稿");advance(f);
  fireEvent.click(screen.getByRole("button",{name:"保存草稿"}));
  await screen.findByText(/版本冲突：原草稿和保存基准保留/);return box;
}
async function compare() {
  fireEvent.click(screen.getByRole("button",{name:"读取当前版本并比较（保留草稿）"}));
  await screen.findByRole("region",{name:"当前已保存"});
}
it("SIMULATED mounted formal conflict compares exact snapshots, explicitly saves A and preserves independent B",async()=>{
  const f=fixture(),session=f.session();await session.load();session.rememberDraft("doc-b",editor("乙独立草稿"),1);await session.flush();
  const box=await conflict(f,session);
  const b=structuredClone(f.get().state.drafts["doc-b"]);
  await act(async()=>{await new Promise(resolve=>setTimeout(resolve,1000));});
  expect(bridge.call.mock.calls.filter(([op])=>op==="document_draft")).toHaveLength(1);
  await compare();
  expect(screen.getByRole("region",{name:"原基准"})).toHaveTextContent("甲正文");
  expect(screen.getByRole("region",{name:"当前已保存"})).toHaveTextContent("另一份已保存正文");
  expect(box).toHaveTextContent("我的独立原稿");expect(session.getSnapshot().state.drafts["doc-a"].base_version).toBe(1);
  fireEvent.click(screen.getByRole("button",{name:"明确保留本稿并按已比较版本保存"}));
  await waitFor(()=>expect(f.get().state.drafts["doc-a"]).toBeUndefined());
  expect(f.get().state.drafts["doc-b"]).toEqual(b);
  expect(f.records.get("doc-a")?.version).toBe(3);
  expect(f.records.get("doc-a")?.editor_json).toEqual(editor("我的独立原稿"));
  expect(bridge.call.mock.calls.filter(([op])=>op==="document_draft").map(([,p])=>p.body.expected_version)).toEqual([1,2]);
});
it("SIMULATED merge is explicit, a second 409 preserves merged content and stops automatic retries",async()=>{
  const f=fixture(),session=f.session();await session.load();const box=await conflict(f,session);await compare();
  fireEvent.click(screen.getByRole("button",{name:"编辑合并稿"}));edit(box,"人工合并后的完整稿");advance(f,"再次变化");
  fireEvent.click(screen.getByRole("button",{name:"明确采用合并稿并按已比较版本保存"}));
  await screen.findByText(/版本冲突：原草稿和保存基准保留/);
  expect(box).toHaveTextContent("人工合并后的完整稿");
  expect(f.get().state.drafts["doc-a"]).toEqual({base_version:2,editor_json:editor("人工合并后的完整稿")});
  await act(async()=>{await new Promise(resolve=>setTimeout(resolve,1000));});
  expect(bridge.call.mock.calls.filter(([op])=>op==="document_draft")).toHaveLength(2);
});
it("SIMULATED comparison rejects wrong identity and late readback never replaces new input",async()=>{
  const f=fixture(),session=f.session();await session.load();const box=await conflict(f,session);
  const call=bridge.call.getMockImplementation()!;
  bridge.call.mockImplementation((op:string,p:Record<string,unknown>)=>op==="document_version"?Promise.resolve({...f.records.get("doc-a"),document_id:"doc-wrong",version:1}):call(op,p));
  fireEvent.click(screen.getByRole("button",{name:"读取当前版本并比较（保留草稿）"}));
  await screen.findByText(/比较未确认/);expect(screen.queryByRole("region",{name:"当前已保存"})).toBeNull();
  let release!:(value:unknown)=>void;
  bridge.call.mockImplementation((op:string,p:Record<string,unknown>)=>op==="document_get"?new Promise(resolve=>{release=resolve;}):call(op,p));
  fireEvent.click(screen.getByRole("button",{name:"读取当前版本并比较（保留草稿）"}));await waitFor(()=>expect(release).toBeDefined());
  edit(box,"读取期间晚输入");await act(async()=>{release(f.records.get("doc-a"));});
  await screen.findByText(/比较读取期间新增输入已保留/);
  expect(box).toHaveTextContent("读取期间晚输入");expect(screen.queryByRole("region",{name:"当前已保存"})).toBeNull();
});
it("SIMULATED 403 identifies permission refusal, preserves draft and does not retry after more editing",async()=>{
  const f=fixture(),session=f.session();await session.load();mount(session,{purpose:"reader",initialDocumentId:"doc-a"});
  const box=await screen.findByRole("textbox",{name:"文档草稿"});const call=bridge.call.getMockImplementation()!;
  bridge.call.mockImplementation((op:string,p:Record<string,unknown>)=>op==="document_draft"?Promise.reject(new ApiError(403,"denied")):call(op,p));
  edit(box,"权限拒绝稿");fireEvent.click(screen.getByRole("button",{name:"保存草稿"}));await screen.findByText(/身份拒绝：原草稿仍保留/);
  edit(box,"权限拒绝后的晚输入");await act(async()=>{await new Promise(resolve=>setTimeout(resolve,1000));});
  expect(bridge.call.mock.calls.filter(([op])=>op==="document_draft")).toHaveLength(1);
  expect(session.getSnapshot().state.drafts["doc-a"].editor_json).toEqual(editor("权限拒绝后的晚输入"));expect(f.records.get("doc-a")?.version).toBe(1);
});
it("SIMULATED conflict save ACK with later editing keeps the new draft and confirmed version",async()=>{
  const f=fixture(),session=f.session();await session.load();const box=await conflict(f,session);await compare();f.holdDraft();
  fireEvent.click(screen.getByRole("button",{name:"明确保留本稿并按已比较版本保存"}));
  await waitFor(()=>expect(f.records.get("doc-a")?.version).toBe(3));
  fireEvent.compositionStart(box);edit(box,"冲突解决 ACK 期间晚输入");await act(async()=>{f.releaseDraft();});
  await waitFor(()=>expect(f.get().state.drafts["doc-a"]?.base_version).toBe(3));
  expect(box).toHaveTextContent("冲突解决 ACK 期间晚输入");expect(f.transport.clearSaved).not.toHaveBeenCalled();
});
it("SIMULATED conflict resolution known ACK plus failed journal cleanup retries journal only",async()=>{
  const f=fixture(),session=f.session();await session.load();await conflict(f,session);await compare();f.refuseClear();
  fireEvent.click(screen.getByRole("button",{name:"明确保留本稿并按已比较版本保存"}));await screen.findByText(/正文已保存；工作草稿保全尚未确认/);
  fireEvent.click(screen.getByRole("button",{name:"仅核对工作草稿保全"}));await waitFor(()=>expect(f.get().state.drafts["doc-a"]).toBeUndefined());
  await act(async()=>{await new Promise(resolve=>setTimeout(resolve,1000));});
  expect(f.records.get("doc-a")?.version).toBe(3);expect(bridge.call.mock.calls.filter(([op])=>op==="document_draft")).toHaveLength(2);
});
it("SIMULATED a journal CAS refusal cannot become a document comparison or send a body",async()=>{
  const f=fixture(),session=f.session();await session.load();mount(session,{purpose:"reader",initialDocumentId:"doc-a"});
  const box=await screen.findByRole("textbox",{name:"文档草稿"});
  vi.mocked(f.transport.write).mockRejectedValueOnce(new ApiError(409,"journal CAS changed"));
  edit(box,"工作保全冲突稿");fireEvent.click(screen.getByRole("button",{name:"保存草稿"}));
  await screen.findByText(/工作草稿保全尚未确认.*正文未发送/);
  await act(async()=>{await new Promise(resolve=>setTimeout(resolve,1000));});
  expect(bridge.call.mock.calls.filter(([op])=>op==="document_draft")).toHaveLength(0);
  expect(screen.queryByRole("button",{name:"读取当前版本并比较（保留草稿）"})).toBeNull();
  expect(session.getSnapshot().state.drafts["doc-a"].editor_json).toEqual(editor("工作保全冲突稿"));
});
it("SIMULATED a permission change during explicit resolution preserves the chosen draft and new basis",async()=>{
  const f=fixture(),session=f.session();await session.load();const box=await conflict(f,session);await compare();
  const call=bridge.call.getMockImplementation()!;
  bridge.call.mockImplementation((op:string,p:Record<string,unknown>)=>op==="document_draft"?Promise.reject(new ApiError(403,"permission changed")):call(op,p));
  fireEvent.click(screen.getByRole("button",{name:"明确保留本稿并按已比较版本保存"}));await screen.findByText(/身份拒绝：原草稿仍保留/);
  expect(box).toHaveTextContent("我的独立原稿");expect(f.get().state.drafts["doc-a"]).toEqual({base_version:2,editor_json:editor("我的独立原稿")});
  expect(f.records.get("doc-a")?.version).toBe(2);
});

