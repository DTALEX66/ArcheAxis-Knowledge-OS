import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { ConsoleWindow } from "../components/ConsoleWindow";
import { WorkspaceContextMenu } from "../components/WorkspaceContextMenu";

const native = vi.hoisted(() => ({ create: vi.fn() }));
vi.mock("@tauri-apps/api/menu", () => ({ Menu: { new: native.create } }));
const props = () => ({ onPage: vi.fn(), onCompanion: vi.fn(), onInspector: vi.fn(), companionOpen: true, inspectorOpen: false });
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); native.create.mockReset(); delete (window as unknown as Record<string, unknown>).__TAURI_INTERNALS__; });

describe("workspace context commands (SIMULATED; native popup is mocked)", () => {
  it("delegates navigation and panel controls and supports keyboard dismissal", async () => {
    const handlers = props();
    render(<ConsoleWindow><button>工作区</button><WorkspaceContextMenu {...handlers}/></ConsoleWindow>);
    const target = screen.getByRole("button", { name: "工作区" }); target.focus();
    const event = new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: 30, clientY: 40 });
    fireEvent(target, event); expect(event.defaultPrevented).toBe(true);
    expect(screen.getByRole("menu", { name: "当前位置操作" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("menuitem", { name: "查看全部能力" }));
    await waitFor(() => expect(handlers.onPage).toHaveBeenCalledWith("17"));
    fireEvent.keyDown(target, { key: "F10", shiftKey: true });
    fireEvent.keyDown(document.activeElement!, { key: "End" });
    expect(screen.getByRole("menuitem", { name: "显示来源检查器" })).toHaveFocus();
    fireEvent.keyDown(document.activeElement!, { key: "ArrowDown" });
    expect(screen.getByRole("menuitem", { name: "导入资料…" })).toHaveFocus();
    fireEvent.keyDown(document.activeElement!, { key: "Escape" });
    expect(screen.queryByRole("menu")).not.toBeInTheDocument(); expect(target).toHaveFocus();
  });

  it("uses only the clicked document's existing command and respects its latest disabled state", async () => {
    const first = vi.fn(), second = vi.fn();
    render(<><article data-context-surface="document"><span>文档甲</span><button data-context-command="read" onClick={first}>打开阅读</button></article><article data-context-surface="document"><span>文档乙</span><button data-context-command="read" onClick={second}>打开阅读</button></article><WorkspaceContextMenu {...props()}/></>);
    fireEvent.contextMenu(screen.getByText("文档乙"));
    fireEvent.click(screen.getByRole("menuitem", { name: "打开阅读" }));
    await waitFor(() => expect(second).toHaveBeenCalledOnce()); expect(first).not.toHaveBeenCalled();
    fireEvent.contextMenu(screen.getByText("文档乙"));
    screen.getAllByRole("button", { name: "打开阅读" })[1].setAttribute("disabled", "");
    fireEvent.click(screen.getByRole("menuitem", { name: "打开阅读" }));
    await Promise.resolve(); expect(second).toHaveBeenCalledOnce();
  });

  it("restores text selection before editing, keeps readonly inputs safe and excludes password copying", async () => {
    const command = vi.fn(() => true); Object.defineProperty(document, "execCommand", { configurable: true, value: command });
    render(<><textarea aria-label="草稿" defaultValue="保留文字"/><input aria-label="只读" readOnly defaultValue="来源"/><input aria-label="密码" type="password" defaultValue="secret"/><WorkspaceContextMenu {...props()}/></>);
    const draft = screen.getByLabelText("草稿") as HTMLTextAreaElement; draft.focus(); draft.setSelectionRange(1, 3);
    fireEvent.contextMenu(draft); fireEvent.click(screen.getByRole("menuitem", { name: "复制" }));
    await waitFor(() => expect(command).toHaveBeenCalledWith("copy")); expect(draft).toHaveFocus(); expect([draft.selectionStart, draft.selectionEnd]).toEqual([1, 3]);
    fireEvent.contextMenu(screen.getByLabelText("只读")); expect(screen.queryByRole("menuitem", { name: "剪切" })).not.toBeInTheDocument(); expect(screen.queryByRole("menuitem", { name: "粘贴" })).not.toBeInTheDocument();
    const password = screen.getByLabelText("密码") as HTMLInputElement; password.setSelectionRange(0, 6);
    fireEvent.contextMenu(password); expect(screen.queryByRole("menuitem", { name: "复制" })).not.toBeInTheDocument(); expect(screen.queryByRole("menuitem", { name: "剪切" })).not.toBeInTheDocument();
  });

  it("does not expose background navigation through a modal and closes on outside input", () => {
    render(<><div role="dialog" aria-modal="true" aria-label="保存确认"><div data-context-surface="editor"><span>正文</span><button data-context-command="save" disabled>保存草稿</button></div></div><WorkspaceContextMenu {...props()}/></>);
    fireEvent.contextMenu(screen.getByText("正文"));
    expect(screen.getByRole("menuitem", { name: "保存草稿" })).toBeDisabled(); expect(screen.queryByRole("menuitem", { name: "查看全部能力" })).not.toBeInTheDocument();
    fireEvent.pointerDown(document.body); expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("bounds the fallback at the viewport edges", () => {
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({ width: 224, height: 300, top: 0, left: 0, right: 224, bottom: 300, x: 0, y: 0, toJSON() {} });
    render(<><button>工作区</button><WorkspaceContextMenu {...props()}/></>);
    fireEvent.contextMenu(screen.getByText("工作区"), { clientX: window.innerWidth, clientY: window.innerHeight });
    const menu = screen.getByRole("menu"); expect(menu.style.left).toBe(`${window.innerWidth - 232}px`); expect(menu.style.top).toBe(`${window.innerHeight - 308}px`);
  });

  it("keeps native resources alive after popup resolves and releases them before replacement/unmount", async () => {
    (window as unknown as Record<string, unknown>).__TAURI_INTERNALS__ = {};
    const first = { popup: vi.fn().mockResolvedValue(undefined), close: vi.fn().mockResolvedValue(undefined) }, second = { popup: vi.fn().mockResolvedValue(undefined), close: vi.fn().mockResolvedValue(undefined) };
    native.create.mockResolvedValueOnce(first).mockResolvedValueOnce(second);
    const handlers = props();
    const view = render(<><input aria-label="草稿" defaultValue="原文"/><WorkspaceContextMenu {...handlers}/></>);
    const input = screen.getByLabelText("草稿") as HTMLInputElement; input.setSelectionRange(0, 2); fireEvent.contextMenu(input, { clientX: 10, clientY: 20 });
    await waitFor(() => expect(first.popup).toHaveBeenCalledOnce()); expect(first.close).not.toHaveBeenCalled();
    const options = native.create.mock.calls[0][0];
    expect(options.items.some((item: { item?: string }) => item.item === "Copy")).toBe(true);
    expect(options.items.some((item: { item?: string }) => item.item === "Undo")).toBe(false);
    options.items.find((item: { id?: string }) => item.id === "capabilities").action();
    await waitFor(() => expect(handlers.onPage).toHaveBeenCalledWith("17"));
    fireEvent.contextMenu(input); await waitFor(() => expect(second.popup).toHaveBeenCalledOnce()); expect(first.close).toHaveBeenCalledOnce();
    view.unmount(); expect(second.close).toHaveBeenCalledOnce();
  });

  it("falls back to working application actions when native menu creation fails", async () => {
    (window as unknown as Record<string, unknown>).__TAURI_INTERNALS__ = {};
    native.create.mockRejectedValueOnce(new Error("unavailable")); const handlers = props();
    render(<><button>工作区</button><WorkspaceContextMenu {...handlers}/></>);
    fireEvent.contextMenu(screen.getByText("工作区"));
    const menu = await screen.findByRole("menu"); fireEvent.click(within(menu).getByRole("menuitem", { name: "收起小栖" }));
    await waitFor(() => expect(handlers.onCompanion).toHaveBeenCalledOnce());
  });
});
