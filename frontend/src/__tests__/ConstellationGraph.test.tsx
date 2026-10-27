import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { ConstellationGraph } from "../components/ConstellationGraph";
import type { ConstellationNode, ConstellationEdge } from "../presentation/neuralGraph";

const nodes: ConstellationNode[] = [
  { id: "a", label: "中心", referenceLabel: "doc-a · v1", status: "resolved", group: "documents" },
  { id: "b", label: "固定文档", referenceLabel: "doc-b · v3 · block-1", status: "resolved", group: "blocks" },
  { id: "c", label: "原件", referenceLabel: "source-c · sha-c", status: "resolved", group: "sources" },
  { id: "d", label: "未解析", referenceLabel: "doc-d · v2", status: "unavailable", group: "unavailable" },
];
const edges: ConstellationEdge[] = [
  { id: "ab", from: "a", to: "b", label: "证据支持", kind: "supports", direction: "outgoing" },
  { id: "cb", from: "c", to: "b", label: "反链", kind: "related", direction: "backlink" },
];
let reduced = false, serial = 0;
let frames: Map<number, FrameRequestCallback>, mediaListeners: Set<() => void>;
beforeEach(() => {
  reduced = false; serial = 0; frames = new Map(); mediaListeners = new Set();
  vi.spyOn(document, "hidden", "get").mockReturnValue(false);
  vi.stubGlobal("PointerEvent", class extends MouseEvent {
    pointerId: number;
    constructor(type: string, options: PointerEventInit = {}) { super(type, options); this.pointerId = options.pointerId ?? 1; }
  });
  vi.stubGlobal("requestAnimationFrame", vi.fn((callback: FrameRequestCallback) => { const id = ++serial; frames.set(id, callback); return id; }));
  vi.stubGlobal("cancelAnimationFrame", vi.fn((id: number) => { frames.delete(id); }));
  vi.stubGlobal("matchMedia", vi.fn(() => ({ get matches() { return reduced; }, addEventListener: (_: string, callback: () => void) => mediaListeners.add(callback), removeEventListener: (_: string, callback: () => void) => mediaListeners.delete(callback) })));
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it("SIMULATED preserves fixed-object click/Enter/Space callbacks and disables unavailable objects", () => {
  const open = vi.fn(); render(<ConstellationGraph nodes={nodes} edges={edges} centerId="a" onOpen={open}/>);
  const fixed = screen.getByRole("button", { name: "图节点 doc-b · v3 · block-1 · resolved" });
  fireEvent.click(fixed); fireEvent.keyDown(fixed, { key: "Enter" }); fireEvent.keyDown(fixed, { key: " " });
  expect(open.mock.calls).toEqual([["b"], ["b"], ["b"]]);
  const missing = screen.getByRole("button", { name: "图节点 doc-d · v2 · unavailable" });
  expect(missing).toHaveAttribute("aria-disabled", "true"); expect(missing).toHaveAttribute("tabindex", "-1");
  fireEvent.click(missing); fireEvent.keyDown(missing, { key: "Enter" }); expect(open).toHaveBeenCalledTimes(3);
});
it("SIMULATED highlights incoming and outgoing one-hop neighbors for hover and keyboard focus", () => {
  const { container } = render(<ConstellationGraph nodes={nodes} edges={edges} centerId="a" onOpen={() => {}}/>);
  const b = screen.getByRole("button", { name: /图节点 doc-b/ }); fireEvent.mouseEnter(b);
  expect(container.querySelector('[data-graph-node="a"]')).toHaveAttribute("data-highlighted", "true");
  expect(container.querySelector('[data-graph-node="c"]')).toHaveAttribute("data-highlighted", "true");
  expect(container.querySelector('[data-graph-node="d"]')).toHaveAttribute("data-highlighted", "false");
  fireEvent.mouseLeave(b); fireEvent.focus(screen.getByRole("button", { name: /图节点 source-c/ }));
  expect(container.querySelector('[data-graph-node="b"]')).toHaveAttribute("data-highlighted", "true");
  expect(container.querySelector('[data-graph-node="a"]')).toHaveAttribute("data-highlighted", "false");
});
it("SIMULATED keeps cluster focus separate from opening and Escape returns from a focused node", () => {
  const open = vi.fn(), { container } = render(<ConstellationGraph nodes={nodes} edges={edges} centerId="a" onOpen={open}/>);
  fireEvent.click(screen.getByText("显示与分类",{selector:"summary"}));
  expect(screen.getByRole("button", { name: /^知识星团/ })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: /^段落星团/ }));
  expect(container.firstChild).toHaveAttribute("data-focus-group", "blocks"); expect(open).not.toHaveBeenCalled();
  fireEvent.keyDown(screen.getByRole("button", { name: /图节点 doc-b/ }), { key: "Escape" });
  expect(container.firstChild).toHaveAttribute("data-focus-group", "all"); expect(open).not.toHaveBeenCalled();
});
it("SIMULATED zoom/pan/fit update view state without opening or changing graph data", () => {
  const open = vi.fn(), { container } = render(<ConstellationGraph nodes={nodes} edges={edges} centerId="a" onOpen={open}/>);
  const before = JSON.stringify({ nodes, edges });
  fireEvent.click(screen.getByRole("button", { name: "放大关系图" })); expect(screen.getByLabelText("关系图缩放")).toHaveTextContent("120%");
  const world = container.querySelector("[data-graph-viewport]")!, previous = world.getAttribute("transform");
  fireEvent.keyDown(screen.getByLabelText("关系星图视口"), { key: "ArrowRight" }); expect(world.getAttribute("transform")).not.toBe(previous);
  const graph = screen.getByLabelText("关系星图视口"), beforeDrag = world.getAttribute("transform");
  fireEvent.pointerDown(graph, { pointerId: 7, button: 0, clientX: 10, clientY: 10 });
  fireEvent.pointerMove(graph, { pointerId: 7, clientX: 100, clientY: 60 }); fireEvent.pointerUp(graph, { pointerId: 7 });
  expect(world.getAttribute("transform")).not.toBe(beforeDrag);
  fireEvent.click(screen.getByRole("button", { name: "适应全部节点" }));
  expect(JSON.stringify({ nodes, edges })).toBe(before); expect(open).not.toHaveBeenCalled();
});
it("SIMULATED brings keyboard-focused offscreen nodes back into the viewport", () => {
  const view = render(<ConstellationGraph nodes={nodes} edges={edges} centerId="a" onOpen={() => {}}/>);
  const graph = screen.getByLabelText("关系星图视口"), world = view.container.querySelector("[data-graph-viewport]")!;
  for (let i = 0; i < 30; i++) fireEvent.keyDown(graph, { key: "ArrowLeft" });
  const offscreen = world.getAttribute("transform");
  fireEvent.focus(screen.getByRole("button", { name: /图节点 doc-b/ }));
  expect(world.getAttribute("transform")).not.toBe(offscreen);
});
it("SIMULATED retains full-projection slots when filters or input ordering change", () => {
  reduced = true;
  const view = render(<ConstellationGraph nodes={nodes} layoutNodes={nodes} edges={edges} centerId="a" onOpen={() => {}}/>);
  const position = view.container.querySelector('[data-graph-node="b"]')!.getAttribute("transform");
  view.rerender(<ConstellationGraph nodes={[nodes[1], nodes[0]]} layoutNodes={nodes.slice().reverse()} edges={[edges[0]]} centerId="a" onOpen={() => {}}/>);
  expect(view.container.querySelector('[data-graph-node="b"]')).toHaveAttribute("transform", position!);
  expect(view.container.querySelectorAll("[data-relation-node]")).toHaveLength(2);
});
it("SIMULATED stops frame loops for live reduced-motion, low quality, hidden documents and unmount", () => {
  const view = render(<ConstellationGraph nodes={nodes} edges={edges} centerId="a" onOpen={() => {}}/>);
  expect(frames.size).toBe(1);
  act(() => { reduced = true; mediaListeners.forEach(change => change()); }); expect(frames.size).toBe(0); expect(view.container.firstChild).toHaveAttribute("data-animated", "false");
  act(() => { reduced = false; mediaListeners.forEach(change => change()); }); expect(frames.size).toBe(1);
  fireEvent.change(screen.getByLabelText("星图显示质量"), { target: { value: "low" } }); expect(frames.size).toBe(0);
  fireEvent.change(screen.getByLabelText("星图显示质量"), { target: { value: "medium" } }); expect(frames.size).toBe(1);
  vi.spyOn(document, "hidden", "get").mockReturnValue(true); fireEvent(document, new Event("visibilitychange")); expect(frames.size).toBe(0);
  view.unmount(); expect(frames.size).toBe(0); expect(mediaListeners.size).toBe(0);
});
it("SIMULATED preserves 1000 edges and every node while reducing decoration", () => {
  const many = Array.from({ length: 1000 }, (_, i) => ({ ...edges[0], id: `edge-${i}` }));
  const { container } = render(<ConstellationGraph nodes={nodes} edges={many} centerId="a" onOpen={() => {}}/>);
  expect(container.querySelectorAll("[data-relation-edge]")).toHaveLength(1000);
  expect(container.querySelectorAll("[data-relation-node]")).toHaveLength(4);
  expect(screen.getByText(/当前图包含 4 个节点、1000 条关系/)).toHaveTextContent("全部节点和关系列表保留");
  expect(frames.size).toBe(0);
});
it("SIMULATED handles empty graphs and exposes missing endpoint scope without inventing nodes", () => {
  const { container } = render(<ConstellationGraph nodes={[]} edges={edges} centerId={null} onOpen={() => {}}/>);
  expect(container.querySelectorAll("[data-relation-node]")).toHaveLength(0); expect(container.querySelectorAll("[data-relation-edge]")).toHaveLength(0);
  expect(screen.getByText(/2 条关系端点未出现在当前投影/)).toBeVisible(); expect(screen.getByText(/此页没有可绘制的节点/)).toBeVisible(); expect(frames.size).toBe(0);
});
