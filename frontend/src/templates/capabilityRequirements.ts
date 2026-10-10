/**
 * The one resolver that answers "what does this template actually call?".
 *
 * It reads three things and nothing else:
 *  - `TEMPLATES` in ./disciplines — the declared requirement (name + optional stable CAP ID +
 *    the first-party Core commands the template really invokes);
 *  - `CAPABILITY_CATALOG` in ../api/generated/capability-catalog — the generated join of
 *    docs/truth/CAPABILITY_ATLAS_V2.yaml (identity, intent) and config/capability-map.v1.json
 *    (implementation declaration + runtime capability names);
 *  - the live `capabilities_list` readback, but only as much of it as the caller hands in. A read
 *    that never happened renders NOT_RUN, a failed read renders 未知; neither may be shown as 可用.
 *
 * Boundaries this module exists to keep: it creates no second capability registry, copies no plugin
 * code, dependency install or connection configuration into the template, and never infers a join
 * from a similar name — `search.local` does not become CAP-0110 because the Atlas talks about FTS,
 * and `canvas.references` does not become `canvas.structure` because both mention a canvas.
 */
import { CAPABILITY_CATALOG, type CapabilityCatalogEntry } from "../api/generated/capability-catalog";
import { ABSORPTION_SURFACE_BY_CAPABILITY,
  type AbsorptionSurfaceClass, type AbsorptionSurfaceRow,
} from "../api/generated/absorption-surface";
import { TEMPLATES, type TemplateDefinition, type TemplateRequirement } from "./disciplines";

/** One live handshake row, narrowed to the fields this resolver is allowed to read. */
export type LiveCapabilityRow = { capability?: unknown; enabled?: unknown; health?: unknown };

/** How much runtime truth the caller actually holds. Never invented by defaulting to a value. */
export type CapabilityRead =
  | { state: "read"; rows: Map<string, LiveCapabilityRow> }
  | { state: "not_read" }
  | { state: "read_failed" };

/** `map_runtime` — the declared name is verbatim in the map's runtime list for that ID.
 *  `atlas_entry` — the ID was bound by the Atlas entry's own declared text, not by a handshake name.
 *  `unbound` — no stable ID exists for this declaration.
 *  `unknown_id` — an ID is declared but the generated projection has no such entry. */
export type JoinBasis = "map_runtime" | "atlas_entry" | "unbound" | "unknown_id";

/** The declaration verdict: is there a qualified implementation this template may call? */
export type RequirementStatus = "qualified" | "declared_no_implementation" | "provider_unknown";

/** The live verdict, kept separate so a declaration is never read as an observation. */
export type Availability =
  | "allowed" | "disabled" | "handshake_incomplete" | "enabled_unknown" | "runtime_absent"
  | "no_live_surface" | "unlinked" | "not_read" | "read_failed";

export type ImplementationState = "worker_backed" | "core_native" | "not_implemented" | "unlinked";

export type RequirementRow = {
  declared: string;
  capability_id: string | null;
  capability_name: string | null;
  join_basis: JoinBasis;
  join_label: string;
  implementation_state: ImplementationState;
  provider: string;
  handshake_capability: string | null;
  status: RequirementStatus;
  status_label: string;
  availability: Availability;
  availability_label: string;
  health: string | null;
  missing_reason: string;
  served_by: readonly string[];
  navigable: boolean;
};

export const JOIN_LABEL: Record<JoinBasis, string> = {
  map_runtime: "联接依据：映射握手名直连",
  atlas_entry: "联接依据：目录条目声明（人工核对，非握手名）",
  unbound: "无稳定 ID",
  unknown_id: "ID 不在目录投影中",
};

export const STATUS_LABEL: Record<RequirementStatus, string> = {
  qualified: "有合格实现声明",
  declared_no_implementation: "已声明需求，无合格实现",
  provider_unknown: "提供方未确认",
};

