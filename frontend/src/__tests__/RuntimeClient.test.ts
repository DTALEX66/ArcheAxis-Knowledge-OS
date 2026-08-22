import { afterEach, describe, expect, it, vi } from "vitest";
import {
  approveMachineKnowledge,
  createBackup,
  deprecateMachineKnowledge,
  downloadLibraryAsset,
  getStatus,
  getActivity,
  getHome,
  resetRuntimeClient,
  verifyBackup,
} from "../api/runtime";

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
      expect(url).toBe("http://127.0.0.1:4312/workspace/api/status");
      return { ok: true, status: 200, json: async () => ({ status: "available" }) } as Response;
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(getStatus()).resolves.toEqual({ status: "available" });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("uses typed governed commands and preserves authorization for source readback", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/v1/system/handshake")) {
        return { ok: true, json: async () => ({ product_id: "archeaxis-workspace" }) } as Response;
      }
      if (url.includes("/content")) {
        expect(init?.headers).toMatchObject({ Authorization: "Bearer " });
        return { ok: true, blob: async () => new Blob(["source"]) } as Response;
      }
      return { ok: true, json: async () => ({ status: "ok" }) } as Response;
    });
    vi.stubGlobal("fetch", fetchMock);

    await approveMachineKnowledge("Candidate");
    await deprecateMachineKnowledge("Candidate");
    await createBackup("release-check");
    await verifyBackup("release-check");
    await expect(downloadLibraryAsset("a".repeat(64))).resolves.toBeInstanceOf(Blob);
    await getHome();
    await getActivity();

    const calls: Array<[string, string | undefined, BodyInit | null | undefined]> =
      fetchMock.mock.calls.map(([input, init]) => [String(input), init?.method, init?.body]);
    expect(calls.some(([url, method]) => url.endsWith("/workspace/api/runtime/approve") && method === "POST")).toBe(true);
    expect(calls.some(([url, method]) => url.endsWith("/workspace/api/runtime/deprecate") && method === "POST")).toBe(true);
    expect(calls.some(([url, method]) => url.endsWith("/workspace/api/backup/create") && method === "POST")).toBe(true);
    expect(calls.some(([url]) => url.endsWith("/workspace/api/backup/verify?name=release-check"))).toBe(true);
    expect(calls.some(([url]) => url.endsWith("/workspace/api/v1/home"))).toBe(true);
    expect(calls.some(([url]) => url.endsWith("/workspace/api/v1/activity?limit=5"))).toBe(true);
  });
});
