import type { SpaceId } from "../spaces/spaces";
export const UI_PAGE_GROUPS = ["日常知识", "人类学习", "AI 知识与学习", "资源与完整能力", "系统与可靠性"] as const;
export type UiPage = { id: string; label: string; group: typeof UI_PAGE_GROUPS[number]; space: SpaceId; implemented: boolean; task: string };
const page = (id: string, label: string, group: UiPage["group"], space: SpaceId, implemented: boolean, task: string): UiPage => ({ id, label, group, space, implemented, task });
// Semantic UI roles from the 2026-10-09 page plan. This is routing, not a capability status store.
export const UI_PAGES: readonly UiPage[] = [
  page("01", "今日工作台", "日常知识", "workspace", true, "UF03"),
  page("02", "知识库", "日常知识", "library", true, "UF03"),
  page("03", "阅读与编辑", "日常知识", "library", true, "UF03"),
  page("04", "双链与图谱", "日常知识", "vault", true, "UF08"),
  page("05", "研究空间", "日常知识", "vault", true, "UF08"),
  page("06", "学习路径", "人类学习", "learning", true, "UF05"),
  page("07", "课程与视觉教学", "人类学习", "learning", true, "UF05"),
  page("08", "教学需求", "人类学习", "learning", true, "UF07"),
  page("09", "表达方案", "人类学习", "learning", true, "UF07"),
  page("10", "交付与版本", "人类学习", "learning", true, "UF07"),
  page("11", "练习 / Teach-back", "人类学习", "learning", true, "UF07"),
  page("12", "反馈与修订", "人类学习", "learning", true, "UF07"),
  page("13", "项目记忆与上下文", "AI 知识与学习", "ai-assets", true, "UF09"),
  page("14", "纠正、评测与复测", "AI 知识与学习", "ai-assets", true, "UF09"),
  page("15", "资源与扩展", "资源与完整能力", "settings", true, "UF10"),
  page("16", "导入导出与互通", "资源与完整能力", "exchange", true, "UF11"),
  page("17", "全部能力与未来蓝图", "资源与完整能力", "settings", true, "UF06"),
  page("18", "能力详情", "资源与完整能力", "settings", true, "UF06"),
  page("19", "设置、权限与恢复", "系统与可靠性", "settings", true, "UF04"),
  page("20", "版本、来源与历史", "系统与可靠性", "library", true, "UF04"),
  page("21", "画布与视觉表达", "人类学习", "learning", true, "UF12"),
  page("22", "受限任务与回执", "AI 知识与学习", "ai-assets", true, "UF09"),
];
export const findUiPage = (id: string): UiPage | undefined => UI_PAGES.find(page => page.id === id);
export const defaultUiPage = (space: SpaceId): string => ({workspace:"01",library:"03",intake:"16",vault:"02",evidence:"20",learning:"06","ai-assets":"13",exchange:"16",settings:"19"})[space];

// Daily workflow projection from PAGE-ENTRY-MAPPING.csv. Page identity stays above.
export type UiEntryPoint = { label: string; pageId: string; pageIds: readonly string[] };
export const UI_DAILY_ENTRY_POINTS: readonly UiEntryPoint[] = [
  { label: "工作台", pageId: "01", pageIds: ["01"] },
  { label: "知识", pageId: "02", pageIds: ["02", "03", "04", "05"] },
  { label: "学习", pageId: "06", pageIds: ["06", "07", "08", "09", "10", "11", "12", "21"] },
  { label: "AI", pageId: "13", pageIds: ["13", "14", "22"] },
  { label: "资源", pageId: "15", pageIds: ["15", "16"] },
];
export const UI_FIXED_ENTRY_POINTS: readonly UiEntryPoint[] = [
  { label: "全部能力", pageId: "17", pageIds: ["17", "18"] },
  { label: "设置", pageId: "19", pageIds: ["19", "20"] },
];
export const uiEntryForPage = (id: string): UiEntryPoint | undefined =>
  [...UI_DAILY_ENTRY_POINTS, ...UI_FIXED_ENTRY_POINTS].find(entry => entry.pageIds.includes(id));
