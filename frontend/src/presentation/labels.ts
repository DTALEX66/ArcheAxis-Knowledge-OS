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

const SAFE_ERROR = "本地数据暂时不可用，请稍后重试或打开系统诊断。";

// UI-03: 离线、冲突、权限、缺失对象是四种不同的用户处境，合并成一句话会让人去查错误的地方。
// 只分类本地核心的已知失败形状，其它错误不编造原因。
export function coreFailureReason(error: unknown): string | null {
  const value = error as { status?: unknown; code?: unknown } | null;
  if (!value || typeof value !== "object") return null;
  if (value.code === "offline") return "离线：此功能需要本地桌面宿主；数据仍留在本机，未被替换。";
  if (value.status === 409) return "冲突：对象版本已变化。已保留你当前的输入，请重新读取后再决定。";
  if (value.code === "unauthorized") return "权限：本地核心拒绝了这次操作的身份，内容未改动。";
  if (value.status === 404) return "缺失：本地核心找不到这个对象；列表可能已变化，页面内容未被替换。";
  if (value.status === 429) return "繁忙：本地核心正在处理其它任务，稍后重试；本次结果未知。";
  if (value.code === "incompatible") return "不兼容：本地核心的返回不符合当前合同，已停止而未按成功显示。";
  if (value.code === "unavailable") return "不可用：本地核心没有完成这次操作，当前内容保持不变。";
  return null;
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
  if (/\/(?:api|workspace)\b|https?:|\bHTTP\b|\b[A-Z_]{4,}\b|->|[{}\[\]]/.test(message)) return SAFE_ERROR;
  return message;
}
