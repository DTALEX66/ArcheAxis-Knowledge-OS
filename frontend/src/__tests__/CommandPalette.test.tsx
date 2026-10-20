import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CommandPalette } from "../components/CommandPalette";
import { EFFECTIVE_NAVIGATION_ENTRIES } from "../presentation/navigation";
import { SPACES } from "../spaces/spaces";

// AXW-UI-804: CommandPalette - the global command dialog. These tests pin the
// keyboard entry points, the assistive-tech containment while it is open, the
// filter contract, and that selecting an option navigates then closes.
function renderPalette(onNavigate: (id: (typeof SPACES)[number]["id"]) => void = () => {}) {
  render(<CommandPalette onNavigate={onNavigate} />);
  return screen.getByRole("button", { name: "打开全局命令" });
}

describe("CommandPalette", () => {
  it.each(["removed","hidden","inert","css-hidden"])("returns to the visible global trigger when navigation leaves the opener %s", async mode=>{
    function Pages(){const [left,setLeft]=useState(false);return <>
      {!(left&&mode==="removed")&&<div hidden={left&&mode==="hidden"} {...(left&&mode==="inert"?{inert:""}:{})} style={{display:left&&mode==="css-hidden"?"none":undefined}}><input aria-label="旧页草稿"/></div>}
      <CommandPalette onNavigate={()=>setLeft(true)}/>
    </>;}
    render(<Pages/>);const user=userEvent.setup();
    const input=screen.getByRole("textbox",{name:"旧页草稿"});input.focus();
    await user.keyboard("{Control>}k{/Control}");
    const option=within(screen.getByRole("listbox",{name:"可用命令"})).getAllByRole("option").find(n=>n.dataset.entryId==="space:workspace")!;
    option.focus();await user.keyboard("{Enter}");
    await waitFor(()=>expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.getByRole("button",{name:"打开全局命令"})).toHaveFocus();
  });
  it("returns Escape to the still-visible draft and preserves its text",async()=>{
    render(<><input aria-label="当前草稿" defaultValue="保留文字"/><CommandPalette onNavigate={vi.fn()}/></>);
    const draft=screen.getByRole("textbox",{name:"当前草稿"});draft.focus();const user=userEvent.setup();
    await user.keyboard("{Control>}k{/Control}");await user.keyboard("{Escape}");
    await waitFor(()=>expect(draft).toHaveFocus());expect(draft).toHaveValue("保留文字");
  });
  it("consumes each external open request once and allows a later request to reopen", () => {
    const onNavigate = vi.fn();
    const view = render(<CommandPalette onNavigate={onNavigate} openRequest={0} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    view.rerender(<CommandPalette onNavigate={onNavigate} openRequest={1} />);
    expect(screen.getByRole("dialog", {name:"全局命令"})).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", {name:"关闭全局命令"}));
    view.rerender(<CommandPalette onNavigate={onNavigate} openRequest={1} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    view.rerender(<CommandPalette onNavigate={onNavigate} openRequest={2} />);
    expect(screen.getByRole("dialog", {name:"全局命令"})).toBeInTheDocument();
  });
  it("advertises its keyboard shortcut on the trigger", () => {
    const trigger = renderPalette();
    expect(trigger).toHaveAttribute("aria-keyshortcuts", "Control+K");
  });

  it("opens on Ctrl+K and hides the app shell from assistive technology while open", () => {
    const shell = document.createElement("div");
    shell.className = "app-shell";
    document.body.appendChild(shell);
    try {
      renderPalette();
      fireEvent.keyDown(window, { key: "k", ctrlKey: true });
      expect(screen.getByRole("dialog", { name: "全局命令" })).toBeInTheDocument();
      expect(shell).toHaveAttribute("inert");
      expect(shell).toHaveAttribute("aria-hidden", "true");
    } finally {
      shell.remove();
    }
  });

  it("closes on Escape", () => {
    renderPalette();
    fireEvent.click(screen.getByRole("button", { name: "打开全局命令" }));
    expect(screen.getByRole("dialog", { name: "全局命令" })).toBeInTheDocument();
    // The palette is a Radix dialog now, whose dismiss layer listens on the document;
    // an event fired on window never reaches it.
    fireEvent.keyDown(screen.getByRole("searchbox", { name: "搜索空间或命令" }), { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("lists every space as an option when the query is empty", () => {
    renderPalette();
    fireEvent.click(screen.getByRole("button", { name: "打开全局命令" }));
    const listbox = screen.getByRole("listbox", { name: "可用命令" });
    const options = within(listbox).getAllByRole("option");
    expect(options).toHaveLength(EFFECTIVE_NAVIGATION_ENTRIES.length);
    for (const space of SPACES) {
      expect(options.some((option) => option.textContent?.includes(space.label))).toBe(true);
    }
  });

  it("drops to the empty message when nothing matches the query", () => {
    renderPalette();
    fireEvent.click(screen.getByRole("button", { name: "打开全局命令" }));
    fireEvent.change(screen.getByRole("searchbox", { name: "搜索空间或命令" }), {
      target: { value: "zzz-no-such-space" },
    });
    expect(screen.getByText("没有匹配的可用空间")).toBeInTheDocument();
    expect(screen.queryByRole("option")).not.toBeInTheDocument();
  });

  it("navigates to the selected space and closes the dialog", () => {
    const onNavigate = vi.fn();
    render(<CommandPalette onNavigate={onNavigate} />);
    fireEvent.click(screen.getByRole("button", { name: "打开全局命令" }));
    const listbox = screen.getByRole("listbox", { name: "可用命令" });
    const workspaceCommand = within(listbox).getAllByRole("option").find(option => option.getAttribute("data-entry-id") === "space:workspace");
    expect(workspaceCommand).toBeDefined();
    fireEvent.click(workspaceCommand!);
    expect(onNavigate).toHaveBeenCalledTimes(1);
    expect(onNavigate).toHaveBeenCalledWith(SPACES[0].id);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
