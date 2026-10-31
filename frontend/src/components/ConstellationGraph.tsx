/// <reference types="vite/client" />
import { useEffect, useId, useMemo, useRef, useState, type CSSProperties } from "react";
import noticeUrl from "./neural-creator-NOTICE.txt?url";
import { qualityProfiles, useVisibilityState, type QualityProfile } from "../runtime/performance";
import {
  GRAPH_GROUPS, GRAPH_SIZE, boundViewport, buildAdjacency, curvePoint, edgeCurve, edgeLanes, graphLabel,
  fitViewport, layoutConstellation, seededStars, springStep, stableSeed, zoomViewport,
  type ConstellationEdge, type ConstellationNode, type Curve, type GraphGroupId, type Point, type Spring, type Viewport,
} from "../presentation/neuralGraph";
import "./ConstellationGraph.css";

// The semantic SVG nodes and fixed-version callback remain the existing renderer.
// Upstream visual geometry attribution: ./neural-creator-NOTICE.txt.
export function ConstellationGraph({ nodes, edges, layoutNodes = nodes, centerId, onOpen }: {
  nodes: readonly ConstellationNode[]; edges: readonly ConstellationEdge[];
  layoutNodes?: readonly ConstellationNode[];
  centerId: string | null; onOpen: (id: string) => void;
}) {
  const prefix = "constellation-" + useId().replace(/:/g, "");
  const host = useRef<HTMLDivElement>(null), svg = useRef<SVGSVGElement>(null);
  const nodeElements = useRef(new Map<string, SVGGElement>());
  const pathElements = useRef(new Map<string, SVGPathElement>());
  const labelElements = useRef(new Map<string, SVGTextElement>());
  const particleElements = useRef(new Map<string, SVGCircleElement>());
  const positions = useRef(new Map<string, Point>());
  const sceneTime = useRef(0);
  const documentVisibility = useVisibilityState();
  const [inView, setInView] = useState(true);
  const [reduced, setReduced] = useState(() => typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [quality, setQuality] = useState<QualityProfile>("medium");
  const [paused, setPaused] = useState(false);
  const [focusedGroup, setFocusedGroup] = useState<GraphGroupId | null>(null);
  const [hovered, setHovered] = useState<string | null>(null), [focusedNode, setFocusedNode] = useState<string | null>(null);
  const [viewport, setViewport] = useState<Viewport>({ x: 0, y: 0, scale: 1 });
  const pan = useRef<{ pointer: number; origin: Point; viewport: Viewport } | null>(null);
  const large = nodes.length > 160 || edges.length > 350;
  const effectiveQuality = large ? "low" : quality;
  const visible = documentVisibility === "visible" && inView;
  const animated = visible && !reduced && !paused && effectiveQuality !== "low" && nodes.length > 0;
  // Layout slots use the complete loaded projection, so local filters never move a retained node.
  const layout = useMemo(() => layoutConstellation(layoutNodes, centerId, focusedGroup), [layoutNodes, centerId, focusedGroup]);
  const adjacency = useMemo(() => buildAdjacency(nodes, edges), [nodes, edges]);
  const activeId = hovered ?? focusedNode;
  const highlighted = activeId ? adjacency.get(activeId) : null;
  const drawableEdges = useMemo(() => edges.filter(edge => layout.positions.has(edge.from) && layout.positions.has(edge.to)), [edges, layout]);
  const lanes = useMemo(() => edgeLanes(drawableEdges), [drawableEdges]);
  const allPoints = useMemo(() => {
    const points = [...nodes.map(node => layout.positions.get(node.id)!).filter(Boolean), ...layout.groups.map(group => group.anchor), layout.center];
    for (const edge of drawableEdges) {
      const curve = edgeCurve(layout.positions.get(edge.from)!, layout.positions.get(edge.to)!, lanes.get(edge.id));
      points.push(curve.c1, curve.c2);
    }
    return points;
  }, [layout, nodes, drawableEdges, lanes]);
  const reverse = useMemo(() => new Set(drawableEdges.map(edge => JSON.stringify([edge.from, edge.to]))), [drawableEdges]);
  const particles = useMemo(() => effectiveQuality === "low" ? new Set<string>() : new Set(drawableEdges.slice().sort((a, b) => stableSeed(a.id) - stableSeed(b.id)).slice(0, effectiveQuality === "high" ? 32 : 16).map(edge => edge.id)), [drawableEdges, effectiveQuality]);
  const stars = useMemo(() => seededStars("aaos-neural-sky-v1", effectiveQuality === "low" ? 35 : effectiveQuality === "high" ? 150 : 90), [effectiveQuality]);

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const change = () => setReduced(media.matches); change();
    if (media.addEventListener) { media.addEventListener("change", change); return () => media.removeEventListener("change", change); }
    media.addListener(change); return () => media.removeListener(change);
  }, []);
  useEffect(() => {
    if (!host.current || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(entries => setInView(entries.some(entry => entry.isIntersecting)));
    observer.observe(host.current); return () => observer.disconnect();
  }, []);
  useEffect(() => {
    if (!visible) {
      const pointer = pan.current?.pointer;
      if (pointer !== undefined && svg.current?.hasPointerCapture?.(pointer)) svg.current.releasePointerCapture(pointer);
      pan.current = null;
    }
  }, [visible]);
  // A filter can remove the focused group's items. Clear view focus only, never data.
  useEffect(() => {
    if (focusedGroup && !nodes.some(node => node.id !== centerId && node.group === focusedGroup)) setFocusedGroup(null);
  }, [nodes, centerId, focusedGroup]);

  useEffect(() => {
    const state = new Map<string, { x: Spring; y: Spring }>();
    for (const [id, target] of layout.positions) {
      const old = positions.current.get(id) ?? target;
      state.set(id, { x: { x: old.x, velocity: 0 }, y: { x: old.y, velocity: 0 } });
    }
    const current = new Map<string, Point>();
    const curves = new Map<string, Curve>();
    const applyGeometry = () => {
      for (const [id, point] of current) nodeElements.current.get(id)?.setAttribute("transform", `translate(${point.x} ${point.y})`);
      for (const edge of drawableEdges) {
        const a = current.get(edge.from), b = current.get(edge.to); if (!a || !b) continue;
        const curve = edgeCurve(a, b, lanes.get(edge.id)); curves.set(edge.id, curve);
        pathElements.current.get(edge.id)?.setAttribute("d", curve.path);
        const midpoint = curvePoint(curve, .5), element = labelElements.current.get(edge.id);
        element?.setAttribute("x", String(midpoint.x)); element?.setAttribute("y", String(midpoint.y - 8));
      }
      positions.current = new Map(current);
    };
    // Snap without any continuing frame loop in low/reduced/hidden states.
    for (const [id, target] of layout.positions) current.set(id, animated ? { x: state.get(id)!.x.x, y: state.get(id)!.y.x } : target);
    applyGeometry();
    if (!animated || typeof requestAnimationFrame !== "function") return;
    let frame = 0, previous = performance.now(), drawn = previous, moving = true;
    const interval = 1000 / qualityProfiles[effectiveQuality].maxFPS;
    const step = (now: number) => {
      const elapsed = Math.max(0, Math.min(1 / 30, (now - previous) / 1000)); previous = Math.max(previous, now);
      sceneTime.current += elapsed;
      if (now - drawn >= interval - .5) {
        const seconds = Math.max(0, Math.min(1 / 30, (now - drawn) / 1000)); drawn = now;
        if (moving) {
          moving = false;
          for (const [id, target] of layout.positions) {
            const point = state.get(id)!;
            point.x = springStep(point.x, target.x, seconds); point.y = springStep(point.y, target.y, seconds);
            const settled = Math.abs(point.x.x - target.x) + Math.abs(point.y.x - target.y) + Math.abs(point.x.velocity) + Math.abs(point.y.velocity) < .08;
            current.set(id, settled ? target : { x: point.x.x, y: point.y.x });
            moving ||= !settled;
          }
          applyGeometry();
        }
        for (const id of particles) {
          const curve = curves.get(id), element = particleElements.current.get(id); if (!curve || !element) continue;
          const u = (sceneTime.current * .12 + stableSeed(id) / 4294967296) % 1;
          const point = curvePoint(curve, u);
          element.setAttribute("cx", String(point.x)); element.setAttribute("cy", String(point.y));
          element.setAttribute("opacity", String(Math.sin(u * Math.PI) * .85));
        }
      }
      frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [layout, drawableEdges, lanes, particles, animated, effectiveQuality]);

  function changeViewport(next: Viewport) { setViewport(boundViewport(next, allPoints)); }
  function focusGroup(group: GraphGroupId | null) {
    setFocusedGroup(group); setHovered(null); setFocusedNode(null);
    const nextLayout = layoutConstellation(layoutNodes, centerId, group);
    const points = [...nodes.map(node => nextLayout.positions.get(node.id)!).filter(Boolean), ...nextLayout.groups.map(item => item.anchor)];
    for (const edge of drawableEdges) {
      const a = nextLayout.positions.get(edge.from), b = nextLayout.positions.get(edge.to);
      if (a && b) { const curve = edgeCurve(a, b, lanes.get(edge.id)); points.push(curve.c1, curve.c2); }
    }
    setViewport(boundViewport(fitViewport(points), points));
  }
  function localPoint(event: { clientX: number; clientY: number }): Point {
    const rect = svg.current?.getBoundingClientRect();
    return { x: (event.clientX - (rect?.left ?? 0)) * GRAPH_SIZE.x / (rect?.width || GRAPH_SIZE.x),
      y: (event.clientY - (rect?.top ?? 0)) * GRAPH_SIZE.y / (rect?.height || GRAPH_SIZE.y) };
  }
  const groupCounts = new Map(GRAPH_GROUPS.map(group => [group.id, nodes.filter(node => node.id !== centerId && node.group === group.id).length]));
  return <div ref={host} className="constellation-graph" aria-label="同版本关系图" data-license-notice={noticeUrl} data-animated={animated} data-quality={effectiveQuality} data-focus-group={focusedGroup ?? "all"}>
    <div className="cg-toolbar" role="toolbar" aria-label="关系星图控制">
      <button type="button" aria-label="缩小关系图" disabled={viewport.scale <= .15} onClick={() => changeViewport(zoomViewport(viewport, viewport.scale / 1.2))}>−</button>
      <span aria-label="关系图缩放">{Math.round(viewport.scale * 100)}%</span>
      <button type="button" aria-label="放大关系图" disabled={viewport.scale >= 2.5} onClick={() => changeViewport(zoomViewport(viewport, viewport.scale * 1.2))}>＋</button>
      <button type="button" onClick={() => changeViewport(fitViewport(allPoints))}>适应全部节点</button>
      <button type="button" aria-label="重置关系图视角" onClick={() => changeViewport({ x: 0, y: 0, scale: 1 })}>100%</button>
      <details className="cg-options"><summary>显示与分类</summary><div>
      <button type="button" aria-pressed={!focusedGroup} onClick={() => focusGroup(null)}>全部星团</button>
      {GRAPH_GROUPS.map(group => <button type="button" key={group.id} disabled={!groupCounts.get(group.id)} aria-pressed={focusedGroup === group.id} onClick={() => focusGroup(group.id)}>{group.label}星团 · {groupCounts.get(group.id) ?? 0}</button>)}
      <label>星图显示质量<select value={quality} onChange={event => setQuality(event.target.value as QualityProfile)}><option value="high">完整装饰</option><option value="medium">均衡装饰</option><option value="low">静态装饰</option></select></label>
      <button type="button" disabled={reduced || effectiveQuality === "low"} aria-pressed={paused} onClick={() => setPaused(value => !value)}>{paused ? "继续星图动画" : "暂停星图动画"}</button>
      <p className="cg-help">聚焦星团展开列队；悬停或键盘聚焦查看一跳连接，选择节点打开固定对象。拖动空白平移，聚焦图面后方向键平移、＋/−缩放、Home适应全部。</p>
      </div></details>
    </div>
    {large && <p className="cg-budget" aria-live="polite">当前图包含 {nodes.length} 个节点、{edges.length} 条关系，已降低装饰并停止连续动画；全部节点和关系列表保留。</p>}
    {edges.length !== drawableEdges.length && <p className="cg-budget">{edges.length - drawableEdges.length} 条关系端点未出现在当前投影，未绘制连线；完整关系列表保留。</p>}
    <svg ref={svg} className="cg-viewport" viewBox="0 0 1200 760" tabIndex={0} aria-label="关系星图视口"
      onKeyDown={event => {
        if (event.nativeEvent.isComposing) return;
        if (event.key === "Escape" && focusedGroup) { event.preventDefault(); event.stopPropagation(); focusGroup(null); return; }
        if (event.target !== event.currentTarget) return;
        if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) { event.preventDefault(); changeViewport({ ...viewport, x: viewport.x + (event.key === "ArrowLeft" ? 60 : event.key === "ArrowRight" ? -60 : 0), y: viewport.y + (event.key === "ArrowUp" ? 60 : event.key === "ArrowDown" ? -60 : 0) }); }
        else if (["+", "=", "-"].includes(event.key)) { event.preventDefault(); changeViewport(zoomViewport(viewport, viewport.scale * (event.key === "-" ? 1 / 1.2 : 1.2))); }
        else if (event.key === "Home") { event.preventDefault(); changeViewport(fitViewport(allPoints)); }
      }}
      onPointerDown={event => {
        if (event.button !== 0 || (event.target as Element).closest("[data-graph-node]")) return;
        pan.current = { pointer: event.pointerId, origin: localPoint(event), viewport };
        event.currentTarget.setPointerCapture?.(event.pointerId);
      }}
      onPointerMove={event => {
        const drag = pan.current; if (!drag || drag.pointer !== event.pointerId || !visible) return;
        const point = localPoint(event); changeViewport({ ...drag.viewport, x: drag.viewport.x + point.x - drag.origin.x, y: drag.viewport.y + point.y - drag.origin.y });
      }}
      onPointerUp={event => { pan.current = null; if (event.currentTarget.hasPointerCapture?.(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId); }}
      onPointerCancel={() => { pan.current = null; }} onLostPointerCapture={() => { pan.current = null; }}>
      <defs>
        <radialGradient id={`${prefix}-cloud`}><stop stopColor="var(--ax-accent)" stopOpacity=".17"/><stop offset="1" stopColor="var(--ax-accent)" stopOpacity="0"/></radialGradient>
        <radialGradient id={`${prefix}-core`}><stop stopColor="#fff8dc"/><stop offset=".16" stopColor="#e8c884" stopOpacity=".9"/><stop offset=".42" stopColor="var(--ax-accent)" stopOpacity=".26"/><stop offset="1" stopColor="var(--ax-accent)" stopOpacity="0"/></radialGradient>
        <radialGradient id={`${prefix}-spark`}><stop stopColor="#fff6d5"/><stop offset="1" stopColor="#e8c884" stopOpacity="0"/></radialGradient>
        <marker id={`${prefix}-arrow`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="context-stroke"/></marker>
        <clipPath id={`${prefix}-node-label`}><rect x="-61" y="-19" width="137" height="23"/></clipPath>
      </defs>
      <g aria-hidden="true" pointerEvents="none">
        <ellipse cx="340" cy="310" rx="600" ry="230" fill={`url(#${prefix}-cloud)`} transform="rotate(-22 340 310)"/>
        <ellipse cx="960" cy="400" rx="450" ry="300" fill={`url(#${prefix}-cloud)`}/>
        {stars.map((star, i) => <circle key={i} className="cg-star" cx={star.x} cy={star.y} r={star.radius} opacity={star.opacity} style={{ "--cg-phase": `${-star.phase}s` } as CSSProperties}/>)}
      </g>
      <g data-graph-viewport="" transform={`translate(${viewport.x} ${viewport.y}) scale(${viewport.scale})`}>
        <g aria-hidden="true" pointerEvents="none">
          <circle className="cg-core-glow" cx={layout.center.x} cy={layout.center.y} r="160" fill={`url(#${prefix}-core)`}/>
          {[0, 1, 2].map(i => <ellipse key={i} cx={layout.center.x} cy={layout.center.y} rx={85 + i * 20} ry={24 + i * 9} transform={`rotate(-22 ${layout.center.x} ${layout.center.y})`} className="cg-core-ring"/>)}
          {layout.groups.map(group => <g key={group.id} className={focusedGroup && focusedGroup !== group.id ? "cg-dim-region" : ""}>
            <path d={edgeCurve(layout.center, group.anchor).path} className="cg-region-thread"/>
            <ellipse cx={group.anchor.x} cy={group.anchor.y} rx="165" ry="92" fill={`url(#${prefix}-cloud)`}/>
            <text x={group.anchor.x} y={group.anchor.y - 77} className="cg-group-name" textAnchor="middle">{group.label} · {groupCounts.get(group.id) ?? 0}</text>
          </g>)}
        </g>
        {drawableEdges.map(edge => {
          const curve = edgeCurve(layout.positions.get(edge.from)!, layout.positions.get(edge.to)!, lanes.get(edge.id));
          const midpoint = curvePoint(curve, .5), mutual = edge.from !== edge.to && reverse.has(JSON.stringify([edge.to, edge.from]));
          const lit = !highlighted || (highlighted.has(edge.from) && highlighted.has(edge.to));
          return <g key={edge.id} data-relation-edge={edge.sourceId ?? edge.id} className={`cg-edge ${mutual ? "cg-mutual" : ""} ${lit ? "cg-lit" : "cg-dim"}`}>
            <title>{edge.direction} · {edge.kind} · {edge.label}</title>
            <path ref={element => { if (element) pathElements.current.set(edge.id, element); else pathElements.current.delete(edge.id); }} d={curve.path} fill="none" markerEnd={`url(#${prefix}-arrow)`}/>
            <text ref={element => { if (element) labelElements.current.set(edge.id, element); else labelElements.current.delete(edge.id); }} data-relation-label={edge.sourceId ?? edge.id} x={midpoint.x} y={midpoint.y - 8} textAnchor="middle" className="cg-edge-label"><title>{edge.label || edge.kind}</title>{(edge.label || edge.kind).slice(0, 20)}</text>
            {particles.has(edge.id) && <circle ref={element => { if (element) particleElements.current.set(edge.id, element); else particleElements.current.delete(edge.id); }} className="cg-particle" aria-hidden="true" pointerEvents="none" opacity="0" r="6" cx={midpoint.x} cy={midpoint.y} fill={`url(#${prefix}-spark)`}/>}</g>;
        })}
        {nodes.map(node => {
          const point = layout.positions.get(node.id)!;
          const lit = !highlighted || highlighted.has(node.id), selected = node.id === activeId;
          return <g key={node.id} ref={element => { if (element) nodeElements.current.set(node.id, element); else nodeElements.current.delete(node.id); }}
            data-graph-node={node.id} data-highlighted={selected ? "selected" : lit ? "true" : "false"}
            className={`cg-node ${node.id === centerId ? "cg-center-node" : ""} ${lit ? "cg-lit" : "cg-dim"} ${selected ? "cg-selected" : ""}`}
            transform={`translate(${point.x} ${point.y})`} role="button" aria-label={`图节点 ${node.referenceLabel} · ${node.status}`}
            aria-disabled={node.status !== "resolved"} tabIndex={node.status === "resolved" ? 0 : -1}
            onMouseEnter={() => setHovered(node.id)} onMouseLeave={() => setHovered(null)} onFocus={() => {
              setFocusedNode(node.id);
      const position = positions.current.get(node.id) ?? point;
              const x = position.x * viewport.scale + viewport.x, y = position.y * viewport.scale + viewport.y;
              if (x < 100 || x > 1100 || y < 55 || y > 705) changeViewport({ ...viewport, x: 600 - position.x * viewport.scale, y: 380 - position.y * viewport.scale });
            }} onBlur={() => setFocusedNode(null)}
            onClick={() => node.status === "resolved" && onOpen(node.id)}
            onKeyDown={event => { if ((event.key === "Enter" || event.key === " ") && !event.nativeEvent.isComposing && node.status === "resolved") { event.preventDefault(); event.stopPropagation(); onOpen(node.id); } }}>
            <title>{node.label} · {node.referenceLabel} · {node.status}</title>
            <rect data-relation-node={node.id} x="-86" y="-27" width="172" height="54" rx="12"/>
            <circle className="cg-node-star" cx="-72" cy="-6" r={node.id === centerId ? 4 : 2.8}/>
            <text className="cg-node-name" clipPath={`url(#${prefix}-node-label)`} x="-61" y="-3">{graphLabel(node.label)}</text>
            <text className="cg-node-meta" x="-61" y="15">{node.status === "resolved" ? "固定对象可读" : "目标不可用"}</text>
          </g>;
        })}
      </g>
    </svg>
    {!nodes.length && <p className="cg-empty">此页没有可绘制的节点；扫描范围与关系列表见下方。</p>}
    <p className="cg-legend">实线与箭头表示固定关系，暖色弯线表示实际互向连接；虚线仅表示星团分区。</p>
  </div>;
}
