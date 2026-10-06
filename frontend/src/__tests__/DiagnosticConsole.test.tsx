import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DiagnosticConsole, RawReceiptButton } from "../components/DiagnosticConsole";
import { clearDiagnostics } from "../presentation/diagnostics";

beforeEach(() => { clearDiagnostics(); vi.restoreAllMocks(); });

// The reading surfaces no longer print raw backend payloads, so the console must really carry them.
describe("diagnostic console", () => {
  it("starts empty and says where a payload would go", () => {
    render(<DiagnosticConsole />);
    expect(screen.getByLabelText("诊断控制台")).toHaveTextContent("暂无原始回执");
  });

  it("lists a published payload verbatim and mirrors it to the developer console", async () => {
    const debug = vi.spyOn(console, "debug").mockImplementation(() => {});
    const user = userEvent.setup();
    render(<><RawReceiptButton label="损失、引擎与处理记录" payload={{ engine: "openpyxl", engine_version: "3.1.5" }} /><DiagnosticConsole /></>);
    await user.click(screen.getByRole("button", { name: /损失、引擎与处理记录/ }));
    expect(debug.mock.calls.some(([, label, payload]) => label === "损失、引擎与处理记录" && JSON.stringify(payload).includes("openpyxl"))).toBe(true);
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
