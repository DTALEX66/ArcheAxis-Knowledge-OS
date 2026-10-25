import { createContext, useContext, useEffect, useRef, useState, type KeyboardEvent, type PointerEvent, type ReactNode } from "react";
import "./ConsoleWindow.css";

export type ConsoleRect = { x: number; y: number; width: number; height: number };
export type ConsoleViewport = { width: number; height: number; topInset?: number; bottomInset?: number };
type ResizeEdge = "n" | "ne" | "e" | "se" | "s" | "sw" | "w" | "nw";
const additionalEdges: readonly ResizeEdge[] = ["n", "ne", "e", "s", "sw", "w", "nw"];
function resizeConsole(rect: ConsoleRect, viewport: ConsoleViewport, edge: ResizeEdge, dx: number, dy: number): ConsoleRect {
  const right = rect.x + rect.width, bottom = rect.y + rect.height;
  const top = viewport.topInset ?? 0, bottomLimit = viewport.height - (viewport.bottomInset ?? 0);
  const floorWidth = Math.min(640, viewport.width), floorHeight = Math.min(480, bottomLimit - top);
  const x = edge.includes("w") ? Math.max(0, Math.min(rect.x + dx, right - floorWidth)) : rect.x;
  const y = edge.includes("n") ? Math.max(top, Math.min(rect.y + dy, bottom - floorHeight)) : rect.y;
  const endX = edge.includes("e") ? Math.min(viewport.width, Math.max(right + dx, x + floorWidth)) : right;
  const endY = edge.includes("s") ? Math.min(bottomLimit, Math.max(bottom + dy, y + floorHeight)) : bottom;
  return { x, y, width: endX - x, height: endY - y };
}
export function constrainConsole(rect: ConsoleRect, viewport: ConsoleViewport): ConsoleRect {
  const width = Math.min(viewport.width, Math.max(640, rect.width));
  const top = viewport.topInset ?? 0, bottomLimit = viewport.height - (viewport.bottomInset ?? 0);
  const height = Math.min(bottomLimit - top, Math.max(480, rect.height));
  return { width, height, x: Math.max(0, Math.min(rect.x, viewport.width - width)), y: Math.max(top, Math.min(rect.y, bottomLimit - height)) };
}
export function defaultConsoleRect(viewport: ConsoleViewport): ConsoleRect {
  const size = constrainConsole({ x: 0, y: 0, width: Math.round(viewport.width * .9), height: Math.min(Math.round(viewport.height * .84), viewport.height - 128) }, viewport);
  return { ...size, x: Math.round((viewport.width - size.width) / 2), y: Math.max(0, Math.min(viewport.height - size.height, Math.max(48, Math.round((viewport.height - size.height) / 2) - 8))) };
}
/** Preserve the received main/auxiliary proportions as the desktop grows. */
export function stitchConsoleRect(viewport: ConsoleViewport): ConsoleRect {
  if (viewport.width < 1280 || viewport.height < 700) return defaultConsoleRect(viewport);
  const width = viewport.width * .64;
  const auxiliaryWidth = viewport.width * .29;
  const top = viewport.topInset ?? 48, bottom = viewport.bottomInset ?? 64;
  const height = viewport.height - top - bottom;
  return { x: (viewport.width - width - auxiliaryWidth - 20) / 2, y: top + (viewport.height - top - bottom - height) / 2, width, height };
}
const readViewport = (): ConsoleViewport => ({ width: window.innerWidth, height: window.innerHeight, ...(window.innerWidth > 900 && window.innerHeight > 600 ? { topInset: 48, bottomInset: 64 } : {}) });
type ConsoleControls = {
  mode: "floating" | "full" | "compact";
  toggle: () => void;
  reset: () => void;
  begin: (event: PointerEvent<HTMLElement>, kind: "move" | "resize", edge?: ResizeEdge) => void;
  move: (event: PointerEvent<HTMLElement>) => void;
  end: (event: PointerEvent<HTMLElement>) => void;
  cancel: () => void;
  keys: (event: KeyboardEvent<HTMLElement>) => void;
};
const ConsoleContext = createContext<ConsoleControls | null>(null);
export const useConsoleWindow = () => useContext(ConsoleContext);

