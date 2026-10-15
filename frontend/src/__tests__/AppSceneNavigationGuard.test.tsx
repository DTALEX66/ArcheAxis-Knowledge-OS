import {act,fireEvent,render,screen,waitFor} from "@testing-library/react";
import {afterEach,beforeEach,expect,it,vi} from "vitest";
import {webcrypto} from "node:crypto";
import {getRecoveryStatus} from "../api/workspace";
import {verifyCanonicalCore} from "../api/core";
import {App} from "../app/App";
import type {WorkingRead,WorkingState} from "../presentation/coreWorkingState";
import {useState} from "react";
vi.mock("../spaces/CanonicalAiJourneySpace",()=>({CanonicalAiJourneySpace:({onOpenReceipts}:{onOpenReceipts:(id:string)=>void})=>{
  const [request,setRequest]=useState("frozen-request-exact");
  return <><input aria-label="SIMULATED retained machine request" value={request} onChange={event=>setRequest(event.target.value)}/><button onClick={()=>onOpenReceipts("task-exact")}>SIMULATED read journey receipt</button></>;
}}));
const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call,verifyCanonicalCore:vi.fn().mockResolvedValue({})}));
vi.mock("../api/workspace",async original=>({...await original<typeof import("../api/workspace")>(),getRecoveryStatus:vi.fn().mockResolvedValue({state:"ready",safe_mode:false,backend_available:true,message:"SIMULATED ready",backups:[],external_dev:false})}));
const empty=():WorkingState=>({drafts:{},opened_documents:[],active_document:null,page_id:null,pending_original:null});
let read:WorkingRead,release!:(value:WorkingRead)=>void;
beforeEach(()=>{vi.mocked(getRecoveryStatus).mockResolvedValue({state:"ready",safe_mode:false,backend_available:true,message:"SIMULATED ready",backups:[],external_dev:false});vi.mocked(verifyCanonicalCore).mockResolvedValue(undefined);vi.stubGlobal("crypto",webcrypto);window.__TAURI__={core:{invoke:vi.fn()}};window.location.hash="#page=03";bridge.call.mockReset();read={schema:"archeaxis.ui-working-state/v1",workspace_id:"a".repeat(32),restore_epoch:"initial",state_revision:0,state:empty(),draft_digests:{},pending_document_id:null,recovery_candidates:null,recovery_requires_confirmation:false};
bridge.call.mockImplementation(async(op:string,p:{body?:{state:WorkingState}}={})=>{if(op==="ui_state_read")return structuredClone(read);if(op==="ui_state_write")return new Promise<WorkingRead>(resolve=>{release=value=>resolve(value);read={...read,state_revision:read.state_revision+1,state:structuredClone(p.body!.state)};});if(op==="sources_list")return {sources:[]};if(op==="documents_list")return {documents:[],next_cursor:null,snapshot_count:0};return {};});});
afterEach(()=>{delete window.__TAURI__;vi.unstubAllGlobals();vi.restoreAllMocks();});
it("SIMULATED restore notice exposes separate machine and review candidates without dispatch",async()=>{
  read.recovery_requires_confirmation=true;read.recovery_candidates={...empty(),pending_machine:{machine:{journal_id:"machine",owner_knowledge_id:"k1",operation:"answer",origin_restore_epoch:"initial",body:{knowledge_id:"k1",question:"Synthetic retained request",max_tokens:2048,timeout_s:120,client_request_id:"machine"}}},pending_reviews:{event:{item_key:"item",client_event_id:"event",origin_restore_epoch:"initial",body:{item_key:"item",client_event_id:"event",answer:"Synthetic retained review",assessment_id:"assessment",knowledge_version:"v1",correct:true,rating:3}}}};
  render(<App/>);
  await screen.findByText(/0 份独立草稿、0 个转换请求、1 个机器请求及 1 个复习请求/);
  expect(screen.getByRole("button",{name:"保留恢复候选"})).toBeEnabled();
  expect(screen.getByRole("button",{name:"丢弃恢复候选"})).toBeDisabled();
  expect(bridge.call.mock.calls.every(([op])=>op!=="machine_answer"&&op!=="machine_retest"&&op!=="learning_review"&&op!=="ui_state_recover")).toBe(true);
});
it("SIMULATED App guards leaving when only a frozen review is pending",async()=>{
  read.state.pending_reviews={event:{item_key:"item",client_event_id:"event",origin_restore_epoch:"initial",body:{item_key:"item",client_event_id:"event",answer:"retained",assessment_id:"assessment",knowledge_version:"v1",correct:true,rating:3}}};
  const confirm=vi.spyOn(window,"confirm").mockReturnValue(false);render(<App/>);
  await waitFor(()=>expect(bridge.call.mock.calls.some(([op])=>op==="ui_state_write")).toBe(true));
  confirm.mockClear();
  fireEvent.click(document.querySelector('.navigation-sidebar button[data-page-id="02"]')!);
  expect(confirm).toHaveBeenCalledTimes(1);expect(window.location.hash).toBe("#page=03");
});
it("SIMULATED App guards an unsubmitted learning draft even outside the learning page",async()=>{
  read.state.learning_drafts={assessment:{item_key:"item",assessment_id:"assessment",knowledge_version:"v1",answer:"retained learning answer",checked_correct:null,rating:null,answer_revealed:false}};
  const confirm=vi.spyOn(window,"confirm").mockReturnValue(false);render(<App/>);
  await waitFor(()=>expect(bridge.call.mock.calls.some(([op])=>op==="ui_state_write")).toBe(true));confirm.mockClear();
  fireEvent.click(document.querySelector('.navigation-sidebar button[data-page-id="02"]')!);
  expect(confirm).toHaveBeenCalledTimes(1);expect(window.location.hash).toBe("#page=03");
});
it("SIMULATED restore notice lists learning drafts without applying or submitting them",async()=>{
  read.recovery_requires_confirmation=true;read.recovery_candidates={...empty(),learning_drafts:{assessment:{item_key:"retained-item",assessment_id:"assessment",knowledge_version:"v1",answer:"answer",checked_correct:null,rating:null,answer_revealed:false}}};
  render(<App/>);await screen.findByText("另有 1 份未提交学习草稿。");expect(screen.getByText("retained-item · v1")).toBeInTheDocument();
  expect(bridge.call.mock.calls.some(([op])=>op==="learning_review"||op==="ui_state_recover")).toBe(false);
});
it("SIMULATED mounted App retains a dirty AI journey across receipt panels and still guards leaving",async()=>{
  window.location.hash="#page=14";read.state.page_id="14";
  const confirm=vi.spyOn(window,"confirm").mockReturnValue(false);
  render(<App/>);
  const request=await screen.findByLabelText("SIMULATED retained machine request");
  fireEvent.change(request,{target:{value:"uncertain-request-retained"}});
  act(()=>window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner:"machine-answer",dirty:true}})));
  confirm.mockClear();
  fireEvent.click(screen.getByRole("button",{name:"SIMULATED read journey receipt"}));
  await waitFor(()=>expect(window.location.hash).toBe("#page=22"));
  expect(confirm).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button",{name:"返回同一纠正与复测旅程"}));
  await waitFor(()=>expect(window.location.hash).toBe("#page=14"));
  expect(screen.getByLabelText("SIMULATED retained machine request")).toBe(request);
  expect(request).toHaveValue("uncertain-request-retained");
  act(()=>{window.history.replaceState(null,"","/#page=22");window.dispatchEvent(new HashChangeEvent("hashchange"));});
  await screen.findByRole("button",{name:"返回同一纠正与复测旅程"});
  expect(confirm).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button",{name:"返回同一纠正与复测旅程"}));
  expect(request).toHaveValue("uncertain-request-retained");
  fireEvent.click(document.querySelector('.navigation-sidebar button[data-page-id="02"]')!);
  expect(confirm).toHaveBeenCalledTimes(1);
  expect(window.location.hash).toBe("#page=14");
});
it("SIMULATED mounted App with real CoreWorkingStateSession navigates while only scene CAS ACK is pending",async()=>{const confirm=vi.spyOn(window,"confirm").mockReturnValue(false);render(<App/>);await waitFor(()=>expect(bridge.call.mock.calls.some(([op])=>op==="ui_state_write")).toBe(true));expect(read.state.drafts).toEqual({});expect(read.state.pending_original).toBeNull();fireEvent.click(document.querySelector('.navigation-sidebar button[data-page-id="02"]')!);await waitFor(()=>expect(window.location.hash).toBe("#page=02"));expect(confirm).not.toHaveBeenCalled();await act(async()=>release(structuredClone(read)));});
it.each(["draft","pending original","editor event"])("SIMULATED mounted App still protects actual %s during navigation",async(kind)=>{window.location.hash="#page=19";read.state.page_id="19";if(kind==="draft"){read.state.drafts["doc-exact"]={base_version:1,editor_json:{type:"doc",content:[{type:"paragraph",content:[{type:"text",text:"保留"}]}]}};read.draft_digests["doc-exact"]="b".repeat(64);}if(kind==="pending original"){read.state.pending_original={create_request_id:"request-exact",title:"保留笔记",editor_json:{type:"doc",content:[]}};read.pending_document_id="doc_req_"+"b".repeat(64);}const confirm=vi.spyOn(window,"confirm").mockReturnValue(false);render(<App/>);await screen.findByRole("heading",{name:"本地工作区与恢复"});if(kind==="editor event")act(()=>window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner:"actual-editor",dirty:true}})));confirm.mockClear();fireEvent.click(document.querySelector('.navigation-sidebar button[data-page-id="02"]')!);expect(confirm).toHaveBeenCalledTimes(1);expect(window.location.hash).toBe("#page=19");});

