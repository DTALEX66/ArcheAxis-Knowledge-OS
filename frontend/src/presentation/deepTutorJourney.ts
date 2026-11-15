import { coreCommand } from "../api/core";
import { ApiError } from "../api/client";
import type { CoreOperation, DocumentDto, DeepTutorMaterialSnapshotDto as Snapshot, DeepTutorQuestionTurnRequestDto, DeepTutorQuestionAcceptRequestDto, DeepTutorTeachingFeedbackRequestDto, DeepTutorQuestionTurnStatusDto, DeepTutorQuestionTurnCancelDto } from "../api/generated/core-contract";
import { assertCoreDto } from "../api/generated/core-contract";
import { object, sameValue, sha256 } from "./exchangeProof";

export const JOURNEY_NAMESPACE = "archeaxis_deeptutor_journey";
export const JOURNEY_SCHEMA = "archeaxis.deeptutor-journey/v1";
type Json = Record<string, unknown>;
export type JourneyAction = "material_grant" | "generate" | "accept" | "question_grant" | "activity" | "start" | "grade" | "feedback";
type Pending = { kind: JourneyAction; operation: CoreOperation; payload: Json; document_id?: string };
export type Journey = {
  schema: typeof JOURNEY_SCHEMA; material: Snapshot; workspace_id: string; restore_epoch: string;
  purpose: string; correct_answer: string; explanation: string; answer: string; reflection: string;
  material_grant?: Snapshot; candidate?: Snapshot; question?: Snapshot; question_grant?: Snapshot; feedback?: Snapshot;
  activity?: Json; attempt_id?: string; pending?: Pending; unknown_requests: Pending[];
  closed_requests?: {request:Pending;request_sha256:string;outcome:"FAILED"}[];
};
export type JourneyRecoveryState="unconfirmed"|"save_unconfirmed"|"not_found"|"dispatched"|"unknown"|"failed"|"conflict"|"unavailable"|"available"|"completed"|"closed_failed";
export const journeyRecoveryCopy:Record<JourneyRecoveryState,{title:string;detail:string}>={
  unconfirmed:{title:"原请求结果尚未确认",detail:"原学习目标和输入已保留。查询只读取原结果，不会再次调用模型。"},
  save_unconfirmed:{title:"学习记录保存尚未确认",detail:"先查询原保存结果；内容和版本完全相同才确认成功。可先保全恢复记录，避免丢失输入。"},
  not_found:{title:"尚未找到原请求的已保存结果",detail:"未找到记录不能证明没有执行。原请求继续保留，不改用新编号生成。可稍后再查询或保全恢复记录。"},
  dispatched:{title:"原请求已登记，结果尚未确认",detail:"登记状态不代表模型仍在运行，也不能证明已停止。请查询原结果；此处不会重新派发。"},
  unknown:{title:"原请求执行结果未知",detail:"模型可能曾经执行，当前无法确认是否完成。原请求保留；可以查询和保全，不会通过新编号绕过。"},
  failed:{title:"本次生成已确认失败",detail:"Core 已记录失败，未得到可恢复题目。可保全记录，或明确结束本次失败任务；之后开始的是会重新生成的新任务。"},
  conflict:{title:"原请求与读回记录不一致",detail:"没有接纳其他内容，也没有覆盖本地输入。请保全恢复记录并核对，不能更换编号继续生成。"},
  unavailable:{title:"暂时无法查询原请求",detail:"本地服务或记录暂不可读，原输入仍保留。恢复连接后再次查询；本次不会重发生成。"},
  available:{title:"已找到原请求的保存结果",detail:"请查询并核对保存的固定版本后恢复；尚未把该结果接入当前学习记录。"},
  completed:{title:"已按原请求恢复保存结果",detail:"恢复只读取了固定版本。题目仍需人工复核，作答与自报反馈不等于独立掌握。"},
  closed_failed:{title:"已保留并结束本次失败记录",detail:"可以修改学习目标。再次生成属于新任务，会重新使用本地模型；原失败记录仍可保全。"},
};
class JourneyRecoveryError extends Error {constructor(readonly state:JourneyRecoveryState,message:string){super(message);}}
type Transport = (operation: CoreOperation, payload?: Json) => Promise<unknown>;
type WorkspaceIdentity = { workspace_id:string; restore_epoch:string };
type SaveObserver = (documentId:string, editor:ReturnType<typeof journeyEditor>, baseVersion:number) => Promise<((saved:DocumentDto)=>Promise<void>) | undefined>;
const textHash = (value: string) => sha256(new TextEncoder().encode(value));
export const snapshot = (doc: DocumentDto): Snapshot => ({ document_id: doc.document_id, version: doc.version, content_sha256: doc.content_sha256 });
export const journeyEditor = (journey: Journey) => ({ type: "doc" as const, content: [], attrs: { [JOURNEY_NAMESPACE]: journey } });
export async function journeyIdentity(material: Snapshot, workspace: WorkspaceIdentity) {
  const request = `dt_journey_${await textHash(JSON.stringify({material,workspace_id:workspace.workspace_id,restore_epoch:workspace.restore_epoch}))}`;
  return { request, document_id: `doc_req_${await textHash(request)}` };
}
async function resultDocument(kind: "generate" | "accept" | "feedback", id: string) {
  const prefixes = { generate: "deeptutor_question_turn", accept: "deeptutor_question_accept", feedback: "deeptutor_teaching_feedback" };
  return `doc_req_${await textHash(`${prefixes[kind]}_${await textHash(id)}`)}`;
}
/** Mirrors each domain request_sha256's json! Value frame, including Option nulls. */
async function frozenRequestProof(kind:"generate"|"accept"|"feedback",body:Json) {
  const schemas={generate:"DeepTutorQuestionTurnRequestDto",accept:"DeepTutorQuestionAcceptRequestDto",feedback:"DeepTutorTeachingFeedbackRequestDto"};
  assertCoreDto(schemas[kind],body);
  const frame=kind==="generate"?{...body,model:body.model??null}
    :kind==="accept"?{...body,explanation:body.explanation??null,question_text:body.question_text??null}
    :{...body,profile:body.profile??null};
  // These finite DTOs have ASCII field names and integral snapshot versions. Core hashes
  // serde_json::Value::to_string's BTreeMap order, not the Rust struct declaration order.
  const canonical=JSON.stringify(frame,(_key,item:unknown)=>item&&typeof item==="object"&&!Array.isArray(item)
    ?Object.fromEntries(Object.entries(item as Json).sort(([a],[b])=>a<b?-1:a>b?1:0)):item);
  return {frame,sha256:await textHash(canonical)};
}
async function assertFrozenRequest(kind:"generate"|"accept"|"feedback",body:Json,saved:Json) {
  const proof=await frozenRequestProof(kind,body);
  if(saved[kind==="accept"?"request_sha256":"generation_request_sha256"]!==proof.sha256
    ||kind==="generate"&&!sameValue(saved.request_frame,proof.frame)) {
    throw new JourneyRecoveryError("conflict","持久化结果未绑定本次冻结请求；保留原请求，不接纳其他内容。");
  }
}
function validSnapshot(value: unknown): value is Snapshot {
  if (!value || typeof value !== "object") return false;
  const row = value as Snapshot;
  return /^[A-Za-z0-9_-]{1,128}$/.test(row.document_id) && Number.isSafeInteger(row.version) && row.version > 0 && /^[a-f0-9]{64}$/.test(row.content_sha256);
}
export function parseJourney(doc: DocumentDto, material: Snapshot): Journey {
  const value = object(object(doc.editor_json).attrs)[JOURNEY_NAMESPACE] as Journey;
  if (!value || value.schema !== JOURNEY_SCHEMA || !sameValue(value.material, material)
    || typeof value.workspace_id !== "string" || typeof value.restore_epoch !== "string"
    || ![value.purpose,value.correct_answer,value.explanation,value.answer,value.reflection].every(v => typeof v === "string")
    || !Array.isArray(value.unknown_requests) || value.unknown_requests.length > 32
    || value.closed_requests!==undefined&&(!Array.isArray(value.closed_requests)||value.closed_requests.length>32||value.closed_requests.some(row=>row.outcome!=="FAILED"||!/^[a-f0-9]{64}$/.test(row.request_sha256)))
    || [value.material_grant,value.candidate,value.question,value.question_grant,value.feedback].some(v => v !== undefined && !validSnapshot(v))) throw new Error("学习记录格式或材料版本不符；保留原文。 ");
  // Persisted content is data. Only this finite set of locally prepared operations can be observed.
  for (const pending of [...value.unknown_requests,...(value.closed_requests??[]).map(row=>row.request), ...(value.pending ? [value.pending] : [])]) {
    const operations: Record<JourneyAction, string> = { material_grant:"document_create", generate:"learning_deeptutor_question_turn",accept:"learning_deeptutor_question_accept",question_grant:"document_create",activity:"learning_provider_activity_create",start:"learning_provider_attempt_start",grade:"learning_deeptutor_practice_grade",feedback:"learning_deeptutor_teaching_feedback" };
    if (!pending || operations[pending.kind] !== pending.operation || !pending.payload || typeof pending.payload !== "object") throw new Error("学习记录含未知请求；不会执行或重放。");
  }
  return structuredClone(value);
}

