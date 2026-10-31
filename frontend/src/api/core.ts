// Native finite business commands only. No URL, method or credential reaches UI.
import { assertMaterialQuestionDto } from "./generated/material-question";
import { ApiError } from "./client";
import { readMachineFailureDiagnostics } from "./machineFailure";
import { jobAdmissionRefusal } from "./jobAdmission";
import { readMachineAdmissionRefusal } from "./machineAdmission";
import { assertCoreDto, type CoreOperation, type SemanticSearchDto } from "./generated/core-contract";
import { assertAiAssetDto } from "./generated/ai-asset-contract";
import { assertTeachingDto } from "./generated/teaching-contract";
import { assertCollectionDto } from "./generated/collection-contract";
import { assertUiWorkingState } from "./generated/ui-working-state-contract";
import { assertLayoutDto } from "./generated/layout-contract";
import { assertHandoffDto } from "./generated/project-handoff";
import { beginDiagnosticObservation, recordDiagnosticFailure } from "../presentation/diagnostics";
export type { CoreOperation } from "./generated/core-contract";
const teachingResponses: Partial<Record<CoreOperation,string>> = {
  teaching_list:"RecordPage",teaching_get:"RecordView",teaching_create:"WriteReceipt",
  teaching_withdraw:"WithdrawalReceipt",teaching_export:"ExchangeBundle",
  teaching_import_preview:"ImportPreview",teaching_import:"ImportReceipt",
};
const responseSchemas: Partial<Record<CoreOperation, string>> = {
  workspace_backups: "BackupsListDto",
  operation_failure_log_read:"FailureLogSnapshot",operation_failure_log_append:"FailureLogSnapshot",operation_failure_log_clear:"FailureLogSnapshot",
  ingest_batch_register:"IngestBatchDto",ingest_batch_get:"IngestBatchDto",ingest_batches_list:"IngestBatchesDto",
  ingest_member_import:"IngestMemberImportDto",ingest_member_enqueue:"IngestMemberJobDto",
  ingest_member_relations_apply:"IngestRelationsDto",
  public_research_search:"PublicResearchReceiptDto", public_research_read:"PublicResearchReceiptDto",
  public_research_list:"PublicResearchJournalDto", public_research_cancel:"PublicResearchCancelDto",
  public_research_materialize:"PublicResearchSelectionDto",
  source_job_format_qualification: "FileFormatQualificationDto",
  configuration_plans_read: "ConfigurationPlanCatalog",
  character_memory_get:"CharacterProfile", character_memory_context:"CharacterContext",
  character_memory_apply:"CharacterMemoryReceipt", character_memory_export:"CharacterMemoryExport",
  model_configuration_get:"ModelConfiguration", model_configuration_put:"ModelConfiguration", model_configuration_resolve:"ResolvedModel",
  machine_configuration: "MachineConfigurationDto",
  machine_inventory: "MachineInventoryDto",
  ui_state_machine_status: "MachineJournalStatusDto",
  ui_state_cancel_machine: "MachineCancelDto",
  document_graph: "RelationProjectionDto",
  sources_list: "SourcesListDto", source_get: "SourceDto", source_jobs: "SourceJobsDto", source_members: "SourceMembersDto", source_pages: "SourcePagesDto", source_original: "OriginalDto", documents_list: "DocumentsListDto",
  document_create: "DocumentDto", document_get: "DocumentDto", document_draft: "DocumentDto",
  document_checks: "DocumentChecksDto", document_check_record: "DocumentCheckDto", document_check_execute: "DocumentCheckDto",
  document_version: "DocumentDto", document_restore: "DocumentDto", anchors_list: "AnchorsListDto", anchor_create: "AnchorDto", anchor_resolve: "AnchorResolutionDto",
  semantic_search: "SemanticSearchDto",
  search: "SearchDto", knowledge_get: "KnowledgeDto", learning_items: "LearningItemsDto",
  learning_state: "LearningStateDto", document_export: "DocumentExportDto", document_package_export: "DocumentPackageDto", document_package_import: "DocumentPackageImportDto",
  machine_retest: "MachineRetestDto",
  job_execution_status: "JobExecutionStatusDto", job_execution_cancel: "JobExecutionCancelDto",
  machine_tasks_list: "MachineTasksPageDto",
  machine_contexts_list: "MachineDocumentsPageDto", machine_rubrics_list: "MachineDocumentsPageDto",
  machine_evaluations_list: "MachineDocumentsPageDto", machine_rubric_create: "DocumentDto",
  machine_evaluation_create: "DocumentDto", machine_answer_snapshot: "MachineAnswerSnapshotDto",
};

