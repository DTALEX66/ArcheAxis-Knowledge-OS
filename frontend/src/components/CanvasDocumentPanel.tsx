import { useEffect, useState } from "react";
import type { DocumentDto, OriginalDto, SourceDto } from "../api/generated/core-contract";
import { mappedCanvasTexts, verifiedCanvas, type CanvasSource } from "../presentation/canvasDocument";

/** Inert saved-source projection. Paths, URLs, Markdown and background declarations are text only. */
export function CanvasDocumentPanel({ source, original, bytes, document }: { source: SourceDto; original: OriginalDto; bytes: Uint8Array; document?: DocumentDto }) {
  const identity = JSON.stringify([source.source_id, source.source_revision, document?.document_id, document?.version, document?.content_sha256]);
  const [state, setState] = useState<{ identity: string; canvas?: CanvasSource; texts?: Map<string, string>; error?: string }>({ identity });
  useEffect(() => {
    let alive = true;
    setState({ identity });
    void verifiedCanvas(source, original, bytes).then(canvas => {
      const texts = document ? mappedCanvasTexts(canvas, source, document) : new Map(canvas.nodes.filter(n => n.type === "text").map(n => [n.id, n.text as string]));
      if (alive) setState({ identity, canvas, texts });
    }).catch(error => { if (alive) setState({ identity, error: error instanceof Error ? error.message : "画布读取未确认；原件仍保留。" }); });
    return () => { alive = false; };
  }, [identity, source, original, bytes, document]);
  const shown: typeof state = state.identity === identity ? state : { identity };
  const canvas = shown.canvas;
  if (!canvas) return <section aria-label="只读画布"><p role={shown.error ? "alert" : "status"}>{shown.error ?? "正在核对固定画布原件…"}</p></section>;
  const minX = Math.min(0, ...canvas.nodes.map(n => n.x)), minY = Math.min(0, ...canvas.nodes.map(n => n.y));
  const width = Math.max(1, ...canvas.nodes.map(n => n.x + n.width - minX)), height = Math.max(1, ...canvas.nodes.map(n => n.y + n.height - minY));
  const nodes = new Map(canvas.nodes.map(n => [n.id, n]));
  return <section aria-label="只读画布">
    <h4>{document ? `已保存版画布 · v${document.version}` : "固定原件画布"}</h4>
    <p>只读位置与连线示意；完整文字和引用声明列在下方。文件、链接、背景与扩展字段保留在原件中，不打开目标或执行内容。</p>
    <p>编辑只替换原文本节点的文字。坐标、节点增删、附件打包及外部软件往返尚未提供；富文本格式不转换为 Canvas Markdown。</p>
    <svg role="img" aria-label="画布位置与连线示意" viewBox={`${minX} ${minY} ${width} ${height}`} style={{ width: "100%", height: 280, border: "1px solid var(--ax-border)" }}>
      {canvas.edges.map(edge => { const from = nodes.get(edge.fromNode)!, to = nodes.get(edge.toNode)!; return <line key={edge.id} x1={from.x + from.width / 2} y1={from.y + from.height / 2} x2={to.x + to.width / 2} y2={to.y + to.height / 2} stroke="currentColor"><title>{edge.id}{typeof edge.label === "string" ? ` · ${edge.label}` : ""}</title></line>; })}
      {canvas.nodes.map(node => <g key={node.id}><rect x={node.x} y={node.y} width={node.width} height={node.height} fill="var(--ax-bg-inset, transparent)" stroke="currentColor"/><text x={node.x + 4} y={node.y + 16} fill="currentColor" fontSize={14}>{node.id}</text></g>)}
    </svg>
    <p>{canvas.nodes.length} 个节点 · {canvas.edges.length} 条连线；颜色、边端样式和分组背景未在示意图复现。</p>
    <ol>{canvas.nodes.map(node => <li key={node.id}><strong>{node.id} · {node.type}</strong>
      {node.type === "text" ? <pre style={{ whiteSpace: "pre-wrap" }}>{shown.texts?.get(node.id)}</pre> : node.type === "file" ? <p>文件声明：{String(node.file)}{typeof node.subpath === "string" ? node.subpath : ""}（未打开）</p> : node.type === "link" ? <p>链接声明：{String(node.url)}（未打开）</p> : <p>分组：{typeof node.label === "string" ? node.label : "未命名"}{typeof node.background === "string" ? `；背景声明：${node.background}（未打开）` : ""}</p>}
    </li>)}</ol>
    {canvas.edges.length ? <details><summary>连线声明</summary><ul>{canvas.edges.map(edge => <li key={edge.id}>{edge.id}：{edge.fromNode} → {edge.toNode}{typeof edge.label === "string" ? ` · ${edge.label}` : ""}</li>)}</ul></details> : null}
  </section>;
}
