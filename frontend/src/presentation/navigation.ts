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

// Space IDs remain route identities; capability IDs come only from the generated
// Atlas/map projection. This is presentation glue, not a second capability registry.
export const EFFECTIVE_NAVIGATION_ENTRIES: readonly EffectiveNavigationEntry[] = [
  ...UI_PAGES.map((page)=>({entry_id:`page:${page.id}`,label:page.label,description:`UI / ${page.id} · ${page.implemented ? "已有关联底座，完整资格独立核实" : "页面尚未接通"} · ${page.task}`,group_id:page.group,aliases:[`page=${page.id}`],keywords:[page.task, uiEntryForPage(page.id)?.label ?? ""],page})),
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
    description: `${capability.atlas.authority_status} · ${capability.atlas.technical_state}`,
    group_id: capability.atlas.product_layer,
    aliases: capability.atlas.origin_requirement_ids as readonly string[],
    keywords: [
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

export function getCapabilityNextStep(capability: CapabilityCatalogEntry): string {
  if (canNavigateToCapability(capability) && getCapabilityDestination(capability)) {
    return "通过当前 AAOS 产品入口继续；运行资格和产物质量仍需独立回执。";
  }
  if (canNavigateToCapability(capability)) return "当前有实现声明，但尚未关联可打开的产品动作入口；先补齐领域契约与入口映射，勿推断可执行。";
  if (capability.atlas.authority_status === "binding_long_term") {
    return "保留长期能力发现；先满足列明的合同、依赖与验收证据，再由后续实施包启用。";
  }
  if (["parked", "deferred_retained"].includes(capability.atlas.roadmap_state)) {
    return "当前路线延后；查看前置合同与降级方式，前置未满足时继续用已实现的 AAOS 入口。";
  }
  return "当前未实现；按前置、依赖和证据要求安排实施，已接入替代入口保持可用。";
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
