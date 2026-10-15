import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SpaceTopNavigation } from "../components/SpaceTopNavigation";
import { UI_DAILY_ENTRY_POINTS, UI_FIXED_ENTRY_POINTS } from "../presentation/uiPages";
import type { SpaceId } from "../spaces/spaces";

describe("alternate top navigation", () => {
  it.each<[SpaceId, string]>([["learning", "学习"], ["library", "知识"], ["vault", "知识"], ["ai-assets", "AI"], ["exchange", "资源"], ["settings", "设置"]])("projects a page-less %s route to one daily entry", (activeSpace, label) => {
    render(<SpaceTopNavigation activeSpace={activeSpace} onPage={vi.fn()}/>);
    const nav = screen.getByRole("navigation", {name:"顶部空间导航"});
    expect(nav.querySelectorAll("[aria-current='page']")).toHaveLength(1);
    expect(within(nav).getByRole("button", {name:label})).toHaveAttribute("aria-current", "page");
  });
  it("prefers explicit pages over spaces and capabilities over both without double selection", () => {
    const {rerender} = render(<SpaceTopNavigation activeSpace="learning" pageId="03" onPage={vi.fn()}/>);
    expect(screen.getByRole("button", {name:"知识"})).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("button", {name:"学习"})).not.toHaveAttribute("aria-current");
    rerender(<SpaceTopNavigation activeSpace="learning" pageId="03" activeCapabilityId="selected-capability" onPage={vi.fn()}/>);
    expect(screen.getByRole("button", {name:"全部能力"})).toHaveAttribute("aria-current", "page");
    expect(document.querySelectorAll("[data-top-page][aria-current='page']")).toHaveLength(1);
  });
  it("uses existing page identities for every daily and fixed entry", async () => {
    const user = userEvent.setup(); const onPage = vi.fn();
    render(<SpaceTopNavigation pageId="03" onPage={onPage}/>);
    const nav = screen.getByRole("navigation", {name: "顶部空间导航"});
    for (const entry of [...UI_DAILY_ENTRY_POINTS, ...UI_FIXED_ENTRY_POINTS]) {
      expect(within(nav).getByRole("button", {name: entry.label})).toBeInTheDocument();
    }
    const knowledge = screen.getByRole("button", {name: "知识"});
    expect(knowledge).toHaveAttribute("aria-current", "page");
    await user.click(knowledge);
    await user.click(screen.getByRole("menuitem", {name: "阅读与编辑"}));
    expect(onPage).toHaveBeenLastCalledWith("03");
    expect(knowledge).toHaveFocus(); expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", {name: "全部能力"}));
    expect(onPage).toHaveBeenLastCalledWith("17");
  });
  it("supports horizontal keys, menu keys, Escape and outside dismissal", async () => {
    const user = userEvent.setup(); const onPage = vi.fn();
    render(<SpaceTopNavigation onPage={onPage}/>);
    screen.getByRole("button", {name:"工作台"}).focus();
    await user.keyboard("{ArrowRight}");
    const knowledge = screen.getByRole("button", {name:"知识"}); expect(knowledge).toHaveFocus();
    await user.click(knowledge);
    const items = screen.getAllByRole("menuitem"); items[0].focus();
    await user.keyboard("{ArrowDown}"); expect(items[1]).toHaveFocus();
    await user.keyboard("{End}"); expect(items.at(-1)).toHaveFocus();
    await user.keyboard("{Escape}"); expect(knowledge).toHaveFocus();
    expect(onPage).not.toHaveBeenCalled();
    await user.click(knowledge); fireEvent.pointerDown(document.body);
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });
});
