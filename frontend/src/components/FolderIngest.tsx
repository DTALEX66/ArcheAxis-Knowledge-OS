import type { FolderMemberSelection } from "../presentation/ingestRelations";
import { useJobJournal, JobJournalRecovery } from "../presentation/useJobJournal";
import { useEffect, useId, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import type { IngestBatchDto, IngestBatchesDto, IngestBatchSummaryDto } from "../api/generated/core-contract";
import { ApiError, type JobAdmissionRefusal } from "../api/client";
import { FrozenCapabilityRecovery } from "./FrozenCapabilityRecovery";
import { recoverableJobRefusal } from "../api/jobAdmission";
import { conversionKindFor } from "../api/conversionKinds";
import { confirmedImport, type ImportReceipt } from "../presentation/importReceipt";
import { sha256 as contentSha256 } from "../presentation/exchangeProof";
import { RawReceiptButton } from "./DiagnosticConsole";
import { failureMessage, userErrorMessage } from "../presentation/labels";
import { conversionRecovery } from "../presentation/conversionRecovery";
import { ConversionRecoveryNotice } from "./ConversionRecoveryNotice";
import type { BoundedJobCommand, JobStatus } from "./BoundedJobPanel";
import { freezeFolderAttempt, folderCancelAck, folderExecutionAck, freshAttemptEligible, jobState, pollFolderAttempt, readFolderStatus, terminalJobState, type FolderAttempt, type JobState } from "../presentation/folderIngestExecution";

const MAX_FILES = 200; // per-batch budget; already-handled and explicitly-excluded items never re-consume it
const MAX_BYTES = 64 * 1024 * 1024;
const EXCLUDED_DIRS = new Set([".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv",
  ".project-local", ".hermes", ".cache", "dist", "build", "target"]);
// Compared case-insensitively, matching `directory_batch.py`'s `part.casefold()` rule; on Windows
// the file system is case-insensitive, so `.CODEX` is the same private state as `.codex`.
const PRIVATE_STATE = new Set([".zcode", ".codex", ".hermes", ".openhuman", ".git"]);

type RefusalState = "跳过：隐藏路径" | "跳过：排除目录" | "未导入：超过大小上限";
type Refusal = { relative: string; bytes: number; state: RefusalState; detail: string };
type RowState = JobState | RefusalState | "UNKNOWN" | "ORIGINAL_ONLY" | "IMPORT_FAILED" | "ENQUEUE_FAILED" | "IDENTITY_CONFLICT";
type Row = { key: string; batch_id: string; relative: string; bytes: number; state: RowState; detail: string; last_error_message?: string;
  source_id?: string; sha256?: string; job_id?: string; kind?: string; status?: JobStatus;
  attempt?: FolderAttempt; cancelPending?: boolean; executionRefused?: boolean; admissionProof?:JobAdmissionRefusal; capabilityBusy?:boolean };
const LABEL: Record<RowState, string> = {
  queued:"已入队", pending:"已入队", running:"作业运行中", leased:"作业运行中", starting:"作业运行中",
  succeeded:"已成功", failed:"失败待处理", cancelled:"已取消", rejected:"已拒绝",
  UNKNOWN:"处理结果待确认", ORIGINAL_ONLY:"原件已保管，无转换通路", IMPORT_FAILED:"原件导入未确认",
  ENQUEUE_FAILED:"转换未入队", IDENTITY_CONFLICT:"作业身份冲突",
  "跳过：隐藏路径":"跳过：隐藏路径", "跳过：排除目录":"跳过：排除目录", "未导入：超过大小上限":"未导入：超过大小上限",
};

function folderFailureSummary(status: JobStatus): string {
  const fallback = "转换未完成，请查看诊断详情核对原因。";
  if (status.state !== "failed" || !status.error) return fallback;
  const recovery = conversionRecovery(status);
  if (recovery) return recovery.summary;
  const safeSummary = (message: unknown) => {
    const summary = userErrorMessage(message);
    return summary === userErrorMessage(null) ? fallback : summary;
  };
  const error = status.error.trim();
  if (!error.startsWith("{")) return safeSummary(error);
  try {
    const result = JSON.parse(error);
    // The outer status has already passed readFolderStatus's row/source checks.
    // An embedded worker response must also belong to this exact failed attempt.
    if (!result || result.schema !== "archeaxis.worker-response/v1" || result.type !== "job_result"
      || result.status !== "failed" || result.job_id !== status.job_id
      || !status.request_id || result.request_id !== status.request_id
      || !Number.isSafeInteger(status.attempt) || Number(status.attempt) < 1 || result.attempt !== status.attempt
      || !result.error || typeof result.error.code !== "string" || typeof result.error.message !== "string"
      || typeof result.error.retryable !== "boolean") return fallback;
    if (result.error.code === "AAK-WORKER-003" && result.error.message === "File is not a zip file") {
      return "文档结构无法读取，请检查文件格式或文件是否损坏。";
    }
    return safeSummary(result.error.message);
  } catch { return fallback; }
}
// Stable module-level finite port: no component render changes the command identity.
const folderCommand: BoundedJobCommand = (operation, payload) => coreCommand(operation, payload);

function base64Of(buffer: ArrayBuffer): string {
  const content = new Uint8Array(buffer);
  let binary = "";
  for (let offset = 0; offset < content.length; offset += 8192) {
    binary += String.fromCharCode(...content.subarray(offset, offset + 8192));
  }
  return btoa(binary);
}

/** The picked folder's own name, or null when the selection does not look like one folder. */
function folderOf(files: File[]): string | null {
  const roots = new Set(files.map((file) => (file.webkitRelativePath || file.name).split("/")[0]));
  return roots.size === 1 ? [...roots][0] : null;
}

/** The path stored as the original's name: inside the folder, without the folder's own name. */
function relativeOf(file: File): string {
  const path = file.webkitRelativePath || file.name;
  const parts = path.split("/");
  return parts.length > 1 ? parts.slice(1).join("/") : path;
}

/** The full visible path the picker handed over, including the root folder's own name. */
function visiblePathOf(file: File): string {
  return file.webkitRelativePath || file.name;
}

/** A private-state segment anywhere in the visible path, root name included, case-insensitively. */
function privateVisibleSegment(file: File): string | null {
  return (visiblePathOf(file).split("/").find((part) => PRIVATE_STATE.has(part.toLowerCase())) ?? null);
}

function refuseBeforeUpload(relative: string, bytes: number): Refusal | null {
  const segments = relative.split("/");
  if (segments.some((part) => part.startsWith("."))) {
    return { relative, bytes, state: "跳过：隐藏路径", detail: "以点开头的路径不进入原件库。" };
  }
  if (segments.some((part) => EXCLUDED_DIRS.has(part.toLowerCase()))) {
    return { relative, bytes, state: "跳过：排除目录", detail: "构建与依赖目录不是用户的文档。" };
  }
  if (bytes > MAX_BYTES) {
    return { relative, bytes, state: "未导入：超过大小上限", detail: `原件导入上限为 ${MAX_BYTES / 1024 / 1024} MiB。` };
  }
  return null;
}

export function FolderIngest({ onOpenSource, onSelectRelations }: { onOpenSource?: (sourceId: string, jobId?: string, revision?:string) => void; onSelectRelations?:(selection:FolderMemberSelection)=>void }) {
  const journal=useJobJournal("folder");
  const [rows, setRows] = useState<Row[]>([]), [folder, setFolder] = useState<string | null>(null);
  const [batchId, setBatchId] = useState<string | null>(null), [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false), [remaining, setRemaining] = useState(0), [cancelBusy, setCancelBusy] = useState(false);
  const rowsRef = useRef<Row[]>([]), queue = useRef(new Map<string, File>()), handled = useRef(new Set<string>());
  const folderRef = useRef<string | null>(null), batchRef = useRef<string | null>(null);
  const running = useRef(false), stopAfter = useRef(false), cancelFlight = useRef(false);
  const capabilityFlight = useRef(false);
  const mounted = useRef(true), epoch = useRef(0), active = useRef<{ key: string; attempt: FolderAttempt } | null>(null);
  const timers = useRef(new Map<number, () => void>()), callback = useRef(onOpenSource); callback.current = onOpenSource;
  const owner = `folder-ingest-${useId()}`;
  const durable = useRef<IngestBatchDto | null>(null);
  const [failure,setFailure]=useState<unknown>(null);
  useEffect(()=>{setFailure(null);},[batchId]);
  function reportFailure(error:unknown){setFailure(error instanceof Error?{name:error.name,message:error.message}:error);return failureMessage(error);}
  const ordinals = useRef(new Map<string, number>());
  const [history,setHistory]=useState<IngestBatchSummaryDto[]>([]),[historyCursor,setHistoryCursor]=useState<string|null>(null);
  const [needsFiles,setNeedsFiles]=useState(false),[manifestPending,setManifestPending]=useState(false);
  const registration=useRef<Record<string,unknown>[]|null>(null);
  async function historyPage(cursor?:string){
    const generation=lock();if(generation===null)return;
    try{
      const page=await coreCommand<IngestBatchesDto>("ingest_batches_list",cursor?{cursor}:{});
      if(!current(generation))return;
      setHistory(old=>cursor?[...old,...page.batches]:page.batches);setHistoryCursor(page.next_cursor);
    }catch(error){if(current(generation))setMessage(`历史批次未读回：${reportFailure(error)}`);}
    finally{unlock(generation);}
  }
  async function restoreBatch(batch:string){
    const generation=lock();if(generation===null)return;
    try{
      let page=await coreCommand<IngestBatchDto>("ingest_batch_get",{batch_id:batch});
      const head=page, members=[...page.members];
      while(page.next_ordinal!==null){
        page=await coreCommand<IngestBatchDto>("ingest_batch_get",{batch_id:batch,after_ordinal:page.next_ordinal});
        if(page.workspace_id!==head.workspace_id||page.restore_epoch!==head.restore_epoch||members.length>=10000)throw new Error("工作区恢复身份已变化，请重新读取。");
        members.push(...page.members);
      }
      if(!current(generation))return;
      durable.current={...head,members};registration.current=null;setManifestPending(false);
      batchRef.current=batch;folderRef.current=head.folder_label;setBatchId(batch);setFolder(head.folder_label);
      queue.current.clear();handled.current.clear();ordinals.current.clear();setRemaining(0);
      for(const m of members){
        ordinals.current.set(m.relative_path,m.ordinal);
        const refusal=refuseBeforeUpload(m.relative_path,m.byte_length);
        replace({key:`${batch}:${m.relative_path}`,batch_id:batch,relative:m.relative_path,bytes:m.byte_length,
          source_id:m.source_id??undefined,sha256:m.source_revision??undefined,job_id:m.job_id??undefined,kind:m.kind??undefined,
          state:refusal?.state??(m.job_id?jobState(m.job_state):m.source_id?"ORIGINAL_ONLY":"IMPORT_FAILED"),
          detail:refusal?.detail??(m.source_id?"已读取保存的原件和处理状态；未自动执行。":"原文件内容未上传；需重新选择文件夹。")});
        if(m.source_id||refusal)handled.current.add(m.relative_path);
      }
      setNeedsFiles(members.some(m=>!m.source_id&&m.disposition==="pending")||!head.complete);
      setMessage("历史成员、来源与作业已读取；浏览器文件句柄不能重启恢复，未上传内容需重新选择。读取不会执行。");
    }catch(error){if(current(generation))setMessage(`批次未完整读回：${reportFailure(error)}`);}
    finally{unlock(generation);}
  }
  async function registerSelection(){
    const generation=lock();if(generation===null)return;
    let ready=false;
    try{
      if(!registration.current){
        const identity=durable.current??await coreCommand<IngestBatchesDto>("ingest_batches_list",{});
        if(!current(generation))return;
        const files=[...queue.current.entries()].sort(([a],[b])=>a<b?-1:a>b?1:0);
        const members=files.map(([relative,file],ordinal)=>{
          ordinals.current.set(relative,ordinal);
          const state=refuseBeforeUpload(relative,file.size)?.state;
          return {ordinal,relative_path:relative,byte_length:file.size,disposition:state==="跳过：隐藏路径"?"excluded_hidden":state==="跳过：排除目录"?"excluded_directory":state?"too_large":"pending"};
        });
        registration.current=[];
        for(let offset=0;offset<members.length;offset+=200)registration.current.push({
          workspace_id:identity.workspace_id,restore_epoch:identity.restore_epoch,batch_id:batchRef.current,
          folder_label:folderRef.current,expected_members:members.length,members:members.slice(offset,offset+200),
        });
      }
      for(const body of registration.current){
        if(stopAfter.current)throw new Error("已停止后续清单登记；原批次保留。");
        const receipt=await coreCommand<IngestBatchDto>("ingest_batch_register",{body});
        if(!current(generation))return;
        if(receipt.batch_id!==batchRef.current||receipt.workspace_id!==body.workspace_id||receipt.restore_epoch!==body.restore_epoch)throw new Error("批次登记回执身份不匹配");
        durable.current=receipt;
      }
      if(!durable.current?.complete)throw new Error("清单尚不完整；未上传或入队。");
      registration.current=null;setManifestPending(false);setNeedsFiles(false);
      if(stopAfter.current){
        setRemaining([...queue.current.keys()].filter(relative=>!handled.current.has(relative)).length);
        setMessage("清单已登记；已停止后续导入，需明确继续下一批。");
      }else ready=true;
    }catch(error){if(current(generation)){setManifestPending(true);setMessage(`清单登记未确认：${reportFailure(error)}；保留相同批次，可核对历史或重试登记。`);}}
    finally{unlock(generation);}
    if(ready&&current(generation))await runBatch();
  }
  async function retryImport(key:string){
    const row=rowsRef.current.find(item=>item.key===key);
    if(!row||row.batch_id!==batchRef.current)return;
    const file=queue.current.get(row.relative);
    if(!file){setNeedsFiles(true);setMessage("原文件句柄不可用，请重新选择此批次文件夹。");return;}
    const generation=lock();if(generation===null)return;
    try{const result=await processFile(file,row.relative,row.batch_id,generation);if(result&&current(generation))replace(result);}
    finally{unlock(generation);}
  }
  async function enqueueRetained(key:string){
    const row=rowsRef.current.find(item=>item.key===key),identity=durable.current;
    if(!row?.source_id||!row.sha256||!identity||row.batch_id!==identity.batch_id)return;
    const kind=conversionKindFor(row.relative);if(!kind)return;
    const generation=lock();if(generation===null)return;
    try{
      const receipt=await coreCommand<{job_id:string;state:string}>("ingest_member_enqueue",{batch_id:row.batch_id,body:{
        workspace_id:identity.workspace_id,restore_epoch:identity.restore_epoch,ordinal:ordinals.current.get(row.relative),
        source_id:row.source_id,source_revision:row.sha256,kind}});
      if(current(generation)&&receipt.job_id===`folder-${kind}-${row.sha256}`)patch(key,{job_id:receipt.job_id,kind,state:jobState(receipt.state),detail:"已核对成员并入队；尚未执行。"});
    }catch(error){if(current(generation))setMessage(`入队未确认：${reportFailure(error)}；来源保留。`);}
    finally{unlock(generation);}
  }
  function current(generation: number) { return mounted.current && epoch.current === generation; }
  function publish() { if (mounted.current) window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: { owner, dirty: running.current || rowsRef.current.some(row => !!row.attempt || row.cancelPending) } })); }
  function update(transform: (old: Row[]) => Row[]) {
    if (!mounted.current) return;
    rowsRef.current = transform(rowsRef.current); setRows(rowsRef.current); publish();
  }
  function patch(key: string, value: Partial<Row>) { update(old => old.map(row => row.key === key ? { ...row, ...value } : row)); }
  function replace(row: Row) { update(old => old.some(item => item.key === row.key) ? old.map(item => item.key === row.key ? row : item) : [...old, row]); }
  function wait(ms: number): Promise<void> { return new Promise(resolve => { const timer = window.setTimeout(() => { timers.current.delete(timer); resolve(); }, ms); timers.current.set(timer, resolve); }); }
  useEffect(() => { mounted.current = true; return () => {
    mounted.current = false; epoch.current++; for (const [timer, resolve] of timers.current) { window.clearTimeout(timer); resolve(); } timers.current.clear();
    window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: { owner, dirty: false } }));
  }; }, [owner]);
  function tally(list: Row[]) {
    const count = (...states: RowState[]) => list.filter(row => states.includes(row.state)).length;
    return `原件已保管 ${list.filter(row => !!row.source_id).length} · 已入队 ${count("queued", "pending")} · 运行中 ${count("running", "leased", "starting")}`
      + ` · 已成功 ${count("succeeded")} · 失败待处理 ${count("failed")} · 已取消 ${count("cancelled")} · 已拒绝 ${count("rejected")}`
      + ` · 仅保管 ${count("ORIGINAL_ONLY")} · 处理结果待确认 ${count("UNKNOWN")} · 冲突 ${count("IDENTITY_CONFLICT")}`
      + ` · 未入队 ${count("ENQUEUE_FAILED")} · 原件导入未确认 ${count("IMPORT_FAILED")} · 跳过 ${count("跳过：隐藏路径", "跳过：排除目录", "未导入：超过大小上限")}`;
  }
  async function processFile(file: File, relative: string, batch: string, generation: number): Promise<Row | null> {
    const base = { key: `${batch}:${relative}`, batch_id: batch, relative, bytes: file.size };
    const refusal = refuseBeforeUpload(relative, file.size);
    if (refusal) { handled.current.add(relative); return { ...base, ...refusal }; }
    let imported: ImportReceipt;
    try {
      const bytes = await file.arrayBuffer();
      const expectedSha256 = await contentSha256(new Uint8Array(bytes));
      const content_base64 = base64Of(bytes); if (!current(generation)) return null;
      const identity=durable.current;
      if(!identity?.complete||identity.batch_id!==batch)throw new Error("已保存的文件清单与当前批次尚未核对。");
      const ordinal=ordinals.current.get(relative);
      const receipt=await coreCommand<{batch_id:string;ordinal:number}>("ingest_member_import", { batch_id:batch,body: {
        workspace_id:identity.workspace_id,restore_epoch:identity.restore_epoch,
        ordinal,expected_sha256:expectedSha256,content_base64 } });
      if(receipt.batch_id!==batch||receipt.ordinal!==ordinal)throw new Error("成员导入回执身份不匹配。");
      imported=confirmedImport(receipt,expectedSha256);
      if (!current(generation)) return null;
      handled.current.add(relative);
    } catch (error) {
      if (!current(generation)) return null;
      handled.current.add(relative); return { ...base, state: "IMPORT_FAILED", detail: failureMessage(error), last_error_message: error instanceof Error ? error.message : String(error) };
    }
    const {source_id, sha256} = imported, kind = conversionKindFor(relative);
    if (!kind) return { ...base, source_id, sha256, state: "ORIGINAL_ONLY", detail: "当前未提供此格式的转换方式；原件已单独保存，未安排转换。" };
    const job_id = `folder-${kind}-${sha256}`, original = { ...base, source_id, sha256, kind, job_id };
    try {
      const identity=durable.current!;
      const receipt = await coreCommand<{ job_id?: unknown; state?: unknown }>("ingest_member_enqueue", { batch_id:batch,body: {
        workspace_id:identity.workspace_id,restore_epoch:identity.restore_epoch,ordinal:ordinals.current.get(relative),
        kind,source_id,source_revision:sha256 } });
      if (!current(generation)) return null;
      if (receipt.job_id !== job_id) return { ...original, state: "UNKNOWN", detail: "转换入队回执身份不匹配；未执行任何作业。" };
      const state = jobState(receipt.state);
      const row: Row = { ...original, state, detail: `原件已保留${imported.duplicate ? "（相同内容的原件已存在）" : ""}；转换状态：${LABEL[state]}。` };
      if (!["queued", "pending"].includes(state)) {
        try { row.status = await readFolderStatus(folderCommand, job_id, source_id); if (!current(generation)) return null; row.state = jobState(row.status.state); }
        catch { row.detail += " 当前新尝试条件未读回；不会自动重执行。"; }
      }
      return row;
    } catch (error) {
      if (!current(generation)) return null;
      const explicitlyRefused=error instanceof ApiError && error.status>=400 && error.status<500;
      return { ...original, state: error instanceof ApiError && error.status === 409 ? "IDENTITY_CONFLICT" : explicitlyRefused ? "ENQUEUE_FAILED" : "UNKNOWN",
        detail: error instanceof ApiError && error.status === 409 ? `同一作业标识持有不同的 ${kind} 参数，需人工核对。` : `原件已保留，${kind} 入队未确认；请查看处理进度，不会自动执行。` };
    }
  }
  function lock(): number | null {
    if (capabilityFlight.current || running.current) return null; running.current = true; stopAfter.current = false; setBusy(true); publish(); return epoch.current;
  }
  function unlock(generation: number) { if (!current(generation)) return; running.current = false; setBusy(false); active.current = null; publish(); }
  async function runBatch() {
    const generation = lock(); if (generation === null) return;
    const batch = batchRef.current!;
    const currentFolder = folderRef.current;
    if (currentFolder && folderRef.current !== currentFolder) {
      handled.current.clear();
    }
    const next = [...queue.current.keys()].filter(relative => !handled.current.has(relative)).sort((a, b) => a.localeCompare(b)).slice(0, MAX_FILES);
    let processed = 0;
    try {
      for (const relative of next) {
        if (!current(generation) || stopAfter.current) break;
        const row = await processFile(queue.current.get(relative)!, relative, batch, generation);
        if (!current(generation)) return; if (row) { replace(row); processed++; }
      }
      const left = [...queue.current.keys()].filter(relative => !handled.current.has(relative)).length;
      if (current(generation)) { setRemaining(left); setMessage(`文件夹「${folderRef.current}」批次处理：本次 ${processed} 项 · ${tally(rowsRef.current)} · ${left ? `剩余 ${left} 项待下一批（已成功或排除的项不重复计入本批上限）` : "全部处理完毕"}${stopAfter.current ? " · 已停止后续导入；当前任务的处理记录已保留" : ""}`); window.dispatchEvent(new Event("archeaxis-job-changed")); }
    } finally { unlock(generation); }
  }
  function statusPatch(key: string, status: JobStatus) {
    const frozen=rowsRef.current.find(row=>row.key===key)?.attempt;
    if(journal.available&&frozen&&terminalJobState(status.state)&&status.request_id===frozen.request_id){
      void journal.clear(frozen.request_id).then(()=>{if(mounted.current&&rowsRef.current.some(row=>row.key===key&&row.attempt?.request_id===frozen.request_id))patch(key,{attempt:undefined,cancelPending:false,executionRefused:false,admissionProof:undefined});}).catch(()=>{if(mounted.current&&rowsRef.current.some(row=>row.key===key&&row.attempt?.request_id===frozen.request_id))patch(key,{detail:"处理结果已记录，但待处理记录尚未确认清理；本次处理记录仍保留，请再核对状态。"});});
    }
    const terminal = terminalJobState(status.state);
    patch(key, { status, state: jobState(status.state), detail: status.state === "failed" ? `原件已保留；${folderFailureSummary(status)}` : terminal ? `转换状态：${LABEL[jobState(status.state)]}；原件已保留，成功产物可按所选来源查看。${status.error ? ` ${status.error}` : ""}` : `转换状态：${LABEL[jobState(status.state)]}；最终结果尚未确认。`,
      ...(terminal && !journal.available ? { attempt: undefined, cancelPending: false, executionRefused: false, admissionProof:undefined, capabilityBusy:false } : {}) });
  }
  async function executeOne(key: string, mode: "queued" | "fresh" | "same", generation: number) {
    let row = rowsRef.current.find(item => item.key === key);
    if (!row?.job_id || !row.source_id) return;
    if (mode !== "same") {
      try {
        const checked = await readFolderStatus(folderCommand, row.job_id, row.source_id);
        if (!current(generation)) return; statusPatch(key, checked);
        if (mode === "fresh" ? !freshAttemptEligible(checked) : !["queued", "pending"].includes(checked.state)) {
          setMessage("本地服务尚未确认能否重新处理；原件、历史与错误保留，不会自动再次执行。"); return;
        }
      } catch (error) {
        if (current(generation)) { patch(key, { state:"UNKNOWN", last_error_message:error instanceof Error?error.message:String(error), detail:`执行前状态未确认：${failureMessage(error)}；未创建执行请求。` }); stopAfter.current = true; }
        return;
      }
    }
    row = rowsRef.current.find(item => item.key === key)!;
    const attempt = mode === "same" ? row.attempt : freezeFolderAttempt(row.job_id!);
    if (!attempt || mode === "same" && row.executionRefused) return;
    const source = row.source_id!;
    const belongs = () => current(generation) && rowsRef.current.some(item => item.key === key && item.attempt?.request_id === attempt.request_id);
    patch(key, { attempt, state: "UNKNOWN", detail: "已保留本次处理记录；等待处理结果，本次最多等待 90 秒。", executionRefused: false, admissionProof:undefined }); active.current = { key, attempt };
    try {
      if(!row.sha256||!row.kind)throw new Error("来源与种类身份缺失；未执行。");
      await journal.stage({source_id:source,source_revision:row.sha256,kind:row.kind,job_id:attempt.job_id,request_id:attempt.request_id,body:attempt.body,mode:"single",relative:row.relative});
      if(!belongs())return;
      const receipt = await folderCommand("job_execute", { job_id: attempt.job_id, request_id: attempt.request_id, body: attempt.body });
      if (!belongs()) return;
      folderExecutionAck(receipt, attempt); // An ACK is not a terminal readback.
      await pollFolderAttempt(folderCommand, attempt, source, belongs, status => { if (belongs()) statusPatch(key, status); }, wait);
      if (current(generation)) window.dispatchEvent(new Event("archeaxis-job-changed"));
    } catch (error) {
      if (belongs()) {
        const recovery = recoverableJobRefusal(error, attempt, source, row.kind);
        patch(key, { state: "UNKNOWN", executionRefused: error instanceof ApiError && error.status >= 400 && error.status < 500 && !recoverableJobRefusal(error, attempt, source, row.kind),
          admissionProof:recovery?(error as ApiError).jobAdmission:undefined,
          last_error_message:error instanceof Error?error.message:String(error), detail: recovery ? "本地服务已确认上次处理未受理；此功能已禁用。可在此启用，本次处理记录仍保留；之后另点“重试上次处理”。" : `执行未确认：${failureMessage(error)}；保留本次处理记录；仅重试上次处理或查看进度，不会另行创建处理任务。` });
        stopAfter.current = true;
      }
    } finally { if (active.current?.attempt.request_id === attempt.request_id) active.current = null; }
  }
  async function executeBatch() {
    const generation = lock(); if (generation === null) return;
    try {
      const keys = rowsRef.current.filter(row => row.batch_id===batchRef.current && ["queued", "pending"].includes(row.state) && row.job_id && !row.attempt).map(row => row.key);
      for (const key of keys) { if (!current(generation) || stopAfter.current) break; await executeOne(key, "queued", generation); }
      if (current(generation)) setMessage(`本批次转换：${tally(rowsRef.current)}${stopAfter.current ? " · 后续转换未开始，当前回执保留" : ""}。`);
    } finally { unlock(generation); }
  }
  async function rowAction(key: string, mode: "fresh" | "same" | "read") {
    const generation = lock(); if (generation === null) return;
    try {
      const row = rowsRef.current.find(item => item.key === key);
      if (!row?.job_id || !row.source_id) return;
      if (mode === "read") {
        const attempt = row.attempt, source = row.source_id;
        const belongs = () => current(generation) && (!attempt || rowsRef.current.some(item => item.key === key && item.attempt?.request_id === attempt.request_id));
        const status = await readFolderStatus(folderCommand, row.job_id, source, attempt);
        if (belongs()) statusPatch(key, status);
        if (attempt && belongs() && !terminalJobState(status.state)) await pollFolderAttempt(folderCommand, attempt, source, belongs, status => { if (belongs()) statusPatch(key,status); }, wait);
      }
      else await executeOne(key, mode, generation);
    } catch (error) { if (current(generation)) setMessage(`状态或新尝试条件未确认：${reportFailure(error)}；本次处理记录和历史仍保留。`); }
    finally { unlock(generation); }
  }
  async function cancel(key: string) {
    const row = rowsRef.current.find(item => item.key === key), attempt = row?.attempt;
    if (!row?.source_id || !attempt || cancelFlight.current || capabilityFlight.current) return;
    const generation = epoch.current; cancelFlight.current = true; setCancelBusy(true); stopAfter.current = true;
    const belongs = () => current(generation) && rowsRef.current.some(item => item.key === key && item.attempt?.request_id === attempt.request_id);
    patch(key, { cancelPending: true, detail: "取消待确认；继续读回当前转换，202 不等于已取消。" });
    try {
      const receipt = await folderCommand("job_execution_cancel", { job_id: attempt.job_id, request_id: attempt.request_id });
      if (!belongs()) return; folderCancelAck(receipt, attempt);
      const status = await readFolderStatus(folderCommand, attempt.job_id, row.source_id, attempt);
      if (belongs()) statusPatch(key, status);
      if (belongs() && !terminalJobState(status.state)) await pollFolderAttempt(folderCommand, attempt, row.source_id, belongs, status => { if (belongs()) statusPatch(key,status); }, wait);
    } catch (error) { if (belongs()) patch(key, { last_error_message:error instanceof Error?error.message:String(error), detail: `取消未确认：${failureMessage(error)}；同身份取消可重试，原件和当前尝试保留。` }); }
    finally { cancelFlight.current = false; if (current(generation)) setCancelBusy(false); }
  }
  function open(row: Row) {
    if (capabilityFlight.current || running.current || rowsRef.current.some(item => item.attempt || item.cancelPending)) { setMessage("仍有正在处理或结果待确认的任务，请先核对状态再打开来源；批次与原件保留。"); return; }
    if (row.source_id) callback.current?.(row.source_id, row.state === "succeeded" ? row.job_id : undefined, row.sha256);
  }
  function selectRelations(row:Row) {
    const saved=durable.current,ordinal=ordinals.current.get(row.relative);
    if(running.current||capabilityFlight.current||rowsRef.current.some(item=>item.attempt||item.cancelPending)||!saved||saved.batch_id!==row.batch_id||ordinal===undefined||!row.source_id||!row.sha256)return;
    onSelectRelations?.({batch_id:row.batch_id,ordinal,workspace_id:saved.workspace_id,restore_epoch:saved.restore_epoch,source_id:row.source_id,source_revision:row.sha256});
  }
  const capabilityBusy = rows.some(row=>row.capabilityBusy);
  return <section aria-label="文件夹导入"><h4>文件夹导入</h4><JobJournalRecovery entries={journal.entries} disabled={busy||cancelBusy||capabilityFlight.current||journal.blocked} onRestore={entry=>{const key=`recovered:${entry.request_id}`;replace({key,batch_id:"recovered",relative:entry.relative??entry.source_id,bytes:0,source_id:entry.source_id,sha256:entry.source_revision,job_id:entry.job_id,kind:entry.kind,attempt:{job_id:entry.job_id,request_id:entry.request_id,body:entry.body},state:"UNKNOWN",detail:"待确认任务已找回；本地待处理文件列表未恢复。请先检查状态，不会自动再次执行。"});}} onAbandon={async entry=>{await journal.clear(entry.request_id,"abandon_unadmitted");update(old=>old.filter(row=>row.attempt?.request_id!==entry.request_id));}}/>
    <label className="content-import">选择一个文件夹<input type="file" aria-label="选择文件夹" disabled={busy || rows.some(row => !!row.attempt)} {...({ webkitdirectory: "", directory: "" } as Record<string, string>)} multiple onChange={event => {
      if (capabilityFlight.current || running.current || rowsRef.current.some(row => !!row.attempt)) return;
      const files = Array.from(event.target.files ?? []); event.target.value = "";
      if (!files.length) { setMessage("没有收到任何文件；浏览器可能拒绝了此选择。"); return; }
      const root = folderOf(files); if (!root) { setMessage("所选内容不像是同一个文件夹，未开始导入。"); return; }
      const privates = files.map(privateVisibleSegment).filter((p): p is string => p !== null);
      if (privates.length) { setMessage(`整个文件夹被拒绝：${privates.length} 条路径落在私有状态目录里（如 ${privates[0]}），未导入任何文件。请重新选择或明确缩小范围。`); return; }
      if(root.startsWith(".")||EXCLUDED_DIRS.has(root.toLowerCase())){setMessage("选中的根目录属于排除目录；未登记或导入，原批次保留。");return;}
      // A picker selection is a new provenance batch: identical root names do not
      // identify the same disk folder or the same content revision. Preserve rows
      // and frozen-request guards; Core job identity remains content-addressed.
      if(files.length>10000||new Set(files.map(relativeOf)).size!==files.length){setMessage("清单超过 10000 项或相对路径重复；未登记或上传。");return;}
      epoch.current++; handled.current.clear(); queue.current.clear();durable.current=null;registration.current=null;ordinals.current.clear();
      setNeedsFiles(false);setManifestPending(false);folderRef.current = root; batchRef.current = crypto.randomUUID(); setFolder(root); setBatchId(batchRef.current); setRemaining(0);
      for (const file of files) queue.current.set(relativeOf(file), file); void registerSelection();
    }}/></label>
    <button disabled={busy||rows.some(row=>!!row.attempt)} onClick={()=>void historyPage()}>读取历史批次</button>
    {history.map(item=><button key={item.batch_id} disabled={busy||rows.some(row=>!!row.attempt)} onClick={()=>void restoreBatch(item.batch_id)}>查看批次 {item.folder_label}</button>)}
    {historyCursor?<button disabled={busy} onClick={()=>void historyPage(historyCursor)}>更多历史批次</button>:null}
    {needsFiles?<label>继续未上传成员<input type="file" aria-label="重新选择此批次文件夹" disabled={busy} multiple {...({webkitdirectory:"",directory:""} as Record<string,string>)} onChange={event=>{
      const files=Array.from(event.target.files??[]);event.target.value="";const saved=durable.current;
      if(!saved||running.current)return;
      if(saved.folder_label.startsWith(".")||EXCLUDED_DIRS.has(saved.folder_label.toLowerCase())){setMessage("选中的根目录属于排除目录；历史批次仍可读取，未继续登记或导入。");return;}
      const sorted=files.sort((a,b)=>relativeOf(a)<relativeOf(b)?-1:relativeOf(a)>relativeOf(b)?1:0);
      if(folderOf(files)!==saved.folder_label||files.length!==saved.expected_members||new Set(files.map(relativeOf)).size!==files.length
        ||files.some(file=>privateVisibleSegment(file))||saved.members.some(member=>!sorted[member.ordinal]||relativeOf(sorted[member.ordinal])!==member.relative_path||sorted[member.ordinal].size!==member.byte_length)){
        setMessage("所选文件夹与已保存的文件清单在路径、数量或大小上不符；未上传。");return;
      }
      queue.current.clear();for(const file of files)queue.current.set(relativeOf(file),file);
      registration.current=null;void registerSelection();
    }}/></label>:null}
    {folder ? <p>当前批次「{folder}」。继续处理当前选择请用“下一批”；关闭应用后，未上传的文件需要重新选择。</p> : null}
    <p>“停止”只停止后续文件。正在转换的文件需单独请求取消，最长等待 90 秒；结果未确认时请先检查，不会自动重试。</p>
    <details><summary>导入与恢复说明</summary><p>原件保存与内容转换分别记录；已经接收的文件仍会核对实际结果。没有正在处理的批次时，“停止”不可用。</p>
      <p>每次选择文件夹都会建立新批次，系统保存完整相对路径、原件与处理记录的关联。重新打开应用后，历史记录仍可读取；尚未上传的文件需要重新选择。</p>
      <p>重新选择时会核对文件路径、数量和大小，但这不代表文件内容完全相同；你重新选择的实际内容将作为本次提交的内容。应用不会保存可在重启后直接读取文件的句柄，也无法从浏览器取得磁盘绝对路径。</p>
    </details>
    <div>{remaining > 0 ? <button disabled={busy || rows.some(row => !!row.attempt)} onClick={() => void runBatch()}>下一批（剩余 {remaining}）</button> : null}
      {manifestPending?<button disabled={busy} onClick={()=>void registerSelection()}>重试准备此批次</button>:null}
      {rows.some(row => row.batch_id===batchId && ["queued", "pending"].includes(row.state)) ? <button disabled={busy || rows.some(row => !!row.attempt)} onClick={() => void executeBatch()}>开始处理本批文件</button> : null}
      <button disabled={!busy} title={!busy?"当前没有正在处理的导入任务":undefined} onClick={() => { stopAfter.current = true; setMessage("已请求停止后续处理；当前受理项仍须读回真实状态。"); }}>停止</button>
    </div>{message ? <p role="status">{message}</p> : null}{failure!==null?<RawReceiptButton label="最近文件夹处理错误详细信息" payload={failure}/>:null}
    {rows.length ? <><p aria-label="批次真实统计">{tally(rows)}</p><p>表格可横向滚动查看操作列。</p><div className="folder-ingest-table-scroll" role="region" aria-label="批次明细与操作，可横向滚动" tabIndex={0}><table className="data-table"><thead><tr>{["文件夹内路径","字节","原件","转换结果","说明","操作"].map(label=><th key={label}>{label}</th>)}</tr></thead><tbody>{rows.map(row => <tr key={row.key}>
      <td>{row.relative}</td><td>{row.bytes}</td><td>{row.source_id ? <span>原件已保存</span> : "原件未确认保管"}</td><td>{LABEL[row.state]}{row.cancelPending ? " · 取消待确认" : ""}</td>
      <td>{row.detail}<ConversionRecoveryNotice status={row.status}/>{row.source_id || row.job_id || row.attempt || row.status || row.last_error_message ? <RawReceiptButton label="此文件导入与转换详细信息" category="data" payload={{source_id:row.source_id,sha256:row.sha256,job_id:row.job_id,attempt:row.attempt,status:row.status,last_error_message:row.last_error_message}}/> : null}</td>
      <td><div>{row.job_id ? <button disabled={busy||capabilityBusy} onClick={() => void rowAction(row.key,"read")}>{row.attempt ? "检查上次处理结果" : "查看处理进度"}</button> : null}
        {row.batch_id===batchId&&!row.source_id&&row.state==="IMPORT_FAILED"?<button disabled={busy||capabilityBusy} onClick={()=>void retryImport(row.key)}>重试导入此文件</button>:null}
        {row.batch_id===batchId&&row.source_id&&(!row.job_id||row.state==="ENQUEUE_FAILED")&&conversionKindFor(row.relative)?<button disabled={busy||capabilityBusy} onClick={()=>void enqueueRetained(row.key)}>继续处理此文件</button>:null}
        {row.attempt && row.state === "UNKNOWN" && !row.executionRefused ? <button disabled={busy||capabilityBusy} onClick={() => void rowAction(row.key,"same")}>重试上次处理</button> : null}
        {row.attempt&&row.admissionProof&&row.source_id?<FrozenCapabilityRecovery key={row.attempt.request_id} proof={row.admissionProof} attempt={row.attempt} source={row.source_id} kind={row.kind} disabled={busy||cancelBusy||capabilityBusy} current={()=>mounted.current&&!running.current&&!cancelFlight.current&&rowsRef.current.some(item=>item.key===row.key&&item.attempt?.request_id===row.attempt?.request_id)} onBusyChange={value=>{if(mounted.current&&rowsRef.current.some(item=>item.key===row.key&&item.attempt?.request_id===row.attempt?.request_id)){capabilityFlight.current=value;patch(row.key,{capabilityBusy:value});}}}/>:null}{!row.attempt && row.status && freshAttemptEligible(row.status) ? <button disabled={busy||capabilityBusy} onClick={() => void rowAction(row.key,"fresh")}>重新处理失败文件</button> : null}
        {row.attempt ? <button disabled={cancelBusy||capabilityBusy} onClick={() => void cancel(row.key)}>请求取消当前转换</button> : null}
        {onSelectRelations&&row.source_id&&row.sha256&&row.batch_id===batchId&&/\.(md|markdown)$/i.test(row.relative)?<button disabled={busy||rows.some(item=>!!item.attempt)} onClick={()=>selectRelations(row)}>映射此原件中的链接</button>:null}
        {row.source_id && onOpenSource ? <button disabled={busy || rows.some(item => !!item.attempt)} onClick={() => open(row)}>{row.state === "succeeded" ? "打开成功产物与来源" : "打开保留原件"}</button> : null}</div></td>
    </tr>)}</tbody></table></div><p>任务完成后仍需核对识别内容和专业依据。成功结果可从对应文件的已保存记录中打开。</p></> : null}
  </section>;
}
