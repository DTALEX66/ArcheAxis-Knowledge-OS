// Real read-only runtime API clients for Workspace/Library/Evidence/AI Assets/Settings.
// Fail-closed: on error the caller shows the message; no mock data is ever mixed in.
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

export interface StatusDto {
  status?: string;
  version?: string;
  workspace_id?: string | null;
  migration_state?: string;
  [k: string]: unknown;
}

async function getJSON<T>(path: string, baseUrl = ""): Promise<T> {
  const res = await fetch(`${baseUrl}${path}`);
  if (!res.ok) {
    throw new Error(`${path} -> ${res.status}`);
  }
  return (await res.json()) as T;
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

export function getMachineKnowledge(): Promise<Record<string, unknown>> {
  return getJSON<Record<string, unknown>>("/api/runtime/knowledge");
}

export function getSetupStatus(): Promise<Record<string, unknown>> {
  return getJSON<Record<string, unknown>>("/api/v1/setup/status");
}
