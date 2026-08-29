import { afterEach, describe, expect, it, vi } from "vitest";
import {
  approveMachineKnowledge,
  approveResearchCandidate,
  createBackup,
  deprecateMachineKnowledge,
  dispatchDelivery,
  downloadLibraryAsset,
  downloadPdfAsset,
  getActivityJobs,
  getBatchStatus,
  getConversionRun,
  getConvertedContent,
  getDelivery,
  getHome,
  getSetupStatus,
  getStatus,
  getActivity,
  initializeSetup,
  intakeUrl,
  listLibraryAssets,
  listEvidenceBundles,
  listEvidenceAnchors,
  listResearchCandidates,
  preflightSetup,
  resetRuntimeClient,
  retryFailedDelivery,
  startBatchImport,
  verifyBackup,
} from "../api/workspace";
import * as runtime from "../api/workspace";
import { normalizeRecoveryLogTail, normalizeRecoveryStatus } from "../runtime/recovery";
import { ApiError, runtimeProjectionMessage } from "../api/client";

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

  it("projects handshake failures as safe Chinese diagnostics", () => {
    expect(runtimeProjectionMessage(new ApiError(0, "runtime identity is incomplete", "incompatible")))
      .toBe("本地核心身份字段不完整。");
    expect(runtimeProjectionMessage(new Error("network detail")))
      .toBe("已认证的本地核心握手失败。");
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
          json: async () => ({
            product_id: "archeaxis-workspace", product_name: "ArcheAxis Knowledge", api_contract: "1.x", backend_version: "0.6.0",
            source_commit: "abc1234", schema_version: 15, runtime_mode: "desktop",
            workspace_id: "workspace-001", capabilities: [], migration_state: "ready",
          }),
        } as Response;
      }
      expect(url).toBe("http://127.0.0.1:4312/workspace/api/status");
      return { ok: true, status: 200, json: async () => ({
        schema_version: "v1", observed_at: "2026-08-29T00:00:00Z",
        release: { version: "0.6.11", status: "candidate", public: false }, components: {}, migrations: {}, counts: {}, capabilities: {},
      }) } as Response;
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(getStatus()).resolves.toMatchObject({ schema_version: "v1" });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("rejects malformed successful product projections instead of rendering partial truth", async () => {
    window.__TAURI__ = { core: { invoke: vi.fn().mockResolvedValue({ port: 4312, token: "memory-only", scopes: ["workspace:write"] }) } };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/v1/system/handshake")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            product_id: "archeaxis-workspace", product_name: "ArcheAxis Knowledge", api_contract: "1.x", backend_version: "0.6.0",
            source_commit: "abc1234", schema_version: 15, runtime_mode: "desktop",
            workspace_id: "workspace-001", capabilities: [], migration_state: "ready",
          }),
        } as Response;
      }
      if (url.endsWith("/workspace/api/library")) {
        return { ok: true, status: 200, json: async () => ({ items: null }) } as Response;
      }
      if (url.includes("/workspace/api/v1/activity")) {
        return { ok: true, status: 200, json: async () => ({ items: "not-an-array" }) } as Response;
      }
      if (url.endsWith("/workspace/api/research")) {
        return { ok: true, status: 200, json: async () => ({ items: [{}] }) } as Response;
      }
      if (url.includes("/workspace/api/evidence/anchors")) {
        return { ok: true, status: 200, json: async () => ({ count: 1, items: [{ anchor_id: "a", raw_sha256: "b".repeat(64), source_revision: "r", locator: "bad" }], next_cursor: null }) } as Response;
      }
      if (url.endsWith("/workspace/api/v1/home")) {
        return { ok: true, status: 200, json: async () => ({ release: {}, counts: {}, capabilities: {}, components: {}, recent_activity: "bad" }) } as Response;
      }
      if (url.endsWith("/workspace/api/delivery")) {
        return { ok: true, status: 200, json: async () => ({ summary: { jobs: 0, outbox: { failed: "zero" }, receipts: {} } }) } as Response;
      }
      if (url.endsWith("/api/v1/setup/status")) {
        return { ok: true, status: 200, json: async () => ({ ready: "yes", steps: [] }) } as Response;
      }
      if (url.includes("/workspace/api/evidence/bundles")) {
        return { ok: true, status: 200, json: async () => ({ items: [{ bundle_id: "b" }] }) } as Response;
      }
      if (url.endsWith("/workspace/api/jobs")) {
        return { ok: true, status: 200, json: async () => ({ jobs: [{ activity: "x" }] }) } as Response;
      }
      if (url.endsWith("/api/v1/setup/preflight")) {
        return { ok: true, status: 200, json: async () => ({ ready: true, mode: "quick", domains: {}, library_health: {} }) } as Response;
      }
      if (url.endsWith("/workspace/api/research/approve")) {
        return { ok: true, status: 200, json: async () => ({}) } as Response;
      }
      if (url.endsWith("/workspace/api/delivery/dispatch") || url.endsWith("/workspace/api/delivery/retry")) {
        return { ok: true, status: 200, json: async () => ({ status: "invented" }) } as Response;
      }
      if (url.endsWith("/workspace/api/runtime/approve") || url.endsWith("/workspace/api/runtime/deprecate")) {
        return { ok: true, status: 200, json: async () => ({}) } as Response;
      }
      if (url.endsWith("/workspace/api/intake/url")) {
        return { ok: true, status: 200, json: async () => ({}) } as Response;
      }
      if (url.includes("/workspace/api/batch/")) {
        if (url.endsWith("/status")) return { ok: true, status: 200, json: async () => ({ state: "invented" }) } as Response;
        return { ok: true, status: 200, json: async () => ({ batch_id: "x", state: "invented" }) } as Response;
      }
      if (url.endsWith("/converted")) {
        return { ok: true, status: 200, json: async () => ({ engine: "passthrough" }) } as Response;
      }
      if (url.endsWith("/conversion-run")) {
        return { ok: true, status: 200, json: async () => ({ engine: "passthrough", loss_notes: "bad" }) } as Response;
      }
      throw new Error(`unexpected URL ${url}`);
    }));

    await expect(listLibraryAssets()).rejects.toMatchObject({ code: "incompatible" });
    await expect(getActivity()).rejects.toMatchObject({ code: "incompatible" });
    await expect(listResearchCandidates()).rejects.toMatchObject({ code: "incompatible" });
    await expect(getHome()).rejects.toMatchObject({ code: "incompatible" });
    await expect(getDelivery()).rejects.toMatchObject({ code: "incompatible" });
    await expect(getSetupStatus()).rejects.toMatchObject({ code: "incompatible" });
    await expect(listEvidenceBundles()).rejects.toMatchObject({ code: "incompatible" });
    await expect(getActivityJobs()).rejects.toMatchObject({ code: "incompatible" });
    await expect(listEvidenceAnchors()).rejects.toMatchObject({ code: "incompatible" });
    await expect(preflightSetup({ mode: "quick", root: "D:/ArcheAxis" })).rejects.toMatchObject({ code: "incompatible" });
    await expect(approveResearchCandidate("https://example.test/source")).rejects.toMatchObject({ code: "incompatible" });
    await expect(dispatchDelivery()).rejects.toMatchObject({ code: "incompatible" });
    await expect(retryFailedDelivery()).rejects.toMatchObject({ code: "incompatible" });
    await expect(approveMachineKnowledge("Candidate")).rejects.toMatchObject({ code: "incompatible" });
    await expect(deprecateMachineKnowledge("Approved")).rejects.toMatchObject({ code: "incompatible" });
    await expect(intakeUrl("https://example.test/a")).rejects.toMatchObject({ code: "incompatible" });
    await expect(startBatchImport({ batch_id: "b", source_dir: "D:/x" })).rejects.toMatchObject({ code: "incompatible" });
    await expect(getBatchStatus("b")).rejects.toMatchObject({ code: "incompatible" });
    await expect(getConvertedContent("a".repeat(64))).rejects.toMatchObject({ code: "incompatible" });
    await expect(getConversionRun("a".repeat(64))).rejects.toMatchObject({ code: "incompatible" });
  });

  it("rejects a null workspace identity even when a caller claims first-run capability", async () => {
    window.__TAURI__ = { core: { invoke: vi.fn().mockResolvedValue({ port: 4312, token: "memory-only" }) } };
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/v1/system/handshake")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            product_id: "archeaxis-workspace", product_name: "ArcheAxis Knowledge", api_contract: "1.x", backend_version: "0.6.0",
            source_commit: "abc1234", schema_version: 15, runtime_mode: "desktop",
            workspace_id: null, capabilities: ["first_run_setup"], migration_state: "ready",
          }),
        } as Response;
      }
      return { ok: true, status: 200, json: async () => ({
        schema_version: "v1", observed_at: "2026-08-29T00:00:00Z",
        release: { version: "0.6.11", status: "candidate", public: false }, components: {}, migrations: {}, counts: {}, capabilities: {},
      }) } as Response;
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(getStatus()).rejects.toMatchObject({ code: "incompatible" });
  });

  it("uses typed governed commands and preserves authorization for source readback", async () => {
    window.__TAURI__ = {
      core: { invoke: vi.fn().mockResolvedValue({ port: 4312, token: "memory-only", scopes: ["workspace:write"] }) },
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/v1/system/handshake")) {
        return {
          ok: true,
          json: async () => ({
            product_id: "archeaxis-workspace", product_name: "ArcheAxis Knowledge", api_contract: "1.x", backend_version: "0.6.0",
            source_commit: "abc1234", schema_version: 15, runtime_mode: "desktop",
            workspace_id: "workspace-001", capabilities: [], migration_state: "ready",
          }),
        } as Response;
      }
      if (url.includes("/api/pdf/")) {
        expect(init?.headers).toMatchObject({ "X-ArcheAxis-Launch-Token": "memory-only" });
        expect(init?.headers).not.toHaveProperty("Authorization");
        return { ok: true, blob: async () => new Blob(["%PDF-1.7"], { type: "application/pdf" }) } as Response;
      }
      if (url.includes("/content")) {
        expect(init?.headers).toMatchObject({ "X-ArcheAxis-Launch-Token": "memory-only" });
        expect(init?.headers).not.toHaveProperty("Authorization");
        return { ok: true, blob: async () => new Blob(["source"]) } as Response;
      }
      if (url.endsWith("/workspace/api/v1/home")) {
        return { ok: true, json: async () => ({
          release: { version: "0.6.11", status: "candidate", public: false },
          counts: {}, capabilities: {}, components: {}, recent_activity: [],
        }) } as Response;
      }
      if (url.includes("/workspace/api/v1/activity")) {
        return { ok: true, json: async () => ({ items: [], next_cursor: null }) } as Response;
      }
      if (url.endsWith("/workspace/api/backup/create")) {
        return { ok: true, json: async () => ({ file_count: 1 }) } as Response;
      }
      if (url.includes("/workspace/api/backup/verify")) {
        return { ok: true, json: async () => ({ valid: true }) } as Response;
      }
      if (url.endsWith("/workspace/api/runtime/approve")) {
        return { ok: true, json: async () => ({ title: "Candidate", status: "approved" }) } as Response;
      }
      if (url.endsWith("/workspace/api/runtime/deprecate")) {
        return { ok: true, json: async () => ({ title: "Candidate", status: "deprecated" }) } as Response;
      }
      return { ok: true, json: async () => ({ status: "ok" }) } as Response;
    });
    vi.stubGlobal("fetch", fetchMock);

    await approveMachineKnowledge("Candidate");
    await deprecateMachineKnowledge("Candidate");
    await createBackup("release-check");
    await verifyBackup("release-check");
    await expect(downloadLibraryAsset("a".repeat(64))).resolves.toBeInstanceOf(Blob);
    await expect(downloadPdfAsset("b".repeat(64))).resolves.toBeInstanceOf(Blob);
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
    expect(calls.some(([url]) => url.endsWith(`/workspace/api/pdf/sha256:${"b".repeat(64)}`))).toBe(true);
  });

  it("rejects an incompatible API contract before requesting a workspace projection", async () => {
    window.__TAURI__ = {
      core: { invoke: vi.fn().mockResolvedValue({ port: 4312, token: "memory-only", scopes: ["workspace:write"] }) },
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        product_id: "archeaxis-workspace",
        product_name: "ArcheAxis Knowledge",
        api_contract: "0.9",
        backend_version: "0.6.0",
        source_commit: "abc1234",
        schema_version: 15,
        runtime_mode: "desktop",
        workspace_id: "workspace-001",
        capabilities: [],
        migration_state: "ready",
      }),
    } as Response));

    await expect(getStatus()).rejects.toMatchObject({ code: "incompatible" });
  });

  it("rejects a handshake with incomplete runtime identity", async () => {
    window.__TAURI__ = {
      core: { invoke: vi.fn().mockResolvedValue({ port: 4312, token: "memory-only", scopes: ["workspace:write"] }) },
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        product_id: "archeaxis-workspace", product_name: "", api_contract: "1.x",
        backend_version: "0.6.0", source_commit: "", schema_version: 15,
        runtime_mode: "desktop", workspace_id: "workspace-001", capabilities: [],
        migration_state: "ready",
      }),
    } as Response));

    await expect(getStatus()).rejects.toMatchObject({ code: "incompatible" });
  });

  it("attaches token scope and idempotency headers to every typed product write", async () => {
    window.__TAURI__ = {
      core: { invoke: vi.fn().mockResolvedValue({ port: 4312, token: "memory-only", scopes: ["workspace:write"] }) },
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/api/v1/system/handshake")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            product_id: "archeaxis-workspace",
            product_name: "ArcheAxis Knowledge",
            api_contract: "1.x",
            backend_version: "0.6.0",
            source_commit: "abc1234",
            schema_version: 15,
            runtime_mode: "desktop",
            workspace_id: "workspace-001",
            capabilities: [],
            migration_state: "ready",
          }),
        } as Response;
      }
      expect(init?.method).toBe("POST");
      expect(init?.headers).toMatchObject({
        "X-ArcheAxis-Launch-Token": "memory-only",
        "X-ArcheAxis-Scopes": "workspace:write",
        "Idempotency-Key": expect.stringMatching(/^workspace-/),
      });
      const url = String(input);
      if (url.endsWith("/workspace/api/research/approve")) {
        return { ok: true, status: 200, json: async () => ({ status: "candidate" }) } as Response;
      }
      if (url.endsWith("/workspace/api/runtime/approve")) {
        return { ok: true, status: 200, json: async () => ({ title: "Candidate", status: "approved" }) } as Response;
      }
      if (url.endsWith("/workspace/api/runtime/deprecate")) {
        return { ok: true, status: 200, json: async () => ({ title: "Candidate", status: "deprecated" }) } as Response;
      }
      if (url.endsWith("/workspace/api/backup/create")) {
        return { ok: true, status: 200, json: async () => ({ file_count: 1 }) } as Response;
      }
      if (url.endsWith("/api/v1/setup/initialize")) {
        return { ok: true, status: 200, json: async () => ({
          initialized: true,
          workspace_id: "workspace-001",
          workspace_root: "D:/ArcheAxis",
          mode: "quick",
          library_health: {
            source_archive: {}, evidence_ledger: {}, human_learning_vault: {}, ai_asset_vault: {},
          },
          domains: {
            source_archive: "D:/ArcheAxis/source", evidence_ledger: "D:/ArcheAxis/evidence",
            human_learning_vault: "D:/ArcheAxis/learning", ai_asset_vault: "D:/ArcheAxis/assets",
          },
          status: {
            schema_version: "v1", ready: true, workspace_id: "workspace-001", workspace_root: "D:/ArcheAxis",
            steps: [{ id: "paths_writable", state: "ready", message: "ready", action_hint: "" }],
          },
        }) } as Response;
      }
      return { ok: true, status: 200, json: async () => ({ status: "ok" }) } as Response;
    });
    vi.stubGlobal("fetch", fetchMock);

    await approveMachineKnowledge("Candidate");
    await deprecateMachineKnowledge("Candidate");
    await approveResearchCandidate("https://example.com/research");
    await createBackup("release-check");
    await initializeSetup();
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
