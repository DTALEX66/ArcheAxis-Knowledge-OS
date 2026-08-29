import { useCallback, useRef, useState } from "react";

interface CanvasNode {
  id: string;
  type: string;
  x: number;
  y: number;
  width: number;
  height: number;
  text?: string;
  file?: string;
  url?: string;
}

interface CanvasEdge {
  id: string;
  fromNode: string;
  toNode: string;
}

export function CanvasBoard({ doc, onChange }: { doc: Record<string, unknown>; onChange: (next: Record<string, unknown>) => void }) {
  const nodes: CanvasNode[] = Array.isArray(doc.nodes) ? (doc.nodes as CanvasNode[]) : [];
  const edges: CanvasEdge[] = Array.isArray(doc.edges) ? (doc.edges as CanvasEdge[]) : [];
  const [dragging, setDragging] = useState<{ nodeId: string; offsetX: number; offsetY: number } | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  const updateNodes = useCallback((updater: (prev: CanvasNode[]) => CanvasNode[]) => {
    onChange({ ...doc, nodes: updater(nodes), edges });
  }, [doc, nodes, edges, onChange]);

  const handlePointerDown = useCallback((e: React.PointerEvent, nodeId: string) => {
    if ((e.target as HTMLElement).closest("button, input, textarea")) return;
    const node = nodes.find((n) => n.id === nodeId);
    if (!node) return;
    setDragging({ nodeId, offsetX: e.clientX - node.x, offsetY: e.clientY - node.y });
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  }, [nodes]);

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!dragging) return;
    const newX = Math.max(0, Math.round((e.clientX - dragging.offsetX) / 10) * 10);
    const newY = Math.max(0, Math.round((e.clientY - dragging.offsetY) / 10) * 10);
    updateNodes((prev) => prev.map((n) => n.id === dragging.nodeId ? { ...n, x: newX, y: newY } : n));
  }, [dragging, updateNodes]);

  const handlePointerUp = useCallback(() => {
    setDragging(null);
  }, []);

  function addTextNode() {
    const text = window.prompt("新文本节点内容");
    if (text === null) return;
    const id = `node-${Date.now().toString(36)}`;
    updateNodes((prev) => [...prev, { id, type: "text", x: 20, y: 20 + prev.length * 80, width: 240, height: 60, text }]);
  }

  function removeNode(id: string) {
    onChange({
      ...doc,
      nodes: nodes.filter((n) => n.id !== id),
      edges: edges.filter((e) => e.fromNode !== id && e.toNode !== id),
    });
  }

  function startEdit(node: CanvasNode) {
    setEditingId(node.id);
    setEditText(node.text ?? "");
  }

  function commitEdit() {
    if (!editingId) return;
    updateNodes((prev) => prev.map((n) => n.id === editingId ? { ...n, text: editText } : n));
    setEditingId(null);
    setEditText("");
  }

  const canvasWidth = Math.max(800, ...nodes.map((n) => n.x + n.width + 40));
  const canvasHeight = Math.max(500, ...nodes.map((n) => n.y + n.height + 40));

  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  return (
    <div className="canvas-board" aria-label="画布内容">
      <div className="canvas-toolbar">
        <button type="button" onClick={addTextNode}>添加文本节点</button>
        <span className="muted">拖拽移动 · 网格 10px · 节点 {nodes.length} · 连线 {edges.length}</span>
      </div>
      <div
        ref={containerRef}
        className="canvas-viewport"
        style={{ position: "relative", width: canvasWidth, height: canvasHeight, overflow: "auto", border: "1px solid var(--ax-border)", borderRadius: 12, background: "var(--ax-bg-inset)" }}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
      >
        <svg style={{ position: "absolute", top: 0, left: 0, width: canvasWidth, height: canvasHeight, pointerEvents: "none" }}>
          {edges.map((edge) => {
            const from = nodeMap.get(edge.fromNode);
            const to = nodeMap.get(edge.toNode);
            if (!from || !to) return null;
            return (
              <line
                key={edge.id}
                x1={from.x + from.width / 2}
                y1={from.y + from.height / 2}
                x2={to.x + to.width / 2}
                y2={to.y + to.height / 2}
                stroke="var(--ax-border)"
                strokeWidth={2}
              />
            );
          })}
        </svg>
        {nodes.map((node) => (
          <div
            key={node.id}
            className="canvas-node-card"
            style={{ position: "absolute", left: node.x, top: node.y, width: node.width, minHeight: node.height, zIndex: dragging?.nodeId === node.id ? 10 : 1 }}
            onPointerDown={(e) => handlePointerDown(e, node.id)}
          >
            <div className="canvas-node-header">
              <span className="canvas-node-type">{node.type}</span>
              <div className="canvas-node-actions">
                <button type="button" aria-label={`编辑 ${node.text ?? node.id}`} onClick={() => startEdit(node)}>✏</button>
                <button type="button" aria-label={`删除 ${node.text ?? node.id}`} onClick={() => removeNode(node.id)}>×</button>
              </div>
            </div>
            {editingId === node.id ? (
              <textarea
                className="canvas-node-edit"
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                onBlur={commitEdit}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); commitEdit(); } }}
                autoFocus
              />
            ) : (
              <div className="canvas-node-text">{node.text ?? node.file ?? node.url ?? "节点"}</div>
            )}
          </div>
        ))}
      </div>
      {nodes.length === 0 ? <p className="muted">空画布。添加文本节点开始绘制。</p> : null}
    </div>
  );
}