/** One session-only console. Geometry never changes the mounted workspace or its data. */
export function ConsoleWindow({ children, presentation = "default" }: { children: ReactNode; presentation?: "default" | "stitch" }) {
  const initialRect = presentation === "stitch" ? stitchConsoleRect : defaultConsoleRect;
  const [viewport, setViewport] = useState(readViewport);
  const [rect, setRect] = useState(() => initialRect(readViewport()));
  const [full, setFull] = useState(false);
  const customized = useRef(false);
  const gesture = useRef<{ id: number; x: number; y: number; rect: ConsoleRect; customized: boolean; kind: "move" | "resize"; edge: ResizeEdge } | null>(null);
  const compact = viewport.width <= 900 || viewport.height <= 600;
  const mode = compact ? "compact" : full ? "full" : "floating";
  const expandedWidth = presentation === "stitch" && viewport.width >= 1280 && viewport.height >= 700 ? viewport.width * .71 - 36 : viewport.width;
  const shown = mode === "floating" ? constrainConsole(rect, viewport) : { x: 0, y: 0, width: expandedWidth, height: viewport.height };
  useEffect(() => {
    const resize = () => {
      gesture.current = null;
      const next = readViewport();
      setViewport(next);
      if (presentation === "stitch" && !customized.current) setRect(stitchConsoleRect(next));
    };
    const escape = (event: globalThis.KeyboardEvent) => {
      if (event.key !== "Escape" || !gesture.current) return;
      event.preventDefault(); event.stopPropagation();
      setRect(gesture.current.rect); customized.current = gesture.current.customized; gesture.current = null;
    };
    window.addEventListener("resize", resize);
    window.addEventListener("keydown", escape, true);
    return () => { window.removeEventListener("resize", resize); window.removeEventListener("keydown", escape, true); };
  }, [presentation]);
  const cancel = () => { if (gesture.current) { setRect(gesture.current.rect); customized.current = gesture.current.customized; } gesture.current = null; };
  const controls: ConsoleControls = {
    mode,
    toggle: () => { gesture.current = null; if (!compact) setFull(value => !value); },
    reset: () => { gesture.current = null; customized.current = false; setRect(initialRect(viewport)); setFull(false); },
    begin: (event, kind, edge = "se") => {
      if (mode !== "floating" || event.button !== 0) return;
      if (kind === "move" && (event.target as Element).closest("button:not(.console-move-handle),a,input,select,textarea,[contenteditable='true']")) return;
      event.preventDefault();
      gesture.current = { id: event.pointerId, x: event.clientX, y: event.clientY, rect: shown, customized: customized.current, kind, edge };
      event.currentTarget.setPointerCapture?.(event.pointerId);
    },
    move: event => {
      const start = gesture.current;
      if (!start || start.id !== event.pointerId || mode !== "floating") return;
      const dx = event.clientX - start.x, dy = event.clientY - start.y;
      customized.current = true;
      setRect(constrainConsole(start.kind === "move" ? { ...start.rect, x: start.rect.x + dx, y: start.rect.y + dy } : resizeConsole(start.rect, viewport, start.edge, dx, dy), viewport));
    },
    end: event => {
      if (gesture.current?.id !== event.pointerId) return;
      gesture.current = null;
      if (event.currentTarget.hasPointerCapture?.(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
    },
    cancel,
    keys: event => {
      if (event.key === "Escape") { cancel(); return; }
      if (mode !== "floating" || event.altKey || event.ctrlKey || event.metaKey || !["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) return;
      event.preventDefault();
      customized.current = true;
      const dx = event.key === "ArrowRight" ? 10 : event.key === "ArrowLeft" ? -10 : 0;
      const dy = event.key === "ArrowDown" ? 10 : event.key === "ArrowUp" ? -10 : 0;
      setRect(constrainConsole(event.shiftKey ? { ...shown, width: Math.min(viewport.width - shown.x, shown.width + dx), height: Math.min(viewport.height - shown.y, shown.height + dy) } : { ...shown, x: shown.x + dx, y: shown.y + dy }, viewport));
    },
  };
  return <ConsoleContext.Provider value={controls}>
    <div className="console-window" data-console-mode={mode} style={{ left: shown.x, top: shown.y, width: shown.width, height: shown.height }}>
      {children}
      {additionalEdges.map(edge => <span key={edge} className="console-edge-handle" data-console-edge={edge} aria-hidden="true" hidden={mode !== "floating"}
        onPointerDown={event => controls.begin(event, "resize", edge)} onPointerMove={controls.move} onPointerUp={controls.end} onPointerCancel={controls.cancel} onLostPointerCapture={() => { gesture.current = null; }} />)}
      <button type="button" className="console-resize-handle" aria-label="调整主控台大小" aria-describedby="console-window-help" disabled={mode !== "floating"} title={mode === "floating" ? "拖动调整大小；也可在移动主控台按钮上使用Shift加方向键" : "铺满时无需调整大小"}
        onPointerDown={event => controls.begin(event, "resize")} onPointerMove={controls.move} onPointerUp={controls.end} onPointerCancel={controls.cancel} onLostPointerCapture={() => { gesture.current = null; }} onKeyDown={controls.keys}>◢</button>
    </div>
  </ConsoleContext.Provider>;
}
