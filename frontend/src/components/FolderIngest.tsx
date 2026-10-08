import { useRef, useState } from "react";
import { coreCommand } from "../api/core";
import { ApiError } from "../api/client";
import { conversionKindFor } from "../api/conversionKinds";
import { DataTable } from "./RealData";

// The folder entry drives the same Core calls `scripts/ingest/directory_batch.py` drives and keeps
// that script's refusals, so the folder closed loop does not change shape when it moves from the
// CLI to the screen. The browser holds no file system, so progress across a >200 folder comes from
// a session queue the picker refills, not from a stored JSONL manifest.
const MAX_FILES = 200; // per-batch budget; already-handled and explicitly-excluded items never re-consume it
const MAX_BYTES = 64 * 1024 * 1024;
const EXECUTE_DEADLINE_MS = 90_000;
const POLL_MS = 300;
const EXCLUDED_DIRS = new Set([".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv",
  ".project-local", ".hermes", ".cache", "dist", "build", "target"]);
// Compared case-insensitively, matching `directory_batch.py`'s `part.casefold()` rule; on Windows
// the file system is case-insensitive, so `.CODEX` is the same private state as `.codex`.
const PRIVATE_STATE = new Set([".zcode", ".codex", ".hermes", ".openhuman", ".git"]);

type Row = {
  relative: string;
  bytes: number;
  state: string;
  detail: string;
  job_id?: string;
  source_id?: string;
  kind?: string;
  executable?: boolean;
};

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

