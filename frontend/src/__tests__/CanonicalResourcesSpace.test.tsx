import { act, render, renderHook, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { basename, resolve } from "node:path";
import { CanonicalResourcesSpace, readCapabilityDecision, readResourceHandshake } from "../spaces/CanonicalResourcesSpace";
import { RESOURCE_CATALOG } from "../api/generated/resource-catalog";
import { useDiagnosticState } from "../presentation/diagnostics";

const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));
vi.mock("../templates/TemplateWorkspace", () => ({ TemplateWorkspace: ({ onDirtyChange }: { onDirtyChange?: (dirty: boolean) => void }) => <section aria-label="真实模板回调测试"><button onClick={() => onDirtyChange?.(true)}>产生模板草稿</button><button onClick={() => onDirtyChange?.(false)}>完成模板处理</button></section> }));
const repository = basename(process.cwd()) === "frontend" ? resolve(process.cwd(), "..") : process.cwd();

describe("resource source catalog", () => {
  beforeEach(() => { bridge.call.mockReset(); bridge.call.mockResolvedValue({ capabilities: [] }); });

  it("preserves all68 original envelopes/all115conflicts and actual input byte bindings", () => {
    const original = JSON.parse(readFileSync(resolve(repository, "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json"), "utf8"));
    expect(RESOURCE_CATALOG.entries.map(entry => entry.original_surface)).toEqual(original.entries);
    expect(RESOURCE_CATALOG.entries).toHaveLength(68);
    expect(new Set(RESOURCE_CATALOG.entries.map(entry => entry.stable_key)).size).toBe(68);
    expect(RESOURCE_CATALOG.entries.reduce((sum, entry) => sum + (entry.original_surface.conflicts as unknown[]).length, 0)).toBe(115);
    for (const source of RESOURCE_CATALOG.sources) expect(createHash("sha256").update(readFileSync(resolve(repository, source.path))).digest("hex")).toBe(source.sha256);
  });

  it("shows allseven classes and donor modes without installation or qualification claims", async () => {
    render(<CanonicalResourcesSpace/>);
    await userEvent.setup().click(screen.getByRole("tab",{name:"接入来源与运行设置"}));
    await screen.findByText(/宿主返回空能力列表/);
    const directory = screen.getByRole("region", { name: "资源目录" });
    expect(within(directory).getAllByRole("button", { name: / · / })).toHaveLength(68);
    expect(screen.getByLabelText("来源类别").querySelectorAll("option")).toHaveLength(8);
    expect(within(directory).queryByRole("button", { name: /^(安装|升级|启用)(?:\s|$)/ })).not.toBeInTheDocument();
    expect(bridge.call).toHaveBeenCalledTimes(1);
    expect(bridge.call).toHaveBeenCalledWith("capabilities_list");
  });

  it("keeps source fingerprints in diagnostics while preserving the exact evidence", async () => {
    const entry = RESOURCE_CATALOG.entries.find(item => item.qualification.evidence.version.source_refs.length > 0)!;
    render(<CanonicalResourcesSpace/>);
    await userEvent.setup().click(screen.getByRole("tab",{name:"接入来源与运行设置"}));
    await screen.findByText(/宿主返回空能力列表/);
    const directory = screen.getByRole("region", { name: "资源目录" });
    const button = within(directory).getAllByRole("button").find(item => item.querySelector("strong")?.textContent === entry.display_names[0])!;
    await userEvent.setup().click(button);
    const evidence = screen.getByRole("region", { name: "版本证据" });
    const diagnostics = renderHook(() => useDiagnosticState());
    expect(evidence).not.toHaveTextContent(entry.qualification.evidence.version.source_refs[0].sha256);
    await userEvent.setup().click(within(evidence).getByRole("button", { name: /版本证据来源与原始登记/ }));
    expect(diagnostics.result.current.entries[0].payload).toEqual(entry.qualification.evidence.version);
  });

  it("searches the lastentry and原冲突, retains declared reasons and frozen activation", async () => {
    const user = userEvent.setup(); render(<CanonicalResourcesSpace/>);
    await userEvent.setup().click(screen.getByRole("tab",{name:"接入来源与运行设置"}));
    await user.type(screen.getByRole("textbox", { name: "查找资源与原冲突" }), "xyflow");
    await user.click(screen.getByRole("button", { name: /xyflow|XYFlow|xyFlow|React Flow/i }));
    const details = screen.getByRole("complementary", { name: "资源来源详情" });
    expect(details).toHaveTextContent("未来候选");
    expect(within(details).getByRole("region", { name: "启用条件" })).toBeInTheDocument();
    await user.clear(screen.getByRole("textbox", { name: "查找资源与原冲突" }));
    await user.type(screen.getByRole("textbox", { name: "查找资源与原冲突" }), "capability-id-is-not-a-declared-route");
    expect(screen.getByText(/筛选结果/)).not.toHaveTextContent("筛选结果 0 项");
  });

  it("shows live route permission separately and does not promote donor qualification", async () => {
    bridge.call.mockResolvedValue({ capabilities: [{ capability: "media.transcribe", enabled: false, health: "handshake_ready" }] });
    render(<CanonicalResourcesSpace/>);
    await userEvent.setup().click(screen.getByRole("tab",{name:"接入来源与运行设置"}));
    await screen.findByText(/已读取 1 项能力状态/);
    await userEvent.setup().click(screen.getByRole("button", { name: /faster-whisper.* · /i }));
    const relation = screen.getByRole("region", { name: "资源连接状态" });
    expect(relation).toHaveTextContent("已禁用");
    expect(relation).toHaveTextContent("尚未确认");
    expect(relation).toHaveTextContent("功能已连接不代表");
    const capabilities = screen.getByRole("region", { name: "当前可用能力" });
    expect(capabilities).toHaveTextContent("音频转写 · 使用权限 已禁用 · 连接状态 连接已响应，运行尚未确认");
    expect(capabilities).not.toHaveTextContent("media.transcribe");
    expect(capabilities).not.toHaveTextContent("handshake_ready");
    expect(within(screen.getByRole("complementary", { name: "资源来源详情" })).queryByRole("button", { name: /^(启用|安装)(?:\s|$)/ })).not.toBeInTheDocument();
  });

  it("labels unknown permission and health honestly while retaining their exact diagnostic values", async () => {
    const capabilities = [{ capability: "media.video", health: "future_health" }];
    bridge.call.mockResolvedValue({ capabilities });
    render(<CanonicalResourcesSpace/>);
    await userEvent.setup().click(screen.getByRole("tab",{name:"接入来源与运行设置"}));
    const region = screen.getByRole("region", { name: "当前可用能力" });
    await within(region).findByText(/视频内容处理 · 使用权限 尚未确认 · 连接状态 尚未确认/);
    expect(within(region).queryByRole("button", { name: /^(启用|禁用)/ })).not.toBeInTheDocument();
    expect(region).not.toHaveTextContent(/media\.video|future_health|UNKNOWN/);
    const diagnostics = renderHook(useDiagnosticState);
    await userEvent.setup().click(within(region).getByRole("button", { name: "状态与诊断：能力运行详细信息" }));
    expect(diagnostics.result.current.entries[0].payload).toEqual({ state: "read", rows: capabilities });
    expect(bridge.call.mock.calls).toEqual([["capabilities_list"]]);
  });

  it("keeps the complete catalog when handshake is unavailable or malformed", async () => {
    bridge.call.mockRejectedValue(new Error("offline")); render(<CanonicalResourcesSpace/>);
    await userEvent.setup().click(screen.getByRole("tab",{name:"接入来源与运行设置"}));
    await screen.findByRole("alert"); expect(screen.getByRole("alert")).toHaveTextContent("无法确认当前可用功能");
    const diagnostics=renderHook(useDiagnosticState);await userEvent.setup().click(screen.getByRole("button",{name:"状态与诊断：能力运行详细信息"}));
    expect(diagnostics.result.current.entries[0].payload).toMatchObject({state:"failed"});
    expect(within(screen.getByRole("region", { name: "资源目录" })).getAllByRole("button", { name: / · / })).toHaveLength(68);
    bridge.call.mockResolvedValue({ capabilities: [{ capability: "media.video" }, { capability: "media.video" }] });
    await userEvent.setup().click(screen.getByRole("button", { name: "刷新本机可用功能" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("无法确认当前可用功能"));
    expect(screen.queryByText(/已读回 2 条/)).not.toBeInTheDocument();
  });

  it("ignores an older successful response after the latest failed read", async () => {
    let resolveOld!: (value: unknown) => void;
    bridge.call.mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve; })).mockRejectedValueOnce(new Error("latest offline"));
    render(<CanonicalResourcesSpace/>);
    await userEvent.setup().click(screen.getByRole("tab",{name:"接入来源与运行设置"}));
    await userEvent.setup().click(screen.getByRole("button", { name: "刷新本机可用功能" }));
    await screen.findByRole("alert");
    await act(async () => resolveOld({ capabilities: [{ capability: "old", enabled: true }] }));
    expect(screen.getByRole("alert")).toHaveTextContent("无法确认当前可用功能");
    expect(screen.queryByText(/old · 权限/)).not.toBeInTheDocument();
  });

  it("changes one explicit setting and confirms a fresh readback rather than optimistic success", async () => {
    const basis = "the workspace's capability record; an absent record means enabled";
    let enabled = true;
    bridge.call.mockImplementation(async (operation, payload) => {
      if (operation === "capability_set_enabled") {
        enabled = payload.enabled;
        return { capability: { capability: "text.extract", enabled, enabled_basis: basis } };
      }
      return { capabilities: [{ capability: "text.extract", enabled, enabled_basis: basis }] };
    });
    render(<CanonicalResourcesSpace/>);
    await userEvent.setup().click(screen.getByRole("tab",{name:"接入来源与运行设置"}));
    await userEvent.setup().click(await screen.findByRole("button", { name: "禁用文字解析" }));
    await screen.findByText(/文字解析已禁用，工作区设置已确认/);
    expect(bridge.call).toHaveBeenCalledWith("capability_set_enabled", { capability: "text.extract", enabled: false });
    await userEvent.setup().click(screen.getByRole("button", { name: "启用文字解析" }));
    await screen.findByText(/文字解析已启用，工作区设置已确认/);
    expect(bridge.call.mock.calls.filter(([op]) => op === "capabilities_list")).toHaveLength(3);
  });

  it("does not repeat an uncertain write; reads the persisted decision even when the ACK is lost", async () => {
    const basis = "the workspace's capability record; an absent record means enabled";
    let enabled = true;
    bridge.call.mockImplementation(async operation => {
      if (operation === "capability_set_enabled") { enabled = false; throw new Error("reply lost"); }
      return { capabilities: [{ capability: "text.extract", enabled, enabled_basis: basis }] };
    });
    render(<CanonicalResourcesSpace/>);
    await userEvent.setup().click(screen.getByRole("tab",{name:"接入来源与运行设置"}));
    await userEvent.setup().click(await screen.findByRole("button", { name: "禁用文字解析" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("变更未获确认");
    expect(await screen.findByRole("button", { name: "启用文字解析" })).toBeEnabled();
    expect(bridge.call.mock.calls.filter(([op]) => op === "capability_set_enabled")).toHaveLength(1);
    expect(screen.queryByText(/已禁用，工作区设置已确认/)).not.toBeInTheDocument();
  });

  it("rejects a mismatched ACK and a readback that contradicts the requested setting", async () => {
    const basis = "the workspace's capability record; an absent record means enabled";
    bridge.call.mockImplementation(async operation => operation === "capability_set_enabled"
      ? { capability: { capability: "text.extract", enabled: false, enabled_basis: basis } }
      : { capabilities: [{ capability: "text.extract", enabled: true, enabled_basis: basis }] });
    render(<CanonicalResourcesSpace/>);
    await userEvent.setup().click(screen.getByRole("tab",{name:"接入来源与运行设置"}));
    await userEvent.setup().click(await screen.findByRole("button", { name: "禁用文字解析" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("变更未获确认");
    expect(screen.queryByText(/已禁用，工作区设置已确认/)).not.toBeInTheDocument();
    expect(() => readCapabilityDecision({ capability: { capability: "another", enabled: false, enabled_basis: basis } }, "text.extract", false)).toThrow();
    expect(() => readCapabilityDecision({ capability: { capability: "text.extract", enabled: "false", enabled_basis: basis } }, "text.extract", false)).toThrow();
  });

  it("locks refresh and duplicate decisions while one setting write is pending", async () => {
    const basis = "the workspace's capability record; an absent record means enabled";
    let finish!: (value: unknown) => void;
    let enabled = true;
    bridge.call.mockImplementation(operation => operation === "capability_set_enabled"
      ? new Promise(resolve => { finish = resolve; })
      : Promise.resolve({ capabilities: [{ capability: "text.extract", enabled, enabled_basis: basis }] }));
    render(<CanonicalResourcesSpace/>);
    await userEvent.setup().click(screen.getByRole("tab",{name:"接入来源与运行设置"}));
    await userEvent.setup().click(await screen.findByRole("button", { name: "禁用文字解析" }));
    expect(screen.getByRole("button", { name: "刷新本机可用功能" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "禁用文字解析" })).not.toBeInTheDocument();
    enabled = false;
    await act(async () => finish({ capability: { capability: "text.extract", enabled, enabled_basis: basis } }));
    await screen.findByText(/已禁用，工作区设置已确认/);
    expect(bridge.call.mock.calls.filter(([op]) => op === "capability_set_enabled")).toHaveLength(1);
  });

  it("blocks tab unmount while templates are dirty and publishes only its own owner", async () => {
    const seen: { owner: string; dirty: boolean }[] = [];
    const listener = (event: Event) => seen.push((event as CustomEvent).detail);
    window.addEventListener("archeaxis-draft-dirty", listener);
    const dirty = vi.fn(); const user = userEvent.setup();
    const view = render(<CanonicalResourcesSpace onDirtyChange={dirty}/>);
    await user.click(screen.getByRole("tab", { name: "学科模板" }));
    await user.click(screen.getByRole("button", { name: "产生模板草稿" }));
    await user.click(screen.getByRole("tab", { name: "接入来源与运行设置" }));
    expect(screen.getByRole("region", { name: "真实模板回调测试" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("未保存修改或待确认操作");
    expect(seen.at(-1)?.dirty).toBe(true); expect(dirty).toHaveBeenLastCalledWith(true);
    await user.click(screen.getByRole("button", { name: "完成模板处理" }));
    await user.click(screen.getByRole("tab", { name: "接入来源与运行设置" }));
    expect(screen.getByRole("region", { name: "资源目录" })).toBeInTheDocument();
    view.unmount(); expect(seen.at(-1)?.dirty).toBe(false);
    expect(new Set(seen.map(event => event.owner)).size).toBe(1);
    window.removeEventListener("archeaxis-draft-dirty", listener);
  });

  it.each([null, {}, { capabilities: null }, { capabilities: [null] }, { capabilities: [{ capability: "x", enabled: "yes" }] }, { capabilities: [{ capability: "x", health: 4 }] }])("rejects partial handshake %j", value => {
    expect(() => readResourceHandshake(value)).toThrow();
  });
});
