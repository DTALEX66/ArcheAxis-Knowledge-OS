import { createHash, webcrypto } from "node:crypto";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { DocumentDto } from "../api/generated/core-contract";
import { ApiError } from "../api/client";
const mock=vi.hoisted(()=>({call:vi.fn(),working:null as any,download:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:mock.call}));
vi.mock("../presentation/useCoreWorkingState",()=>({useOptionalCoreWorkingState:()=>mock.working}));
vi.mock("../presentation/exchangeProof",async importOriginal=>({...await importOriginal<typeof import("../presentation/exchangeProof")>(),downloadBytes:mock.download}));
import { DeepTutorLearningPanel } from "../components/DeepTutorLearningPanel";
import { DeepTutorJourneySession, journeyEditor, journeyIdentity, snapshot } from "../presentation/deepTutorJourney";

const hash=(text:string)=>createHash("sha256").update(text,"utf8").digest("hex");
const proof=(value:unknown)=>hash(JSON.stringify(value,(_key,item)=>item&&typeof item==="object"&&!Array.isArray(item)?Object.fromEntries(Object.entries(item).sort(([a],[b])=>a<b?-1:a>b?1:0)):item));
const clone=<T,>(value:T):T=>JSON.parse(JSON.stringify(value));
const material:DocumentDto={document_id:"doc_recovery_material",version:1,content_sha256:"a".repeat(64),source_id:null,source_revision:null,title:"恢复练习材料",editor_json:{type:"doc",content:[]},text_projection:"材料",blocks:[]};
const scope={workspace_id:"workspace_recovery",restore_epoch:"epoch_recovery"};
const request={create_request_id:"original_request",material:snapshot(material),requirement:"原学习目标",model:null};
const candidateId=(id:string)=>`doc_req_${hash(`deeptutor_question_turn_${hash(id)}`)}`;
const resultId=candidateId(request.create_request_id);
const question={question_id:"q_recovered",question:"原材料的问题",question_type:"choice",options:{A:"一",B:"二",C:"三",D:"四"}};
type State="NOT_FOUND"|"DISPATCHED"|"FAILED"|"UNKNOWN"|"COMPLETED";
let state:State, statusPatch:Record<string,unknown>, statusError:Error|undefined, hideLatest:boolean;
let docs:Map<string,DocumentDto>, fixedDocs:Map<string,DocumentDto>, writes:DocumentDto[];
const doc=(id:string,editor:unknown,version=1):DocumentDto=>({...material,document_id:id,version,editor_json:clone(editor),content_sha256:hash(JSON.stringify(editor))});
function candidate(body:typeof request=request){return doc(candidateId(body.create_request_id),{type:"doc",content:[],attrs:{archeaxis_deeptutor_question_turn_candidate:{schema:"archeaxis.deeptutor-question-turn-document/v1",create_request_id:body.create_request_id,generation_request_sha256:proof(body),request_frame:body,material:body.material,question}}});}
async function transport(operation:string,payload:any={}){
  if(operation==="document_get"){
    if(hideLatest&&payload.document_id===resultId)throw new ApiError(404,"missing");
    const saved=docs.get(payload.document_id);if(!saved)throw new ApiError(404,"missing");return clone(saved);
  }
  if(operation==="document_version"){
    const saved=fixedDocs.get(payload.document_id);if(!saved||saved.version!==payload.version)throw new ApiError(404,"missing version");return clone(saved);
  }
  if(operation==="learning_deeptutor_question_turn_status"){
    if(statusError)throw statusError;
    const result=state==="COMPLETED"?fixedDocs.get(resultId)!:null;
    return {request_id:request.create_request_id,request_sha256:proof(request),state,result_document_id:result?.document_id??null,result_version:result?.version??null,result_content_sha256:result?.content_sha256??null,current_invocation:{worker_invoked:false,model_invoked:false},...statusPatch};
  }
  if(operation==="document_create"||operation==="document_draft"){
    const body=payload.body,id=operation==="document_create"?`doc_req_${hash(body.create_request_id)}`:payload.document_id,previous=docs.get(id);
    if(operation==="document_draft"&&previous?.version!==body.expected_version)throw new ApiError(409,"write conflict");
    const saved=doc(id,body.editor_json,(previous?.version??0)+1);docs.set(id,saved);writes.push(clone(saved));return clone(saved);
  }
  if(operation==="learning_deeptutor_question_turn"){
    const saved=candidate(payload.body);docs.set(saved.document_id,saved);fixedDocs.set(saved.document_id,saved);return {document:clone(saved)};
  }
  throw new Error("Unexpected operation "+operation);
}
async function fixture(){
  const session=new DeepTutorJourneySession(snapshot(material),scope,mock.call);
  session.value.purpose=request.requirement;session.value.material_grant={document_id:"doc_material_grant",version:1,content_sha256:"b".repeat(64)};
  session.value.pending={kind:"generate",operation:"learning_deeptutor_question_turn",payload:{body:clone(request)},document_id:resultId};
  const identity=await journeyIdentity(snapshot(material),scope);const journal=doc(identity.document_id,journeyEditor(session.value));docs.set(journal.document_id,journal);await session.load();
  return session;
}
beforeEach(()=>{
  vi.stubGlobal("crypto",webcrypto);state="UNKNOWN";statusPatch={};statusError=undefined;hideLatest=false;docs=new Map([[material.document_id,clone(material)]]);fixedDocs=new Map();writes=[];
  mock.call.mockReset().mockImplementation(transport);mock.download.mockReset();
  mock.working={server:{...scope,recovery_requires_confirmation:false},status:"ready",state:{drafts:{}},session:{getSnapshot:()=>mock.working,rememberDraft:vi.fn((id,editor,base)=>{mock.working.state.drafts[id]={base_version:base,editor_json:clone(editor)};}),flush:vi.fn().mockResolvedValue(undefined),clearSaved:vi.fn(async(id:string,sent:any,version:number)=>{
    if(version!==sent.base_version+1||JSON.stringify(sent.editor_json)!==JSON.stringify(docs.get(id)!.editor_json))throw new Error("invalid exact draft clear");delete mock.working.state.drafts[id];return true;
  })}};
});

