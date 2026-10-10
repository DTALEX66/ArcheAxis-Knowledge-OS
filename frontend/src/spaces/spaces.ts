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
  { id: "workspace", label: "工作台", icon: "Workspace", description: "本地文档与学习继续" },
  { id: "library", label: "资料库", icon: "Source", description: "原件、转换与保留" },
  { id: "intake", label: "导入", icon: "Import", description: "本地原件与多格式导入" },
  { id: "vault", label: "知识库", icon: "Knowledge", description: "本地笔记、搜索与画布" },
  { id: "evidence", label: "证据", icon: "Evidence", description: "可信证据与知识账本" },
  { id: "learning", label: "学习", icon: "Review", description: "人类学习与掌握反馈" },
  { id: "ai-assets", label: "机器知识", icon: "HumanAi", description: "经批准供机器使用的知识" },
  { id: "exchange", label: "交换", icon: "Connection", description: "开放交换包的导出与验证" },
  { id: "settings", label: "设置", icon: "Settings", description: "系统与能力设置" },
] as const;

// Host transport does not change the business page description.
export function spaceDescription(space: SpaceDef): string {
  return space.description;
}