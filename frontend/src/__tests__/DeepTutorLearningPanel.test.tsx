import { webcrypto } from "node:crypto";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ApiError } from "../api/client";
import type { DocumentDto } from "../api/generated/core-contract";
const mock = vi.hoisted(() => ({ call:vi.fn(), working:null as any }));
vi.mock("../api/core",()=>({coreCommand:mock.call}));
vi.mock("../presentation/useCoreWorkingState",()=>({useOptionalCoreWorkingState:()=>mock.working}));
import { DeepTutorLearningPanel } from "../components/DeepTutorLearningPanel";
import { DeepTutorJourneySession, journeyEditor, journeyIdentity, snapshot } from "../presentation/deepTutorJourney";
import { sha256 } from "../presentation/exchangeProof";

const json=<T,>(value:T):T=>JSON.parse(JSON.stringify(value));
const material:DocumentDto={document_id:"doc_material",version:1,content_sha256:"a".repeat(64),source_id:null,source_revision:null,title:"测试材料",editor_json:{type:"doc",content:[]},text_projection:"材料",blocks:[]};
const scope={workspace_id:"workspace_test",restore_epoch:"epoch_test"};
const hash=(value:string)=>sha256(new TextEncoder().encode(value));
const requestHash=(body:Record<string,unknown>)=>hash(JSON.stringify(body,(_key,value)=>value&&typeof value==="object"&&!Array.isArray(value)?Object.fromEntries(Object.entries(value).sort(([a],[b])=>a<b?-1:a>b?1:0)):value));
let documents:Map<string,DocumentDto>, events:string[], activities:Map<string,any>, attempts:Map<string,any>;
let generationUnknown=false;
let candidateOptions:any={A:"一",B:"二",C:"三",D:"四"};
function doc(id:string,editor:unknown,version=1):DocumentDto{return {...material,document_id:id,version,editor_json:json(editor),content_sha256:String(version%10).repeat(64)};}
async function transport(operation:string,payload:any={}) {
  payload=json(payload);events.push(operation);const body=payload.body;
  if(operation==="document_get") {const result=documents.get(payload.document_id);if(!result)throw new ApiError(404,"missing");return json(result);}
  if(operation==="document_create"||operation==="document_draft") {
    const id=operation==="document_create"?`doc_req_${await hash(body.create_request_id)}`:payload.document_id;
    const old=documents.get(id);if(operation==="document_draft"&&old?.version!==body.expected_version)throw new ApiError(409,"conflict");
    const result=doc(id,body.editor_json,(old?.version??0)+1);documents.set(id,result);return json(result);
  }
  if(operation==="learning_deeptutor_question_turn") {
    const id=`doc_req_${await hash(`deeptutor_question_turn_${await hash(body.create_request_id)}`)}`;
    const result=doc(id,{type:"doc",content:[],attrs:{archeaxis_deeptutor_question_turn_candidate:{schema:"archeaxis.deeptutor-question-turn-document/v1",create_request_id:body.create_request_id,generation_request_sha256:await requestHash(body),request_frame:body,material:body.material,question:{question_id:"q1",question:"材料中的结论？",question_type:"choice",options:candidateOptions}}}});documents.set(id,result);
    if(generationUnknown)throw new ApiError(503,"response lost");return {document:json(result)};
  }
  if(operation==="learning_deeptutor_question_accept") {
    const id=`doc_req_${await hash(`deeptutor_question_accept_${await hash(body.create_request_id)}`)}`;
    const result=doc(id,{type:"doc",content:[],attrs:{archeaxis_deeptutor_question_acceptance:{create_request_id:body.create_request_id,request_sha256:await requestHash(body),accepted_from:{candidate:body.candidate}},archeaxis_deeptutor_question:{question:{question_id:"q1",question:"材料中的结论？",question_type:"choice",options:{A:"一",B:"二",C:"三",D:"四"},correct_answer:body.correct_answer}}}});documents.set(id,result);return {document:json(result)};
  }
  if(operation==="learning_deeptutor_question_view")return {schema:"archeaxis.deeptutor-question-view/v1",question_document:body.question_document,source_material:snapshot(material),question_version:"sha256:"+"b".repeat(64),independent_mastery:"not_established",question:{question_id:"q1",question:"材料中的结论？",question_type:"choice",options:{A:"一",B:"二",C:"三",D:"四"}}};
  if(operation==="learning_provider_activity_create"){activities.set(body.activity_id,body);return body;}
  if(operation==="learning_provider_activity_get")return {schema:"archeaxis.provider-learning-history/v1",activity:activities.get(payload.activity_id),attempts:[...attempts.values()].filter(row=>row.activity_id===payload.activity_id),next_cursor:null};
  if(operation==="learning_provider_attempt_start"){attempts.set(body.attempt_id,{activity_id:payload.activity_id,attempt_id:body.attempt_id,state:"pending"});return {};}
  if(operation==="learning_deeptutor_practice_grade"){attempts.set(body.attempt_id,{activity_id:body.activity_id,attempt_id:body.attempt_id,state:"submitted",result:{client_event_id:body.request.client_event_id,answer:body.request.answer,provider_correct:true},grade_disposition:{state:"COMPLETED"}});return {};}
  if(operation==="learning_deeptutor_teaching_feedback") {
    const id=`doc_req_${await hash(`deeptutor_teaching_feedback_${await hash(body.create_request_id)}`)}`;
    const frame={schema:"archeaxis.deeptutor-teaching-feedback/v1",request_id:body.create_request_id,session_id:body.session_id,turn_id:body.turn_id,profile:{},current_message:body.current_message,objective_ids:body.objective_ids,focus_objective_id:body.focus_objective_id,updates:body.updates,include_history:body.include_history};
    const result=doc(id,{type:"doc",content:[],attrs:{archeaxis_deeptutor_teaching_feedback_candidate:{schema:"archeaxis.deeptutor-teaching-feedback-document/v1",create_request_id:body.create_request_id,generation_request_sha256:await requestHash(body),request_frame:JSON.stringify(frame)+"\n",profile_source:body.profile,guidance:{teaching_observations:{practice_objective:{text:body.current_message}}}}}});documents.set(id,result);return {document:json(result)};
  }
  throw new Error("Unexpected operation "+operation);
}
beforeEach(()=>{
  vi.stubGlobal("crypto",webcrypto);documents=new Map([[material.document_id,json(material)]]);events=[];activities=new Map();attempts=new Map();generationUnknown=false;candidateOptions={A:"一",B:"二",C:"三",D:"四"};mock.call.mockReset().mockImplementation(transport);
  mock.working={server:{...scope,schema:"archeaxis.ui-working-state/v1",recovery_requires_confirmation:false,state:{unrelatedDraft:"private"}},status:"ready",state:{drafts:{}},session:{getSnapshot:()=>mock.working,rememberDraft:vi.fn((id,editor,base)=>{mock.working.state.drafts[id]={base_version:base,editor_json:json(editor)};}),flush:vi.fn().mockResolvedValue(undefined),clearSaved:vi.fn().mockImplementation(async(id:string,sent:any,version:number)=>{
    const saved=documents.get(id)!;
    if(version!==sent.base_version+1||JSON.stringify(saved.editor_json)!==JSON.stringify(sent.editor_json))throw new Error("draft save proof mismatch");
    delete mock.working.state.drafts[id];return true;
  })}};
});
async function journal(){const session=new DeepTutorJourneySession(snapshot(material),scope,mock.call);await session.load();await session.save();return session;}