describe("new user-visible original-request recovery",()=>{
  it.each<State>(["NOT_FOUND","DISPATCHED","UNKNOWN"])("keeps %s unresolved and never substitutes a new request ID",async status=>{
    const session=await fixture(),pending=clone(session.value.pending);state=status;mock.call.mockClear();
    await session.recover();expect(session.recoveryState).toBe(status.toLowerCase());expect(session.value.pending).toEqual(pending);
    await expect(session.newRound()).rejects.toThrow("不能换编号");expect(writes).toHaveLength(0);
    expect(mock.call.mock.calls.map(([op])=>op)).toEqual(["document_get","learning_deeptutor_question_turn_status"]);
  });
  it("rejects a status bound to another request hash before adopting or closing anything",async()=>{
    const session=await fixture();statusPatch={request_sha256:"0".repeat(64)};
    await expect(session.recover()).rejects.toThrow("未绑定本次冻结请求");expect(session.recoveryState).toBe("conflict");expect(session.unresolved).toBe(true);expect(writes).toHaveLength(0);
  });
  it("recovers a completed fixed snapshot through read-only status and version read",async()=>{
    const session=await fixture(),saved=candidate();fixedDocs.set(resultId,saved);hideLatest=true;state="COMPLETED";
    await session.recover();expect(session.value.candidate).toEqual(snapshot(saved));expect(session.recoveryState).toBe("completed");
    expect(mock.call).toHaveBeenCalledWith("document_version",{document_id:resultId,version:1});expect(mock.call.mock.calls.some(([op])=>op==="learning_deeptutor_question_turn")).toBe(false);
  });
  it("refuses a completed snapshot whose content digest differs from the version read",async()=>{
    const session=await fixture();fixedDocs.set(resultId,candidate());state="COMPLETED";hideLatest=true;statusPatch={result_content_sha256:"f".repeat(64)};
    await expect(session.recover()).rejects.toThrow("结果版本不符");expect(session.value.candidate).toBeUndefined();expect(session.value.pending).toBeDefined();expect(writes).toHaveLength(0);
  });
  it("recovers the original candidate version when its current document was later edited",async()=>{
    const session=await fixture(),saved=candidate();fixedDocs.set(resultId,saved);docs.set(resultId,{...saved,version:2,content_sha256:"c".repeat(64),editor_json:{type:"doc",content:[]}});
    await session.recover();expect(session.value.candidate).toEqual(snapshot(saved));expect(mock.call).toHaveBeenCalledWith("document_version",{document_id:resultId,version:1});
  });
  it("reopens a recovered historical candidate without replacing its fixed version",async()=>{
    const session=await fixture(),saved=candidate();fixedDocs.set(resultId,saved);docs.set(resultId,{...saved,version:2,content_sha256:"c".repeat(64),editor_json:{type:"doc",content:[]}});
    await session.recover();mock.call.mockClear();
    const reopened=new DeepTutorJourneySession(snapshot(material),scope,mock.call);await reopened.load();
    expect(reopened.value.candidate).toEqual(snapshot(saved));expect(reopened.candidate).toEqual(question);
    expect(mock.call).toHaveBeenCalledWith("document_version",{document_id:resultId,version:1});
    expect(mock.call.mock.calls.some(([op])=>op==="learning_deeptutor_question_turn")).toBe(false);
  });
  it("reopens a fixed feedback version and refuses a different historical digest",async()=>{
    const session=await fixture(),guidance={teaching_observations:[{text:"已保存的本人反馈"}]};
    const saved=doc("doc_fixed_feedback",{type:"doc",content:[],attrs:{archeaxis_deeptutor_teaching_feedback_candidate:{schema:"archeaxis.deeptutor-teaching-feedback-document/v1",guidance}}});
    delete session.value.pending;session.value.feedback=snapshot(saved);await session.save();
    fixedDocs.set(saved.document_id,saved);docs.set(saved.document_id,{...saved,version:2,content_sha256:"d".repeat(64),editor_json:{type:"doc",content:[]}});
    const reopened=new DeepTutorJourneySession(snapshot(material),scope,mock.call);await reopened.load();
    expect(reopened.value.feedback).toEqual(snapshot(saved));expect(reopened.guidance).toEqual(guidance);
    fixedDocs.set(saved.document_id,{...saved,content_sha256:"e".repeat(64)});
    await expect(reopened.load()).rejects.toThrow("固定版本校验不符");expect(reopened.value.feedback).toEqual(snapshot(saved));expect(reopened.guidance).toBeNull();
  });
  it("closes only a rechecked FAILED request and retains it before an explicit new generation",async()=>{
    const session=await fixture();state="FAILED";await session.recover();expect(session.canStartNewRound).toBe(false);
    await session.closeFailedRequest();expect(session.recoveryState).toBe("closed_failed");expect(session.value.closed_requests?.[0].request.payload.body).toEqual(request);
    expect(mock.call.mock.calls.filter(([op])=>op==="learning_deeptutor_question_turn_status")).toHaveLength(2);
    expect(mock.call.mock.calls.some(([op])=>op==="learning_deeptutor_question_turn")).toBe(false);
    session.value.purpose="明确的新目标";await session.act("generate");
    const generated=mock.call.mock.calls.find(([op])=>op==="learning_deeptutor_question_turn")![1].body;
    expect(generated.create_request_id).not.toBe(request.create_request_id);expect(generated.requirement).toBe("明确的新目标");
  });
  it("does not close when the fresh status no longer confirms failure",async()=>{
    const session=await fixture();state="FAILED";await session.recover();state="UNKNOWN";
    await expect(session.closeFailedRequest()).rejects.toThrow("尚未确认失败");expect(session.value.pending).toBeDefined();expect(session.value.closed_requests).toBeUndefined();expect(writes).toHaveLength(0);
  });
  it("preserves unknown state and input across a lookup outage",async()=>{
    const session=await fixture();statusError=new ApiError(0,"offline");await expect(session.recover()).rejects.toThrow("offline");
    expect(session.recoveryState).toBe("unavailable");expect(session.value.purpose).toBe(request.requirement);await expect(session.newRound()).rejects.toThrow();expect(writes).toHaveLength(0);
  });
  it("shows unknown recovery, disables bypass and exports the frozen local record",async()=>{
    await fixture();render(<DeepTutorLearningPanel document={material}/>);
    await waitFor(()=>expect(screen.getByRole("button",{name:"查询原请求与已保存记录"})).toBeEnabled());
    fireEvent.click(screen.getByRole("button",{name:"查询原请求与已保存记录"}));await screen.findByRole("heading",{name:"原请求执行结果未知"});
    expect(screen.getByRole("button",{name:"保留历史并开始新一轮"})).toBeDisabled();expect(screen.getByLabelText("本次学习目标")).toBeDisabled();
    fireEvent.click(screen.getByRole("button",{name:"保全恢复记录到文件"}));
    const saved=JSON.parse(mock.download.mock.calls[0][0]);expect(saved.journey.pending.payload.body).toEqual(request);expect(saved.material).toEqual(snapshot(material));
    expect(mock.call.mock.calls.some(([op])=>op==="learning_deeptutor_question_turn")).toBe(false);
  });
  it("makes failed closure explicit and labels any subsequent generation as a new task",async()=>{
    await fixture();state="FAILED";render(<DeepTutorLearningPanel document={material}/>);
    await waitFor(()=>expect(screen.getByRole("button",{name:"查询原请求与已保存记录"})).toBeEnabled());fireEvent.click(screen.getByRole("button",{name:"查询原请求与已保存记录"}));
    const close=await screen.findByRole("button",{name:"保留失败记录并结束本次任务"});await waitFor(()=>expect(close).toBeEnabled());fireEvent.click(close);
    await screen.findByRole("heading",{name:"已保留并结束本次失败记录"});expect(screen.getByLabelText("本次学习目标")).toBeEnabled();
    expect(screen.getByRole("button",{name:"开始新任务并重新生成题目"})).toBeEnabled();expect(mock.call.mock.calls.some(([op])=>op==="learning_deeptutor_question_turn")).toBe(false);
  });
  it("reopens a legacy unknown request without dropping the current draft or dispatching it",async()=>{
    const session=await fixture(),pending=clone(session.value.pending!);delete session.value.pending;session.value.unknown_requests=[pending];session.value.purpose="应保全的当前草稿";
    await session.resumeHistoricalRequest(0);expect(session.value.pending).toEqual(pending);expect(session.value.unknown_requests).toHaveLength(0);
    expect((writes[0].editor_json as any).attrs.archeaxis_deeptutor_journey.purpose).toBe("应保全的当前草稿");
    expect(mock.call.mock.calls.some(([op])=>op==="learning_deeptutor_question_turn")).toBe(false);
  });
  it("requires a fresh human answer review after selecting a different historical candidate",async()=>{
    const session=await fixture(),pending=clone(session.value.pending!),original=candidate();
    const other=candidate({...request,create_request_id:"other_request",requirement:"另一个目标"});
    docs.set(original.document_id,original);fixedDocs.set(original.document_id,original);docs.set(other.document_id,other);fixedDocs.set(other.document_id,other);
    delete session.value.pending;session.value.unknown_requests=[pending];session.value.candidate=snapshot(other);session.value.purpose="另一个目标";
    session.value.correct_answer="A";session.value.explanation="上一题人工解释";await session.save();writes=[];
    render(<DeepTutorLearningPanel document={material}/>);
    const review=await screen.findByRole("checkbox",{name:"我已核对题目和答案，作为人工声明的答案键保存"});await waitFor(()=>expect(review).toBeEnabled());
    fireEvent.click(review);expect(review).toBeChecked();fireEvent.click(screen.getByRole("button",{name:"接回第 1 个历史请求并查询"}));
    await screen.findByRole("heading",{name:"已按原请求恢复保存结果"});
    await waitFor(()=>expect(screen.getByRole("checkbox",{name:"我已核对题目和答案，作为人工声明的答案键保存"})).not.toBeChecked());
    expect(screen.getByLabelText("你确认的正确选项")).toHaveValue("");expect(screen.getByLabelText("你核对后的解释")).toHaveValue("");
    expect(screen.getByRole("button",{name:"接纳为练习题"})).toBeDisabled();
    const kept=(writes[0].editor_json as any).attrs.archeaxis_deeptutor_journey;expect(kept.correct_answer).toBe("A");expect(kept.explanation).toBe("上一题人工解释");
    expect(mock.call.mock.calls.some(([op])=>op==="learning_deeptutor_question_turn"||op==="learning_deeptutor_question_accept")).toBe(false);
  });
  it("waits for the initial journal read before enabling original-request recovery",async()=>{
    const session=await fixture();let finishRead!:()=>void;
    const held=new Promise<void>(resolve=>{finishRead=resolve;});let initial=true;
    mock.call.mockClear().mockImplementation(async(op,payload)=>{
      if(initial&&op==="document_get"&&payload.document_id===session.document!.document_id){initial=false;await held;}
      return transport(op,payload);
    });
    render(<DeepTutorLearningPanel document={material}/>);
    const query=screen.getByRole("button",{name:"查询原请求与已保存记录"});expect(query).toBeDisabled();
    fireEvent.click(query);expect(mock.call.mock.calls.some(([op])=>op==="learning_deeptutor_question_turn_status")).toBe(false);
    await act(async()=>{finishRead();});await waitFor(()=>expect(query).toBeEnabled());
    fireEvent.click(query);await screen.findByRole("heading",{name:"原请求执行结果未知"});
    expect(mock.call.mock.calls.filter(([op])=>op==="learning_deeptutor_question_turn_status")).toHaveLength(1);
    expect(mock.call.mock.calls.some(([op])=>op==="learning_deeptutor_question_turn")).toBe(false);
  });
  it("re-enables read-only recovery after an initial journal failure without enabling generation",async()=>{
    await fixture();mock.call.mockRejectedValueOnce(new ApiError(503,"initial offline"));render(<DeepTutorLearningPanel document={material}/>);
    await screen.findByText("initial offline");const query=screen.getByRole("button",{name:"查询原请求与已保存记录"});
    await waitFor(()=>expect(query).toBeEnabled());expect(screen.getByRole("button",{name:"生成一道题目候选"})).toBeDisabled();
    fireEvent.click(query);await screen.findByRole("heading",{name:"原请求结果尚未确认"});
    await waitFor(()=>expect(query).toBeEnabled());expect(screen.getByRole("button",{name:"生成一道题目候选"})).toBeDisabled();
    fireEvent.click(query);await screen.findByRole("heading",{name:"原请求执行结果未知"});
    expect(mock.call.mock.calls.some(([op])=>op==="learning_deeptutor_question_turn")).toBe(false);
  });
});
