import { describe, expect, it } from "vitest";
import { boundViewport, buildAdjacency, curvePoint, edgeCurve, edgeLanes, fitViewport, graphLabel, layoutConstellation, screenToWorld, seededStars, springStep, stableSeed, zoomViewport,
  type ConstellationNode, type ConstellationEdge } from "../presentation/neuralGraph";

const node = (id: string): ConstellationNode => ({ id, label: id, referenceLabel: `${id} · v3`, status: "resolved", group: "documents" });
const edge = (id: string, from: string, to: string): ConstellationEdge => ({ id, from, to, label: "支持", kind: "supports", direction: "outgoing" });

describe("constellation presentation geometry", () => {
  it("bounds Chinese and mixed-width labels without splitting surrogate pairs", () => {
    expect(graphLabel("中文短标题")).toBe("中文短标题");
    expect(graphLabel("这是一个超长中文标题必须保持在卡片内部")).toBe("这是一个超长中文标…");
    expect(graphLabel("abcdefghijklmno")).toBe("abcdefghijklmno");
    expect(graphLabel("😀".repeat(20))).toBe("😀".repeat(9) + "…");
  });
  it("handles zero and one fixed-identity node without NaN or invented nodes", () => {
    expect(layoutConstellation([], null, null).positions.size).toBe(0);
    expect(layoutConstellation([node("only")], "only", null).positions.get("only")).toEqual({ x: 600, y: 380 });
    expect(fitViewport([])).toEqual({ x: 0, y: 0, scale: 1 });
  });
  it("keeps expanded cluster context cards apart from each other and the center", () => {
    const nodes: ConstellationNode[] = [node("center"), ...Array.from({ length: 20 }, (_, i) => ({ ...node(`context-${i}`), group: i < 10 ? "documents" as const : "sources" as const })), { ...node("focus"), group: "knowledge" }];
    const points = [...layoutConstellation(nodes, "center", "knowledge").positions.values()];
    for (let i = 0; i < points.length; i++) for (let j = i + 1; j < points.length; j++) {
      expect(Math.abs(points[i].x - points[j].x) >= 180 || Math.abs(points[i].y - points[j].y) >= 62).toBe(true);
    }
  });
  it("uses stable IDs rather than input order or mutable titles for slots and star seeds", () => {
    const nodes = [node("center"), node("z"), node("a"), node("b")];
    const first = layoutConstellation(nodes, "center", null);
    const second = layoutConstellation(nodes.slice().reverse().map(n => ({ ...n, label: "新标题" })), "center", null);
    expect(Object.fromEntries(second.positions)).toEqual(Object.fromEntries(first.positions));
    expect(seededStars("same-snapshot", 10)).toEqual(seededStars("same-snapshot", 10));
    expect(stableSeed("doc-a:v3:block-b")).not.toBe(stableSeed("doc-a:v4:block-b"));
  });
  it("keeps a 1000-item fan complete, balanced and inside the fitted viewport", () => {
    const nodes = Array.from({ length: 1000 }, (_, i) => node(`node-${String(i).padStart(4, "0")}`));
    const result = layoutConstellation(nodes, null, "documents");
    expect(result.positions.size).toBe(1000);
    const viewport = fitViewport([...result.positions.values()]);
    for (const p of result.positions.values()) {
      expect(Number.isFinite(p.x) && Number.isFinite(p.y)).toBe(true);
      expect((p.x - 86) * viewport.scale + viewport.x).toBeGreaterThanOrEqual(0);
      expect((p.x + 86) * viewport.scale + viewport.x).toBeLessThanOrEqual(1200);
      expect((p.y - 27) * viewport.scale + viewport.y).toBeGreaterThanOrEqual(0);
      expect((p.y + 27) * viewport.scale + viewport.y).toBeLessThanOrEqual(760);
    }
  });
  it("indexes both incoming and outgoing neighbors but does not synthesize missing endpoints", () => {
    const adjacent = buildAdjacency([node("a"), node("b"), node("c")], [edge("ab", "a", "b"), edge("cb", "c", "b"), edge("missing", "a", "absent")]);
    expect([...adjacent.get("b")!].sort()).toEqual(["a", "b", "c"]);
    expect([...adjacent.get("a")!].sort()).toEqual(["a", "b"]);
    expect(adjacent.has("absent")).toBe(false);
  });
  it("routes reciprocal and parallel edges by stable provenance keys and preserves endpoints", () => {
    const edges = [edge("a", "a", "b"), edge("b", "b", "a"), edge("c", "a", "b")];
    expect(Object.fromEntries(edgeLanes(edges))).toEqual(Object.fromEntries(edgeLanes(edges.slice().reverse())));
    const curve = edgeCurve({ x: 10, y: 20 }, { x: 200, y: 100 }, 2);
    expect(curvePoint(curve, 0)).toEqual({ x: 10, y: 20 });
    expect(curvePoint(curve, 1)).toEqual({ x: 200, y: 100 });
    const self = edgeCurve({ x: 10, y: 20 }, { x: 10, y: 20 });
    expect(self.path).not.toMatch(/NaN|Infinity/);
    expect(curvePoint(self, .5).y).toBeLessThan(20);
  });
  it("bounds 1000 parallel/reciprocal paths and distinct self-loops inside a fitted geometry envelope", () => {
    const parallels = Array.from({ length: 1000 }, (_, i) => edge(`edge-${i}`, i % 2 ? "b" : "a", i % 2 ? "a" : "b"));
    const loops = Array.from({ length: 20 }, (_, i) => edge(`self-${i}`, "a", "a"));
    const lanes = edgeLanes([...parallels, ...loops]);
    const positions = new Map([["a", { x: 200, y: 300 }], ["b", { x: 900, y: 500 }]]);
    const curves = [...parallels, ...loops].map(e => edgeCurve(positions.get(e.from)!, positions.get(e.to)!, lanes.get(e.id)));
    expect(new Set(curves.map(c => c.path)).size).toBe(1020);
    expect([...lanes.values()].every(lane => Math.abs(lane) <= 3)).toBe(true);
    const viewport = fitViewport(curves.flatMap(c => [c.a, c.c1, c.c2, c.b]));
    for (const curve of curves) for (const t of [0, .25, .5, .75, 1]) {
      const point = curvePoint(curve, t);
      expect(Math.abs(point.x)).toBeLessThan(1200); expect(Math.abs(point.y)).toBeLessThan(900);
      expect(point.x * viewport.scale + viewport.x).toBeGreaterThanOrEqual(0);
      expect(point.x * viewport.scale + viewport.x).toBeLessThanOrEqual(1200);
      expect(point.y * viewport.scale + viewport.y).toBeGreaterThanOrEqual(0);
      expect(point.y * viewport.scale + viewport.y).toBeLessThanOrEqual(760);
    }
  });
  it("clamps negative elapsed time and converges the damped spring without runaway", () => {
    expect(springStep({ x: 10, velocity: 0 }, 100, -1)).toEqual({ x: 10, velocity: 0 });
    let spring = { x: 0, velocity: 0 };
    for (let i = 0; i < 250; i++) spring = springStep(spring, 100, 1 / 30);
    expect(spring.x).toBeCloseTo(100, 4);
    expect(spring.velocity).toBeCloseTo(0, 4);
  });
  it("keeps the zoom anchor fixed in world coordinates and bounds navigation", () => {
    const viewport = { x: 40, y: -10, scale: .8 }, anchor = { x: 250, y: 200 };
    const next = zoomViewport(viewport, 2, anchor);
    expect(screenToWorld(anchor, next)).toEqual(screenToWorld(anchor, viewport));
    const bounded = boundViewport({ x: 1e9, y: -1e9, scale: 100 }, [{ x: 300, y: 200 }]);
    expect(bounded.scale).toBe(2.5); expect(Math.abs(bounded.x)).toBeLessThan(10000); expect(Math.abs(bounded.y)).toBeLessThan(10000);
  });
});
