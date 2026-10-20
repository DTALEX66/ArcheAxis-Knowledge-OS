/** Adapted interaction geometry from neural-creator-dashboard, MIT.
 * Source and full permission notice: ../components/neural-creator-NOTICE.txt.
 * Presentation only: no inferred knowledge links or persisted coordinates.
 */
export type Point = { x: number; y: number };
export type Viewport = Point & { scale: number };
export type GraphGroupId = "documents" | "blocks" | "sources" | "knowledge" | "unavailable";
export type ConstellationNode = {
  id: string; label: string; referenceLabel: string;
  status: "resolved" | "unavailable"; group: GraphGroupId;
};
export type ConstellationEdge = {
  id: string; from: string; to: string; label: string; kind: string;
  direction: "outgoing" | "backlink"; sourceId?: string;
};
export const GRAPH_SIZE = { x: 1200, y: 760 };
export const GRAPH_GROUPS: ReadonlyArray<{ id: GraphGroupId; label: string }> = [
  { id: "documents", label: "文档" }, { id: "blocks", label: "段落" },
  { id: "sources", label: "来源" }, { id: "knowledge", label: "知识" },
  { id: "unavailable", label: "待解析" },
];
export const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));
/** 保守估算标题宽度；SVG 裁剪另作硬边界，完整标题保留在可访问名称中。 */
export function graphLabel(label: string, budget = 10): string {
  const characters = Array.from(label);
  const weight = (c: string) => /^[\x20-\x7e]$/.test(c) ? .65 : 1;
  if (characters.reduce((sum, c) => sum + weight(c), 0) <= budget) return label;
  let text = "", used = 0;
  for (const c of characters) {
    if (used + weight(c) > budget - 1) break;
    text += c; used += weight(c);
  }
  return text + "…";
}
export function stableSeed(id: string): number {
  let value = 2166136261;
  for (let i = 0; i < id.length; i++) value = Math.imul(value ^ id.charCodeAt(i), 16777619);
  return value >>> 0;
}
export function seededStars(seed: string, count: number, width = GRAPH_SIZE.x, height = GRAPH_SIZE.y) {
  let state = stableSeed(seed);
  const next = () => { state = (Math.imul(state, 1664525) + 1013904223) >>> 0; return state / 4294967296; };
  return Array.from({ length: clamp(Math.floor(count), 0, 180) }, () => ({
    x: next() * width, y: next() * height, radius: .5 + next() ** 4 * 1.7,
    opacity: .15 + next() * .6, phase: next() * Math.PI * 2,
  }));
}
export function buildAdjacency(nodes: readonly ConstellationNode[], edges: readonly ConstellationEdge[]) {
  const result = new Map(nodes.map(node => [node.id, new Set<string>([node.id])]));
  for (const edge of edges) {
    if (!result.has(edge.from) || !result.has(edge.to)) continue;
    result.get(edge.from)!.add(edge.to); result.get(edge.to)!.add(edge.from);
  }
  return result;
}
export function layoutConstellation(nodes: readonly ConstellationNode[], centerId: string | null, focus: GraphGroupId | null) {
  const positions = new Map<string, Point>();
  const center = focus ? { x: 110, y: 380 } : { x: 600, y: 380 };
  let contextY = 96;
  const groups = GRAPH_GROUPS.map((group, index) => {
    const angle = -Math.PI / 2 + index * Math.PI * 2 / GRAPH_GROUPS.length;
    const items = nodes.filter(node => node.id !== centerId && node.group === group.id)
      .slice().sort((a, b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
    const anchor = focus ? { x: 290, y: contextY } : {
      x: center.x + Math.cos(angle) * 405, y: center.y + Math.sin(angle) * 255,
    };
    // 聚焦后将其他对象排入独立上下文列；环形抖动会让卡片相互遮挡。
    if (focus) contextY += Math.max(136, focus === group.id ? 0 : items.length * 64 + 48);
    const fanRows = Math.max(8, Math.ceil(Math.sqrt(items.length * 230 / 76)));
    items.forEach((node, i) => {
      if (focus === group.id) {
        // Balance long fans into a readable grid; never truncate or make a 28k-wide strip.
        positions.set(node.id, { x: 580 + Math.floor(i / fanRows) * 230, y: 120 + (i % fanRows) * 76 });
      } else if (focus) {
        positions.set(node.id, { x: anchor.x, y: anchor.y + i * 64 });
      } else {
        const a = i * 2.399963229728653 + stableSeed(group.id) / 4294967296 * Math.PI * 2;
        const r = Math.sqrt(i + 1) * (focus ? 42 : items.length > 160 ? 64 : 76);
        positions.set(node.id, { x: anchor.x + Math.cos(a) * r * 1.5, y: anchor.y + Math.sin(a) * r });
      }
    });
    return { ...group, anchor, count: items.length };
  });
  if (centerId && nodes.some(node => node.id === centerId)) positions.set(centerId, center);
  return { positions, center, groups };
}
export type Curve = { a: Point; c1: Point; c2: Point; b: Point; path: string };
export function edgeCurve(a: Point, b: Point, lane = 0): Curve {
  const dx = b.x - a.x, dy = b.y - a.y, length = Math.hypot(dx, dy) || 1;
  const bend = 24 + lane * 35;
  const self = a.x === b.x && a.y === b.y;
  const c1 = self ? { x: a.x + 135 + lane * 8, y: a.y - 135 - lane * 6 } : { x: a.x + dx * .4 - dy / length * bend, y: a.y + dy * .4 + dx / length * bend };
  const c2 = self ? { x: a.x - 135 - lane * 8, y: a.y - 135 - lane * 6 } : { x: a.x + dx * .7 - dy / length * bend, y: a.y + dy * .7 + dx / length * bend };
  return { a, c1, c2, b, path: `M ${a.x} ${a.y} C ${c1.x} ${c1.y} ${c2.x} ${c2.y} ${b.x} ${b.y}` };
}
export function curvePoint(curve: Curve, u: number): Point {
  const t = clamp(u, 0, 1), m = 1 - t, { a, c1, c2, b } = curve;
  return { x: m ** 3 * a.x + 3 * m * m * t * c1.x + 3 * m * t * t * c2.x + t ** 3 * b.x,
    y: m ** 3 * a.y + 3 * m * m * t * c1.y + 3 * m * t * t * c2.y + t ** 3 * b.y };
}
export function edgeLanes(edges: readonly ConstellationEdge[]) {
  const pairs = new Map<string, ConstellationEdge[]>();
  for (const edge of edges) {
    const pair = JSON.stringify([edge.from, edge.to].sort());
    const items = pairs.get(pair) ?? []; items.push(edge); pairs.set(pair, items);
  }
  const result = new Map<string, number>();
  for (const items of pairs.values()) {
    items.sort((a, b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
    items.forEach((edge, i) => {
      // Canonical orientation prevents reciprocal paths collapsing onto each other.
      const sign = edge.from <= edge.to ? 1 : -1;
      // Dense parallel edges get distinct, bounded lanes, not a 26k-pixel bow.
      const middle = (items.length - 1) / 2;
      result.set(edge.id, ((i - middle) / Math.max(middle, 1) * 2.5 + .35) * sign);
    });
  }
  return result;
}
export type Spring = { x: number; velocity: number };
export function springStep(state: Spring, target: number, elapsed: number, stiffness = 62): Spring {
  const dt = clamp(Number.isFinite(elapsed) ? elapsed : 0, 0, 1 / 30);
  const velocity = state.velocity + (-stiffness * (state.x - target) - 2 * Math.sqrt(stiffness) * state.velocity) * dt;
  return { x: state.x + velocity * dt, velocity };
}
export function screenToWorld(point: Point, viewport: Viewport): Point {
  const scale = clamp(viewport.scale, .15, 2.5);
  return { x: (point.x - viewport.x) / scale, y: (point.y - viewport.y) / scale };
}
export function zoomViewport(viewport: Viewport, scale: number, anchor = { x: 600, y: 380 }): Viewport {
  const next = clamp(scale, .15, 2.5), ratio = next / viewport.scale;
  return { x: anchor.x - (anchor.x - viewport.x) * ratio, y: anchor.y - (anchor.y - viewport.y) * ratio, scale: next };
}
export function fitViewport(points: readonly Point[]): Viewport {
  if (!points.length) return { x: 0, y: 0, scale: 1 };
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const p of points) { minX = Math.min(minX, p.x - 100); maxX = Math.max(maxX, p.x + 100); minY = Math.min(minY, p.y - 65); maxY = Math.max(maxY, p.y + 65); }
  const scale = clamp(Math.min(1120 / Math.max(maxX - minX, 1), 680 / Math.max(maxY - minY, 1), 1), .15, 2.5);
  return { x: 600 - (minX + maxX) / 2 * scale, y: 380 - (minY + maxY) / 2 * scale, scale };
}
export function boundViewport(viewport: Viewport, points: readonly Point[]): Viewport {
  const scale = clamp(viewport.scale, .15, 2.5);
  let extentX = GRAPH_SIZE.x, extentY = GRAPH_SIZE.y;
  for (const point of points) { extentX = Math.max(extentX, Math.abs(point.x) + 150); extentY = Math.max(extentY, Math.abs(point.y) + 150); }
  return { x: clamp(viewport.x, -extentX * scale - 1200, extentX * scale + 1200),
    y: clamp(viewport.y, -extentY * scale - 760, extentY * scale + 760), scale };
}
