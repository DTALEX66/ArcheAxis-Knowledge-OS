import { useEffect, useState } from "react";
import { AaosButton, AaosField, AaosTabs } from "../design-system/AaosPrimitives";
import { coreCommand } from "../api/core";
import { RawReceiptButton } from "../components/DiagnosticConsole";
import { CAPABILITY_CATALOG, type CapabilityCatalogEntry } from "../api/generated/capability-catalog";
import { canNavigateToCapability, CAPABILITY_NAVIGATION_ENTRIES, getCapabilityDestination, getCapabilityNextStep, navigationEntryMatches } from "../presentation/navigation";
import { Section } from "../components/RealData";
import { coreFailureReason } from "../presentation/labels";
import type { SpaceId } from "./spaces";
import type { ObjectTrailLevel } from "../components/NavTrail";

function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("invalid response");
  return value as Record<string, unknown>;
}

export function CanonicalCapabilitiesSpace({ onNavigate, selectedCapabilityId, navigation, onTrail }: { onNavigate: (id: SpaceId) => void; selectedCapabilityId?: string | null; navigation?: { section: string; sequence: number }; onTrail?: (levels: readonly ObjectTrailLevel[]) => void }) {
  const [selected, setSelected] = useState<CapabilityCatalogEntry | null>(() => CAPABILITY_CATALOG.entries.find((entry) => entry.atlas.capability_id === selectedCapabilityId) ?? null);
  const [activeTab, setActiveTab] = useState(selectedCapabilityId ? "details" : "catalog");
  const [query, setQuery] = useState("");
  const [live, setLive] = useState<Map<string, Record<string, unknown>> | null>(null);
  const [message, setMessage] = useState("");
  const [failureReason, setFailureReason] = useState<string | null>(null);

  async function refresh() {
    try {
      const response = record(await coreCommand("capabilities_list"));
      if (!Array.isArray(response.capabilities)) throw new Error("invalid capability list");
      const rows = response.capabilities.map(record);
      if (rows.some((row) => typeof row.capability !== "string")) throw new Error("invalid capability identity");
      setLive(new Map(rows.map((row) => [String(row.capability), row])));
      setMessage("已读取当前 Core worker 握手；不代表引擎产物通过。");
    } catch (error) {
      setLive(null);
      setMessage("当前健康与权限读取失败，显示未知；目录详情仍可浏览。");
      setFailureReason(coreFailureReason(error));
    }
  }

  useEffect(() => { void refresh(); }, []);
  useEffect(() => {
    const entry = CAPABILITY_CATALOG.entries.find((item) => item.atlas.capability_id === selectedCapabilityId) ?? null;
    setSelected(entry);
    if (entry) setActiveTab("details");
  }, [selectedCapabilityId]);
  useEffect(() => {
    if (!navigation?.sequence) return;
    setActiveTab(navigation.section === "details" ? "details" : "catalog");
  }, [navigation?.section, navigation?.sequence]);
  useEffect(() => {
    onTrail?.(selected ? [
      { id: "section:catalog", label: "能力目录与搜索", region: "catalog" },
      { id: selected.atlas.capability_id, label: selected.atlas.canonical_name, detail: `${selected.atlas.capability_id} · ${selected.implementation.state}`, region: "details" },
    ] : []);
  }, [selected, onTrail]);

  const visible = CAPABILITY_NAVIGATION_ENTRIES.filter((entry) => navigationEntryMatches(entry, query));
  const destination = selected ? getCapabilityDestination(selected) : undefined;
  const catalog = <div className="space-section-region" data-section="catalog" tabIndex={-1} aria-label="能力目录与搜索">
    <p>入口身份与别名由 Atlas 投影生成；能力声明、实际实现和运行资格分别核对。未来条目仍可查看用途与前提。</p>
    <AaosField label="查找能力" value={query} onChange={(event) => setQuery(event.currentTarget.value)} placeholder="名称、ID、对象、依赖或旧入口别名" />
    <div className="capability-actions"><AaosButton variant="secondary" onClick={() => void refresh()}>刷新当前健康与权限</AaosButton>
      <span>{CAPABILITY_CATALOG.entries.length} 项 Atlas 投影；筛选结果 {visible.length} 项。条目数量不是能力上限。</span></div>
    <ul className="capability-directory">{visible.map((navigationEntry) => <li key={navigationEntry.entry_id}>
      <button data-entry-id={navigationEntry.entry_id} onClick={() => { setSelected(navigationEntry.capability); setActiveTab("details"); }}>
        <b>{navigationEntry.label}</b><small>{navigationEntry.entry_id} · {navigationEntry.group_id} · {navigationEntry.description}</small>
      </button>
      <span>{navigationEntry.capability.implementation.state === "not_implemented" ? "尚未实现" : navigationEntry.capability.implementation.state === "worker_backed" ? "worker 实现声明" : "Core 原生实现声明"}</span>
    </li>)}</ul>
  </div>;

  const details = <div className="space-section-region" data-section="details" tabIndex={-1} aria-label="能力详情">{selected ? <article aria-label="能力详情">
    <h4>{selected.atlas.canonical_name}</h4>
    <p>稳定入口 ID {selected.atlas.capability_id}</p>
    <p>目录声明：{selected.atlas.authority_status} · 技术 {selected.atlas.technical_state} · 路线 {selected.atlas.roadmap_state} · 时段 {selected.atlas.activation_horizon}</p>
    <p>场景对象：{selected.atlas.objects.join("、")}</p><p>相关视图：{selected.atlas.views.join("、")}</p>
    <p>依赖声明：{selected.atlas.dependencies.length ? selected.atlas.dependencies.join("、") : "目录未列依赖"}</p>
    <p>执行前提：{selected.atlas.entry_gate.join("；") || "目录未列前提"}</p>
    <p>所需验收证据：{selected.atlas.exit_evidence.join("；") || "目录未列证据要求"}</p>
    <p>降级与回退：{selected.atlas.fallbacks.join("；") || "目录未列回退"}</p>
    <p>旧入口别名：{selected.atlas.origin_requirement_ids.join("、") || "目录未列旧别名"}</p>
    <p>下一步：{getCapabilityNextStep(selected)}</p>
    <p>供体映射未建立；不按相似名称推断已吸收关系。</p>
    <h4>当前运行联接、权限与健康</h4>
    <p>实现声明来源：config/capability-map.v1.json · {selected.implementation.state}。声明本身不证明本轮执行。</p>
    {selected.implementation.runtime_capabilities.length ? <ul>{selected.implementation.runtime_capabilities.map((capability) => {
      const observation = live?.get(capability);
      return <li key={capability}>{capability}<p>连接/权限：{typeof observation?.enabled === "boolean" ? (observation.enabled ? "允许" : "已禁用") : "未知"} · 即时健康：{typeof observation?.health === "string" ? observation.health : "未观察"}</p>
        {/* The line above is the human-readable reading surface; the untouched handshake readback goes
            to the diagnostic console, the same channel this file already uses for the catalog sources. */}
        {observation ? <RawReceiptButton label={`Core 握手原始读回 · ${capability}`} payload={observation} /> : null}</li>;
    })}</ul> : <p>{selected.implementation.state === "not_implemented" ? "没有当前运行实现，执行动作不可用。" : "此项声明为 Core 原生；worker 握手不提供该项的运行证据。"}</p>}
    <p>实际引擎身份、版本与产物质量需在具体 job 的质量回执核验。</p>
    <AaosButton variant="primary" disabled={!destination || !canNavigateToCapability(selected)}
      disabledReason={!destination ? "当前没有可打开的产品入口" : undefined} onClick={() => { if (destination) onNavigate(destination); }}>
      {destination ? "打开当前产品入口" : "当前执行入口尚未提供"}
    </AaosButton>
  </article> : <p>从目录选择能力，查看用途、前提、依赖、状态、降级和下一步。</p>}</div>;

  return <Section title="全能力目录">
    <AaosTabs label="能力目录视图" value={activeTab} onValueChange={setActiveTab} tabs={[
      { id: "catalog", label: "目录与搜索", content: catalog },
      { id: "details", label: "能力详情", content: details },
    ]} />
    {message ? <p role="status">{message}</p> : null}
    {failureReason ? <p className="state-reason">{failureReason}</p> : null}
    <p>此视图使用生成的 Atlas/implementation 投影，不建立第二份能力真值。</p>
    <RawReceiptButton label="目录投影来源与哈希" payload={CAPABILITY_CATALOG.sources} />
  </Section>;
}
