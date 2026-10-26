/// <reference types="vite/client" />
import { createContext, useEffect, useRef, useState, type PointerEvent, type ReactNode } from "react";
import { motion, useReducedMotion } from "motion/react";
import { createPortal } from "react-dom";
import { AaosIcon, type AaosIconName } from "./AaosIcon";
import aaosMarkLight from "../assets/brand/aaos-mark-light.svg";
import { UI_PAGES } from "../presentation/uiPages";
import "./StitchWorkspaceChrome.css";

// Presentation only: the research editor retains its materials and draft ownership.
// null keeps standalone rendering; a managed outlet with no host is closed/parked.
export const StitchResearchOutlet = createContext<{ host: HTMLElement | null; onLocate: () => void } | null>(null);

const entries: readonly { page: string; label: string; icon: AaosIconName; pages: readonly string[] }[] = [
  { page: "01", label: "工作台", icon: "Workspace", pages: ["01"] },
  { page: "02", label: "知识", icon: "Knowledge", pages: ["02", "03", "04", "20"] },
  { page: "06", label: "学习", icon: "Learning", pages: ["06", "07", "08", "09", "10", "11", "12", "21"] },
  { page: "05", label: "研究专题", icon: "Research", pages: ["05"] },
];
const menus = [
  { label: "文件", pages: ["02", "03", "16", "20"] },
  { label: "视图", pages: ["01", "04", "21"] },
  { label: "知识", pages: ["02", "03", "04", "20"] },
  { label: "学习", pages: ["06", "07", "08", "09", "10", "11", "12"] },
  { label: "研究", pages: ["05"] },
  { label: "工具", pages: ["15", "16", "17", "18"] },
  { label: "AI 与模型", pages: ["13", "14", "22", "19"] },
] as const;
// Icons describe the existing pages; navigation and capability truth stay in UI_PAGES.
const menuPageIcons: Readonly<Record<string, AaosIconName>> = {
  "01": "Home", "02": "Knowledge", "03": "Write", "04": "Connection", "05": "Research",
  "06": "LearningPath", "07": "Learning", "08": "Learning", "09": "Evidence", "10": "Source",
  "11": "Review", "12": "Write", "13": "Context", "14": "Review", "15": "Extension",
  "16": "ImportDocument", "17": "Apps", "18": "Apps", "19": "Settings", "20": "Source", "21": "Canvas", "22": "Workflow",
};

