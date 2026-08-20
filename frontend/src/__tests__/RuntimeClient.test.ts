import { afterEach, describe, expect, it, vi } from "vitest";
import { getStatus, resetRuntimeClient } from "../api/runtime";

describe("runtime handshake client", () => {
  afterEach(() => {
    resetRuntimeClient();
    delete window.__TAURI__;
    vi.unstubAllGlobals();
  });

  it("validates the Tauri backend handshake before reading a projection", async () => {
    window.__TAURI__ = { core: { invoke: vi.fn().mockResolvedValue({ port: 4312, token: "memory-only" }) } };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/v1/system/handshake")) {
        expect(init?.headers).toMatchObject({ "X-ArcheAxis-Launch-Token": "memory-only" });
        return {
          ok: true,
          status: 200,
          json: async () => ({ product_id: "archeaxis-workspace" }),
        } as Response;
      }
      expect(url).toBe("http://127.0.0.1:4312/api/status");
      return { ok: true, status: 200, json: async () => ({ status: "available" }) } as Response;
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(getStatus()).resolves.toEqual({ status: "available" });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
