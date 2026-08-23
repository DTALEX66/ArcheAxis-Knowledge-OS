// Real runtime API clients for Workspace/Library/Evidence/AI Assets/Settings.
// Every request shares the handshake client; no second unauthenticated client
// or hard-coded runtime port is allowed.
import { createApiClient, type ApiClient } from "./client";
import {
  isOpaqueBackupName,
  normalizeRecoveryLogTail,
  normalizeRecoveryStatus,
  type RecoveryLogTailDto,
  type RecoveryStatusDto,
  type RestoreReceiptDto,
} from "../runtime/recovery";
export interface EvidenceAnchorDto {
  anchor_id: string;
  raw_sha256: string;
  source_revision: string;
  locator: Record<string, unknown>;
}

export interface EvidenceListDto {
  count: number;
  items: EvidenceAnchorDto[];
}

export interface LibraryAssetDto {
  source_name: string;
  raw_sha256: string;
  size_bytes: number;
  retention: string;
  conversion_state: "retained" | "requires_attention";
}

export interface LibraryListDto {
  items: LibraryAssetDto[];
}

export interface ActivityJobDto {
  activity: string;
  state: string;
  delivery_state: string;
  updated_at: string;
}

export interface ActivityJobsDto {
  jobs: ActivityJobDto[];
}

export interface ActivityItemDto {
  public_ref: string;
  kind: "job" | "source";
  label: string;
  state: string;
  updated_at: string;
}

export interface ActivityPageDto {
  items: ActivityItemDto[];
  next_cursor: string | null;
}

export interface MachineKnowledgeDto {
  title: string;
  content: string;
  lifecycle: "approved";
}

export interface MachineKnowledgeCandidateDto {
  title: string;
  content: string;
  lifecycle: "candidate" | "approved" | "deprecated";
  version: string;
  evidence_source: string;
  scope: Record<string, unknown>;
}

export interface ResearchCandidateDto {
  source: string;
  status?: string;
  claim_count?: number;
  evidence_count?: number;
  verification?: string;
  created_at?: string;
}

export interface MachineKnowledgeListDto {
  items: MachineKnowledgeDto[];
}

export interface StatusDto {
  status?: string;
  version?: string;
  workspace_id?: string | null;
  migration_state?: string;
  [k: string]: unknown;
}

export type SetupMode = "quick" | "advanced";

export interface SetupRequestDto {
  [key: string]: unknown;
  mode: SetupMode;
  root?: string;
  domains?: Record<string, string>;
}

export interface SetupHealthDto {
  free_bytes?: number;
  readonly?: boolean;
  filesystem?: string;
  removable?: string;
  [key: string]: unknown;
}

export interface SetupStatusDto {
  ready?: boolean;
  workspace_id?: string | null;
  workspace_root?: string;
  steps?: Array<{ id: string; state: string; message: string; action_hint: string }>;
  [key: string]: unknown;
}

export interface SetupPreflightDto {
  ready: boolean;
  mode: SetupMode;
  domains: Record<string, string>;
  library_health: Record<string, SetupHealthDto>;
}

declare global {
  interface Window {
    __TAURI__?: { core?: { invoke: (command: string, args?: Record<string, unknown>) => Promise<unknown> } };
  }
}

let clientPromise: Promise<ApiClient> | null = null;

// Recovery Shell calls this after a failed launch/handshake. It drops only an
// in-memory rejected client; no endpoint or token is persisted in the UI.
export function resetRuntimeClient(): void {
  clientPromise = null;
}

function recoveryInvoke(command: string, args?: Record<string, unknown>): Promise<unknown> {
  const invoke = window.__TAURI__?.core?.invoke;
  if (!invoke) return Promise.reject(new Error("Recovery controls require the desktop runtime"));
  return args === undefined ? invoke(command) : invoke(command, args);
}

export async function getRecoveryStatus(): Promise<RecoveryStatusDto> {
  return normalizeRecoveryStatus(await recoveryInvoke("recovery_status"));
}

export async function getRecoveryLogTail(): Promise<RecoveryLogTailDto> {
  return normalizeRecoveryLogTail(await recoveryInvoke("recovery_log_tail"));
}

export async function enterRecoverySafeMode(): Promise<RecoveryStatusDto> {
  return normalizeRecoveryStatus(await recoveryInvoke("enter_safe_mode"));
}

export async function retryDesktopBackend(): Promise<void> {
  await recoveryInvoke("retry_backend");
}

export async function restoreRecoveryBackup(name: string): Promise<RestoreReceiptDto> {
  if (!isOpaqueBackupName(name)) {
    throw new Error("Restore requires an enumerated opaque backup name");
  }
  const freshStatus = await getRecoveryStatus();
  if (!freshStatus.backups.includes(name)) {
    throw new Error("Restore selection is absent from the fresh recovery status");
  }
  const receipt = await recoveryInvoke("restore_backup", { name });
  if ((receipt as { status?: unknown } | null)?.status !== "restored") {
    throw new Error("Backup restore did not return a valid receipt");
  }
  return { status: "restored" };
}