describe("new material teaching UI recovery boundaries",()=>{
  it("restores editable input without promoting a working draft into granted lifecycle state",async()=>{
    const saved=await journal();const fake={...saved.value,purpose:"恢复的输入",material_grant:snapshot(material),question:snapshot(material)};
    mock.working.state.drafts[saved.document!.document_id]={base_version:1,editor_json:journeyEditor(fake)};
    render(<DeepTutorLearningPanel document={material}/>);
    expect(await screen.findByDisplayValue("恢复的输入")).toBeInTheDocument();
    expect(screen.getByRole("button",{name:"保存材料授权"})).toBeInTheDocument();
    expect(screen.queryByText(/你已在复核中看过答案/)).not.toBeInTheDocument();
    expect(mock.call.mock.calls.filter(([op])=>op==="learning_deeptutor_question_view")).toHaveLength(0);
  });
  it("releases the visible busy state when the workspace identity changes during a save",async()=>{
    let complete!:(value:unknown)=>void;const view=render(<DeepTutorLearningPanel document={material}/>);
    await waitFor(()=>expect(screen.getByRole("button",{name:"保存学习草稿"})).toBeEnabled());
    mock.call.mockImplementation((op,payload)=>op==="document_create"?new Promise(resolve=>{complete=resolve;}):transport(op,payload));
    fireEvent.click(screen.getByRole("button",{name:"保存学习草稿"}));
    await waitFor(()=>expect(complete).toBeTypeOf("function"));
    mock.working={...mock.working,server:{...scope,workspace_id:"workspace_new",recovery_requires_confirmation:false}};
    view.rerender(<DeepTutorLearningPanel document={material}/>);
    await waitFor(()=>expect(screen.getByRole("button",{name:"保存学习草稿"})).toBeEnabled());
    await act(async()=>complete({}));
  });
  it("clears only an exact one-version draft before continuing lifecycle writes",async()=>{
    await journal();
    mock.working.session.clearSaved.mockImplementation(async(id:string,sent:any,version:number)=>{
      const saved=documents.get(id)!;
      if(version!==sent.base_version+1||JSON.stringify(saved.editor_json)!==JSON.stringify(sent.editor_json))throw new Error("draft save proof mismatch");
      delete mock.working.state.drafts[id];return true;
    });
    render(<DeepTutorLearningPanel document={material}/>);
    await waitFor(()=>expect(screen.getByLabelText("本次学习目标")).toBeEnabled());
    fireEvent.change(screen.getByLabelText("本次学习目标"),{target:{value:"我的目标"}});
    fireEvent.click(screen.getByLabelText("允许使用此材料固定版本进行本地出题与练习"));
    fireEvent.click(screen.getByRole("button",{name:"保存材料授权"}));
    await waitFor(()=>expect(screen.getByRole("button",{name:"保存学习草稿"})).toBeEnabled());
    expect(mock.working.session.clearSaved).toHaveBeenCalled();
    expect(screen.queryByText("draft save proof mismatch")).not.toBeInTheDocument();
    expect(Object.keys(mock.working.state.drafts)).toHaveLength(0);
  });
  it("recovers a lost save acknowledgement by readback, preserving and clearing its exact draft",async()=>{
    const original=await journal();render(<DeepTutorLearningPanel document={material}/>);
    await waitFor(()=>expect(screen.getByLabelText("本次学习目标")).toBeEnabled());
    fireEvent.change(screen.getByLabelText("本次学习目标"),{target:{value:"回执丢失也要保留"}});
    let lost=true;mock.call.mockImplementation(async(op,payload)=>{
      const result=await transport(op,payload);
      if(op==="document_draft"&&lost){lost=false;throw new ApiError(503,"save response lost");}return result;
    });
    fireEvent.click(screen.getByRole("button",{name:"保存学习草稿"}));
    await screen.findByText("save response lost");
    expect(mock.working.state.drafts[original.document!.document_id]).toBeDefined();
    const writes=events.filter(op=>op==="document_draft").length;
    fireEvent.click(screen.getByRole("button",{name:"查询原请求与已保存记录"}));
    await waitFor(()=>expect(screen.getByRole("button",{name:"保存学习草稿"})).toBeEnabled());
    expect(screen.getByDisplayValue("回执丢失也要保留")).toBeInTheDocument();expect(Object.keys(mock.working.state.drafts)).toHaveLength(0);
    expect(events.filter(op=>op==="document_draft")).toHaveLength(writes);
  });
  it("shows every option key when the model returns an ordered option list",async()=>{
    candidateOptions=["一","二","三","四"];
    render(<DeepTutorLearningPanel document={material}/>);
    await waitFor(()=>expect(screen.getByLabelText("本次学习目标")).toBeEnabled());
    fireEvent.change(screen.getByLabelText("本次学习目标"),{target:{value:"理解材料"}});
    fireEvent.click(screen.getByLabelText("允许使用此材料固定版本进行本地出题与练习"));fireEvent.click(screen.getByRole("button",{name:"保存材料授权"}));
    await waitFor(()=>expect(screen.getByRole("button",{name:"生成一道题目候选"})).toBeEnabled());fireEvent.click(screen.getByRole("button",{name:"生成一道题目候选"}));
    const control=await screen.findByLabelText("你确认的正确选项");
    expect([...control.querySelectorAll("option")].map(option=>option.getAttribute("value"))).toEqual(["","A","B","C","D"]);
    expect([...control.querySelectorAll("option")].map(option=>option.getAttribute("data-value"))).toEqual([null,"A","B","C","D"]);
    expect([...control.querySelectorAll("option")].map(option=>option.textContent)).toEqual(["请选择","A","B","C","D"]);
  });
  it("offers the full material-to-feedback click flow with separate grants and honest result labels",async()=>{
    render(<DeepTutorLearningPanel document={material}/>);
    await waitFor(()=>expect(screen.getByLabelText("本次学习目标")).toBeEnabled());
    fireEvent.change(screen.getByLabelText("本次学习目标"),{target:{value:"理解材料"}});
    expect(screen.getByRole("button",{name:"生成一道题目候选"})).toBeDisabled();
    fireEvent.click(screen.getByLabelText("允许使用此材料固定版本进行本地出题与练习"));fireEvent.click(screen.getByRole("button",{name:"保存材料授权"}));
    await waitFor(()=>expect(screen.getByRole("button",{name:"生成一道题目候选"})).toBeEnabled());fireEvent.click(screen.getByRole("button",{name:"生成一道题目候选"}));
    await waitFor(()=>expect(screen.getByLabelText("你确认的正确选项")).toBeEnabled());
    expect(screen.getByLabelText("你确认的正确选项")).toHaveValue("");fireEvent.change(screen.getByLabelText("你确认的正确选项"),{target:{value:"A"}});
    fireEvent.click(screen.getByLabelText("我已核对题目和答案，作为人工声明的答案键保存"));fireEvent.click(screen.getByRole("button",{name:"接纳为练习题"}));
    await screen.findByText(/你已在复核中看过答案/);
    expect(screen.getByRole("button",{name:"建立本次材料练习"})).toBeDisabled();fireEvent.click(screen.getByLabelText("允许使用此接纳题目固定版本进行本地评分"));fireEvent.click(screen.getByRole("button",{name:"保存题目授权"}));
    await waitFor(()=>expect(screen.getByRole("button",{name:"建立本次材料练习"})).toBeEnabled());fireEvent.click(screen.getByRole("button",{name:"建立本次材料练习"}));
    await waitFor(()=>expect(screen.getByRole("button",{name:"开始本次作答"})).toBeEnabled());fireEvent.click(screen.getByRole("button",{name:"开始本次作答"}));
    await waitFor(()=>expect(screen.getByLabelText("作答选项")).toBeEnabled());fireEvent.change(screen.getByLabelText("作答选项"),{target:{value:"A"}});fireEvent.click(screen.getByRole("button",{name:"保存作答并评分"}));
    await screen.findByText(/本地供体评分：与人工答案键一致/);
    await waitFor(()=>expect(screen.getByLabelText("本人的反馈与学习需要")).toBeEnabled());expect(screen.getByLabelText("本人的反馈与学习需要")).toHaveAttribute("maxLength","300");
    fireEvent.change(screen.getByLabelText("本人的反馈与学习需要"),{target:{value:"请增加例子"}});fireEvent.click(screen.getByRole("button",{name:"保存反馈与教学策略"}));
    expect(await screen.findByRole("heading",{name:"已保存的本人反馈"})).toBeInTheDocument();
    expect(events.filter(op=>op==="learning_deeptutor_question_turn")).toHaveLength(1);expect(events).not.toContain("learning_review");
    expect(Object.keys(mock.working.state.drafts)).toHaveLength(0);
  });
});

