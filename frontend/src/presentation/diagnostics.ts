import { useSyncExternalStore } from "react";
import { coreFailureReason } from "./labels";
import type {FailureLogSnapshot, FailureLogOperation, FailureLogCode, FailureLogReason} from "../api/generated/core-contract";

export interface DiagnosticEntry {
  label: string;
  payload: unknown;
  at: string;
  sequence: number;
  category: DiagnosticCategory;
  summary?: string;
  occurrences?: number;
  automatic?: boolean;
  persisted?: boolean;
  historical?: boolean;
}
export const diagnosticCategories = {runtime: "运行与连接", operation: "操作与回执", data: "对象与来源"} as const;
export type DiagnosticCategory = keyof typeof diagnosticCategories;
type Persistence = "session" | "loading" | "ready" | "unavailable" | "corrupt" | "clearing";
type DiagnosticState = {entries: DiagnosticEntry[]; open: boolean; filter: DiagnosticCategory | "all"; selected: number | null; suspended: boolean; persistence: Persistence; persistenceFailure:"read"|"append"|"clear"|null};
const LIMIT = 50;
let state: DiagnosticState = {entries: [], open: false, filter: "all", selected: null, suspended: false, persistence:"session",persistenceFailure:null};
let memory: DiagnosticEntry[] = [];
let durable: DiagnosticEntry[] = [];
type Scope = {workspace_id:string; restore_epoch:string};
type Metadata = {operation:FailureLogOperation; status:number|null; code:FailureLogCode; reason:FailureLogReason};
type LogTransport = {read:(body:Scope)=>Promise<FailureLogSnapshot>; append:(body:Scope & Metadata & {log_generation:string})=>Promise<FailureLogSnapshot>; clear:(body:Scope & {log_generation:string|null})=>Promise<FailureLogSnapshot>};
type LogSession = {scope:Scope; transport:LogTransport; generation:string|null; ready:boolean; flushing:boolean; clearing:boolean; clearVersion:number; queue:Array<{sequence:number; token:number; metadata:Metadata}>; versions:Map<number,number>};
let persistent: LogSession|null=null;
let eventToken=0;
const listeners = new Set<() => void>();
let sequence = 0;
let opener: HTMLElement | null = null;
let observationEpoch = 0;
function update(patch: Partial<DiagnosticState>) {
  state = {...state, ...patch};
  for (const listener of listeners) listener();
}
const subscribe = (listener: () => void) => {listeners.add(listener); return () => {listeners.delete(listener);};};
const snapshot = () => state;

/** A request started in another workspace/recovery generation cannot publish here. */
export function beginDiagnosticObservation(): number | null {
  return state.suspended ? null : observationEpoch;
}

