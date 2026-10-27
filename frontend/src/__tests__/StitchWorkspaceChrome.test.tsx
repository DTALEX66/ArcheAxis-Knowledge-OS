import { useState } from "react";
import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { UI_PAGES } from "../presentation/uiPages";
import { StitchCompanionWindow, StitchWorkspaceDock, StitchWorkspaceMenu } from "../components/StitchWorkspaceChrome";

afterEach(() => vi.unstubAllGlobals());

it("file and view menus expose distinct commands and explicit layout recovery", async () => {
  const user=userEvent.setup(),onPage=vi.fn(),onLayoutMode=vi.fn(),onCompanion=vi.fn(),onInspector=vi.fn();
  render(<StitchWorkspaceMenu onPage={onPage} onNavigation={vi.fn()} layoutMode="focus" onLayoutMode={onLayoutMode} onCompanion={onCompanion} onInspector={onInspector}/>);
  await user.click(screen.getByText("文件",{selector:"summary"}));
  expect(within(screen.getByLabelText("文件页面")).getAllByRole("button").map(button=>button.textContent)).toEqual(["导入或导出资料…"]);
  await user.click(screen.getByText("视图",{selector:"summary"}));
  const view=screen.getByLabelText("视图页面");expect(within(view).getByRole("button",{name:"专注布局"})).toHaveAttribute("aria-pressed","true");expect(view.querySelector("[data-page-id]")).toBeNull();
  await user.click(within(view).getByRole("button",{name:"陪伴布局"}));expect(onLayoutMode).toHaveBeenCalledWith("companion");expect(onPage).not.toHaveBeenCalled();
});

it("hiding the companion keeps its original input mounted and excludes the window from interaction", () => {
  const view=render(<StitchCompanionWindow onClose={vi.fn()}><input aria-label="隐藏时保留原稿" defaultValue="未保存请求"/></StitchCompanionWindow>);
  const input=screen.getByLabelText("隐藏时保留原稿"),panel=document.getElementById("stitch-companion-window")!;
  view.rerender(<StitchCompanionWindow hidden onClose={vi.fn()}><input aria-label="隐藏时保留原稿" defaultValue="未保存请求"/></StitchCompanionWindow>);
  expect(panel).toHaveAttribute("hidden");expect(panel.inert).toBe(true);expect(input).toBeInTheDocument();
  view.rerender(<StitchCompanionWindow onClose={vi.fn()}><input aria-label="隐藏时保留原稿" defaultValue="未保存请求"/></StitchCompanionWindow>);
  expect(panel.inert).toBe(false);expect(screen.getByLabelText("隐藏时保留原稿")).toBe(input);expect(input).toHaveValue("未保存请求");
});

