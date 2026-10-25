import { webcrypto } from "node:crypto";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { coreCommand } from "../api/core";
import { SingleOriginalImport } from "../components/SingleOriginalImport";
vi.mock("../api/core", () => ({ coreCommand: vi.fn() }));
const bytes = new TextEncoder().encode("第一份资料\n原件保留");
let hash: string;
function file(name = "第一份资料.md") {
  const value = new File([bytes], name, { type: "text/markdown" });
  Object.defineProperty(value, "arrayBuffer", { value: vi.fn(async () => bytes.slice().buffer) });
  return value;
}
function pick(value = file()) { fireEvent.change(screen.getByLabelText("导入原件", { exact: true }), { target: { files: [value] } }); }
beforeEach(async () => { vi.stubGlobal("crypto", webcrypto); hash = Buffer.from(await webcrypto.subtle.digest("SHA-256", bytes)).toString("hex"); vi.mocked(coreCommand).mockResolvedValue({ source_id: "source-exact", sha256: hash, duplicate: false }); });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.clearAllMocks(); });

describe("single original import — SIMULATED canonical custody", () => {
  it("submits exact file bytes and exposes an explicit next action only after its matching receipt", async () => {
    const imported = vi.fn(), open = vi.fn(); render(<SingleOriginalImport onImported={imported} onOpenSource={open} />); pick();
    await screen.findByText(/原件已保存在本地/);
    expect(coreCommand).toHaveBeenCalledTimes(1); expect(coreCommand).toHaveBeenCalledWith("source_import", { body: { name: "第一份资料.md", content_base64: Buffer.from(bytes).toString("base64") } });
    expect(imported).toHaveBeenCalledTimes(1); expect(imported).toHaveBeenCalledWith({ source_id: "source-exact", sha256: hash, duplicate: false });
    expect(open).not.toHaveBeenCalled(); fireEvent.click(screen.getByRole("button", { name: "打开刚导入的原件" }));
    expect(open).toHaveBeenCalledTimes(1); expect(open).toHaveBeenCalledWith("source-exact");
    expect(screen.getByLabelText("导入原件", { exact: true })).toBeEnabled();
  });
  it("hash mismatch keeps the exact original request for retry and never enables conversion or a false success", async () => {
    const imported = vi.fn(), open = vi.fn();
    vi.mocked(coreCommand).mockResolvedValueOnce({ source_id: "wrong", sha256: "f".repeat(64), duplicate: false });
    render(<SingleOriginalImport onImported={imported} onOpenSource={open} />); pick();
    expect(await screen.findByRole("alert")).toHaveTextContent("导入结果尚未确认");
    expect(imported).not.toHaveBeenCalled(); expect(screen.queryByRole("button", { name: "打开刚导入的原件" })).toBeNull();
    expect(screen.getByLabelText("导入原件", { exact: true })).toBeDisabled();
    const first = vi.mocked(coreCommand).mock.calls[0];
    fireEvent.click(screen.getByRole("button", { name: "重试这一次原件导入" })); await screen.findByRole("button", { name: "打开刚导入的原件" });
    expect(vi.mocked(coreCommand).mock.calls).toEqual([first, first]);
    expect(imported).toHaveBeenCalledTimes(1); expect(open).not.toHaveBeenCalled();
  });
  it.each([{}, { source_id: "", sha256: "a".repeat(64), duplicate: false }, { source_id: "source-exact", sha256: "invalid", duplicate: false }, { source_id: "source-exact", duplicate: false }])("incomplete receipt cannot mark import successful: %j", async receipt => {
    const imported = vi.fn(); vi.mocked(coreCommand).mockResolvedValue(receipt); render(<SingleOriginalImport onImported={imported} />); pick();
    await screen.findByRole("alert"); expect(imported).not.toHaveBeenCalled(); expect(screen.queryByText(/已确认原件：/)).toBeNull();
  });
  it("does not read or send an oversized file, and allows selecting a smaller file", async () => {
    const large = file(); Object.defineProperty(large, "size", { value: 64 * 1024 * 1024 + 1 }); render(<SingleOriginalImport />); pick(large);
    expect(screen.getByRole("status")).toHaveTextContent("未发起导入"); expect(large.arrayBuffer).not.toHaveBeenCalled(); expect(coreCommand).not.toHaveBeenCalled();
    expect(screen.getByLabelText("导入原件", { exact: true })).toBeEnabled(); pick(); await screen.findByText(/已确认原件：/); expect(coreCommand).toHaveBeenCalledTimes(1);
  });
  it("does not send partial file reads", async () => {
    const partial = file(); Object.defineProperty(partial, "size", { value: bytes.byteLength + 1 }); render(<SingleOriginalImport />); pick(partial);
    await screen.findByText(/文件暂时无法完整读取，未发起导入/); expect(coreCommand).not.toHaveBeenCalled();
  });
  it("synchronous repeated file selection and retry clicks cannot launch parallel requests", async () => {
    let release!: (value: unknown) => void;
    vi.mocked(coreCommand).mockRejectedValueOnce(new Error("lost ACK")).mockImplementationOnce(() => new Promise(resolve => { release = resolve; }) as never);
    render(<SingleOriginalImport />); pick(); pick(file("第二份.md")); await screen.findByRole("alert"); expect(coreCommand).toHaveBeenCalledTimes(1);
    const retry = screen.getByRole("button", { name: "重试这一次原件导入" }); fireEvent.click(retry); fireEvent.click(retry);
    await waitFor(() => expect(coreCommand).toHaveBeenCalledTimes(2));
    await act(async () => { release({ source_id: "source-exact", sha256: hash, duplicate: true }); });
    expect(screen.getByText(/这份原件已在本地/)).toBeInTheDocument();
    expect(vi.mocked(coreCommand).mock.calls[1]).toEqual(vi.mocked(coreCommand).mock.calls[0]);
  });
  it("late import acknowledgements after unmount cannot navigate or refresh another workspace", async () => {
    let release!: (value: unknown) => void; const imported = vi.fn();
    vi.mocked(coreCommand).mockImplementation(() => new Promise(resolve => { release = resolve; }) as never);
    const mounted = render(<SingleOriginalImport onImported={imported} />); pick(); await waitFor(() => expect(coreCommand).toHaveBeenCalledTimes(1)); mounted.unmount();
    await act(async () => { release({ source_id: "source-exact", sha256: hash, duplicate: false }); }); expect(imported).not.toHaveBeenCalled();
  });
  it("keeps the navigation guard dirty while the exact original request remains unconfirmed", async () => {
    const events: boolean[] = []; const listener = (event: Event) => events.push((event as CustomEvent<{ dirty: boolean }>).detail.dirty);
    window.addEventListener("archeaxis-draft-dirty", listener);
    try { vi.mocked(coreCommand).mockRejectedValueOnce(new Error("lost ACK")); const mounted = render(<SingleOriginalImport />); pick(); await screen.findByRole("alert"); expect(events.at(-1)).toBe(true);
      fireEvent.click(screen.getByRole("button", { name: "重试这一次原件导入" })); await screen.findByText(/已确认原件：/); expect(events.at(-1)).toBe(false); mounted.unmount(); expect(events.at(-1)).toBe(false);
    } finally { window.removeEventListener("archeaxis-draft-dirty", listener); }
  });
});