/** A bounded UI projection over ordinary Documents and existing activities. No new queue or automatic replay. */
export class DeepTutorJourneySession {
  document: DocumentDto | null = null;
  value: Journey;
  candidate: Json | null = null;
  question: Json | null = null;
  guidance: Json | null = null;
  result: Json | null = null;
  recovery:JourneyRecoveryState|null=null;
  private writeUnknown = false;
  private pendingWrite: {editor:ReturnType<typeof journeyEditor>;version:number}|null = null;
  private busy = false;
  private cancelBusy = false;
  private active = true;
  private identity: Awaited<ReturnType<typeof journeyIdentity>> | null = null;
  constructor(readonly material: Snapshot, readonly workspace: WorkspaceIdentity, private call: Transport = coreCommand, private beforeSave?: SaveObserver, private onStateChange?:()=>void) {
    this.value = { schema:JOURNEY_SCHEMA,material,workspace_id:workspace.workspace_id,restore_epoch:workspace.restore_epoch,purpose:"",correct_answer:"",explanation:"",answer:"",reflection:"",unknown_requests:[] };
  }
  deactivate() { this.active=false; }
  private assertActive() { if(!this.active)throw new Error("材料或工作区已切换；原请求保留，不继续发送后续操作。"); }
  get unresolved() { return this.writeUnknown || !!this.value.pending; }
  get recoveryState():JourneyRecoveryState|null {return this.writeUnknown?"save_unconfirmed":this.recovery??(this.value.pending?"unconfirmed":null);}
  get canStartNewRound() {return !this.busy&&!this.cancelBusy&&!this.unresolved&&!this.value.unknown_requests.length;}
  get canCancelGeneration() {return this.active&&!this.cancelBusy&&!this.writeUnknown&&this.value.pending?.kind==="generate";}
  get journalDocumentId() { return this.identity?.document_id; }
  private async read(id: string,version?:number): Promise<DocumentDto> {
    const doc = await this.call(version===undefined?"document_get":"document_version",{document_id:id,...(version===undefined?{}:{version})}) as DocumentDto;
    if (!doc || doc.document_id !== id || !validSnapshot(snapshot(doc)) || version!==undefined&&doc.version!==version) throw new JourneyRecoveryError("conflict","文档读回身份不符。");
    return doc;
  }
  private async readPinned(binding:Snapshot, label:string):Promise<DocumentDto> {
    let doc:DocumentDto|undefined;
    try { doc=await this.read(binding.document_id); }
    catch(error) {
      if(!(error instanceof ApiError)||error.status!==404)throw error;
    }
    if(!doc||!sameValue(snapshot(doc),binding))doc=await this.read(binding.document_id,binding.version);
    if(!sameValue(snapshot(doc),binding))throw new JourneyRecoveryError("conflict",`${label}固定版本校验不符；原引用保留，未替换历史。`);
    return doc;
  }
  recordFailure(error:unknown) {
    if(error instanceof JourneyRecoveryError)this.recovery=error.state;
    else if(error instanceof ApiError&&error.deeptutorReason==="question_turn_request_id_conflict")this.recovery="conflict";
    else if(error instanceof ApiError&&error.deeptutorReason==="question_turn_execution_outcome_unresolved")this.recovery="unknown";
    else if(this.value.pending&&!this.recovery)this.recovery="unknown";
  }
  recoveryRecord() {
    return JSON.stringify({schema:"archeaxis.deeptutor-recovery-export/v1",material:this.material,workspace_id:this.workspace.workspace_id,restore_epoch:this.workspace.restore_epoch,journal:this.document?snapshot(this.document):null,journey:this.value,pending_save:this.pendingWrite,observed_state:this.recoveryState,note:"本地恢复记录；状态须由原工作区只读核对，不授予重发或模型执行权限。"},null,2);
  }
  async load() {
    this.identity ??= await journeyIdentity(this.material,this.workspace);
    let doc: DocumentDto;
    try { doc = await this.read(this.identity.document_id); }
    catch (error) { if (error instanceof ApiError && error.status === 404 && !this.document && !this.writeUnknown) return; throw error; }
    if(this.writeUnknown&&(!this.pendingWrite||doc.version!==this.pendingWrite.version||!sameValue(doc.editor_json,this.pendingWrite.editor))) {
      throw new Error("读回记录与本次待保存输入不一致；本地输入已保留，请先通过恢复工具导出并比较，不会覆盖或重发。");
    }
    const value = parseJourney(doc,this.material);
    if (value.workspace_id !== this.workspace.workspace_id || value.restore_epoch !== this.workspace.restore_epoch) throw new Error("学习记录属于恢复前的工作区；历史保留，不自动恢复授权或重放请求。");
    this.document = doc; this.value = value; this.writeUnknown = false;this.pendingWrite=null;this.recovery=null;
    await this.readOutputs();
  }
  async ensureCurrent() {
    if (!sameValue(snapshot(await this.read(this.material.document_id)),this.material)) throw new Error("材料版本已变化；当前学习记录保留为历史，请打开新版本开始。");
  }
  async save() {
    this.assertActive();
    if (this.writeUnknown) throw new Error("学习记录保存尚未确认，请先读取已保存记录；未发送新请求。");
    this.identity ??= await journeyIdentity(this.material,this.workspace);
    const editor = journeyEditor(structuredClone(this.value));
    const expected = this.document ? this.document.version + 1 : 1;
    const afterSave = await this.beforeSave?.(this.identity.document_id,editor,expected-1);
    this.assertActive();
    this.pendingWrite={editor:structuredClone(editor),version:expected};
    this.writeUnknown = true;
    const payload = this.document ? {document_id:this.document.document_id,body:{expected_version:this.document.version,editor_json:editor}}
      : {body:{create_request_id:this.identity.request,title:"学习记录 · 材料练习",editor_json:editor}};
    const wrote = await this.call(this.document?"document_draft":"document_create",payload) as DocumentDto;
    const read = await this.read(this.identity.document_id);
    if (wrote.document_id !== read.document_id || wrote.version !== expected || read.version !== expected || !sameValue(read.editor_json,editor)
      || wrote.content_sha256 !== read.content_sha256) throw new Error("学习记录保存读回未确认；没有发送后续请求。");
    this.document = read; this.writeUnknown = false;this.pendingWrite=null;
    this.assertActive();
    await afterSave?.(read);
  }
  private async readOutputs() {
    this.candidate=null;this.question=null;this.guidance=null;this.result=null;
    if (this.value.candidate) {
      const doc = await this.readPinned(this.value.candidate,"题目候选");
      const data = object(object(doc.editor_json).attrs).archeaxis_deeptutor_question_turn_candidate;
      const candidate = object(data);
      if (candidate.schema !== "archeaxis.deeptutor-question-turn-document/v1" || !sameValue(candidate.material,this.material)) throw new Error("候选与材料绑定不符。");
      this.candidate = object(candidate.question);
    }
    if (this.value.question) {
      const view = object(await this.call("learning_deeptutor_question_view",{body:{question_document:this.value.question}}));
      if (view.schema !== "archeaxis.deeptutor-question-view/v1" || !sameValue(view.question_document,this.value.question) || !sameValue(view.source_material,this.material)
        || typeof view.question_version !== "string" || view.independent_mastery !== "not_established") throw new Error("练习题版本或材料绑定不符。");
      this.question = view;
    }
    if (this.value.feedback) {
      const doc = await this.readPinned(this.value.feedback,"教学反馈");
      const data = object(object(object(doc.editor_json).attrs).archeaxis_deeptutor_teaching_feedback_candidate);
      if (data.schema !== "archeaxis.deeptutor-teaching-feedback-document/v1") throw new Error("教学反馈格式不符。");
      this.guidance = object(data.guidance);
    }
    if (this.value.activity) await this.readHistory();
  }
  async readHistory() {
    if (!this.value.activity) return null;
    const activityId = this.value.activity.activity_id;
    const history = object(await this.call("learning_provider_activity_get",{activity_id:activityId,...(this.value.attempt_id?{after_attempt_id:this.value.attempt_id.slice(0,-1)}:{})}));
    if (history.schema !== "archeaxis.provider-learning-history/v1" || !sameValue(history.activity,this.value.activity) || !Array.isArray(history.attempts)) throw new Error("作答历史未绑定此活动。");
    const row = history.attempts.find(item=>object(item).attempt_id===this.value.attempt_id);
    this.result = row ? object(row) : null;
    return history;
  }
  private async grant(material: Snapshot, basis: string) {
    if (!basis.trim()) throw new Error("请明确确认此版本的练习授权。");
    const id = `dt_grant_${crypto.randomUUID()}`;
    return {kind:(sameValue(material,this.material)?"material_grant":"question_grant") as JourneyAction,operation:"document_create" as const,document_id:`doc_req_${await textHash(id)}`,
      payload:{body:{create_request_id:id,title:"材料练习授权",editor_json:{type:"doc",content:[],attrs:{archeaxis_provider_material_grant:{schema:"archeaxis.provider-material-grant/v1",purpose:"材料练习",consumer:"deeptutor",operations:["practice"],material,authorization_basis:basis,expires_at:null,state:"granted"}}}}}};
  }
  async act(kind: JourneyAction, authorization = "") {
    this.assertActive();
    if (this.busy || this.cancelBusy || this.unresolved) throw new Error("存在正在处理或结果未知的请求；先查询原记录。");
    if(kind==="generate"&&this.value.unknown_requests.length)throw new Error("仍有未确认的历史请求；先接回原请求查询，不会换编号生成。");
    this.recovery=null;
    this.busy = true;
    try {
      await this.ensureCurrent();
      const id = `dt_${crypto.randomUUID()}`;
      let pending: Pending;
      if (kind === "material_grant") pending = await this.grant(this.material,authorization);
      else if (kind === "generate") {
        if (!this.value.material_grant || !this.value.purpose.trim()) throw new Error("先确认材料授权并填写学习目标。");
        const body: DeepTutorQuestionTurnRequestDto = {create_request_id:id,material:this.material,requirement:this.value.purpose,model:null};
        pending = {kind,operation:"learning_deeptutor_question_turn",payload:{body},document_id:await resultDocument(kind,id)};
      } else if (kind === "accept") {
        if (!this.value.candidate || !this.value.correct_answer.trim()) throw new Error("先复核候选并明确填写答案键。");
        const body: DeepTutorQuestionAcceptRequestDto = {create_request_id:id,candidate:this.value.candidate,correct_answer:this.value.correct_answer,explanation:this.value.explanation,question_text:null};
        pending = {kind,operation:"learning_deeptutor_question_accept",payload:{body},document_id:await resultDocument(kind,id)};
      } else if (kind === "question_grant") {
        if (!this.value.question) throw new Error("先接纳题目。");
        pending = await this.grant(this.value.question,authorization);
      } else if (kind === "activity") {
        if (!this.value.material_grant || !this.value.question_grant || !this.question) throw new Error("材料与题目均需明确授权。");
        const question = object(this.question.question);
        const body = {activity_id:`dt_activity_${crypto.randomUUID()}`,material:this.material,provider:{id:"deeptutor",version:"1.7.1"},question:{question_id:question.question_id,question_version:this.question.question_version},grant:this.value.material_grant};
        pending = {kind,operation:"learning_provider_activity_create",payload:{body}};
      } else if (kind === "start") {
        if (!this.value.activity) throw new Error("先建立材料练习活动。");
        pending = {kind,operation:"learning_provider_attempt_start",payload:{activity_id:this.value.activity.activity_id,body:{attempt_id:`attempt_${crypto.randomUUID()}`}}};
      } else if (kind === "grade") {
        if (!this.value.activity || !this.value.attempt_id || !this.value.question_grant || !this.value.question || !this.value.answer.trim()) throw new Error("先开始作答并填写答案。");
        pending = {kind,operation:"learning_deeptutor_practice_grade",payload:{body:{activity_id:this.value.activity.activity_id,attempt_id:this.value.attempt_id,request:{client_event_id:id,question_document:this.value.question,question_grant:this.value.question_grant,answer:this.value.answer}}}};
      } else {
        if (!this.value.reflection.trim() || !this.value.purpose.trim()) throw new Error("先填写学习目标和本人的反馈。");
        if(Array.from(this.value.reflection).length>300)throw new Error("本次反馈请保留在300字以内；原文保留。");
        const objective = "practice_objective";
        const body: DeepTutorTeachingFeedbackRequestDto = {create_request_id:id,session_id:this.identity?.request??id,turn_id:id,profile:this.value.feedback??null,current_message:this.value.reflection,objective_ids:[objective],focus_objective_id:objective,
          updates:[{kind:"observation",op:"upsert",key:objective,knowledge_point_id:objective,text:this.value.reflection,basis:"learner_report",evidence:this.value.reflection}],include_history:false};
        pending = {kind,operation:"learning_deeptutor_teaching_feedback",payload:{body},document_id:await resultDocument(kind,id)};
      }
      const inputSchemas: Partial<Record<JourneyAction,string>>={generate:"DeepTutorQuestionTurnRequestDto",accept:"DeepTutorQuestionAcceptRequestDto",feedback:"DeepTutorTeachingFeedbackRequestDto"};
      if(inputSchemas[kind])assertCoreDto(inputSchemas[kind]!,pending.payload.body);
      this.value.pending = pending;
      await this.save(); // The frozen request is durable before any provider work begins.
      this.assertActive();
      this.onStateChange?.(); // Expose the durable request while the independent cancel command remains usable.
      const receipt = object(await this.call(pending.operation,structuredClone(pending.payload)));
      await this.observe(pending,receipt);
      delete this.value.pending;
      await this.save();
    } catch(error){this.recordFailure(error);throw error;} finally { this.busy = false; }
  }
  private async observe(pending: Pending, receipt?: Json, fixed?:Snapshot, recoverHistorical=false) {
    const body = object(pending.payload.body);
    if (pending.document_id) {
      let doc = await this.read(pending.document_id,fixed?.version);
      if(recoverHistorical&&pending.kind==="generate"&&doc.version!==1)doc=await this.read(pending.document_id,1);
      if(fixed&&!sameValue(snapshot(doc),fixed))throw new JourneyRecoveryError("conflict","已保存候选与原请求的结果版本不符。");
      const attrs = object(object(doc.editor_json).attrs);
      if (pending.kind === "material_grant" || pending.kind === "question_grant") {
        if (!sameValue(doc.editor_json,body.editor_json) || doc.version !== 1) throw new Error("授权读回不一致，未扩大权限。");
        this.value[pending.kind] = snapshot(doc);
      } else if (pending.kind === "generate") {
        const data = object(attrs.archeaxis_deeptutor_question_turn_candidate);
        if (data.schema !== "archeaxis.deeptutor-question-turn-document/v1" || data.create_request_id !== body.create_request_id || !sameValue(data.material,this.material) || doc.version !== 1) throw new Error("生成候选读回身份不一致。");
        await assertFrozenRequest("generate",body,data);
        this.value.candidate = snapshot(doc); this.candidate = object(data.question);
      } else if (pending.kind === "accept") {
        const data = object(attrs.archeaxis_deeptutor_question_acceptance);
        if (data.create_request_id !== body.create_request_id || !sameValue(object(data.accepted_from).candidate,body.candidate) || doc.version !== 1) throw new Error("接纳题目读回与候选不符。");
        await assertFrozenRequest("accept",body,data);
        this.value.question = snapshot(doc);
        await this.readOutputs();
      } else {
        const data = object(attrs.archeaxis_deeptutor_teaching_feedback_candidate);
        if (data.schema !== "archeaxis.deeptutor-teaching-feedback-document/v1" || data.create_request_id !== body.create_request_id || doc.version !== 1) throw new Error("反馈读回身份不符。");
        await assertFrozenRequest("feedback",body,data);
        this.value.feedback = snapshot(doc); this.guidance = object(data.guidance);
      }
      if (receipt?.document && !sameValue(snapshot(receipt.document as DocumentDto),snapshot(doc))) throw new Error("返回文档与读回版本不同。");
    } else if (pending.kind === "activity") {
      const history = object(await this.call("learning_provider_activity_get",{activity_id:body.activity_id}));
      if (history.schema !== "archeaxis.provider-learning-history/v1" || !sameValue(history.activity,body)) throw new Error("活动创建尚未确认。");
      this.value.activity = body;
    } else if (pending.kind === "start") {
      const old = this.value.attempt_id; this.value.attempt_id = String(body.attempt_id);
      try { await this.readHistory(); if (!this.result || this.result.state !== "pending") throw new Error("作答开始尚未确认。"); }
      catch (error) { if(old===undefined)delete this.value.attempt_id;else this.value.attempt_id=old;throw error; }
    } else {
      await this.readHistory();
      const result = this.result?.result ? object(this.result.result) : null;
      const request = object(body.request);
      if (!this.result || this.result.state !== "submitted" || !result || result.client_event_id !== request.client_event_id || result.answer !== request.answer
        || typeof result.provider_correct !== "boolean" || object(this.result.grade_disposition).state !== "COMPLETED") throw new Error("评分结果尚未确认；不会自动再次评分。");
    }
  }
  async recover() {
    this.assertActive();
    try {
      // All recovery uses read projections; never replay the persisted provider operation.
      if (this.writeUnknown) await this.load();
      if (!this.value.pending) { await this.load(); return; }
      const pending=this.value.pending;
      try {await this.observe(pending,undefined,undefined,true);}
      catch(error){
        if(pending.kind!=="generate"||!(error instanceof ApiError)||error.status!==404)throw error;
        const status=await this.readGenerationStatus(pending);
        if(status.state!=="COMPLETED")return;
        await this.observe(pending,undefined,{document_id:status.result_document_id!,version:status.result_version!,content_sha256:status.result_content_sha256!});
      }
      delete this.value.pending;
      await this.save();this.recovery="completed";
    } catch(error){this.recordFailure(error);throw error;}
  }
  private async readGenerationStatus(pending:Pending):Promise<DeepTutorQuestionTurnStatusDto> {
    this.assertActive();
    if(pending.kind!=="generate")throw new Error("此操作没有出题请求状态。");
    try {
      const body=object(pending.payload.body);
      const status=await this.boundGenerationStatus(pending,await this.call("learning_deeptutor_question_turn_status",{body:structuredClone(body)}));
      this.recovery=status.state==="COMPLETED"?"available":status.state.toLowerCase() as JourneyRecoveryState;
      return status;
    } catch(error){
      this.recovery="unavailable";this.recordFailure(error);throw error;
    }
  }
  private async boundGenerationStatus(pending:Pending,input:unknown):Promise<DeepTutorQuestionTurnStatusDto> {
    const body=object(pending.payload.body),proof=await frozenRequestProof("generate",body);
    const status=assertCoreDto<DeepTutorQuestionTurnStatusDto>("DeepTutorQuestionTurnStatusDto",input);
    if(status.request_id!==body.create_request_id||status.request_sha256!==proof.sha256
      ||status.state==="COMPLETED"&&(status.result_document_id!==await resultDocument("generate",String(body.create_request_id))||status.result_version!==1||!validSnapshot({document_id:status.result_document_id,version:status.result_version,content_sha256:status.result_content_sha256}))
      ||status.state!=="COMPLETED"&&(status.result_document_id!==null||status.result_version!==null||status.result_content_sha256!==null))throw new JourneyRecoveryError("conflict","查询结果未绑定本次冻结请求，原输入保留。");
    return status;
  }
  /** Independent of the in-flight generation/write lease. It never clears, saves or replays a request. */
  async cancelGeneration():Promise<DeepTutorQuestionTurnCancelDto> {
    this.assertActive();
    if(!this.canCancelGeneration)throw new Error("先核对已保存的原生成请求；当前不能提交取消。");
    const pending=structuredClone(this.value.pending!);
    this.cancelBusy=true;
    try {
      const body=assertCoreDto<DeepTutorQuestionTurnRequestDto>("DeepTutorQuestionTurnRequestDto",pending.payload.body);
      if(!sameValue(body.material,this.material)||pending.document_id!==await resultDocument("generate",body.create_request_id))throw new JourneyRecoveryError("conflict","冻结取消请求与当前材料或结果身份不符；未发送取消。");
      this.assertActive();
      if(!sameValue(this.value.pending,pending))throw new JourneyRecoveryError("conflict","原请求已变化；未发送取消，请核对已保存结果。");
      const receipt=assertCoreDto<DeepTutorQuestionTurnCancelDto>("DeepTutorQuestionTurnCancelDto",
        await this.call("learning_deeptutor_question_turn_cancel",{body:structuredClone(body)}));
      const {cancel_requested,provider_stop_state,...status}=receipt;
      await this.boundGenerationStatus(pending,status);
      if(cancel_requested!==(status.state==="UNKNOWN")||provider_stop_state!=="UNKNOWN")throw new JourneyRecoveryError("conflict","取消回执状态不一致；原请求保留，未确认停止。");
      this.assertActive();
      const read=await this.boundGenerationStatus(pending,await this.call("learning_deeptutor_question_turn_status",{body:structuredClone(pending.payload.body)}));
      this.assertActive();
      if(cancel_requested&&read.state!=="UNKNOWN")throw new JourneyRecoveryError("conflict","取消后的读回状态不一致；保留原请求，未接受迟到结果。");
      if(!this.busy&&sameValue(this.value.pending,pending))this.recovery=read.state==="COMPLETED"?"available":read.state.toLowerCase() as JourneyRecoveryState;
      return receipt;
    } catch(error) {if(!this.busy&&sameValue(this.value.pending,pending))this.recordFailure(error);throw error;}
    finally {this.cancelBusy=false;this.onStateChange?.();}
  }
  async closeFailedRequest() {
    this.assertActive();
    if(this.busy||this.writeUnknown||!this.value.pending)throw new Error("先确认原请求和保存结果。");
    this.busy=true;
    try {
      const pending=this.value.pending,status=await this.readGenerationStatus(pending);
      this.assertActive();
      if(status.state!=="FAILED")throw new JourneyRecoveryError(this.recovery!,"原请求尚未确认失败，不能结束或换编号继续。");
      if((this.value.closed_requests?.length??0)>=32)throw new Error("已保留32次失败记录，请先保全并核对历史。");
      this.value.closed_requests=[...(this.value.closed_requests??[]),{request:structuredClone(pending),request_sha256:status.request_sha256,outcome:"FAILED"}];
      delete this.value.pending;
      await this.save();this.recovery="closed_failed";
    } finally {this.busy=false;}
  }
  async resumeHistoricalRequest(index:number) {
    this.assertActive();
    if(this.busy||this.unresolved)throw new Error("请先核对当前请求。");
    const pending=this.value.unknown_requests[index];
    if(!pending)throw new Error("未找到所选历史请求。");
    if(pending.kind!=="generate")throw new Error("此历史操作需原学习活动上下文；请先保全恢复记录并核对原学习文档版本。");
    await this.save();
    // The previous journal version retains the current round; this only selects an old request for reading.
    delete this.value.candidate;delete this.value.question;delete this.value.question_grant;delete this.value.activity;delete this.value.attempt_id;
    this.value.pending=structuredClone(pending);this.value.unknown_requests.splice(index,1);
    this.value.correct_answer="";this.value.explanation="";this.value.answer="";
    if(pending.kind==="generate")this.value.purpose=String(object(pending.payload.body).requirement??this.value.purpose);
    this.candidate=null;this.question=null;this.result=null;this.recovery="unconfirmed";
    await this.save();await this.recover();
  }
  async newRound() {
    this.assertActive();
    if (!this.canStartNewRound) throw new Error("原请求结果尚未确认；只能查询和保全，不能换编号开始新任务。");
    const next=structuredClone(this.value);
    delete next.candidate;delete next.question;delete next.question_grant;delete next.activity;delete next.attempt_id;delete next.pending;
    this.value = {...next,correct_answer:"",answer:"",explanation:""};
    this.candidate = null; this.question = null; this.result = null;
    await this.save();this.recovery=null;
  }
}
