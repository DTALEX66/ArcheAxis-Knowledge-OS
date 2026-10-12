import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { basename, resolve } from "node:path";
import { CanonicalResourcesSpace, readCapabilityDecision, readResourceHandshake } from "../spaces/CanonicalResourcesSpace";
import { RESOURCE_CATALOG } from "../api/generated/resource-catalog";

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
    await screen.findByText(/宿主返回空能力列表/);
    const directory = screen.getByRole("region", { name: "资源供体目录" });
    expect(within(directory).getAllByRole("button", { name: / · / })).toHaveLength(68);
    expect(screen.getByLabelText("来源类别").querySelectorAll("option")).toHaveLength(8);
    expect(screen.queryByRole("button", { name: /安装|升级|启用/ })).not.toBeInTheDocument();
    expect(bridge.call).toHaveBeenCalledTimes(1);
    expect(bridge.call).toHaveBeenCalledWith("capabilities_list");
  });

  it("exposes source fingerprints for reading without opening a diagnostic receipt", async () => {
    const entry = RESOURCE_CATALOG.entries.find(item => item.qualification.evidence.version.source_refs.length > 0)!;
    render(<CanonicalResourcesSpace/>);
    await screen.findByText(/宿主返回空能力列表/);
    const directory = screen.getByRole("region", { name: "资源供体目录" });
    const button = within(directory).getAllByRole("button").find(item => item.querySelector("strong")?.textContent === entry.display_names[0])!;
    await userEvent.setup().click(button);
    const evidence = screen.getByRole("region", { name: "版本证据" });
    const summary = within(evidence).getByText("核对来源指纹");
    await userEvent.setup().click(summary);
    expect(summary.closest("details")).toHaveAttribute("open");
    for (const source of entry.qualification.evidence.version.source_refs) {
      expect(summary.closest("details")).toHaveTextContent(source.path);
      expect(summary.closest("details")).toHaveTextContent(`SHA-256 ${source.sha256}`);
    }
  });

  it("searches the lastentry and原冲突, retains declared reasons and frozen activation", async () => {
    const user = userEvent.setup(); render(<CanonicalResourcesSpace/>);
    await user.type(screen.getByRole("textbox", { name: "查找资源与原冲突" }), "xyflow");
    await user.click(screen.getByRole("button", { name: /xyflow|XYFlow|xyFlow|React Flow/i }));
    const details = screen.getByRole("complementary", { name: "资源登记详情" });
    expect(details).toHaveTextContent("未来候选");
    expect(within(details).getByRole("region", { name: "激活与冻结条件" })).toBeInTheDocument();
    await user.clear(screen.getByRole("textbox", { name: "查找资源与原冲突" }));
    await user.type(screen.getByRole("textbox", { name: "查找资源与原冲突" }), "capability-id-is-not-a-declared-route");
    expect(screen.getByText(/筛选结果/)).not.toHaveTextContent("筛选结果 0 项");
  });

  it("shows live route permission separately and does not promote donor qualification", async () => {
    bridge.call.mockResolvedValue({ capabilities: [{ capability: "media.transcribe", enabled: false, health: "handshake_ready" }] });
    render(<CanonicalResourcesSpace/>);
    await screen.findByText(/已读回 1 条宿主能力/);
    await userEvent.setup().click(screen.getByRole("button", { name: /faster-whisper.* · /i }));
    const relation = screen.getByRole("region", { name: "供体运行联接" });
    expect(relation).toHaveTextContent("已禁用");
    expect(relation).toHaveTextContent("handshake_ready");
    expect(relation).toHaveTextContent("握手不证明");
    expect(screen.queryByRole("button", { name: /启用|安装/ })).not.toBeInTheDocument();
  });

  it("keeps the complete catalog when handshake is unavailable or malformed", async () => {
    bridge.call.mockRejectedValue(new Error("offline")); render(<CanonicalResourcesSpace/>);
    await screen.findByRole("alert"); expect(screen.getByRole("alert")).toHaveTextContent("UNKNOWN");
    expect(within(screen.getByRole("region", { name: "资源供体目录" })).getAllByRole("button", { name: / · / })).toHaveLength(68);
    bridge.call.mockResolvedValue({ capabilities: [{ capability: "media.video" }, { capability: "media.video" }] });
    await userEvent.setup().click(screen.getByRole("button", { name: "重新读取当前宿主能力" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("UNKNOWN"));
    expect(screen.queryByText(/已读回 2 条/)).not.toBeInTheDocument();
  });

  it("ignores an older successful response after the latest failed read", async () => {
    let resolveOld!: (value: unknown) => void;
    bridge.call.mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve; })).mockRejectedValueOnce(new Error("latest offline"));
    render(<CanonicalResourcesSpace/>);
    await userEvent.setup().click(screen.getByRole("button", { name: "重新读取当前宿主能力" }));
    await screen.findByRole("alert");
    await act(async () => resolveOld({ capabilities: [{ capability: "old", enabled: true }] }));
    expect(screen.getByRole("alert")).toHaveTextContent("UNKNOWN");
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
    await userEvent.setup().click(await screen.findByRole("button", { name: "禁用 text.extract" }));
    await screen.findByText(/text.extract 已禁用，工作区设置已读回/);
    expect(bridge.call).toHaveBeenCalledWith("capability_set_enabled", { capability: "text.extract", enabled: false });
    await userEvent.setup().click(screen.getByRole("button", { name: "启用 text.extract" }));
    await screen.findByText(/text.extract 已启用，工作区设置已读回/);
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
    await userEvent.setup().click(await screen.findByRole("button", { name: "禁用 text.extract" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("变更未获确认");
    expect(await screen.findByRole("button", { name: "启用 text.extract" })).toBeEnabled();
    expect(bridge.call.mock.calls.filter(([op]) => op === "capability_set_enabled")).toHaveLength(1);
    expect(screen.queryByText(/已禁用，工作区设置已读回/)).not.toBeInTheDocument();
  });

  it("rejects a mismatched ACK and a readback that contradicts the requested setting", async () => {
    const basis = "the workspace's capability record; an absent record means enabled";
    bridge.call.mockImplementation(async operation => operation === "capability_set_enabled"
      ? { capability: { capability: "text.extract", enabled: false, enabled_basis: basis } }
      : { capabilities: [{ capability: "text.extract", enabled: true, enabled_basis: basis }] });
    render(<CanonicalResourcesSpace/>);
    await userEvent.setup().click(await screen.findByRole("button", { name: "禁用 text.extract" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("变更未获确认");
    expect(screen.queryByText(/已禁用，工作区设置已读回/)).not.toBeInTheDocument();
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
    await userEvent.setup().click(await screen.findByRole("button", { name: "禁用 text.extract" }));
    expect(screen.getByRole("button", { name: "重新读取当前宿主能力" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "禁用 text.extract" })).not.toBeInTheDocument();
    enabled = false;
    await act(async () => finish({ capability: { capability: "text.extract", enabled, enabled_basis: basis } }));
    await screen.findByText(/已禁用，工作区设置已读回/);
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
    await user.click(screen.getByRole("tab", { name: "吸收来源与供体" }));
    expect(screen.getByRole("region", { name: "真实模板回调测试" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("未保存修改或冻结请求");
    expect(seen.at(-1)?.dirty).toBe(true); expect(dirty).toHaveBeenLastCalledWith(true);
    await user.click(screen.getByRole("button", { name: "完成模板处理" }));
    await user.click(screen.getByRole("tab", { name: "吸收来源与供体" }));
    expect(screen.getByRole("region", { name: "资源供体目录" })).toBeInTheDocument();
    view.unmount(); expect(seen.at(-1)?.dirty).toBe(false);
    expect(new Set(seen.map(event => event.owner)).size).toBe(1);
    window.removeEventListener("archeaxis-draft-dirty", listener);
  });

  it.each([null, {}, { capabilities: null }, { capabilities: [null] }, { capabilities: [{ capability: "x", enabled: "yes" }] }, { capabilities: [{ capability: "x", health: 4 }] }])("rejects partial handshake %j", value => {
    expect(() => readResourceHandshake(value)).toThrow();
  });
});
