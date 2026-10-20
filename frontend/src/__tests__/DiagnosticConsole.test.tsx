import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DiagnosticCenter, DiagnosticConsole, RawReceiptButton } from "../components/DiagnosticConsole";
import { clearDiagnostics, resetDiagnostics } from "../presentation/diagnostics";
import { AaosDialog } from "../design-system/AaosPrimitives";
import { useState } from "react";

beforeEach(() => { clearDiagnostics(); vi.restoreAllMocks(); });

// The reading surfaces no longer print raw backend payloads, so the console must really carry them.
describe("diagnostic console", () => {
  it("closes only the diagnostic above an open picker and returns to its exact trigger", async () => {
    resetDiagnostics();
    const user=userEvent.setup();
    function Picker() {
      const [open,setOpen]=useState(true);
      return <><DiagnosticCenter/><AaosDialog title="保留的引用选择" description="输入保持" open={open} onOpenChange={setOpen}><input aria-label="引用关键词" defaultValue="原输入"/><RawReceiptButton label="嵌套原始记录" payload={{identity:"second"}}/></AaosDialog></>;
    }
    render(<Picker/>);
    const trigger=screen.getByRole("button",{name:"查看诊断详情：嵌套原始记录"});
    await user.click(trigger);
    const diagnostic=screen.getByRole("dialog",{name:"运行诊断"});
    await waitFor(()=>expect(within(diagnostic).getByRole("button",{name:"关闭运行诊断"})).toHaveFocus());
    await user.keyboard("{Escape}");
    await waitFor(()=>expect(screen.queryByRole("dialog",{name:"运行诊断"})).not.toBeInTheDocument());
    expect(screen.getByRole("dialog",{name:"保留的引用选择"})).toBeInTheDocument();
    expect(screen.getByRole("textbox",{name:"引用关键词"})).toHaveValue("原输入");
    await waitFor(()=>expect(trigger).toHaveFocus());
    await user.keyboard("{Escape}");
    await waitFor(()=>expect(screen.queryByRole("dialog",{name:"保留的引用选择"})).not.toBeInTheDocument());
  });

  it("keeps the focused diagnostic open for an IME Escape", async () => {
    resetDiagnostics();
    const user=userEvent.setup();
    render(<><DiagnosticCenter/><RawReceiptButton label="组合输入记录" payload={{raw:true}}/></>);
    await user.click(screen.getByRole("button",{name:"查看诊断详情：组合输入记录"}));
    const diagnostic=screen.getByRole("dialog",{name:"运行诊断"});
    const close=within(diagnostic).getByRole("button",{name:"关闭运行诊断"});
    await waitFor(()=>expect(close).toHaveFocus());
    fireEvent.keyDown(close,{key:"Escape",code:"Escape",isComposing:true});
    expect(screen.getByRole("dialog",{name:"运行诊断"})).toBeInTheDocument();
  });

  it("starts empty and says where a payload would go", () => {
    render(<DiagnosticConsole />);
    expect(screen.getByLabelText("诊断控制台")).toHaveTextContent("暂无原始回执");
  });

  it("lists a published payload verbatim without copying it to the developer console", async () => {
    const debug = vi.spyOn(console, "debug").mockImplementation(() => {});
    const user = userEvent.setup();
    render(<><RawReceiptButton label="损失、引擎与处理记录" payload={{ engine: "openpyxl", engine_version: "3.1.5" }} /><DiagnosticConsole /></>);
    await user.click(screen.getByRole("button", { name: /损失、引擎与处理记录/ }));
    expect(debug).not.toHaveBeenCalled();
    const console_ = screen.getByLabelText("诊断控制台");
    expect(console_).toHaveTextContent("损失、引擎与处理记录");
    expect(console_).toHaveTextContent("openpyxl");
    expect(console_).toHaveTextContent("3.1.5");
  });

  it("clears entries on request without touching what was already read", async () => {
    vi.spyOn(console, "debug").mockImplementation(() => {});
    const user = userEvent.setup();
    render(<><RawReceiptButton label="导出格式与损失回执" payload={{ files: ["manifest.json"] }} /><DiagnosticConsole /></>);
    await user.click(screen.getByRole("button", { name: /导出格式与损失回执/ }));
    await user.click(screen.getByRole("button", { name: "清空诊断" }));
    expect(screen.getByLabelText("诊断控制台")).toHaveTextContent("暂无原始回执");
  });
});
