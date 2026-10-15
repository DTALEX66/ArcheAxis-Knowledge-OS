import type { JSONContent } from "@tiptap/core";
import type { UiWorkingStateTeachingDraft, UiWorkingStateLearningDraft, UiWorkingStatePendingJob, UiWorkingStatePendingReview, UiWorkingStatePendingMachine } from "../api/generated/ui-working-state-contract";
import { assertUiWorkingState } from "../api/generated/ui-working-state-contract";

export type WorkingEditor = JSONContent & {type:"doc";content:JSONContent[]};
export type WorkingDraft = {base_version:number;editor_json:WorkingEditor};
export type PendingOriginal = {create_request_id:string;title:string;editor_json:WorkingEditor;source_id?:string;source_revision?:string};
export type PendingJob = UiWorkingStatePendingJob;
export type PendingReview = UiWorkingStatePendingReview;
export type PendingMachine = UiWorkingStatePendingMachine;
export type LearningDraft = UiWorkingStateLearningDraft;
export type TeachingDraft = UiWorkingStateTeachingDraft;
type PreparationAttempt = NonNullable<TeachingDraft["preparation_attempt"]>;
type PreparationFinish = {key:string;attempt:PreparationAttempt;preparation:NonNullable<TeachingDraft["preparation"]>;saved:string;original:TeachingDraft;remove:boolean};
function applyPreparationFinish(state:WorkingState,finish:PreparationFinish):void {
  const entry=state.teaching_drafts?.[finish.key];
  if(!entry||!equal(entry.preparation_attempt,finish.attempt))return;
  if(finish.remove&&equal(entry,finish.original)){delete state.teaching_drafts![finish.key];if(!Object.keys(state.teaching_drafts!).length)delete state.teaching_drafts;return;}
  entry.preparation=structuredClone(finish.preparation);entry.saved_preparation=finish.saved;delete entry.preparation_attempt;
}
export type WorkingState = {drafts:Record<string,WorkingDraft>;teaching_drafts?:Record<string,TeachingDraft>;learning_drafts?:Record<string,LearningDraft>;opened_documents:string[];active_document:string|null;page_id:string|null;pending_original?:PendingOriginal|null;pending_jobs?:Record<string,PendingJob>;pending_reviews?:Record<string,PendingReview>;pending_machine?:Record<string,UiWorkingStatePendingMachine>};
export type WorkingRead = {schema:"archeaxis.ui-working-state/v1";workspace_id:string;restore_epoch:string;state_revision:number;state:WorkingState;draft_digests:Record<string,string>;pending_document_id:string|null;recovery_candidates:WorkingState|null;recovery_requires_confirmation:boolean};
type Basis = Pick<WorkingRead,"workspace_id"|"restore_epoch"|"state_revision">;
export type WorkingTransport = {
  read:()=>Promise<WorkingRead>;
  write:(request:Basis & {state:WorkingState;release_teaching?:{draft_key:string;record_id:string}})=>Promise<WorkingRead>;
  clearSaved:(request:Basis & {document_id:string;base_version:number;content_sha256:string;saved_version:number})=>Promise<WorkingRead>;
  clearMachine?:(request:Basis & {journal_id:string;task_id:string})=>Promise<WorkingRead>;
  clearJob?:(request:Basis & {request_id:string;action:"terminal"|"abandon_unadmitted"})=>Promise<WorkingRead>;
  recover:(request:Basis & {action:"preserve"|"discard"})=>Promise<WorkingRead>;
};
export type WorkingView = {state:WorkingState;server:WorkingRead|null;status:"loading"|"ready"|"unsaved"|"saving"|"blocked"|"recovery";error:string|null};
const empty=():WorkingState=>({drafts:{},opened_documents:[],active_document:null,page_id:null,pending_original:null});
// Equality only: Core supplies the authoritative digest; JS never re-encodes a Rust digest.
function equal(a:unknown,b:unknown):boolean {
  if(a===b)return true;
  if(!a||!b||typeof a!=="object"||typeof b!=="object")return false;
  if(Array.isArray(a)||Array.isArray(b))return Array.isArray(a)&&Array.isArray(b)&&a.length===b.length&&a.every((v,i)=>equal(v,b[i]));
  const left=a as Record<string,unknown>,right=b as Record<string,unknown>,keys=Object.keys(left);
  return keys.length===Object.keys(right).length&&keys.every(k=>Object.prototype.hasOwnProperty.call(right,k)&&equal(left[k],right[k]));
}
function sameWorkspace(a:WorkingRead,b:WorkingRead):boolean{return a.workspace_id===b.workspace_id&&a.restore_epoch===b.restore_epoch;}
function basis(read:WorkingRead):Basis{return {workspace_id:read.workspace_id,restore_epoch:read.restore_epoch,state_revision:read.state_revision};}

