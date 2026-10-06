// Native finite business commands only. No URL, method or credential reaches UI.
import { ApiError } from "./client";
import { assertCoreDto, type CoreOperation } from "./generated/core-contract";
export type { CoreOperation } from "./generated/core-contract";
const responseSchemas: Partial<Record<CoreOperation, string>> = {
  sources_list: "SourcesListDto", source_jobs: "SourceJobsDto", source_members: "SourceMembersDto", source_original: "OriginalDto", documents_list: "DocumentsListDto",
  document_create: "DocumentDto", document_get: "DocumentDto", document_draft: "DocumentDto",
  document_checks: "DocumentChecksDto", document_check_record: "DocumentCheckDto", document_check_execute: "DocumentCheckDto",
  document_version: "DocumentDto", document_restore: "DocumentDto", anchors_list: "AnchorsListDto", anchor_create: "AnchorDto",
  search: "SearchDto", knowledge_get: "KnowledgeDto", learning_items: "LearningItemsDto",
  learning_state: "LearningStateDto", document_export: "DocumentExportDto",
};

export async function coreCommand<T>(operation: CoreOperation, payload: Record<string, unknown> = {}): Promise<T> {
  const invoke = window.__TAURI__?.core?.invoke;
  if (!invoke) throw new ApiError(0, "请在本地桌面应用打开此内容。", "offline");
  let result: unknown;
  try { result = await invoke("core_command", { request: { operation, payload } }); }
  catch { throw new ApiError(502, "本地核心暂时无法响应，请保留草稿后重试。", "unavailable"); }
  if (!result || typeof result !== "object") throw new ApiError(502, "本地核心返回格式无效。", "incompatible");
  const response = result as { status?: unknown; body?: unknown };
  if (typeof response.status !== "number" || !Number.isInteger(response.status)) throw new ApiError(502, "本地核心状态无效。", "incompatible");
  if (response.status < 200 || response.status >= 300) {
    // One sentence for every failure sends someone looking in the wrong place: a missing object,
    // a refused argument and a core-side fault need different next actions.
    const reason = response.status === 409 ? "版本已变化，请保留当前草稿并重新读取。"
      : response.status === 401 || response.status === 403 ? "本地核心拒绝了此操作的身份。"
      : response.status === 404 ? `本地核心找不到 ${operation} 所需的对象。`
      : response.status === 429 ? "本地核心繁忙，请稍后重试。"
      : response.status >= 500 ? `本地核心未能完成 ${operation}（${response.status}）。`
      : `本地核心拒绝了 ${operation}（${response.status}）。`;
    throw new ApiError(response.status, reason, response.status === 401 || response.status === 403 ? "unauthorized" : "unavailable");
  }
  const schema = responseSchemas[operation];
  try { return schema ? assertCoreDto<T>(schema, response.body) : response.body as T; }
  catch { throw new ApiError(502, "本地核心内容合同不兼容。", "incompatible"); }
}

export async function verifyCanonicalCore(): Promise<void> {
  const version = await coreCommand<unknown>("system_version");
  if (!version || typeof version !== "object") throw new ApiError(502, "Core identity missing", "incompatible");
  const identity = version as Record<string, unknown>;
  if (identity.runtime !== "archeaxis-api" || identity.contract !== "0.1.0-outline"
    || !Number.isInteger(identity.schema_version) || (identity.schema_version as number) < 1) {
    throw new ApiError(502, "Core identity incompatible", "incompatible");
  }
  const parts=typeof identity.sqlite_version === "string" ? identity.sqlite_version.split(".").map(Number) : [];
  const [major,minor,patch]=parts;
  const fixed=parts.length===3&&parts.every(Number.isInteger)&&(major>3||(major===3&&(minor>51||(minor===51&&patch>=3)||(minor===50&&patch>=7)||(minor===44&&patch>=6))));
  if(!fixed)throw new ApiError(502,"本地核心需更新。","incompatible");
}