export const AVAILABILITY_LABEL: Record<Availability, string> = {
  allowed: "本轮握手：允许",
  disabled: "本轮握手：已禁用",
  handshake_incomplete: "本轮握手：未就绪",
  enabled_unknown: "本轮握手：权限字段缺失，状态未知",
  runtime_absent: "本轮握手列表无此运行能力",
  no_live_surface: "不经 worker 握手（无运行状态可读回）",
  unlinked: "无运行状态可联接（目录未联接）",
  not_read: "未读取（NOT_RUN）",
  read_failed: "读取失败，显示未知",
};

export function capabilityEntry(capability_id: string | null | undefined): CapabilityCatalogEntry | undefined {
  if (!capability_id) return undefined;
  return CAPABILITY_CATALOG.entries.find((entry) => entry.atlas.capability_id === capability_id);
}

function stateOf(entry: CapabilityCatalogEntry | undefined): ImplementationState {
  return entry ? entry.implementation.state : "unlinked";
}

/** The generated projection types each entry's runtime list as its own literal tuple, so an empty
 *  one is `readonly []` and `includes` refuses any argument. Widening here is the only place that
 *  touches that shape; the values themselves are never rewritten. */
function runtimeNames(entry: CapabilityCatalogEntry | undefined): readonly string[] {
  return entry ? (entry.implementation.runtime_capabilities as readonly string[]) : [];
}

function joinBasisOf(declared: string, entry: CapabilityCatalogEntry | undefined): JoinBasis {
  // Only called for a requirement that declares an ID: no entry means the ID itself is unmatched.
  if (!entry) return "unknown_id";
  return runtimeNames(entry).includes(declared) ? "map_runtime" : "atlas_entry";
}

function providerLabel(entry: CapabilityCatalogEntry | undefined, declared: string): string {
  if (!entry) return "目录投影未联接，无提供方可述";
  // Only this requirement's own handshake name is quoted. Listing every runtime name the entry
  // declares would fill the row with names that answer to something else, and make two rows of the
  // same capability indistinguishable to a reader (or to a test that addresses rows by name).
  const kind = entry.implementation.state === "worker_backed"
    ? runtimeNames(entry).includes(declared)
      ? `worker 实现声明（握手名：${declared}）`
      : "worker 实现声明（此声明名不是该条目的握手名）"
    : entry.implementation.state === "core_native"
      ? "Core 原生实现声明（无 worker 握手名）"
      : "映射声明 not_implemented（无实现方）";
  return `${kind} · ${entry.atlas.capability_id}`;
}

function availabilityOf(read: CapabilityRead, entry: CapabilityCatalogEntry | undefined, handshake: string | null): Availability {
  if (!entry) return "unlinked";
  if (entry.implementation.state === "not_implemented" || handshake === null) return "no_live_surface";
  if (read.state === "not_read") return "not_read";
  if (read.state === "read_failed") return "read_failed";
  const row = read.rows.get(handshake);
  if (!row) return "runtime_absent";
  if (row.enabled === false) return "disabled";
  if (row.enabled !== true) return "enabled_unknown";
  return row.health === "handshake_ready" ? "allowed" : "handshake_incomplete";
}