const operationLabels: Record<string, string> = {
  sources_list: "读取资料列表", source_get: "打开原件", source_original: "读取原件",
  documents_list: "读取文档列表", document_get: "打开文档", document_create: "新建文档",
  document_draft: "保存文档", document_restore: "恢复文档版本", search: "搜索内容",
  learning_items: "读取学习队列", learning_state: "读取学习记录", learning_review: "保存复习记录",
  machine_answer: "获取 AI 回答", machine_retest: "复测 AI 回答", machine_tasks_list: "读取 AI 任务",
  job_execute: "处理文件", job_execution_status: "查询文件处理进度", job_execution_cancel: "取消文件处理",
  model_configuration_get: "读取模型连接", model_configuration_put: "保存模型连接",
  workspace_backups: "读取备份列表", ui_state_read: "读取工作进度", ui_state_write: "保存工作进度",
  local_request: "连接本地服务", local_write: "保存本地内容",
};
function metadataReason(error:unknown):FailureLogReason {
  const e=error as {status?:unknown;code?:unknown;jobAdmission?:{schema?:unknown;admission_state?:unknown;enabled?:unknown;active_execution?:unknown};machineAdmission?:{schema?:unknown;execution_state?:unknown;prior_request_execution?:unknown};execution?:{execution_state?:unknown;answer_published?:unknown};machineFailure?:{execution_state?:unknown;answer_published?:unknown}}|null;
  if(!e||typeof e!=="object")return "unknown_result";
  if(e.jobAdmission?.schema==="archeaxis.job-admission-refusal/v1"&&e.jobAdmission.admission_state==="NOT_ADMITTED"&&e.jobAdmission.enabled===false&&e.jobAdmission.active_execution===false)return "not_admitted";
  if(e.machineAdmission?.schema==="archeaxis.context-admission-refusal/v1"&&e.machineAdmission.execution_state==="NOT_EXECUTED"&&e.machineAdmission.prior_request_execution==="UNVERIFIED")return "restored_authorization";
  if(e.execution?.execution_state==="EXECUTED_BUT_WITHHELD"&&e.execution.answer_published===false)return "withheld";
  if(e.machineFailure?.execution_state==="UNVERIFIED"&&e.machineFailure.answer_published===false)return "model_unconfirmed";
  if(e.code==="offline")return "offline";if(e.code==="migrating")return "migrating";if(e.code==="backend_starting")return "starting";
  if(e.status===409)return "conflict";if(e.code==="unauthorized")return "permission";if(e.status===404)return "missing";if(e.status===429)return "busy";if(e.code==="incompatible")return "incompatible";
  return "unknown_result";
}
function reasonSummary(reason:FailureLogReason):string {
  const errors:Partial<Record<FailureLogReason,unknown>>={offline:{code:"offline"},migrating:{code:"migrating"},starting:{code:"backend_starting"},conflict:{status:409},permission:{code:"unauthorized"},missing:{status:404},busy:{status:429},incompatible:{code:"incompatible"},not_admitted:{jobAdmission:{schema:"archeaxis.job-admission-refusal/v1",admission_state:"NOT_ADMITTED",enabled:false,active_execution:false}},restored_authorization:{machineAdmission:{schema:"archeaxis.context-admission-refusal/v1",execution_state:"NOT_EXECUTED",prior_request_execution:"UNVERIFIED"}},withheld:{execution:{execution_state:"EXECUTED_BUT_WITHHELD",answer_published:false}}};
  return reason==="model_unconfirmed"?"AI 处理结果尚未确认，请查看原任务的记录，避免重复执行。":coreFailureReason(errors[reason])??"这次操作的结果尚未确认，请查看当前页面的处理状态后再决定是否重试。";
}
function refresh(patch:Partial<DiagnosticState>={}) {
  const key=(e:DiagnosticEntry)=>{const p=e.payload as Partial<Metadata>;return JSON.stringify([p.operation,p.status,p.code,p.reason]);};
  const pending=new Set(memory.filter(e=>e.automatic).map(key));
  const entries=[...memory,...durable.filter(e=>e.historical||!pending.has(key(e)))].sort((a,b)=>Date.parse(b.at)-Date.parse(a.at)).slice(0,LIMIT);
  update({...patch,entries});
}
function accept(session:LogSession,snapshot:FailureLogSnapshot) {
  if(persistent!==session||state.suspended||snapshot.workspace_id!==session.scope.workspace_id||snapshot.restore_epoch!==session.scope.restore_epoch)throw new Error("Diagnostic scope changed");
  session.generation=snapshot.log_generation;session.ready=!snapshot.corrupt&&snapshot.log_generation!==null;
  durable=snapshot.entries.map(e=>{const summary=reasonSummary(e.reason);return {sequence:++sequence,label:operationLabels[e.operation]??"功能操作",payload:{operation:e.operation,status:e.status,code:e.code,reason:e.reason,summary},at:e.at,category:"operation",summary,occurrences:e.count,automatic:true,persisted:true,historical:e.restore_epoch!==snapshot.restore_epoch};});
  refresh({persistence:snapshot.corrupt?"corrupt":"ready",persistenceFailure:null});
}
async function flush(session:LogSession) {
  if(session.flushing||!session.ready||session.clearing||persistent!==session)return;
  session.flushing=true;
  let sentGeneration=session.generation, sentClearVersion=session.clearVersion;
  try {
    while(session.queue.length&&persistent===session&&!state.suspended&&!session.clearing&&session.generation) {
      const event=session.queue.shift()!;
      const generation=session.generation;
      sentGeneration=generation;sentClearVersion=session.clearVersion;
      const result=await session.transport.append({...session.scope,...event.metadata,log_generation:generation});
      if(persistent!==session||state.suspended||session.clearing||session.generation!==generation||session.clearVersion!==sentClearVersion)return;
      if(session.versions.get(event.sequence)===event.token){memory=memory.filter(e=>e.sequence!==event.sequence);session.versions.delete(event.sequence);}
      accept(session,result);
    }
  } catch {
    if(persistent===session&&!session.clearing&&session.generation===sentGeneration&&session.clearVersion===sentClearVersion){session.ready=false;session.queue=[];refresh({persistence:"unavailable",persistenceFailure:"append"});}
  } finally {session.flushing=false;if(session.queue.length&&session.ready&&!session.clearing&&persistent===session&&!state.suspended)void flush(session);}
}
/** Configured only after the existing workspace/recovery identity barrier. No raw receipt is sent. */
export function connectDiagnosticPersistence(scope:Scope,transport:LogTransport):void {
  if(state.suspended)return;
  if(persistent&&persistent.scope.workspace_id===scope.workspace_id&&persistent.scope.restore_epoch===scope.restore_epoch)return;
  const session:LogSession={scope:{...scope},transport,generation:null,ready:false,flushing:false,clearing:false,clearVersion:0,queue:[],versions:new Map()};persistent=session;
  refresh({persistence:"loading",persistenceFailure:null});
  void (async()=>{try{accept(session,await transport.read(session.scope));void flush(session);}catch{if(persistent===session)refresh({persistence:"unavailable",persistenceFailure:"read"});}})();
}
/** Explicit user read-back only: no replay of failed log appends or business actions. */
export function reloadDiagnosticPersistence():void {
  const previous=persistent;if(!previous||state.suspended||previous.clearing||state.persistence==="loading")return;
  persistent=null;connectDiagnosticPersistence(previous.scope,previous.transport);
}

