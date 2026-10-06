import type { AaosIconName } from "../components/AaosIcon";

export type SpaceId =
  | "workspace"
  | "library"
  | "intake"
  | "vault"
  | "evidence"
  | "learning"
  | "ai-assets"
  | "exchange"
  | "settings";

export interface SpaceDef {
  id: SpaceId;
  label: string;
  icon: AaosIconName;
  description: string;
}

// AXW-UI-802: the product spaces. Third-party brands appear only inside
// Adapter settings, never as top-level spaces.
// Navigation reuses the existing AAOS VI line icons from the Avalonia client.
export const SPACES: readonly SpaceDef[] = [
  { id: "workspace", label: "工作台", icon: "Workspace", description: "当前工作区与任务" },
  { id: "library", label: "资料库", icon: "Source", description: "原件、转换与保留" },
  { id: "intake", label: "导入", icon: "Import", description: "URL、文件与批量多格式导入" },
  { id: "vault", label: "知识库", icon: "Knowledge", description: "本地笔记、搜索与画布" },
  { id: "evidence", label: "证据", icon: "Evidence", description: "可信证据与知识账本" },
  { id: "learning", label: "学习", icon: "Review", description: "人类学习与掌握反馈" },
  { id: "ai-assets", label: "机器知识", icon: "HumanAi", description: "经批准供机器使用的知识" },
  { id: "exchange", label: "交换", icon: "Connection", description: "开放交换包的导出与验证" },
  { id: "settings", label: "设置", icon: "Settings", description: "系统与能力设置" },
] as const;

// The desktop shell routes several of these ids to Canonical surfaces, so the label must not
// promise a capability that surface does not offer. Web development mode keeps the legacy text.
const DESKTOP_DESCRIPTIONS: Partial<Record<SpaceId, string>> = {
  workspace: "任务、备份与能力状态",
  intake: "导入原件与多格式转换",
  vault: "文档、搜索与知识候选",
  exchange: "导出与投递回执",
  settings: "本机能力与状态",
};

export function spaceDescription(space: SpaceDef): string {
  if (typeof window === "undefined" || !window.__TAURI__?.core?.invoke) return space.description;
  return DESKTOP_DESCRIPTIONS[space.id] ?? space.description;
}