function refuseBeforeUpload(relative: string, bytes: number): Row | null {
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

// A durable enqueue receipt already carries the job's real state; the folder entry must show that
// state, not overwrite every receipt with "已入队". Only a genuinely queued job is worth executing.
function classifyReceipt(state: unknown, kind: string, repeated: string): { state: string; detail: string; executable: boolean } {
  switch (state) {
    case "queued": return { state: "已入队", detail: `已入队转换${repeated}：${kind} 作业等待执行。`, executable: true };
    case "running": case "leased": case "starting": return { state: "作业运行中", detail: `作业运行中${repeated}：${kind}。`, executable: false };
    case "succeeded": return { state: "已成功", detail: `此内容已有成功结果${repeated}：${kind}。`, executable: false };
    case "failed": return { state: "失败待重试", detail: `此内容已有失败记录${repeated}：${kind}，可重试。`, executable: true };
    case "cancelled": case "rejected": return { state: `已${String(state)}`, detail: `此内容作业已${String(state)}${repeated}：${kind}，可重试。`, executable: true };
    default: return { state: "已受理未回执", detail: `作业已受理${repeated}：${kind}，状态未回执。`, executable: false };
  }
}

export function FolderIngest() {
  const [rows, setRows] = useState<Row[]>([]);
  const [folder, setFolder] = useState<string | null>(null);
  const [batchId, setBatchId] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [remaining, setRemaining] = useState(0);
  const [executed, setExecuted] = useState(false);
  const stopped = useRef(false);
  // The session queue survives a re-selection of the same folder, so batch 2 advances past batch 1
  // instead of re-slicing the same first 200. Keyed by the relative path the picker repeats verbatim.
  const queue = useRef<Map<string, File>>(new Map());
  const handled = useRef<Set<string>>(new Set());
  const folderRef = useRef<string | null>(null);
  const batchRef = useRef<string | null>(null);
  const running = useRef(false);

  function tally(list: Row[]): string {
    const count = (prefix: string) => list.filter((row) => row.state.startsWith(prefix)).length;
    return `已入队 ${count("已入队")} · 运行中 ${count("作业运行中")} · 已成功 ${count("已成功")}`
      + ` · 失败待重试 ${count("失败待重试")} · 仅保管 ${count("原件已保管")}`
      + ` · 冲突 ${count("作业身份冲突")} · 未入队 ${count("转换未入队")} · 跳过 ${count("跳过：") + count("未导入")}`;
  }

  async function processFile(file: File, relative: string, root: string): Promise<Row> {
    const refusal = refuseBeforeUpload(relative, file.size);
    if (refusal) { handled.current.add(relative); return { ...refusal, relative, bytes: file.size }; }
    try {
      const imported = await coreCommand<{ source_id?: unknown; sha256?: unknown; duplicate?: unknown }>(
        "source_import",
        {
          body: {
            name: relative,
            content_base64: base64Of(await file.arrayBuffer()),
            origin_kind: "path",
            // A stable opaque batch id, not the folder basename: two folders on different disks that
            // share a name stay distinguishable, and no absolute path is claimed from the browser.
            origin_ref: batchRef.current ?? root,
            origin_name: file.name,
          },
        });
      const sourceId = typeof imported.source_id === "string" ? imported.source_id : null;
      const digest = typeof imported.sha256 === "string" ? imported.sha256 : null;
      handled.current.add(relative);
      if (!sourceId || !digest) return { relative, bytes: file.size, state: "未导入", detail: "导入回执缺少 source_id 或 sha256" };
      const repeated = imported.duplicate === true ? "（同哈希原件已存在）" : "";
      const kind = conversionKindFor(relative);
      if (!kind) {
        return { relative, bytes: file.size, source_id: sourceId, state: "原件已保管，无转换通路",
          detail: `此扩展名没有映射到任何 Core 作业种类，所以未入队${repeated}。` };
      }
      try {
        const receipt = await coreCommand<{ job_id?: unknown; state?: unknown }>("job_enqueue",
          { body: { job_id: `folder-${kind}-${digest}`, kind, input_ref: sourceId } });
        const classified = classifyReceipt(receipt.state, kind, repeated);
        return { relative, bytes: file.size, source_id: sourceId, kind,
          job_id: typeof receipt.job_id === "string" ? receipt.job_id : `folder-${kind}-${digest}`,
          executable: classified.executable, state: classified.state, detail: classified.detail };
      } catch (error) {
        if (error instanceof ApiError && error.status === 409) {
          // 409 means the same job id was offered with a different kind or input — a real conflict,
          // not a duplicate. It must not be smoothed into "already queued".
          return { relative, bytes: file.size, source_id: sourceId, kind,
            state: "作业身份冲突", detail: `同一作业标识已持有不同的 ${kind} 参数，需要人工核对后处理。` };
        }
        return { relative, bytes: file.size, source_id: sourceId, kind, state: "转换未入队", detail: `本地核心拒绝了 ${kind} 作业。` };
      }
    } catch (error) {
      handled.current.add(relative);
      const detail = error instanceof ApiError || error instanceof Error ? error.message : "未知原因";
      return { relative, bytes: file.size, state: "未导入", detail };
    }
  }

  async function runBatch(start: Row[]) {
    if (running.current) return;
    running.current = true; setBusy(true); stopped.current = false;
    setExecuted(false);
    const outcome = start;
    const pending = [...queue.current.keys()].filter((relative) => !handled.current.has(relative))
      .sort((a, b) => a.localeCompare(b));
    const next = pending.slice(0, MAX_FILES);
    for (const relative of next) {
      if (stopped.current) break;
      const file = queue.current.get(relative)!;
      outcome.push(await processFile(file, relative, folderRef.current ?? ""));
      setRows([...outcome]);
    }
    window.dispatchEvent(new Event("archeaxis-job-changed"));
    const left = [...queue.current.keys()].filter((relative) => !handled.current.has(relative)).length;
    setRemaining(left);
    setMessage(`文件夹「${folder}」批次处理：本次 ${next.length} 项 · ${tally(outcome)}`
      + ` · ${left > 0 ? `剩余 ${left} 项待下一批（已成功或排除的项不重复占预算）` : "全部处理完毕"}`
      + (stopped.current ? " · 已按你的要求停止" : ""));
    setBusy(false); running.current = false;
  }

  // A06: the folder entry is not complete at "enqueued". Execute this batch's queued jobs through
  // the same bounded, cancellable path a single source uses, and reflect the real terminal state.
  async function executeBatch() {
    if (running.current) return;
    const targets = rows.filter((row) => row.executable && row.job_id);
    if (!targets.length) { setMessage("本批次没有等待执行的作业。"); return; }
    running.current = true; setBusy(true); stopped.current = false;
    const updated = [...rows];
    for (let index = 0; index < updated.length; index += 1) {
      const row = updated[index];
      if (!row.executable || !row.job_id) continue;
      if (stopped.current) break;
      updated[index] = { ...row, state: "执行中", detail: `正在执行 ${row.kind} 作业。` };
      setRows([...updated]);
      try {
        await coreCommand("job_execute", { job_id: row.job_id });
        window.dispatchEvent(new Event("archeaxis-job-changed"));
        let state: unknown = null; const deadline = Date.now() + EXECUTE_DEADLINE_MS;
        while (Date.now() < deadline) {
          const read = await coreCommand<{ state?: unknown }>("jobs_get", { job_id: row.job_id });
          state = read.state;
          if (["succeeded", "failed", "cancelled", "rejected"].includes(String(state))) break;
          await new Promise((resolve) => setTimeout(resolve, POLL_MS));
        }
        updated[index] = { ...row, executable: false, state: String(state ?? "未回执"),
          detail: state === "succeeded" ? "转换产物已持久化，可从资料页打开。"
            : ["failed", "cancelled", "rejected"].includes(String(state)) ? `执行结束于 ${String(state)}，可单独重试。`
              : `执行未在 ${EXECUTE_DEADLINE_MS / 1000}s 内进入终态，保持可重试。` };
      } catch (error) {
        updated[index] = { ...row, executable: false, state: "执行失败",
          detail: error instanceof Error ? error.message : "执行未完成" };
      }
      setRows([...updated]);
    }
    window.dispatchEvent(new Event("archeaxis-job-changed"));
    setExecuted(true);
    const done = updated.filter((row) => row.state === "succeeded").length;
    setMessage(`本批次执行：${done} 项成功，其余保留真实状态可单独重试${stopped.current ? " · 已停止" : ""}。`);
    setBusy(false); running.current = false;
  }

  async function asyncRetry(row: Row) {
    if (running.current || !row.job_id) return;
    setRows((list) => list.map((item) => item === row ? { ...item, state: "执行中", detail: `重试 ${item.kind} 作业。`, executable: true } : item));
    try {
      await coreCommand("job_execute", { job_id: row.job_id });
      const read = await coreCommand<{ state?: unknown }>("jobs_get", { job_id: row.job_id });
      window.dispatchEvent(new Event("archeaxis-job-changed"));
      setRows((list) => list.map((item) => item === row ? { ...item, executable: false, state: String(read.state ?? "未回执"), detail: "重试后读回真实状态。" } : item));
    } catch {
      setRows((list) => list.map((item) => item === row ? { ...item, executable: true, state: "执行失败", detail: "重试未完成，可再次尝试。" } : item));
    }
  }

  return (
    <section aria-label="文件夹导入">
      <h4>文件夹导入</h4>
      <label className="content-import">
        选择一个文件夹
        <input
          type="file"
          aria-label="选择文件夹"
          disabled={busy}
          {...({ webkitdirectory: "", directory: "" } as Record<string, string>)}
          multiple
          onChange={(event) => {
            const files = Array.from(event.target.files ?? []);
            event.target.value = "";
            if (!files.length) { setMessage("没有收到任何文件；浏览器可能拒绝了此选择。"); return; }
            const root = folderOf(files);
            if (!root) { setMessage("所选内容不像是同一个文件夹，未开始导入。"); return; }
            // Refuse this whole submission before importing anything if any visible path — root name
            // included, case-insensitive — sits in a private-state directory.
            const privates = files.map(privateVisibleSegment).filter((p): p is string => p !== null);
            if (privates.length) {
              setMessage(`整个文件夹被拒绝：${privates.length} 条路径落在私有状态目录里（如 ${privates[0]}），未导入任何文件。请重新选择或明确缩小范围。`);
              return;
            }
            if (folderRef.current !== root) {
              handled.current.clear(); queue.current.clear(); folderRef.current = root;
              batchRef.current = crypto.randomUUID(); setRows([]); setFolder(root); setBatchId(batchRef.current);
            }
            for (const file of files) queue.current.set(relativeOf(file), file);
            void runBatch([]);
          }}
        />
      </label>
      {folder ? <p>当前批次「{folder}」· 批次标识 {batchId?.slice(0, 8)}…；来源关系记为该批次标识下的相对路径。浏览器不把磁盘绝对路径交给产品，所以此处不声称绝对路径，父目录链也无法核验。</p> : null}
      <div>
        {remaining > 0 ? <button type="button" disabled={busy} onClick={() => void runBatch([...rows])}>下一批（剩余 {remaining}）</button> : null}
        {rows.some((row) => row.executable) ? <button type="button" disabled={busy} onClick={() => void executeBatch()}>执行本批次转换</button> : null}
        <button type="button" disabled={!busy} onClick={() => { stopped.current = true; }}>停止</button>
      </div>
      {message ? <p role="status">{message}</p> : null}
      {rows.length ? (
        <DataTable columns={[{ key: "relative", label: "文件夹内路径" }, { key: "bytes", label: "字节" },
          { key: "state", label: "结果" }, { key: "detail", label: "说明" },
          { key: "action", label: "操作" }]}
          rows={rows.map((row) => ({ relative: row.relative, bytes: String(row.bytes), state: row.state,
            detail: row.detail,
            action: row.job_id && (["失败待重试", "failed", "执行失败"].includes(row.state) || row.state.startsWith("已cancelled") || row.state.startsWith("已rejected"))
              ? <button type="button" onClick={() => void asyncRetry(row)}>重试</button> : null }))}
          empty="此文件夹没有可列出的文件。" />
      ) : null}
      {executed ? <p>执行完成不等同识别核验或专业依据已确认；结果可从资料页按真实转换读回。</p> : null}
    </section>
  );
}
