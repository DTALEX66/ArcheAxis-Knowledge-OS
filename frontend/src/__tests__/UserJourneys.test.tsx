// SIMULATED UI journeys; native FE24 installation/restart is a separate gate.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ModelConfigurationPanel } from "../components/ModelConfigurationPanel";
import type { ModelConfiguration } from "../api/generated/model-configuration-contract";
const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));
let saved: ModelConfiguration;
beforeEach(() => {
  saved = { schema: "archeaxis.model-configuration/v1", workspace_id: "a".repeat(32), restore_epoch: "initial", revision: 3,
    profiles: { local: { endpoint: "http://127.0.0.1:1234/v1", protocol: "openai", model: "chosen", credential_ref: null, max_tokens: 512, timeout_s: 20 } },
    bindings: [{ purpose: "answer", lane: "deep", profile_id: "local" }] };
  bridge.call.mockReset();
  bridge.call.mockImplementation(async (op: string, args: any) => {
    if (op === "model_configuration_get") return saved;
    if (op === "model_configuration_put") { saved = { ...args.body.configuration, revision: saved.revision + 1 }; return saved; }
    throw new Error(`Unexpected operation ${op}`);
  });
});
afterEach(() => vi.unstubAllGlobals());
async function open() {
  const user = userEvent.setup(); render(<ModelConfigurationPanel />);
  await user.click(screen.getByRole("button", { name: "读取模型配置" }));
  await screen.findByLabelText("模型名称"); return user;
}
describe("SIMULATED configuration read → diagnose → save → read", () => {
  it("uses the native directory command in the actual settings component without browser CORS", async()=>{
    const invoke=vi.fn().mockResolvedValue({schema:"archeaxis.local-model-inventory/v1",models:["chosen"],inference_status:"NOT_EXECUTED",loaded_status:"UNKNOWN"});
    const fetcher=vi.fn().mockRejectedValue(new TypeError("CORS blocked"));
    vi.stubGlobal("__TAURI__",{core:{invoke}});vi.stubGlobal("fetch",fetcher);
    const user=await open();await user.click(screen.getByRole("button",{name:"测试连接"}));await screen.findByText(/目录读取成功/);
    expect(invoke).toHaveBeenCalledTimes(1);expect(fetcher).not.toHaveBeenCalled();
    expect(bridge.call.mock.calls.some(([op])=>op==="model_configuration_put")).toBe(false);
    expect(saved.profiles.local.model).toBe("chosen");
  });
  it("starts a new profile at LM Studio without overwriting existing profiles or bindings", async () => {
    const user = await open();
    await user.clear(screen.getByLabelText("配置名称"));
    await user.type(screen.getByLabelText("配置名称"), "new-local");
    expect(screen.getByLabelText("本地服务地址")).toHaveValue("http://127.0.0.1:1234/v1");
    expect(screen.getByLabelText("协议")).toHaveValue("openai");
    expect(screen.getByLabelText("模型名称")).toHaveValue("");
    expect(saved.profiles.local.model).toBe("chosen");
    expect(saved.bindings).toEqual([{ purpose: "answer", lane: "deep", profile_id: "local" }]);
    expect(bridge.call.mock.calls.every(([op]) => op === "model_configuration_get")).toBe(true);
  });
  it.each([
    ["openai", "http://127.0.0.1:1234/v1", "/v1/models", { data: [{ id: "chosen" }] }],
    ["openai", "http://127.0.0.1:1234/v1/", "/v1/models", { data: [{ id: "chosen" }] }],
    ["openai", "http://127.0.0.1:1234", "/v1/models", { data: [{ id: "chosen" }] }],
    ["ollama", "http://127.0.0.1:11434/", "/api/tags", { models: [{ name: "chosen" }] }],
  ])("diagnoses %s at %s and preserves bindings", async (protocol, endpoint, path, inventory) => {
    const fetcher = vi.fn().mockResolvedValue({ ok: true, json: async () => inventory }); vi.stubGlobal("fetch", fetcher);
    const user = await open(); await user.selectOptions(screen.getByLabelText("协议"), protocol as string);
    await user.clear(screen.getByLabelText("本地服务地址")); await user.type(screen.getByLabelText("本地服务地址"), endpoint as string);
    await user.click(screen.getByRole("button", { name: "测试连接" })); await screen.findByText(/目录读取成功/);
    expect(fetcher.mock.calls[0][0]).toBe(new URL(path as string, endpoint as string).href);
    expect(fetcher.mock.calls[0][1]).toMatchObject({ credentials: "omit", redirect: "error" });
    expect(bridge.call.mock.calls.some(([op]) => op === "model_configuration_put")).toBe(false);
    await user.click(screen.getByRole("button", { name: "保存配置与用途绑定" })); await screen.findByText(/已保存版本 4/);
    await user.click(screen.getByRole("button", { name: "读取模型配置" }));
    expect(screen.getByLabelText("本地服务地址")).toHaveValue((endpoint as string).replace(/\/+$/, ""));
    expect(saved.profiles.local.endpoint).toBe((endpoint as string).replace(/\/+$/, ""));
    expect(screen.getByLabelText("answer / DEEP")).toHaveValue("local");
    expect(saved.profiles.local.protocol).toBe(protocol);
  });
  it.each([null, { data: {} }, { data: [{ id: "" }] }, { models: [] }])("rejects malformed inventory %j", async inventory => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => inventory })); const user = await open();
    await user.click(screen.getByRole("button", { name: "测试连接" })); await screen.findByText(/响应格式不正确/);
    expect(screen.queryByText(/目录读取成功/)).toBeNull();
  });
  it("retains input after HTTP failure and supports retry", async () => {
    const fetcher = vi.fn().mockResolvedValueOnce({ ok: false, status: 503 }).mockResolvedValue({ ok: true, json: async () => ({ data: [{ id: "unsaved" }] }) });
    vi.stubGlobal("fetch", fetcher); const user = await open();
    await user.clear(screen.getByLabelText("模型名称")); await user.type(screen.getByLabelText("模型名称"), "unsaved");
    await user.click(screen.getByRole("button", { name: "测试连接" })); await screen.findByText(/HTTP 503/);
    expect(screen.getByLabelText("模型名称")).toHaveValue("unsaved");
    await user.click(screen.getByRole("button", { name: "测试连接" })); await screen.findByText(/目录读取成功/);
  });
  it("does not claim an absent configured model is available", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ data: [{ id: "different" }] }) }));
    const user = await open(); await user.click(screen.getByRole("button", { name: "测试连接" }));
    await screen.findByText(/所选模型不在目录中/);
  });
  it("discards a late diagnosis after a profile edit", async () => {
    let resolve!: (value: unknown) => void;
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise(done => { resolve = done; })));
    const user = await open(); await user.click(screen.getByRole("button", { name: "测试连接" }));
    await user.clear(screen.getByLabelText("模型名称")); await user.type(screen.getByLabelText("模型名称"), "changed");
    await act(async () => { resolve({ ok: true, json: async () => ({ data: [{ id: "chosen" }] }) }); });
    expect(screen.queryByText(/目录读取成功|连接成功/)).toBeNull();
    expect(screen.getByRole("button", { name: "测试连接" })).toBeEnabled();
  });
  it.each(["https://example.com/v1", "http://localhost:1234/v1", "http://user:pass@127.0.0.1:1234/v1", "http://127.0.0.1:1234/v1?key=value"])("rejects unsupported destination %s before networking", async endpoint => {
    const fetcher = vi.fn(); vi.stubGlobal("fetch", fetcher); saved.profiles.local.endpoint = endpoint;
    const user = await open(); await user.click(screen.getByRole("button", { name: "测试连接" }));
    await screen.findByText(/仅支持无凭据.*数值 loopback/); expect(fetcher).not.toHaveBeenCalled();
  });
});

