import { afterEach, describe, expect, it, vi } from "vitest";
import { coreCommand, verifyCanonicalCore } from "../api/core";

afterEach(() => { delete window.__TAURI__; });
describe("finite Core bridge", () => {
  it.each(["3.51.3","3.50.7","3.44.6","3.52.0"])("accepts a fixed SQLite version %s",async(sqlite_version)=>{
    window.__TAURI__={core:{invoke:vi.fn().mockResolvedValue({status:200,body:{runtime:"archeaxis-api",contract:"0.1.0-outline",schema_version:7,sqlite_version}})}};
    await expect(verifyCanonicalCore()).resolves.toBeUndefined();
  });
  it.each(["3.46.0","3.51.2",undefined])("rejects an old or missing SQLite version %s",async(sqlite_version)=>{
    window.__TAURI__={core:{invoke:vi.fn().mockResolvedValue({status:200,body:{runtime:"archeaxis-api",contract:"0.1.0-outline",schema_version:7,sqlite_version}})}};
    await expect(verifyCanonicalCore()).rejects.toMatchObject({message:"本地核心需更新。"});
  });
  it("forwards only a business operation and payload, never an HTTP URL or token", async () => {
    const invoke = vi.fn().mockResolvedValue({ status: 200, body: { runtime: "archeaxis-api", contract: "0.1.0-outline", schema_version: 7, sqlite_version: "3.51.3" } });
    window.__TAURI__ = { core: { invoke } };
    await verifyCanonicalCore();
    expect(invoke).toHaveBeenCalledWith("core_command", { request: { operation: "system_version", payload: {} } });
  });
  it("distinguishes a missing object, a refused argument, a core fault and an identity refusal", async () => {
    const cases: Array<[number, RegExp]> = [
      [404, /找不到 sources_list 所需的对象/],
      [400, /拒绝了 sources_list（400）/],
      [503, /未能完成 sources_list（503）/],
      [403, /拒绝了此操作的身份/],
    ];
    for (const [status, pattern] of cases) {
      window.__TAURI__ = { core: { invoke: vi.fn().mockResolvedValue({ status, body: {} }) } };
      await expect(coreCommand("sources_list")).rejects.toThrowError(pattern);
    }
  });
  it("reports version conflict and rejects malformed status instead of returning success", async () => {
    const invoke = vi.fn().mockResolvedValue({ status: 409, body: {} });
    window.__TAURI__ = { core: { invoke } };
    await expect(coreCommand("document_draft", {})).rejects.toMatchObject({ status: 409 });
    invoke.mockResolvedValue({ status: "200", body: {} });
    await expect(coreCommand("sources_list")).rejects.toMatchObject({ status: 502 });
  });
  it("validates successful DTO bodies and withholds raw native exception text", async () => {
    const invoke = vi.fn().mockResolvedValue({status:200,body:{sources:[{source_id:"partial"}]}});
    window.__TAURI__={core:{invoke}};
    await expect(coreCommand("sources_list")).rejects.toMatchObject({status:502,code:"incompatible"});
    invoke.mockRejectedValue("CORE_RESPONSE_INVALID private transport details");
    await expect(coreCommand("sources_list")).rejects.toMatchObject({status:502,message:"本地核心暂时无法响应，请保留草稿后重试。"});
  });
});
