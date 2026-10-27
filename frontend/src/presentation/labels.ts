const STATE_LABELS: Record<string, string> = {
  available: "可用",
  unavailable: "不可用",
  completed: "已完成",
  succeeded: "已完成",
  running: "执行中",
  pending: "待处理",
  failed: "失败",
  blocked: "已阻断",
  delivered: "已发送",
  recorded: "已记录",
  missing: "缺失",
  candidate: "候选",
  accepted: "已接受",
  approved: "已批准",
  deprecated: "已弃用",
  unverified: "未核验",
  unreviewed: "未复核",
  ready: "就绪",
  stopped: "已停止",
  safe_mode: "安全模式",
  booting: "正在启动",
  checking: "正在检查",
  reconnecting: "正在重新连接",
  incompatible: "不兼容",
  verified: "已核验",
  open: "待处理",
  anchored: "已锚定",
  retained: "已保留",
  immutable: "不可变",
  idle: "无待处理项",
  requeued: "已重新排队",
  queued: "排队中",
  cancelled: "已取消",
  rejected: "未获允许",
  granted: "已授权",
  revoked: "已撤回",
  adopted: "已采用",
  withdrawn: "已撤回",
};

export function stateLabel(value: unknown): string {
  return typeof value === "string" ? STATE_LABELS[value] ?? "状态未知" : "状态未知";
}

/** A connection response does not verify a task, engine or output. */
export function capabilityHealthLabel(value: unknown): string {
  if (value === "healthy") return "正常";
  if (value === "handshake_ready") return "连接已响应，运行尚未确认";
  return "尚未确认";
}

const JOB_KIND_LABELS: Record<string, string> = {
  text: "文字解析",
  "text.extract": "文字解析",
  document_structure: "文档结构读取",
  ocr: "文字识别",
  transcribe: "音频转写",
  caption: "图片内容说明",
  media_decode: "媒体读取",
  video: "视频解析",
  office: "Office 文档解析",
  pdf: "PDF 解析",
  image: "图片识别",
  archive: "压缩包目录读取",
  media: "音视频信息读取",
  canvas: "画布结构读取",
  subtitles: "字幕解析",
  html: "网页解析",
  diarize: "说话时段区分",
  detect: "文件类型识别",
};

export function jobKindLabel(value: unknown): string {
  return typeof value === "string" ? JOB_KIND_LABELS[value] ?? "其他处理任务" : "其他处理任务";
}

export function sourceLabel(value: unknown, index = 0): string {
  if (typeof value === "string") {
    try {
      const url = new URL(value);
      if (url.protocol === "http:" || url.protocol === "https:") {
        return `网页来源 · ${url.hostname}`;
      }
    } catch {
      // Opaque/local source identities intentionally fall through.
    }
  }
  return `本地资料 ${index + 1}`;
}

const SAFE_ERROR = "本地数据暂时不可用，请稍后重试或打开运行诊断。";