// This is a transport readback boundary, not a new ranking implementation.
function checkSemanticReadback(value: unknown, query: unknown): void {
  const result = assertCoreDto<SemanticSearchDto>("SemanticSearchDto", value);
  const fail = () => { throw new Error("CORE_SEMANTIC_BINDING_INVALID"); };
  if (result.q !== query || result.candidate_count !== result.candidates.length) fail();
  const candidates = new Map(result.candidates.map(row => [row.knowledge_id, row]));
  if (candidates.size !== result.candidates.length || result.candidates.some(row =>
    row.knowledge_version !== row.knowledge_id || (row.anchor_id !== null && row.source_revision !== row.current_source_revision))) fail();
  for (const leg of [result.embedding, result.reranker]) {
    const seen = new Set<string>();
    for (const row of leg.rank) {
      const candidate = candidates.get(row.knowledge_id);
      if (!candidate || seen.has(row.knowledge_id) || row.knowledge_version !== candidate.knowledge_version
        || row.anchor_id !== candidate.anchor_id || row.source_id !== candidate.source_id || row.source_revision !== candidate.source_revision) fail();
      seen.add(row.knowledge_id);
    }
    if (leg.complete && leg.rank.length !== result.candidate_count) fail();
  }
  const complete = result.embedding.complete && result.reranker.complete;
  const hasRank = result.embedding.rank.length > 0 || result.reranker.rank.length > 0;
  if (result.status === "EMPTY") {
    if (result.candidate_count !== 0 || result.complete || complete || result.embedding.complete || result.reranker.complete || hasRank || result.batches?.length) fail();
  } else {
    if (!result.candidate_count || result.complete !== complete
      || result.status !== (complete ? "AVAILABLE" : hasRank ? "PARTIAL" : "UNAVAILABLE")
      || !result.batches?.length || typeof result.ranking_basis !== "string") fail();
    const ids = result.batches!.flatMap(batch => batch.candidate_ids);
    if (ids.length !== candidates.size || new Set(ids).size !== ids.length || ids.some(id => !candidates.has(id))) fail();
  }
}

export async function coreCommand<T>(operation: CoreOperation, payload: Record<string, unknown> = {}): Promise<T> {
  const observation = beginDiagnosticObservation();
  try { return await executeCoreCommand<T>(operation, payload); }
  catch (error) {
    if (!["operation_failure_log_read","operation_failure_log_append","operation_failure_log_clear"].includes(operation)) recordDiagnosticFailure(operation, error, observation);
    throw error;
  }
}

