import { useEffect, useRef, useState } from "react";
import { AaosButton, AaosField, AaosTabs } from "../design-system/AaosPrimitives";
import { coreCommand } from "../api/core";
import { RawReceiptButton } from "../components/DiagnosticConsole";
import { CAPABILITY_CATALOG, type CapabilityCatalogEntry } from "../api/generated/capability-catalog";
import { absorptionClassification, SURFACE_CLASS_LABEL, templatesRequiring } from "../templates/capabilityRequirements";
import { canNavigateToCapability, CAPABILITY_NAVIGATION_ENTRIES, CAPABILITY_PAGES, getCapabilityDestination, getCapabilityNextStep, navigationEntryMatches } from "../presentation/navigation";
import { Section } from "../components/RealData";
import { coreFailureReason, stateLabel } from "../presentation/labels";
import type { SpaceId } from "./spaces";
import type { ObjectTrailLevel } from "../components/NavTrail";
import { UI_CAPABILITY_INTENT, UI_CAPABILITY_SOURCE } from "../presentation/uiCapabilityIntent";
import { RESEARCH_BOUNDARIES } from "../presentation/researchBoundaries";
import { ModelTaskRoles } from "../components/ModelTaskRoles";
import { readScopedReadiness } from "../api/scopedReadiness";
import { capabilityPresentation, capabilityOperationName, capabilityDetailText, type CapabilityGroup } from "../presentation/capabilityCenter";
import { CapabilityPackageDetails } from "../components/CapabilityPackageDetails";
import { focusVisibleTarget } from "../presentation/focus";
import "./capabilities.css";