// UI-03: 离线、冲突、权限、缺失对象是四种不同的用户处境，合并成一句话会让人去查错误的地方。
// 只分类本地核心的已知失败形状，其它错误不编造原因。通用的“核心不可用”故意不在此列：
// 它由 userErrorMessage 的原句承担，好让 Web 端 5xx 的既有措辞与测试保持一致。
export function coreFailureReason(error: unknown): string | null {
  const value = error as { status?: unknown; code?: unknown; jobAdmission?: {schema?: unknown; admission_state?: unknown; enabled?: unknown; active_execution?: unknown}; machineAdmission?: {schema?: unknown; execution_state?: unknown; prior_request_execution?: unknown}; execution?: {execution_state?: unknown; answer_published?: unknown}; machineFailure?: {reason_code?: unknown; execution_state?: unknown; answer_published?: unknown} } | null;
  if (!value || typeof value !== "object") return null;
  // Validated business refusals carry more meaning than the HTTP status alone.
  // A disabled processor is not a document version conflict; an answer withheld
  // after execution must never be described as an operation that did not run.
  if (value.jobAdmission?.schema === "archeaxis.job-admission-refusal/v1" && value.jobAdmission.admission_state === "NOT_ADMITTED" && value.jobAdmission.enabled === false && value.jobAdmission.active_execution === false) return "这项处理尚未启用，本次没有开始。请先启用，再重试原来的任务。";
  if (value.machineAdmission?.schema === "archeaxis.context-admission-refusal/v1" && value.machineAdmission.execution_state === "NOT_EXECUTED" && value.machineAdmission.prior_request_execution === "UNVERIFIED") return "这次调用没有执行：恢复前的资料授权已失效。请重新核对并授权；先前请求的结果仍需查询。";
  if (value.execution?.execution_state === "EXECUTED_BUT_WITHHELD" && value.execution.answer_published === false) return "AI 已处理这次请求，但回答未能提供。请查看原任务的记录，再决定下一步，避免重复执行。";
  if (value.machineFailure?.execution_state === "UNVERIFIED" && value.machineFailure.answer_published === false) {
    const reasons: Record<string, string> = {
      MODEL_CALL_FAILED: "暂时没有取得 AI 回答，请检查模型服务是否可用。",
      MODEL_CALL_TIMEOUT: "等待 AI 回答的时间过长，请先查询这次任务的状态。",
      NO_FINAL_ANSWER: "AI 没有提供最终回答，请查看这次任务的处理状态。",
      EMPTY_ANSWER: "AI 返回的回答为空，请查看这次任务的处理状态。",
      WORKER_TIMEOUT: "AI 处理用时过长，请先查询这次任务的状态。",
      OUTPUT_LIMIT: "AI 返回的内容超过本次限额，请查看任务记录后调整请求。",
      INVALID_OUTPUT: "暂时无法读取 AI 返回的内容，请查看这次任务的记录。",
      PIPE_DRAIN_FAILED: "暂时无法确认 AI 的处理结果，请先查询这次任务的状态。",
      WORKER_FAILED: "AI 处理遇到了问题，请查看这次任务的记录。",
    };
    if (typeof value.machineFailure.reason_code === "string" && Object.prototype.hasOwnProperty.call(reasons, value.machineFailure.reason_code)) return `${reasons[value.machineFailure.reason_code]} 当前结果尚未确认，请保留原来的任务。`;
  }
  if (value.code === "offline") return "离线：请在桌面应用中使用此功能；当前内容已保留。";
  if (value.code === "migrating") return "迁移中：正在升级本地数据，完成后再继续操作。";
  if (value.code === "backend_starting") return "正在启动：请稍后重试；本次操作结果尚未确认。";
  if (value.status === 409) return "冲突：对象版本已变化。已保留你当前的输入，请重新读取后再决定。";
  if (value.code === "unauthorized") return "权限：你暂时不能执行此操作；内容未改动。";
  if (value.status === 404) return "缺失：此条目暂时找不到，请刷新列表；当前内容已保留。";
  if (value.status === 429) return "繁忙：正在处理其他任务，请稍后重试；本次结果尚未确认。";
  if (value.code === "incompatible") return "不兼容：应用版本暂不兼容，已停止读取；请查看运行诊断，本次结果尚未确认。";
  return null;
}

export function failureMessage(error: unknown): string {
  if (error instanceof Error && error.message === "复习请求保全将超过 1 MiB；请先保存或明确丢弃其他草稿。") {
    return "复习内容与其他草稿合计超过 1 MiB；请先保存或明确丢弃其他草稿。";
  }
  return coreFailureReason(error) ?? userErrorMessage(error instanceof Error ? error.message : error);
}

const PRODUCT_LAYER_LABELS: Record<string, string> = {
  Workspace: "工作台",
  Library: "资料库",
  Evidence: "证据",
  Learning: "学习",
  "AI Assets": "机器知识",
  Desktop: "桌面宿主",
  Exploration: "探索",
  Settings: "设置",
};

/** The navigation projection groups by the Core's English layer enum; the rail must not show it raw. */
export function productLayerLabel(layer: string): string {
  return PRODUCT_LAYER_LABELS[layer] ?? layer;
}

export function userErrorMessage(value: unknown): string {
  if (typeof value !== "string") return SAFE_ERROR;
  const message = value.trim().slice(0, 180);
  if (!message || !/[\u3400-\u9fff]/.test(message)) return SAFE_ERROR;
  if (/\/(?:api|workspace)\b|https?:|\b[A-Z]:[\\/]|\b(?:HTTP|Core|Rust|worker|DTO|CAS|SQLite|Error|TypeError|ReferenceError|SyntaxError|Exception|Traceback)\b|\b[A-Z_]{4,}\b|\b[a-z]+_[a-z_]+\b|\.(?:tsx?|jsx?|rs|py):\d+|回执|读回|保全|正典|->|=>|[`{}\[\]]/i.test(message)) return SAFE_ERROR;
  return message;
}
