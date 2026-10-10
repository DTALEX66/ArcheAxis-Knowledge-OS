import { UI_DAILY_ENTRY_POINTS, UI_FIXED_ENTRY_POINTS, UI_PAGES, defaultUiPage, uiEntryForPage } from "../presentation/uiPages";
import { AaosIcon } from "./AaosIcon";
import { useRef, useState } from "react";
import { spaceDescription, type SpaceDef, type SpaceId } from "../spaces/spaces";
import { CAPABILITY_NAVIGATION_ENTRIES } from "../presentation/navigation";
import { productLayerLabel } from "../presentation/labels";

export function SpaceRail({
  active,
  onNavigate,
  onOpenCapability,
  activeCapabilityId,
  spaces, pageId, onPage,
}: {
  active: SpaceId;
  onNavigate: (id: SpaceId) => void;
  onOpenCapability?: (id: string) => void;
  activeCapabilityId?: string | null;
  spaces: readonly SpaceDef[];
  pageId?: string; onPage?: (id:string)=>void;
}) {
  const navRef = useRef<HTMLElement>(null);
  const [capabilitiesOpen, setCapabilitiesOpen] = useState(false);

  function activateCapability(id: string) {
    setCapabilitiesOpen(false);
    onOpenCapability?.(id);
  }

  function focusIndex(index: number) {
    const buttons = navRef.current?.querySelectorAll<HTMLButtonElement>(
      "button[data-page-id], ul[aria-label='产品空间'] button[data-space-id], .capability-rail[open] .capability-nav-group[open] button[data-entry-id]",
    );
    if (!buttons || buttons.length === 0) return;
    const next = (index + buttons.length) % buttons.length;
    const target = buttons[next];
    target?.focus();
    if(target?.dataset.pageId) onPage?.(target.dataset.pageId);
    else if(target?.dataset.spaceId) onNavigate(target.dataset.spaceId as SpaceId);
    else if(target?.dataset.capabilityId) activateCapability(target.dataset.capabilityId);
  }

  function onNavigationItemKeyDown(event: React.KeyboardEvent) {
    if (event.nativeEvent.isComposing || event.nativeEvent.keyCode === 229 || event.repeat || event.getModifierState("AltGraph")) return;
    const buttons = navRef.current?.querySelectorAll<HTMLButtonElement>(
      "button[data-page-id], ul[aria-label='产品空间'] button[data-space-id], .capability-rail[open] .capability-nav-group[open] button[data-entry-id]",
    );
    const index = buttons ? Array.from(buttons).indexOf(event.currentTarget as HTMLButtonElement) : -1;
    if(index<0)return;
    switch (event.key) {
      case "ArrowDown":
        event.preventDefault();
        focusIndex(index + 1);
        break;
      case "ArrowUp":
        event.preventDefault();
        focusIndex(index - 1);
        break;
      case "Home":
        event.preventDefault();
        focusIndex(0);
        break;
      case "End":
        event.preventDefault();
        focusIndex((navRef.current?.querySelectorAll("button[data-page-id], ul[aria-label='产品空间'] button[data-space-id], .capability-rail[open] .capability-nav-group[open] button[data-entry-id]").length ?? spaces.length) - 1);
        break;
      default:
        break;
    }
  }

  const orderedCapabilities = CAPABILITY_NAVIGATION_ENTRIES;
  return (
    <nav ref={navRef} className="space-rail" aria-label="主空间导航">
      {onPage ? <div className="ui-page-navigation">
        <ul className="space-rail-list" aria-label="日常工作流">
          {UI_DAILY_ENTRY_POINTS.map(entry => <li key={entry.pageId}><button type="button" data-page-id={entry.pageId} className="space-rail-item"
            aria-current={entry.pageIds.includes(pageId ?? defaultUiPage(active)) && !activeCapabilityId ? (pageId === entry.pageId ? "page" : "true") : undefined}
            onKeyDown={onNavigationItemKeyDown} onClick={() => onPage(entry.pageId)}>{entry.label}</button></li>)}
        </ul>
        {(() => {
          const entry = uiEntryForPage(pageId ?? defaultUiPage(active));
          const children = UI_PAGES.filter(page => entry?.pageIds.includes(page.id) && page.id !== entry.pageId && page.id !== "18");
          return children.length > 0 && <div><h2 className="ui-page-group">{entry?.label}页面</h2><ul className="space-rail-list" aria-label={`${entry?.label}页面`}>
            {children.map(page => <li key={page.id}><button type="button" data-page-id={page.id} className="space-rail-item" aria-current={page.id === pageId && !activeCapabilityId ? "page" : undefined}
              onKeyDown={onNavigationItemKeyDown} onClick={() => onPage(page.id)}>{page.label}</button></li>)}
          </ul></div>;
        })()}
        <ul className="space-rail-list" aria-label="固定入口">
          {UI_FIXED_ENTRY_POINTS.map(entry => <li key={entry.pageId}><button type="button" data-page-id={entry.pageId} className="space-rail-item"
            aria-current={entry.pageIds.includes(pageId ?? defaultUiPage(active)) ? (pageId === entry.pageId && !activeCapabilityId ? "page" : "true") : undefined}
            onKeyDown={onNavigationItemKeyDown} onClick={() => onPage(entry.pageId)}>{entry.label}</button></li>)}
        </ul>
      </div> : <ul className="space-rail-list" role="list" aria-label="产品空间">
        {spaces.map((space) => (
          <li key={space.id}>
            <button
              type="button"
              data-space-id={space.id}
              data-navigation-item
              className="space-rail-item"
              aria-current={space.id === active && !activeCapabilityId ? "page" : undefined}
              onClick={() => onNavigate(space.id)}
              onKeyDown={onNavigationItemKeyDown}
              title={spaceDescription(space)}
            >
              <span className="space-rail-icon" aria-hidden="true"><AaosIcon name={space.icon} /></span>
              <span>{space.label}</span>
            </button>
          </li>
        ))}
      </ul>}
      <details className="capability-rail" open={capabilitiesOpen} onToggle={(event) => setCapabilitiesOpen(event.currentTarget.open)}>
        <summary aria-label="展开全能力目录">全能力目录</summary>
        {Array.from(new Set(orderedCapabilities.map((entry) => entry.group_id))).map((group) => <details key={group} className="capability-nav-group" open>
          <summary>{productLayerLabel(group)}</summary>
          <ul className="capability-rail-list">
            {orderedCapabilities.map((entry) => {
              if (entry.group_id !== group) return null;
              const capability = entry.capability;
              if (!capability) return null;
              return <li key={entry.entry_id}><button type="button" className="space-rail-item capability-rail-item" data-entry-id={entry.entry_id} data-capability-id={capability.atlas.capability_id}
                data-navigation-item onKeyDown={onNavigationItemKeyDown}
                aria-current={activeCapabilityId === capability.atlas.capability_id ? "page" : undefined}
                onClick={() => activateCapability(capability.atlas.capability_id)} title={`${entry.description} · 查看能力详情`}>
                <span className="space-rail-icon" aria-hidden="true">◇</span><span>{entry.label}</span>
              </button></li>;
            })}
          </ul>
        </details>)}
      </details>
    </nav>
  );
}
