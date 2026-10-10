import { useCallback, useEffect, useId, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import { RESOURCE_CATALOG, type ResourceClass, type ResourceEntry, type ResourceEvidence, type ResourceJson } from "../api/generated/resource-catalog";
import { RawReceiptButton } from "../components/DiagnosticConsole";
import { AaosField, AaosTabs } from "../design-system/AaosPrimitives";
import { SURFACE_CLASS_LABEL } from "../templates/capabilityRequirements";
import { TemplateWorkspace } from "../templates/TemplateWorkspace";
import { coreFailureReason } from "../presentation/labels";
import "./resources.css";

type Handshake = { capability: string; enabled?: boolean; health?: string; [key: string]: unknown };
type Read = { state: "not_read" } | { state: "reading" } | { state: "failed"; reason: string } | { state: "read"; rows: Handshake[] };

/** Never reduce a malformed/duplicate native receipt to a partial successful capability list. */
export function readResourceHandshake(value: unknown): Handshake[] {
  if (!value || typeof value !== "object" || !Array.isArray((value as { capabilities?: unknown }).capabilities)) throw new Error("invalid capability list");
  const rows = (value as { capabilities: unknown[] }).capabilities;
  const ids = new Set<string>();
  return rows.map(row => {
    if (!row || typeof row !== "object" || Array.isArray(row)) throw new Error("invalid capability row");
    const item = row as Record<string, unknown>;
    if (typeof item.capability !== "string" || !item.capability || ids.has(item.capability)) throw new Error("invalid/duplicate capability identity");
    if (item.enabled !== undefined && typeof item.enabled !== "boolean") throw new Error("invalid capability permission");
    if (item.health !== undefined && typeof item.health !== "string") throw new Error("invalid capability health");
    ids.add(item.capability);
    return item as Handshake;
  });
}

export function readCapabilityDecision(value: unknown, capability: string, enabled: boolean): Handshake {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("invalid capability decision");
  const row = (value as { capability?: unknown }).capability;
  const [decision] = readResourceHandshake({ capabilities: [row] });
  if (decision.capability !== capability || decision.enabled !== enabled || decision.enabled_basis !== "the workspace's capability record; an absent record means enabled") throw new Error("unconfirmed capability decision");
  return decision;
}

function Values({ value }: { value: ResourceJson }) {
  if (value === null) return <span>未登记</span>;
  if (Array.isArray(value)) return value.length ? <ul>{value.map((item, index) => <li key={index}><Values value={item}/></li>)}</ul> : <span>未列出</span>;
  if (typeof value === "object") return <dl>{Object.entries(value).map(([key, item]) => <div key={key}><dt>{key}</dt><dd><Values value={item}/></dd></div>)}</dl>;
  return <span>{String(value)}</span>;
}

function Evidence({ title, evidence }: { title: string; evidence: ResourceEvidence }) {
  return <section aria-label={title} className="resources-evidence"><h5>{title} · {evidence.state}</h5><Values value={evidence.value}/>
    <p>本项来源：{evidence.source_refs.map(source => source.path).join("；") || "未登记"}</p>
    {evidence.source_refs.length ? <details><summary>核对来源指纹</summary><ul>{evidence.source_refs.map((source, index) => <li key={`${source.path}:${index}`}><span>{source.path}</span><br/><code>SHA-256 {source.sha256}</code></li>)}</ul></details> : null}
    <RawReceiptButton label={`${title}来源与原始登记`} payload={evidence}/>
  </section>;
}

export function CanonicalResourcesSpace({ onOpenDocument, onOpenCapability, onDirtyChange }: {
  onOpenDocument?: (id: string) => void;
  onOpenCapability?: (id: string) => void;
  onDirtyChange?: (dirty: boolean) => void;
}) {
  const [tab, setTab] = useState("resources");
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<ResourceClass | "all">("all");
  const [selected, setSelected] = useState<ResourceEntry | null>(null);
  const [read, setRead] = useState<Read>({ state: "not_read" });
  const [message, setMessage] = useState("");
  const [changing, setChanging] = useState<string | null>(null);
  const [decisionNotice, setDecisionNotice] = useState<{ failed: boolean; text: string } | null>(null);
  const writePending = useRef(false);
  const generation = useRef(0), mounted = useRef(true), templateDirty = useRef(false);
  const owner = useId();
  const callbacks = useRef({ onDirtyChange, onOpenDocument });
  callbacks.current = { onDirtyChange, onOpenDocument };

  const onTemplateDirty = useCallback((dirty: boolean) => {
    templateDirty.current = dirty;
    callbacks.current.onDirtyChange?.(dirty);
    window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: { owner, dirty } }));
  }, [owner]);
  async function refresh() {
    const epoch = ++generation.current;
    setRead({ state: "reading" });
    try {
      const rows = readResourceHandshake(await coreCommand("capabilities_list"));
      if (mounted.current && epoch === generation.current) {
        setRead({ state: "read", rows });
        return rows;
      }
    } catch (reason) {
      if (mounted.current && epoch === generation.current) setRead({ state: "failed", reason: coreFailureReason(reason) ?? "UNKNOWN" });
    }
  }
  async function changeEnabled(row: Handshake) {
    if (writePending.current || typeof row.enabled !== "boolean" || templateDirty.current) return;
    writePending.current = true;
    const enabled = !row.enabled;
    const epoch = ++generation.current;
    setChanging(row.capability);
    setDecisionNotice(null);
    setRead({ state: "reading" });
    try {
      readCapabilityDecision(await coreCommand("capability_set_enabled", { capability: row.capability, enabled }), row.capability, enabled);
      if (!mounted.current || epoch !== generation.current) return;
      const rows = await refresh();
      if (!mounted.current) return;
      const actual = rows?.find(item => item.capability === row.capability);
      if (actual?.enabled !== enabled || actual.enabled_basis !== "the workspace's capability record; an absent record means enabled") throw new Error("decision readback unavailable");
      setDecisionNotice({ failed: false, text: `${row.capability} 已${enabled ? "启用" : "禁用"}，工作区设置已读回。引擎运行与产物质量仍须独立验证。` });
    } catch {
      if (!mounted.current) return;
      setDecisionNotice({ failed: true, text: `${row.capability} 的变更未获确认；可能已写入。请核对当前读回状态后再操作，不自动重发。` });
      await refresh();
    } finally {
      writePending.current = false;
      if (mounted.current) setChanging(null);
    }
  }
  useEffect(() => {
    mounted.current = true;
    void refresh();
    return () => { mounted.current = false; generation.current++; onTemplateDirty(false); };
  }, [onTemplateDirty]);

  function changeTab(next: string) {
    if (templateDirty.current) { setMessage("模板有未保存修改或冻结请求；请先在模板工作区保存或处理，再切换目录。"); return; }
    setMessage(""); setTab(next);
  }
  const term = query.trim().toLocaleLowerCase();
  const visible = RESOURCE_CATALOG.entries.filter(entry => (category === "all" || entry.surface_class === category)
    && (!term || JSON.stringify({ names: entry.display_names, key: entry.stable_key, mode: entry.absorption_mode, reason: entry.classification_reason, qualification: entry.qualification.reason, conflicts: entry.original_surface.conflicts }).toLocaleLowerCase().includes(term)));
  const observed = selected?.declared_runtime_route && read.state === "read" ? read.rows.find(row => row.capability === selected.declared_runtime_route) : undefined;
  const originalConflicts = selected?.original_surface.conflicts;
  const conflicts = Array.isArray(originalConflicts) ? originalConflicts : [];

  const directory = <section aria-label="资源供体目录">
    <p>完整保留 {RESOURCE_CATALOG.entries.length} 项吸收来源及 {String(RESOURCE_CATALOG.crosswalk_metadata.conflict_count)} 条原冲突。类别、吸收方式和登记资格分别陈述；数量不代表集成数。</p>
    <p>原交叉登记观察时间 {String(RESOURCE_CATALOG.crosswalk_metadata.observed_at)}。历史 tier/currently_usable 字段保留为登记，不能作为本次宿主资格。</p>
    <div className="resources-controls"><AaosField label="查找资源与原冲突" value={query} onChange={event => setQuery(event.currentTarget.value)}/>
      <div><label htmlFor={`${owner}-resource-class`}>来源类别</label><select id={`${owner}-resource-class`} value={category} onChange={event => setCategory(event.currentTarget.value as ResourceClass | "all")}><option value="all">全部来源</option>{Object.entries(SURFACE_CLASS_LABEL).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></div>
    </div>
    <p>筛选结果 {visible.length} 项；不自动安装、升级、授权或启动供体。</p>
    <div className="ui-content-main-side resources-directory">
      <ul className="resources-list">{visible.map(entry => <li key={entry.stable_key}><button aria-pressed={selected?.stable_key === entry.stable_key} onClick={() => setSelected(entry)}>
        <strong>{entry.display_names[0] || entry.stable_key}</strong><span>{SURFACE_CLASS_LABEL[entry.surface_class]} · {entry.absorption_mode}</span>
      </button></li>)}</ul>
      <aside aria-label="资源登记详情" className="semantic-panel">{selected ? <>
        <h3>{selected.display_names[0]}</h3><p>身份 {selected.stable_key}</p>
        <p>来源类别：{SURFACE_CLASS_LABEL[selected.surface_class]}；吸收模式：{selected.absorption_mode}</p>
        <p>分类原因：{selected.classification_reason}</p>
        <p>处置登记：{selected.qualification.disposition}；{selected.qualification.reason}</p>
        <section aria-label="激活与冻结条件"><h4>激活与冻结条件 · {selected.qualification.activation.state}</h4>
          <Values value={selected.qualification.activation.scope}/><Values value={selected.qualification.activation.conditions}/>
          <p>这是可复核条件登记，不是执行授权。</p>
        </section>
        <Evidence title="版本证据" evidence={selected.qualification.evidence.version}/>
        <Evidence title="许可证证据" evidence={selected.qualification.evidence.license}/>
        <Evidence title="权限证据" evidence={selected.qualification.evidence.permissions}/>
        <Evidence title="运行证据" evidence={selected.qualification.evidence.runtime}/>
        <Evidence title="实测资格" evidence={selected.qualification.evidence.qualification}/>
        <section aria-label="原始登记冲突"><h4>原始登记冲突 · {conflicts.length}</h4>
          {conflicts.length ? <ol>{conflicts.map((conflict, index) => <li key={index}><Values value={conflict}/></li>)}</ol> : <p>此记录未列原冲突；不等于本次资格通过。</p>}
        </section>
        <section aria-label="供体运行联接"><h4>供体运行联接</h4>
          <p>{selected.declared_runtime_route ? `原登记路线 ${selected.declared_runtime_route}` : "原登记无单一运行路线；不按相似名称联接。"}</p>
          <p>{read.state !== "read" ? "本轮运行状态未知。" : !selected.declared_runtime_route ? "没有可直接对应的 worker 握手。" : !observed ? "当前宿主未返回这条握手。" : `当前路线权限 ${observed.enabled === true ? "允许" : observed.enabled === false ? "已禁用" : "UNKNOWN"}；健康 ${observed.health ?? "UNKNOWN"}`}</p>
          <p>路线握手不证明所选供体的引擎版本、许可证或实际产物质量。</p>
        </section>
        <RawReceiptButton label="完整供体与历史冲突登记" payload={selected}/>
      </> : <p>选择一个真实登记来源，查看原始分类、冲突和激活条件。</p>}</aside>
    </div>
    <section aria-label="当前宿主能力读回"><h3>当前宿主能力读回</h3>
      <button disabled={changing !== null} onClick={() => void refresh()}>重新读取当前宿主能力</button>
      <p>逐项改变当前工作区的执行开关，不安装供体，也不修改模型或默认 provider。禁用阻止后续执行申请，不取消已经运行的任务。</p>
      {changing ? <p role="status">正在更新 {changing}，等待核心确认与读回…</p> : null}
      {decisionNotice ? <p role={decisionNotice.failed ? "alert" : "status"}>{decisionNotice.text}</p> : null}
      {read.state === "reading" ? <p role="status">正在读取宿主能力…</p> : read.state === "failed" ? <p role="alert">宿主读取失败：{read.reason}。资格 UNKNOWN，资源目录仍完整保留。</p> : read.state === "not_read" ? <p>本轮未读取（NOT_RUN）。</p> : <>
        <p>已读回 {read.rows.length} 条宿主能力；不代表 {RESOURCE_CATALOG.entries.length} 项供体均集成。</p>
        {read.rows.length ? <ul>{read.rows.map(row => <li key={row.capability}>{row.capability} · 权限 {row.enabled === true ? "允许" : row.enabled === false ? "已禁用" : "UNKNOWN"} · 健康 {row.health ?? "UNKNOWN"} {typeof row.enabled === "boolean" && row.enabled_basis === "the workspace's capability record; an absent record means enabled" ? <button disabled={changing !== null} aria-label={`${row.enabled === false ? "启用" : "禁用"} ${row.capability}`} onClick={() => void changeEnabled(row)}>{row.enabled === false ? "启用" : "禁用"}</button> : <span> · 执行设置未确认，无法变更</span>}</li>)}</ul> : <p>宿主返回空能力列表；不填造运行项。</p>}
      </>}
      <RawReceiptButton label="当前宿主能力原始读回" payload={read}/>
    </section>
    <RawReceiptButton label="资源单源投影及冻结登记" payload={{ sources: RESOURCE_CATALOG.sources, original: RESOURCE_CATALOG.crosswalk_metadata, overlay: RESOURCE_CATALOG.qualification_metadata, freeze: RESOURCE_CATALOG.freeze_register }}/>
  </section>;
  return <section aria-label="资源与扩展" className="ui-resources"><h2>资源与扩展</h2>
    <AaosTabs label="资源与模板工作区" value={tab} onValueChange={changeTab} tabs={[
      { id: "resources", label: "吸收来源与供体", content: directory },
      { id: "templates", label: "学科模板", content: <div className="template-launcher"><TemplateWorkspace onOpen={id => {
        if (callbacks.current.onOpenDocument) callbacks.current.onOpenDocument(id);
        else setMessage("当前宿主未提供文档阅读入口；已保存模板仍保留。");
      }} onOpenCapability={onOpenCapability} onDirtyChange={onTemplateDirty}/></div> },
    ]}/>
    {message ? <p role="status">{message}</p> : null}
  </section>;
}
