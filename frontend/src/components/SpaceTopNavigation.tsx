import { useEffect, useRef, useState } from "react";
import { defaultUiPage, UI_DAILY_ENTRY_POINTS, UI_FIXED_ENTRY_POINTS, UI_PAGES } from "../presentation/uiPages";
import type { SpaceId } from "../spaces/spaces";
import { AaosIcon, type AaosIconName } from "./AaosIcon";

const entries = [...UI_DAILY_ENTRY_POINTS, ...UI_FIXED_ENTRY_POINTS];
const icons: Record<string, AaosIconName> = { "02": "Knowledge", "03": "Source", "04": "Connection", "05": "Connection" };

/** A presentation of the existing page routes; App still owns all navigation guards. */
export function SpaceTopNavigation({ pageId, activeSpace = "workspace", onPage, activeCapabilityId }: {
  pageId?: string; activeSpace?: SpaceId; onPage: (id: string) => void; activeCapabilityId?: string | null;
}) {
  const effectivePageId = activeCapabilityId ? "18" : pageId ?? defaultUiPage(activeSpace);
  const ref = useRef<HTMLElement>(null);
  const [open, setOpen] = useState<string | null>(null);
  const trigger = (id: string) => ref.current?.querySelector<HTMLButtonElement>(`[data-top-page="${id}"]`);
  useEffect(() => {
    const close = (event: PointerEvent) => { if (!ref.current?.contains(event.target as Node)) setOpen(null); };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, []);
  function focusItem(index: number, selector: string) {
    const items = ref.current?.querySelectorAll<HTMLButtonElement>(selector);
    if (items?.length) items[(index + items.length) % items.length]?.focus();
  }
  return <nav ref={ref} className="space-top-navigation" aria-label="顶部空间导航" onBlur={event => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setOpen(null);
  }} onKeyDown={event => {
    if (event.nativeEvent.isComposing || event.repeat || event.altKey || event.ctrlKey || event.metaKey) return;
    const inMenu = (event.target as HTMLElement).closest("[role='menu']");
    const selector = inMenu ? "[role='menuitem']" : "[data-top-page]";
    const items = Array.from(ref.current?.querySelectorAll<HTMLButtonElement>(selector) ?? []);
    const index = items.indexOf(event.target as HTMLButtonElement);
    if (event.key === "Escape" && open) { event.preventDefault(); trigger(open)?.focus(); setOpen(null); }
    else if (index >= 0 && (event.key === "Home" || event.key === "End")) {
      event.preventDefault(); focusItem(event.key === "Home" ? 0 : items.length - 1, selector);
    } else if (index >= 0 && (inMenu ? ["ArrowDown", "ArrowUp"] : ["ArrowRight", "ArrowLeft"]).includes(event.key)) {
      event.preventDefault(); focusItem(index + (["ArrowDown", "ArrowRight"].includes(event.key) ? 1 : -1), selector);
    }
  }}>
    {entries.map(entry => {
      const pages = UI_PAGES.filter(page => entry.pageIds.includes(page.id) && page.id !== "18");
      const grouped = pages.length > 1;
      const current = entry.pageIds.includes(effectivePageId);
      return <div className="space-top-entry" key={entry.pageId}>
        <button type="button" data-top-page={entry.pageId} aria-current={current ? "page" : undefined}
          aria-haspopup={grouped ? "menu" : undefined} aria-expanded={grouped ? open === entry.pageId : undefined}
          aria-controls={grouped && open === entry.pageId ? `top-menu-${entry.pageId}` : undefined}
          onKeyDown={event => {
            if (grouped && event.key === "ArrowDown" && !event.nativeEvent.isComposing) {
              event.preventDefault(); setOpen(entry.pageId);
              requestAnimationFrame(() => ref.current?.querySelector<HTMLButtonElement>("[role='menuitem']")?.focus());
            }
          }}
          onClick={() => { if (grouped) setOpen(open === entry.pageId ? null : entry.pageId); else { setOpen(null); onPage(entry.pageId); } }}>
          {entry.label}{current && entry.pageId !== "01" ? <span className="space-top-active-dot" aria-hidden="true"/> : null}
        </button>
        {grouped && open === entry.pageId ? <div className="space-top-menu" id={`top-menu-${entry.pageId}`} role="menu" aria-label={`${entry.label}页面`}>
          <p aria-hidden="true">{entry.label}</p>
          {pages.map(page => <button type="button" key={page.id} role="menuitem" aria-current={effectivePageId === page.id ? "page" : undefined}
            onClick={() => { setOpen(null); trigger(entry.pageId)?.focus(); onPage(page.id); }}>
            <AaosIcon name={icons[page.id] ?? "Source"} size={22}/><span>{page.label}</span>
          </button>)}
        </div> : null}
      </div>;
    })}
  </nav>;
}