it("all current business roles remain reachable through actual application menu actions", async () => {
  const user = userEvent.setup(), onPage = vi.fn(), onNavigation = vi.fn();
  render(<StitchWorkspaceMenu onPage={onPage} onNavigation={onNavigation}/>);
  const menu = screen.getByRole("navigation", { name: "应用菜单" });
  const reached = new Set<string>();
  await user.click(within(menu).getByRole("button", { name: "ArcheAxis Knowledge 今日工作台" })); reached.add(onPage.mock.lastCall![0]);
  for (const details of menu.querySelectorAll("details")) {
    await user.click(details.querySelector("summary")!);
    const labels = [...details.querySelectorAll<HTMLButtonElement>("button[data-page-id]")].map(button => button.textContent);
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

it("the closed menu identifies one current group without claiming that its trigger is the current page", () => {
  const props = { onPage: vi.fn(), onNavigation: vi.fn() };
  const view = render(<StitchWorkspaceMenu {...props} pageId="03"/>);
  for (const page of UI_PAGES) {
    view.rerender(<StitchWorkspaceMenu {...props} pageId={page.id}/>);
    const current = view.container.querySelectorAll('summary[data-current-group="true"]');
    expect(current).toHaveLength(page.id === "01" ? 0 : 1);
    if (page.id !== "01") { expect(current[0]).toHaveAttribute("aria-description", `当前页面：${page.label}`); expect(current[0]).not.toHaveAttribute("aria-current"); }
    expect(view.container.querySelector("details[open]")).not.toBeInTheDocument();
    const actualPages = [...view.container.querySelectorAll('button[aria-current="page"]')];
    expect(actualPages.length).toBeGreaterThan(0);
    expect(actualPages.every(button => button.getAttribute("data-page-id") === page.id)).toBe(true);
  }
  for (const [pageId, label] of [["03", "知识"], ["13", "AI 与模型"], ["16", "文件"], ["21", "学习"], ["19", "工具"]]) {
    view.rerender(<StitchWorkspaceMenu {...props} pageId={pageId}/>);
    expect(view.container.querySelector('summary[data-current-group="true"]')).toHaveTextContent(label);
  }
  view.rerender(<StitchWorkspaceMenu {...props} pageId="unknown"/>);
  expect(view.container.querySelector("[data-current-group]")).not.toBeInTheDocument();
});

it("mouse hover switches an already open menu without navigating, while touch and pen do not open menus", async () => {
  class Pointer extends MouseEvent { pointerType: string; constructor(type: string, init: PointerEventInit) { super(type, init); this.pointerType = init.pointerType ?? ""; } }
  vi.stubGlobal("PointerEvent", Pointer);
  const user = userEvent.setup(), onPage = vi.fn();
  render(<StitchWorkspaceMenu onPage={onPage} onNavigation={vi.fn()}/>);
  const knowledge = screen.getByText("知识", { selector: "summary" }), learning = screen.getByText("学习", { selector: "summary" });
  fireEvent.pointerEnter(learning, { pointerType: "mouse" });
  expect(learning.parentElement).not.toHaveAttribute("open");
  await user.click(knowledge);
  await user.keyboard("{ArrowDown}");
  expect(within(knowledge.parentElement!).getByRole("button", { name: "知识库" })).toHaveFocus();
  for (const pointerType of ["touch", "pen", ""]) {
    fireEvent.pointerEnter(learning, { pointerType });
    expect(knowledge.parentElement).toHaveAttribute("open");
    expect(learning.parentElement).not.toHaveAttribute("open");
  }
  fireEvent.pointerEnter(learning, { pointerType: "mouse" });
  expect(knowledge.parentElement).not.toHaveAttribute("open");
  expect(learning.parentElement).toHaveAttribute("open");
  expect(learning).toHaveFocus();
  fireEvent.pointerEnter(learning, { pointerType: "mouse" });
  expect(learning.parentElement).toHaveAttribute("open");
  expect(onPage).not.toHaveBeenCalled();
  await user.keyboard("{ArrowDown}{Enter}");
  expect(onPage).toHaveBeenCalledOnce();
  expect(onPage).toHaveBeenCalledWith("06");
});

it("a delayed menu-strip scroll repositions the open popup without hiding its focused keyboard action", async () => {
  const user = userEvent.setup(), onPage = vi.fn();
  const view = render(<StitchWorkspaceMenu onPage={onPage} onNavigation={vi.fn()}/>);
  const knowledge = screen.getByText("知识", { selector: "summary" });
  await user.click(knowledge);
  await user.keyboard("{ArrowDown}");
  const popup = within(knowledge.parentElement!).getByLabelText("知识页面"), target = within(popup).getByRole("button", { name: "知识库" });
  expect(target).toHaveFocus();
  const originalLeft = popup.style.left;
  vi.spyOn(knowledge, "getBoundingClientRect").mockReturnValue({ x: 180, y: 0, left: 180, top: 0, right: 220, bottom: 32, width: 40, height: 32, toJSON() {} });
  fireEvent.scroll(popup);
  expect(popup.style.left).toBe(originalLeft);
  expect(knowledge.parentElement).toHaveAttribute("open"); expect(target).toHaveFocus();
  fireEvent.scroll(view.container.querySelector(".stitch-menus")!);
  expect(knowledge.parentElement).toHaveAttribute("open"); expect(target).toHaveFocus();
  expect(popup.style.left).toBe("180px");
  expect(onPage).not.toHaveBeenCalled();
  expect(target.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  await user.keyboard("{Enter}");
  expect(onPage).toHaveBeenCalledOnce(); expect(onPage).toHaveBeenCalledWith("02");
  expect(knowledge.parentElement).not.toHaveAttribute("open"); expect(knowledge).toHaveFocus();
});

it.each([{ left: -40, expected: "12px" }, { left: 300, expected: "58px" }])("scroll positioning retains the popup viewport clamp: %j", async ({ left, expected }) => {
  vi.stubGlobal("innerWidth", 390);
  const user = userEvent.setup();
  const view = render(<StitchWorkspaceMenu onPage={vi.fn()} onNavigation={vi.fn()}/>);
  const knowledge = screen.getByText("知识", { selector: "summary" });
  await user.click(knowledge); await user.keyboard("{ArrowDown}");
  const popup = within(knowledge.parentElement!).getByLabelText("知识页面"), target = within(popup).getByRole("button", { name: "知识库" });
  vi.spyOn(knowledge, "getBoundingClientRect").mockReturnValue({ x: left, y: 0, left, top: 0, right: left + 40, bottom: 32, width: 40, height: 32, toJSON() {} });
  fireEvent.scroll(view.container.querySelector(".stitch-menus")!);
  expect(popup.style.left).toBe(expected);
  expect(knowledge.parentElement).toHaveAttribute("open"); expect(target).toHaveFocus();
});

it.each([{ deltaX: 160 }, { deltaY: 160, shiftKey: true }])("horizontal wheel closes the original menu before scrolling can trigger another hover: %j", async delta => {
  class Pointer extends MouseEvent { pointerType = "mouse"; }
  vi.stubGlobal("PointerEvent", Pointer);
  const user = userEvent.setup(), onPage = vi.fn();
  const view = render(<StitchWorkspaceMenu onPage={onPage} onNavigation={vi.fn()}/>);
  const strip = view.container.querySelector(".stitch-menus")!;
  Object.defineProperties(strip, { scrollWidth: { value: 900 }, clientWidth: { value: 600 } });
  const file = screen.getByText("文件", { selector: "summary" }), next = screen.getByText("视图", { selector: "summary" });
  file.focus(); await user.keyboard("{ArrowDown}");
  expect(within(file.parentElement!).getByRole("button", { name: "导入或导出资料…" })).toHaveFocus();
  const wheel = new WheelEvent("wheel", { bubbles: true, cancelable: true, ...delta });
  fireEvent(file, wheel);
  expect(wheel.defaultPrevented).toBe(false);
  expect(file.parentElement).not.toHaveAttribute("open"); expect(file).toHaveFocus();
  fireEvent.pointerEnter(next); fireEvent.scroll(strip);
  expect(next.parentElement).not.toHaveAttribute("open"); expect(file).toHaveFocus();
  expect(onPage).not.toHaveBeenCalled();
});

it("wheel inside popup contents and a menu strip without overflow preserve the open menu", async () => {
  const user = userEvent.setup();
  const view = render(<StitchWorkspaceMenu onPage={vi.fn()} onNavigation={vi.fn()}/>);
  const strip = view.container.querySelector(".stitch-menus")!;
  Object.defineProperties(strip, { scrollWidth: { value: 900, configurable: true }, clientWidth: { value: 600 } });
  const learning = screen.getByText("学习", { selector: "summary" });
  learning.focus(); await user.keyboard("{ArrowDown}");
  const popup = within(learning.parentElement!).getByLabelText("学习页面"), first = within(popup).getByRole("button", { name: "学习路径" });
  fireEvent.wheel(popup, { deltaY: 160 }); fireEvent.wheel(popup, { deltaX: 80, deltaY: 160 });
  expect(learning.parentElement).toHaveAttribute("open"); expect(first).toHaveFocus();
  Object.defineProperty(strip, "scrollWidth", { value: 600 });
  fireEvent.wheel(learning, { deltaX: 160 });
  expect(learning.parentElement).toHaveAttribute("open"); expect(first).toHaveFocus();
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

it("dock marks only a genuine page group and delegates genuine navigation", async () => {
  const user = userEvent.setup(), onPage = vi.fn(), onCompanion = vi.fn();
  const groups: Record<string, string> = {"01":"工作台","02":"知识","03":"知识","04":"知识","20":"知识","05":"研究专题","06":"学习","07":"学习","08":"学习","09":"学习","10":"学习","11":"学习","12":"学习","21":"学习","13":"AI","14":"AI","22":"AI","15":"资源","16":"资源"};
  const view = render(<StitchWorkspaceDock pageId="01" onPage={onPage} companionOpen={false} onCompanion={onCompanion}/>);
  for (const page of UI_PAGES) {
    view.rerender(<StitchWorkspaceDock pageId={page.id} onPage={onPage} companionOpen={false} onCompanion={onCompanion}/>);
    const current = view.container.querySelectorAll('[aria-current="page"]');
    expect(current).toHaveLength(groups[page.id] ? 1 : 0);
    if (groups[page.id]) expect(current[0]).toHaveTextContent(groups[page.id]);
    expect(screen.getByRole("button", { name: "全部能力" })).not.toHaveAttribute("aria-current");
  }
  await user.click(screen.getByRole("button", { name: "研究专题" })); expect(onPage).toHaveBeenLastCalledWith("05");
  await user.click(screen.getByRole("button", { name: "小栖" })); expect(onCompanion).toHaveBeenCalledOnce();
});

it("capability launcher exposes expansion without impersonating the current page", async () => {
  const onLaunchpad = vi.fn();
  render(<StitchWorkspaceDock pageId="17" onPage={vi.fn()} companionOpen={false} onCompanion={vi.fn()} onLaunchpad={onLaunchpad} launchpadOpen/>);
  const launcher = screen.getByRole("button", { name: "全部能力" });
  expect(launcher).toHaveAttribute("aria-expanded", "true");
  expect(launcher).toHaveAttribute("aria-haspopup", "dialog");
  expect(launcher).not.toHaveAttribute("aria-current");
  await userEvent.setup().click(launcher);
  expect(onLaunchpad).toHaveBeenCalledOnce();
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