export async function exitRecoveryApplication(): Promise<void> {
  await recoveryInvoke("exit_application");
}

async function runtimeClient(): Promise<ApiClient> {
  if (!clientPromise) {
    clientPromise = (async () => {
      const invoke = window.__TAURI__?.core?.invoke;
      const client = !invoke
        ? createApiClient("", "")
        : await (async () => {
          const backend = await invoke("backend_info") as { port: number; token: string } | null;
          if (!backend) throw new Error("desktop backend is unavailable; open Recovery Shell to retry");
          return createApiClient(`http://127.0.0.1:${backend.port}`, backend.token);
        })();
      // Do not allow a backend that failed the product/API handshake to serve
      // any UI projection. The launch token stays in the closure only.
      await client.handshake();
      return client;
    })();
  }
  return clientPromise;
}

export async function runtimeJSON<T>(path: string, init?: RequestInit): Promise<T> {
  return (await runtimeClient()).request<T>(path, init);
}

async function getJSON<T>(path: string): Promise<T> {
  return (await runtimeClient()).request<T>(path);
}

function commandId(prefix: string): string {
  const value = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
  return `workspace-${prefix}-${value}`;
}

async function postJSON<T>(path: string, body?: Record<string, unknown>): Promise<T> {
  return (await runtimeClient()).request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
}

export function listEvidenceAnchors(limit = 50): Promise<EvidenceListDto> {
  return getJSON<EvidenceListDto>(`/workspace/api/evidence/anchors?limit=${limit}`);
}

export function getStatus(): Promise<StatusDto> {
  return getJSON<StatusDto>("/workspace/api/status");
}

export function getHome(): Promise<Record<string, unknown>> {
  return getJSON<Record<string, unknown>>("/workspace/api/v1/home");
}

export function getActivity(limit = 5): Promise<ActivityPageDto> {
  return getJSON<ActivityPageDto>(`/workspace/api/v1/activity?limit=${limit}`);
}

export function listLibraryAssets(): Promise<LibraryListDto> {
  return getJSON<LibraryListDto>("/workspace/api/library");
}

export async function downloadLibraryAsset(rawSha256: string): Promise<Blob> {
  const response = await (await runtimeClient()).requestRaw(
    `/workspace/api/library/${encodeURIComponent(rawSha256)}/content`,
  );
  return response.blob();
}

export function listResearchCandidates(): Promise<{ items: ResearchCandidateDto[] }> {
  return getJSON<{ items: ResearchCandidateDto[] }>("/workspace/api/research");
}

export function approveResearchCandidate(source: string): Promise<Record<string, unknown>> {
  return postJSON("/workspace/api/research/approve", {
    command_id: commandId("research"), source,
  });
}

export function getActivityJobs(): Promise<ActivityJobsDto> {
  return getJSON<ActivityJobsDto>("/workspace/api/jobs");
}

export function getMachineKnowledge(): Promise<MachineKnowledgeListDto> {
  return getJSON<MachineKnowledgeListDto>("/workspace/api/runtime/knowledge");
}

export function listMachineKnowledgeCandidates(): Promise<{ items: MachineKnowledgeCandidateDto[] }> {
  return getJSON<{ items: MachineKnowledgeCandidateDto[] }>("/workspace/api/runtime/candidates");
}

export function approveMachineKnowledge(title: string): Promise<Record<string, unknown>> {
  return postJSON("/workspace/api/runtime/approve", {
    command_id: commandId("runtime-approve"), title,
  });
}

export function deprecateMachineKnowledge(title: string): Promise<Record<string, unknown>> {
  return postJSON("/workspace/api/runtime/deprecate", {
    command_id: commandId("runtime-deprecate"), title,
  });
}

export function getSetupStatus(): Promise<SetupStatusDto> {
  return getJSON<SetupStatusDto>("/api/v1/setup/status");
}

export function preflightSetup(payload: SetupRequestDto): Promise<SetupPreflightDto> {
  return postJSON<SetupPreflightDto>("/api/v1/setup/preflight", payload);
}

export function initializeSetup(payload: SetupRequestDto): Promise<Record<string, unknown>> {
  return postJSON<Record<string, unknown>>("/api/v1/setup/initialize", payload);
}


export function createBackup(name: string): Promise<Record<string, unknown>> {
  return postJSON("/workspace/api/backup/create", { name });
}

export function verifyBackup(name: string): Promise<Record<string, unknown>> {
  return getJSON<Record<string, unknown>>(
    `/workspace/api/backup/verify?name=${encodeURIComponent(name)}`,
  );
}
