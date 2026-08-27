// The only credential-bearing HTTP client. Desktop credentials remain in the
// invoking WebView process and are never persisted by this module.
export interface Handshake {
  product_id: string;
  product_name: string;
  api_contract: string;
  backend_version: string;
  source_commit: string;
  schema_version: number;
  runtime_mode: string;
  workspace_id: string;
  capabilities: string[];
  migration_state: string;
}

export type RuntimeProjection =
  | "offline"
  | "backend_starting"
  | "migrating"
  | "incompatible"
  | "unauthorized"
  | "unavailable";

const EXPECTED_PRODUCT_ID = "archeaxis-workspace";
const EXPECTED_API_CONTRACT = "1.x";
const WRITE_SCOPE = "workspace:write";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code: RuntimeProjection = "unavailable",
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function runtimeProjectionMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return "已认证的本地核心握手失败。";
  switch (error.code) {
    case "offline":
      return "本地核心当前离线。";
    case "backend_starting":
      return "本地核心仍在启动。";
    case "migrating":
      return "工作区正在迁移。";
    case "incompatible":
      if (error.message === "runtime identity is incomplete") return "本地核心身份字段不完整。";
      if (error.message.startsWith("product mismatch")) return "本地核心产品身份不匹配。";
      if (error.message.startsWith("API contract mismatch")) return "本地核心接口契约不匹配。";
      if (error.message === "runtime schema version is invalid") return "本地核心数据结构版本无效。";
      if (error.message === "runtime capabilities are invalid") return "本地核心能力声明无效。";
      return "本地核心与当前桌面版本不兼容。";
    case "unauthorized":
      return "桌面本地授权被拒绝。";
    default:
      return "已认证的本地核心握手失败。";
  }
}

function unavailableCode(status: number): RuntimeProjection {
  if (status === 401 || status === 403) return "unauthorized";
  if (status === 503) return "backend_starting";
  return "unavailable";
}

function incompatible(message: string): never {
  throw new ApiError(0, message, "incompatible");
}

function nonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function validateHandshake(value: unknown): Handshake {
  if (!value || typeof value !== "object") incompatible("runtime handshake is invalid");
  const handshake = value as Record<string, unknown>;
  if (handshake.product_id !== EXPECTED_PRODUCT_ID) incompatible(`product mismatch: ${String(handshake.product_id)}`);
  if (!nonEmptyString(handshake.product_name)) incompatible("product identity is incomplete");
  if (handshake.api_contract !== EXPECTED_API_CONTRACT) incompatible(`API contract mismatch: ${String(handshake.api_contract)}`);
  if (
    !nonEmptyString(handshake.backend_version)
    || !nonEmptyString(handshake.source_commit)
    || !nonEmptyString(handshake.runtime_mode)
    || !nonEmptyString(handshake.workspace_id)
  ) {
    incompatible("runtime identity is incomplete");
  }
  if (!Number.isInteger(handshake.schema_version) || (handshake.schema_version as number) < 1) {
    incompatible("runtime schema version is invalid");
  }
  if (!Array.isArray(handshake.capabilities) || handshake.capabilities.some((item) => typeof item !== "string")) {
    incompatible("runtime capabilities are invalid");
  }
  if (handshake.migration_state === "migrating") {
    throw new ApiError(503, "workspace migration is in progress", "migrating");
  }
  if (handshake.migration_state !== "ready") {
    throw new ApiError(503, "workspace migration is unavailable", "backend_starting");
  }
  return handshake as unknown as Handshake;
}

export function createApiClient(baseUrl: string, token: string, scopes: string[] = []) {
  async function requestRaw(path: string, init?: RequestInit): Promise<Response> {
    let response: Response;
    try {
      response = await fetch(`${baseUrl}${path}`, {
        ...init,
        headers: {
          ...(token ? { "X-ArcheAxis-Launch-Token": token } : {}),
          ...(init?.headers ?? {}),
        },
      });
    } catch {
      throw new ApiError(0, "local Core is offline", "offline");
    }
    if (!response.ok) {
      throw new ApiError(response.status, `${path} -> ${response.status}`, unavailableCode(response.status));
    }
    return response;
  }

  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await requestRaw(path, init);
    return (await response.json()) as T;
  }

  async function write<T>(path: string, body: Record<string, unknown>, idempotencyKey: string): Promise<T> {
    if (!token || !scopes.includes(WRITE_SCOPE)) {
      throw new ApiError(403, "desktop write scope is unavailable", "unauthorized");
    }
    return request<T>(path, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-ArcheAxis-Scopes": scopes.join(" "),
        "Idempotency-Key": idempotencyKey,
      },
      body: JSON.stringify(body),
    });
  }

  async function handshake(): Promise<Handshake> {
    return validateHandshake(await request<unknown>("/api/v1/system/handshake"));
  }

  return { handshake, request, requestRaw, write };
}

export type ApiClient = ReturnType<typeof createApiClient>;
