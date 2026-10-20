import { useOptionalCoreWorkingState } from "./useCoreWorkingState";
import type { PendingJob } from "./coreWorkingState";
import { useState } from "react";
import { RawReceiptButton } from "../components/DiagnosticConsole";

export function useJobJournal(surface:PendingJob["surface"]) {
  const working=useOptionalCoreWorkingState();
  const allEntries=Object.values(working?.state.pending_jobs??{});
  const entries=allEntries.filter(entry=>entry.surface===surface);
  function getJobOwner(jobId:string) {
    return Object.values(working?.session.getSnapshot().state.pending_jobs??{}).find(entry=>entry.job_id===jobId);
  }
  function assertReady() {
    if(!working){if(window.__TAURI__)throw new Error("执行需要 Core 工作状态保全。");return;}
    if(!working.server||working.server.recovery_requires_confirmation||["blocked","recovery","loading"].includes(working.status))throw new Error("请先核对 Core 工作状态；未发送执行请求。");
  }
  async function stage(entry:Omit<PendingJob,"surface"|"origin_restore_epoch">) {
    assertReady();if(!working)return;
    const existing=working.session.getSnapshot().state.pending_jobs?.[entry.request_id];
    if(existing?.origin_restore_epoch!==undefined&&existing.origin_restore_epoch!==working.server!.restore_epoch)throw new Error("冻结请求来自恢复前现场，历史执行 UNVERIFIED；仅允许核对状态或已记录终态，不自动重放。");
    await working.session.stageJob({...entry,surface:existing?.surface??surface,origin_restore_epoch:working.server!.restore_epoch});
  }
  async function clear(request:string,action:"terminal"|"abandon_unadmitted"="terminal") {
    assertReady();if(!working)return;
    const entry=working.session.getSnapshot().state.pending_jobs?.[request];
    if(!entry)throw new Error("执行日志身份未读回；冻结现场保留。");
    await working.session.clearJob(entry,action);
  }
  return {entries,allEntries,getJobOwner,stage,clear,available:!!working,blocked:!!working&&(!working.server||working.server.recovery_requires_confirmation||["blocked","recovery","loading"].includes(working.status))};
}

/** Restores a rendered scene only. Never dispatches an execution or relies on an old enable proof. */
export function JobJournalRecovery({entries,disabled,onRestore,onAbandon}:{entries:PendingJob[];disabled?:boolean;onRestore:(entry:PendingJob)=>void;onAbandon:(entry:PendingJob)=>Promise<void>}) {
  const [busy,setBusy]=useState(false),[error,setError]=useState("");
  return entries.length?<section aria-label="待确认的处理任务"><p>这些任务已保存。恢复后先查看原进度；继续处理、取消或启用能力都需要你另行操作。</p>{error?<p role="alert">{error}</p>:null}{entries.map((entry,index)=><div key={entry.request_id} data-recovery-request={entry.request_id}><p>待确认任务 {index+1}</p><RawReceiptButton label={`处理任务 ${index+1} 的执行记录`} payload={entry}/><button data-recovery-action="restore" disabled={disabled||busy} onClick={()=>onRestore(structuredClone(entry))}>恢复处理任务 {index+1}</button><button disabled={disabled||busy} onClick={()=>{setBusy(true);setError("");void onAbandon(entry).catch(()=>setError("尚未确认任务是否开始，原记录已保留。请先查看进度；已开始的任务需要明确取消。" )).finally(()=>setBusy(false));}}>放弃尚未开始的任务 {index+1}</button></div>)}</section>:null;
}
