// Native finite business commands only. No URL, method or credential reaches UI.
import { ApiError } from "./client";
import { assertCoreDto, type CoreOperation } from "./generated/core-contract";
import { assertAiAssetDto } from "./generated/ai-asset-contract";
import { assertTeachingDto } from "./generated/teaching-contract";
import { assertCollectionDto } from "./generated/collection-contract";
import { assertUiWorkingState } from "./generated/ui-working-state-contract";
export type { CoreOperation } from "./generated/core-contract";
const teachingResponses: Partial<Record<CoreOperation,string>> = {
  teaching_list:"RecordPage",teaching_get:"RecordView",teaching_create:"WriteReceipt",
  teaching_withdraw:"WithdrawalReceipt",teaching_export:"ExchangeBundle",
  teaching_import_preview:"ImportPreview",teaching_import:"ImportReceipt",
};
const responseSchemas: Partial<Record<CoreOperation, string>> = {
  document_graph: "RelationProjectionDto",
  sources_list: "SourcesListDto", source_jobs: "SourceJobsDto", source_members: "SourceMembersDto", source_pages: "SourcePagesDto", source_original: "OriginalDto", documents_list: "DocumentsListDto",
  document_create: "DocumentDto", document_get: "DocumentDto", document_draft: "DocumentDto",
  document_checks: "DocumentChecksDto", document_check_record: "DocumentCheckDto", document_check_execute: "DocumentCheckDto",
  document_version: "DocumentDto", document_restore: "DocumentDto", anchors_list: "AnchorsListDto", anchor_create: "AnchorDto", anchor_resolve: "AnchorResolutionDto",
  search: "SearchDto", knowledge_get: "KnowledgeDto", learning_items: "LearningItemsDto",
  learning_state: "LearningStateDto", document_export: "DocumentExportDto",
  machine_retest: "MachineRetestDto",
  job_execution_status: "JobExecutionStatusDto", job_execution_cancel: "JobExecutionCancelDto",
  machine_tasks_list: "MachineTasksPageDto",
  machine_contexts_list: "MachineDocumentsPageDto", machine_rubrics_list: "MachineDocumentsPageDto",
  machine_evaluations_list: "MachineDocumentsPageDto", machine_rubric_create: "DocumentDto",
  machine_evaluation_create: "DocumentDto", machine_answer_snapshot: "MachineAnswerSnapshotDto",
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
    const refusal = response.body as Record<string,unknown> | null;
    if (["machine_answer","machine_retest"].includes(operation) && refusal?.schema === "archeaxis.machine-execution-refusal/v1"
      && refusal.execution_state === "EXECUTED_BUT_WITHHELD" && refusal.answer_published === false
      && ((response.status === 403 && refusal.audit_status === "RECORDED" && typeof refusal.audit_task_id === "string" && /^withheld_[a-f0-9]{64}$/.test(refusal.audit_task_id))
        || (response.status === 500 && refusal.audit_status === "FAILED" && refusal.audit_task_id === null))) {
      throw new ApiError(response.status,"推理已经执行，答案未发布。", "unavailable", {
        execution_state:"EXECUTED_BUT_WITHHELD",answer_published:false,
        audit_status:refusal.audit_status as "RECORDED"|"FAILED",audit_task_id:refusal.audit_task_id as string|null,
      });
    }
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
  if (["ui_state_read", "ui_state_write", "ui_state_clear_saved", "ui_state_recover"].includes(operation)) {
    try { return assertUiWorkingState<T>("Read", response.body); }
    catch { throw new ApiError(502, "工作草稿保全回读格式无效，当前编辑内容仍保留。", "incompatible"); }
  }
  try { return operation === "ai_assets_list" || operation === "ai_asset_packet" ? assertAiAssetDto<T>(operation === "ai_assets_list" ? "AiAssetsPage" : "AssetPacketResponse",response.body) : operation === "collection_query" ? assertCollectionDto<T>("CollectionQueryDto",response.body) : teachingResponses[operation] ? assertTeachingDto<T>(teachingResponses[operation]!,response.body) : schema ? assertCoreDto<T>(schema, response.body) : response.body as T; }
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
