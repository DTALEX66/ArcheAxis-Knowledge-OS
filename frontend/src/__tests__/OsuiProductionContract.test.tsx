import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { App } from "../app/App";
import { SPACES } from "../spaces/spaces";
import { LearningSpace } from "../spaces/LearningSpace";
import userEvent from "@testing-library/user-event";

describe("OSUI v3 production contract", () => {
  it("uses Chinese-first names for every primary product space", () => {
    expect(SPACES.map((space) => space.label)).toEqual([
      "工作台",
      "资料库",
      "导入",
      "知识库",
      "证据",
      "学习",
      "机器知识",
      "交换",
      "设置",
    ]);
  });

  it("renders the Archive Desk workbench instead of a generic status dashboard", () => {
    render(<App />);

    expect(document.querySelector(".archive-desk-shell")).toBeInTheDocument();
    expect(document.querySelector(".workspace-page")).toBeInTheDocument();
    const main = screen.getByRole("main", { name: "当前空间内容" });
    expect(within(main).getByRole("heading", { name: /工作台/ })).toBeInTheDocument();
  });

  it("renders one complete product shell with global commands and contextual navigation", () => {
    render(<App />);

    expect(screen.getByRole("button", { name: "打开全局命令" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "当前空间导航" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "展开检查器" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "展开活动坞" })).toBeInTheDocument();
  });

  it("uses the global command palette to navigate without exposing planned modules", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: "打开全局命令" }));
    expect(screen.getByRole("dialog", { name: "全局命令" })).toBeInTheDocument();
    await user.type(screen.getByRole("searchbox", { name: "搜索空间或命令" }), "资料");
    await user.click(screen.getByRole("option", { name: /资料库/ }));
    expect(
      within(screen.getByRole("main")).getByRole("heading", { name: "资料库" }),
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

    await user.click(within(rail).getByRole("button", { name: /资料库/ }));
    expect(
      within(screen.getByRole("main")).getByRole("heading", { name: "资料库" }),
    ).toBeInTheDocument();
    await user.click(within(rail).getByRole("button", { name: /工作台/ }));
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
});
