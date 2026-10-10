import { useEffect, useId, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import { ApiError } from "../api/client";
import { conversionKindFor } from "../api/conversionKinds";
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
type Row = { key: string; batch_id: string; relative: string; bytes: number; state: RowState; detail: string;
  source_id?: string; sha256?: string; job_id?: string; kind?: string; status?: JobStatus;
  attempt?: FolderAttempt; cancelPending?: boolean; executionRefused?: boolean };
const LABEL: Record<RowState, string> = {
  queued:"已入队", pending:"已入队", running:"作业运行中", leased:"作业运行中", starting:"作业运行中",
  succeeded:"已成功", failed:"失败待重试", cancelled:"已取消", rejected:"已拒绝",
  UNKNOWN:"结果 UNKNOWN，待核对", ORIGINAL_ONLY:"原件已保管，无转换通路", IMPORT_FAILED:"原件导入未确认",
  ENQUEUE_FAILED:"转换未入队", IDENTITY_CONFLICT:"作业身份冲突",
  "跳过：隐藏路径":"跳过：隐藏路径", "跳过：排除目录":"跳过：排除目录", "未导入：超过大小上限":"未导入：超过大小上限",
};
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

export function FolderIngest({ onOpenSource }: { onOpenSource?: (sourceId: string, jobId?: string) => void }) {
  const [rows, setRows] = useState<Row[]>([]), [folder, setFolder] = useState<string | null>(null);
  const [batchId, setBatchId] = useState<string | null>(null), [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false), [remaining, setRemaining] = useState(0), [cancelBusy, setCancelBusy] = useState(false);
  const rowsRef = useRef<Row[]>([]), queue = useRef(new Map<string, File>()), handled = useRef(new Set<string>());
  const folderRef = useRef<string | null>(null), batchRef = useRef<string | null>(null);
  const running = useRef(false), stopAfter = useRef(false), cancelFlight = useRef(false);
  const mounted = useRef(true), epoch = useRef(0), active = useRef<{ key: string; attempt: FolderAttempt } | null>(null);
  const timers = useRef(new Map<number, () => void>()), callback = useRef(onOpenSource); callback.current = onOpenSource;
  const owner = `folder-ingest-${useId()}`;
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
      + ` · 已成功 ${count("succeeded")} · 失败待重试 ${count("failed")} · 已取消 ${count("cancelled")} · 已拒绝 ${count("rejected")}`
      + ` · 仅保管 ${count("ORIGINAL_ONLY")} · UNKNOWN ${count("UNKNOWN")} · 冲突 ${count("IDENTITY_CONFLICT")}`
      + ` · 未入队 ${count("ENQUEUE_FAILED")} · 原件导入未确认 ${count("IMPORT_FAILED")} · 跳过 ${count("跳过：隐藏路径", "跳过：排除目录", "未导入：超过大小上限")}`;
  }
  async function processFile(file: File, relative: string, batch: string, generation: number): Promise<Row | null> {
    const base = { key: `${batch}:${relative}`, batch_id: batch, relative, bytes: file.size };
    const refusal = refuseBeforeUpload(relative, file.size);
    if (refusal) { handled.current.add(relative); return { ...base, ...refusal }; }
    let imported: { source_id?: unknown; sha256?: unknown; duplicate?: unknown };
    try {
      const content_base64 = base64Of(await file.arrayBuffer()); if (!current(generation)) return null;
      imported = await coreCommand("source_import", { body: { name: relative, content_base64, origin_kind: "path", origin_ref: batch, origin_name: file.name } });
      if (!current(generation)) return null;
      handled.current.add(relative);
      if (typeof imported.source_id !== "string" || !imported.source_id || typeof imported.sha256 !== "string" || !/^[a-f0-9]{64}$/.test(imported.sha256)
        || typeof imported.duplicate !== "boolean") return { ...base, state: "IMPORT_FAILED", detail: "导入回执未确认 source_id/sha256/duplicate；请保留原件，未启动转换。" };
    } catch (error) {
      if (!current(generation)) return null;
      handled.current.add(relative); return { ...base, state: "IMPORT_FAILED", detail: error instanceof Error ? error.message : "原件导入未确认" };
    }
    const source_id = imported.source_id as string, sha256 = imported.sha256 as string, kind = conversionKindFor(relative);
    if (!kind) return { ...base, source_id, sha256, state: "ORIGINAL_ONLY", detail: "此扩展名没有映射到任何 Core 作业种类；原件独立保管，未入队。" };
    const job_id = `folder-${kind}-${sha256}`, original = { ...base, source_id, sha256, kind, job_id };
    try {
      const receipt = await coreCommand<{ job_id?: unknown; state?: unknown }>("job_enqueue", { body: { job_id, kind, input_ref: source_id } });
      if (!current(generation)) return null;
      if (receipt.job_id !== job_id) return { ...original, state: "UNKNOWN", detail: "转换入队回执身份不匹配；未执行任何作业。" };
      const state = jobState(receipt.state);
      const row: Row = { ...original, state, detail: `原件已保留${imported.duplicate ? "（同哈希原件已存在）" : ""}；转换 Core 状态 ${state}。` };
      if (!["queued", "pending"].includes(state)) {
        try { row.status = await readFolderStatus(folderCommand, job_id, source_id); if (!current(generation)) return null; row.state = jobState(row.status.state); }
        catch { row.detail += " 当前新尝试条件未读回；不会自动重执行。"; }
      }
      return row;
    } catch (error) {
      if (!current(generation)) return null;
      const explicitlyRefused=error instanceof ApiError && error.status>=400 && error.status<500;
      return { ...original, state: error instanceof ApiError && error.status === 409 ? "IDENTITY_CONFLICT" : explicitlyRefused ? "ENQUEUE_FAILED" : "UNKNOWN",
        detail: error instanceof ApiError && error.status === 409 ? `同一作业标识持有不同的 ${kind} 参数，需人工核对。` : `原件已保留，${kind} 入队未确认；请读取转换状态，不会自动执行。` };
    }
  }
  function lock(): number | null {
    if (running.current) return null; running.current = true; stopAfter.current = false; setBusy(true); publish(); return epoch.current;
  }
  function unlock(generation: number) { if (!current(generation)) return; running.current = false; setBusy(false); active.current = null; publish(); }
  async function runBatch() {
    const generation = lock(); if (generation === null) return;
    const batch = batchRef.current!;
    const next = [...queue.current.keys()].filter(relative => !handled.current.has(relative)).sort((a, b) => a.localeCompare(b)).slice(0, MAX_FILES);
    let processed = 0;
    try {
      for (const relative of next) {
        if (!current(generation) || stopAfter.current) break;
        const row = await processFile(queue.current.get(relative)!, relative, batch, generation);
        if (!current(generation)) return; if (row) { replace(row); processed++; }
      }
      const left = [...queue.current.keys()].filter(relative => !handled.current.has(relative)).length;
      if (current(generation)) { setRemaining(left); setMessage(`文件夹「${folderRef.current}」批次处理：本次 ${processed} 项 · ${tally(rowsRef.current)} · ${left ? `剩余 ${left} 项待下一批（已成功或排除的项不重复占预算）` : "全部处理完毕"}${stopAfter.current ? " · 已停止后续导入；当前受理项的真实回执已保留" : ""}`); window.dispatchEvent(new Event("archeaxis-job-changed")); }
    } finally { unlock(generation); }
  }
  function statusPatch(key: string, status: JobStatus) {
    const terminal = terminalJobState(status.state);
    patch(key, { status, state: jobState(status.state), detail: terminal ? `转换终态 ${status.state}；原件保留，成功产物可按真实来源定位。${status.error ? ` ${status.error}` : ""}` : `转换仍为 ${status.state}；终态未确认。`,
      ...(terminal ? { attempt: undefined, cancelPending: false, executionRefused: false } : {}) });
  }
  async function executeOne(key: string, mode: "queued" | "fresh" | "same", generation: number) {
    let row = rowsRef.current.find(item => item.key === key);
    if (!row?.job_id || !row.source_id) return;
    if (mode !== "same") {
      try {
        const checked = await readFolderStatus(folderCommand, row.job_id, row.source_id);
        if (!current(generation)) return; statusPatch(key, checked);
        if (mode === "fresh" ? !freshAttemptEligible(checked) : !["queued", "pending"].includes(checked.state)) {
          setMessage("Core 未确认当前可新建尝试；原件、历史与错误保留，不会自动重执行。"); return;
        }
      } catch (error) {
        if (current(generation)) { patch(key, { state:"UNKNOWN", detail:`执行前状态未确认：${error instanceof Error ? error.message : "未知原因"}；未创建执行请求。` }); stopAfter.current = true; }
        return;
      }
    }
    row = rowsRef.current.find(item => item.key === key)!;
    const attempt = mode === "same" ? row.attempt : freezeFolderAttempt(row.job_id!);
    if (!attempt || mode === "same" && row.executionRefused) return;
    const source = row.source_id!;
    const belongs = () => current(generation) && rowsRef.current.some(item => item.key === key && item.attempt?.request_id === attempt.request_id);
    patch(key, { attempt, state: "UNKNOWN", detail: "执行请求已冻结；等待真实回执，90s 单次预算。", executionRefused: false }); active.current = { key, attempt };
    try {
      const receipt = await folderCommand("job_execute", { job_id: attempt.job_id, request_id: attempt.request_id, body: attempt.body });
      if (!belongs()) return;
      folderExecutionAck(receipt, attempt); // An ACK is not a terminal readback.
      await pollFolderAttempt(folderCommand, attempt, source, belongs, status => { if (belongs()) statusPatch(key, status); }, wait);
      if (current(generation)) window.dispatchEvent(new Event("archeaxis-job-changed"));
    } catch (error) {
      if (belongs()) {
        patch(key, { state: "UNKNOWN", executionRefused: error instanceof ApiError && error.status >= 400 && error.status < 500,
          detail: `执行未确认：${error instanceof Error ? error.message : "未知原因"}；保留冻结身份，仅同请求重试或读取状态，不产生新尝试。` });
        stopAfter.current = true;
      }
    } finally { if (active.current?.attempt.request_id === attempt.request_id) active.current = null; }
  }
  async function executeBatch() {
    const generation = lock(); if (generation === null) return;
    try {
      const keys = rowsRef.current.filter(row => ["queued", "pending"].includes(row.state) && row.job_id && !row.attempt).map(row => row.key);
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
    } catch (error) { if (current(generation)) setMessage(`状态或新尝试条件未确认：${error instanceof Error ? error.message : "未知原因"}；原冻结请求及历史保留。`); }
    finally { unlock(generation); }
  }
  async function cancel(key: string) {
    const row = rowsRef.current.find(item => item.key === key), attempt = row?.attempt;
    if (!row?.source_id || !attempt || cancelFlight.current) return;
    const generation = epoch.current; cancelFlight.current = true; setCancelBusy(true); stopAfter.current = true;
    const belongs = () => current(generation) && rowsRef.current.some(item => item.key === key && item.attempt?.request_id === attempt.request_id);
    patch(key, { cancelPending: true, detail: "取消待确认；继续读回当前转换，202 不等于已取消。" });
    try {
      const receipt = await folderCommand("job_execution_cancel", { job_id: attempt.job_id, request_id: attempt.request_id });
      if (!belongs()) return; folderCancelAck(receipt, attempt);
      const status = await readFolderStatus(folderCommand, attempt.job_id, row.source_id, attempt);
      if (belongs()) statusPatch(key, status);
      if (belongs() && !terminalJobState(status.state)) await pollFolderAttempt(folderCommand, attempt, row.source_id, belongs, status => { if (belongs()) statusPatch(key,status); }, wait);
    } catch (error) { if (belongs()) patch(key, { detail: `取消未确认：${error instanceof Error ? error.message : "未知原因"}；同身份取消可重试，原件和当前尝试保留。` }); }
    finally { cancelFlight.current = false; if (current(generation)) setCancelBusy(false); }
  }
  function open(row: Row) {
    if (running.current || rowsRef.current.some(item => item.attempt || item.cancelPending)) { setMessage("仍有运行或冻结请求，请先核对状态再打开来源；批次与原件保留。"); return; }
    if (row.source_id) callback.current?.(row.source_id, row.state === "succeeded" ? row.job_id : undefined);
  }
  return <section aria-label="文件夹导入"><h4>文件夹导入</h4>
    <label className="content-import">选择一个文件夹<input type="file" aria-label="选择文件夹" disabled={busy || rows.some(row => !!row.attempt)} {...({ webkitdirectory: "", directory: "" } as Record<string, string>)} multiple onChange={event => {
      if (running.current || rowsRef.current.some(row => !!row.attempt)) return;
      const files = Array.from(event.target.files ?? []); event.target.value = "";
      if (!files.length) { setMessage("没有收到任何文件；浏览器可能拒绝了此选择。"); return; }
      const root = folderOf(files); if (!root) { setMessage("所选内容不像是同一个文件夹，未开始导入。"); return; }
      const privates = files.map(privateVisibleSegment).filter((p): p is string => p !== null);
      if (privates.length) { setMessage(`整个文件夹被拒绝：${privates.length} 条路径落在私有状态目录里（如 ${privates[0]}），未导入任何文件。请重新选择或明确缩小范围。`); return; }
      if (folderRef.current !== root) { epoch.current++; handled.current.clear(); queue.current.clear(); folderRef.current = root; batchRef.current = crypto.randomUUID(); update(() => []); setFolder(root); setBatchId(batchRef.current); setRemaining(0); }
      for (const file of files) queue.current.set(relativeOf(file), file); void runBatch();
    }}/></label>
    {folder ? <p>当前批次「{folder}」· 批次标识 {batchId?.slice(0, 8)}…；来源关系为该批次下的相对路径。浏览器不把磁盘绝对路径交给产品，所以此处不声称绝对路径，父目录链无法核验；当前队列是本页面会话状态，不声称重启恢复。</p> : null}
    <p>原件导入与转换分别记录。停止仅停止后续导入或转换；已受理原件仍读回真实结果。当前转换须单独请求 Core 取消，预算 90s；拒绝或资格未知不会自动重执行。</p>
    <div>{remaining > 0 ? <button disabled={busy || rows.some(row => !!row.attempt)} onClick={() => void runBatch()}>下一批（剩余 {remaining}）</button> : null}
      {rows.some(row => ["queued", "pending"].includes(row.state)) ? <button disabled={busy || rows.some(row => !!row.attempt)} onClick={() => void executeBatch()}>执行本批次转换</button> : null}
      <button disabled={!busy} onClick={() => { stopAfter.current = true; setMessage("已请求停止后续处理；当前受理项仍须读回真实状态。"); }}>停止</button>
    </div>{message ? <p role="status">{message}</p> : null}
    {rows.length ? <><p aria-label="批次真实统计">{tally(rows)}</p><p>表格可横向滚动查看操作列。</p><div className="folder-ingest-table-scroll" role="region" aria-label="批次明细与操作，可横向滚动" tabIndex={0}><table className="data-table"><thead><tr>{["文件夹内路径","字节","原件","转换结果","说明","操作"].map(label=><th key={label}>{label}</th>)}</tr></thead><tbody>{rows.map(row => <tr key={row.key}>
      <td>{row.relative}</td><td>{row.bytes}</td><td>{row.source_id ? <span>原件已保管 · {row.source_id}<br/>SHA-256 {row.sha256}</span> : "原件未确认保管"}</td><td>{LABEL[row.state]}{row.cancelPending ? " · 取消待确认" : ""}</td>
      <td>{row.detail}{row.job_id ? <><br/>job {row.job_id}</> : null}{row.attempt ? <><br/>冻结请求 {row.attempt.request_id} · {row.attempt.body.deadline_ms}ms</> : row.status?.request_id ? <><br/>实际请求 {row.status.request_id}</> : null}</td>
      <td><div>{row.job_id ? <button disabled={busy} onClick={() => void rowAction(row.key,"read")}>{row.attempt ? "核对冻结请求状态" : "读取转换状态"}</button> : null}
        {row.attempt && row.state === "UNKNOWN" && !row.executionRefused ? <button disabled={busy} onClick={() => void rowAction(row.key,"same")}>同请求重试</button> : null}
        {!row.attempt && row.status && freshAttemptEligible(row.status) ? <button disabled={busy} onClick={() => void rowAction(row.key,"fresh")}>重试失败项（新请求）</button> : null}
        {row.attempt ? <button disabled={cancelBusy} onClick={() => void cancel(row.key)}>请求取消当前转换</button> : null}
        {row.source_id && onOpenSource ? <button disabled={busy || rows.some(item => !!item.attempt)} onClick={() => open(row)}>{row.state === "succeeded" ? "打开成功产物与来源" : "打开保留原件"}</button> : null}</div></td>
    </tr>)}</tbody></table></div><p>执行终态不等同识别核验或专业依据已确认；成功产物须按真实 source_id/job_id 从持久化记录读取。</p></> : null}
  </section>;
}
