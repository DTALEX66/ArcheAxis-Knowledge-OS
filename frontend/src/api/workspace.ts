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
  format?: string;
  engine?: string | null;
  error_reason?: string | null;
  converted_char_count?: number | null;
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

const SETUP_DOMAIN_IDS = [
  "source_archive",
  "evidence_ledger",
  "human_learning_vault",
  "ai_asset_vault",
] as const;

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

function numberField(record: Record<string, unknown>, field: string, label: string): number {
  if (typeof record[field] !== "number" || !Number.isFinite(record[field])) invalidProjection(label);
  return record[field] as number;
}

function booleanField(record: Record<string, unknown>, field: string, label: string): boolean {
  if (typeof record[field] !== "boolean") invalidProjection(label);
  return record[field] as boolean;
}

function numericRecord(value: unknown, label: string): Record<string, number> {
  const record = recordProjection(value, label);
  if (Object.values(record).some((item) => typeof item !== "number" || !Number.isFinite(item) || item < 0)) {
    invalidProjection(label);
  }
  return record as Record<string, number>;
}

function stringRecord(value: unknown, label: string): Record<string, string> {
  const record = recordProjection(value, label);
  if (Object.values(record).some((item) => typeof item !== "string")) invalidProjection(label);
  return record as Record<string, string>;
}

function nestedNumericRecord(value: unknown, label: string): Record<string, Record<string, number>> {
  const record = recordProjection(value, label);
  for (const [key, nested] of Object.entries(record)) numericRecord(nested, `${label} ${key}`);
  return record as Record<string, Record<string, number>>;
}

function requireItemFields(items: unknown[], fields: string[], label: string): void {
  for (const item of items) {
    const record = recordProjection(item, label);
    for (const field of fields) stringField(record, field, label);
  }
}

function validateRelease(value: unknown, label: string): Record<string, unknown> {
  const release = recordProjection(value, label);
  stringField(release, "version", label);
  stringField(release, "status", label);
  booleanField(release, "public", label);
  return release;
}