/**
 * Automatic failures are bounded, session-local metadata. Never collect request
 * bodies, arbitrary exception messages, paths, credentials or stacks. Recording
 * does not open a dialog, move focus, retry a request or change its exception.
 */
export function recordDiagnosticFailure(operation: string, error: unknown, observed: number | null): void {
  try {
    if (observed === null || observed !== observationEpoch || state.suspended) return;
    const safeOperation:FailureLogOperation = Object.prototype.hasOwnProperty.call(operationLabels,operation) ? operation as FailureLogOperation : "unknown_operation";
    const value = error && typeof error === "object" ? error as {status?: unknown; code?: unknown} : null;
    const status = typeof value?.status === "number" && Number.isInteger(value.status) && value.status >= 0 && value.status <= 599 ? value.status : null;
    const code:FailureLogCode = typeof value?.code === "string" && ["offline", "backend_starting", "migrating", "incompatible", "unauthorized", "unavailable"].includes(value.code) ? value.code as FailureLogCode : "unknown";
    const summary = coreFailureReason(error) ?? "这次操作的结果尚未确认，请查看当前页面的处理状态后再决定是否重试。";
    const label = operationLabels[safeOperation] ?? "功能操作";
    const now = new Date();
    const reason=metadataReason(error);
    const payload = {operation: safeOperation, status, code, reason, summary};
    const previous = memory.find(entry => entry.automatic && entry.label === label && JSON.stringify(entry.payload) === JSON.stringify(payload) && now.getTime() - Date.parse(entry.at) < 30_000);
    const entry: DiagnosticEntry = {label, payload, summary, automatic: true, occurrences: (previous?.occurrences ?? 0) + 1, category: "operation", at: now.toISOString(), sequence: previous?.sequence ?? ++sequence};
    memory=[entry,...memory.filter(item=>item!==previous)].slice(0,LIMIT);refresh();
    const session=persistent;
    if(session&&(session.ready||state.persistence==="loading"||session.clearing)) {
      const token=++eventToken;session.versions.set(entry.sequence,token);session.versions=new Map([...session.versions].filter(([id])=>memory.some(e=>e.sequence===id)));session.queue.push({sequence:entry.sequence,token,metadata:{operation:safeOperation,status,code,reason}});session.queue=session.queue.slice(-LIMIT);void flush(session);
    }
  } catch { /* Logging must never replace the original business result or error. */ }
}