function missingReason(requirement: TemplateRequirement, entry: CapabilityCatalogEntry | undefined, handshake: string | null, availability: Availability): string {
  if (!requirement.capability_id) {
    const served = requirement.served_by?.length
      ? `当前由第一方 Core 命令 ${requirement.served_by.join("、")} 直接承担；这不等于目录已把它列为能力。`
      : "模板也未调用任何 Core 命令或 worker 实现它；此需求目前是纯声明。";
    return `能力目录（Atlas 稳定 ID）与运行映射（capability-map 的 runtime_capabilities）都不含“${requirement.declared}”。${served}`;
  }
  if (!entry) return `模板声明的 ${requirement.capability_id} 不在生成的目录投影中；先修正声明或由 Owner 补齐目录，不推断提供方。`;
  if (entry.implementation.state === "not_implemented") return `${requirement.capability_id} 在映射中声明为 not_implemented：目录保留该能力，尚无实现方。`;
  if (handshake === null) {
    const listed = runtimeNames(entry);
    return listed.length
      ? `“${requirement.declared}”不是 ${requirement.capability_id} 的握手名（该条目握手名：${listed.join("、")}）；不把别的握手项状态当作它的运行状态。`
      : `${requirement.capability_id} 声明为 Core 原生实现；worker 握手列表不提供该项的运行证据。`;
  }
  if (availability === "not_read") return `本轮未读取 capabilities_list，${handshake} 的运行状态按未知处理（NOT_RUN），不写“可用”。`;
  if (availability === "read_failed") return `本轮 capabilities_list 读取失败，${handshake} 的运行状态未知。`;
  if (availability === "runtime_absent") return `本轮 Core 注册路由中没有 ${handshake}；当前宿主未挂载该运行能力，执行会落到降级路径。`;
  if (availability === "disabled") return `工作区能力记录已将 ${handshake} 置为禁用，执行路径会拒绝它；模板按降级方式工作。`;
  if (availability === "enabled_unknown") return `握手行未提供 ${handshake} 的权限字段，无法判断是否允许。`;
  if (availability === "handshake_incomplete") return `${handshake} 的握手未就绪，该项当前不可用。`;
  return `无缺失：${handshake} 已注册且握手允许；实际引擎产物质量仍需具体 job 的质量回执。`;
}

export function resolveRequirement(requirement: TemplateRequirement, read: CapabilityRead): RequirementRow {
  const entry = capabilityEntry(requirement.capability_id);
  const join_basis = requirement.capability_id ? joinBasisOf(requirement.declared, entry) : "unbound";
  const handshake = join_basis === "map_runtime" ? requirement.declared : null;
  // One readback row is the only source of a live verdict, and it is looked up by the exact
  // handshake name the map declares for this requirement — never by a neighbouring row.
  const observation = handshake && read.state === "read" ? read.rows.get(handshake) ?? null : null;
  const availability = availabilityOf(read, entry, handshake);
  const status: RequirementStatus = !requirement.capability_id || entry?.implementation.state === "not_implemented"
    ? "declared_no_implementation"
    : entry ? "qualified" : "provider_unknown";
  return {
    declared: requirement.declared,
    capability_id: requirement.capability_id ?? null,
    capability_name: entry?.atlas.canonical_name ?? null,
    join_basis,
    join_label: JOIN_LABEL[join_basis],
    implementation_state: stateOf(entry),
    provider: providerLabel(entry, requirement.declared),
    handshake_capability: handshake,
    status,
    status_label: STATUS_LABEL[status],
    availability,
    availability_label: AVAILABILITY_LABEL[availability],
    health: typeof observation?.health === "string" ? observation.health : null,
    missing_reason: missingReason(requirement, entry, handshake, availability),
    served_by: requirement.served_by ?? [],
    navigable: Boolean(entry),
  };
}

export function templateDefinition(template_id: string | null | undefined): TemplateDefinition | undefined {
  return TEMPLATES.find((template) => template.id === template_id);
}

/** Every requirement of one template, each with its own join, provider, availability and reason. */
export function resolveTemplateRequirements(template_id: string | null | undefined, read: CapabilityRead): RequirementRow[] {
  const template = templateDefinition(template_id);
  return template ? template.capabilities.map((requirement) => resolveRequirement(requirement, read)) : [];
}

export type TemplateRequirementRef = {
  template_id: string;
  template_name: string;
  declared: string;
  join_basis: JoinBasis;
  join_label: string;
  status: RequirementStatus;
  status_label: string;
  served_by: readonly string[];
};

/** The reverse read used by the plugin (capability) detail: which templates require this ID.
 *  Derived from the same declarations the forward table uses, so the two views cannot disagree,
 *  and it needs no new route, store or registry. */
