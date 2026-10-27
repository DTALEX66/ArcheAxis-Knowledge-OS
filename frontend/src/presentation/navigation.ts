import { UI_CAPABILITY_INTENT } from "./uiCapabilityIntent";
import { findUiPage, uiEntryForPage, UI_PAGES, type UiPage } from "./uiPages";
import { CAPABILITY_CATALOG, type CapabilityCatalogEntry } from "../api/generated/capability-catalog";
import { SPACES, spaceDescription, type SpaceDef, type SpaceId } from "../spaces/spaces";

export type EffectiveNavigationEntry = {
  entry_id: string;
  label: string;
  description: string;
  group_id: string;
  aliases: readonly string[];
  keywords: readonly string[];
  destination?: SpaceId;
  space?: SpaceDef;
  page?: UiPage;
  capability?: CapabilityCatalogEntry;
};

// Keep product destinations beside the effective entry projection so the shell,
// command palette, details view, and generated entry matrix describe one route.
export const CAPABILITY_DESTINATIONS: Readonly<Partial<Record<string, SpaceId>>> = {
  "CAP-0010": "library", "CAP-0020": "library", "CAP-0030": "library",
  "CAP-0040": "learning", "CAP-0050": "vault", "CAP-0110": "vault", "CAP-0140": "library",
};

// Existing page identities, not execution grants. More precise than a space's
// default page; App owns draft guards and restoration when opening them.
export const CAPABILITY_PAGES: Readonly<Partial<Record<string, string>>> = {
  "CAP-0010":"02", "CAP-0020":"16", "CAP-0030":"03", "CAP-0040":"06",
  "CAP-0050":"13", "CAP-0060":"07", "CAP-0090":"05", "CAP-0110":"04",
  "CAP-0120":"19", "CAP-0140":"19",
};

// Space IDs remain route identities; capability IDs come only from the generated
// Atlas/map projection. This is presentation glue, not a second capability registry.
const PAGE_PURPOSES: Readonly<Record<string, string>> = {
  "01": "继续最近的工作，查看待办与学习进展",
  "02": "查找、整理和打开知识资料",
  "03": "阅读资料、编辑正文并保留版本",
  "04": "沿双向链接探索知识关系",
  "05": "收集研究材料，组织问题与引用",
  "06": "安排学习目标与复习步骤",
  "07": "组织课程内容与视觉教学材料",
  "08": "记录学习对象、目标与教学需求",
  "09": "整理讲解思路与表达方案",
  "10": "查看教学交付内容与版本",
  "11": "通过练习与复述检查理解",
  "12": "汇总反馈并修订学习内容",
  "13": "管理项目记忆与模型上下文",
  "14": "查看纠正记录、评测与复测结果",
  "15": "浏览资源与扩展的适用条件",
  "16": "导入、导出并交换常用格式",
  "17": "浏览能力范围、当前入口与后续规划",
  "18": "查看能力说明、使用条件与替代方式",
  "19": "管理偏好、模型连接、权限与恢复",
  "20": "追溯内容版本、来源与修改历史",
  "21": "用画布组织材料与视觉表达",
  "22": "查看受限任务的状态、结果与回执",
};

export const EFFECTIVE_NAVIGATION_ENTRIES: readonly EffectiveNavigationEntry[] = [
  ...UI_PAGES.map((page)=>({entry_id:`page:${page.id}`,label:page.label,description:page.implemented ? PAGE_PURPOSES[page.id] ?? `打开${page.label}` : "页面尚未接通，查看相关能力与替代入口",group_id:uiEntryForPage(page.id)?.label ?? page.group,aliases:[`page=${page.id}`],keywords:[page.task, page.group],page})),
  ...SPACES.map((space) => ({
    entry_id: `space:${space.id}`,
    label: space.label,
    description: spaceDescription(space),
    group_id: "产品空间",
    aliases: [space.id, `aaos.space.${space.id}`],
    keywords: [space.description],
    space,
  })),
  ...CAPABILITY_CATALOG.entries.map((capability) => ({
    entry_id: capability.atlas.capability_id,
    label: capability.atlas.canonical_name,
    description: capability.implementation.state === "not_implemented" ? "尚未实现，查看使用前提与替代方式" : "查看当前入口、适用范围与使用条件",
    group_id: capability.atlas.product_layer,
    aliases: capability.atlas.origin_requirement_ids as readonly string[],
    keywords: [
      capability.atlas.authority_status, capability.atlas.technical_state,
      ...(UI_CAPABILITY_INTENT[capability.atlas.capability_id] ?? []),
      ...capability.atlas.objects,
      ...capability.atlas.views,
      ...capability.atlas.dependencies,
      ...capability.atlas.entry_gate,
      ...capability.atlas.fallbacks,
    ],
    ...(CAPABILITY_DESTINATIONS[capability.atlas.capability_id] ? { destination: CAPABILITY_DESTINATIONS[capability.atlas.capability_id] } : {}),
    capability,
  })),
];

export function getCapabilityDestination(capability: CapabilityCatalogEntry): SpaceId | undefined {
  return CAPABILITY_DESTINATIONS[capability.atlas.capability_id];
}

export const CAPABILITY_NAVIGATION_ENTRIES = EFFECTIVE_NAVIGATION_ENTRIES.filter(
  (entry): entry is EffectiveNavigationEntry & { capability: CapabilityCatalogEntry } => Boolean(entry.capability),
);

