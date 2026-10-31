import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { StitchLaunchpad } from "../components/StitchLaunchpad";
import { StitchWorkspaceDock } from "../components/StitchWorkspaceChrome";
import { CAPABILITY_NAVIGATION_ENTRIES, EFFECTIVE_NAVIGATION_ENTRIES } from "../presentation/navigation";
import { CAPABILITY_DESIGN_DETAIL_COUNT, capabilityPresentation } from "../presentation/capabilityCenter";

it("search reaches existing page routes and refuses closing when the draft guard refuses navigation", async () => {
  const user = userEvent.setup(), onPage = vi.fn<() => boolean>(() => false), onOpenChange = vi.fn();
  render(<StitchLaunchpad open onOpenChange={onOpenChange} onPage={onPage} onCapability={vi.fn()}/>);
  const search = screen.getByRole("textbox", { name: "搜索能力" });
  await user.type(search, "导入");
  const grid = screen.getByRole("list", { name: "能力入口" });
  await user.click(within(grid).getByRole("button", { name: /导入导出与互通/ }));
  expect(onPage).toHaveBeenCalledWith("16"); expect(onOpenChange).not.toHaveBeenCalled();
  onPage.mockReturnValue(true);
  await user.click(within(grid).getByRole("button", { name: /导入导出与互通/ }));
  expect(onOpenChange).toHaveBeenCalledWith(false);
});

it("future icons open catalog descriptions through the existing capability route, never a page execution", async () => {
  const user = userEvent.setup(), onPage = vi.fn(), onCapability = vi.fn();
  render(<StitchLaunchpad open onOpenChange={vi.fn()} onPage={onPage} onCapability={onCapability}/>);
  await user.click(screen.getByRole("button", { name: "扩展与未来" }));
  const future = EFFECTIVE_NAVIGATION_ENTRIES.find(entry => entry.capability && capabilityPresentation(entry.capability).group === "future")!;
  const button = within(screen.getByRole("list", { name: "能力入口" })).getByRole("button", { name: new RegExp(future.label) });
  expect(button).toHaveTextContent("规划中 · 查看说明");
  await user.click(button);
  expect(onCapability).toHaveBeenCalledWith(future.entry_id); expect(onPage).not.toHaveBeenCalled();
});

it("Escape closes and returns focus to the real dock trigger without changing the current route", async () => {
  const user = userEvent.setup(), onPage = vi.fn(), onOpenChange = vi.fn();
  const view = render(<><StitchWorkspaceDock onPage={onPage} companionOpen={false} onCompanion={vi.fn()}/><StitchLaunchpad open onOpenChange={onOpenChange} onPage={onPage} onCapability={vi.fn()}/></>);
  await user.keyboard("{Escape}"); expect(onOpenChange).toHaveBeenCalledWith(false); expect(onPage).not.toHaveBeenCalled();
  view.rerender(<><StitchWorkspaceDock onPage={onPage} companionOpen={false} onCompanion={vi.fn()}/><StitchLaunchpad open={false} onOpenChange={onOpenChange} onPage={onPage} onCapability={vi.fn()}/></>);
  await waitFor(() => expect(screen.getByRole("button", { name: "全部能力" })).toHaveFocus());
});

it("all page roles except catalog detail are reachable from the full page grid", async () => {
  const user = userEvent.setup(), onPage = vi.fn();
  render(<StitchLaunchpad open onOpenChange={vi.fn()} onPage={onPage} onCapability={vi.fn()}/>);
  await user.click(screen.getByRole("button", { name: "全部页面" }));
  const buttons = within(screen.getByRole("list", { name: "能力入口" })).getAllByRole("button");
  for (const button of buttons) await user.click(button);
  expect(onPage.mock.calls.map(call => call[0]).sort()).toEqual(EFFECTIVE_NAVIGATION_ENTRIES.filter(entry => entry.page && entry.page.id !== "18").map(entry => entry.page!.id).sort());
});

it("exposes all 16 capability families and a guarded complete catalog entry", async () => {
  const user = userEvent.setup(), onPage = vi.fn<(page: string) => boolean>(() => false), onOpenChange = vi.fn(), onCapability = vi.fn<(id: string) => boolean>(() => false);
  render(<StitchLaunchpad open onOpenChange={onOpenChange} onPage={onPage} onCapability={onCapability}/>);
  expect(screen.getByText("16 个能力族 · 186 条设计细项")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "常用入口" })).toHaveAttribute("aria-pressed", "true");
  const frequentButtons = within(screen.getByRole("list", { name: "能力入口" })).getAllByRole("button");
  expect(frequentButtons).toHaveLength(10);
  expect(frequentButtons.length).toBeLessThan(CAPABILITY_NAVIGATION_ENTRIES.length);
  expect(frequentButtons.length).toBeLessThan(CAPABILITY_DESIGN_DETAIL_COUNT);
  expect(screen.getByText("当前显示 10 个常用入口（部分工作页面）")).toBeVisible();
  expect(screen.getByRole("dialog", { name: "全部能力" })).toHaveAccessibleDescription("“常用入口”只是部分工作页面。查看所有能力请选“全部能力族”；查看完整蓝图请点“查看完整能力目录”，再选“全部设计细项”。");
  await user.click(screen.getByRole("button", { name: "查看完整能力目录" }));
  expect(onPage).toHaveBeenCalledWith("17"); expect(onOpenChange).not.toHaveBeenCalled();
  expect(screen.getByRole("dialog", { name: "全部能力" })).toBeVisible();
  await user.click(screen.getByRole("button", { name: "全部能力族" }));
  const buttons = within(screen.getByRole("list", { name: "能力入口" })).getAllByRole("button");
  expect(buttons).toHaveLength(16);
  expect(screen.getByText("16 个入口")).toBeVisible();
  expect(screen.queryByText("当前显示 10 个常用入口（部分工作页面）")).not.toBeInTheDocument();
  for (const button of buttons) await user.click(button);
  expect(onCapability.mock.calls.map(call => call[0]).sort()).toEqual(EFFECTIVE_NAVIGATION_ENTRIES.filter(entry => entry.capability).map(entry => entry.entry_id).sort());
  expect(onOpenChange).not.toHaveBeenCalled();
});

it("search includes built-in families and previews the authored child that matched", async () => {
  const user = userEvent.setup();
  render(<StitchLaunchpad open onOpenChange={vi.fn()} onPage={vi.fn()} onCapability={vi.fn()}/>);
  await user.type(screen.getByRole("textbox", { name: "搜索能力" }), "跨会话");
  const button = within(screen.getByRole("list", { name: "能力入口" })).getByRole("button", { name: /AI 学习资产与受控调用/ });
  expect(button).toHaveTextContent("跨会话 / 客户端上下文"); expect(button).toHaveTextContent("独立证据未核验");
});
