import { createHash, webcrypto } from "node:crypto";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { CoreOperation, DocumentDto } from "../api/generated/core-contract";
import { DeepTutorJourneySession, snapshot } from "../presentation/deepTutorJourney";

type Json=Record<string,unknown>;
type Kind="generate"|"accept"|"feedback";
const material={document_id:"doc_material",version:1,content_sha256:"a".repeat(64)};
const candidate={document_id:"doc_candidate",version:1,content_sha256:"b".repeat(64)};
const scope={workspace_id:"workspace_binding",restore_epoch:"epoch_binding"};
const question={question_id:"q1",question:"这是材料的问题",question_type:"choice",options:{A:"一",B:"二",C:"三",D:"四"}};
const hash=(text:string)=>createHash("sha256").update(text,"utf8").digest("hex");
// Core request_sha256 uses json! Value::to_string (BTreeMap key order), not struct field order.
const requestHash=(body:Json)=>hash(JSON.stringify(body,(_key,value)=>value&&typeof value==="object"&&!Array.isArray(value)?Object.fromEntries(Object.entries(value).sort(([a],[b])=>a<b?-1:a>b?1:0)):value));
const requests:Record<Kind,Json>={
  generate:{create_request_id:"request_1",material,requirement:"原学习目标",model:null},
  accept:{create_request_id:"request_1",candidate,correct_answer:"A",explanation:"人工说明\n第二行",question_text:null},
  feedback:{create_request_id:"request_1",session_id:"session_1",turn_id:"turn_1",profile:null,current_message:"需要例子",objective_ids:["objective_1"],focus_objective_id:"objective_1",updates:[{kind:"observation",op:"upsert",key:"note_1",knowledge_point_id:"objective_1",text:"需要例子",basis:"learner_report",evidence:"需要例子"}],include_history:false},
};
const operations:Record<Kind,CoreOperation>={generate:"learning_deeptutor_question_turn",accept:"learning_deeptutor_question_accept",feedback:"learning_deeptutor_teaching_feedback"};
const namespaces:Record<Kind,string>={generate:"archeaxis_deeptutor_question_turn_candidate",accept:"archeaxis_deeptutor_question_acceptance",feedback:"archeaxis_deeptutor_teaching_feedback_candidate"};
function storedBody(kind:Kind,body:Json):Json {
  if(kind==="generate")return {schema:"archeaxis.deeptutor-question-turn-document/v1",create_request_id:body.create_request_id,generation_request_sha256:requestHash(body),generation_route:"deeptutor_question_turn_local_model",material:body.material,request_frame:body,question,model_call:"INVOKED",human_review_required:true,active_content_executed:false,rendering_authorized:false,answer_secrecy:"not_established"};
  if(kind==="accept")return {create_request_id:body.create_request_id,request_sha256:requestHash(body),accepted_from:{candidate:body.candidate,generation_route:"deeptutor_question_turn_local_model",model_reply_sha256:"c".repeat(64),capture_binding_sha256:"d".repeat(64)},answer_key_source:"human_declared",model_answer_used_as_key:false,explanation_source:"human_supplied"};
  const workerFrame={schema:"archeaxis.deeptutor-teaching-feedback/v1",request_id:body.create_request_id,session_id:body.session_id,turn_id:body.turn_id,profile:{},current_message:body.current_message,objective_ids:body.objective_ids,focus_objective_id:body.focus_objective_id,updates:body.updates,include_history:body.include_history};
  return {schema:"archeaxis.deeptutor-teaching-feedback-document/v1",create_request_id:body.create_request_id,generation_request_sha256:requestHash(body),generation_route:"deeptutor_teaching_feedback_donor_rules",session_id:body.session_id,turn_id:body.turn_id,objective_ids:body.objective_ids,focus_objective_id:body.focus_objective_id,profile_source:body.profile,input_profile:{},result_profile:{},guidance:{teaching_observations:{}},request_frame:JSON.stringify(workerFrame)+"\n",model_call:"NOT_INVOKED",independent_mastery:"not_established"};
}
function document(id:string,editor:unknown):DocumentDto{return {...material,document_id:id,source_id:null,source_revision:null,title:"synthetic Core persistence shape",editor_json:editor,text_projection:"",blocks:[]};}
function setup(kind:Kind,changed:Json={},missingProof=false){
  const body=structuredClone(requests[kind]),stored=storedBody(kind,{...structuredClone(body),...changed});
  if(missingProof)delete stored[kind==="accept"?"request_sha256":"generation_request_sha256"];
  const prefix={generate:"deeptutor_question_turn",accept:"deeptutor_question_accept",feedback:"deeptutor_teaching_feedback"}[kind];
  const outputId=`doc_req_${hash(`${prefix}_${hash(String(body.create_request_id))}`)}`;
  const docs=new Map<string,DocumentDto>([[outputId,document(outputId,{type:"doc",content:[],attrs:{[namespaces[kind]]:stored,...(kind==="accept"?{archeaxis_deeptutor_question:{schema:"archeaxis.deeptutor-question/v1",source_material:material,origin:"user_import_unverified",question:{...question,correct_answer:body.correct_answer,explanation:body.explanation}}}:{})}})]]);
  const call=vi.fn(async(op:CoreOperation,payload:Json={})=>{
    if(op==="document_get")return structuredClone(docs.get(String(payload.document_id)));
    if(op==="document_create"){
      const request=payload.body as Json,id=`doc_req_${hash(String(request.create_request_id))}`,saved=document(id,request.editor_json);docs.set(id,saved);return structuredClone(saved);
    }
    if(op==="learning_deeptutor_question_view")return {schema:"archeaxis.deeptutor-question-view/v1",question_document:snapshot(docs.get(outputId)!),source_material:material,question_version:"sha256:"+"c".repeat(64),independent_mastery:"not_established",question};
    throw new Error("Unexpected operation "+op);
  });
  const session=new DeepTutorJourneySession(material,scope,call);
  session.value.pending={kind,operation:operations[kind],payload:{body},document_id:outputId};
  return {session,call,stored};
}
beforeEach(()=>vi.stubGlobal("crypto",webcrypto));