async function executeCoreCommand<T>(operation: CoreOperation, payload: Record<string, unknown>): Promise<T> {
  if (operation === "semantic_search") {
    try {
      if (Object.keys(payload).length !== 1 || !("body" in payload)) throw new Error("invalid payload");
      assertCoreDto("SemanticSearchInput", payload.body);
    } catch { throw new ApiError(422, "语义查询输入无效；未发送请求。", "incompatible"); }
  }
  const invoke = window.__TAURI__?.core?.invoke;
  if (!invoke) throw new ApiError(0, "请在本地桌面应用打开此内容。", "offline");
  let result: unknown;
  try { result = await invoke("core_command", { request: { operation, payload } }); }
  catch { throw new ApiError(502, "本地核心暂时无法响应，请保留草稿后重试。", "unavailable"); }
  if (!result || typeof result !== "object") throw new ApiError(502, "本地核心返回格式无效。", "incompatible");
  const response = result as { status?: unknown; body?: unknown };
  if (typeof response.status !== "number" || !Number.isInteger(response.status)) throw new ApiError(502, "本地核心状态无效。", "incompatible");
  if (response.status < 200 || response.status >= 300) {
    if (operation === "project_handoff_preview" || operation === "project_handoff_snapshot") {
      const code = (response.body as {code?:unknown} | null)?.code;
      const messages: Record<string,string> = {
        IDENTITY_MISMATCH: "工作区身份或恢复版本已变化；请重新取得引用，原页面仍保留。",
        NOT_FOUND: "此工作区没有指定的固定版本；未读取其他文档。",
        REFERENCE_MISMATCH: "固定版本指纹不一致；未替换为其他版本。",
        CONTENT_INVALID: "固定正文完整性核对失败；原文档未改变，请查看本地数据状态。",
        EXPIRED: "上下文引用已到期；请重新取得引用。",
        TOO_LARGE: "固定正文超过当前阅读限额；未截断或替换正文。",
        HUMAN_REQUIRED: "请在本机桌面的人类会话中读取此引用。",
        INVALID_INPUT: "上下文引用格式或有效期不符；请重新取得引用。",
      };
      const prefix = operation === "project_handoff_preview" ? "HANDOFF_PREVIEW_" : "HANDOFF_SNAPSHOT_";
      const message = typeof code === "string" && code.startsWith(prefix) ? messages[code.slice(prefix.length)] : undefined;
      throw new ApiError(response.status, message ?? "固定引用核对未完成；保留原页面后重试。", response.status === 401 || response.status === 403 ? "unauthorized" : "unavailable");
    }
    if (operation === "job_execute" && response.status === 409) {
      const p = payload as { job_id: string; request_id: string; body: { deadline_ms: number; split: boolean; words: boolean } };
      const admission = p.body && jobAdmissionRefusal(response.body, p);
      if (admission) throw new ApiError(409, "能力已禁用，原请求未受理；启用后可显式同请求重试。", "unavailable", undefined, admission);
    }
    const refusal = response.body as Record<string,unknown> | null;
    if (["machine_answer","machine_retest"].includes(operation) && response.status === 503
      && refusal?.schema === "archeaxis.machine-call-failure/v1"
      && refusal.operation === (operation === "machine_answer" ? "answer" : "retest")
      && refusal.execution_state === "UNVERIFIED" && refusal.answer_published === false) {
      const reasons:Record<string,string> = {
        MODEL_CALL_FAILED:"模型服务调用失败", MODEL_CALL_TIMEOUT:"模型服务调用超时", NO_FINAL_ANSWER:"模型未返回最终答案",
        EMPTY_ANSWER:"模型答案为空", WORKER_TIMEOUT:"模型执行超时", OUTPUT_LIMIT:"模型输出超过限额",
        INVALID_OUTPUT:"模型输出格式无效", PIPE_DRAIN_FAILED:"模型进程输出收尾未确认", WORKER_FAILED:"模型执行失败",
      };
      if(typeof refusal.reason_code === "string" && Object.prototype.hasOwnProperty.call(reasons,refusal.reason_code)) {
        const diagnostics=readMachineFailureDiagnostics(refusal.diagnostics);
        throw new ApiError(503,`${reasons[refusal.reason_code]}；执行状态未确认，保留原请求。`,"unavailable",undefined,undefined,undefined,
          {reason_code:refusal.reason_code,execution_state:"UNVERIFIED",answer_published:false,...(diagnostics?{diagnostics}:{})});
      }
    }
    if (["machine_answer","machine_retest"].includes(operation) && refusal?.schema === "archeaxis.context-admission-refusal/v1") {
      const body=payload.body;
      const admission=response.status===403&&body&&typeof body==="object"&&!Array.isArray(body)
        ?await readMachineAdmissionRefusal(refusal,operation==="machine_answer"?"answer":"retest",body as Record<string,unknown>):undefined;
      if(!admission)throw new ApiError(502,"授权拒绝回执未绑定当前请求；保留冻结身份并核对历史。","incompatible");
      throw new ApiError(403,"恢复后的旧授权已隔离；本次调用未执行，历史请求执行仍未验证。","unauthorized",undefined,undefined,admission);
    }
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
      : response.status === 401 || response.status === 403 ? "你暂时不能进行这项操作，请检查是否已获得授权。"
      : response.status === 404 ? "暂时找不到这项内容，请刷新列表后重试。"
      : response.status === 429 ? "正在处理其他任务，请稍后重试。"
      : response.status >= 500 ? "这项操作暂时未能完成，请查看问题记录后重试。"
      : "这项操作未获允许，请检查填写的内容后重试。";
    throw new ApiError(response.status, reason, response.status === 401 || response.status === 403 ? "unauthorized" : "unavailable");
  }
  if (["layout_read", "layout_write", "layout_recover"].includes(operation)) {
    try { return assertLayoutDto<T>("Snapshot", response.body); }
    catch { throw new ApiError(502, "布局回读格式无效，请保留当前布局。", "incompatible"); }
  }
  if (operation === "project_handoff_preview" || operation === "project_handoff_snapshot") {
    try { return assertHandoffDto<T>(operation === "project_handoff_preview" ? "Preview" : "Snapshot", response.body); }
    catch { throw new ApiError(502, "上下文引用回读格式不兼容，未打开正文。", "incompatible"); }
  }
  if (operation === "material_question_submit" && response.status === 202) {
    try { return assertMaterialQuestionDto<T>("MaterialQuestionAdmissionDto", response.body); }
    catch { throw new ApiError(502, "材料异步受理回执结构不兼容；保留原请求并查询。", "incompatible"); }
  }
  if (operation === "semantic_search") {
    try { checkSemanticReadback(response.body, (payload.body as {q:string}).q); }
    catch { throw new ApiError(502, "语义查询回读不完整或身份不一致。", "incompatible"); }
  }
  const schema = responseSchemas[operation];
  if (["ui_state_read", "ui_state_write", "ui_state_clear_saved", "ui_state_clear_job", "ui_state_clear_machine", "ui_state_recover"].includes(operation)) {
    try { return assertUiWorkingState<T>("Read", response.body); }
    catch { throw new ApiError(502, "工作草稿保全回读格式无效，当前编辑内容仍保留。", "incompatible"); }
  }
  try { return operation === "ai_assets_list" || operation === "ai_asset_packet" ? assertAiAssetDto<T>(operation === "ai_assets_list" ? "AiAssetsPage" : "AssetPacketResponse",response.body) : operation === "collection_query" ? assertCollectionDto<T>("CollectionQueryDto",response.body) : teachingResponses[operation] ? assertTeachingDto<T>(teachingResponses[operation]!,response.body) : schema ? assertCoreDto<T>(schema, response.body) : response.body as T; }
  catch { throw new ApiError(502, "本地核心内容结构不兼容。", "incompatible"); }
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