export function CanonicalCapabilitiesSpace({ onNavigate, onOpenPage, selectedCapabilityId, navigation, onTrail }: { onNavigate: (id: SpaceId) => void; onOpenPage?: (id: string) => void; selectedCapabilityId?: string | null; navigation?: { section: string; sequence: number }; onTrail?: (levels: readonly ObjectTrailLevel[]) => void }) {
  const [selected, setSelected] = useState<CapabilityCatalogEntry | null>(() => CAPABILITY_CATALOG.entries.find((entry) => entry.atlas.capability_id === selectedCapabilityId) ?? null);
  const [activeTab, setActiveTab] = useState(selectedCapabilityId ? "details" : "catalog");
  const detailsHeading=useRef<HTMLHeadingElement>(null),focusDetails=useRef(Boolean(selectedCapabilityId));
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<CapabilityGroup | "all">("all");
  const [observation, setObservation] = useState<{ capabilityId: string; sequence: number; expiresAt: number; rows: Map<string, Record<string, unknown>> } | null>(null);
  const live = observation && observation.capabilityId === selected?.atlas.capability_id && observation.expiresAt > Date.now() ? observation.rows : null;
  const [message, setMessage] = useState("");
  const [failureReason, setFailureReason] = useState<string | null>(null);

  const sequence=useRef(0);
  async function refresh(target=selected) {
    const generation=++sequence.current;setObservation(null);setFailureReason(null);setMessage("正在读取所选能力的状态…");
    if(!target||!target.implementation.runtime_capabilities.length){setFailureReason(null);setMessage("请选择具体运行能力；目录声明不提供运行资格，不轮询全部引擎。");return;}
    const operations:readonly string[]=target.implementation.runtime_capabilities;

    try {
      const scope=`view:${target.atlas.capability_id}`;
      const response = await coreCommand("operation_readiness",{body:{scope,operations}});
      if(generation!==sequence.current)return;
      const { snapshot, expiresAt } = readScopedReadiness(response, scope, operations);
      setObservation({capabilityId:target.atlas.capability_id,sequence:generation,expiresAt,
        rows:new Map(snapshot.operations.map(row=>[row.operation,{...row,enabled:row.permission==="ENABLED"?true:row.permission==="DISABLED"?false:undefined,health:row.connection}]))});
      setMessage("已读取当前视图的范围化状态；连接与运行资格分别保留未知，不加载模型。");
    } catch (error) {
      if(generation!==sequence.current)return;
      setObservation(null);
      setMessage("当前健康与权限读取失败，显示未知；目录详情仍可浏览。");
      setFailureReason(coreFailureReason(error));
    }
  }

  useEffect(() => { void refresh(selected);return()=>{sequence.current++;}; }, [selected]);
  useEffect(()=>{if(!observation)return;const timer=setTimeout(()=>{if(sequence.current!==observation.sequence)return;setObservation(null);setMessage("状态已过期，连接、权限与资格降级未知；按当前视图显式刷新。");},Math.max(0,observation.expiresAt-Date.now()));return()=>clearTimeout(timer);},[observation]);
  useEffect(() => {
    const entry = CAPABILITY_CATALOG.entries.find((item) => item.atlas.capability_id === selectedCapabilityId) ?? null;
    setSelected(entry);
    if (entry) {focusDetails.current=true;setActiveTab("details");}
  }, [selectedCapabilityId]);
  useEffect(()=>{
    if(activeTab!=="details"||!selected||!focusDetails.current)return;
    // Radix mounts the selected panel through Presence. Focus after that
    // commit rather than while the previous panel is still being detached.
    const frame=requestAnimationFrame(()=>{const heading=detailsHeading.current;if(!heading||!focusDetails.current)return;focusVisibleTarget(heading,null);if(document.activeElement===heading){heading.scrollIntoView?.({block:"start",inline:"nearest",behavior:"instant"});focusDetails.current=false;}});
    return()=>cancelAnimationFrame(frame);
  },[selected,activeTab]);
  useEffect(() => {
    if (!navigation?.sequence) return;
    setActiveTab(navigation.section === "details" ? "details" : "catalog");
  }, [navigation?.section, navigation?.sequence]);
  useEffect(() => {
    onTrail?.(selected ? [
      { id: "section:catalog", label: "能力目录与搜索", region: "catalog" },
      { id: selected.atlas.capability_id, label: selected.atlas.canonical_name, detail: capabilityPresentation(selected).status, region: "details" },
    ] : []);
  }, [selected, onTrail]);

  const visible = CAPABILITY_NAVIGATION_ENTRIES.filter((entry) => navigationEntryMatches(entry, query)
    && (category === "all" || capabilityPresentation(entry.capability).group === category));
  const destination = selected ? getCapabilityDestination(selected) : undefined;
  const pageDestination = selected ? CAPABILITY_PAGES[selected.atlas.capability_id] : undefined;
  const hasDestination = Boolean(destination || (pageDestination && onOpenPage));
  // The reverse read of the template suite: derived from the same declarations the template surface
  // resolves against, so the two views cannot disagree, and it owns no second template list.
  const requiring = selected ? templatesRequiring(selected.atlas.capability_id) : [];
  const absorption = selected ? absorptionClassification(selected.atlas.capability_id) : null;
  const catalog = <div className="space-section-region" data-section="catalog" tabIndex={-1} aria-label="能力目录与搜索">
    <p>从这里发现内置工作流、可选扩展和未来能力。选择用途查看入口与条件；尚未接入的条目也保留说明。</p>
    <p>插件、技能与 MCP 是接入形式；当前目录不提供未经实现的安装或执行操作。</p>
    <AaosField label="查找能力" value={query} onChange={(event) => setQuery(event.currentTarget.value)} placeholder="名称、用途、对象或依赖" />
    <div className="capability-center-filters" role="group" aria-label="能力分类">{([
      ["all", "全部"], ["builtin", "内置能力"], ["extension", "扩展能力"], ["future", "未来规划"],
    ] as const).map(([id,label])=><AaosButton key={id} aria-pressed={category===id} onClick={()=>setCategory(id)}>{label}</AaosButton>)}</div>
    <div className="capability-actions"><AaosButton variant="secondary" onClick={() => void refresh()}>刷新当前健康与权限</AaosButton>
      <span>目录收录 {CAPABILITY_CATALOG.entries.length} 项能力；筛选结果 {visible.length} 项。条目数量不是能力上限。</span></div>
    {!visible.length ? <p role="status">没有符合条件的能力；可以清空搜索或切换分类。</p> : null}
    <ul className="capability-directory capability-center-list">{visible.map((navigationEntry) => {const view=capabilityPresentation(navigationEntry.capability);return <li key={navigationEntry.entry_id}>
      <button data-entry-id={navigationEntry.entry_id} onClick={() => { focusDetails.current=true;setSelected(navigationEntry.capability); setActiveTab("details"); }}>
        <b>{navigationEntry.label}</b><span>{view.purpose}</span><small>{view.form}</small>
      </button>
      <span>{view.status}</span>
    </li>;})}</ul>
  </div>;

  const details = <div className="space-section-region" data-section="details" tabIndex={-1} aria-label="能力详情">{selected ? <article aria-label="能力详情">
    <h3 ref={detailsHeading} tabIndex={-1}>{selected.atlas.canonical_name}</h3>
    <p>{capabilityPresentation(selected).purpose}</p>
    <p>{capabilityPresentation(selected).status} · {capabilityPresentation(selected).form}</p>
    <RawReceiptButton label="能力登记与运行声明" payload={{atlas:selected.atlas,implementation:selected.implementation}} />
    <p>相关视图：{selected.atlas.views.join("、")}</p>
    <p>依赖声明：{selected.atlas.dependencies.length ? selected.atlas.dependencies.join("、") : "目录未列依赖"}</p>
    <p>执行前提：{selected.atlas.entry_gate.map(capabilityDetailText).join("；") || "目录未列前提"}</p>
    <p>所需验收证据：{selected.atlas.exit_evidence.map(capabilityDetailText).join("；") || "目录未列证据要求"}</p>
    <p>降级与回退：{selected.atlas.fallbacks.map(capabilityDetailText).join("；") || "目录未列回退"}</p>
    <section aria-label="设计细项与独立证据">
      <h4>新设计保留的细项</h4>
      <p>以下来自设计输入，每项是否实现仍待独立核验。父能力声明和运行握手不证明这些细项全部完成。</p>
      <ul>{(UI_CAPABILITY_INTENT[selected.atlas.capability_id] ?? []).map(intent => <li key={intent}>{capabilityDetailText(intent)} · 独立证据未核验</li>)}</ul>
      <RawReceiptButton label="设计来源与校验指纹" payload={{source:UI_CAPABILITY_SOURCE,items:UI_CAPABILITY_INTENT[selected.atlas.capability_id]??[]}} />
    </section>
    <p>下一步：{getCapabilityNextStep(selected, Boolean(onOpenPage))}</p>
    {RESEARCH_BOUNDARIES[selected.atlas.capability_id] && <section aria-label="集合与研究实施边界">
      <h4>当前入口提供的范围</h4>
      <p>以下是本地入口范围，安装态、真人验收与来源平台语义资格仍分别核验。</p>
      <ul>{RESEARCH_BOUNDARIES[selected.atlas.capability_id].available.map(item => <li key={item}>{item}</li>)}</ul>
      <h4>待实现或待独立资格验收</h4>
      <ul>{RESEARCH_BOUNDARIES[selected.atlas.capability_id].pending.map(item => <li key={item}>{item} · 未执行</li>)}</ul>
    </section>}
    <p>{absorption?.sources.length ? "以下复用来源按当前能力登记关联；分类与历史验证分别保留，不代表本轮运行通过。" : "供体映射未建立；不按相似名称推断已吸收关系。"}</p>
    <div>吸收来源分类：{absorption?.label}。{absorption?.sources.length
      ? <ul>{absorption!.sources.map((row) => <li key={`${row.source}/${row.surface_class}`}>{row.source}<p>类别：{SURFACE_CLASS_LABEL[row.surface_class]} · 历史验证层级 {row.verification_tier ?? "未分层"} · 历史可用登记：{row.currently_usable ? "是" : "否"}（不代表当前运行可用） · 跨词汇表分歧 {row.conflicts} 条</p></li>)}</ul>
      : <>候选类别为 {absorption!.classes.map((item) => item.label).join("、")}；尚未登记此能力的复用来源。</>}
    </div>
    <RawReceiptButton label="复用来源登记" payload={absorption} />
    <h4>使用此能力的模板</h4>
    {requiring.length ? <ul className="capability-directory">{requiring.map((reference) => <li key={`${reference.template_id}:${reference.declared}`}>
      <b>{reference.template_id} {reference.template_name}</b>
      <small>{reference.declared} · {reference.join_label} · {reference.status_label}</small>
    </li>)}</ul> : <p>模板套件当前没有声明此能力；这不代表能力无用，只代表联接尚未建立。</p>}
    <p>{requiring.length ? "此处只列声明了该 ID 的模板；模板不复制插件代码、依赖安装或连接配置。对象在资料库的「学科模板」展开区，本视图不建立第二份模板清单。" : "无声明联接时不提供跳转，避免打开一个没有对象的入口。"}</p>
    {requiring.length ? <AaosButton variant="secondary" onClick={() => onNavigate("library")}>到资料库打开学科模板</AaosButton> : null}
    <CapabilityPackageDetails capabilityId={selected.atlas.capability_id} />
    <h4>当前运行联接、权限与健康</h4>
    <ModelTaskRoles capabilities={live} scopeLabel={selected.atlas.canonical_name}/>
    <p>功能登记不代表本轮已成功执行；请分别核对连接、权限与业务验证。</p>
    {selected.implementation.runtime_capabilities.length ? <ul>{selected.implementation.runtime_capabilities.map((capability) => {
      const observation = live?.get(capability);
      const name=capabilityOperationName(capability);
      return <li key={capability}>{name}<p>连接/权限：{typeof observation?.enabled === "boolean" ? (observation.enabled ? "允许" : "已禁用") : "未知"} · 即时健康：{stateLabel(typeof observation?.health==="string"?observation.health.toLowerCase():null)}</p><p>业务运行尚未独立验证。{observation?.enabled===false?"此步骤已禁用，请先核对权限设置。":!observation?"尚未取得有效状态，请刷新后再试。":"详细原因可在运行诊断中核对。"}</p>
        {/* The line above is the human-readable reading surface; the untouched handshake readback goes
            to the diagnostic console, the same channel this file already uses for the catalog sources. */}
        {observation ? <RawReceiptButton label={`能力运行详细信息 · ${name}`} payload={observation} /> : null}</li>;
    })}</ul> : <p>{selected.implementation.state === "not_implemented" ? "没有当前运行实现，执行动作不可用。" : "此功能由应用内部提供；当前页面尚不能确认它是否可用。"}</p>}
    <p>使用后可在该任务的运行诊断中查看处理方式、版本和结果质量。</p>
    {selected.atlas.capability_id === "CAP-0150" ? <p>完整模型管理尚不可用；你可以单独查看现有的模型连接与用途设置。<AaosButton disabled={!onOpenPage} disabledReason={!onOpenPage ? "当前无法打开模型设置页面" : undefined} onClick={()=>onOpenPage?.("19")}>查看现有模型配置</AaosButton></p> : null}
    <AaosButton variant="primary" disabled={!hasDestination || !canNavigateToCapability(selected)}
      disabledReason={!hasDestination ? "当前没有可打开的产品入口" : undefined} onClick={() => { if (pageDestination && onOpenPage) onOpenPage(pageDestination); else if (destination) onNavigate(destination); }}>
      {hasDestination ? "打开当前产品入口" : "当前执行入口尚未提供"}
    </AaosButton>
  </article> : <p>从目录选择能力，查看用途、前提、依赖、状态、降级和下一步。</p>}</div>;

  return <Section title="能力中心">
    <AaosTabs label="能力目录视图" value={activeTab} onValueChange={setActiveTab} tabs={[
      { id: "catalog", label: "目录与搜索", content: catalog },
      { id: "details", label: "能力详情", content: details },
    ]} />
    {message ? <p role="status">{message}</p> : null}
    {failureReason ? <p className="state-reason">{failureReason}</p> : null}
    <p>此目录与应用内的能力登记保持一致；具体执行结果以相应任务为准。</p>
    <RawReceiptButton label="目录投影来源与哈希" payload={CAPABILITY_CATALOG.sources} />
  </Section>;
}