it("SIMULATED scene-only unknown ACK retains journal error without claiming a content draft",async()=>{const original=bridge.call.getMockImplementation()!;bridge.call.mockImplementation(async(op,p)=>{if(op==="ui_state_write")throw new Error("SIMULATED scene ACK lost");return original(op,p);});const confirm=vi.spyOn(window,"confirm").mockReturnValue(false);render(<App/>);await screen.findByText("SIMULATED scene ACK lost");fireEvent.click(document.querySelector('.navigation-sidebar button[data-page-id="02"]')!);await waitFor(()=>expect(window.location.hash).toBe("#page=02"));expect(confirm).not.toHaveBeenCalled();expect(screen.getByText("SIMULATED scene ACK lost")).toBeInTheDocument();});

it.each([false,true])("SIMULATED hydrated same-page click normalizes an empty URL with retained draft=%s",async(withDraft)=>{
  window.history.replaceState(null,"","/");
  read.state.page_id="19";
  if(withDraft){read.state.drafts["doc-exact"]={base_version:1,editor_json:{type:"doc",content:[]}};read.draft_digests["doc-exact"]="b".repeat(64);}
  const confirm=vi.spyOn(window,"confirm").mockReturnValue(false);
  render(<App/>);
  await screen.findByRole("heading",{name:"本地工作区与恢复"});
  expect(window.location.hash).toBe("");
  const writes=bridge.call.mock.calls.filter(([op])=>op==="ui_state_write").length;
  const retained=structuredClone(read.state.drafts);
  confirm.mockClear();
  fireEvent.click(document.querySelector('.navigation-sidebar button[data-page-id="19"]')!);
  expect(window.location.hash).toBe("#page=19");
  expect(confirm).not.toHaveBeenCalled();
  expect(read.state.drafts).toEqual(retained);
  expect(bridge.call.mock.calls.filter(([op])=>op==="ui_state_write")).toHaveLength(writes);
});