describe("new frozen-request binding for read-only DeepTutor recovery",()=>{
  it("matches the shared Core acceptance vector with explicit null and UTF-8 newline",()=>{
    expect(requestHash(requests.accept)).toBe("8ac653b4972266b5aad694a543709c7b51467de1c94d1d2100ca894860350e3c");
  });
  it.each<[Kind,Json]>([
    ["generate",{requirement:"另一个学习目标"}],
    ["generate",{model:"other-local-model"}],
    ["accept",{correct_answer:"B"}],
    ["accept",{explanation:"另一个人的答案说明"}],
    ["feedback",{current_message:"不同的本人反馈"}],
    ["feedback",{profile:{...candidate,document_id:"doc_other_profile"}}],
  ])("rejects same-ID %s output for a different frozen body %j",async(kind,changed)=>{
    const {session,call}=setup(kind,changed);const pending=structuredClone(session.value.pending);
    await expect(session.recover()).rejects.toThrow(/冻结请求/);
    expect(session.value.pending).toEqual(pending);expect(session.value.candidate).toBeUndefined();expect(session.value.question).toBeUndefined();expect(session.value.feedback).toBeUndefined();
    expect(call.mock.calls.map(([op])=>op)).toEqual(["document_get"]);
  });
  it.each<Kind>(["generate","accept","feedback"])("requires persisted Core request proof for %s",async kind=>{
    const {session,call}=setup(kind,{},true);await expect(session.recover()).rejects.toThrow(/冻结请求/);
    expect(session.unresolved).toBe(true);expect(call.mock.calls.map(([op])=>op)).toEqual(["document_get"]);
  });
  it.each<Kind>(["generate","accept","feedback"])("recovers the exact %s request through reads and journal save without provider replay",async kind=>{
    const {session,call}=setup(kind);await session.recover();
    expect(session.value.pending).toBeUndefined();expect(session.unresolved).toBe(false);
    expect(call.mock.calls.some(([op])=>op===operations[kind])).toBe(false);
    expect(session.value[kind==="generate"?"candidate":kind==="accept"?"question":"feedback"]).toBeDefined();
  });
});
