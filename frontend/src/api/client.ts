// The only credential-bearing HTTP client. Desktop credentials remain in the
// invoking WebView process and are never persisted by this module.
import { beginDiagnosticObservation, recordDiagnosticFailure } from "../presentation/diagnostics";
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

export type MachineExecutionRefusal = { execution_state: "EXECUTED_BUT_WITHHELD"; audit_status: "RECORDED" | "FAILED"; audit_task_id: string | null; answer_published: false };
export type MachineAdmissionRefusal = {
  schema:"archeaxis.context-admission-refusal/v1"; reason_code:"RESTORED_GRANT_FENCED";
  execution_state:"NOT_EXECUTED"; execution_scope:"CURRENT_INVOCATION";
  prior_request_execution:"UNVERIFIED"; answer_published:false;
  operation:"answer"|"retest"; knowledge_id:string; client_request_id:string|null; retest_of:string|null;
  request_sha256:string; grant:{document_id:string;version:number;content_sha256:string};
};
export type JobAdmissionRefusal = {
  schema: "archeaxis.job-admission-refusal/v1"; code: "AAK-CAP-001";
  job_id: string; request_id: string; input_ref: string; kind: string; capability: string;
  budget: { deadline_ms: number; split: boolean; words: boolean };
  admission_state: "NOT_ADMITTED"; request_consumed: false; active_execution: false;
  enabled: false; same_request_retry_allowed: true;
};
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code: RuntimeProjection = "unavailable",
    public execution?: MachineExecutionRefusal,
    public jobAdmission?: JobAdmissionRefusal,
    public machineAdmission?: MachineAdmissionRefusal,
    public machineFailure?: {reason_code:string;execution_state:"UNVERIFIED";answer_published:false;diagnostics?:import("./machineFailure").MachineFailureDiagnostics},
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function runtimeProjectionMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return "暂时无法建立本地连接，请重试或查看详细记录。";
  switch (error.code) {
    case "offline":
      return "暂时连接不上本地服务，请稍后重试。";
    case "backend_starting":
      return "本地服务正在启动，请稍候。";
    case "migrating":
      return "正在升级工作区，请等待完成后再继续。";
    case "incompatible":
      if (error.message === "runtime identity is incomplete") return "暂时无法确认本地服务是否适用于这个应用，请查看详细记录。";
      if (error.message.startsWith("product mismatch")) return "当前连接的服务不属于这个应用，请检查后重试。";
      if (error.message.startsWith("API contract mismatch")) return "应用与本地服务的版本不一致，请先检查版本。";
      if (error.message === "runtime schema version is invalid") return "暂时无法读取工作区的版本信息，请查看详细记录。";
      if (error.message === "runtime capabilities are invalid") return "暂时无法确认可用功能，请查看详细记录。";
      return "应用与本地服务暂时不能配合运行，请检查版本。";
    case "unauthorized":
      return "未取得访问本地服务的许可，请重新检查连接。";
    default:
      return "暂时无法建立本地连接，请重试或查看详细记录。";
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

function isFailureLogPath(path:string):boolean {return ["read","append","clear"].some(action=>path===`/api/v1/workspace/operation-failures/${action}`);}
export function createApiClient(baseUrl: string, token: string, scopes: string[] = []) {
  async function requestRaw(path: string, init?: RequestInit): Promise<Response> {
    const observation = beginDiagnosticObservation();
    try {
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
    } catch (error) { if(!isFailureLogPath(path))recordDiagnosticFailure("local_request", error, observation); throw error; }
  }

  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const observation = beginDiagnosticObservation();
    const response = await requestRaw(path, init);
    try { return (await response.json()) as T; }
    catch (error) { if(!isFailureLogPath(path))recordDiagnosticFailure("local_request", error, observation); throw error; }
  }

  async function write<T>(path: string, body: Record<string, unknown>, idempotencyKey: string): Promise<T> {
    if (!token || !scopes.includes(WRITE_SCOPE)) {
      const error = new ApiError(403, "desktop write scope is unavailable", "unauthorized");
      if(!isFailureLogPath(path))recordDiagnosticFailure("local_write", error, beginDiagnosticObservation());
      throw error;
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