/** App-owned lifetime. No browser storage, Document writes, automatic merges or restore decisions. */
export class CoreWorkingStateSession {
  private view:WorkingView={state:empty(),server:null,status:"loading",error:null};
  private listeners=new Set<()=>void>();
  private serial=0;
  private inFlight:Promise<WorkingRead>|null=null;
  private readFlight:Promise<WorkingRead>|null=null;
  private clearFlight:Promise<boolean>|null=null;
  private unknown:{base:WorkingRead;state:WorkingState;releasedTeaching?:{key:string;draft:TeachingDraft};finishedPreparation?:PreparationFinish;cleared?:{id:string;sent:WorkingDraft};clearedTeaching?:{key:string;draft:TeachingDraft};clearedReview?:PendingReview;clearedLearning?:LearningDraft;clearedJob?:PendingJob;clearedMachine?:PendingMachine}|null=null;
  getSnapshot=():WorkingView=>this.view;
  subscribe=(listener:()=>void):(()=>void)=>{this.listeners.add(listener);return()=>this.listeners.delete(listener);};
  constructor(private transport:WorkingTransport) {}
  private publish(update:Partial<WorkingView>):void {this.view={...this.view,...update};this.listeners.forEach(listener=>listener());}
  private fail(error:unknown):never {
    const message=error instanceof Error?error.message:"工作草稿保存未确认；本地输入保留。";
    this.publish({status:"blocked",error:message});throw error;
  }
  async load():Promise<WorkingRead> {
    if(this.readFlight)return this.readFlight;
    if(this.inFlight||this.clearFlight)throw new Error("工作状态请求仍在执行，请稍后重读。");
    const run=this.readOnce();this.readFlight=run;
    try{return await run;}finally{this.readFlight=null;}
  }
  private async readOnce():Promise<WorkingRead> {
    try {
      const read=assertUiWorkingState<WorkingRead>("Read",await this.transport.read());
      if(this.view.server&&!sameWorkspace(this.view.server,read)) {
        this.publish({server:read,status:read.recovery_requires_confirmation?"recovery":"blocked",error:"工作区或恢复身份已变化；本地草稿保留，请明确核对。"});
        return read;
      }
      if(this.unknown) {
        const pending=this.unknown;
        if(!sameWorkspace(pending.base,read))return this.fail(new Error("冻结请求属于不同工作区或恢复现场；未自动重放。"));
        if(read.state_revision===pending.base.state_revision+1&&equal(read.state,pending.state)) {
          if(pending.releasedTeaching&&equal(this.view.state.teaching_drafts?.[pending.releasedTeaching.key],pending.releasedTeaching.draft)){const state=structuredClone(this.view.state);state.teaching_drafts![pending.releasedTeaching.key].pending_record=null;this.publish({state});}
          if(pending.finishedPreparation){const state=structuredClone(this.view.state);applyPreparationFinish(state,pending.finishedPreparation);this.publish({state});}
          if(pending.clearedTeaching&&equal(this.view.state.teaching_drafts?.[pending.clearedTeaching.key],pending.clearedTeaching.draft)) {
            const state=structuredClone(this.view.state);delete state.teaching_drafts![pending.clearedTeaching.key];if(!Object.keys(state.teaching_drafts!).length)delete state.teaching_drafts;this.publish({state});
          }
          if(pending.cleared&&equal(this.view.state.drafts[pending.cleared.id],pending.cleared.sent)) {
            const state=structuredClone(this.view.state);delete state.drafts[pending.cleared.id];this.publish({state});
          }
          if(pending.clearedJob&&equal(this.view.state.pending_jobs?.[pending.clearedJob.request_id],pending.clearedJob)) {
            const state=structuredClone(this.view.state);delete state.pending_jobs![pending.clearedJob.request_id];
            if(!Object.keys(state.pending_jobs!).length)delete state.pending_jobs;
            this.publish({state});
          }
          if(pending.clearedMachine&&equal(this.view.state.pending_machine?.[pending.clearedMachine.journal_id],pending.clearedMachine)) {
            const state=structuredClone(this.view.state);delete state.pending_machine![pending.clearedMachine.journal_id];if(!Object.keys(state.pending_machine!).length)delete state.pending_machine;this.publish({state});
          }
          if(pending.clearedLearning&&equal(this.view.state.learning_drafts?.[pending.clearedLearning.assessment_id],pending.clearedLearning)) {
            const state=structuredClone(this.view.state);delete state.learning_drafts![pending.clearedLearning.assessment_id];if(!Object.keys(state.learning_drafts!).length)delete state.learning_drafts;this.publish({state});
          }
          if(pending.clearedReview&&equal(this.view.state.pending_reviews?.[pending.clearedReview.client_event_id],pending.clearedReview)) {
            const state=structuredClone(this.view.state);delete state.pending_reviews![pending.clearedReview.client_event_id];if(!Object.keys(state.pending_reviews!).length)delete state.pending_reviews;this.publish({state});
          }
          this.unknown=null;this.publish({server:read,status:equal(read.state,this.view.state)?"ready":"unsaved",error:null});return read;
        }
        if(read.state_revision===pending.base.state_revision&&equal(read.state,pending.base.state)) {
          this.unknown=null;this.publish({server:read,status:"unsaved",error:null});return read;
        }
        return this.fail(new Error("工作状态存在其他修订；本地草稿与冻结请求保留，请比较后明确恢复。"));
      }
      if(read.recovery_requires_confirmation){this.publish({server:read,status:"recovery",error:null});return read;}
      if(this.serial===0)this.publish({state:structuredClone(read.state),server:read,status:"ready",error:null});
      else if(this.view.server&&sameWorkspace(this.view.server,read)&&equal(read.state,this.view.server.state))this.publish({server:read,status:"unsaved",error:null});
      else if(!this.view.server&&equal(read.state,empty()))this.publish({server:read,status:"unsaved",error:null});
      else if(equal(read.state,this.view.state))this.publish({server:read,status:"ready",error:null});
      else return this.fail(new Error("远端工作状态与本地输入不同；未自动替换草稿。"));
      return read;
    } catch(error){return this.fail(error);}
  }
  /** Explicit retirement, never a network-catch fallback. Core fences late arrivals atomically. */
  async releaseTeachingDraft(key:string,draft:TeachingDraft):Promise<boolean> {
    if(this.clearFlight){await this.clearFlight;return this.releaseTeachingDraft(key,draft);}
    const run=this.releaseTeachingDraftOnce(key,draft);this.clearFlight=run;
    try{return await run;}finally{this.clearFlight=null;}
  }
  private async releaseTeachingDraftOnce(key:string,draft:TeachingDraft):Promise<boolean> {
    await this.flush();const server=this.view.server!;
    if(!draft.pending_record||!equal(this.view.state.teaching_drafts?.[key],draft)||!equal(server.state.teaching_drafts?.[key],draft))return false;
    const expected=structuredClone(server.state);expected.teaching_drafts![key].pending_record=null;
    const request={...basis(server),state:structuredClone(expected),release_teaching:{draft_key:key,record_id:draft.pending_record.record_id}};
    assertUiWorkingState("Write",request);
    this.publish({status:"saving",error:null});const run=this.transport.write(request);this.inFlight=run;
    try {
      const read=assertUiWorkingState<WorkingRead>("Read",await run);
      if(!sameWorkspace(server,read)||read.recovery_requires_confirmation||read.state_revision!==server.state_revision+1||!equal(read.state,expected))throw new Error("教学请求解除冻结回执未确认；原记录请求保留。");
      const state=structuredClone(this.view.state);if(equal(state.teaching_drafts?.[key],draft))state.teaching_drafts![key].pending_record=null;
      this.publish({state,server:read,status:equal(state,read.state)?"ready":"unsaved",error:null});return true;
    }catch(error){this.unknown={base:server,state:expected,releasedTeaching:{key,draft:structuredClone(draft)}};return this.fail(error);}finally{this.inFlight=null;}
  }
  change(update:(state:WorkingState)=>void):void {
    const state=structuredClone(this.view.state);update(state);this.serial++;
    this.publish({state,status:this.view.status==="blocked"||this.view.status==="recovery"?this.view.status:"unsaved"});
  }
  rememberDraft(id:string,editor:WorkingEditor,baseVersion:number):void {this.change(state=>{state.drafts[id]={base_version:baseVersion,editor_json:structuredClone(editor)};});}
  rememberTeachingDraft(key:string,draft:TeachingDraft):void {
    assertUiWorkingState("TeachingDraft",draft);
    if(key!==`${draft.page_id}:${draft.context_item_key??""}`||[draft.context_item_key,draft.item_key].some(s=>s!==null&&(!s.trim()||new TextEncoder().encode(s).length>512)))throw new Error("教学草稿对象身份无效；原文保留。");
    const old=this.view.state.teaching_drafts?.[key];
    if(old?.pending_record&&!equal(old,draft))throw new Error("教学请求已冻结；请先核对同一记录回执。");
    if(old?.preparation_attempt&&!equal(old.preparation_attempt,draft.preparation_attempt))throw new Error("准备正文请求已冻结；请先核对同一保存回执。");
    if(!old&&Object.keys(this.view.state.teaching_drafts??{}).length>=32)throw new Error("最多保留 32 份教学草稿；请先保存已有正文，当前原文保留。");
    if(new TextEncoder().encode(draft.form.content).length>65_536||new TextEncoder().encode(draft.form.purpose).length>512||new TextEncoder().encode(draft.form.rubric_version).length>128)throw new Error("教学正文或用途超过 UTF-8 字节上限；本次输入未保全，请保留原文。");
    const state=structuredClone(this.view.state);state.teaching_drafts??={};state.teaching_drafts[key]=structuredClone(draft);
    assertUiWorkingState("State",state);
    if(new TextEncoder().encode(JSON.stringify(state)).length>1_048_576)throw new Error("工作草稿总量超过 1 MiB；教学输入未保全，请先保存已有正文。");
    if(!equal(old,draft))this.change(next=>{next.teaching_drafts??={};next.teaching_drafts[key]=structuredClone(draft);});
  }
  /** Core proves the exact frozen Document intent before clearing it; later typing survives. */
  async finishTeachingPreparation(key:string,attempt:PreparationAttempt,preparation:NonNullable<TeachingDraft["preparation"]>,saved:string):Promise<boolean> {
    if(this.clearFlight){await this.clearFlight;return this.finishTeachingPreparation(key,attempt,preparation,saved);}
    const run=this.finishTeachingPreparationOnce(key,attempt,preparation,saved);this.clearFlight=run;
    try{return await run;}finally{this.clearFlight=null;}
  }
  private async finishTeachingPreparationOnce(key:string,attempt:PreparationAttempt,preparation:NonNullable<TeachingDraft["preparation"]>,saved:string):Promise<boolean> {
    await this.flush();const server=this.view.server!,entry=server.state.teaching_drafts?.[key];
    if(!entry||!equal(entry.preparation_attempt,attempt)||!equal(this.view.state.teaching_drafts?.[key]?.preparation_attempt,attempt))return false;
    const ordinary=!entry.knowledge_id&&!entry.parent&&!entry.course_id&&!entry.item_key&&!entry.assessment_id&&!entry.pending_record&&entry.form.scope==="personal"&&entry.form.privacy==="local_only"&&!entry.form.assisted&&!entry.form.feedback_class&&!entry.form.rubric_version&&entry.form.producer_kind==="human_authored";
    const finish:PreparationFinish={key,attempt:structuredClone(attempt),preparation,saved,original:structuredClone(entry),remove:ordinary&&JSON.stringify({purpose:entry.form.purpose,content:entry.form.content})===saved};
    const expected=structuredClone(server.state);applyPreparationFinish(expected,finish);
    this.publish({status:"saving",error:null});const run=this.transport.write({...basis(server),state:structuredClone(expected)});this.inFlight=run;
    try {
      const read=assertUiWorkingState<WorkingRead>("Read",await run);
      if(!sameWorkspace(server,read)||read.recovery_requires_confirmation||read.state_revision!==server.state_revision+1||!equal(read.state,expected))throw new Error("准备正文清理回执未确认；冻结请求保留。");
      const state=structuredClone(this.view.state);applyPreparationFinish(state,finish);this.publish({state,server:read,status:equal(state,read.state)?"ready":"unsaved",error:null});return true;
    }catch(error){this.unknown={base:server,state:expected,finishedPreparation:finish};return this.fail(error);}finally{this.inFlight=null;}
  }
  /** Only the exact snapshot is removed, after a caller verifies its domain save/readback. */
  async finishTeachingDraft(key:string,draft:TeachingDraft):Promise<boolean> {
    if(this.clearFlight){await this.clearFlight;return this.finishTeachingDraft(key,draft);}
    const run=this.finishTeachingDraftOnce(key,draft);this.clearFlight=run;
    try{return await run;}finally{this.clearFlight=null;}
  }
  private async finishTeachingDraftOnce(key:string,draft:TeachingDraft):Promise<boolean> {
    await this.flush();const server=this.view.server!;
    if(!equal(this.view.state.teaching_drafts?.[key],draft)||!equal(server.state.teaching_drafts?.[key],draft))return false;
    const expected=structuredClone(server.state);delete expected.teaching_drafts![key];if(!Object.keys(expected.teaching_drafts!).length)delete expected.teaching_drafts;
    this.publish({status:"saving",error:null});const run=this.transport.write({...basis(server),state:structuredClone(expected)});this.inFlight=run;
    try {
      const read=assertUiWorkingState<WorkingRead>("Read",await run);
      if(!sameWorkspace(server,read)||read.recovery_requires_confirmation||read.state_revision!==server.state_revision+1||!equal(read.state,expected))throw new Error("教学草稿清理回执未确认；原文保留。");
      const state=structuredClone(this.view.state);if(equal(state.teaching_drafts?.[key],draft)){delete state.teaching_drafts![key];if(!Object.keys(state.teaching_drafts!).length)delete state.teaching_drafts;}
      this.publish({state,server:read,status:equal(state,read.state)?"ready":"unsaved",error:null});return true;
    }catch(error){this.unknown={base:server,state:expected,clearedTeaching:{key,draft:structuredClone(draft)}};return this.fail(error);}finally{this.inFlight=null;}
  }
  rememberLearningDraft(draft:LearningDraft):void {
    assertUiWorkingState("LearningDraft",draft);
    if([draft.item_key,draft.knowledge_version,draft.question_version].some(value=>value!==undefined&&(!value.trim()||new TextEncoder().encode(value).length>512)))throw new Error("学习题目或修订标识为空或超过 512 UTF-8 字节；原答案保留。");
    if(Object.values(this.view.state.pending_reviews??{}).some(entry=>entry.item_key===draft.item_key))throw new Error("此题已有冻结复习请求；草稿不能改写待核对的答案。");
    const old=this.view.state.learning_drafts?.[draft.assessment_id];
    if(old&&(old.item_key!==draft.item_key||old.knowledge_version!==draft.knowledge_version||old.question_version!==draft.question_version))throw new Error("学习草稿属于不同题目修订；原文保留。");
    if(!old&&Object.keys(this.view.state.learning_drafts??{}).length>=32)throw new Error("最多保留 32 份学习草稿；请先完成复习或明确丢弃一份旧草稿，原答案均保留。");
    if(new TextEncoder().encode(draft.answer).length>65_536)throw new Error("本题答案超过 65536 UTF-8 字节；本次输入未应用，原答案保留。");
    const next=structuredClone(this.view.state);next.learning_drafts??={};next.learning_drafts[draft.assessment_id]=structuredClone(draft);
    if(new TextEncoder().encode(JSON.stringify(next)).length>1_048_576)throw new Error("工作草稿总量超过 1 MiB；本次输入未应用，请先保存或明确丢弃已有草稿。");
    this.change(state=>{state.learning_drafts??={};state.learning_drafts[draft.assessment_id]=structuredClone(draft);});
  }
  /** Explicit user discard; retain the exact local answer until Core ACK or matching readback. */
  async discardLearningDraft(draft:LearningDraft):Promise<void> {
    if(this.clearFlight){await this.clearFlight;return this.discardLearningDraft(draft);}
    const run=this.discardLearningDraftOnce(draft).then(()=>true);this.clearFlight=run;
    try{await run;}finally{this.clearFlight=null;}
  }
  private async discardLearningDraftOnce(draft:LearningDraft):Promise<void> {
    const checked=()=>{
      if(!equal(this.view.state.learning_drafts?.[draft.assessment_id],draft))throw new Error("学习草稿已变化；未丢弃新输入。");
      if(Object.values(this.view.state.pending_reviews??{}).some(entry=>entry.item_key===draft.item_key))throw new Error("此题已有冻结复习请求；请先核对回执，不能丢弃草稿。");
    };
    checked();await this.flush();checked();
    const server=this.view.server!;
    if(!equal(server.state.learning_drafts?.[draft.assessment_id],draft))throw new Error("学习草稿保全身份未确认。");
    const expected=structuredClone(server.state);delete expected.learning_drafts![draft.assessment_id];if(!Object.keys(expected.learning_drafts!).length)delete expected.learning_drafts;
    this.publish({status:"saving",error:null});
    const run=this.transport.write({...basis(server),state:structuredClone(expected)});this.inFlight=run;
    try{
      const read=assertUiWorkingState<WorkingRead>("Read",await run);
      if(!sameWorkspace(server,read)||read.recovery_requires_confirmation||read.state_revision!==server.state_revision+1||!equal(read.state,expected))throw new Error("学习草稿丢弃回执未确认。");
      const state=structuredClone(this.view.state);
      if(equal(state.learning_drafts?.[draft.assessment_id],draft)){delete state.learning_drafts![draft.assessment_id];if(!Object.keys(state.learning_drafts!).length)delete state.learning_drafts;}
      this.publish({state,server:read,status:equal(state,read.state)?"ready":"unsaved",error:null});
    }catch(error){this.unknown={base:server,state:expected,clearedLearning:structuredClone(draft)};this.fail(error);}finally{this.inFlight=null;}
  }
  async stageMachine(entry:PendingMachine):Promise<void> {
    assertUiWorkingState("PendingMachine",entry);
    const server=this.view.server;
    if(!server||!["ready","unsaved"].includes(this.view.status)||entry.origin_restore_epoch!==server.restore_epoch)throw new Error("机器请求保全身份未就绪；尚未发送。");
    const old=this.view.state.pending_machine?.[entry.journal_id];
    if(old&&!equal(old,entry))throw new Error("机器请求已冻结，不能替换。");
    this.change(state=>{state.pending_machine??={};state.pending_machine[entry.journal_id]=structuredClone(entry);});
    const read=await this.flush();
    if(!equal(read.state.pending_machine?.[entry.journal_id],entry))throw new Error("机器请求落盘未确认；尚未发送。");
  }
  rememberScene(page:string|null,id?:string):void {this.change(state=>{state.page_id=page;if(id){if(!state.opened_documents.includes(id))state.opened_documents.push(id);state.active_document=id;}});}
  async flush():Promise<WorkingRead> {
    if(this.readFlight)await this.readFlight;
    if(this.inFlight){await this.inFlight;return this.flush();}
    const server=this.view.server;
    if(!server||this.unknown||this.view.status==="blocked"||this.view.status==="recovery"||server.recovery_requires_confirmation)throw new Error("请先读取或明确恢复工作状态；本地输入保留。");
    if(equal(server.state,this.view.state)) {
      if(this.view.status!=="ready"||this.view.error!==null)this.publish({status:"ready",error:null});
      return server;
    }
    const state=structuredClone(this.view.state);
    this.publish({status:"saving",error:null});
    const run=this.transport.write({...basis(server),state:structuredClone(state)});this.inFlight=run;
    try {
      const read=assertUiWorkingState<WorkingRead>("Read",await run);
      if(!sameWorkspace(server,read)||read.state_revision!==server.state_revision+1||read.recovery_requires_confirmation||!equal(read.state,state))throw new Error("工作状态回执身份或正文不一致。");
      this.publish({server:read,status:equal(state,this.view.state)?"ready":"unsaved",error:null});return read;
    } catch(error){this.unknown={base:server,state};return this.fail(error);}
    finally{this.inFlight=null;}
  }
  /** Journal must be ACKed before the caller sends document_create. */
  async stageOriginal(body:PendingOriginal):Promise<void> {
    if(this.view.state.pending_original&&!equal(this.view.state.pending_original,body))throw new Error("已有冻结笔记请求；请先核对它。");
    this.change(state=>{state.pending_original=structuredClone(body);});
    const read=await this.flush();
    if(!equal(read.state.pending_original,body))throw new Error("笔记创建请求尚未持久化确认。");
  }
  async freezeReview(entry:PendingReview):Promise<void> {
    const server=this.view.server;
    const old=this.view.state.pending_reviews?.[entry.client_event_id];
    const retained=server?.state.pending_reviews?.[entry.client_event_id];
    if(!server||(server.restore_epoch!==entry.origin_restore_epoch&&(!equal(old,entry)||!equal(retained,entry))))throw new Error("复习请求属于另一恢复现场；未发送。");
    if(old&&!equal(old,entry))throw new Error("复习请求已冻结，不能替换。");
    const next=structuredClone(this.view.state);next.pending_reviews??={};next.pending_reviews[entry.client_event_id]=structuredClone(entry);
    assertUiWorkingState("State",next);
    if(new TextEncoder().encode(JSON.stringify(next)).length>1_048_576)throw new Error("复习请求保全将超过 1 MiB；请先保存或明确丢弃其他草稿。");
    this.change(state=>{state.pending_reviews??={};state.pending_reviews[entry.client_event_id]=structuredClone(entry);});
    const read=await this.flush();if(!equal(read.state.pending_reviews?.[entry.client_event_id],entry))throw new Error("复习身份保全未确认；尚未发送。");
  }
  async finishReview(entry:PendingReview,draft?:LearningDraft):Promise<void> {
    if(this.clearFlight){await this.clearFlight;return this.finishReview(entry,draft);}
    const run=this.finishReviewOnce(entry,draft).then(()=>true);this.clearFlight=run;
    try{await run;}finally{this.clearFlight=null;}
  }
  private async finishReviewOnce(entry:PendingReview,draft?:LearningDraft):Promise<void> {
    await this.flush();
    const server=this.view.server!;
    if(!equal(this.view.state.pending_reviews?.[entry.client_event_id],entry)||!equal(server.state.pending_reviews?.[entry.client_event_id],entry))throw new Error("冻结复习身份已变化。");
    const expected=structuredClone(server.state);
    delete expected.pending_reviews![entry.client_event_id];if(!Object.keys(expected.pending_reviews!).length)delete expected.pending_reviews;
    const clearedLearning=draft&&equal(expected.learning_drafts?.[draft.assessment_id],draft)
        &&draft.item_key===entry.item_key&&draft.assessment_id===entry.body.assessment_id
        &&draft.knowledge_version===entry.body.knowledge_version&&draft.question_version===entry.body.question_version
        &&draft.answer.trim()===entry.body.answer&&draft.checked_correct===entry.body.correct&&draft.rating===entry.body.rating?structuredClone(draft):undefined;
    if(clearedLearning){delete expected.learning_drafts![clearedLearning.assessment_id];if(!Object.keys(expected.learning_drafts!).length)delete expected.learning_drafts;}
    this.publish({status:"saving",error:null});
    const run=this.transport.write({...basis(server),state:structuredClone(expected)});this.inFlight=run;
    try{
      const read=assertUiWorkingState<WorkingRead>("Read",await run);
      if(!sameWorkspace(server,read)||read.recovery_requires_confirmation||read.state_revision!==server.state_revision+1||!equal(read.state,expected))throw new Error("复习草稿清理回执未确认。");
      const state=structuredClone(this.view.state);
      if(equal(state.pending_reviews?.[entry.client_event_id],entry)){delete state.pending_reviews![entry.client_event_id];if(!Object.keys(state.pending_reviews!).length)delete state.pending_reviews;}
      if(clearedLearning&&equal(state.learning_drafts?.[clearedLearning.assessment_id],clearedLearning)){delete state.learning_drafts![clearedLearning.assessment_id];if(!Object.keys(state.learning_drafts!).length)delete state.learning_drafts;}
      this.publish({state,server:read,status:equal(state,read.state)?"ready":"unsaved",error:null});
    }catch(error){this.unknown={base:server,state:expected,clearedReview:structuredClone(entry),clearedLearning};this.fail(error);}finally{this.inFlight=null;}
  }
  async stageJob(entry:PendingJob):Promise<void> {
    const old=this.view.state.pending_jobs?.[entry.request_id];
    if(old&&!equal(old,entry))throw new Error("已有不同的冻结执行请求；未覆盖。");
    if(Object.values(this.view.state.pending_jobs??{}).some(item=>item.job_id===entry.job_id&&item.request_id!==entry.request_id))throw new Error("此作业已有冻结执行身份；请先恢复原请求。");
    this.change(state=>{state.pending_jobs??={};state.pending_jobs[entry.request_id]=structuredClone(entry);});
    const read=await this.flush();
    if(!equal(read.state.pending_jobs?.[entry.request_id],entry))throw new Error("执行身份保全未确认；尚未发送任务。");
  }
  async clearJob(entry:PendingJob,action:"terminal"|"abandon_unadmitted"):Promise<void> {
    if(this.clearFlight){await this.clearFlight;return this.clearJob(entry,action);}
    const run=this.clearJobOnce(entry,action).then(()=>true);this.clearFlight=run;
    try{await run;}finally{this.clearFlight=null;}
  }
  private async clearJobOnce(entry:PendingJob,action:"terminal"|"abandon_unadmitted"):Promise<void> {
    await this.flush();
    const server=this.view.server!;
    if(!equal(server.state.pending_jobs?.[entry.request_id],entry)||!this.transport.clearJob)throw new Error("执行保全清理身份未确认。");
    const expected=structuredClone(server.state);delete expected.pending_jobs![entry.request_id];
    if(!Object.keys(expected.pending_jobs!).length)delete expected.pending_jobs;
    const run=this.transport.clearJob({...basis(server),request_id:entry.request_id,action});this.inFlight=run;
    try {
      const read=assertUiWorkingState<WorkingRead>("Read",await run);
      if(!sameWorkspace(server,read)||read.state_revision!==server.state_revision+1||!equal(read.state,expected))throw new Error("执行保全清理回执未确认。");
      const state=structuredClone(this.view.state);
      if(equal(state.pending_jobs?.[entry.request_id],entry)){delete state.pending_jobs![entry.request_id];if(!Object.keys(state.pending_jobs!).length)delete state.pending_jobs;}
      this.publish({state,server:read,status:equal(state,read.state)?"ready":"unsaved",error:null});
    }catch(error){this.unknown={base:server,state:expected,clearedJob:structuredClone(entry)};this.fail(error);}finally{this.inFlight=null;}
  }
  async clearMachine(entry:PendingMachine,taskId:string):Promise<void> {
    if(this.clearFlight){await this.clearFlight;return this.clearMachine(entry,taskId);}
    const run=this.clearMachineOnce(entry,taskId).then(()=>true);this.clearFlight=run;
    try{await run;}finally{this.clearFlight=null;}
  }
  private async clearMachineOnce(entry:PendingMachine,taskId:string):Promise<void> {
    await this.flush();
    const server=this.view.server!;
    if(!equal(server.state.pending_machine?.[entry.journal_id],entry)||!this.transport.clearMachine)throw new Error("执行保全清理身份未确认。");
    const expected=structuredClone(server.state);delete expected.pending_machine![entry.journal_id];
    if(!Object.keys(expected.pending_machine!).length)delete expected.pending_machine;
    const run=this.transport.clearMachine({...basis(server),journal_id:entry.journal_id,task_id:taskId});this.inFlight=run;
    try {
      const read=assertUiWorkingState<WorkingRead>("Read",await run);
      if(!sameWorkspace(server,read)||read.state_revision!==server.state_revision+1||!equal(read.state,expected))throw new Error("执行保全清理回执未确认。");
      const state=structuredClone(this.view.state);
      if(equal(state.pending_machine?.[entry.journal_id],entry)){delete state.pending_machine![entry.journal_id];if(!Object.keys(state.pending_machine!).length)delete state.pending_machine;}
      this.publish({state,server:read,status:equal(state,read.state)?"ready":"unsaved",error:null});
    }catch(error){this.unknown={base:server,state:expected,clearedMachine:structuredClone(entry)};this.fail(error);}finally{this.inFlight=null;}
  }
  async finishOriginal(body:PendingOriginal):Promise<void> {
    if(!equal(this.view.state.pending_original,body))throw new Error("冻结笔记请求身份已变化。");
    this.change(state=>{state.pending_original=null;});await this.flush();
  }
  /** The frozen journal ACK supplies digest/base; a later local edit must never be cleared. */
  async clearSaved(id:string,sent:WorkingDraft,savedVersion:number):Promise<boolean> {
    if(this.clearFlight){await this.clearFlight;return this.clearSaved(id,sent,savedVersion);}
    const run=this.clearSavedOnce(id,sent,savedVersion);this.clearFlight=run;
    try{return await run;}finally{this.clearFlight=null;}
  }
  private async clearSavedOnce(id:string,sent:WorkingDraft,savedVersion:number):Promise<boolean> {
    await this.flush();
    const server=this.view.server!;
    if(!equal(this.view.state.drafts[id],sent)||!equal(server.state.drafts[id],sent))return false;
    const digest=server.draft_digests[id];
    if(!digest||savedVersion!==sent.base_version+1)throw new Error("保存回执与草稿基础版本不符；输入保留。");
    const serial=this.serial;this.publish({status:"saving",error:null});
    const run=this.transport.clearSaved({...basis(server),document_id:id,base_version:sent.base_version,content_sha256:digest,saved_version:savedVersion});this.inFlight=run;
    try {
      const read=assertUiWorkingState<WorkingRead>("Read",await run);
      const expected=structuredClone(server.state);delete expected.drafts[id];
      if(!sameWorkspace(server,read)||read.state_revision!==server.state_revision+1||!equal(read.state,expected))throw new Error("清理草稿回执不一致；输入保留。");
      if(this.serial===serial&&equal(this.view.state.drafts[id],sent)) {
        const state=structuredClone(this.view.state);delete state.drafts[id];this.publish({state});
      }
      this.publish({server:read,status:equal(this.view.state,read.state)?"ready":"unsaved",error:null});return true;
    } catch(error){
      const expected=structuredClone(server.state);delete expected.drafts[id];
      this.unknown={base:server,state:expected,cleared:{id,sent:structuredClone(sent)}};return this.fail(error);
    }
    finally{this.inFlight=null;}
  }
  /** Must be called by an explicit human action after presenting recovery_candidates. */
  async recover(action:"preserve"|"discard"):Promise<void> {
    const server=this.view.server;
    if(!server?.recovery_requires_confirmation||this.inFlight||this.readFlight||this.clearFlight)throw new Error("没有可确认的恢复候选，或请求仍在执行。");
    if(action==="discard"&&(Object.keys(server.recovery_candidates?.pending_machine??{}).length||Object.keys(server.recovery_candidates?.pending_reviews??{}).length||Object.values(server.recovery_candidates?.teaching_drafts??{}).some(d=>d.pending_record||d.preparation_attempt)))throw new Error("恢复候选含未确认的机器、复习或教学请求；请保留候选后核对回执，不能直接丢弃执行记录。");
    const serial=this.serial;
    const expected=action==="preserve"?server.recovery_candidates:empty();
    const run=this.transport.recover({...basis(server),action});this.inFlight=run;
    try {
      const read=assertUiWorkingState<WorkingRead>("Read",await run);
      if(!sameWorkspace(server,read)||read.recovery_requires_confirmation||read.state_revision!==server.state_revision+1||this.serial!==serial||!equal(read.state,expected))throw new Error("恢复确认期间本地输入或身份已变化；未自动应用。");
      if(Object.keys(this.view.state.drafts).length||Object.keys(this.view.state.teaching_drafts??{}).length||Object.keys(this.view.state.learning_drafts??{}).length||this.view.state.pending_original||Object.keys(this.view.state.pending_jobs??{}).length||Object.keys(this.view.state.pending_reviews??{}).length||Object.keys(this.view.state.pending_machine??{}).length) {
        this.unknown=null;this.publish({server:read,status:"blocked",error:"Core恢复候选已处理；现场另有本地草稿，请比较保全后再继续，未自动覆盖。"});return;
      }
      this.serial=0;this.unknown=null;this.publish({state:structuredClone(read.state),server:read,status:"ready",error:null});
    } catch(error){if(expected)this.unknown={base:server,state:expected};this.fail(error);}
    finally{this.inFlight=null;}
  }
}
