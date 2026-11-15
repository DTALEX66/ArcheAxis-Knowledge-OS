import { createHash, webcrypto } from "node:crypto";
import { beforeEach, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ApiError } from "../api/client";
import type { DocumentDto } from "../api/generated/core-contract";
import { DeepTutorJourneySession, journeyEditor, journeyIdentity, snapshot } from "../presentation/deepTutorJourney";
import { DeepTutorLearningPanel } from "../components/DeepTutorLearningPanel";

const bridge=vi.hoisted(()=>({call:vi.fn(),working:null as any}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
vi.mock("../presentation/useCoreWorkingState",()=>({useOptionalCoreWorkingState:()=>bridge.working}));
const hash=(text:string)=>createHash("sha256").update(text).digest("hex");
const proof=(value:unknown)=>hash(JSON.stringify(value,(_key,item)=>item&&typeof item==="object"&&!Array.isArray(item)?Object.fromEntries(Object.entries(item).sort(([a],[b])=>a<b?-1:a>b?1:0)):item));
const scope={workspace_id:"cancel_workspace",restore_epoch:"cancel_epoch"};
const material:DocumentDto={document_id:"cancel_material",version:1,content_sha256:"a".repeat(64),source_id:null,source_revision:null,title:"取消练习",editor_json:{type:"doc",content:[]},text_projection:"材料",blocks:[]};
const request={create_request_id:"cancel_request",material:snapshot(material),requirement:"保持原目标",model:null};
const resultId=(id:string)=>`doc_req_${hash(`deeptutor_question_turn_${hash(id)}`)}`;
const doc=(id:string,editor:unknown,version=1):DocumentDto=>({...material,document_id:id,version,editor_json:structuredClone(editor),content_sha256:hash(JSON.stringify(editor))});
function status(body=request,state="UNKNOWN") {return {request_id:body.create_request_id,request_sha256:proof(body),state,
  result_document_id:state==="COMPLETED"?resultId(body.create_request_id):null,result_version:state==="COMPLETED"?1:null,
  result_content_sha256:state==="COMPLETED"?"b".repeat(64):null,current_invocation:{worker_invoked:false,model_invoked:false}};}
let docs:Map<string,DocumentDto>;
let cancelPatch:Record<string,unknown>;
let readState:string;
let dispatched:typeof request;
let holdGeneration:((reason:unknown)=>void)|undefined;
async function transport(op:string,p:any={}){
  if(op==="document_get"||op==="document_version") {const d=docs.get(p.document_id);if(!d)throw new ApiError(404,"missing");return structuredClone(d);}
  if(op==="document_create"||op==="document_draft"){
    const id=op==="document_create"?(await journeyIdentity(snapshot(material),scope)).document_id:p.document_id;
    const old=docs.get(id);if(op==="document_draft"&&p.body.expected_version!==old?.version)throw new ApiError(409,"conflict");
    const saved=doc(id,p.body.editor_json,(old?.version??0)+1);docs.set(id,saved);return structuredClone(saved);
  }
  if(op==="learning_deeptutor_question_turn"){dispatched=structuredClone(p.body);return new Promise((_resolve,reject)=>{holdGeneration=reject;});}
  if(op==="learning_deeptutor_question_turn_cancel")return {...status(p.body,readState),cancel_requested:readState==="UNKNOWN",provider_stop_state:"UNKNOWN",...cancelPatch};
  if(op==="learning_deeptutor_question_turn_status")return status(p.body,readState);
  throw new Error(`unconfigured ${op}`);
}
async function fixture(pending=true){
  const session=new DeepTutorJourneySession(snapshot(material),scope,bridge.call);
  session.value.purpose=request.requirement;session.value.material_grant={document_id:"material_grant",version:1,content_sha256:"c".repeat(64)};
  if(pending)session.value.pending={kind:"generate",operation:"learning_deeptutor_question_turn",payload:{body:structuredClone(request)},document_id:resultId(request.create_request_id)};
  const id=(await journeyIdentity(snapshot(material),scope)).document_id;docs.set(id,doc(id,journeyEditor(session.value)));await session.load();bridge.call.mockClear();return session;
}
beforeEach(()=>{
  vi.stubGlobal("crypto",webcrypto);docs=new Map([[material.document_id,material]]);cancelPatch={};readState="UNKNOWN";dispatched=request;holdGeneration=undefined;
  bridge.call.mockReset().mockImplementation(transport);
  bridge.working={server:{...scope,recovery_requires_confirmation:false},status:"ready",state:{drafts:{}},session:{
    getSnapshot:()=>bridge.working,rememberDraft:vi.fn((id,editor,base_version)=>{bridge.working.state.drafts[id]={editor_json:structuredClone(editor),base_version};}),flush:vi.fn().mockResolvedValue(undefined),
    clearSaved:vi.fn(async(id:string,_draft:unknown,_version:number)=>{delete bridge.working.state.drafts[id];return true;})}};
});

it("cancels only the frozen original and keeps unknown requests without saving or replaying",async()=>{
  const session=await fixture(),pending=structuredClone(session.value.pending);
  session.value.purpose="界面后来输入的目标";
  const receipt=await session.cancelGeneration();expect(receipt.cancel_requested).toBe(true);expect(receipt.provider_stop_state).toBe("UNKNOWN");
  expect(session.value.pending).toEqual(pending);expect(session.value.purpose).toBe("界面后来输入的目标");expect(session.canStartNewRound).toBe(false);
  expect(bridge.call.mock.calls).toEqual([["learning_deeptutor_question_turn_cancel",{body:request}],["learning_deeptutor_question_turn_status",{body:request}]]);
});
it("refuses a locally corrupted material binding before sending a cancel",async()=>{
  const session=await fixture();(session.value.pending!.payload.body as typeof request).material.document_id="different_material";
  await expect(session.cancelGeneration()).rejects.toThrow("当前材料或结果身份不符");expect(bridge.call).not.toHaveBeenCalled();expect(session.value.pending).toBeDefined();
});
it("does not dispatch an old cancellation after the workspace changes during identity hashing",async()=>{
  const session=await fixture(),digest=webcrypto.subtle.digest.bind(webcrypto.subtle);
  let release!:()=>void;const gate=new Promise<void>(resolve=>{release=resolve;});
  const spy=vi.spyOn(webcrypto.subtle,"digest").mockImplementationOnce(async(algorithm,data)=>{await gate;return digest(algorithm,data);});
  try{
    const pending=session.cancelGeneration();await waitFor(()=>expect(spy).toHaveBeenCalled());session.deactivate();release();
    await expect(pending).rejects.toThrow("材料或工作区已切换");expect(bridge.call).not.toHaveBeenCalled();
  }finally{spy.mockRestore();}
});
it.each([{request_sha256:"d".repeat(64)},{provider_stop_state:"STOPPED"},{cancel_requested:false}])("rejects an unbound or overclaimed cancellation receipt %j",async patch=>{
  const session=await fixture();cancelPatch=patch;
  await expect(session.cancelGeneration()).rejects.toThrow();expect(session.value.pending).toBeDefined();expect(session.canStartNewRound).toBe(false);
  expect(bridge.call.mock.calls).toHaveLength(1);
});
it("completion wins without deleting or automatically adopting the completed request",async()=>{
  const session=await fixture();readState="COMPLETED";
  const receipt=await session.cancelGeneration();expect(receipt.cancel_requested).toBe(false);expect(session.recoveryState).toBe("available");
  expect(session.value.pending).toBeDefined();expect(session.value.candidate).toBeUndefined();expect(bridge.call.mock.calls.map(([op])=>op)).toEqual(["learning_deeptutor_question_turn_cancel","learning_deeptutor_question_turn_status"]);
});
it("ignores a late cancellation receipt after the original session is deactivated",async()=>{
  const session=await fixture();let complete!:(v:unknown)=>void;
  bridge.call.mockImplementation((op,p)=>op==="learning_deeptutor_question_turn_cancel"?new Promise(resolve=>{complete=resolve;}):transport(op,p));
  const pending=session.cancelGeneration();await waitFor(()=>expect(complete).toBeDefined());session.deactivate();
  complete({...status(),cancel_requested:true,provider_stop_state:"UNKNOWN"});
  await expect(pending).rejects.toThrow("材料或工作区已切换");
  expect(bridge.call.mock.calls.map(([op])=>op)).toEqual(["learning_deeptutor_question_turn_cancel"]);expect(session.value.pending).toBeDefined();
});
it("lets the original generation finish when commit wins the concurrent cancellation without replay or stale recovery state",async()=>{
  const session=await fixture(false);let finish!:(v:unknown)=>void;let result:DocumentDto|undefined;
  bridge.call.mockImplementation(async(op,p)=>{
    if(op==="learning_deeptutor_question_turn"){dispatched=structuredClone(p.body);return new Promise(resolve=>{finish=resolve;});}
    if(op==="learning_deeptutor_question_turn_cancel"){
      result=doc(resultId(dispatched.create_request_id),{type:"doc",content:[],attrs:{archeaxis_deeptutor_question_turn_candidate:{
        schema:"archeaxis.deeptutor-question-turn-document/v1",create_request_id:dispatched.create_request_id,material:dispatched.material,
        request_frame:dispatched,generation_request_sha256:proof(dispatched),question:{question_id:"q",question:"依据是什么？",question_type:"choice",options:{A:"一",B:"二"}}}}});
      docs.set(result.document_id,result);
      return {...status(dispatched,"COMPLETED"),result_content_sha256:result.content_sha256,cancel_requested:false,provider_stop_state:"UNKNOWN"};
    }
    if(op==="learning_deeptutor_question_turn_status")return {...status(dispatched,"COMPLETED"),result_content_sha256:result!.content_sha256};
    return transport(op,p);
  });
  const generation=session.act("generate");await waitFor(()=>expect(finish).toBeDefined());
  expect((await session.cancelGeneration()).cancel_requested).toBe(false);expect(session.value.pending).toBeDefined();
  finish({document:result});await generation;
  expect(session.value.candidate).toEqual(snapshot(result!));expect(session.value.pending).toBeUndefined();expect(session.recoveryState).toBeNull();
  expect(bridge.call.mock.calls.filter(([op])=>op==="learning_deeptutor_question_turn")).toHaveLength(1);
});
it("NOT_FOUND and a lost cancellation response never permit replacement requests",async()=>{
  const session=await fixture();readState="NOT_FOUND";expect((await session.cancelGeneration()).cancel_requested).toBe(false);
  expect(session.canStartNewRound).toBe(false);
  bridge.call.mockImplementation(async(op,p)=>{if(op==="learning_deeptutor_question_turn_cancel")throw new ApiError(0,"lost cancel ack");return transport(op,p);});
  await expect(session.cancelGeneration()).rejects.toThrow("lost cancel ack");expect(session.value.pending).toBeDefined();
  await expect(session.newRound()).rejects.toThrow("不能换编号");expect(bridge.call.mock.calls.some(([op])=>op==="learning_deeptutor_question_turn")).toBe(false);
});
it("keeps the cancel button usable while generation is held, then queries without releasing the original ID",async()=>{
  await fixture(false);render(<DeepTutorLearningPanel document={material}/>);
  const generate=screen.getByRole("button",{name:"生成一道题目候选"});await waitFor(()=>expect(generate).toBeEnabled());fireEvent.click(generate);
  const cancel=await screen.findByRole("button",{name:"取消本次生成"});await waitFor(()=>expect(cancel).toBeEnabled());
  expect(holdGeneration).toBeDefined();fireEvent.click(cancel);
  expect(await screen.findByText(/已禁止此请求后续发布/)).toBeVisible();
  expect(screen.getByRole("button",{name:"查询原请求与已保存记录"})).toBeDisabled();
  expect(bridge.call).toHaveBeenCalledWith("learning_deeptutor_question_turn_cancel",{body:dispatched});
  holdGeneration!(new ApiError(409,"generation cancelled; original unresolved"));
  await waitFor(()=>expect(screen.getByRole("button",{name:"查询原请求与已保存记录"})).toBeEnabled());
  expect(bridge.call.mock.calls.filter(([op])=>op==="learning_deeptutor_question_turn")).toHaveLength(1);
  const journal=docs.get((await journeyIdentity(snapshot(material),scope)).document_id)!;
  expect((journal.editor_json as any).attrs.archeaxis_deeptutor_journey.pending.payload.body).toEqual(dispatched);
  expect(screen.getByRole("button",{name:"保留历史并开始新一轮"})).toBeDisabled();
});
