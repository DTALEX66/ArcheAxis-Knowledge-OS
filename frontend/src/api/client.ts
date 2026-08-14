// Loopback API client (AXW-UI-801). Token is held in memory only — never
// persisted to localStorage (task pack §9.2). Fail-closed on product/api
// contract mismatch.
export interface Handshake {
  product_id: string;
  product_name: string;
  api_contract: string;
  backend_version: string;
  source_commit: string;
  schema_version: number;
  runtime_mode: string;
  workspace_id: string | null;
  capabilities: string[];
  migration_state: string;
}

const EXPECTED_PRODUCT_ID = "archeaxis-workspace";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function createApiClient(baseUrl: string, token: string) {
  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const res = await fetch(`${baseUrl}${path}`, {
      ...init,
      headers: {
        Authorization: `Bearer ${token}`,
        ...(init?.headers ?? {}),
      },
    });
    if (!res.ok) {
      throw new ApiError(res.status, `${path} -> ${res.status}`);
    }
    return (await res.json()) as T;
  }

  async function handshake(): Promise<Handshake> {
    const h = await request<Handshake>("/api/v1/system/handshake");
    if (h.product_id !== EXPECTED_PRODUCT_ID) {
      throw new ApiError(0, `product mismatch: ${h.product_id}`);
    }
    return h;
  }

  return { handshake, request };
}

export type ApiClient = ReturnType<typeof createApiClient>;
