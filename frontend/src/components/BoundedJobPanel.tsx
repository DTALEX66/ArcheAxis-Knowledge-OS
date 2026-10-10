import { folderJobStatus } from "../presentation/folderIngestExecution";
import { useJobJournal, JobJournalRecovery } from "../presentation/useJobJournal";
import type { PendingJob } from "../presentation/coreWorkingState";
import { useEffect, useId, useRef, useState } from "react";
import type { SourcesListDto, SourceJobsDto } from "../api/generated/core-contract";

/** Integration port: add these finite operations to generated Core/native contracts first. */
export type BoundedJobOperation = "sources_list" | "source_jobs" | "jobs_get" | "job_execute" | "job_execution_status" | "job_execution_cancel";
export type BoundedJobCommand = (operation: BoundedJobOperation, payload: Record<string, unknown>) => Promise<unknown>;
export type JobStatus = { job_id: string; input_ref: string; state: string; attempt: number | null; request_id: string | null; error: string | null; [key: string]: unknown };
type Attempt = { job_id: string; request_id: string; body: { deadline_ms: number; split: boolean; words: boolean } };
const terminal = (state: string) => ["succeeded", "failed", "cancelled", "rejected"].includes(state);
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("响应结构无效");
  return value as Record<string, unknown>;
}
function statusOf(value: unknown, job: string, source: string): JobStatus {
  const row = object(value);
  if (row.job_id !== job || row.input_ref !== source || typeof row.state !== "string"
    || !(row.attempt === null || (Number.isSafeInteger(row.attempt) && Number(row.attempt) > 0))
    || !(row.request_id === null || typeof row.request_id === "string")
    || !(row.error === null || typeof row.error === "string")) throw new Error("任务状态身份不匹配");
  return row as JobStatus;
}

