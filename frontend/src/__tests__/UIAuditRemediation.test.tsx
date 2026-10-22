import { afterEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../app/App";
import type { InspectionHandler } from "../components/Inspector";
import { commandKeyLabel } from "../presentation/keyboardShortcuts";
import { EFFECTIVE_NAVIGATION_ENTRIES, navigationEntryMatches } from "../presentation/navigation";

vi.mock("../spaces/SpaceView", async importOriginal => {
  const actual = await importOriginal<typeof import("../spaces/SpaceView")>();
  return { ...actual, SpaceView: ({ uiPageId, onInspect }: { uiPageId?: string; onInspect: InspectionHandler }) => <section>
    <output data-testid="audit-page">{uiPageId}</output>
    <button onClick={() => onInspect({ title: "自动同步条目", source: "SIMULATED", lifecycle: "测试" }, { reveal: false })}>同步当前条目</button>
    <button onClick={() => onInspect({ title: "主动检查条目", source: "SIMULATED", lifecycle: "测试" })}>主动检查</button>
  </section> };
});

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); window.history.replaceState(null, "", "#page=01"); });

describe("审计缺陷回归：实际 App 与 SIMULATED 业务子端口", () => {
  it.each(["click", "keyboard"])("工具对话框通过统一导航打开设置：%s", async mode => {
    window.history.replaceState(null, "", "#page=01"); render(<App />);
    const user = userEvent.setup(), trigger = screen.getByRole("button", { name: "界面与工具设置" });
    if (mode === "keyboard") { trigger.focus(); await user.keyboard("{Enter}"); } else await user.click(trigger);
    const button = within(screen.getByRole("dialog", { name: "界面与工具" })).getByRole("button", { name: "打开设置" });
    if (mode === "keyboard") { button.focus(); await user.keyboard("{Enter}"); } else await user.click(button);
    expect(screen.getByTestId("audit-page")).toHaveTextContent("19");
    expect(window.location.hash).toBe("#page=19");
    expect(screen.queryByRole("dialog", { name: "界面与工具" })).not.toBeInTheDocument();
  });
  it("工具里的设置遵守未保存草稿、输入法与工作区恢复屏障", () => {
    window.history.replaceState(null, "", "#page=01"); render(<App />);
    const openSettings = () => {
      fireEvent.click(screen.getByRole("button", { name: "界面与工具设置" }));
      fireEvent.click(within(screen.getByRole("dialog", { name: "界面与工具" })).getByRole("button", { name: "打开设置" }));
    };
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    act(() => window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: { owner: "audit", dirty: true } })));
    openSettings(); expect(confirm).toHaveBeenCalled(); expect(window.location.hash).toBe("#page=01");
    act(() => window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: { owner: "audit", dirty: false } })));
    fireEvent.compositionStart(window); openSettings(); expect(window.location.hash).toBe("#page=01"); fireEvent.compositionEnd(window);
    act(() => window.dispatchEvent(new Event("workspace-restore-start"))); fireEvent.click(screen.getByRole("button",{name:"界面与工具设置"})); expect(screen.queryByRole("dialog",{name:"界面与工具"})).not.toBeInTheDocument(); expect(window.location.hash).toBe("#page=01");
    act(() => window.dispatchEvent(new Event("workspace-restore-finish"))); openSettings(); expect(window.location.hash).toBe("#page=19");
  });
  it("窄窗口自动更新检查对象保留阅读区，显式打开与已打开检查器仍正常", () => {
    vi.stubGlobal("innerWidth", 640); render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "同步当前条目" }));
    expect(screen.queryByRole("complementary", { name: "检查器" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "主动检查" }));
    expect(screen.getByRole("complementary", { name: "检查器" })).toHaveTextContent("主动检查条目");
    fireEvent.click(screen.getByRole("button", { name: "同步当前条目" }));
    expect(screen.getByRole("complementary", { name: "检查器" })).toHaveTextContent("自动同步条目");
    fireEvent.click(screen.getByRole("button", { name: "关闭检查器" }));
    fireEvent.click(screen.getByRole("button", { name: "同步当前条目" }));
    expect(screen.queryByRole("complementary", { name: "检查器" })).not.toBeInTheDocument();
  });
});

it("平台快捷键文案一致且未知平台回退到 Ctrl", () => {
  expect(commandKeyLabel("Win32")).toBe("Ctrl"); expect(commandKeyLabel("MacIntel")).toBe("⌘"); expect(commandKeyLabel("")).toBe("Ctrl");
  render(<App />);
  expect(screen.getAllByRole("button", { name: "打开全局命令" })).toHaveLength(1);
  expect(screen.getByRole("button", { name: "打开全局命令" })).toHaveAttribute("aria-keyshortcuts", "Control+K");
  expect(screen.getByRole("button", { name: "打开全局命令" })).toHaveAttribute("title", `打开全局命令（${commandKeyLabel()} K）`);
});

it("页面命令显示使用目的，同时保留任务编号检索", () => {
  const reader = EFFECTIVE_NAVIGATION_ENTRIES.find(entry => entry.entry_id === "page:03")!;
  expect(reader.description).toBe("阅读资料、编辑正文并保留版本"); expect(navigationEntryMatches(reader, "UF03")).toBe(true);
  for (const entry of EFFECTIVE_NAVIGATION_ENTRIES.filter(entry => entry.page)) expect(entry.description).not.toMatch(/UI \/|底座|资格独立|UF\d/);
});
