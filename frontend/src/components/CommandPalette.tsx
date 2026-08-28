import { useEffect, useMemo, useState } from "react";
import { SPACES, type SpaceId } from "../spaces/spaces";

export function CommandPalette({ onNavigate }: { onNavigate: (id: SpaceId) => void }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen(true);
      }
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const matches = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase("zh-CN");
    if (!needle) return SPACES;
    return SPACES.filter((space) => `${space.label} ${space.description}`.toLocaleLowerCase("zh-CN").includes(needle));
  }, [query]);

  const select = (id: SpaceId) => {
    onNavigate(id);
    setOpen(false);
    setQuery("");
  };

  return <>
    <button type="button" className="command-trigger" aria-label="打开全局命令" onClick={() => setOpen(true)}>
      <span aria-hidden="true">⌕</span><span>搜索或前往</span><kbd>Ctrl K</kbd>
    </button>
    {open ? <div className="command-backdrop" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget) setOpen(false);
    }}>
      <section className="command-palette" role="dialog" aria-modal="true" aria-label="全局命令">
        <header>
          <input
            autoFocus
            type="search"
            role="searchbox"
            aria-label="搜索空间或命令"
            placeholder="搜索工作台、资料、证据、学习…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <button type="button" aria-label="关闭全局命令" onClick={() => setOpen(false)}>关闭</button>
        </header>
        <div role="listbox" aria-label="可用命令">
          {matches.map((space) => <button
            key={space.id}
            type="button"
            role="option"
            aria-selected="false"
            onClick={() => select(space.id)}
          >
            <span className="command-icon" aria-hidden="true">{space.icon}</span>
            <span><b>{space.label}</b><small>{space.description}</small></span>
          </button>)}
          {matches.length === 0 ? <p className="command-empty">没有匹配的可用空间</p> : null}
        </div>
      </section>
    </div> : null}
  </>;
}
