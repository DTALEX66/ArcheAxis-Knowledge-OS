// Typed Workspace API facade for Workspace/Library/Evidence/AI Assets/Settings.
// Every request shares the handshake client; no second unauthenticated client
// or hard-coded runtime port is allowed.
import { ApiError, createApiClient, type ApiClient } from "./client";
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
  next_cursor: string | null;
}

export interface EvidenceBundleSummaryDto {
  bundle_id: string;
  claim_id: string;
  review_decision: string | null;
  created_at: string;
}

export interface EvidenceBundleReviewDto {
  decision: string;
  reviewer_id: string;
  reviewed_at: string;
  rationale: string;
}

export interface EvidenceBundleInspectionDto {
  bundle_id: string;
  claim_id: string;
  fingerprint: string;
  entries: Array<Record<string, unknown>>;
  review_history: EvidenceBundleReviewDto[];
  latest_review: EvidenceBundleReviewDto | null;
  conflict: boolean;
  rights: string[];
  scopes: string[];
  version_history: Array<{
    version_id: string;
    canonical_key: string;
    parent_version_id: string | null;
    lifecycle_status: string;
    created_at: string;
    conflict: { id: string; status: string } | null;
  }>;
}

export interface LibraryAssetDto {
  source_name: string;
  raw_sha256: string;
  size_bytes: number;
  mime_type?: string;
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

export interface ActivityObjectDto {
  label: string;
  state: string;
  source?: string;
  updated_at?: string;
}

export interface DeliveryDto {
  summary: {
    jobs: number;
    outbox: Record<string, number>;
    receipts: Record<string, number>;
  };
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

function invalidProjection(label: string): never {
  throw new ApiError(502, `${label} projection is incompatible`, "incompatible");
}

function recordProjection(value: unknown, label: string): Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) invalidProjection(label);
  return value as Record<string, unknown>;
}

function itemsProjection<T>(value: unknown, label: string): { items: T[] } & Record<string, unknown> {
  const record = recordProjection(value, label);
  if (!Array.isArray(record.items)) invalidProjection(label);
  return record as { items: T[] } & Record<string, unknown>;
}

function stringField(record: Record<string, unknown>, field: string, label: string): string {
  if (typeof record[field] !== "string") invalidProjection(label);
  return record[field] as string;
}

function requireItemFields(items: unknown[], fields: string[], label: string): void {
  for (const item of items) {
    const record = recordProjection(item, label);
    for (const field of fields) stringField(record, field, label);
  }
}

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
          const backend = await invoke("backend_info") as { port: number; token: string; scopes?: unknown } | null;
          if (!backend) throw new Error("desktop backend is unavailable; open Recovery Shell to retry");
          const scopes = Array.isArray(backend.scopes)
            ? backend.scopes.filter((scope): scope is string => typeof scope === "string")
            : [];
          return createApiClient(`http://127.0.0.1:${backend.port}`, backend.token, scopes);
        })();
      // Do not allow a backend that failed the product/API handshake to serve
      // any UI projection. The launch token stays in the closure only.
      await client.handshake();
      return client;
    })();
  }
  return clientPromise;
}

export async function runtimeJSON<T>(path: string): Promise<T> {
  return (await runtimeClient()).request<T>(path);
}

async function getJSON<T>(path: string): Promise<T> {
  return (await runtimeClient()).request<T>(path);
}

function commandId(prefix: string): string {
  const value = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
  return `workspace-${prefix}-${value}`;
}

async function postJSON<T>(path: string, body?: Record<string, unknown>, prefix = "write"): Promise<T> {
  const payload = body ?? {};
  const suppliedCommandId = payload.command_id;
  const idempotencyKey = typeof suppliedCommandId === "string"
    ? suppliedCommandId
    : commandId(prefix);
  return (await runtimeClient()).write<T>(path, payload, idempotencyKey);
}

export function runtimePostJSON<T>(
  path: string,
  body: Record<string, unknown>,
  prefix = "write",
): Promise<T> {
  return postJSON<T>(path, body, prefix);
}

export async function listEvidenceAnchors(limit = 50, cursor?: string): Promise<EvidenceListDto> {
  const query = cursor
    ? `?limit=${limit}&cursor=${encodeURIComponent(cursor)}`
    : `?limit=${limit}`;
  const record = itemsProjection<EvidenceAnchorDto>(await getJSON<unknown>(`/workspace/api/evidence/anchors${query}`), "evidence anchors");
  requireItemFields(record.items, ["anchor_id", "raw_sha256", "source_revision"], "evidence anchor");
  if (typeof record.count !== "number" || !(record.next_cursor === null || typeof record.next_cursor === "string")) invalidProjection("evidence anchors");
  return record as unknown as EvidenceListDto;
}

export async function listEvidenceBundles(limit = 50): Promise<{ items: EvidenceBundleSummaryDto[] }> {
  return itemsProjection<EvidenceBundleSummaryDto>(await getJSON<unknown>(`/workspace/api/evidence/bundles?limit=${limit}`), "evidence bundles");
}

export async function getEvidenceBundleInspection(bundleId: string): Promise<EvidenceBundleInspectionDto> {
  const record = recordProjection(await getJSON<unknown>(
    `/workspace/api/evidence/bundles/${encodeURIComponent(bundleId)}/inspection`,
  ), "evidence bundle inspection");
  for (const field of ["entries", "review_history", "rights", "scopes", "version_history"]) {
    if (!Array.isArray(record[field])) invalidProjection("evidence bundle inspection");
  }
  if (typeof record.conflict !== "boolean") invalidProjection("evidence bundle inspection");
  return record as unknown as EvidenceBundleInspectionDto;
}