function validateSetupStatusRecord(record: Record<string, unknown>, label: string): void {
  stringField(record, "schema_version", label);
  booleanField(record, "ready", label);
  stringField(record, "workspace_root", label);
  if (!(record.workspace_id === null || typeof record.workspace_id === "string")) invalidProjection(label);
  if (!Array.isArray(record.steps) || record.steps.length === 0) invalidProjection(label);
  requireItemFields(record.steps, ["id", "state", "message", "action_hint"], `${label} step`);
  if (record.ready === true && record.steps.some((step) => !["ready", "completed"].includes(String((step as Record<string, unknown>).state)))) {
    invalidProjection(label);
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
  for (const item of record.items) {
    if (!/^[0-9a-f]{64}$/i.test(item.raw_sha256)) invalidProjection("evidence anchor");
    const locator = recordProjection(item.locator, "evidence anchor locator");
    if (locator.page !== undefined && (typeof locator.page !== "number" || !Number.isInteger(locator.page) || locator.page < 1)) invalidProjection("evidence anchor locator");
  }
  if (typeof record.count !== "number" || !(record.next_cursor === null || typeof record.next_cursor === "string")) invalidProjection("evidence anchors");
  return record as unknown as EvidenceListDto;
}

export async function listEvidenceBundles(limit = 50): Promise<{ items: EvidenceBundleSummaryDto[] }> {
  const record = itemsProjection<EvidenceBundleSummaryDto>(await getJSON<unknown>(`/workspace/api/evidence/bundles?limit=${limit}`), "evidence bundles");
  requireItemFields(record.items, ["bundle_id", "claim_id", "created_at"], "evidence bundle");
  if (record.items.some((item) => !(item.review_decision === null || typeof item.review_decision === "string"))) invalidProjection("evidence bundle");
  return record;
}

export async function getEvidenceBundleInspection(bundleId: string): Promise<EvidenceBundleInspectionDto> {
  const record = recordProjection(await getJSON<unknown>(
    `/workspace/api/evidence/bundles/${encodeURIComponent(bundleId)}/inspection`,
  ), "evidence bundle inspection");
  for (const field of ["entries", "review_history", "rights", "scopes", "version_history"]) {
    if (!Array.isArray(record[field])) invalidProjection("evidence bundle inspection");
  }
  for (const field of ["bundle_id", "claim_id", "fingerprint"]) stringField(record, field, "evidence bundle inspection");
  if ((record.rights as unknown[]).some((item) => typeof item !== "string") || (record.scopes as unknown[]).some((item) => typeof item !== "string")) invalidProjection("evidence bundle inspection");
  for (const item of record.entries as unknown[]) recordProjection(item, "evidence bundle entry");
  for (const item of record.review_history as unknown[]) {
    const review = recordProjection(item, "evidence bundle review");
    for (const field of ["decision", "reviewer_id", "reviewed_at", "rationale"]) stringField(review, field, "evidence bundle review");
  }
  if (record.latest_review !== null) {
    const review = recordProjection(record.latest_review, "evidence bundle latest review");
    for (const field of ["decision", "reviewer_id", "reviewed_at", "rationale"]) stringField(review, field, "evidence bundle latest review");
  }
  for (const item of record.version_history as unknown[]) {
    const version = recordProjection(item, "evidence bundle version");
    for (const field of ["version_id", "canonical_key", "lifecycle_status", "created_at"]) stringField(version, field, "evidence bundle version");
    if (!(version.parent_version_id === null || typeof version.parent_version_id === "string")) invalidProjection("evidence bundle version");
    if (version.conflict !== null) {
      const conflict = recordProjection(version.conflict, "evidence bundle conflict");
      stringField(conflict, "id", "evidence bundle conflict");
      stringField(conflict, "status", "evidence bundle conflict");
    }
  }
  if (typeof record.conflict !== "boolean") invalidProjection("evidence bundle inspection");
  return record as unknown as EvidenceBundleInspectionDto;
}

export async function getStatus(): Promise<StatusDto> {
  const record = recordProjection(await getJSON<unknown>("/workspace/api/status"), "workspace status");
  stringField(record, "schema_version", "workspace status");
  stringField(record, "observed_at", "workspace status");
  validateRelease(record.release, "workspace status release");
  stringRecord(record.components, "workspace status components");
  numericRecord(record.migrations, "workspace status migrations");
  nestedNumericRecord(record.counts, "workspace status counts");
  stringRecord(record.capabilities, "workspace status capabilities");
  return record as StatusDto;
}

export async function getHome(): Promise<Record<string, unknown>> {
  const record = recordProjection(await getJSON<unknown>("/workspace/api/v1/home"), "workspace home");
  validateRelease(record.release, "workspace home release");
  nestedNumericRecord(record.counts, "workspace home counts");
  stringRecord(record.capabilities, "workspace home capabilities");
  stringRecord(record.components, "workspace home components");
  if (!Array.isArray(record.recent_activity)) invalidProjection("workspace home activity");
  requireItemFields(record.recent_activity, ["public_ref", "kind", "label", "state", "updated_at"], "workspace home activity");
  return record;
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
  const jobs = numberField(summary, "jobs", "delivery summary");
  const outbox = numericRecord(summary.outbox, "delivery outbox");
  const receipts = numericRecord(summary.receipts, "delivery receipts");
  if (jobs < 0 || Object.values(outbox).reduce((sum, item) => sum + item, 0) !== jobs || Object.values(receipts).reduce((sum, item) => sum + item, 0) !== jobs) invalidProjection("delivery summary");
  return record as unknown as DeliveryDto;
}

async function deliveryCommand(path: string, prefix: string, allowed: string[]): Promise<{ status: string }> {
  const record = recordProjection(await postJSON<unknown>(path, {}, prefix), "delivery command");
  const status = stringField(record, "status", "delivery command");
  if (!allowed.includes(status)) invalidProjection("delivery command");
  return { status };
}

export function dispatchDelivery(): Promise<{ status: string }> {
  return deliveryCommand("/workspace/api/delivery/dispatch", "delivery-dispatch", ["idle", "delivered", "failed"]);
}

export function retryFailedDelivery(): Promise<{ status: string }> {
  return deliveryCommand("/workspace/api/delivery/retry", "delivery-retry", ["idle", "requeued"]);
}

export async function listLibraryAssets(): Promise<LibraryListDto> {
  const record = itemsProjection<LibraryAssetDto>(await getJSON<unknown>("/workspace/api/library"), "library");
  requireItemFields(record.items, ["source_name", "raw_sha256", "retention", "conversion_state"], "library item");
  if (record.items.some((item) => typeof item.size_bytes !== "number")) invalidProjection("library item");
  for (const item of record.items) {
    if (!/^[0-9a-f]{64}$/i.test(item.raw_sha256)) invalidProjection("library item");
    if (item.format !== undefined && typeof item.format !== "string") invalidProjection("library item");
    if (item.engine !== undefined && item.engine !== null && typeof item.engine !== "string") invalidProjection("library item");
    if (item.error_reason !== undefined && item.error_reason !== null && typeof item.error_reason !== "string") invalidProjection("library item");
    if (item.converted_char_count !== undefined && item.converted_char_count !== null && typeof item.converted_char_count !== "number") invalidProjection("library item");
    if (item.converted_char_count !== undefined && item.converted_char_count !== null && item.converted_char_count < 0) invalidProjection("library item");
  }
  return record as unknown as LibraryListDto;
}

export async function downloadLibraryAsset(rawSha256: string): Promise<Blob> {
  const response = await (await runtimeClient()).requestRaw(
    `/workspace/api/library/${encodeURIComponent(rawSha256)}/content`,
  );
  return response.blob();
}

export async function downloadPdfAsset(rawSha256: string): Promise<Blob> {
  if (!/^[0-9a-f]{64}$/i.test(rawSha256)) invalidProjection("PDF content identity");
  const response = await (await runtimeClient()).requestRaw(
    `/workspace/api/pdf/sha256:${rawSha256.toLowerCase()}`,
  );
  const blob = await response.blob();
  if (blob.type !== "application/pdf") invalidProjection("PDF content");
  return blob;
}

export async function listResearchCandidates(): Promise<{ items: ResearchCandidateDto[] }> {
  const record = itemsProjection<ResearchCandidateDto>(await getJSON<unknown>("/workspace/api/research"), "research candidates");
  requireItemFields(record.items, ["source"], "research candidate");
  return record;
}

export async function approveResearchCandidate(source: string): Promise<Record<string, unknown>> {
  const record = recordProjection(await postJSON<unknown>("/workspace/api/research/approve", {
    command_id: commandId("research"), source,
  }), "research approval");
  const status = stringField(record, "status", "research approval");
  if (!["candidate", "approved"].includes(status)) invalidProjection("research approval");
  return record;
}

export async function getActivityJobs(): Promise<ActivityJobsDto> {
  const record = recordProjection(await getJSON<unknown>("/workspace/api/jobs"), "jobs");
  if (!Array.isArray(record.jobs)) invalidProjection("jobs");
  requireItemFields(record.jobs, ["activity", "state", "delivery_state", "updated_at"], "job");
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

async function machineKnowledgeCommand(path: string, prefix: string, title: string, expectedStatus: string): Promise<Record<string, unknown>> {
  const record = recordProjection(await postJSON<unknown>(path, {
    command_id: commandId(prefix), title,
  }), "machine knowledge command");
  if (stringField(record, "title", "machine knowledge command") !== title || stringField(record, "status", "machine knowledge command") !== expectedStatus) invalidProjection("machine knowledge command");
  return record;
}

export function approveMachineKnowledge(title: string): Promise<Record<string, unknown>> {
  return machineKnowledgeCommand("/workspace/api/runtime/approve", "runtime-approve", title, "approved");
}

export function deprecateMachineKnowledge(title: string): Promise<Record<string, unknown>> {
  return machineKnowledgeCommand("/workspace/api/runtime/deprecate", "runtime-deprecate", title, "deprecated");
}

export async function getSetupStatus(): Promise<SetupStatusDto> {
  const record = recordProjection(await getJSON<unknown>("/api/v1/setup/status"), "setup status");
  validateSetupStatusRecord(record, "setup status");
  return record as SetupStatusDto;
}

export async function preflightSetup(payload: SetupRequestDto): Promise<SetupPreflightDto> {
  const record = recordProjection(await postJSON<unknown>("/api/v1/setup/preflight", payload), "setup preflight");
  if (typeof record.ready !== "boolean" || !["quick", "advanced"].includes(String(record.mode))) invalidProjection("setup preflight");
  const domains = recordProjection(record.domains, "setup domains");
  const health = recordProjection(record.library_health, "setup library health");
  for (const domain of SETUP_DOMAIN_IDS) {
    if (typeof domains[domain] !== "string" || !(domains[domain] as string).trim()) invalidProjection("setup domains");
    const item = recordProjection(health[domain], `setup health ${domain}`);
    numberField(item, "free_bytes", `setup health ${domain}`);
    booleanField(item, "readonly", `setup health ${domain}`);
    stringField(item, "filesystem", `setup health ${domain}`);
    stringField(item, "removable", `setup health ${domain}`);
  }
  return record as unknown as SetupPreflightDto;
}

export async function initializeSetup(
  payload: SetupRequestDto = { mode: "quick" },
): Promise<Record<string, unknown>> {
  const record = recordProjection(await postJSON<unknown>("/api/v1/setup/initialize", payload, "setup"), "setup initialize");
  if (record.initialized !== true) invalidProjection("setup initialize");
  for (const field of ["workspace_id", "workspace_root", "mode"]) stringField(record, field, "setup initialize");
  if (!["quick", "advanced"].includes(String(record.mode))) invalidProjection("setup initialize");
  const domains = recordProjection(record.domains, "setup initialize domains");
  const health = recordProjection(record.library_health, "setup initialize library health");
  for (const domain of SETUP_DOMAIN_IDS) {
    stringField(domains, domain, "setup initialize domains");
    recordProjection(health[domain], `setup initialize health ${domain}`);
  }
  const status = recordProjection(record.status, "setup initialize status");
  validateSetupStatusRecord(status, "setup initialize status");
  return record;
}


export async function createBackup(name: string): Promise<Record<string, unknown>> {
  const record = recordProjection(await postJSON<unknown>("/workspace/api/backup/create", { name }, "backup"), "backup create");
  numberField(record, "file_count", "backup create");
  return record;
}

export async function verifyBackup(name: string): Promise<Record<string, unknown>> {
  const record = recordProjection(await getJSON<unknown>(
    `/workspace/api/backup/verify?name=${encodeURIComponent(name)}`,
  ), "backup verify");
  booleanField(record, "valid", "backup verify");
  return record;
}

// ── Pipeline: multi-format intake ──────────────────────────────────────────

export interface IntakeResultDto {
  source_type: "file" | "web" | "github_repository";
  requires_human_review: boolean;
  file_name?: string | null;
  format?: string | null;
  engine?: string | null;
  content_preview?: string | null;
  char_count?: number | null;
  raw_sha256?: string | null;
  source_count?: number | null;
  claim_count?: number | null;
  evidence_count?: number | null;
}

function validateIntakeResult(value: unknown): IntakeResultDto {
  const record = recordProjection(value, "intake result");
  if (!["file", "web", "github_repository"].includes(String(record.source_type))) invalidProjection("intake result");
  booleanField(record, "requires_human_review", "intake result");
  for (const field of ["file_name", "format", "engine", "content_preview", "raw_sha256"]) {
    if (record[field] !== undefined && record[field] !== null && typeof record[field] !== "string") invalidProjection("intake result");
  }
  for (const field of ["char_count", "source_count", "claim_count", "evidence_count"]) {
    if (record[field] !== undefined && record[field] !== null && (typeof record[field] !== "number" || !Number.isFinite(record[field] as number))) invalidProjection("intake result");
  }
  if (record.raw_sha256 !== undefined && record.raw_sha256 !== null && !/^[0-9a-f]{64}$/i.test(String(record.raw_sha256))) invalidProjection("intake result");
  return record as unknown as IntakeResultDto;
}

export async function intakeUrl(url: string): Promise<IntakeResultDto> {
  return validateIntakeResult(await postJSON<unknown>("/workspace/api/intake/url", { url }, "intake"));
}

export async function intakeUpload(file: File): Promise<IntakeResultDto> {
  const form = new FormData();
  form.append("file", file, file.name);
  const response = await (await runtimeClient()).requestRaw("/workspace/api/intake/upload", {
    method: "POST",
    body: form,
  });
  return validateIntakeResult(await response.json());
}

// ── Pipeline: controllable batch import ────────────────────────────────────

export interface BatchTaskResultDto {
  status: "completed" | "failed";
  result_digest?: string;
  error?: string;
}

export interface BatchStatusDto {
  schema_version: string;
  batch_id: string;
  state: "idle" | "running" | "paused" | "finished" | "shutdown";
  total: number;
  completed: number;
  failed: number;
  skipped: number;
  created_at: string;
  results?: Record<string, BatchTaskResultDto>;
  attempts?: Record<string, number>;
}

function validateBatchStatus(value: unknown): BatchStatusDto {
  const record = recordProjection(value, "batch status");
  stringField(record, "batch_id", "batch status");
  if (!["idle", "running", "paused", "finished", "shutdown"].includes(String(record.state))) invalidProjection("batch status");
  for (const field of ["total", "completed", "failed", "skipped"]) numberField(record, field, "batch status");
  if (record.results !== undefined) {
    const results = recordProjection(record.results, "batch results");
    for (const [task, entry] of Object.entries(results)) {
      const item = recordProjection(entry, `batch result ${task}`);
      stringField(item, "status", `batch result ${task}`);
      if (!["completed", "failed"].includes(String(item.status))) invalidProjection(`batch result ${task}`);
    }
  }
  if (record.attempts !== undefined) numericRecord(record.attempts, "batch attempts");
  return record as unknown as BatchStatusDto;
}

export interface BatchStartRequest {
  batch_id: string;
  source_dir: string;
  pattern?: string;
  max_files?: number;
  rate_per_second?: number | null;
  max_retries?: number;
}

export async function startBatchImport(payload: BatchStartRequest): Promise<BatchStatusDto> {
  const record = recordProjection(await postJSON<unknown>("/workspace/api/batch/import", { ...payload }, "batch"), "batch start");
  stringField(record, "batch_id", "batch start");
  if (!["idle", "running", "paused"].includes(String(record.state))) invalidProjection("batch start");
  numberField(record, "total", "batch start");
  return record as unknown as BatchStatusDto;
}

export async function getBatchStatus(batchId: string): Promise<BatchStatusDto> {
  return validateBatchStatus(await getJSON<unknown>(`/workspace/api/batch/${encodeURIComponent(batchId)}/status`));
}

async function batchControl(batchId: string, action: string, prefix: string): Promise<BatchStatusDto> {
  const record = recordProjection(await postJSON<unknown>(
    `/workspace/api/batch/${encodeURIComponent(batchId)}/${action}`, {}, prefix,
  ), `batch ${action}`);
  if (stringField(record, "batch_id", `batch ${action}`) !== batchId) invalidProjection(`batch ${action}`);
  if (!["idle", "running", "paused", "finished", "shutdown"].includes(String(record.state))) invalidProjection(`batch ${action}`);
  return record as unknown as BatchStatusDto;
}

export function pauseBatch(batchId: string): Promise<BatchStatusDto> {
  return batchControl(batchId, "pause", "batch-pause");
}

export function resumeBatch(batchId: string): Promise<BatchStatusDto> {
  return batchControl(batchId, "resume", "batch-resume");
}

export function shutdownBatch(batchId: string): Promise<BatchStatusDto> {
  return batchControl(batchId, "shutdown", "batch-shutdown");
}

// ── Pipeline: converted content and conversion runs ────────────────────────

export interface ConvertedContentDto {
  schema_version: string;
  raw_sha256: string;
  engine: string;
  version: number;
  block_count: number;
  content: string;
}

export interface ConversionRunDto {
  schema_version: string;
  raw_sha256: string;
  engine: string;
  version: number;
  block_count: number;
  loss_notes: string[];
  preview: string;
}

function validateRawSha256(rawSha256: string): void {
  if (!/^[0-9a-f]{64}$/i.test(rawSha256)) invalidProjection("converted content identity");
}

export async function getConvertedContent(rawSha256: string): Promise<ConvertedContentDto> {
  validateRawSha256(rawSha256);
  const record = recordProjection(await getJSON<unknown>(
    `/workspace/api/library/${rawSha256}/converted`,
  ), "converted content");
  stringField(record, "raw_sha256", "converted content");
  stringField(record, "engine", "converted content");
  numberField(record, "version", "converted content");
  numberField(record, "block_count", "converted content");
  stringField(record, "content", "converted content");
  return record as unknown as ConvertedContentDto;
}

export async function getConversionRun(rawSha256: string): Promise<ConversionRunDto> {
  validateRawSha256(rawSha256);
  const record = recordProjection(await getJSON<unknown>(
    `/workspace/api/library/${rawSha256}/conversion-run`,
  ), "conversion run");
  stringField(record, "raw_sha256", "conversion run");
  stringField(record, "engine", "conversion run");
  numberField(record, "version", "conversion run");
  numberField(record, "block_count", "conversion run");
  if (!Array.isArray(record.loss_notes) || record.loss_notes.some((note) => typeof note !== "string")) invalidProjection("conversion run");
  stringField(record, "preview", "conversion run");
  return record as unknown as ConversionRunDto;
}

// ── Vault: approved-root knowledge base workbench ──────────────────────────

export interface VaultFileEntryDto {
  relative_path: string;
  kind: "markdown" | "canvas" | "attachment";
  file_size: number;
  source_hash: string;
  mime_type: string;
  frontmatter: Record<string, unknown>;
}

export interface VaultInspectDto {
  schema_version: string;
  root_name: string;
  files: VaultFileEntryDto[];
  loss_report: Record<string, unknown>;
}

export interface VaultFileDto {
  schema_version: string;
  relative_path: string;
  raw_text: string;
  frontmatter: Record<string, unknown>;
  body: string;
  is_canvas: boolean;
  source_hash: string;
  loss_report: Record<string, unknown>;
  canvas?: Record<string, unknown>;
}

export interface VaultSearchResultDto {
  relative_path: string;
  snippet: string;
  source_hash: string;
}

export interface VaultSearchDto {
  schema_version: string;
  query: string;
  results: VaultSearchResultDto[];
}

export interface VaultWriteReceiptDto {
  schema_version: string;
  relative_path: string;
  source_hash: string;
  expected_hash_checked: boolean;
}

export interface VaultBackupEntryDto {
  backup_name: string;
  file_size: number;
  modified: number;
}

export interface VaultBackupsDto {
  schema_version: string;
  relative_path: string;
  backups: VaultBackupEntryDto[];
}

function validateVaultFileEntry(item: unknown, label: string): VaultFileEntryDto {
  const record = recordProjection(item, label);
  stringField(record, "relative_path", label);
  if (!["markdown", "canvas", "attachment"].includes(String(record.kind))) invalidProjection(label);
  numberField(record, "file_size", label);
  stringField(record, "source_hash", label);
  if (!/^[0-9a-f]{64}$/i.test(String(record.source_hash))) invalidProjection(label);
  stringField(record, "mime_type", label);
  return record as unknown as VaultFileEntryDto;
}

function validateVaultRoot(root: string): void {
  if (!root.trim() || root.length > 4096) invalidProjection("vault root");
}

export async function inspectVault(root: string): Promise<VaultInspectDto> {
  validateVaultRoot(root);
  const record = recordProjection(await postJSON<unknown>("/workspace/api/vault/inspect", { root }, "vault"), "vault inspect");
  stringField(record, "schema_version", "vault inspect");
  stringField(record, "root_name", "vault inspect");
  if (!Array.isArray(record.files)) invalidProjection("vault inspect");
  record.files.forEach((entry) => validateVaultFileEntry(entry, "vault file"));
  recordProjection(record.loss_report, "vault loss report");
  return record as unknown as VaultInspectDto;
}

export async function readVaultFile(root: string, relativePath: string): Promise<VaultFileDto> {
  validateVaultRoot(root);
  const record = recordProjection(await postJSON<unknown>(
    "/workspace/api/vault/file", { root, relative_path: relativePath }, "vault",
  ), "vault file");
  stringField(record, "schema_version", "vault file");
  stringField(record, "relative_path", "vault file");
  stringField(record, "raw_text", "vault file");
  stringField(record, "source_hash", "vault file");
  booleanField(record, "is_canvas", "vault file");
  recordProjection(record.frontmatter, "vault frontmatter");
  stringField(record, "body", "vault file");
  return record as unknown as VaultFileDto;
}

export async function searchVault(root: string, query: string): Promise<VaultSearchDto> {
  validateVaultRoot(root);
  const record = recordProjection(await postJSON<unknown>(
    "/workspace/api/vault/search", { root, query }, "vault",
  ), "vault search");
  stringField(record, "schema_version", "vault search");
  stringField(record, "query", "vault search");
  if (!Array.isArray(record.results)) invalidProjection("vault search");
  for (const item of record.results) {
    const result = recordProjection(item, "vault search result");
    stringField(result, "relative_path", "vault search result");
    stringField(result, "snippet", "vault search result");
    stringField(result, "source_hash", "vault search result");
  }
  return record as unknown as VaultSearchDto;
}

export async function writeVaultFile(
  root: string,
  relativePath: string,
  content: string,
  expectedHash?: string | null,
): Promise<VaultWriteReceiptDto> {
  validateVaultRoot(root);
  const record = recordProjection(await postJSON<unknown>(
    "/workspace/api/vault/write",
    { root, relative_path: relativePath, content, expected_hash: expectedHash ?? null },
    "vault-write",
  ), "vault write");
  stringField(record, "schema_version", "vault write");
  stringField(record, "relative_path", "vault write");
  stringField(record, "source_hash", "vault write");
  booleanField(record, "expected_hash_checked", "vault write");
  return record as unknown as VaultWriteReceiptDto;
}

export async function readVaultCanvas(root: string, relativePath: string): Promise<VaultFileDto> {
  validateVaultRoot(root);
  const record = recordProjection(await postJSON<unknown>(
    "/workspace/api/vault/canvas/read", { root, relative_path: relativePath }, "vault",
  ), "vault canvas");
  stringField(record, "schema_version", "vault canvas");
  stringField(record, "source_hash", "vault canvas");
  booleanField(record, "is_canvas", "vault canvas");
  recordProjection(record.canvas, "vault canvas document");
  return record as unknown as VaultFileDto;
}

export async function writeVaultCanvas(
  root: string,
  relativePath: string,
  canvas: Record<string, unknown>,
  expectedHash?: string | null,
): Promise<VaultWriteReceiptDto> {
  validateVaultRoot(root);
  const record = recordProjection(await postJSON<unknown>(
    "/workspace/api/vault/canvas/write",
    { root, relative_path: relativePath, canvas, expected_hash: expectedHash ?? null },
    "vault-canvas-write",
  ), "vault canvas write");
  stringField(record, "schema_version", "vault canvas write");
  stringField(record, "relative_path", "vault canvas write");
  stringField(record, "source_hash", "vault canvas write");
  booleanField(record, "expected_hash_checked", "vault canvas write");
  return record as unknown as VaultWriteReceiptDto;
}

export async function listVaultBackups(root: string, relativePath: string): Promise<VaultBackupsDto> {
  validateVaultRoot(root);
  const record = recordProjection(await postJSON<unknown>(
    "/workspace/api/vault/backups", { root, relative_path: relativePath }, "vault",
  ), "vault backups");
  stringField(record, "schema_version", "vault backups");
  stringField(record, "relative_path", "vault backups");
  if (!Array.isArray(record.backups)) invalidProjection("vault backups");
  for (const item of record.backups) {
    const backup = recordProjection(item, "vault backup");
    stringField(backup, "backup_name", "vault backup");
    numberField(backup, "file_size", "vault backup");
    numberField(backup, "modified", "vault backup");
  }
  return record as unknown as VaultBackupsDto;
}

export async function restoreVaultBackup(
  root: string,
  relativePath: string,
  backupName: string,
): Promise<Record<string, unknown>> {
  validateVaultRoot(root);
  const record = recordProjection(await postJSON<unknown>(
    "/workspace/api/vault/restore",
    { root, relative_path: relativePath, backup_name: backupName },
    "vault-restore",
  ), "vault restore");
  stringField(record, "relative_path", "vault restore");
  return record;
}

// ── Exchange: verifiable open exchange export ──────────────────────────────

export interface ExchangeExportDto {
  destination: string;
  item_count: number;
  manifest_sha256: string;
}

export async function exportExchange(name: string, overwrite = false): Promise<ExchangeExportDto> {
  const record = recordProjection(await postJSON<unknown>(
    "/workspace/api/exchange/export", { name, overwrite }, "exchange",
  ), "exchange export");
  stringField(record, "destination", "exchange export");
  numberField(record, "item_count", "exchange export");
  stringField(record, "manifest_sha256", "exchange export");
  return record as unknown as ExchangeExportDto;
}

export async function verifyExchange(name = "exchange"): Promise<Record<string, unknown>> {
  const record = recordProjection(await getJSON<unknown>(
    `/workspace/api/exchange/verify?name=${encodeURIComponent(name)}`,
  ), "exchange verify");
  booleanField(record, "valid", "exchange verify");
  return record;
}

// ── Evidence: page-level anchors from the reader ───────────────────────────

export async function createEvidenceAnchor(rawSha256: string, page: number): Promise<{ locator: { page: number } }> {
  if (!/^[0-9a-f]{64}$/i.test(rawSha256)) invalidProjection("evidence anchor identity");
  if (!Number.isInteger(page) || page < 1) invalidProjection("evidence anchor page");
  const record = recordProjection(await postJSON<unknown>(
    "/workspace/api/evidence/anchor",
    {
      raw_sha256: rawSha256,
      source_revision: `original:${rawSha256.slice(0, 24)}`,
      locator: { page },
    },
    "evidence-anchor",
  ), "evidence anchor create");
  const locator = recordProjection(record.locator, "evidence anchor locator");
  if (typeof locator.page !== "number" || !Number.isInteger(locator.page) || locator.page < 1) invalidProjection("evidence anchor locator");
  // Internal anchor_id never crosses the product boundary.
  return { locator: { page: locator.page } };
}
