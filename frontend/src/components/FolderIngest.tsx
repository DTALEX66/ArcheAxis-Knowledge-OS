import { useRef, useState } from "react";
import { coreCommand } from "../api/core";
import { ApiError } from "../api/client";
import { conversionKindFor } from "../api/conversionKinds";
import { DataTable } from "./RealData";

// The folder entry drives the same two Core calls `scripts/ingest/directory_batch.py` drives, and
// keeps that script's refusals, so the folder closed loop does not change shape when it moves from
// the CLI to the screen. The script's own JSONL resume state cannot live here: the browser holds no
// file system, so idempotence comes from the Core instead — a job id derived from the stored
// original's hash, which the Core answers with 409 when that content was already queued.
const MAX_FILES = 200;
const MAX_BYTES = 64 * 1024 * 1024;
const EXCLUDED_DIRS = new Set([".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv",
  ".project-local", ".hermes", ".cache", "dist", "build", "target"]);
const PRIVATE_STATE = new Set([".zcode", ".codex", ".hermes", ".openhuman", ".git"]);

type Row = { path: string; bytes: number; state: string; detail: string };

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

function privateStatePath(relative: string): string | null {
  return relative.split("/").some((part) => PRIVATE_STATE.has(part)) ? relative : null;
}

function refuseBeforeUpload(relative: string, bytes: number): Row | null {
  const segments = relative.split("/");
  if (segments.some((part) => part.startsWith("."))) {
    return { path: relative, bytes, state: "跳过：隐藏路径", detail: "以点开头的路径不进入原件库。" };
  }
  if (segments.some((part) => EXCLUDED_DIRS.has(part))) {
    return { path: relative, bytes, state: "跳过：排除目录", detail: "构建与依赖目录不是用户的文档。" };
  }
  if (bytes > MAX_BYTES) {
    return { path: relative, bytes, state: "未导入：超过大小上限", detail: `原件导入上限为 ${MAX_BYTES / 1024 / 1024} MiB。` };
  }
  return null;
}

export function FolderIngest() {
  const [rows, setRows] = useState<Row[]>([]);
  const [folder, setFolder] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const stopped = useRef(false);

  async function ingest(files: File[], root: string) {
    setRows([]); setFolder(root); setBusy(true); stopped.current = false;
    const ordered = [...files].sort((a, b) => relativeOf(a).localeCompare(relativeOf(b)));
    const plan = ordered.map((file) => ({ file, relative: relativeOf(file) }));

    // The CLI refuses the whole folder rather than importing around private state; a folder
    // picker must not be the weaker surface.
    const privates = plan.map((item) => privateStatePath(item.relative)).filter((p): p is string => p !== null);
    if (privates.length) {
      setMessage(`整个文件夹被拒绝：${privates.length} 条路径落在私有状态目录里（如 ${privates[0]}），未导入任何文件。`);
      setBusy(false);
      return;
    }

    const beyond = plan.slice(MAX_FILES);
    const kept = plan.slice(0, MAX_FILES);
    const outcome: Row[] = [];
    for (const { file, relative } of kept) {
      if (stopped.current) {
        outcome.push({ path: relative, bytes: file.size, state: "跳过：未开始", detail: "已按你的要求停止；之前的结果保留。" });
        continue;
      }
      const refusal = refuseBeforeUpload(relative, file.size);
      if (refusal) { outcome.push(refusal); setRows([...outcome]); continue; }
      try {
        const imported = await coreCommand<{ source_id?: unknown; sha256?: unknown; duplicate?: unknown }>(
          "source_import",
          {
            body: {
              name: relative,
              content_base64: base64Of(await file.arrayBuffer()),
              origin_kind: "path",
              origin_ref: root,
              origin_name: file.name,
            },
          });
        const sourceId = typeof imported.source_id === "string" ? imported.source_id : null;
        const digest = typeof imported.sha256 === "string" ? imported.sha256 : null;
        if (!sourceId || !digest) throw new Error("导入回执缺少 source_id 或 sha256");
        const repeated = imported.duplicate === true ? "（同哈希原件已存在）" : "";
        const kind = conversionKindFor(relative);
        if (!kind) {
          outcome.push({ path: relative, bytes: file.size, state: "原件已保管，无转换通路",
            detail: `此扩展名没有映射到任何 Core 作业种类，所以未入队${repeated}。` });
        } else {
          try {
            await coreCommand("job_enqueue", { body: { job_id: `folder-${digest.slice(0, 12)}`, kind, input_ref: sourceId } });
            outcome.push({ path: relative, bytes: file.size, state: "已入队转换", detail: `${kind} 作业已受理${repeated}。` });
          } catch (error) {
            if (error instanceof ApiError && error.status === 409) {
              outcome.push({ path: relative, bytes: file.size, state: "已在队列中", detail: `本地核心已为此内容持有 ${kind} 作业${repeated}。` });
            } else {
              outcome.push({ path: relative, bytes: file.size, state: "转换未入队", detail: `本地核心拒绝了 ${kind} 作业。` });
            }
          }
        }
      } catch (error) {
        const detail = error instanceof ApiError || error instanceof Error ? error.message : "未知原因";
        outcome.push({ path: relative, bytes: file.size, state: "未导入", detail });
      }
      setRows([...outcome]);
    }
    for (const { file, relative } of beyond) {
      outcome.push({ path: relative, bytes: file.size, state: "跳过：超过本次上限",
        detail: `一次最多处理 ${MAX_FILES} 个文件；请再次选择同一文件夹，已入库的内容会记为“已在队列中”。` });
    }
    setRows(outcome);
    const tally = (prefix: string) => outcome.filter((row) => row.state.startsWith(prefix)).length;
    setMessage(`文件夹「${root}」清点完成：共 ${outcome.length} 项 · 已入队 ${tally("已入队")} · 已在队列 ${tally("已在队列")}`
      + ` · 仅保管 ${tally("原件已保管")} · 未导入 ${tally("未导入")} · 入队被拒 ${tally("转换未入队")}`
      + ` · 跳过 ${tally("跳过：")}${stopped.current ? " · 已停止" : ""}。`);
    setBusy(false);
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
            const root = files.length ? folderOf(files) : null;
            if (!files.length) { setMessage("没有收到任何文件；浏览器可能拒绝了此选择。"); return; }
            if (!root) { setMessage("所选内容不像是同一个文件夹，未开始导入。"); return; }
            void ingest(files, root);
          }}
        />
      </label>
      <button type="button" disabled={!busy} onClick={() => { stopped.current = true; }}>停止</button>
      {message ? <p role="status">{message}</p> : null}
      {folder ? <p>来源关系记为「{folder}」下的相对路径；浏览器不把磁盘绝对路径交给产品，所以此处不声称绝对路径，父目录链也无法核验。</p> : null}
      {rows.length ? (
        <DataTable columns={[{ key: "path", label: "文件夹内路径" }, { key: "bytes", label: "字节" },
          { key: "state", label: "结果" }, { key: "detail", label: "说明" }]}
          rows={rows.map((row) => ({ ...row, bytes: String(row.bytes) }))}
          empty="此文件夹没有可列出的文件。" />
      ) : null}
    </section>
  );
}