/**
 * Raw backend payloads belong in a diagnostic channel, not in the reading surface.
 * Session-local observations only: never persist or mirror full receipts to console.
 * Publications are explicit user clicks, not asynchronous completion handlers.
 */
export function publishDiagnostic(label: string, payload: unknown, category: DiagnosticCategory = "operation", trigger?: HTMLElement): void {
  if (state.suspended) return;
  const entry: DiagnosticEntry = {label, payload, category, at: new Date().toISOString(), sequence: ++sequence};
  opener = trigger ?? (document.activeElement instanceof HTMLElement ? document.activeElement : null);
  memory=[entry,...memory].slice(0,LIMIT);refresh({open: true, filter: category, selected: entry.sequence});
}
export function openDiagnostics(trigger: HTMLElement): void {
  if (state.suspended) return;
  opener = trigger;
  update({open: true});
}
export function closeDiagnostics(): void {update({open: false});}
export function restoreDiagnosticFocus(): void {
  const usable = (element: HTMLElement | null): element is HTMLElement => {
    if (!element?.isConnected || element.closest('[hidden],[inert],[aria-hidden="true"]') || element.matches(':disabled')) return false;
    for (let node: HTMLElement | null = element; node; node = node.parentElement) {
      const style = getComputedStyle(node);
      if (style.display === "none" || style.visibility === "hidden") return false;
    }
    return true;
  };
  const target = usable(opener) ? opener : document.querySelector<HTMLElement>('[data-diagnostic-trigger="true"]');
  if (!state.suspended && usable(target)) target.focus();
  opener = null;
}
export function setDiagnosticFilter(filter: DiagnosticState["filter"]): void {update({filter});}
export async function clearDiagnostics(): Promise<void> {
  const session=persistent;
  if(!session){memory=[];durable=[];refresh({selected:null,filter:"all"});return;}
  if(session.clearing||state.persistence==="loading")return;
  const clearedMemory=new Set(memory);
  session.clearing=true;session.clearVersion++;session.queue=[];refresh({persistence:"clearing"});
  try {const result=await session.transport.clear({...session.scope,log_generation:session.generation});if(persistent!==session||state.suspended)return;memory=memory.filter(e=>!clearedMemory.has(e));session.versions=new Map([...session.versions].filter(([id])=>memory.some(e=>e.sequence===id)));session.clearing=false;accept(session,result);refresh({selected:null,filter:"all"});void flush(session);}
  catch {if(persistent===session){session.clearing=false;session.ready=false;refresh({persistence:"unavailable",persistenceFailure:"clear"});}}
}
export function resetDiagnostics(): void {observationEpoch++;opener=null;persistent=null;memory=[];durable=[];update({entries:[],open:false,filter:"all",selected:null,suspended:false,persistence:"session",persistenceFailure:null});}
export function suspendDiagnostics(): void {if (!state.suspended) observationEpoch++;persistent=null;update({open:false,suspended:true,persistence:"session",persistenceFailure:null});}
export function resumeDiagnostics(): void {update({suspended: false});}
export function useDiagnosticState(): DiagnosticState {return useSyncExternalStore(subscribe, snapshot, snapshot);}
export function useDiagnostics(): DiagnosticEntry[] {return useDiagnosticState().entries;}
