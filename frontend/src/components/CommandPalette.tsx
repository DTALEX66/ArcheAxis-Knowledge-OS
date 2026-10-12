import { AaosIcon } from "./AaosIcon";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AaosButton, AaosDialog, AaosField } from "../design-system/AaosPrimitives";
import { canNavigateToCapability, EFFECTIVE_NAVIGATION_ENTRIES, navigationEntryMatches, type EffectiveNavigationEntry } from "../presentation/navigation";
import type { SpaceId } from "../spaces/spaces";
import { GlobalObjectSearch } from "./GlobalObjectSearch";
import type { ObjectReference } from "../api/generated/research-contract";

export function CommandPalette({ onNavigate, onOpenCapability, onOpenChange, onPage, onOpenObject }: { onNavigate: (id: SpaceId) => void; onOpenCapability?: (id: string) => void; onOpenChange?: (open: boolean) => void; onPage?: (id:string)=>void; onOpenObject?:(reference:ObjectReference,contentSha?:string)=>void }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(-1);
  const [composing,setComposing]=useState(false);
  const openRef = useRef(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const optionRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const previousFocus = useRef<HTMLElement | null>(null);

  useEffect(() => { onOpenChange?.(open); }, [open, onOpenChange]);
  useEffect(() => () => { onOpenChange?.(false); }, [onOpenChange]);

  const openPalette = useCallback(() => {
    if (openRef.current) return;
    openRef.current = true;
    previousFocus.current = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : triggerRef.current;
    setOpen(true);
  }, []);

  const closePalette = useCallback(() => {
    openRef.current = false;
    setOpen(false);
    setQuery("");
    setComposing(false);
    setActiveIndex(-1);
  }, []);

  useEffect(()=>{window.addEventListener("workspace-restore-start",closePalette);return()=>window.removeEventListener("workspace-restore-start",closePalette);},[closePalette]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.isComposing || event.keyCode === 229 || event.repeat || event.getModifierState("AltGraph") || event.altKey || event.shiftKey) return;
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        openPalette();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [openPalette]);

  useEffect(() => {
    if (!open) return;
    const shell = document.querySelector<HTMLElement>(".app-shell");
    shell?.setAttribute("inert", "");
    shell?.setAttribute("aria-hidden", "true");
    return () => {
      shell?.removeAttribute("inert");
      shell?.removeAttribute("aria-hidden");
    };
  }, [open]);

  const matches = useMemo(() => {
    return EFFECTIVE_NAVIGATION_ENTRIES.filter((entry) => (!onPage || !entry.space) && navigationEntryMatches(entry, query));
  }, [query, onPage]);

  useEffect(() => {
    setActiveIndex(-1);
    optionRefs.current = optionRefs.current.slice(0, matches.length);
  }, [matches]);

  const focusOption = (index: number) => {
    if (matches.length === 0) return;
    const next = (index + matches.length) % matches.length;
    setActiveIndex(next);
    optionRefs.current[next]?.focus();
  };

  const select = (entry: EffectiveNavigationEntry) => {
    if (entry.page) { if(onPage) onPage(entry.page.id); else window.location.hash=`page=${entry.page.id}`; }
    else if (entry.capability) onOpenCapability?.(entry.capability.atlas.capability_id);
    else if (entry.space) onNavigate(entry.space.id);
    closePalette();
  };

  const onDialogOpenChange = (next: boolean) => next ? openPalette() : closePalette();
  const onOpenAutoFocus = (event: Event) => {
    event.preventDefault();
    queueMicrotask(() => inputRef.current?.focus());
  };
  const onCloseAutoFocus = (event: Event) => {
    event.preventDefault();
    (previousFocus.current ?? triggerRef.current)?.focus();
  };

  return <AaosDialog
    title="全局命令"
    description="搜索页面与能力；未来能力可查看前提、依赖和降级方式。"
    trigger={<button ref={triggerRef} type="button" className="command-trigger" aria-label="打开全局命令" aria-keyshortcuts="Control+K">
      <span aria-hidden="true">⌕</span><span>搜索页面与能力</span><kbd>Ctrl K</kbd>
    </button>}
    open={open}
    onOpenChange={onDialogOpenChange}
    overlayClassName="command-backdrop"
    contentClassName="command-palette"
    onOpenAutoFocus={onOpenAutoFocus}
    onCloseAutoFocus={onCloseAutoFocus}
  >
      <header>
        <AaosField
          ref={inputRef}
          type="search"
          role="searchbox"
          label="搜索页面与能力"
          labelClassName="sr-only"
          className="command-search-input"
          aria-label="搜索空间或命令"
          aria-controls="command-options"
          placeholder="搜索页面与能力…"
          value={query}
          onCompositionStart={()=>setComposing(true)}
          onCompositionEnd={()=>setComposing(false)}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.nativeEvent.isComposing || event.nativeEvent.keyCode === 229 || event.repeat || event.getModifierState("AltGraph")) return;
            if (event.key === "ArrowDown") {
              event.preventDefault();
              focusOption(0);
            } else if (event.key === "ArrowUp") {
              event.preventDefault();
              focusOption(matches.length - 1);
            }
          }}
        />
        <AaosButton variant="ghost" aria-label="关闭全局命令" onClick={closePalette}>关闭</AaosButton>
      </header>
      <div id="command-options" role="listbox" aria-label="可用命令">
        {matches.map((entry, index) => <button
          ref={(element) => { optionRefs.current[index] = element; }}
          key={entry.entry_id}
          data-entry-id={entry.entry_id}
          type="button"
          role="option"
          aria-selected={activeIndex === index}
          onFocus={() => setActiveIndex(index)}
          onKeyDown={(event) => {
            if (event.nativeEvent.isComposing || event.nativeEvent.keyCode === 229 || event.repeat || event.getModifierState("AltGraph")) return;
            if (event.key === "ArrowDown") {
              event.preventDefault();
              focusOption(index + 1);
            } else if (event.key === "ArrowUp") {
              event.preventDefault();
              focusOption(index - 1);
            } else if (event.key === "Home") {
              event.preventDefault();
              focusOption(0);
            } else if (event.key === "End") {
              event.preventDefault();
              focusOption(matches.length - 1);
            } else if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              select(entry);
            }
          }}
          onClick={() => select(entry)}
        >
          <span className="command-icon" aria-hidden="true">{entry.space ? <AaosIcon name={entry.space.icon} /> : "◇"}</span>
          <span><b>{entry.label}</b><small>{entry.capability && !canNavigateToCapability(entry.capability) ? "查看详情 · 尚未实现" : `${entry.group_id} · ${entry.description}`}</small></span>
        </button>)}
        {matches.length === 0 ? <p className="command-empty">没有匹配的可用空间</p> : null}
      </div>
      {onOpenObject&&open?<GlobalObjectSearch query={query} composing={composing} onOpen={(reference,sha)=>{onOpenObject(reference,sha);closePalette();}}/>:null}
  </AaosDialog>;
}
