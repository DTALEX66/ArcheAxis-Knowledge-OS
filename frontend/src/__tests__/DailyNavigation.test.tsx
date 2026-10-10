import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import mappingText from "../../../docs/history/ui-design-increment-20261009/PAGE-ENTRY-MAPPING.csv?raw";
import { SpaceRail } from "../components/SpaceRail";
import { CommandPalette } from "../components/CommandPalette";
import { SPACES } from "../spaces/spaces";
import { UI_PAGES, UI_DAILY_ENTRY_POINTS, UI_FIXED_ENTRY_POINTS, uiEntryForPage } from "../presentation/uiPages";
import { EFFECTIVE_NAVIGATION_ENTRIES, resolveNavigationHash } from "../presentation/navigation";

// SIMULATED UI evidence; no fixture is a Core authorization or implementation claim.
describe("five daily navigation", () => {
  it("preserves every original page assignment and deep link from the immutable mapping", () => {
    const rows=mappingText.trim().split(/\r?\n/).slice(1);
    expect(rows).toHaveLength(22);expect(UI_PAGES).toHaveLength(22);
    for(const row of rows){const [id,,entry]=row.split(",");expect(uiEntryForPage(id)?.label).toBe(entry);expect(resolveNavigationHash(`#page=${id}`)?.pageId).toBe(id);}
    const ids=[...UI_DAILY_ENTRY_POINTS,...UI_FIXED_ENTRY_POINTS].flatMap(entry=>entry.pageIds);
    expect(new Set(ids).size).toBe(22);expect(ids.slice().sort()).toEqual(UI_PAGES.map(page=>page.id).sort());
    expect(EFFECTIVE_NAVIGATION_ENTRIES.filter(entry=>entry.page)).toHaveLength(22);
  });
  it("shows five daily and two fixed entries while preserving research, canvas and receipt children", () => {
    const onPage=vi.fn();const view=render(<SpaceRail active="vault" pageId="05" onPage={onPage} onNavigate={vi.fn()} spaces={SPACES}/>);
    expect(within(screen.getByRole("list",{name:"日常工作流"})).getAllByRole("button").map(button=>button.textContent)).toEqual(["工作台","知识","学习","AI","资源"]);
    expect(within(screen.getByRole("list",{name:"固定入口"})).getAllByRole("button").map(button=>button.textContent)).toEqual(["全部能力","设置"]);
    expect(screen.getByRole("button",{name:"研究空间"})).toHaveAttribute("aria-current","page");
    fireEvent.click(screen.getByRole("button",{name:"阅读与编辑"}));expect(onPage).toHaveBeenCalledWith("03");
    view.rerender(<SpaceRail active="learning" pageId="21" onPage={onPage} onNavigate={vi.fn()} spaces={SPACES}/>);
    expect(screen.getByRole("button",{name:"画布与视觉表达"})).toHaveAttribute("aria-current","page");
    view.rerender(<SpaceRail active="ai-assets" pageId="22" onPage={onPage} onNavigate={vi.fn()} spaces={SPACES}/>);
    expect(screen.getByRole("button",{name:"受限任务与回执"})).toHaveAttribute("aria-current","page");
    expect(screen.getByText("全能力目录")).toBeInTheDocument();
  });
  it("keeps keyboard navigation but does not consume composing, repeat or AltGraph input", () => {
    const onPage=vi.fn();render(<SpaceRail active="workspace" pageId="01" onPage={onPage} onNavigate={vi.fn()} spaces={SPACES}/>);
    const button=screen.getByRole("button",{name:"工作台"});button.focus();
    fireEvent.keyDown(button,{key:"ArrowDown",isComposing:true});fireEvent.keyDown(button,{key:"ArrowDown",repeat:true});
    const event=new KeyboardEvent("keydown",{key:"ArrowDown",bubbles:true});Object.defineProperty(event,"getModifierState",{value:(key:string)=>key==="AltGraph"});fireEvent(button,event);
    expect(onPage).not.toHaveBeenCalled();fireEvent.keyDown(button,{key:"ArrowDown"});expect(onPage).toHaveBeenCalledWith("02");expect(screen.getByRole("button",{name:"知识"})).toHaveFocus();
  });
  it("searches all pages outside the active daily group without claiming object search", () => {
    const onPage=vi.fn();render(<CommandPalette onPage={onPage} onNavigate={vi.fn()}/>);
    fireEvent.keyDown(window,{key:"k",ctrlKey:true,isComposing:true});fireEvent.keyDown(window,{key:"k",ctrlKey:true,repeat:true});expect(screen.queryByRole("dialog")).toBeNull();
    fireEvent.keyDown(window,{key:"k",ctrlKey:true});
    const input=screen.getByRole("searchbox",{name:"搜索空间或命令"});expect(input).toHaveAttribute("placeholder","搜索页面与能力…");
    fireEvent.change(input,{target:{value:"画布与视觉表达"}});const option=document.querySelector<HTMLButtonElement>('[data-entry-id="page:21"]');expect(option).not.toBeNull();fireEvent.click(option!);expect(onPage).toHaveBeenCalledWith("21");
  });
});
