import type { JSONContent } from "@tiptap/core";
import type { UiWorkingStatePendingJob } from "../api/generated/ui-working-state-contract";
import { assertUiWorkingState } from "../api/generated/ui-working-state-contract";

export type WorkingEditor = JSONContent & {type:"doc";content:JSONContent[]};
export type WorkingDraft = {base_version:number;editor_json:WorkingEditor};
export type PendingOriginal = {create_request_id:string;title:string;editor_json:WorkingEditor};
export type PendingJob = UiWorkingStatePendingJob;
export type WorkingState = {drafts:Record<string,WorkingDraft>;opened_documents:string[];active_document:string|null;page_id:string|null;pending_original?:PendingOriginal|null;pending_jobs?:Record<string,PendingJob>};
export type WorkingRead = {schema:"archeaxis.ui-working-state/v1";workspace_id:string;restore_epoch:string;state_revision:number;state:WorkingState;draft_digests:Record<string,string>;pending_document_id:string|null;recovery_candidates:WorkingState|null;recovery_requires_confirmation:boolean};
type Basis = Pick<WorkingRead,"workspace_id"|"restore_epoch"|"state_revision">;
export type WorkingTransport = {
  read:()=>Promise<WorkingRead>;
  write:(request:Basis & {state:WorkingState})=>Promise<WorkingRead>;
  clearSaved:(request:Basis & {document_id:string;base_version:number;content_sha256:string;saved_version:number})=>Promise<WorkingRead>;
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
  private unknown:{base:WorkingRead;state:WorkingState;cleared?:{id:string;sent:WorkingDraft}}|null=null;
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
          if(pending.cleared&&equal(this.view.state.drafts[pending.cleared.id],pending.cleared.sent)) {
            const state=structuredClone(this.view.state);delete state.drafts[pending.cleared.id];this.publish({state});
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
  change(update:(state:WorkingState)=>void):void {
    const state=structuredClone(this.view.state);update(state);this.serial++;
    this.publish({state,status:this.view.status==="blocked"||this.view.status==="recovery"?this.view.status:"unsaved"});
  }
  rememberDraft(id:string,editor:WorkingEditor,baseVersion:number):void {this.change(state=>{state.drafts[id]={base_version:baseVersion,editor_json:structuredClone(editor)};});}
  rememberScene(page:string|null,id?:string):void {this.change(state=>{state.page_id=page;if(id){if(!state.opened_documents.includes(id))state.opened_documents.push(id);state.active_document=id;}});}
  async flush():Promise<WorkingRead> {
    if(this.readFlight)await this.readFlight;
    if(this.inFlight){await this.inFlight;return this.flush();}
    const server=this.view.server;
    if(!server||this.view.status==="blocked"||server.recovery_requires_confirmation)throw new Error("请先读取或明确恢复工作状态；本地输入保留。");
    if(equal(server.state,this.view.state))return server;
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
  async stageJob(entry:PendingJob):Promise<void> {
    const old=this.view.state.pending_jobs?.[entry.request_id];
    if(old&&!equal(old,entry))throw new Error("已有不同的冻结执行请求；未覆盖。");
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
    }catch(error){this.unknown={base:server,state:expected};this.fail(error);}finally{this.inFlight=null;}
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
    const serial=this.serial;
    const expected=action==="preserve"?server.recovery_candidates:empty();
    const run=this.transport.recover({...basis(server),action});this.inFlight=run;
    try {
      const read=assertUiWorkingState<WorkingRead>("Read",await run);
      if(!sameWorkspace(server,read)||read.recovery_requires_confirmation||read.state_revision!==server.state_revision+1||this.serial!==serial||!equal(read.state,expected))throw new Error("恢复确认期间本地输入或身份已变化；未自动应用。");
      if(Object.keys(this.view.state.drafts).length||this.view.state.pending_original||Object.keys(this.view.state.pending_jobs??{}).length) {
        this.unknown=null;this.publish({server:read,status:"blocked",error:"Core恢复候选已处理；现场另有本地草稿，请比较保全后再继续，未自动覆盖。"});return;
      }
      this.serial=0;this.unknown=null;this.publish({state:structuredClone(read.state),server:read,status:"ready",error:null});
    } catch(error){if(expected)this.unknown={base:server,state:expected};this.fail(error);}
    finally{this.inFlight=null;}
  }
}
