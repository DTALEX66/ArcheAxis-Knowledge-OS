import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { SPACES, type SpaceId } from "../spaces/spaces";

export function CommandPalette({ onNavigate }: { onNavigate: (id: SpaceId) => void }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(-1);
  const openRef = useRef(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const optionRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const previousFocus = useRef<HTMLElement | null>(null);

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
    setActiveIndex(-1);
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        openPalette();
      }
      if (event.key === "Escape" && open) {
        event.preventDefault();
        closePalette();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [closePalette, open, openPalette]);

  useEffect(() => {
    if (!open) return;
    const shell = document.querySelector<HTMLElement>(".app-shell");
    shell?.setAttribute("inert", "");
    shell?.setAttribute("aria-hidden", "true");
    inputRef.current?.focus();
    return () => {
      shell?.removeAttribute("inert");
      shell?.removeAttribute("aria-hidden");
      queueMicrotask(() => (previousFocus.current ?? triggerRef.current)?.focus());
    };
  }, [open]);

  const matches = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase("zh-CN");
    if (!needle) return SPACES;
    return SPACES.filter((space) => `${space.label} ${space.description}`.toLocaleLowerCase("zh-CN").includes(needle));
  }, [query]);

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

  const select = (id: SpaceId) => {
    onNavigate(id);
    closePalette();
  };

  const trapFocus = (event: React.KeyboardEvent<HTMLElement>) => {
    if (event.key !== "Tab") return;
    const focusable = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>(
      'input:not([disabled]), button:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ) ?? []);
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable.at(-1)!;
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const overlay = open ? <div className="command-backdrop" role="presentation" onMouseDown={(event) => {
    if (event.target === event.currentTarget) closePalette();
  }}>
    <section
      ref={dialogRef}
      className="command-palette"
      role="dialog"
      aria-modal="true"
      aria-label="全局命令"
      onKeyDown={trapFocus}
    >
      <header>
        <input
          ref={inputRef}
          autoFocus
          type="search"
          role="searchbox"
          aria-label="搜索空间或命令"
          aria-controls="command-options"
          placeholder="搜索工作台、资料、证据、学习…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "ArrowDown") {
              event.preventDefault();
              focusOption(0);
            } else if (event.key === "ArrowUp") {
              event.preventDefault();
              focusOption(matches.length - 1);
            }
          }}
        />
        <button type="button" aria-label="关闭全局命令" onClick={closePalette}>关闭</button>
      </header>
      <div id="command-options" role="listbox" aria-label="可用命令">
        {matches.map((space, index) => <button
          ref={(element) => { optionRefs.current[index] = element; }}
          key={space.id}
          type="button"
          role="option"
          aria-selected={activeIndex === index}
          onFocus={() => setActiveIndex(index)}
          onKeyDown={(event) => {
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
              select(space.id);
            }
          }}
          onClick={() => select(space.id)}
        >
          <span className="command-icon" aria-hidden="true">{space.icon}</span>
          <span><b>{space.label}</b><small>{space.description}</small></span>
        </button>)}
        {matches.length === 0 ? <p className="command-empty">没有匹配的可用空间</p> : null}
      </div>
    </section>
  </div> : null;

  return <>
    <button ref={triggerRef} type="button" className="command-trigger" aria-label="打开全局命令" onClick={openPalette}>
      <span aria-hidden="true">⌕</span><span>搜索或前往</span><kbd>Ctrl K</kbd>
    </button>
    {overlay ? createPortal(overlay, document.body) : null}
  </>;
}