export function templatesRequiring(capability_id: string): TemplateRequirementRef[] {
  const entry = capabilityEntry(capability_id);
  const status: RequirementStatus = entry?.implementation.state === "not_implemented"
    ? "declared_no_implementation"
    : entry ? "qualified" : "provider_unknown";
  const rows: TemplateRequirementRef[] = [];
  for (const template of TEMPLATES) {
    for (const requirement of template.capabilities) {
      if (requirement.capability_id !== capability_id) continue;
      const join_basis = joinBasisOf(requirement.declared, entry);
      rows.push({
        template_id: template.id,
        template_name: template.name,
        declared: requirement.declared,
        join_basis,
        join_label: JOIN_LABEL[join_basis],
        status,
        status_label: STATUS_LABEL[status],
        served_by: requirement.served_by ?? [],
      });
    }
  }
  return rows;
}

/** The same seven classes, in the words the surface shows. Keyed by the generated union, so a new
 *  class in the crosswalk fails to compile here instead of rendering as a blank label. */
export const SURFACE_CLASS_LABEL: Record<AbsorptionSurfaceClass, string> = {
  enableable_plugin: "可启停能力供体",
  absorbed_algorithm: "吸收算法",
  ux_donor: "体验供体",
  format_spec: "格式规范",
  base_dependency: "基础依赖",
  future_candidate: "未来候选",
  not_adopted: "未采用",
};

/** The closed vocabulary, derived from the label map rather than repeated here. The list used to
 *  name six buckets with its own ids (`frontend_plugin`, `experience_donor`) and omit `not_adopted`,
 *  so the surface could display a class the crosswalk never emits. */
export const ABSORPTION_CLASSES: readonly { id: AbsorptionSurfaceClass; label: string }[] =
  Object.entries(SURFACE_CLASS_LABEL).map(([id, label]) => ({ id: id as AbsorptionSurfaceClass, label }));
export type AbsorptionClassification = {
  confirmed: boolean;
  label: string;
  reason: string;
  donor_mapping: string;
  sources: readonly AbsorptionSurfaceRow[];
  classes: readonly { id: AbsorptionSurfaceClass; label: string }[];
};

/**
 * Absorption-source classification for one catalogued capability, read from the generated
 * projection of `docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json`.
 *
 * A capability with no row in that projection still answers 分类未确认. The projection is keyed by
 * stable capability id only, so a donor that joins to nothing cannot borrow a neighbour's class -
 * which is the whole reason the crosswalk carries its 115 vocabulary disagreements instead of
 * resolving them here.
 */
export function absorptionClassification(capability_id: string): AbsorptionClassification {
  const donor_mapping = CAPABILITY_CATALOG.donor_mapping;
  const rows = ABSORPTION_SURFACE_BY_CAPABILITY[capability_id] ?? [];
  if (!rows.length) {
    return {
      confirmed: false,
      label: "分类未确认",
      reason: `吸收来源跨接中没有以 ${capability_id} 为键的行；没有联接就不按相似名称推断分类。`,
      donor_mapping,
      sources: [],
      classes: ABSORPTION_CLASSES,
    };
  }
  const conflicts = rows.reduce((total, row) => total + row.conflicts, 0);
  return {
    confirmed: true,
    label: [...new Set(rows.map((row) => SURFACE_CLASS_LABEL[row.surface_class]))].join("、"),
    reason: `来自 ${rows.length} 条已联接来源的派生分类`
      + (conflicts ? `；其中 ${conflicts} 条带跨词汇表分歧，按原样保留，不由本视图判定胜负` : "")
      + `。可启停仅指 ${rows.filter((row) => row.surface_class === "enableable_plugin").length} 条，`
      + "其余是算法、供体、格式规范、基础依赖或候选。",
    donor_mapping,
    sources: rows,
    classes: ABSORPTION_CLASSES,
  };
}
