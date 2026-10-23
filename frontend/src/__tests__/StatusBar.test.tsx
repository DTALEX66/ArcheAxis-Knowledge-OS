import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StatusBar } from "../components/StatusBar";
import { ThemeProvider } from "../design-system/ThemeProvider";

// Single Stitch window tool group; business navigation remains owned by App.
describe("StatusBar as Stitch window tools", () => {
  it("exposes one command trigger and tools without duplicating global navigation or branding", () => {
    render(<StatusBar activeSpace="library" backendState="available" />);
    const tools = screen.getByRole("group", { name: "搜索与工作空间工具" });
    expect(within(tools).getAllByRole("button", { name: "打开全局命令" })).toHaveLength(1);
    expect(within(tools).getByRole("button", { name: "界面与工具设置" })).toBeInTheDocument();
    expect(screen.queryByRole("banner")).not.toBeInTheDocument();
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("导航呈现")).not.toBeInTheDocument();
  });

  it("renders connection status with readable text rather than color alone", () => {
    render(<StatusBar activeSpace="workspace" backendState="checking" />);
    const badge = screen.getByRole("status");
    expect(badge).toHaveTextContent("正在检查本地连接…");
    expect(badge).toHaveAttribute("data-state", "checking");
  });

  it("renders a persistent DEV marker only for explicit external development", () => {
    const { rerender } = render(<StatusBar activeSpace="workspace" backendState="available" externalDev />);
    expect(screen.getByRole("status")).toHaveTextContent("本地连接可用 · 开发");
    rerender(<StatusBar activeSpace="workspace" backendState="available" externalDev={false} />);
    expect(screen.getByRole("status")).toHaveTextContent("本地连接可用");
    expect(screen.getByRole("status")).not.toHaveTextContent("开发");
  });

  it("renders unavailable state without exposing an unreachable recovery control", () => {
    render(<StatusBar activeSpace="workspace" backendState="unavailable" />);
    expect(screen.getByRole("status")).toHaveTextContent("本地连接不可用");
    expect(screen.getByRole("status")).toHaveAttribute("data-state", "unavailable");
    expect(screen.getByRole("button", { name: "打开全局命令" })).toHaveAttribute("aria-keyshortcuts", "Control+K");
    expect(screen.queryByRole("button", { name: /重试后端|进入安全模式|恢复备份/ })).not.toBeInTheDocument();
  });

  it("labels immediate non-desktop rendering as browser preview", () => {
    render(<StatusBar activeSpace="workspace" backendState="web" />);
    expect(screen.getByRole("status")).toHaveTextContent("浏览器预览");
    expect(screen.getByRole("status")).toHaveAttribute("data-state", "web");
    expect(screen.queryByText("本地连接可用")).not.toBeInTheDocument();
  });

  it("opens real theme controls in the tools dialog and restores focus after Escape", async () => {
    const preferenceKey = "aaos.ui.theme.v1", previousPreference = localStorage.getItem(preferenceKey);
    localStorage.removeItem(preferenceKey);
    const user = userEvent.setup();
    try {
      render(<ThemeProvider><StatusBar activeSpace="workspace" backendState="web" /></ThemeProvider>);
      const trigger = screen.getByRole("button", { name: "界面与工具设置" });
      await user.click(trigger);
      const dialog = screen.getByRole("dialog", { name: "界面与工具" });
      const picker = within(dialog).getByRole("combobox", { name: "界面主题" });
      for (const id of ["black", "white", "cosmic"] as const) {
        await user.selectOptions(picker, id);
        expect(document.documentElement.dataset.aaosTheme).toBe(id);
        expect(localStorage.getItem(preferenceKey)).toBe(id);
      }
      await user.keyboard("{Escape}");
      expect(screen.queryByRole("dialog", { name: "界面与工具" })).not.toBeInTheDocument();
      expect(trigger).toHaveFocus();
    } finally {
      if (previousPreference === null) localStorage.removeItem(preferenceKey);
      else localStorage.setItem(preferenceKey, previousPreference);
      delete document.documentElement.dataset.aaosTheme;
    }
  });

  it("delegates settings navigation to App and closes tools before the destination renders", async () => {
    const user = userEvent.setup(), onPage = vi.fn();
    render(<StatusBar activeSpace="workspace" backendState="web" onPage={onPage} />);
    await user.click(screen.getByRole("button", { name: "界面与工具设置" }));
    await user.click(within(screen.getByRole("dialog", { name: "界面与工具" })).getByRole("button", { name: "打开设置" }));
    expect(onPage).toHaveBeenCalledOnce();
    expect(onPage).toHaveBeenLastCalledWith("19");
    expect(screen.queryByRole("dialog", { name: "界面与工具" })).not.toBeInTheDocument();
  });
});