export function BoundedJobPanel({ command, pollMs = 1000 }: { command: BoundedJobCommand; pollMs?: number }) {
  const journal=useJobJournal("bounded");
  const restoreEntry=useRef<PendingJob|null>(null);
  const owner = `bounded-job-${useId()}`;
  const [sources, setSources] = useState<SourcesListDto["sources"]>([]);
  const [sourceId, setSourceId] = useState("");
  const [jobs, setJobs] = useState<SourceJobsDto["jobs"]>([]);
  const [capped, setCapped] = useState(false);
  const [jobId, setJobId] = useState("");
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [deadline, setDeadline] = useState("60000");
  const [split, setSplit] = useState(false);
  const [words, setWords] = useState(false);
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [uncertain, setUncertain] = useState(false);
  const [cancelPending, setCancelPending] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const epoch = useRef(0), alive = useRef(true), readSerial = useRef(0), action = useRef(false);
  const currentAttempt = useRef(attempt); currentAttempt.current = attempt;
  const cancelRequest = useRef<string | null>(null);
  const polling = useRef(false);
  const selectedJob = jobs.find(row => row.job_id === jobId);
  const currentReceipt = status && Array.isArray(status.attempts) ? status.attempts.find(value => value && typeof value === "object" && (value as Record<string, unknown>).attempt === status.attempt) as Record<string, unknown> | undefined : undefined;
  const continuation = currentReceipt?.continuation && typeof currentReceipt.continuation === "object" ? currentReceipt.continuation as Record<string, unknown> : undefined;
  const pending = uncertain || cancelPending || !!attempt && !(status && terminal(status.state) && status.request_id === attempt.request_id);
  const dirty = deadline !== "60000" || split || words || pending;
  useEffect(() => { window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: { owner, dirty } })); }, [owner, dirty]);
  useEffect(() => () => { window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: { owner, dirty: false } })); }, [owner]);
  useEffect(() => {
    alive.current = true;
    command("sources_list", {}).then(value => {
      const row = object(value); if (!Array.isArray(row.sources)) throw new Error("来源列表无效");
      if (alive.current) setSources(row.sources as SourcesListDto["sources"]);
    }).catch(() => { if (alive.current) setMessage("来源列表读取失败；不会自动创建任务。"); });
    return () => { alive.current = false; epoch.current++; };
  }, [command]);
  useEffect(() => {
    const generation = ++epoch.current; ++readSerial.current;
    setJobs([]); setJobId(""); setStatus(null); setCapped(false); setAttempt(null); setUncertain(false); setCancelPending(false); cancelRequest.current = null;
    if (!sourceId) return;
    command("source_jobs", { source_id: sourceId }).then(value => {
      const row = object(value);
      if (row.source_id !== sourceId || !Array.isArray(row.jobs) || row.jobs.length > 50 || row.jobs.some(raw => object(raw).input_ref !== sourceId)) throw new Error("来源任务不匹配");
      if (alive.current && generation === epoch.current) { setJobs(row.jobs as SourceJobsDto["jobs"]); setCapped(row.jobs_capped === true);if(restoreEntry.current?.source_id===sourceId)setJobId(restoreEntry.current.job_id); }
    }).catch(() => { if (alive.current && generation === epoch.current) setMessage("来源任务读取失败；保留预算设置。"); });
  }, [command, sourceId]);
  async function refresh(job = jobId, source = sourceId, generation = epoch.current, initial = false) {
    const serial = ++readSerial.current;
    try {
      const value = statusOf(await command(initial ? "jobs_get" : "job_execution_status", { job_id: job }), job, source);
      if (!alive.current || generation !== epoch.current || serial !== readSerial.current) return;
      const frozen = currentAttempt.current;
      if(frozen&&journal.available){
        folderJobStatus(value,job,source,frozen);
        const binding=journal.entries.find(entry=>entry.request_id===frozen.request_id);
        if(!binding||value.kind!==binding.kind)throw new Error("冻结作业种类不匹配");
      }
      const expectedRequest = frozen?.request_id ?? cancelRequest.current;
      if (expectedRequest && value.request_id !== expectedRequest) throw new Error("当前任务已是另一请求；保留原请求回执");
      setStatus(value);
      if (!frozen && terminal(value.state)) setCancelPending(false);
      if(frozen&&journal.available&&terminal(value.state)&&value.request_id===frozen.request_id){
        await journal.clear(frozen.request_id);
        if(!alive.current||generation!==epoch.current||serial!==readSerial.current)return;
      }
      if (frozen && value.request_id === frozen.request_id) {
        setUncertain(false);
        if (terminal(value.state)) setCancelPending(false);
      }
    } catch (error) {
      if (alive.current && generation === epoch.current && serial === readSerial.current) setMessage(`状态读回未确认：${String(error)}；已有回执与检查点保留。`);
    }
  }
  useEffect(() => {
    if (!jobId) return;
    const generation = ++epoch.current; ++readSerial.current;
    setStatus(null); setAttempt(null); setUncertain(false); setCancelPending(false); cancelRequest.current = null; setSplit(false); setWords(false);
    const restored=restoreEntry.current;
    if(restored?.job_id===jobId&&restored.source_id===sourceId){
      const frozen={job_id:restored.job_id,request_id:restored.request_id,body:restored.body};
      currentAttempt.current=frozen;setAttempt(frozen);setUncertain(true);setDeadline(String(restored.body.deadline_ms));setSplit(restored.body.split);setWords(restored.body.words);restoreEntry.current=null;
    }else currentAttempt.current=null;
    void refresh(jobId, sourceId, generation, true).then(() => {
      if (alive.current && generation === epoch.current) return refresh(jobId, sourceId, generation);
    });
  }, [jobId]);
  useEffect(() => {
    if (!jobId || !(pending || status?.state === "running")) return;
    const timer = window.setInterval(() => {
      if (polling.current) return;
      polling.current = true;
      void refresh().finally(() => { polling.current = false; });
    }, Math.max(250, pollMs));
    return () => window.clearInterval(timer);
  }, [jobId, sourceId, pending, status?.state, command, pollMs]);
  async function execute(retry: boolean) {
    if (action.current || !jobId) return;
    const budget = Number(deadline);
    if (!retry && (!/^\d+$/.test(deadline) || !Number.isSafeInteger(budget) || budget < 1 || budget > 300000)) { setMessage("预算必须为 1..300000 的整数毫秒。"); return; }
    const frozen = retry ? currentAttempt.current : { job_id: jobId, request_id: `job_${crypto.randomUUID()}`, body: { deadline_ms: budget, split: selectedJob?.kind === "transcribe" && split, words: selectedJob?.kind === "transcribe" && words } };
    if (!frozen) return;
    action.current = true; setBusy(true); setAttempt(frozen); currentAttempt.current = frozen; setUncertain(true);
    const generation = epoch.current;
    try {
      const selected=sources.find(row=>row.source_id===sourceId);
      if(journal.available&&(!selected?.source_revision||!selectedJob?.kind))throw new Error("来源指纹或作业种类未读回。");
      if(selected&&selectedJob)await journal.stage({source_id:sourceId,source_revision:selected.source_revision,kind:selectedJob.kind,job_id:frozen.job_id,request_id:frozen.request_id,body:frozen.body,mode:frozen.body.split?"split":"single",relative:null});
      if(!alive.current||generation!==epoch.current)return;
      const receipt = object(await command("job_execute", { ...frozen }));
      if (receipt.job_id !== frozen.job_id || receipt.request_id !== frozen.request_id || typeof receipt.state !== "string") throw new Error("执行回执身份不匹配");
      if (alive.current && generation === epoch.current) { setMessage("执行请求已读回；以持久化状态确认结果。"); await refresh(); }
    } catch {
      if (alive.current && generation === epoch.current) setMessage("执行未确认；请用同一请求重试或读取状态，不能改预算产生另一请求。");
    } finally { action.current = false; if (alive.current && generation === epoch.current) setBusy(false); }
  }
  async function cancel() {
    const request = currentAttempt.current?.request_id ?? status?.request_id;
    if (action.current || !request || !jobId) return;
    const generation = epoch.current; action.current = true; setBusy(true); setCancelPending(true); cancelRequest.current = request;
    try {
      const receipt = object(await command("job_execution_cancel", { job_id: jobId, request_id: request }));
      if (receipt.job_id !== jobId || receipt.request_id !== request || typeof receipt.cancel_requested !== "boolean") throw new Error("取消回执身份不匹配");
      if (alive.current && generation === epoch.current) { setMessage("取消请求已接收或此前已终止；尚须状态读回确认。202 不等于已取消。"); await refresh(); }
    } catch { if (alive.current && generation === epoch.current) setMessage("取消请求未确认；保留请求身份，请重试取消或读取状态。"); }
    finally { action.current = false; if (alive.current && generation === epoch.current) setBusy(false); }
  }
  const locked = busy || pending || status?.state === "running";
  return <section aria-label="受限任务执行"><JobJournalRecovery entries={journal.entries} disabled={busy||journal.blocked} onRestore={entry=>{if(currentAttempt.current&&currentAttempt.current.request_id!==entry.request_id)return;restoreEntry.current=entry;if(sourceId!==entry.source_id)setSourceId(entry.source_id);else if(jobId!==entry.job_id)setJobId(entry.job_id);else{const frozen={job_id:entry.job_id,request_id:entry.request_id,body:entry.body};currentAttempt.current=frozen;setAttempt(frozen);setUncertain(true);setDeadline(String(entry.body.deadline_ms));setSplit(entry.body.split);setWords(entry.body.words);restoreEntry.current=null;}setMessage("冻结身份已从 Core 恢复；只读取状态，不自动执行或启用能力。");}} onAbandon={async entry=>{await journal.clear(entry.request_id,"abandon_unadmitted");if(alive.current&&currentAttempt.current?.request_id===entry.request_id){currentAttempt.current=null;setAttempt(null);setUncertain(false);}}}/>
    <h2>受限任务与检查点</h2>
    {message ? <p role="status">{message}</p> : null}
    <p>仅执行已保存的 Core job。机器回执历史单独保留；不授予通用 Agent 权限。</p>
    <label>已保存来源 <select value={sourceId} disabled={locked} onChange={event => { setSourceId(event.target.value); setMessage(""); }}><option value="">选择来源</option>{sources.map(row => <option key={row.source_id} value={row.source_id}>{row.original_name} · {row.source_id}</option>)}</select></label>
    <label>来源任务 <select value={jobId} disabled={locked} onChange={event => { setJobId(event.target.value); setMessage(""); }}><option value="">选择任务</option>{jobs.map(row => <option key={row.job_id} value={row.job_id}>{row.kind} · {row.job_id} · {row.state}</option>)}</select></label>
    {capped ? <p>只列最近 50 个来源任务；未列出不表示不存在。</p> : null}
    <label>单次预算（毫秒）<input type="number" min={1} max={300000} step={1} value={deadline} disabled={locked} onChange={event => setDeadline(event.target.value)} /></label>
    <label><input type="checkbox" checked={split} disabled={locked || selectedJob?.kind !== "transcribe"} onChange={event => setSplit(event.target.checked)} />媒体分段（窗口计划由 Core 决定）</label>
    <label><input type="checkbox" checked={words} disabled={locked || selectedJob?.kind !== "transcribe"} onChange={event => setWords(event.target.checked)} />词级时间</label>
    <button disabled={!status || locked || !["queued", "pending"].includes(status.state)} onClick={() => void execute(false)}>执行已保存任务</button>
    <button disabled={!attempt || !uncertain || busy} onClick={() => void execute(true)}>同请求重试</button>
    <button disabled={locked || !status || !["failed", "cancelled"].includes(status.state) || continuation?.new_attempt_eligible_state !== true} onClick={() => void execute(false)}>新请求重试（不等于检查点恢复）</button>
    <button disabled={!jobId || busy} onClick={() => void refresh()}>刷新实际状态</button>
    <button disabled={busy || !(status?.state === "running" || pending) || !(attempt?.request_id || status?.request_id)} onClick={() => void cancel()}>请求取消</button>
    {cancelPending ? <p>取消待确认：继续轮询实际状态。</p> : null}
    {attempt ? <p>冻结请求 {attempt.request_id} · {attempt.body.deadline_ms} ms</p> : null}
    {currentReceipt ? <><h3>实际尝试步骤与提交记录</h3><pre aria-label="实际预算与步骤">{JSON.stringify({budget:currentReceipt.budget,steps:currentReceipt.steps},null,2)}</pre><pre aria-label="已提交检查点">{JSON.stringify(currentReceipt.checkpoint,null,2)}</pre><pre aria-label="继续条件">{JSON.stringify(currentReceipt.continuation,null,2)}</pre><p>CORE_COMMITTED 只表示这些 Core 提交记录。NOT_OBSERVED 不等于无数据；NOT_SUPPORTED 不支持检查点恢复。新请求仍须当前来源、能力与路由通过 Core 校验。</p></> : <p>当前接口未提供预算、步骤或检查点明细，不能推导进度或保证可恢复。</p>}
    {status ? <><dl><dt>任务</dt><dd>{status.job_id}</dd><dt>实际 attempt</dt><dd>{status.attempt ?? "未提供"}</dd><dt>实际 request_id</dt><dd>{status.request_id ?? "未提供"}</dd><dt>状态</dt><dd>{status.state}</dd><dt>错误</dt><dd>{status.error ?? "未提供"}</dd></dl><details><summary>完整状态与检查点回执</summary><pre>{JSON.stringify(status, null, 2)}</pre></details>{["failed", "cancelled", "rejected"].includes(status.state) ? <p>此尝试已终止，原提交记录与错误保留。只有 Core 提供当前新尝试条件时才开放新请求重试；它不是同请求重放，也不自动证明媒体检查点已恢复。</p> : null}</> : null}
  </section>;
}
