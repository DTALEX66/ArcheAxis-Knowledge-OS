import { useCallback, useEffect, useId, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import { RESOURCE_CATALOG, type ResourceClass, type ResourceEntry, type ResourceEvidence } from "../api/generated/resource-catalog";
import { RawReceiptButton } from "../components/DiagnosticConsole";
import { AaosField, AaosTabs } from "../design-system/AaosPrimitives";
import { SURFACE_CLASS_LABEL } from "../templates/capabilityRequirements";
import { TemplateWorkspace } from "../templates/TemplateWorkspace";
import { T3LifecycleControls } from "../templates/T3LifecycleControls";
import { changeTemplate, type Definition, type TemplateAction, type TemplateState } from "../templates/templateLifecycle";
import { capabilityHealthLabel, coreFailureReason, jobKindLabel } from "../presentation/labels";
import { capabilityOperationName } from "../presentation/capabilityCenter";
import { readResourceHandshake, readCapabilityDecision, type CapabilityHandshake as Handshake } from "../api/capabilitySettings";
import "./resources.css";

export { readResourceHandshake, readCapabilityDecision } from "../api/capabilitySettings";
type Read = { state: "not_read" } | { state: "reading" } | { state: "failed"; reason: string } | { state: "read"; rows: Handshake[] };

const evidenceStateLabel: Record<string,string> = { FORMAT_REFERENCE:"格式说明", HISTORICAL_SOURCE_NOT_CURRENT:"仅有历史记录", LOCK_PINNED:"版本已记录", SOURCE_CONTRACT:"来源要求已记录", UNVERIFIED:"尚未核实", DECLARED_NOT_REQUALIFIED:"已有声明，尚未重新核实", LOCAL_DECLARATION_WITH_OFFICIAL_READBACK:"本机声明已核对", OFFICIAL_READBACK_NOT_EXACT_SNAPSHOT:"已查到公开资料，版本仍待核对", DECLARED_INHERITED:"沿用已有声明", NOT_RUN:"尚未运行核对", INHERITED_ONLY:"仅有历史依据" };
const dispositionLabel: Record<string,string> = { CURRENT_PAGE_SELECTED:"当前选用", FROZEN_NOT_SELECTED:"暂未选用", "REJECT-CORE":"不适用", "REVIEW-BLOCK":"等待审核" };
const absorptionLabel: Record<string,string> = { ALGORITHM_DONOR:"参考处理方法", CONTRACT_ADAPTER:"通过适配器接入", DIRECT_DEPENDENCY:"作为基础组件", PYTHON_WORKER:"通过文件处理服务接入", REFERENCE_ONLY:"仅供参考", SELF_BUILD_GAP:"功能仍待实现", SIDECAR:"通过独立服务接入", UX_DONOR:"参考交互设计" };
const capabilityName = (capability: string) => capability === "text.extract" ? jobKindLabel(capability) : capabilityOperationName(capability);

function Evidence({ title, evidence }: { title: string; evidence: ResourceEvidence }) {
  return <section aria-label={title} className="resources-evidence"><h5>{title} · {evidenceStateLabel[evidence.state] ?? "尚未核实"}</h5>
    <p>{evidence.source_refs.length ? "依据已登记，可查看详细信息。" : "尚未登记依据。"}</p>

    <RawReceiptButton label={`${title}来源与原始登记`} payload={evidence}/>
  </section>;
}

export function CanonicalResourcesSpace({ onOpenDocument, onOpenCapability, onDirtyChange }: {
  onOpenDocument?: (id: string) => void;
  onOpenCapability?: (id: string) => void;
  onDirtyChange?: (dirty: boolean) => void;
}) {
  const [tab, setTab] = useState("templates");
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
      setDecisionNotice({ failed: false, text: `${capabilityName(row.capability)}已${enabled ? "启用" : "禁用"}，工作区设置已确认。实际运行与结果质量仍须单独验证。` });
    } catch {
      if (!mounted.current) return;
      setDecisionNotice({ failed: true, text: `${capabilityName(row.capability)}的变更未获确认；可能已保存。请重新查看当前设置后再操作，不会自动重试。` });
      await refresh();
    } finally {
      writePending.current = false;
      if (mounted.current) setChanging(null);
    }
  }
  async function changeT3(state:TemplateState,action:TemplateAction,target=state.definition) {
    if(writePending.current||templateDirty.current)return;
    writePending.current=true;setChanging("template.T3");setDecisionNotice(null);
    try {
      const next=await changeTemplate(state,action,target);
      if(!mounted.current)return;
      setRead(old=>old.state==="read"?{state:"read",rows:old.rows.map(row=>row.capability==="template.T3"?next:row)}:old);
      setDecisionNotice({failed:false,text:`学习与实践模板变更已保存并读回：v${next.definition.version}，${next.installed?(next.enabled?"已启用":"已停用"):"已卸载"}；已有对象保留。`});
    } catch {
      if(!mounted.current)return;
      setDecisionNotice({failed:true,text:"模板变更未确认或状态已变化；不自动重发，请核对当前读回。"});
      await refresh();
    } finally {writePending.current=false;if(mounted.current)setChanging(null);}
  }
  useEffect(() => {
    mounted.current = true;
    void refresh();
    return () => { mounted.current = false; generation.current++; onTemplateDirty(false); };
  }, [onTemplateDirty]);

  function changeTab(next: string) {
    if (templateDirty.current) { setMessage("模板有未保存修改或待确认操作；请先保存或检查结果，再切换目录。"); return; }
    setMessage(""); setTab(next);
  }
  const term = query.trim().toLocaleLowerCase();
  const visible = RESOURCE_CATALOG.entries.filter(entry => (category === "all" || entry.surface_class === category)
    && (!term || JSON.stringify({ names: entry.display_names, key: entry.stable_key, mode: entry.absorption_mode, reason: entry.classification_reason, qualification: entry.qualification.reason, conflicts: entry.original_surface.conflicts }).toLocaleLowerCase().includes(term)));
  const observed = selected?.declared_runtime_route && read.state === "read" ? read.rows.find(row => row.capability === selected.declared_runtime_route) : undefined;
  const originalConflicts = selected?.original_surface.conflicts;
  const conflicts = Array.isArray(originalConflicts) ? originalConflicts : [];

  const directory = <section aria-label="资源目录">
    <p>完整保留 {RESOURCE_CATALOG.entries.length} 项吸收来源及 {String(RESOURCE_CATALOG.crosswalk_metadata.conflict_count)} 条原冲突。类别、吸收方式和登记资格分别陈述；数量不代表集成数。</p>
    <p>目录来自已保存的历史登记；当前能否使用请以下方实际运行状态为准。</p>
    <div className="resources-controls"><AaosField label="查找资源与原冲突" value={query} onChange={event => setQuery(event.currentTarget.value)}/>
      <div><label htmlFor={`${owner}-resource-class`}>来源类别</label><select id={`${owner}-resource-class`} value={category} onChange={event => setCategory(event.currentTarget.value as ResourceClass | "all")}><option value="all">全部来源</option>{Object.entries(SURFACE_CLASS_LABEL).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></div>
    </div>
    <p>筛选结果 {visible.length} 项；不自动安装、升级、授权或启动供体。</p>
    <div className="stitch-resource-browser resources-directory">
      <ul className="resources-list">{visible.map(entry => <li key={entry.stable_key}><button aria-pressed={selected?.stable_key === entry.stable_key} onClick={() => setSelected(entry)}>
        <strong>{entry.display_names[0] || entry.stable_key}</strong><span>{SURFACE_CLASS_LABEL[entry.surface_class]} · {absorptionLabel[entry.absorption_mode] ?? "待确认"}</span>
      </button></li>)}</ul>
      <aside aria-label="资源来源详情" className="stitch-resource-details">{selected ? <>
        <h3>{selected.display_names[0]}</h3>
        <p>来源类别：{SURFACE_CLASS_LABEL[selected.surface_class]}；接入方式：{absorptionLabel[selected.absorption_mode] ?? "待确认"}</p>
        <RawReceiptButton label="资源分类与选择依据详细信息" category="data" payload={{stable_key:selected.stable_key,absorption_mode:selected.absorption_mode,classification_reason:selected.classification_reason,qualification:selected.qualification}}/>
        <p>当前选择：{dispositionLabel[selected.qualification.disposition] ?? "尚未核实"}。具体原因可查看详细信息。</p>
        <section aria-label="启用条件"><h4>启用条件 · {selected.qualification.activation.state === "FROZEN" ? "暂不可启用" : "仅供参考"}</h4>
          <p>启用前需核对范围和条件。</p><RawReceiptButton label="资源启用条件详细信息" category="data" payload={selected.qualification.activation}/>
          <p>这是可复核条件登记，不是执行授权。</p>
        </section>
        <Evidence title="版本证据" evidence={selected.qualification.evidence.version}/>
        <Evidence title="许可证证据" evidence={selected.qualification.evidence.license}/>
        <Evidence title="权限证据" evidence={selected.qualification.evidence.permissions}/>
        <Evidence title="运行证据" evidence={selected.qualification.evidence.runtime}/>
        <Evidence title="实测资格" evidence={selected.qualification.evidence.qualification}/>
        <section aria-label="原始登记冲突"><h4>原始登记冲突 · {conflicts.length}</h4>
          {conflicts.length ? <><p>有 {conflicts.length} 项历史来源冲突，需逐项核对。</p><RawReceiptButton label="资源来源冲突详细信息" category="data" payload={conflicts}/></> : <p>此记录未列原冲突；不等于本次资格通过。</p>}
        </section>
        <section aria-label="资源连接状态"><h4>资源连接状态</h4>
          <p>{selected.declared_runtime_route ? "已登记使用路线；实际连接状态见下方。" : "原登记无单一运行路线；不按相似名称联接。"}</p>
          <p>{read.state !== "read" ? "本轮运行状态未知。" : !selected.declared_runtime_route ? "当前无法直接确认运行连接。" : !observed ? "当前无法确认这项能力是否已连接。" : `当前使用权限${observed.enabled === true ? "允许" : observed.enabled === false ? "已禁用" : "尚未确认"}；运行状态${capabilityHealthLabel(observed.health)}`}</p>
          <p>功能已连接不代表版本、许可或实际结果已核实。</p>
        </section>
        <RawReceiptButton label="完整供体与历史冲突登记" payload={selected}/>
      </> : <p>选择一个真实登记来源，查看原始分类、冲突和激活条件。</p>}</aside>
    </div>
    <section aria-label="当前可用能力"><h3>当前可用能力</h3>
      <button disabled={changing !== null} onClick={() => void refresh()}>刷新本机可用功能</button>
      <p>逐项改变当前工作区的功能开关，不安装新组件，也不修改模型或服务配置。禁用会阻止后续任务，不取消已经运行的任务。</p>
      {changing ? <p role="status">正在更新 {changing === "template.T3" ? "学习与实践模板" : capabilityName(changing)}，等待保存结果…</p> : null}
      {decisionNotice ? <p role={decisionNotice.failed ? "alert" : "status"}>{decisionNotice.text}</p> : null}
      {read.state === "reading" ? <p role="status">正在读取宿主能力…</p> : read.state === "failed" ? <p role="alert">无法确认当前可用功能；资源目录仍可查看。请重试或查看运行诊断。</p> : read.state === "not_read" ? <p>本次尚未检查。</p> : <>
        <p>已读取 {read.rows.length} 项能力状态；不代表 {RESOURCE_CATALOG.entries.length} 项来源均已接入。</p>
        {read.rows.length ? <ul>{read.rows.map(row => <li key={row.capability}>{row.capability==="template.T3"?<T3LifecycleControls row={row} disabled={changing!==null||templateDirty.current} onChange={(state:TemplateState,action:TemplateAction,target?:Definition)=>void changeT3(state,action,target)}/>:<>{capabilityName(row.capability)} · 使用权限 {row.enabled === true ? "允许" : row.enabled === false ? "已禁用" : "尚未确认"} · 连接状态 {capabilityHealthLabel(row.health)} {typeof row.enabled === "boolean" && row.enabled_basis === "the workspace's capability record; an absent record means enabled" ? <button disabled={changing !== null} aria-label={`${row.enabled === false ? "启用" : "禁用"}${capabilityName(row.capability)}`} onClick={() => void changeEnabled(row)}>{row.enabled === false ? "启用" : "禁用"}</button> : <span> · 执行设置未确认，无法变更</span>}</>}</li>)}</ul> : <p>宿主返回空能力列表；不填造运行项。</p>}
      </>}
      <RawReceiptButton label="能力运行详细信息" payload={read}/>
    </section>
    <RawReceiptButton label="资源来源与启用规则详情" payload={{ sources: RESOURCE_CATALOG.sources, original: RESOURCE_CATALOG.crosswalk_metadata, overlay: RESOURCE_CATALOG.qualification_metadata, freeze: RESOURCE_CATALOG.freeze_register }}/>
  </section>;
  return <section aria-label="资源与扩展内容" className="stitch-resources"><div className="stitch-resource-topic"><div><p>资源与已接入模板</p><h2>资源与扩展</h2></div><span>已有登记 · 本地运行状态</span></div>
    <AaosTabs label="资源与模板工作区" value={tab} onValueChange={changeTab} tabs={[
      { id: "templates", label: "学科模板", content: <div className="template-launcher"><TemplateWorkspace onOpen={id => {
        if (callbacks.current.onOpenDocument) callbacks.current.onOpenDocument(id);
        else setMessage("当前宿主未提供文档阅读入口；已保存模板仍保留。");
      }} onOpenCapability={onOpenCapability} onDirtyChange={onTemplateDirty}/></div> },
      { id: "resources", label: "接入来源与运行设置", content: directory },
    ]}/>
    {message ? <p role="status">{message}</p> : null}
  </section>;
}
