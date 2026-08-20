// Real runtime API clients for Workspace/Library/Evidence/AI Assets/Settings.
// Every request shares the handshake client; no second unauthenticated client
// or hard-coded runtime port is allowed.
import { createApiClient, type ApiClient } from "./client";
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

export interface MachineKnowledgeDto {
  title: string;
  content: string;
  lifecycle: "approved";
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

declare global {
  interface Window {
    __TAURI__?: { core?: { invoke: <T>(command: string) => Promise<T> } };
  }
}

let clientPromise: Promise<ApiClient> | null = null;

// Recovery Shell calls this after a failed launch/handshake. It drops only an
// in-memory rejected client; no endpoint or token is persisted in the UI.
export function resetRuntimeClient(): void {
  clientPromise = null;
}

export async function retryDesktopBackend(): Promise<void> {
  const invoke = window.__TAURI__?.core?.invoke;
  if (invoke) await invoke("retry_backend");
}

async function runtimeClient(): Promise<ApiClient> {
  if (!clientPromise) {
    clientPromise = (async () => {
      const invoke = window.__TAURI__?.core?.invoke;
      const client = !invoke
        ? createApiClient("", "")
        : await (async () => {
          const backend = await invoke<{ port: number; token: string }>("backend_info");
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

async function getJSON<T>(path: string): Promise<T> {
  return (await runtimeClient()).request<T>(path);
}

export function listEvidenceAnchors(limit = 50): Promise<EvidenceListDto> {
  return getJSON<EvidenceListDto>(`/api/evidence/anchors?limit=${limit}`);
}

export function getStatus(): Promise<StatusDto> {
  return getJSON<StatusDto>("/api/status");
}

export function getHome(): Promise<Record<string, unknown>> {
  return getJSON<Record<string, unknown>>("/api/v1/home");
}

export function listLibraryAssets(): Promise<LibraryListDto> {
  return getJSON<LibraryListDto>("/workspace/api/library");
}

export function getActivityJobs(): Promise<ActivityJobsDto> {
  return getJSON<ActivityJobsDto>("/workspace/api/jobs");
}

export function getMachineKnowledge(): Promise<MachineKnowledgeListDto> {
  return getJSON<MachineKnowledgeListDto>("/workspace/api/runtime/knowledge");
}

export function getSetupStatus(): Promise<Record<string, unknown>> {
  return getJSON<Record<string, unknown>>("/api/v1/setup/status");
}

export async function initializeSetup(): Promise<Record<string, unknown>> {
  return (await runtimeClient()).request<Record<string, unknown>>(
    "/api/v1/setup/initialize", { method: "POST" },
  );
}
