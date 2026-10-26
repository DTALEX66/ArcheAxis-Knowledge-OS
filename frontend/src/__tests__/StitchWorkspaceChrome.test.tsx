import { useState } from "react";
import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { UI_PAGES } from "../presentation/uiPages";
import { StitchCompanionWindow, StitchWorkspaceDock, StitchWorkspaceMenu } from "../components/StitchWorkspaceChrome";

afterEach(() => vi.unstubAllGlobals());

it("all current business roles remain reachable through actual application menu actions", async () => {
  const user = userEvent.setup(), onPage = vi.fn(), onNavigation = vi.fn();
  render(<StitchWorkspaceMenu onPage={onPage} onNavigation={onNavigation}/>);
  const menu = screen.getByRole("navigation", { name: "应用菜单" });
  const reached = new Set<string>();
  for (const details of menu.querySelectorAll("details")) {
    await user.click(details.querySelector("summary")!);
    const labels = within(details).getAllByRole("button").map(button => button.textContent);
    for (const label of labels) {
      if (!details.open) await user.click(details.querySelector("summary")!);
      await user.click(within(details).getByRole("button", { name: label! }));
      reached.add(onPage.mock.lastCall![0]);
      expect(details.open).toBe(false);
    }
  }
  expect([...reached].sort()).toEqual(UI_PAGES.map(page => page.id).sort());
  await user.click(within(menu).getByRole("button", { name: "全部页面，打开产品导航" }));
  expect(onNavigation).toHaveBeenCalledOnce();
});

it("menus dismiss with Escape, outside input and focus leaving; Escape restores the menu trigger", async () => {
  const user = userEvent.setup();
  render(<><StitchWorkspaceMenu onPage={vi.fn()} onNavigation={vi.fn()}/><button>外部操作</button></>);
  const summary = screen.getByText("学习", { selector: "summary" });
  await user.click(summary); expect(summary.parentElement).toHaveAttribute("open");
  await user.keyboard("{Escape}"); expect(summary.parentElement).not.toHaveAttribute("open"); expect(summary).toHaveFocus();
  await user.click(summary); await user.click(screen.getByRole("button", { name: "外部操作" }));
  expect(summary.parentElement).not.toHaveAttribute("open");
});

it("menu current-page markers follow the actual page while retaining ordinary navigation buttons", async () => {
  const user = userEvent.setup(), onPage = vi.fn();
  const view = render(<StitchWorkspaceMenu pageId="03" onPage={onPage} onNavigation={vi.fn()}/>);
  for (const page of UI_PAGES) {
    view.rerender(<StitchWorkspaceMenu pageId={page.id} onPage={onPage} onNavigation={vi.fn()}/>);
    const marked = [...view.container.querySelectorAll('button[aria-current="page"]')];
    expect(marked.length).toBeGreaterThan(0);
    expect(marked.every(button => button.getAttribute("data-page-id") === page.id)).toBe(true);
    expect(view.container.querySelector('[aria-selected]')).not.toBeInTheDocument();
  }
  view.rerender(<StitchWorkspaceMenu pageId="03" onPage={onPage} onNavigation={vi.fn()}/>);
  const knowledge = screen.getByText("知识", { selector: "summary" });
  await user.click(knowledge);
  const current = within(knowledge.parentElement!).getByRole("button", { current: "page" });
  expect(current).toHaveTextContent("阅读");
  await user.click(current);
  expect(onPage).toHaveBeenLastCalledWith("03");
  expect(knowledge.parentElement).not.toHaveAttribute("open");
  expect(knowledge).toHaveFocus();
});

it("native menu disclosures support keyboard traversal without changing guarded page actions", async () => {
  const user = userEvent.setup(), onPage = vi.fn();
  render(<StitchWorkspaceMenu onPage={onPage} onNavigation={vi.fn()}/>);
  const knowledge = screen.getByText("知识", { selector: "summary" });
  knowledge.focus();
  await user.keyboard("{ArrowDown}");
  expect(knowledge.parentElement).toHaveAttribute("open");
  expect(within(knowledge.parentElement!).getByRole("button", { name: "知识库" })).toHaveFocus();
  await user.keyboard("{End}");
  expect(within(knowledge.parentElement!).getByRole("button", { name: "版本、来源与历史" })).toHaveFocus();
  await user.keyboard("{Home}{ArrowDown}{Enter}");
  expect(onPage).toHaveBeenLastCalledWith("03");
  expect(knowledge.parentElement).not.toHaveAttribute("open");
  expect(knowledge).toHaveFocus();
  await user.keyboard("{ArrowUp}{ArrowRight}");
  const learning = screen.getByText("学习", { selector: "summary" });
  expect(learning).toHaveFocus(); expect(learning.parentElement).toHaveAttribute("open");
  expect(knowledge.parentElement).not.toHaveAttribute("open");
  await user.keyboard("{Escape}");
  expect(learning).toHaveFocus(); expect(learning.parentElement).not.toHaveAttribute("open");
});

