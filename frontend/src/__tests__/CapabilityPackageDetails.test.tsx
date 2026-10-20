import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, within } from "@testing-library/react";
import { CanonicalCapabilitiesSpace } from "../spaces/CanonicalCapabilitiesSpace";
import { CAPABILITY_PACKAGE_DETAILS } from "../api/generated/capability-package-details";
import { scopedReadiness } from "../test/fixtures/readiness";
const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));
vi.mock("../components/DiagnosticConsole", () => ({ RawReceiptButton: ({ label }: { label: string }) => <button>{label}</button> }));

describe("page17 consumes verified manifest declaration without runtime authority", () => {
  beforeEach(() => {
    bridge.call.mockReset();
    bridge.call.mockImplementation(async (_op: string, payload: { body: { scope: string; operations: string[] } }) => scopedReadiness(payload.body));
  });
  it("shows actual byte identity declaration only for its exact selected CAP", async () => {
    await act(async () => { render(<CanonicalCapabilitiesSpace onNavigate={vi.fn()} selectedCapabilityId="CAP-0020" />); });
    const pack = screen.getByRole("article", { name: "包说明 archeaxis.pdf-extract" });
    expect(pack).toHaveTextContent("声明校验通过");
    expect(pack).toHaveTextContent("pymupdf");
    expect(pack).toHaveTextContent("不证明关联引擎内置、已安装或可用");
    expect(within(pack).getByRole("button", { name: /包说明身份与来源/ })).toBeInTheDocument();
    expect(CAPABILITY_PACKAGE_DETAILS.entries[0].identity.sha256).toMatch(/^[a-f0-9]{64}$/);
    expect(bridge.call).toHaveBeenCalledTimes(1);
    expect(bridge.call.mock.calls[0][0]).toBe("operation_readiness");
  });
  it("keeps unknown license, authenticity, qualification and runtime distinct", async () => {
    await act(async () => { render(<CanonicalCapabilitiesSpace onNavigate={vi.fn()} selectedCapabilityId="CAP-0020" />); });
    const pack = screen.getByRole("article", { name: "包说明 archeaxis.pdf-extract" });
    expect(pack).toHaveTextContent("许可声明：未知 · 审查尚未完成");
    expect(pack).toHaveTextContent("发布者真实性尚未验证");
    expect(pack).toHaveTextContent("业务验证尚未完成 · 当前运行状态未知");
    expect(pack).toHaveTextContent("均未授权执行");
    expect(within(pack).queryByRole("button", { name: /安装|执行|启用|重试/ })).not.toBeInTheDocument();
  });
  it("does not borrow another CAP manifest and clears it on selection change", async () => {
    let view!: ReturnType<typeof render>;
    await act(async () => { view = render(<CanonicalCapabilitiesSpace onNavigate={vi.fn()} selectedCapabilityId="CAP-0020" />); });
    expect(screen.getByRole("article", { name: "包说明 archeaxis.pdf-extract" })).toBeInTheDocument();
    await act(async () => { view.rerender(<CanonicalCapabilitiesSpace onNavigate={vi.fn()} selectedCapabilityId="CAP-0090" />); });
    expect(screen.queryByRole("article", { name: "包说明 archeaxis.pdf-extract" })).not.toBeInTheDocument();
    expect(screen.getByText(/此能力尚无已验证的包说明/)).toHaveTextContent("许可、业务验证与运行状态均待核对");
  });
  it("has no manifest display or additional package request before a CAP is selected", async () => {
    await act(async () => { render(<CanonicalCapabilitiesSpace onNavigate={vi.fn()} />); });
    expect(screen.queryByRole("region", { name: "能力包声明" })).not.toBeInTheDocument();
    expect(bridge.call).not.toHaveBeenCalled();
  });
});
