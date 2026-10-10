import type { SpaceId } from "../spaces/spaces";

// UI-02: the secondary level names the object groups a space actually renders.
// A section is `ready` only while the surface that owns its region is the surface
// the shell routes that space to, so no entry can lead to a silent no-op.
export type CanonicalSurface =
  | "canonical_workspace"
  | "canonical_library"
  | "canonical_knowledge"
  | "canonical_learning"
  | "canonical_capabilities"
  | "legacy";

export type SpaceSectionState = "ready" | "todo";

export type SpaceSectionDef = {
  id: string;
  label: string;
  description: string;
  state: SpaceSectionState;
  surface?: CanonicalSurface;
  region?: string;
  goto?: { space: SpaceId; section: string };
  reason?: string;
};

const WEB_HOST_REASON = "此分组由桌面宿主的本地核心读回提供；当前是 Web 开发模式，没有对应的真实对象。";

export const SPACE_SECTIONS: Readonly<Record<SpaceId, readonly SpaceSectionDef[]>> = {
  workspace: [
    { id: "documents", label: "继续阅读", description: "本地已保存文档", state: "ready", surface: "canonical_workspace", region: "documents" },
    { id: "review", label: "学习继续", description: "当前本地学习条目", state: "ready", surface: "canonical_workspace", region: "review" },
    { id: "quick_capture", label: "快速捕获", description: "导入本地原件", state: "ready", goto: {space:"intake",section:"import"} },
  ],  library: [
    { id: "sources", label: "来源原件", description: "不可变原件列表", state: "ready", surface: "canonical_library", region: "sources" },
    { id: "documents", label: "已保存文档", description: "版本化草稿与原创笔记", state: "ready", surface: "canonical_library", region: "documents" },
    { id: "anchors", label: "来源锚点", description: "绑定原件版本的引用记录", state: "ready", surface: "canonical_library", region: "anchors" },
    { id: "versions", label: "文档版本", description: "历史版本读取与恢复", state: "ready", surface: "canonical_library", region: "versions" },
  ],
  intake: [
    { id: "import", label: "导入原件", description: "选择本地文件保留原件", state: "ready", surface: "canonical_library", region: "import" },
    { id: "folder", label: "目录批量导入", description: "按目录批量登记原件", state: "ready", surface: "canonical_library", region: "folder" },
    { id: "sources", label: "已导入原件", description: "导入结果回到原件列表", state: "ready", surface: "canonical_library", region: "sources" },
    { id: "url", label: "网页与代码仓库抓取", description: "从 URL 或仓库获取内容", state: "todo", reason: "本地核心的命令面只有 source_import（本地字节），没有 URL 或仓库抓取操作；不伪造网络导入入口。" },
  ],
  vault: [
    { id: "search", label: "内容搜索", description: "按关键词读回知识、文档与提取文本", state: "ready", surface: "canonical_knowledge", region: "search" },
    { id: "candidates", label: "知识候选与审核", description: "候选正文、资格回执与审核决定", state: "ready", surface: "canonical_knowledge", region: "candidates" },
    { id: "transforms", label: "来源提取文本", description: "转换产物与来源绑定", state: "ready", surface: "canonical_knowledge", region: "transforms" },
    { id: "documents", label: "普通文档", description: "原创与未核验文档的读取编辑", state: "ready", surface: "canonical_knowledge", region: "documents" },
  ],
  evidence: [
    { id: "anchors", label: "来源引用", description: "回到绑定引用记录的原件", state: "ready", goto: { space: "library", section: "anchors" } },
    { id: "qualification", label: "资格与证据回执", description: "候选的 Core 证据读回", state: "ready", goto: { space: "vault", section: "candidates" } },
    { id: "checks", label: "专业核验台账", description: "跨文档汇总核验记录", state: "todo", reason: "document_checks 只在具体文档内读回；当前没有跨文档核验台账视图，不声称已汇总。" },
  ],
  learning: [
    { id: "review", label: "复习队列", description: "到期学习项与下次复习安排", state: "ready", surface: "canonical_learning", region: "review" },
    { id: "record", label: "复习记录与回执", description: "本次提交的历史与 Core 回执", state: "ready", surface: "canonical_learning", region: "record" },
    { id: "mastery", label: "掌握度汇总", description: "跨条目的人类掌握统计", state: "todo", reason: "learning_state 按单条学习项读回人类与机器状态；命令面没有掌握度聚合操作，不做汇总数字。" },
  ],
  "ai-assets": [
    { id: "answers", label: "受控回答", description: "在已接受知识上发起机器回答", state: "ready", goto: { space: "vault", section: "candidates" } },
    { id: "corrections", label: "纠错与复测队列", description: "跨任务的纠错、复测与审核列表", state: "todo", reason: "machine_correction 与 machine_retest 已在命令面，按单个任务读回；当前没有独立纠错队列视图。" },
  ],
  exchange: [
    { id: "export", label: "文档导出回执", description: "Markdown 与 Obsidian 导出结果", state: "ready", surface: "canonical_library", region: "export" },
    { id: "sources", label: "待交换的原件", description: "回到原件列表选择导出对象", state: "ready", surface: "canonical_library", region: "sources" },
    { id: "outbox", label: "投递队列", description: "外部投递与回执状态", state: "todo", reason: "导出写入产品资料目录后由外部应用读取；当前没有投递队列的 Core 读回入口。" },
  ],
  settings: [
    { id: "capabilities", label: "本机能力与健康", description: "Atlas 投影与当前 worker 握手", state: "ready", surface: "canonical_capabilities", region: "catalog" },
    { id: "details", label: "能力详情", description: "所选能力的前提、依赖与下一步", state: "ready", surface: "canonical_capabilities", region: "details" },
    { id: "provider", label: "模型与 Provider 配置", description: "在本机界面调整模型提供方", state: "todo", reason: "模型与 Provider 由 config 文件承担，命令面没有配置读写操作；不在界面伪造配置项。" },
  ],
};