it("dock keeps exactly one active application for every role and delegates genuine navigation", async () => {
  const user = userEvent.setup(), onPage = vi.fn(), onCompanion = vi.fn();
  const view = render(<StitchWorkspaceDock pageId="01" onPage={onPage} companionOpen={false} onCompanion={onCompanion}/>);
  for (const page of UI_PAGES) {
    view.rerender(<StitchWorkspaceDock pageId={page.id} onPage={onPage} companionOpen={false} onCompanion={onCompanion}/>);
    expect(view.container.querySelectorAll('[aria-current="page"]')).toHaveLength(1);
  }
  await user.click(screen.getByRole("button", { name: "研究专题" })); expect(onPage).toHaveBeenLastCalledWith("05");
  await user.click(screen.getByRole("button", { name: "小栖" })); expect(onCompanion).toHaveBeenCalledOnce();
});

it("the independent companion view closes on Escape and returns focus without erasing shared draft state", async () => {
  const user = userEvent.setup();
  function Harness() {
    const [open, setOpen] = useState(false), [draft, setDraft] = useState("");
    return <><StitchWorkspaceDock pageId="05" onPage={vi.fn()} companionOpen={open} onCompanion={() => setOpen(value => !value)}/>{open ? <StitchCompanionWindow focusOnOpen onClose={() => setOpen(false)}><input aria-label="共享会话草稿" value={draft} onChange={event => setDraft(event.target.value)}/></StitchCompanionWindow> : null}</>;
  }
  render(<Harness/>);
  const toggle = screen.getByRole("button", { name: "小栖" });
  await user.click(toggle); expect(screen.getByRole("complementary", { name: "小栖 · 陪伴会话" })).toHaveFocus(); await user.type(screen.getByLabelText("共享会话草稿"), "保留中的请求");
  await user.keyboard("{Escape}"); expect(screen.queryByLabelText("共享会话草稿")).not.toBeInTheDocument(); expect(toggle).toHaveFocus();
  await user.click(toggle); expect(screen.getByLabelText("共享会话草稿")).toHaveValue("保留中的请求");
});

it("companion drag has keyboard equivalence, bounded position and pointer-cancel rollback", () => {
  class Pointer extends MouseEvent { pointerId: number; constructor(type: string, init: PointerEventInit) { super(type, init); this.pointerId = init.pointerId ?? 1; } }
  vi.stubGlobal("PointerEvent", Pointer);
  render(<StitchCompanionWindow onClose={vi.fn()}>真实会话视图占位</StitchCompanionWindow>);
  const panel = screen.getByRole("complementary", { name: "小栖 · 陪伴会话" });
  vi.spyOn(panel, "getBoundingClientRect").mockReturnValue({ x: 100, y: 100, left: 100, top: 100, right: 400, bottom: 400, width: 300, height: 300, toJSON() {} });
  const handle = screen.getByRole("button", { name: "小栖 · 陪伴会话，移动小栖窗口" }), titlebar = handle.parentElement!;
  fireEvent.keyDown(handle, { key: "ArrowRight" }); expect(panel.style.left).toBe("110px");
  fireEvent.pointerDown(titlebar, { pointerId: 3, button: 0, clientX: 100, clientY: 100 });
  fireEvent.pointerMove(titlebar, { pointerId: 3, clientX: -900, clientY: -900 }); expect(panel.style.left).toBe("0px"); expect(panel.style.top).toBe("48px");
  fireEvent.pointerCancel(titlebar, { pointerId: 3 }); expect(panel.style.left).toBe("110px");
});

it("automatic companion appearance preserves the business input focus", () => {
  const view=render(<input aria-label="业务输入"/>);
  const input=screen.getByLabelText("业务输入");input.focus();
  view.rerender(<><input aria-label="业务输入"/><StitchCompanionWindow onClose={vi.fn()}>会话</StitchCompanionWindow></>);
  expect(input).toHaveFocus();
});
