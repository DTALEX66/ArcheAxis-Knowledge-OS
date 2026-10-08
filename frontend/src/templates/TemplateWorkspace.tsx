import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import type { DocumentDto } from "../api/generated/core-contract";
import { CanonicalLearningSpace } from "../spaces/CanonicalLearningSpace";
import { DISCIPLINES, TEMPLATES } from "./disciplines";
import { resolveTemplateRequirements, templateDefinition, type CapabilityRead, type LiveCapabilityRow } from "./capabilityRequirements";
import { backlinks, binding, collection, createTemplate, loadTemplateDocuments, readableBinding, resolveReference, saveBinding, type TemplateBinding } from "./bindings";

/** One live `capabilities_list` readback, validated the same way the capability directory validates
 *  its own read: a row without a string identity is not a partial success, it is a failed read. */
function readCapabilityHandshake(value: unknown): CapabilityRead {
  const rows = (value as { capabilities?: unknown }).capabilities;
  if (!Array.isArray(rows) || rows.some((row) => typeof (row as LiveCapabilityRow | null)?.capability !== "string")) {
    return { state: "read_failed" };
  }
  return { state: "read", rows: new Map(rows.map((row) => [String((row as LiveCapabilityRow).capability), row as LiveCapabilityRow])) };
}

/** What the template declares it needs, and what the platform can actually answer today.
 *  The reading surface carries no raw payload and no live role: the workspace owns one outcome
 *  region below, and this table describes persisted declarations rather than a fresh event. */
function TemplateCapabilityRequirements({ templateId, read, pending, busy, onRefresh, onOpenCapability }: {
  templateId: string;
  read: CapabilityRead;
  pending: boolean;
  busy: boolean;
  onRefresh: () => void;
  onOpenCapability?: (id: string) => void;
}) {
  const template = templateDefinition(templateId);
  const rows = resolveTemplateRequirements(templateId, read);
  const bound = rows.filter((row) => row.navigable).length;
  return <section aria-label="模板能力需求">
    <h4>{template?.name ?? templateId} · 所需能力</h4>
    <p className="template-list-state">{pending ? "正在读取 Core 能力握手…" : read.state === "read_failed" ? "本轮能力握手读取失败，运行状态显示未知。" : read.state === "not_read" ? "本轮未读取运行状态（NOT_RUN）。" : `本轮已读回 ${read.rows.size} 条 Core 握手记录。`} 本表只陈述联接与状态：不复制插件代码、依赖安装或连接配置，未联接到稳定 ID 的声明不显示为可跳转。</p>
    <div className="capability-actions"><button disabled={busy} onClick={onRefresh}>重新读取运行状态</button><span>{rows.length} 项声明需求；其中 {bound} 项联接到稳定 ID。</span></div>
    <table className="data-table">
      <caption>模板 {templateId} 的能力需求、当前提供方、可用性与缺失原因</caption>
      <thead><tr><th>需求与提供方</th><th>状态</th><th>缺失原因</th><th>插件详情</th></tr></thead>
      <tbody>{rows.map((row) => <tr key={row.declared}>
        <td><b>{row.declared}</b><small className="table-sub">{row.capability_id ?? "无稳定 ID"}{row.capability_name ? ` · ${row.capability_name}` : ""}</small><small className="table-sub">{row.join_label} · {row.provider}</small></td>
        <td>{row.status_label}<small className="table-sub">{row.availability_label}{row.health ? ` · ${row.health}` : ""}</small></td>
        <td>{row.missing_reason}</td>
        <td>{row.navigable && onOpenCapability
          ? <button disabled={busy} aria-label={`打开能力详情 ${row.capability_id} · ${row.declared}`} onClick={() => onOpenCapability(row.capability_id as string)}>能力详情</button>
          : <span className="muted">{row.navigable ? "当前视图未提供能力入口" : "无 ID，不可跳转"}</span>}</td>
      </tr>)}</tbody>
    </table>
  </section>;
}