/** All entries resolve through the existing guarded App navigation. No new page registry. */
export function StitchWorkspaceMenu({ pageId, onPage, onNavigation, onGuide }: { pageId?: string; onPage: (page: string) => void; onNavigation: () => void; onGuide?: () => void }) {
  const root = useRef<HTMLElement>(null);
  // File/View also contain shortcuts to other groups; mark the business group first.
  const ownsPage = (menu: typeof menus[number]) => menu.pages.some(page => page === pageId);
  const currentMenu = menus.find(menu => menu.label !== "文件" && menu.label !== "视图" && ownsPage(menu)) ?? menus.find(ownsPage);
  const currentPage = UI_PAGES.find(page => page.id === pageId);
  const dismiss = (returnFocus = false) => {
    root.current?.querySelectorAll<HTMLDetailsElement>("details[open]").forEach(menu => {
      menu.open = false;
      if (returnFocus) menu.querySelector("summary")?.focus({ preventScroll: true });
    });
  };
  useEffect(() => {
    const outside = (event: globalThis.PointerEvent) => { if (event.target instanceof Node && !root.current?.contains(event.target)) dismiss(); };
    document.addEventListener("pointerdown", outside);
    const resize = () => dismiss();
    window.addEventListener("resize", resize);
    return () => { document.removeEventListener("pointerdown", outside); window.removeEventListener("resize", resize); };
  }, []);
  return <nav ref={root} className="stitch-workspace-menu" aria-label="应用菜单" onKeyDown={event => {
    if (event.defaultPrevented || event.nativeEvent.isComposing) return;
    if (event.key === "Escape") { dismiss(true); event.preventDefault(); return; }
    const menu = (event.target as Element).closest("details");
    if (!menu) return;
    const trigger = menu.querySelector("summary"), items = [...menu.querySelectorAll<HTMLButtonElement>("button:not(:disabled)")];
    const index = items.indexOf(event.target as HTMLButtonElement);
    if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
      if (!items.length) return;
      menu.open = true;
      const next = event.key === "Home" ? 0 : event.key === "End" ? items.length - 1 : event.key === "ArrowDown" ? (index + 1) % items.length : (index < 0 ? items.length - 1 : (index - 1 + items.length) % items.length);
      items[next].focus(); event.preventDefault();
    } else if (["ArrowLeft", "ArrowRight"].includes(event.key)) {
      const triggers = [...root.current!.querySelectorAll<HTMLElement>(".stitch-menus > details > summary")];
      const next = triggers[(triggers.indexOf(trigger!) + (event.key === "ArrowRight" ? 1 : -1) + triggers.length) % triggers.length];
      const wasOpen = menu.open; dismiss(); next.focus();
      if (wasOpen) (next.parentElement as HTMLDetailsElement).open = true;
      event.preventDefault();
    }
  }} onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) dismiss(); }}>
    <button type="button" className="stitch-brand" onClick={() => onPage("01")} aria-label="ArcheAxis Knowledge 今日工作台"><img className="stitch-brand-logo" src={aaosMarkLight} alt="" height={22}/><span>ArcheAxis Knowledge</span></button>
    <div className="stitch-menus" onScroll={event => { if (event.target === event.currentTarget) dismiss(true); }}>
      {menus.map(menu => <details key={menu.label} onToggle={event => {
        const opened = event.currentTarget;
        if (opened.open) {
          root.current?.querySelectorAll<HTMLDetailsElement>("details[open]").forEach(other => { if (other !== opened) other.open = false; });
          const bounds = opened.querySelector("summary")!.getBoundingClientRect(), popup = opened.querySelector<HTMLElement>(".stitch-menu-popover")!;
          popup.style.left = `${Math.max(12, Math.min(bounds.left, window.innerWidth - Math.min(320, window.innerWidth - 24) - 12))}px`;
        }
      }}><summary data-current-group={menu === currentMenu || undefined} aria-description={menu === currentMenu && currentPage ? `当前页面：${currentPage.label}` : undefined} onPointerEnter={event => {
        if (event.pointerType !== "mouse") return;
        const previous = root.current?.querySelector<HTMLDetailsElement>("details[open]"), next = event.currentTarget.parentElement as HTMLDetailsElement;
        if (!previous || previous === next) return;
        const ownsFocus = previous.contains(document.activeElement);
        dismiss(); next.open = true;
        if (ownsFocus) event.currentTarget.focus({ preventScroll: true });
      }}>{menu.label}</summary><div className="stitch-menu-popover" aria-label={`${menu.label}页面`}><p className="stitch-menu-heading">{menu.label}</p>{menu.pages.map(page => <button type="button" key={page} data-page-id={page} aria-current={page === pageId ? "page" : undefined} onClick={() => { dismiss(true); onPage(page); }}><AaosIcon name={menuPageIcons[page] ?? "Source"} size={18}/><span>{UI_PAGES.find(entry => entry.id === page)?.label}</span></button>)}</div></details>)}
      <button type="button" aria-label="全部页面，打开产品导航" onClick={onNavigation}>全部页面</button>
      {onGuide ? <button type="button" onClick={onGuide}>使用引导</button> : null}
    </div>
  </nav>;
}

export function StitchWorkspaceDock({ pageId, onPage, companionOpen, onCompanion, onLaunchpad, launchpadOpen = false }: {
  pageId?: string; onPage: (page: string) => void; companionOpen: boolean; onCompanion: () => void;
  onLaunchpad?: () => void; launchpadOpen?: boolean;
}) {
  return <nav className="stitch-workspace-dock" aria-label="工作空间快捷导航">
    {entries.map(entry => <button key={entry.page} type="button" data-page-id={entry.page} title={entry.pages.includes(pageId ?? "") ? `当前：${UI_PAGES.find(page => page.id === pageId)?.label ?? entry.label}` : `前往${entry.label}`} aria-current={entry.pages.includes(pageId ?? "") ? "page" : undefined} onClick={() => onPage(entry.page)}><AaosIcon name={entry.icon} size={18}/><span>{entry.label}</span></button>)}
    <button id="stitch-launchpad-toggle" type="button" aria-expanded={launchpadOpen} aria-haspopup="dialog" onClick={() => onLaunchpad ? onLaunchpad() : onPage("17")}><AaosIcon name="Apps" size={18}/><span>全部能力</span></button>
    <button id="stitch-companion-toggle" type="button" className="stitch-companion-toggle" aria-expanded={companionOpen} aria-controls={companionOpen ? "stitch-companion-window" : undefined} onClick={onCompanion}><AaosIcon name="HumanAi" size={18}/><span>小栖</span></button>
  </nav>;
}

