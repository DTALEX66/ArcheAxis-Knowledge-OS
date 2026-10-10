import { useEffect, useRef, useState, type ReactNode, type KeyboardEvent, type PointerEvent } from "react";
import { EXPRESSION_LIMITS, expressionTextBytes, validExpressionMedia, type ExpressionDocument, type ExpressionMedia, type ExpressionNode } from "../presentation/expression";
import "./expression-board.css";

export interface CanonicalExpressionBoardProps {
  value: ExpressionDocument;
  onChange: (next: ExpressionDocument) => void;
  onAddMedia?: () => Promise<ExpressionMedia | null>;
  /** Host resolves actual Core CAS bytes. No arbitrary URL/HTML is accepted by the board. */
  renderMedia?: (media: ExpressionMedia, node: ExpressionNode) => ReactNode;
  readOnly?: boolean;
  disabled?: boolean;
  documentKey?: string;
  onPendingEditChange?: (pending: boolean) => void;
}
function GeometryInput({ label, value, onDraft, onCommit, onCancel, pending }: { label: string; value: string; onDraft: (raw: string) => void; onCommit: () => void; onCancel: () => void; pending: boolean }) {
  return <span className="expression-geometry-input"><input aria-label={label} type="text" inputMode="decimal" value={value} onChange={event => onDraft(event.target.value)} onBlur={onCommit} onKeyDown={event => { if (event.key === "Enter" && !event.nativeEvent.isComposing) { event.preventDefault(); onCommit(); } if (event.key === "Escape" && !event.nativeEvent.isComposing) { event.preventDefault(); onCancel(); } }} />{pending ? <button type="button" aria-label={`取消${label}修改`} onMouseDown={event => event.preventDefault()} onClick={onCancel}>取消</button> : null}</span>;
}
export function CanonicalExpressionBoard({ value, onChange, onAddMedia, renderMedia, readOnly = false, disabled = false, documentKey = "default", onPendingEditChange }: CanonicalExpressionBoardProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [from, setFrom] = useState(""); const [to, setTo] = useState(""); const [label, setLabel] = useState("");
  const [error, setError] = useState<string | null>(null); const [addingMedia, setAddingMedia] = useState(false);
  const drag = useRef<{ id: string; x: number; y: number; clientX: number; clientY: number } | null>(null);
  const locked = readOnly || disabled;
  const [geometryDrafts, setGeometryDrafts] = useState<Record<string, string>>({});
  const requestSerial = useRef(0);
  const pendingCallback = useRef(onPendingEditChange); pendingCallback.current = onPendingEditChange;
  const pending = !locked && (Object.keys(geometryDrafts).length > 0 || !!from || !!to || !!label || addingMedia);
  useEffect(() => { onPendingEditChange?.(pending); }, [pending, onPendingEditChange]);
  useEffect(() => {
    requestSerial.current++; setGeometryDrafts({}); setFrom(""); setTo(""); setLabel(""); setAddingMedia(false); setError(null); setSelectedId(null); drag.current = null;
  }, [documentKey, locked]);
  useEffect(() => () => { requestSerial.current++; pendingCallback.current?.(false); }, []);
  function clearGeometry(key: string) { setGeometryDrafts(drafts => { const next = { ...drafts }; delete next[key]; return next; }); }
  function draftGeometry(key: string, raw: string, stored: number) {
    if (raw === String(stored)) clearGeometry(key); else setGeometryDrafts(drafts => ({ ...drafts, [key]: raw }));
  }
  function cancelConnection() { setFrom(""); setTo(""); setLabel(""); setError(null); }
  function cancelMedia() { requestSerial.current++; setAddingMedia(false); setError(null); }

  const current = useRef({ value, locked, documentKey }); current.current = { value, locked, documentKey };
  const selected = value.nodes.find(node => node.id === selectedId);
  const originX = Math.min(0, ...value.nodes.map(n => n.x)) - 24;
  const originY = Math.min(0, ...value.nodes.map(n => n.y)) - 24;
  const width = Math.max(600, ...value.nodes.map(n => n.x + n.width - originX + 24));
  const height = Math.max(400, ...value.nodes.map(n => n.y + n.height - originY + 24));
  const nodeMap = new Map(value.nodes.map(n => [n.id, n]));
  function emit(next: ExpressionDocument) { if (!locked) { setError(null); onChange(next); } }
  function updateNode(id: string, patch: Partial<ExpressionNode>) {
    emit({ ...value, nodes: value.nodes.map(n => n.id === id ? { ...n, ...patch } : n) });
  }
  function addNode(type: "text" | "media", media?: ExpressionMedia) {
    if (locked) return;
    if (value.nodes.length >= EXPRESSION_LIMITS.nodes) { setError("节点已达 500 个上限。"); return; }
    const id = crypto.randomUUID();
    const node: ExpressionNode = { id, type, x: 24, y: 24, width: 260, height: 180, text: "", ...(media ? { media } : {}) };
    emit({ ...value, nodes: [...value.nodes, node] }); setSelectedId(id);
  }
  async function addMedia() {
    if (locked || !onAddMedia || addingMedia) return;
    const serial = ++requestSerial.current;
    setAddingMedia(true);setError(null);
    try { const media = await onAddMedia(); if (serial !== requestSerial.current || current.current.documentKey !== documentKey) return; if (current.current.locked || current.current.value !== value) { setError("画布已变更；请重新选择媒体，避免覆盖当前内容。"); return; } if (media) { if (!validExpressionMedia(media)) { setError("媒体来源、指纹或类型无效；未添加节点。"); } else { addNode("media", media); } } }
    catch { if (serial === requestSerial.current) setError("媒体来源读取失败；未添加节点。"); }
    finally { if (serial === requestSerial.current) setAddingMedia(false); }
  }
  function removeNode(id: string) {
    emit({ ...value, nodes: value.nodes.filter(n => n.id !== id), edges: value.edges.filter(e => e.fromNode !== id && e.toNode !== id) });
    setGeometryDrafts(drafts => Object.fromEntries(Object.entries(drafts).filter(([key]) => !key.startsWith(`${id}:`))));
    if (selectedId === id) setSelectedId(null);
  }
  function changeNumber(node: ExpressionNode, key: "x" | "y" | "width" | "height", raw: string) {
    const number = Number(raw); const dimension = key === "width" || key === "height";
    if (!raw.trim() || !Number.isFinite(number) || (dimension ? number < 1 || number > EXPRESSION_LIMITS.dimension : Math.abs(number) > EXPRESSION_LIMITS.coordinate)) {
      setError(dimension ? "尺寸需在 1 至 10000 之间。" : "坐标需在 -100000 至 100000 之间。"); return false;
    }
    updateNode(node.id, { [key]: number }); return true;
  }
  function changeText(node: ExpressionNode, text: string) {
    if (expressionTextBytes(text) > EXPRESSION_LIMITS.textBytes) { setError("节点文字超出 16384 字节上限；内容未截断。"); return; }
    updateNode(node.id, { text });
  }
  function move(node: ExpressionNode, x: number, y: number) {
    if (Math.abs(x) > EXPRESSION_LIMITS.coordinate || Math.abs(y) > EXPRESSION_LIMITS.coordinate) { setError("移动超出坐标边界。"); return; }
    updateNode(node.id, { x, y });
  }
  function keyboard(event: KeyboardEvent<HTMLElement>, node: ExpressionNode) {
    if (locked || event.isDefaultPrevented() || event.nativeEvent.isComposing || (event.target as HTMLElement).closest("input, textarea, select, button")) return;
    const deltas: Record<string, [number, number]> = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
    const delta = deltas[event.key]; if (!delta) return;
    event.preventDefault(); const step = event.shiftKey ? 10 : 1; move(node, node.x + delta[0] * step, node.y + delta[1] * step);
  }
  function pointerDown(event: PointerEvent<HTMLButtonElement>, node: ExpressionNode) {
    if (locked || event.button !== 0) return;
    setSelectedId(node.id); drag.current = { id: node.id, x: node.x, y: node.y, clientX: event.clientX, clientY: event.clientY };
    event.currentTarget.setPointerCapture(event.pointerId);
  }
  function pointerMove(event: PointerEvent<HTMLButtonElement>) {
    const state = drag.current; if (!state || locked) return;
    const node = nodeMap.get(state.id); if (node) move(node, Math.round(state.x + event.clientX - state.clientX), Math.round(state.y + event.clientY - state.clientY));
  }
  function addEdge() {
    if (locked) return;
    if (!nodeMap.has(from) || !nodeMap.has(to)) { setError("请选择真实起点与终点节点。"); return; }
    if (value.edges.length >= EXPRESSION_LIMITS.edges || expressionTextBytes(label) > EXPRESSION_LIMITS.labelBytes) { setError("连线数量或文字超出上限。"); return; }
    emit({ ...value, edges: [...value.edges, { id: crypto.randomUUID(), fromNode: from, toNode: to, label }] });cancelConnection();
  }
  return <section className="expression-board" aria-label="表达画布">
    <div className="expression-toolbar">
      <button type="button" disabled={locked} onClick={() => addNode("text")}>添加文本节点</button>
      <button type="button" disabled={locked || !onAddMedia || addingMedia} onClick={() => void addMedia()}>{addingMedia ? "读取媒体来源…" : "添加媒体节点"}</button>
      {addingMedia ? <button type="button" onClick={cancelMedia}>取消媒体添加</button> : null}
      <span>节点 {value.nodes.length} · 连线 {value.edges.length}</span>
    </div>
    <p className="muted">选择节点后用方向键移动，Shift + 方向键移动 10；负坐标原样保留。媒体来自已校验来源。</p>
    {error ? <p role="alert">{error}</p> : null}
    <label className="expression-picker">当前节点<select aria-label="当前节点" value={selected?.id ?? ""} onChange={e => setSelectedId(e.target.value || null)}><option value="">选择节点</option>{value.nodes.map((n, i) => <option key={n.id} value={n.id}>节点 {i + 1} · {n.type === "text" ? "文字" : "媒体"}</option>)}</select></label>
    {selected ? <fieldset className="expression-properties" disabled={locked}><legend>节点位置与尺寸</legend>{(["x", "y", "width", "height"] as const).map((key, i) => <label key={key}>{["X 坐标", "Y 坐标", "宽度", "高度"][i]}<GeometryInput key={`${documentKey}-${selected.id}-${key}`} label={["X 坐标", "Y 坐标", "宽度", "高度"][i]} value={geometryDrafts[`${selected.id}:${key}`] ?? String(selected[key])} pending={geometryDrafts[`${selected.id}:${key}`] !== undefined} onDraft={raw => draftGeometry(`${selected.id}:${key}`, raw, selected[key])} onCommit={() => { const raw = geometryDrafts[`${selected.id}:${key}`]; if (raw !== undefined && changeNumber(selected, key, raw)) clearGeometry(`${selected.id}:${key}`); }} onCancel={() => { clearGeometry(`${selected.id}:${key}`); setError(null); }} /></label>)}</fieldset> : null}
    <div className="expression-viewport" aria-label="画布滚动区域" tabIndex={0}>
      <div className="expression-plane" style={{ width, height }}>
        <svg className="expression-edges" width={width} height={height} aria-hidden="true">{value.edges.map(edge => {
          const a = nodeMap.get(edge.fromNode); const b = nodeMap.get(edge.toNode); if (!a || !b) return null;
          const x1 = a.x + a.width / 2 - originX; const y1 = a.y + a.height / 2 - originY; const x2 = b.x + b.width / 2 - originX; const y2 = b.y + b.height / 2 - originY;
          return <g key={edge.id}><line x1={x1} y1={y1} x2={x2} y2={y2} /></g>;
        })}</svg>
        {value.edges.map((edge, i) => {
          const a = nodeMap.get(edge.fromNode), b = nodeMap.get(edge.toNode);
          if (!a || !b || !edge.label) return null;
          return <span key={edge.id} className="expression-edge-label" title={edge.label} aria-label={`连线 ${i + 1}: ${edge.label}`} style={{ left: (a.x + a.width / 2 + b.x + b.width / 2) / 2 - originX, top: (a.y + a.height / 2 + b.y + b.height / 2) / 2 - originY - 6 }}>{edge.label}</span>;
        })}
        {value.nodes.map((node, i) => <article key={node.id} className="expression-node" aria-label={`节点 ${i + 1}`} tabIndex={0} onFocus={() => setSelectedId(node.id)} onKeyDown={event => keyboard(event, node)} style={{ left: node.x - originX, top: node.y - originY, width: node.width, height: node.height }}>
          <header><button type="button" aria-label={`拖动节点 ${i + 1}`} disabled={locked} onPointerDown={event => pointerDown(event, node)} onPointerMove={pointerMove} onPointerUp={() => { drag.current = null; }} onPointerCancel={() => { drag.current = null; }}>节点 {i + 1}</button><button type="button" aria-label={`删除节点 ${i + 1}`} disabled={locked} onClick={() => removeNode(node.id)}>删除</button></header>
          {node.type === "media" ? <div className="expression-media">{node.media && validExpressionMedia(node.media) && renderMedia ? renderMedia(node.media, node) : <p>媒体预览未接通或来源无效。</p>}</div> : null}
          <textarea aria-label={`${node.type === "media" ? "媒体说明" : "节点文字"} ${i + 1}`} value={node.text} readOnly={locked} onChange={event => changeText(node, event.target.value)} />
        </article>)}
      </div>
    </div>
    {value.nodes.length === 0 ? <p className="muted">空画布。添加节点开始表达。</p> : null}
    <fieldset className="expression-connect" disabled={locked}><legend>添加连线</legend><label>起点<select aria-label="连线起点" value={from} onChange={e => setFrom(e.target.value)}><option value="">选择起点</option>{value.nodes.map((n, i) => <option key={n.id} value={n.id}>节点 {i + 1}</option>)}</select></label><label>终点<select aria-label="连线终点" value={to} onChange={e => setTo(e.target.value)}><option value="">选择终点</option>{value.nodes.map((n, i) => <option key={n.id} value={n.id}>节点 {i + 1}</option>)}</select></label><label>文字<textarea aria-label="新连线文字" value={label} onChange={e => setLabel(e.target.value)} /></label><button type="button" onClick={addEdge}>添加连线</button><button type="button" onClick={cancelConnection} disabled={!from && !to && !label}>取消未提交连线</button></fieldset>
    <ul className="expression-edge-list" aria-label="连线列表">{value.edges.map((edge, i) => <li key={edge.id}><label>连线 {i + 1}<textarea aria-label={`连线文字 ${i + 1}`} value={edge.label} readOnly={locked} onChange={e => { if (expressionTextBytes(e.target.value) > EXPRESSION_LIMITS.labelBytes) { setError("连线文字超出 1024 字节上限。"); return; } emit({ ...value, edges: value.edges.map(item => item.id === edge.id ? { ...item, label: e.target.value } : item) }); }} /></label><button type="button" disabled={locked} aria-label={`删除连线 ${i + 1}`} onClick={() => emit({ ...value, edges: value.edges.filter(item => item.id !== edge.id) })}>删除连线</button></li>)}</ul>
  </section>;
}