export function navigationEntryMatches(entry: EffectiveNavigationEntry, query: string): boolean {
  const needle = query.trim().toLocaleLowerCase("zh-CN");
  if (!needle) return true;
  return [entry.entry_id, entry.label, entry.description, entry.group_id, ...entry.aliases, ...entry.keywords]
    .some((value) => value.toLocaleLowerCase("zh-CN").includes(needle));
}

export function canNavigateToCapability(capability: CapabilityCatalogEntry): boolean {
  return capability.implementation.state !== "not_implemented";
}

export function getCapabilityNextStep(capability: CapabilityCatalogEntry, hasPageNavigation = false): string {
  if (canNavigateToCapability(capability) && (getCapabilityDestination(capability) || (hasPageNavigation && CAPABILITY_PAGES[capability.atlas.capability_id]))) {
    return "点击“打开当前产品入口”继续，再核对本次操作的结果；打开页面不代表处理已经成功。";
  }
  if (canNavigateToCapability(capability)) return "当前尚未提供可打开的操作入口。可先使用已提供的功能；实现与来源说明见下方详情。";
  if (capability.atlas.authority_status === "binding_long_term") {
    return "这是长期规划能力，目前尚不能使用。你可以查看用途与来源说明，日常工作请先使用已提供的功能。";
  }
  if (["parked", "deferred_retained"].includes(capability.atlas.roadmap_state)) {
    return "此能力暂未提供；你可以查看详情中的现有替代方式，或返回已提供的功能继续。";
  }
  return "此能力尚未实现，当前不能执行。你可以先查看用途和限制，或返回已提供的功能继续。";
}

const LEGACY_SPACE_ALIASES: Readonly<Record<string, SpaceId>> = {
  home: "workspace", dashboard: "workspace", sources: "library", import: "intake",
  capture: "intake", knowledge: "vault", notes: "vault", review: "learning",
  machine: "ai-assets", integrations: "exchange", preferences: "settings",
};

export function resolveLegacySpaceAlias(value: string): SpaceId | undefined {
  const normalized = value.trim().replace(/^#\/?/, "").replace(/^\//, "").toLocaleLowerCase("en-US");
  if (SPACES.some((space) => space.id === normalized)) return normalized as SpaceId;
  return LEGACY_SPACE_ALIASES[normalized];
}

export function resolveCapabilityEntry(value: string): CapabilityCatalogEntry | undefined {
  let normalized = value.trim();
  try { normalized = decodeURIComponent(normalized); } catch { return undefined; }
  const direct = CAPABILITY_CATALOG.entries.find((entry) => entry.atlas.capability_id === normalized);
  if (direct) return direct;
  return CAPABILITY_CATALOG.entries.find((entry) => (entry.atlas.origin_requirement_ids as readonly string[]).includes(normalized));
}

export function validateNavigationProjection(): string[] {
  const failures: string[] = [];
  const ids = new Set<string>();
  const aliasOwners = new Map<string, string>();
  for (const entry of EFFECTIVE_NAVIGATION_ENTRIES) {
    if (!entry.entry_id) failures.push("empty entry_id");
    if (ids.has(entry.entry_id)) failures.push(`duplicate entry_id: ${entry.entry_id}`);
    ids.add(entry.entry_id);
  }
  for (const capability of CAPABILITY_CATALOG.entries) {
    const entryId = capability.atlas.capability_id;
    if (!ids.has(entryId)) failures.push(`capability missing from navigation: ${entryId}`);
    const hash = resolveNavigationHash(`#capability/${encodeURIComponent(entryId)}`);
    if (hash?.capabilityId !== entryId) failures.push(`capability hash does not resolve: ${entryId}`);
    for (const alias of capability.atlas.origin_requirement_ids as readonly string[]) {
      const owner = aliasOwners.get(alias) ?? entryId;
      if (!aliasOwners.has(alias)) aliasOwners.set(alias, entryId);
      if (resolveCapabilityEntry(alias)?.atlas.capability_id !== owner) failures.push(`capability alias does not resolve to stable owner ${owner}: ${alias}`);
    }
  }
  for (const legacy of Object.keys(LEGACY_SPACE_ALIASES)) {
    if (!resolveLegacySpaceAlias(legacy)) failures.push(`legacy space alias does not resolve: ${legacy}`);
  }
  return failures;
}


export type ResolvedNavigationHash = { spaceId: SpaceId; capabilityId: string | null; pageId?: string };

export function resolveNavigationHash(hash: string): ResolvedNavigationHash | null {
  const value = hash.replace(/^#\/?/, "").trim();
  if (!value) return null;
  if (value.startsWith("page=")) { const page = findUiPage(value.slice(5)); return page ? {spaceId:page.space, capabilityId:null, pageId:page.id} : null; }
  const capabilityValue = value.startsWith("capability=") ? value.slice("capability=".length)
    : value.startsWith("capability/") ? value.slice("capability/".length) : null;
  if (capabilityValue !== null) {
    const capability = resolveCapabilityEntry(capabilityValue);
    return capability ? { spaceId: "settings", capabilityId: capability.atlas.capability_id } : null;
  }
  const spaceValue = value.startsWith("space=") ? value.slice("space=".length)
    : value.startsWith("route=") ? value.slice("route=".length) : value;
  const spaceId = resolveLegacySpaceAlias(spaceValue);
  return spaceId ? { spaceId, capabilityId: null } : null;
}

export const navigationSpaceDescription = spaceDescription;
