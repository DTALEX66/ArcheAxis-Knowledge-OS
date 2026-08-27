const STATE_LABELS: Record<string, string> = {
  available: "可用",
  unavailable: "不可用",
  completed: "已完成",
  succeeded: "已完成",
  running: "执行中",
  pending: "待处理",
  failed: "失败",
  blocked: "已阻断",
  delivered: "已投递",
  recorded: "已记录",
  missing: "缺失",
  candidate: "候选",
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
  requeued: "已重新入队",
};

export function stateLabel(value: unknown): string {
  return typeof value === "string" ? STATE_LABELS[value] ?? "状态未知" : "状态未知";
}

const SAFE_ERROR = "本地数据暂时不可用，请稍后重试或打开系统诊断。";

export function userErrorMessage(value: unknown): string {
  if (typeof value !== "string") return SAFE_ERROR;
  const message = value.trim().slice(0, 180);
  if (!message || !/[\u3400-\u9fff]/.test(message)) return SAFE_ERROR;
  if (/\/(?:api|workspace)\b|https?:|\bHTTP\b|\b[A-Z_]{4,}\b|->|[{}\[\]]/.test(message)) return SAFE_ERROR;
  return message;
}
