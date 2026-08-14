export type SpaceId =
  | "workspace"
  | "library"
  | "evidence"
  | "learning"
  | "ai-assets"
  | "settings";

export interface SpaceDef {
  id: SpaceId;
  label: string;
  icon: string;
  description: string;
}

// AXW-UI-802: the six product spaces. Third-party brands appear only inside
// Adapter settings, never as top-level spaces.
export const SPACES: readonly SpaceDef[] = [
  { id: "workspace", label: "Workspace", icon: "◆", description: "当前工作区与任务" },
  { id: "library", label: "Library", icon: "◫", description: "原始资料与收藏" },
  { id: "evidence", label: "Evidence", icon: "✚", description: "可信证据与知识账本" },
  { id: "learning", label: "Learning", icon: "↗", description: "人类学习库" },
  { id: "ai-assets", label: "AI Assets", icon: "✳", description: "AI 资产库" },
  { id: "settings", label: "Settings", icon: "⚙", description: "系统与能力设置" },
] as const;
