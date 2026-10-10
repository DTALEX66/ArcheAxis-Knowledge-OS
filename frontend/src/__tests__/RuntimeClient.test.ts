import { afterEach, describe, expect, it, vi } from "vitest";
import * as runtime from "../api/workspace";
import { normalizeRecoveryLogTail, normalizeRecoveryStatus } from "../runtime/recovery";
import { ApiError, createApiClient, runtimeProjectionMessage } from "../api/client";
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
  afterEach(() => { runtime.resetRuntimeClient(); delete window.__TAURI__; vi.unstubAllGlobals(); });
  const handshake = { product_id: "archeaxis-workspace", product_name: "ArcheAxis Knowledge", api_contract: "1.x", backend_version: "0.6.14", source_commit: "abc", schema_version: 7, runtime_mode: "compatibility", workspace_id: "workspace", capabilities: [], migration_state: "ready" };
  it("projects handshake failures as safe Chinese diagnostics", () => {
    expect(runtimeProjectionMessage(new ApiError(0, "runtime identity is incomplete", "incompatible"))).toBe("本地核心身份字段不完整。");
    expect(runtimeProjectionMessage(new Error("network detail"))).toBe("已认证的本地核心握手失败。");
  });
  it("never requests native credentials or legacy HTTP after the Core bridge cutover", async () => {
    const invoke = vi.fn().mockResolvedValue({ ready: true });
    const fetch = vi.fn(); window.__TAURI__ = { core: { invoke } }; vi.stubGlobal("fetch", fetch);
    await expect(runtime.getStatus()).rejects.toMatchObject({ code: "unavailable" });
    await expect(runtime.listLibraryAssets()).rejects.toMatchObject({ code: "unavailable" });
    await expect(runtime.createEvidenceAnchor("a".repeat(64), 2)).rejects.toMatchObject({ code: "unavailable" });
    expect(invoke).not.toHaveBeenCalled(); expect(fetch).not.toHaveBeenCalled();
  });
  it("keeps explicit compatibility-client handshake validation without a native credential bridge", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => handshake }));
    await expect(createApiClient("", "").handshake()).resolves.toMatchObject({ schema_version: 7 });
  });
  it("rejects an incompatible compatibility contract", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ...handshake, api_contract: "2.x" }) }));
    await expect(createApiClient("", "").handshake()).rejects.toMatchObject({ code: "incompatible" });
  });
  it("rejects incomplete identity and migrating compatibility state", async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ...handshake, workspace_id: null }) }); vi.stubGlobal("fetch", fetch);
    await expect(createApiClient("", "").handshake()).rejects.toMatchObject({ code: "incompatible" });
    fetch.mockResolvedValue({ ok: true, json: async () => ({ ...handshake, migration_state: "migrating" }) });
    await expect(createApiClient("", "").handshake()).rejects.toMatchObject({ code: "migrating" });
  });
  it("rejects writes without explicit credentials and scopes in the compatibility client", async () => {
    const fetch = vi.fn(); vi.stubGlobal("fetch", fetch);
    await expect(createApiClient("", "").write("/test", {}, "test-key")).rejects.toMatchObject({ status: 403 });
    expect(fetch).not.toHaveBeenCalled();
  });
  it("preserves compatibility scope/idempotency enforcement outside the native product route", async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ok: true }) }); vi.stubGlobal("fetch", fetch);
    await createApiClient("", "test-only", ["workspace:write"]).write("/test", { text: "body" }, "test-key");
    expect(fetch).toHaveBeenCalledWith("/test", expect.objectContaining({ headers: expect.objectContaining({ "X-ArcheAxis-Launch-Token": "test-only", "X-ArcheAxis-Scopes": "workspace:write", "Idempotency-Key": "test-key" }) }));
  });
  it("rejects malformed successful legacy browser projections instead of partial truth", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => ({ ok: true, status: 200, json: async () => String(input).endsWith("/handshake") ? handshake : { items: null } })));
    await expect(runtime.listLibraryAssets()).rejects.toMatchObject({ code: "incompatible" });
  });  it("uses Tauri-only recovery commands and rejects a backup name outside the enumerated opaque list", async () => {
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
      if (command === "enter_safe_mode") {
        return {
          state: "stopped",
          safe_mode: true,
          backend_available: false,
          message: "Safe mode is active",
          backups: ["cognitive_os_20260823T010203_000000Z.sqlite"],
          external_dev: false,
        };
      }
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
    expect(invoke).toHaveBeenCalledTimes(6);

    expect(invoke).toHaveBeenNthCalledWith(1, "recovery_status");
    expect(invoke).toHaveBeenNthCalledWith(2, "recovery_log_tail");
    expect(invoke).toHaveBeenNthCalledWith(3, "enter_safe_mode");
    expect(invoke).toHaveBeenNthCalledWith(4, "recovery_status");
    expect(invoke).toHaveBeenNthCalledWith(5, "restore_backup", {
      name: "cognitive_os_20260823T010203_000000Z.sqlite",
    });
    expect(invoke).toHaveBeenNthCalledWith(6, "exit_application");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects a backup removed from the fresh recovery status before restore", async () => {
    const backup = "cognitive_os_20260823T010203_000000Z.sqlite";
    const invoke = vi.fn()
      .mockResolvedValueOnce({
        state: "failed",
        safe_mode: false,
        backend_available: false,
        message: "Core startup is unavailable",
        backups: [backup],
        external_dev: false,
      })
      .mockResolvedValueOnce({
        state: "failed",
        safe_mode: false,
        backend_available: false,
        message: "Core startup is unavailable",
        backups: [],
        external_dev: false,
      });
    window.__TAURI__ = { core: { invoke } };
    const recovery = runtime as typeof runtime & RecoveryRuntimeApi;

    await recovery.getRecoveryStatus();
    await expect(recovery.restoreRecoveryBackup(backup)).rejects.toThrow(/fresh recovery status/i);

    expect(invoke).toHaveBeenNthCalledWith(1, "recovery_status");
    expect(invoke).toHaveBeenNthCalledWith(2, "recovery_status");
    expect(invoke).toHaveBeenCalledTimes(2);
  });

  it("withholds explicit sensitive diagnostic shapes at the recovery DTO boundary", () => {
    expect(normalizeRecoveryStatus({
      state: "failed",
      message: "\u001b[31mAuthorization : Bearer top-secret\u001b[0m",
    }).message).toBe("恢复诊断已隐藏");

    expect(normalizeRecoveryLogTail({
      lines: [
        "token = secret-value",
        "see http://127.0.0.1/private",
        "C:\\Users\\person\\private.db",
        "/home/person/private.db",
        "localhost:4312 unavailable",
        `opaque ${"a".repeat(48)}`,
      ],
    }).lines).toEqual(Array(6).fill("恢复诊断已隐藏"));
  });

  it("withholds control-split credential keys and padded Base64-like tokens", () => {
    expect(normalizeRecoveryStatus({
      state: "failed",
      message: "to\nken = raw-secret",
    }).message).toBe("恢复诊断已隐藏");
    expect(normalizeRecoveryLogTail({
      lines: [
        "to\tken: raw-secret",
        "password\r= raw-secret",
        `opaque ${"Q".repeat(40)}==`,
        `opaque ${"a_".repeat(20)}=`,
      ],
    }).lines).toEqual(Array(4).fill("恢复诊断已隐藏"));
  });

  it("scans the complete normalized diagnostic before applying the 240 character display bound", () => {
    const safePrefix = "safe ".repeat(46);
    expect(safePrefix).toHaveLength(230);

    expect(normalizeRecoveryStatus({
      state: "failed",
      message: `${safePrefix}${"A".repeat(40)}==`,
    }).message).toBe("恢复诊断已隐藏");
  });

  it("preserves ordinary sanitized recovery text without keyword overmatching", () => {
    expect(normalizeRecoveryStatus({
      state: "failed",
      message: "important security review remains available",
    }).message).toBe("important security review remains available");
    expect(normalizeRecoveryLogTail({
      lines: ["Core stopped after a normal health check"],
    }).lines).toEqual(["Core stopped after a normal health check"]);
  });
});