export function spaceSectionsFor(spaceId: SpaceId, surface: CanonicalSurface): readonly SpaceSectionDef[] {
  return SPACE_SECTIONS[spaceId].map((section) => {
    if (section.state === "todo" || !section.surface) return section;
    if (section.surface === surface) return section;
    return { ...section, state: "todo", surface: undefined, region: undefined, reason: WEB_HOST_REASON };
  });
}

export function defaultSpaceSection(spaceId: SpaceId, surface: CanonicalSurface): string | undefined {
  return spaceSectionsFor(spaceId, surface).find((section) => section.state === "ready")?.id;
}

export function focusSpaceSection(region: string): HTMLElement | null {
  const target = document.querySelector<HTMLElement>(`.app-center [data-section="${region}"]`);
  if (!target) return null;
  target.scrollIntoView?.({ block: "nearest", behavior: "auto" });
  target.focus();
  return target;
}

export function validateSpaceSections(): string[] {
  const failures: string[] = [];
  for (const [spaceId, sections] of Object.entries(SPACE_SECTIONS)) {
    const seen = new Set<string>();
    for (const section of sections) {
      if (seen.has(section.id)) failures.push(`${spaceId}: duplicate section ${section.id}`);
      seen.add(section.id);
      if (section.state === "ready") {
        const hasRegion = Boolean(section.surface && section.region);
        if (!hasRegion && !section.goto) {
          failures.push(`${spaceId}/${section.id}: ready section needs a surface with a region or a goto target`);
        }
        if (hasRegion && section.goto) {
          failures.push(`${spaceId}/${section.id}: ready section cannot claim both a region and a goto target`);
        }
      } else if (!section.reason) {
        failures.push(`${spaceId}/${section.id}: todo section must name why it is 待开发`);
      }
      if (section.goto && !SPACE_SECTIONS[section.goto.space].some((item) => item.id === section.goto?.section)) {
        failures.push(`${spaceId}/${section.id}: goto target does not exist: ${section.goto.space}/${section.goto.section}`);
      }
    }
  }
  return failures;
}
