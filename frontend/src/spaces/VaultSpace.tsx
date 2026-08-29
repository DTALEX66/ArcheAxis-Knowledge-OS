import { useCallback, useState } from "react";
import { DataError, Section } from "../components/RealData";
import {
  inspectVault,
  listVaultBackups,
  readVaultCanvas,
  readVaultFile,
  restoreVaultBackup,
  searchVault,
  writeVaultCanvas,
  writeVaultFile,
  type VaultFileDto,
  type VaultFileEntryDto,
  type VaultInspectDto,
  type VaultSearchResultDto,
} from "../api/workspace";
import { userErrorMessage } from "../presentation/labels";

const KIND_LABELS: Record<string, string> = {
  markdown: "Markdown",
  canvas: "画布",
  attachment: "附件",
};

function fileKindLabel(kind: string): string {
  return KIND_LABELS[kind] ?? kind;
}

function CanvasBoard({ doc, onChange }: { doc: Record<string, unknown>; onChange: (next: Record<string, unknown>) => void }) {
  const nodes = Array.isArray(doc.nodes) ? doc.nodes as Array<Record<string, unknown>> : [];
  const edges = Array.isArray(doc.edges) ? doc.edges as Array<Record<string, unknown>> : [];

  function addTextNode() {
    const text = window.prompt("新文本节点内容");
    if (text === null) return;
    const id = `node-${Date.now().toString(36)}`;
    onChange({
      ...doc,
      nodes: [
        ...nodes,
        { id, type: "text", x: 0, y: 0, width: 280, height: 60, text },
      ],
    });
  }

  function removeNode(id: string) {
    onChange({
      ...doc,
      nodes: nodes.filter((node) => node.id !== id),
      edges: edges.filter((edge) => edge.fromNode !== id && edge.toNode !== id),
    });
  }

  function renameNode(id: string) {
    const current = nodes.find((node) => node.id === id);
    const next = window.prompt("节点文本", String(current?.text ?? ""));
    if (next === null) return;
    onChange({
      ...doc,
      nodes: nodes.map((node) => node.id === id ? { ...node, text: next } : node),
    });
  }

  return (
    <div className="canvas-board" aria-label="画布内容">
      <div className="canvas-toolbar">
        <button type="button" onClick={addTextNode}>添加文本节点</button>
        <span className="muted">画布节点 {nodes.length} · 连线 {edges.length}</span>
      </div>
      {nodes.length === 0 ? <p className="muted">空画布。添加文本节点开始绘制。</p> : (
        <ul className="canvas-nodes">
          {nodes.map((node) => (
            <li key={String(node.id)}>
              <span className="canvas-node-type">{String(node.type ?? "text")}</span>
              <span className="canvas-node-text">{String(node.text ?? node.file ?? node.url ?? "节点")}</span>
              <button type="button" aria-label={`编辑节点 ${String(node.text ?? node.id ?? "")}`} onClick={() => renameNode(String(node.id))}>编辑</button>
              <button type="button" aria-label={`删除节点 ${String(node.text ?? node.id ?? "")}`} onClick={() => removeNode(String(node.id))}>删除</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function VaultSpace() {
  const [root, setRoot] = useState("");
  const [inspect, setInspect] = useState<VaultInspectDto | null>(null);
  const [openFile, setOpenFile] = useState<VaultFileDto | null>(null);
  const [editing, setEditing] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<VaultSearchResultDto[]>([]);
  const [backups, setBackups] = useState<Array<{ backup_name: string; file_size: number; modified: number }>>([]);
  const [busy, setBusy] = useState<"open" | "read" | "save" | "search" | "restore" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const openLibrary = useCallback(async (nextRoot: string) => {
    setBusy("open");
    setError(null);
    setMessage(null);
    try {
      const result = await inspectVault(nextRoot);
      setRoot(nextRoot);
      setInspect(result);
      setOpenFile(null);
      setSearchResults([]);
      setMessage(`已打开知识库：${result.root_name} · ${result.files.length} 个文件`);
    } catch (e) {
      setError(userErrorMessage(e instanceof Error ? e.message : e));
    } finally {
      setBusy(null);
    }
  }, []);

  async function openEntry(entry: VaultFileEntryDto) {
    setBusy("read");
    setError(null);
    setMessage(null);
    try {
      const file = entry.kind === "canvas"
        ? await readVaultCanvas(root, entry.relative_path)
        : await readVaultFile(root, entry.relative_path);
      setOpenFile(file);
      setEditing(file.raw_text);
      setBackups([]);
      if (entry.kind !== "attachment") {
        try {
          const backupPage = await listVaultBackups(root, entry.relative_path);
          setBackups(backupPage.backups);
        } catch {
          setBackups([]);
        }
      }
      setMessage(`已读取：${entry.relative_path}`);
    } catch (e) {
      setError(userErrorMessage(e instanceof Error ? e.message : e));
    } finally {
      setBusy(null);
    }
  }

  async function saveFile() {
    if (!openFile) return;
    setBusy("save");
    setError(null);
    try {
      if (openFile.is_canvas) {
        let canvas: Record<string, unknown>;
        try {
          canvas = JSON.parse(editing) as Record<string, unknown>;
        } catch (e) {
          setError("画布内容不是有效的 JSON，无法保存。");
          return;
        }
        await writeVaultCanvas(root, openFile.relative_path, canvas, openFile.source_hash);
      } else {
        await writeVaultFile(root, openFile.relative_path, editing, openFile.source_hash);
      }
      setMessage("已保存；写回时使用了乐观锁校验。");
      const refreshed = openFile.is_canvas
        ? await readVaultCanvas(root, openFile.relative_path)
        : await readVaultFile(root, openFile.relative_path);
      setOpenFile(refreshed);
      setEditing(refreshed.raw_text);
    } catch (e) {
      const detail = e instanceof Error ? e.message : String(e);
      if (detail.includes("409") || detail.includes("conflict") || /已修改/.test(detail)) {
        setError("文件在读取后被其他程序修改；请重新读取后再保存。");
      } else {
        setError(userErrorMessage(detail));
      }
    } finally {
      setBusy(null);
    }
  }

  async function runSearch() {
    const query = searchQuery.trim();
    if (!query || !root) return;
    setBusy("search");
    setError(null);
    try {
      const result = await searchVault(root, query);
      setSearchResults(result.results);
      setMessage(`搜索「${query}」：${result.results.length} 处匹配`);
    } catch (e) {
      setError(userErrorMessage(e instanceof Error ? e.message : e));
    } finally {
      setBusy(null);
    }
  }

  async function restoreBackup(backupName: string) {
    if (!openFile) return;
    if (!window.confirm(`恢复备份 ${backupName}？当前状态会先被快照。`)) return;
    setBusy("restore");
    setError(null);
    try {
      await restoreVaultBackup(root, openFile.relative_path, backupName);
      const refreshed = openFile.is_canvas
        ? await readVaultCanvas(root, openFile.relative_path)
        : await readVaultFile(root, openFile.relative_path);
      setOpenFile(refreshed);
      setEditing(refreshed.raw_text);
      setMessage("已从备份恢复并重新读取。");
    } catch (e) {
      setError(userErrorMessage(e instanceof Error ? e.message : e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <Section title="知识库">
      <p className="muted">打开一个本地知识库目录（只读扫描；写入使用哈希乐观锁并自动留备份）。</p>
      <div className="intake-row">
        <label className="visually-hidden" htmlFor="vault-root">知识库路径</label>
        <input id="vault-root" value={root} onChange={(event) => setRoot(event.target.value)} placeholder="D:/Obsidian 知识库" aria-label="知识库路径" />
        <button type="button" onClick={() => void openLibrary(root)} disabled={busy !== null}>{busy === "open" ? "正在扫描…" : "打开知识库"}</button>
      </div>

      {inspect ? (
        <div className="vault-layout">
          <aside className="vault-side" aria-label="知识库文件">
            <div className="intake-row">
              <label className="visually-hidden" htmlFor="vault-search">搜索知识库</label>
              <input id="vault-search" value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} placeholder="搜索文本…" aria-label="搜索知识库" />
              <button type="button" onClick={() => void runSearch()} disabled={busy !== null || !searchQuery.trim()}>搜索</button>
            </div>
            {searchResults.length > 0 ? (
              <ul className="vault-search-results">
                {searchResults.map((result) => (
                  <li key={result.relative_path}>
                    <button type="button" onClick={() => {
                      const entry = inspect.files.find((file) => file.relative_path === result.relative_path);
                      if (entry) void openEntry(entry);
                    }}>{result.relative_path}<small>{result.snippet}</small></button>
                  </li>
                ))}
              </ul>
            ) : (
              <ul className="vault-file-list">
                {inspect.files.map((entry) => (
                  <li key={entry.relative_path}>
                    <button type="button" onClick={() => void openEntry(entry)} disabled={entry.kind === "attachment" || busy !== null}>
                      <span className="vault-kind">{fileKindLabel(entry.kind)}</span>
                      <span className="vault-path">{entry.relative_path}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </aside>

          <div className="vault-main">
            {openFile ? (
              <>
                <header className="vault-file-header">
                  <div><span className="archive-eyebrow">当前文件</span><h4>{openFile.relative_path}</h4></div>
                  {openFile.is_canvas ? (
                    <button type="button" onClick={() => void saveFile()} disabled={busy !== null}>{busy === "save" ? "正在保存…" : "保存画布"}</button>
                  ) : (
                    <button type="button" onClick={() => void saveFile()} disabled={busy !== null}>{busy === "save" ? "正在保存…" : "保存"}</button>
                  )}
                </header>
                {openFile.is_canvas ? (
                  <CanvasBoard doc={openFile.canvas ?? { nodes: [], edges: [] }} onChange={(next) => {
                    setOpenFile({ ...openFile, canvas: next });
                    setEditing(JSON.stringify(next, null, 2));
                  }} />
                ) : (
                  <textarea
                    className="vault-editor"
                    aria-label={`编辑 ${openFile.relative_path}`}
                    value={editing}
                    onChange={(event) => setEditing(event.target.value)}
                    spellCheck={false}
                  />
                )}
                {backups.length > 0 ? (
                  <section className="vault-backups" aria-label="文件备份">
                    <h5>可恢复备份</h5>
                    <ul>{backups.map((backup) => (
                      <li key={backup.backup_name}>
                        <span>{backup.backup_name}</span>
                        <button type="button" onClick={() => void restoreBackup(backup.backup_name)} disabled={busy !== null}>恢复</button>
                      </li>
                    ))}</ul>
                  </section>
                ) : null}
              </>
            ) : <p className="muted">选择一个文件查看或编辑；附件只读（元数据）。</p>}
          </div>
        </div>
      ) : null}

      {error ? <DataError label="知识库" message={error} /> : null}
      {message ? <p role="status" className="muted">{message}</p> : null}
    </Section>
  );
}
