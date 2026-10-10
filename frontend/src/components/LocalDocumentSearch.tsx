import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import type { DocumentSearchDto, SearchDto } from "../api/generated/core-contract";
import { coreFailureReason } from "../presentation/labels";

/** Explicit local Core text search, independent of AI/provider availability. */
export function LocalDocumentSearch({ onOpenDocument }: { onOpenDocument?: (id: string) => void }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<DocumentSearchDto[]>([]);
  const [searchedQuery, setSearchedQuery] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState("");
  const epoch = useRef(0);
  const composing = useRef(false);
  useEffect(() => () => { epoch.current++; }, []);
  async function search() {
    if (composing.current) return;
    const value = query.trim();
    const request = ++epoch.current;
    setFailure(""); setResults([]); setSearchedQuery(null);
    if (!value) { setBusy(false); return; }
    if (new TextEncoder().encode(value).length > 512) {
      setBusy(false); setFailure("搜索文字超过本地检索长度限制，请缩短后重试。"); return;
    }
    setBusy(true);
    try {
      const result = await coreCommand<SearchDto>("search", { q: value, active_only: false });
      const rows = result.documents;
      if (!Array.isArray(rows) || rows.length > 20 || result.document_count !== rows.length
          || new Set(rows.map(row => row.document_id)).size !== rows.length
          || rows.some(row => typeof row.document_id !== "string" || !row.document_id
            || typeof row.title !== "string" || typeof row.head !== "string"
            || !Number.isSafeInteger(row.version) || row.version < 1
            || typeof row.content_sha256 !== "string" || !/^[a-f0-9]{64}$/.test(row.content_sha256))) {
        throw new Error("本地文档搜索结果身份或数量不兼容。");
      }
      if (request === epoch.current) { setResults(rows); setSearchedQuery(value); }
    } catch (error) {
      if (request === epoch.current) setFailure(coreFailureReason(error) ?? "本地文档搜索未完成，请重试。");
    } finally { if (request === epoch.current) setBusy(false); }
  }
  return <section className="ui-local-search" aria-label="本地文档搜索">
    <h2>查找已保存文档</h2>
    <p>搜索本地文档标题与正文，最多显示 20 个结果。AI 语义检索另行进入。</p>
    <form onSubmit={event => { event.preventDefault(); void search(); }}>
      <label>搜索本地文档<input type="search" value={query}
        onCompositionStart={() => { composing.current = true; }} onCompositionEnd={() => { composing.current = false; }}
        onKeyDown={event => { if (event.key === "Enter" && (event.nativeEvent.isComposing || composing.current)) event.preventDefault(); }}
        onChange={event => {
          epoch.current++; setQuery(event.target.value); setBusy(false); setResults([]); setSearchedQuery(null); setFailure("");
        }} /></label>
      <button disabled={busy || !query.trim()}>搜索文档</button>
    </form>
    {busy ? <p role="status">正在搜索本地文档…</p> : null}
    {failure ? <p role="alert">{failure}</p> : null}
    {searchedQuery !== null ? <p role="status">“{searchedQuery}” · {results.length} 个文档结果{results.length === 20 ? "（达到本次上限，可缩小搜索范围）" : ""}</p> : null}
    <ul aria-label="本地文档搜索结果">{results.map(row => <li key={row.document_id}>
      <button disabled={!onOpenDocument} onClick={() => onOpenDocument?.(row.document_id)}>{row.title} · v{row.version}</button>
      <p>{row.head}</p><small>文档 {row.document_id} · {row.source_id ? `来源 ${row.source_id}` : "原创文档"}</small>
    </li>)}</ul>
  </section>;
}
