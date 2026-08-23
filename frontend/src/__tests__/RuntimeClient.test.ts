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
import * as runtime from "../api/runtime";

interface RecoveryRuntimeApi {
  getRecoveryStatus: () => Promise<{
    state: string;
    safe_mode: boolean;
    backend_available: boolean;
    message: string;
    backups: string[];
  }>;
  getRecoveryLogTail: () => Promise<{ lines: string[] }>;
  enterRecoverySafeMode: () => Promise<unknown>;
  restoreRecoveryBackup: (name: string) => Promise<unknown>;
  exitRecoveryApplication: () => Promise<void>;
}

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

  it("uses Tauri-only recovery commands and rejects a backup name outside the enumerated opaque list", async () => {
    const invoke = vi.fn(async (command: string) => {
      if (command === "recovery_status") {
        return {
          state: "failed",
          safe_mode: false,
          backend_available: false,
          message: "Core startup is unavailable",
          backups: ["cognitive_os_20260823T010203_000000Z.sqlite"],
        };
      }
      if (command === "recovery_log_tail") return { lines: ["Core startup is unavailable"] };
      if (command === "enter_safe_mode") return { safe_mode: true };
      if (command === "restore_backup") return { status: "restored" };
      if (command === "exit_application") return undefined;
      throw new Error(`unexpected command: ${command}`);
    });
    const fetchMock = vi.fn();
    window.__TAURI__ = { core: { invoke } };
    vi.stubGlobal("fetch", fetchMock);
    const recovery = runtime as typeof runtime & RecoveryRuntimeApi;

    await expect(recovery.getRecoveryStatus()).resolves.toMatchObject({
      state: "failed",
      backups: ["cognitive_os_20260823T010203_000000Z.sqlite"],
    });
    await expect(recovery.getRecoveryLogTail()).resolves.toEqual({
      lines: ["Core startup is unavailable"],
    });
    await recovery.enterRecoverySafeMode();
    await recovery.restoreRecoveryBackup("cognitive_os_20260823T010203_000000Z.sqlite");
    await recovery.exitRecoveryApplication();
    await expect(recovery.restoreRecoveryBackup("../private-backup.axbak")).rejects.toThrow(
      /enumerated opaque backup/i,
    );

    expect(invoke).toHaveBeenNthCalledWith(1, "recovery_status");
    expect(invoke).toHaveBeenNthCalledWith(2, "recovery_log_tail");
    expect(invoke).toHaveBeenNthCalledWith(3, "enter_safe_mode");
    expect(invoke).toHaveBeenNthCalledWith(4, "restore_backup", {
      name: "cognitive_os_20260823T010203_000000Z.sqlite",
    });
    expect(invoke).toHaveBeenNthCalledWith(5, "exit_application");
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
