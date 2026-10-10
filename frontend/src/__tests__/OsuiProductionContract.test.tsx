import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { App } from "../app/App";
import { UI_DAILY_ENTRY_POINTS, UI_FIXED_ENTRY_POINTS, UI_PAGES } from "../presentation/uiPages";
import { LearningSpace } from "../spaces/LearningSpace";
import userEvent from "@testing-library/user-event";

describe("OSUI v3 production contract", () => {
  it("exposes the new five domains with preserved semantic pages and a detail-only page 18", () => {
    render(<App/>);
    expect(UI_PAGES).toHaveLength(22);
    const rail=screen.getByRole("navigation",{name:"主空间导航"});
    for(const entry of [...UI_DAILY_ENTRY_POINTS,...UI_FIXED_ENTRY_POINTS]) expect(within(rail).getByRole("button",{name:entry.label})).toBeInTheDocument();
    expect(within(rail).queryByRole("button",{name:"研究空间"})).toBeNull();
    expect(within(rail).queryByRole("button",{name:"能力详情"})).toBeNull();
  });
  it("renders the product workbench instead of a generic status dashboard", () => {
    render(<App />);

    expect(document.querySelector(".app-shell")).toBeInTheDocument();
    expect(document.querySelector(".ui-workspace")).toBeInTheDocument();
    const main = screen.getByRole("main", { name: "当前空间内容" });
    expect(within(main).getByRole("heading", { name: /工作台/, level: 1 })).toBeInTheDocument();
  });

  it("renders one complete product shell with global commands and contextual navigation", () => {
    render(<App />);

    expect(screen.getByRole("button", { name: "打开全局命令" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "主空间导航" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "展开检查器" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "展开活动坞" })).toBeInTheDocument();
  });

  it("uses the global command palette to reach an actual content surface", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: "打开全局命令" }));
    expect(screen.getByRole("dialog", { name: "全局命令" })).toBeInTheDocument();
    await user.type(screen.getByRole("searchbox", { name: "搜索空间或命令" }), "阅读与编辑");
    await user.click(screen.getByRole("option", { name: /阅读与编辑/ }));
    expect(
      within(screen.getByRole("main")).getByRole("heading", { name: "阅读与编辑" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Agent")).not.toBeInTheDocument();
  });

  it("traps command focus, hides the background, supports arrows, and restores focus", async () => {
    const user = userEvent.setup();
    render(<App />);
    const trigger = screen.getByRole("button", { name: "打开全局命令" });
    await user.click(trigger);
    const search = screen.getByRole("searchbox", { name: "搜索空间或命令" });
    expect(search).toHaveFocus();
    await user.keyboard("{Control>}k{/Control}");
    expect(document.querySelector(".app-shell")).toHaveAttribute("inert");
    expect(document.querySelector(".app-shell")).toHaveAttribute("aria-hidden", "true");

    await user.keyboard("{ArrowDown}");
    const options = screen.getAllByRole("option");
    expect(options[0]).toHaveFocus();
    expect(options[0]).toHaveAttribute("aria-selected", "true");
    options.at(-1)?.focus();
    await user.tab();
    expect(search).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(trigger).toHaveFocus();
    expect(document.querySelector(".app-shell")).not.toHaveAttribute("inert");
    expect(document.querySelector(".app-shell")).not.toHaveAttribute("aria-hidden");
  });

  it("makes every Workbench quick action operable", async () => {
    const user = userEvent.setup();
    render(<App />);
    const rail = screen.getByRole("navigation", { name: "主空间导航" });

    await user.click(within(rail).getByRole("button", { name: "知识" }));
    await user.click(within(rail).getByRole("button", { name: /阅读与编辑/ }));
    expect(
      within(screen.getByRole("main")).getByRole("heading", { name: "阅读与编辑" }),
    ).toBeInTheDocument();
    await user.click(within(rail).getByRole("button", { name: "工作台" }));
    await user.click(within(rail).getByRole("button", { name: /设置/ }));
    const main = screen.getByRole("main");
    expect(within(main).getByRole("heading", { name: /设置/ })).toBeInTheDocument();
  });

  it("does not expose the former mixed-language primary labels", () => {
    render(<App />);

    for (const leaked of ["Workspace", "Library", "Evidence", "Learning", "AI Assets", "Settings"]) {
      expect(screen.queryByRole("button", { name: leaked })).not.toBeInTheDocument();
    }
    expect(document.body).not.toHaveTextContent("浏览器开发模式（Web development mode）");
  });

  it("keeps unfinished visual lesson and spatial memory out of ordinary navigation", () => {
    render(<LearningSpace />);

    expect(screen.queryByRole("button", { name: "视觉课件" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "空间记忆" })).not.toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("播放未开放");
    expect(document.body).not.toHaveTextContent("规划中");
  });

  it("keeps the product visual structure and accessible motion contract in production", () => {
    render(<App />);

    expect(document.querySelector(".status-bar-brand")).toBeInTheDocument();
    expect(document.querySelector(".space-view[data-motion='enter']")).toBeInTheDocument();
  });
});
