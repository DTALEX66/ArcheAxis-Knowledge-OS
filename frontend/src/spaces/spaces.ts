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
  icon: string;
  description: string;
}

// AXW-UI-802: the product spaces. Third-party brands appear only inside
// Adapter settings, never as top-level spaces.
// Icons are simple geometric Unicode glyphs — no emojis.
export const SPACES: readonly SpaceDef[] = [
  { id: "workspace", label: "工作台", icon: "◆", description: "当前工作区与任务" },
  { id: "library", label: "资料库", icon: "▧", description: "原件、转换与保留" },
  { id: "intake", label: "导入", icon: "↓", description: "URL、文件与批量多格式导入" },
  { id: "vault", label: "知识库", icon: "▤", description: "本地笔记、搜索与画布" },
  { id: "evidence", label: "证据", icon: "✚", description: "可信证据与知识账本" },
  { id: "learning", label: "学习", icon: "↗", description: "人类学习与掌握反馈" },
  { id: "ai-assets", label: "机器知识", icon: "✱", description: "经批准供机器使用的知识" },
  { id: "exchange", label: "交换", icon: "⇄", description: "开放交换包的导出与验证" },
  { id: "settings", label: "设置", icon: "⚙", description: "系统与能力设置" },
] as const;