export function TemplateLauncher({onOpen,onDirtyChange,onOpenCapability}:{onOpen:(id:string)=>void;onDirtyChange?:(value:boolean)=>void;onOpenCapability?:(id:string)=>void}) {
  const [open,setOpen]=useState(false);
  const dirty=useRef(false);
  return <details className="template-launcher" onToggle={event=>{
    if(!event.currentTarget.open&&dirty.current&&!window.confirm("模板属性尚未保存，是否放弃这些属性修改？")){event.currentTarget.open=true;return;}
    setOpen(event.currentTarget.open);
  }}><summary>学科模板 · 知识网络 / 研究与项目 / 学习与实践</summary>
    {open?<TemplateWorkspace onOpen={onOpen} onOpenCapability={onOpenCapability} onDirtyChange={value=>{dirty.current=value;onDirtyChange?.(value);}}/>:null}
  </details>;
}
export function TemplateWorkspace({onOpen,onDirtyChange,onOpenCapability}:{onOpen:(id:string)=>void;onDirtyChange?:(value:boolean)=>void;onOpenCapability?:(id:string)=>void}) {
  const [documents,setDocuments]=useState<DocumentDto[]>([]);
  const [bounded,setBounded]=useState(false);
  const [template,setTemplate]=useState("T1");const [discipline,setDiscipline]=useState("math");
  const [selected,setSelected]=useState<DocumentDto|null>(null);const [draft,setDraft]=useState<TemplateBinding|null>(null);
  const [target,setTarget]=useState("");const [targetBlock,setTargetBlock]=useState("");const [relation,setRelation]=useState("");
  const [resolved,setResolved]=useState<{document:DocumentDto;text:string}|null>(null);
  const [message,setMessage]=useState("");const [busy,setBusy]=useState(false);const epoch=useRef(0);
  // "Core answered nothing" and "Core answered but no object carries template metadata" are different
  // facts; collapsing them into one empty list would state something the read never established.
  const [unreadable,setUnreadable]=useState(false);
  // The requirement table separates "the map declares an implementation" from "this host reported a
  // handshake". That second half only exists if capabilities_list was actually read, so its state is
  // tracked apart from the document read and never defaults to a friendly value.
  const [capabilityRead,setCapabilityRead]=useState<CapabilityRead>({state:"not_read"});
  const [capabilityPending,setCapabilityPending]=useState(true);
  const [capabilityEpoch,setCapabilityEpoch]=useState(0);
  const dirty=useRef(false);const callbacks=useRef(onDirtyChange);callbacks.current=onDirtyChange;
  const pack=DISCIPLINES.find(p=>p.id===(draft?.discipline_id??discipline))!;
  function change(next:TemplateBinding){dirty.current=true;callbacks.current?.(true);setDraft(next);}
  async function refresh(){const data=await loadTemplateDocuments();setUnreadable(false);setDocuments(data.documents);setBounded(data.bounded);return data.documents;}
  useEffect(()=>{let live=true;loadTemplateDocuments().then(data=>{if(live){setUnreadable(false);setDocuments(data.documents);setBounded(data.bounded);}}).catch(()=>{if(live){setUnreadable(true);setMessage("模板对象读取失败，请重试。");}});return()=>{live=false;epoch.current++;callbacks.current?.(false);};},[]);
  // One read of the live capability handshake per mount or explicit refresh. It writes no message into
  // the workspace's single outcome region — a handshake state is a persisted readout the user reads in
  // place, and promoting it would make one mount announce twice.
  useEffect(()=>{let live=true;setCapabilityPending(true);coreCommand("capabilities_list")
    .then(value=>{if(live)setCapabilityRead(readCapabilityHandshake(value));})
    .catch(()=>{if(live)setCapabilityRead({state:"read_failed"});})
    .finally(()=>{if(live)setCapabilityPending(false);});
    return()=>{live=false;};},[capabilityEpoch]);
  function select(document:DocumentDto){
    if(dirty.current&&!window.confirm("模板属性尚未保存，是否放弃这些属性修改？"))return;
    epoch.current++;dirty.current=false;callbacks.current?.(false);setSelected(document);setDraft(binding(document));setResolved(null);setMessage("");
  }
  async function action(work:()=>Promise<void>){if(busy)return;setBusy(true);try{await work();}catch(error){setMessage(error instanceof Error?error.message:"操作失败；请保留修改后重试。");}finally{setBusy(false);}}
  async function create(){if(dirty.current)throw new Error("请先保存模板属性。");const document=await createTemplate(template,discipline);await refresh();select(document);setMessage("已由 Core 保存模板对象；内容仍未评估。");}
  async function save(){if(!selected||!draft)return;const document=await saveBinding(selected,draft);setSelected(document);setDraft(binding(document));dirty.current=false;callbacks.current?.(false);await refresh();setMessage("属性、关系与画布引用已保存；重新进入可读回。");}
  async function addReference(){
    if(!draft)return;const document=await coreCommand<DocumentDto>("document_get",{document_id:target});
    const reference={document_id:document.document_id,version:document.version,block_id:targetBlock.trim()||null,relation:relation.trim()||pack.relations[0],x:20+draft.references.length*20,y:20+draft.references.length*35};
    await resolveReference(reference);
    if(draft.references.some(r=>r.document_id===reference.document_id&&r.version===reference.version&&r.block_id===reference.block_id&&r.relation===reference.relation))throw new Error("此引用关系已存在。");
    change({...draft,references:[...draft.references,reference]});
  }
  const currentCollection=collection(documents,pack.id);
  const savedTemplates=documents.filter(d=>readableBinding(d));
  const incoming=selected?backlinks(documents,selected.document_id):[];
  return <section aria-label="学科模板工作区">
    <label>学科<select value={discipline} disabled={busy} onChange={event=>setDiscipline(event.target.value)}>{DISCIPLINES.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
    <label>模板<select value={template} disabled={busy} onChange={event=>setTemplate(event.target.value)}>{TEMPLATES.map(t=><option key={t.id} value={t.id}>{t.name}</option>)}</select></label>
    <button disabled={busy} onClick={()=>void action(create)}>创建学科对象</button>
    <button disabled={busy||dirty.current} onClick={()=>void action(async()=>{await refresh();})}>重新读取模板集合</button>
    <p>{unreadable?"集合读取未完成，下列计数不代表真实数量。":`集合从已保存文档重建；本次读回 ${documents.length} 个文档对象，其中 ${savedTemplates.length} 个带可解析模板属性；当前读取最多 100 个对象${bounded?"，结果可能不完整":""}。`}</p>
    <TemplateCapabilityRequirements templateId={draft?.template_id??template} read={capabilityRead} pending={capabilityPending} busy={busy} onRefresh={()=>setCapabilityEpoch(value=>value+1)} onOpenCapability={onOpenCapability} />
    <nav aria-label="已保存模板">{savedTemplates.map(d=><button key={d.document_id} disabled={busy} onClick={()=>select(d)}>{d.title} · v{d.version}</button>)}
      {unreadable?<p className="template-list-state">模板集合未能从本地核心读回；列表为空只表示读取失败，不表示没有模板对象。</p>:savedTemplates.length?null:<p className="template-list-state">{documents.length?`已读回的 ${documents.length} 个文档对象中，没有带可解析模板属性的对象。`:"尚无已保存的模板对象；选择学科与模板后创建第一个。"}</p>}
    </nav>
    {documents.length>savedTemplates.length?<p>无效模板属性不参与集合汇总；原文仍可在资料库打开。</p>:null}
    {selected&&draft?<>
      <h3>{selected.title}</h3><button onClick={()=>onOpen(selected.document_id)}>打开真实文档与正文</button>
      <p>{pack.activity}；评价：{pack.evaluation}。普通笔记与假设允许保存，复习间隔不证明实操掌握。</p>
      {["status",...pack.fields].map(field=><label key={field}>{field}<input disabled={busy} value={draft.fields[field]??""} onChange={event=>change({...draft,fields:{...draft.fields,[field]:event.target.value}})}/></label>)}
      <label>关联学习项<input disabled={busy} value={draft.learning_item_key??""} onChange={event=>change({...draft,learning_item_key:event.target.value||null})}/></label>
      <button disabled={busy||!dirty.current} onClick={()=>void action(save)}>保存模板属性与关系</button>
      <p>当前学科集合 {currentCollection.members.length} 个对象，{currentCollection.relations} 条关系；{Object.entries(currentCollection.statuses).map(([state,count])=>`${state}：${count}`).join("；")}</p>
      <label>关系目标<select value={target} disabled={busy} onChange={event=>setTarget(event.target.value)}><option value="">选择已有文档</option>{documents.map(d=><option key={d.document_id} value={d.document_id}>{d.title}</option>)}</select></label>
      <label>目标块 ID（可空）<input disabled={busy} value={targetBlock} onChange={event=>setTargetBlock(event.target.value)}/></label>
      <label>关系类型<input disabled={busy} value={relation} placeholder={pack.relations[0]} onChange={event=>setRelation(event.target.value)}/></label>
      <button disabled={busy||!target||draft.references.length>=100} onClick={()=>void action(addReference)}>加入版本绑定引用</button>
      <div aria-label="局部图谱">{draft.references.map((ref,index)=><button key={index} disabled={busy} onClick={()=>void action(async()=>{const generation=++epoch.current;const result=await resolveReference(ref);if(generation===epoch.current)setResolved(result);})}>{ref.relation} → {documents.find(d=>d.document_id===ref.document_id)?.title??ref.document_id} · v{ref.version}{ref.block_id?` · ${ref.block_id}`:""}</button>)}</div>
      <div aria-label="引用式画布" style={{position:"relative",minHeight:Math.max(150,...draft.references.map(r=>r.y+90)),overflow:"auto"}}>{draft.references.map((ref,index)=><div key={index} style={{position:"absolute",left:ref.x,top:ref.y,border:"1px solid currentColor",padding:8,background:"var(--surface,Canvas)"}}><button disabled={busy} onClick={()=>void action(async()=>{const generation=++epoch.current;const result=await resolveReference(ref);if(generation===epoch.current)setResolved(result);})}>{documents.find(d=>d.document_id===ref.document_id)?.title??ref.document_id} · 引用 v{ref.version}</button><button aria-label={`移动引用卡片 ${index+1}`} disabled={busy} onClick={()=>change({...draft,references:draft.references.map((r,i)=>i===index?{...r,x:r.x+25,y:r.y+15}:r)})}>移动</button><button aria-label={`删除引用 ${index+1}`} disabled={busy} onClick={()=>change({...draft,references:draft.references.filter((_,i)=>i!==index)})}>移除</button></div>)}</div>
      {resolved?<aside aria-label="引用原文"><h4>{resolved.document.title} · v{resolved.document.version}</h4><pre>{resolved.text}</pre><button onClick={()=>onOpen(resolved.document.document_id)}>打开引用对象当前正文</button><p>上方是绑定的历史版本；打开正文显示当前版本。</p></aside>:null}
      <section aria-label="反向引用"><h4>反向引用及上下文</h4>{incoming.length?incoming.map((item,index)=><p key={index}><button onClick={()=>onOpen(item.document.document_id)}>{item.document.title}</button> · {item.reference.relation} · 指向 v{item.reference.version}：{item.context}</p>):<p>当前读取范围没有已保存的反向引用。</p>}</section>
      {draft.template_id==="T3"&&draft.learning_item_key&&!dirty.current?<CanonicalLearningSpace initialItemKey={draft.learning_item_key}/>:draft.template_id==="T3"?<p>绑定已有学习项并保存后，可读取真实作答、反馈与复习状态。课程仅沿用 general 合同；学科标签不会启用专属课程引擎。</p>:null}
    </>:null}
    <p role="status">{message}</p>
  </section>;
}