describe("new bounded teaching journey with JSON transport",()=>{
  it("copies only workspace identity and uses a new journal after restore",async()=>{
    const session=new DeepTutorJourneySession(snapshot(material),{...scope,schema:"archeaxis.ui-working-state/v1",state:{privateDraft:"must not copy"}} as typeof scope,mock.call);
    expect(session.value.schema).toBe("archeaxis.deeptutor-journey/v1");expect(session.value).not.toHaveProperty("state");
    await session.save();const first=session.document!.document_id;
    const restored=new DeepTutorJourneySession(snapshot(material),{...scope,restore_epoch:"epoch_new"},mock.call);await restored.load();await restored.save();
    expect(restored.document!.document_id).not.toBe(first);
  });
  it("persists the request before generation and recovers the original result without replay",async()=>{
    const session=await journal();session.value.purpose="理解材料";await session.act("material_grant","本人确认");generationUnknown=true;
    await expect(session.act("generate")).rejects.toThrow("response lost");expect(session.unresolved).toBe(true);
    const identity=await journeyIdentity(snapshot(material),scope);expect((documents.get(identity.document_id)!.editor_json as any).attrs.archeaxis_deeptutor_journey.pending.kind).toBe("generate");
    const generationIndex=events.indexOf("learning_deeptutor_question_turn");expect(events[generationIndex-1]).toBe("document_get");
    const reopened=new DeepTutorJourneySession(snapshot(material),scope,mock.call);await reopened.load();await reopened.recover();
    expect(reopened.value.candidate).toBeDefined();expect(reopened.unresolved).toBe(false);expect(events.filter(x=>x==="learning_deeptutor_question_turn")).toHaveLength(1);
  });
  it("completes the two-grant reference practice and keeps feedback as learner report",async()=>{
    const session=await journal();session.value.purpose="理解材料";await session.act("material_grant","允许材料");await session.act("generate");
    session.value.correct_answer="A";await session.act("accept");await expect(session.act("activity")).rejects.toThrow("均需明确授权");
    await session.act("question_grant","允许题目");await session.act("activity");await session.act("start");session.value.answer="A";await session.act("grade");session.value.reflection="请增加例子";await session.act("feedback");
    const request=mock.call.mock.calls.find(([op])=>op==="learning_deeptutor_teaching_feedback")![1].body;expect(request.updates[0].basis).toBe("learner_report");
    expect(events.some(op=>["learning_review","assessment_create"].includes(op))).toBe(false);expect(session.result?.state).toBe("submitted");
    const reopened=new DeepTutorJourneySession(snapshot(material),scope,mock.call);await reopened.load();expect(reopened.result?.state).toBe("submitted");
    await reopened.newRound();expect(reopened.value.question).toBeUndefined();expect(reopened.unresolved).toBe(false);
    expect(Object.values(reopened.value).some(value=>value===undefined)).toBe(false);
  });
  it("refuses a new provider operation when the material version changed",async()=>{
    const session=await journal();session.value.purpose="理解材料";await session.act("material_grant","确认");documents.set(material.document_id,{...material,version:2});
    await expect(session.act("generate")).rejects.toThrow("材料版本已变化");expect(events).not.toContain("learning_deeptutor_question_turn");
  });
  it("validates feedback before freezing a request or sending writes",async()=>{
    const session=await journal();session.value.purpose="理解材料";session.value.reflection="字".repeat(301);events=[];
    await expect(session.act("feedback")).rejects.toThrow("300");expect(session.value.pending).toBeUndefined();
    expect(events).toEqual(["document_get"]);
    session.value.reflection="例子";session.value.feedback={...snapshot(material),version:0};events=[];
    await expect(session.act("feedback")).rejects.toThrow("CORE_DTO_INVALID");expect(session.value.pending).toBeUndefined();expect(events).toEqual(["document_get"]);
  });
  it("keeps local input when an unknown save reads back a conflicting journal",async()=>{
    const session=new DeepTutorJourneySession(snapshot(material),scope,mock.call);await session.load();session.value.purpose="必须保留的本人输入";
    mock.call.mockImplementation((op,payload)=>{
      if(op==="document_create"){
        const other=json(payload);other.body.editor_json.attrs.archeaxis_deeptutor_journey.purpose="另一编辑视图的内容";
        return transport(op,other);
      }
      return transport(op,payload);
    });
    await expect(session.save()).rejects.toThrow("保存读回未确认");
    await expect(session.recover()).rejects.toThrow("本地输入已保留");
    expect(session.value.purpose).toBe("必须保留的本人输入");expect(session.unresolved).toBe(true);expect(session.document).toBeNull();
    expect(events.filter(op=>op==="document_create")).toHaveLength(1);
  });
});