type Position = { x: number; y: number };
/** A nonmodal view of the existing shared companion session; closing never cancels its request. */
export function StitchCompanionWindow({ children, onClose, focusOnOpen = false }: { children: ReactNode; onClose: () => void; focusOnOpen?: boolean }) {
  const reduceMotion = useReducedMotion();
  const panel = useRef<HTMLElement>(null);
  const [position, setPosition] = useState<Position | null>(null);
  const gesture = useRef<{ id: number; x: number; y: number; start: Position; previous: Position | null } | null>(null);
  const constrain = (next: Position): Position => {
    const rect = panel.current?.getBoundingClientRect();
    return { x: Math.max(0, Math.min(next.x, window.innerWidth - (rect?.width ?? 300))), y: Math.max(48, Math.min(next.y, window.innerHeight - 64 - (rect?.height ?? 300))) };
  };
  const close = () => { onClose(); document.getElementById("stitch-companion-toggle")?.focus(); };
  useEffect(() => {
    if (focusOnOpen) panel.current?.focus({ preventScroll: true });
  }, [focusOnOpen]);
  useEffect(() => {
    const resize = () => { gesture.current = null; setPosition(null); };
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, []);
  const finish = (event: PointerEvent<HTMLElement>, cancel = false) => {
    if (gesture.current?.id !== event.pointerId) return;
    if (cancel) setPosition(gesture.current.previous);
    gesture.current = null;
    if (event.currentTarget.hasPointerCapture?.(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
  };
  return createPortal(<motion.aside initial={reduceMotion ? false : { opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: reduceMotion ? 0 : 0.18, ease: "easeOut" }} id="stitch-companion-window" ref={panel} className="stitch-companion-window" aria-labelledby="stitch-companion-title" tabIndex={-1} style={position ? { left: position.x, top: position.y, right: "auto" } : undefined} onKeyDown={event => {
    if (event.key !== "Escape" || event.defaultPrevented || event.nativeEvent.isComposing) return;
    if (gesture.current) { setPosition(gesture.current.previous); gesture.current = null; } else close();
    event.preventDefault(); event.stopPropagation();
  }}>
    <header className="stitch-window-titlebar" onPointerDown={event => {
      if (event.button !== 0 || (event.target as Element).closest("button:not(.stitch-companion-move)")) return;
      const rect = panel.current!.getBoundingClientRect();
      gesture.current = { id: event.pointerId, x: event.clientX, y: event.clientY, start: { x: rect.left, y: rect.top }, previous: position };
      event.currentTarget.setPointerCapture?.(event.pointerId); event.preventDefault();
    }} onPointerMove={event => { const start = gesture.current; if (start?.id === event.pointerId) setPosition(constrain({ x: start.start.x + event.clientX - start.x, y: start.start.y + event.clientY - start.y })); }} onPointerUp={event => finish(event)} onPointerCancel={event => finish(event, true)} onLostPointerCapture={() => { gesture.current = null; }}>
      <button type="button" className="stitch-companion-move" aria-label="小栖 · 陪伴会话，移动小栖窗口" title="拖动移动，也可用方向键移动" onKeyDown={event => {
        if (event.altKey || event.ctrlKey || event.metaKey || !["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) return;
        const rect = panel.current!.getBoundingClientRect();
        setPosition(constrain({ x: rect.left + (event.key === "ArrowRight" ? 10 : event.key === "ArrowLeft" ? -10 : 0), y: rect.top + (event.key === "ArrowDown" ? 10 : event.key === "ArrowUp" ? -10 : 0) })); event.preventDefault();
      }}><AaosIcon name="HumanAi" size={17}/><span id="stitch-companion-title">小栖 · 陪伴会话</span></button>
      <button type="button" aria-label="收起小栖窗口" onClick={close}>×</button>
    </header>
    <div className="stitch-companion-content">{children}</div>
  </motion.aside>, document.body);
}