export async function getStatus(): Promise<StatusDto> {
  return recordProjection(await getJSON<unknown>("/workspace/api/status"), "workspace status") as StatusDto;
}

export async function getHome(): Promise<Record<string, unknown>> {
  return recordProjection(await getJSON<unknown>("/workspace/api/v1/home"), "workspace home");
}

export async function getActivity(limit = 5): Promise<ActivityPageDto> {
  const record = itemsProjection<ActivityItemDto>(await getJSON<unknown>(`/workspace/api/v1/activity?limit=${limit}`), "activity");
  requireItemFields(record.items, ["public_ref", "kind", "label", "state", "updated_at"], "activity item");
  if (!(record.next_cursor === null || typeof record.next_cursor === "string")) invalidProjection("activity");
  return record as unknown as ActivityPageDto;
}

export async function getActivityObject(publicRef: string): Promise<ActivityObjectDto> {
  const record = recordProjection(await getJSON<unknown>(`/workspace/api/v1/objects/${encodeURIComponent(publicRef)}`), "activity object");
  stringField(record, "label", "activity object");
  stringField(record, "state", "activity object");
  return record as unknown as ActivityObjectDto;
}

export async function getDelivery(): Promise<DeliveryDto> {
  const record = recordProjection(await getJSON<unknown>("/workspace/api/delivery"), "delivery");
  const summary = recordProjection(record.summary, "delivery summary");
  if (typeof summary.jobs !== "number") invalidProjection("delivery summary");
  recordProjection(summary.outbox, "delivery outbox");
  recordProjection(summary.receipts, "delivery receipts");
  return record as unknown as DeliveryDto;
}

export function dispatchDelivery(): Promise<{ status: string }> {
  return postJSON("/workspace/api/delivery/dispatch", {}, "delivery-dispatch");
}

export function retryFailedDelivery(): Promise<{ status: string }> {
  return postJSON("/workspace/api/delivery/retry", {}, "delivery-retry");
}

export async function listLibraryAssets(): Promise<LibraryListDto> {
  const record = itemsProjection<LibraryAssetDto>(await getJSON<unknown>("/workspace/api/library"), "library");
  requireItemFields(record.items, ["source_name", "raw_sha256", "retention", "conversion_state"], "library item");
  if (record.items.some((item) => typeof item.size_bytes !== "number")) invalidProjection("library item");
  return record as unknown as LibraryListDto;
}

export async function downloadLibraryAsset(rawSha256: string): Promise<Blob> {
  const response = await (await runtimeClient()).requestRaw(
    `/workspace/api/library/${encodeURIComponent(rawSha256)}/content`,
  );
  return response.blob();
}

export async function listResearchCandidates(): Promise<{ items: ResearchCandidateDto[] }> {
  const record = itemsProjection<ResearchCandidateDto>(await getJSON<unknown>("/workspace/api/research"), "research candidates");
  requireItemFields(record.items, ["source"], "research candidate");
  return record;
}

export function approveResearchCandidate(source: string): Promise<Record<string, unknown>> {
  return postJSON("/workspace/api/research/approve", {
    command_id: commandId("research"), source,
  });
}

export async function getActivityJobs(): Promise<ActivityJobsDto> {
  const record = recordProjection(await getJSON<unknown>("/workspace/api/jobs"), "jobs");
  if (!Array.isArray(record.jobs)) invalidProjection("jobs");
  return record as unknown as ActivityJobsDto;
}

export async function getMachineKnowledge(): Promise<MachineKnowledgeListDto> {
  const record = itemsProjection<MachineKnowledgeDto>(await getJSON<unknown>("/workspace/api/runtime/knowledge"), "machine knowledge");
  requireItemFields(record.items, ["title", "content", "lifecycle"], "machine knowledge item");
  return record as unknown as MachineKnowledgeListDto;
}

export async function listMachineKnowledgeCandidates(): Promise<{ items: MachineKnowledgeCandidateDto[] }> {
  const record = itemsProjection<MachineKnowledgeCandidateDto>(await getJSON<unknown>("/workspace/api/runtime/candidates"), "machine knowledge candidates");
  requireItemFields(record.items, ["title", "content", "lifecycle", "version", "evidence_source"], "machine knowledge candidate");
  return record;
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

export async function getSetupStatus(): Promise<SetupStatusDto> {
  return recordProjection(await getJSON<unknown>("/api/v1/setup/status"), "setup status") as SetupStatusDto;
}

export async function preflightSetup(payload: SetupRequestDto): Promise<SetupPreflightDto> {
  const record = recordProjection(await postJSON<unknown>("/api/v1/setup/preflight", payload), "setup preflight");
  if (typeof record.ready !== "boolean" || !["quick", "advanced"].includes(String(record.mode))) invalidProjection("setup preflight");
  recordProjection(record.domains, "setup domains");
  recordProjection(record.library_health, "setup library health");
  return record as unknown as SetupPreflightDto;
}

export function initializeSetup(
  payload: SetupRequestDto = { mode: "quick" },
): Promise<Record<string, unknown>> {
  return postJSON<Record<string, unknown>>("/api/v1/setup/initialize", payload, "setup");
}


export function createBackup(name: string): Promise<Record<string, unknown>> {
  return postJSON("/workspace/api/backup/create", { name }, "backup");
}

export function verifyBackup(name: string): Promise<Record<string, unknown>> {
  return getJSON<Record<string, unknown>>(
    `/workspace/api/backup/verify?name=${encodeURIComponent(name)}`,
  );
}
