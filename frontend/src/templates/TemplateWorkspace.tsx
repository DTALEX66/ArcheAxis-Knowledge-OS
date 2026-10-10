import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import type { DocumentDto } from "../api/generated/core-contract";
import { CanonicalLearningSpace } from "../spaces/CanonicalLearningSpace";
import { DISCIPLINES, TEMPLATES } from "./disciplines";
import { resolveTemplateRequirements, templateDefinition, type CapabilityRead, type LiveCapabilityRow } from "./capabilityRequirements";
import { backlinks, binding, collection, executeTemplateWrite, loadTemplateDocuments, prepareTemplateCreate, prepareTemplateSave, readTemplateWrite, readableBinding, resolveReference, type TemplateBinding, type TemplateWriteAttempt } from "./bindings";

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
  const [titleFilter,setTitleFilter]=useState("");
  const [bounded,setBounded]=useState(false);
  const [template,setTemplate]=useState("T1");const [discipline,setDiscipline]=useState("math");
  const [selected,setSelected]=useState<DocumentDto|null>(null);const [draft,setDraft]=useState<TemplateBinding|null>(null);
  const canvasRef=useRef<HTMLDivElement>(null);
  const editorHeadingRef=useRef<HTMLHeadingElement>(null);
  useEffect(()=>{if(selected)editorHeadingRef.current?.focus();},[selected?.document_id]);
  const [canvasHeight,setCanvasHeight]=useState(150);
  useLayoutEffect(()=>{
    const canvas=canvasRef.current;
    if(!canvas)return;
    const measure=()=>setCanvasHeight(Math.max(150,...Array.from(canvas.children).map(node=>{
      const card=node as HTMLElement;return card.offsetTop+card.offsetHeight+20;
    })));
    measure();
    if(typeof ResizeObserver==="undefined")return;
    const observer=new ResizeObserver(measure);
    Array.from(canvas.children).forEach(node=>observer.observe(node));
    return()=>observer.disconnect();
  },[draft]);
  const [target,setTarget]=useState("");const [targetBlock,setTargetBlock]=useState("");const [relation,setRelation]=useState("");
  const [resolved,setResolved]=useState<{document:DocumentDto;text:string}|null>(null);
  const [message,setMessage]=useState("");const [busy,setBusy]=useState(false);const epoch=useRef(0);
  const mounted=useRef(true),running=useRef(false),serial=useRef(0),referenceEpoch=useRef(0);
  const attempt=useRef<{write:TemplateWriteAttempt;serial:number;generation:number}|null>(null);
  const [uncertain,setUncertain]=useState(false);
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
  function publish(){callbacks.current?.(dirty.current||running.current||!!attempt.current);}
  function change(next:TemplateBinding){if(!mounted.current)return;serial.current++;dirty.current=true;publish();setDraft(next);}
  async function refresh(){const generation=epoch.current;try{const data=await loadTemplateDocuments();if(mounted.current&&generation===epoch.current){setUnreadable(false);setDocuments(data.documents);setBounded(data.bounded);}return data.documents;}catch(error){if(mounted.current&&generation===epoch.current)setUnreadable(true);throw error;}}
  useEffect(()=>{mounted.current=true;let live=true;loadTemplateDocuments().then(data=>{if(live){setUnreadable(false);setDocuments(data.documents);setBounded(data.bounded);}}).catch(()=>{if(live){setUnreadable(true);setMessage("模板对象读取失败，请重试。");}});return()=>{live=false;mounted.current=false;epoch.current++;callbacks.current?.(false);};},[]);
  // One read of the live capability handshake per mount or explicit refresh. It writes no message into
  // the workspace's single outcome region — a handshake state is a persisted readout the user reads in
  // place, and promoting it would make one mount announce twice.
  useEffect(()=>{let live=true;setCapabilityPending(true);coreCommand("capabilities_list")
    .then(value=>{if(live)setCapabilityRead(readCapabilityHandshake(value));})
    .catch(()=>{if(live)setCapabilityRead({state:"read_failed"});})
    .finally(()=>{if(live)setCapabilityPending(false);});
    return()=>{live=false;};},[capabilityEpoch]);
  function select(document:DocumentDto){
    if(running.current||attempt.current)return;
    if(dirty.current&&!window.confirm("模板属性尚未保存，是否放弃这些属性修改？"))return;
    epoch.current++;dirty.current=false;callbacks.current?.(false);setSelected(document);setDraft(binding(document));setResolved(null);setMessage("");
  }
  async function action(work:()=>Promise<void>){if(running.current)return;running.current=true;const generation=epoch.current;setBusy(true);publish();try{await work();}catch(error){if(mounted.current&&generation===epoch.current)setMessage(error instanceof Error?error.message:"操作失败；请保留修改后重试。");}finally{running.current=false;if(mounted.current&&generation===epoch.current){setBusy(false);publish();}}}
  async function finishWrite(readOnly=false){const pending=attempt.current;if(!pending)return;setUncertain(true);let document:DocumentDto;
    try{document=await (readOnly?readTemplateWrite(pending.write):executeTemplateWrite(pending.write));}
    catch{throw new Error("模板请求结果尚未确认；草稿和冻结请求保留，请重试同一请求或核对读回。");}
    if(!mounted.current||pending.generation!==epoch.current)return;
    setSelected(document);if(serial.current===pending.serial)setDraft(structuredClone(binding(document)));dirty.current=serial.current!==pending.serial;
    attempt.current=null;setUncertain(false);setDocuments(old=>[document,...old.filter(row=>row.document_id!==document.document_id)]);publish();
    setMessage(dirty.current?"发送时的模板版本已确认；后续属性修改仍未保存。":"模板对象与属性已保存并完整读回；内容仍未评估。");
    // Collection refresh failure must not turn a durable, confirmed write into an unknown write.
    try{await refresh();}catch{if(mounted.current&&pending.generation===epoch.current)setMessage("模板写入已确认；集合刷新失败，当前数量与关系未知。");}
  }
  async function create(){if(dirty.current||attempt.current)throw new Error("请先保存模板属性或核对冻结请求。");const generation=epoch.current,sentSerial=serial.current;
    const write=await prepareTemplateCreate(template,discipline);if(!mounted.current||generation!==epoch.current)return;
    attempt.current={write,serial:sentSerial,generation};await finishWrite();}
  async function save(){if(!selected||!draft||attempt.current)return;const generation=epoch.current,sentSerial=serial.current;
    const write=await prepareTemplateSave(selected,structuredClone(draft));if(!mounted.current||generation!==epoch.current)return;
    attempt.current={write,serial:sentSerial,generation};await finishWrite();}
  function openDocument(id:string){if(running.current||attempt.current)return;if(dirty.current&&!window.confirm("模板属性尚未保存，是否放弃这些属性修改？"))return;onOpen(id);}
  async function addReference(){
    if(!draft)return;const generation=epoch.current;const document=await coreCommand<DocumentDto>("document_get",{document_id:target});
    const reference={document_id:document.document_id,version:document.version,block_id:targetBlock.trim()||null,relation:relation.trim()||pack.relations[0],x:20,y:20+Math.max(0,...draft.references.map((r,i)=>r.y+((canvasRef.current?.children[i] as HTMLElement|undefined)?.offsetHeight||90)))};
    await resolveReference(reference);
    if(!mounted.current||generation!==epoch.current)return;
    if(draft.references.some(r=>r.document_id===reference.document_id&&r.version===reference.version&&r.block_id===reference.block_id&&r.relation===reference.relation))throw new Error("此引用关系已存在。");
    change({...draft,references:[...draft.references,reference]});
  }
  function moveReference(index:number){
    if(!draft)return;
    const canvas=canvasRef.current;const ref=draft.references[index];
    const card=canvas?.children[index] as HTMLElement|undefined;
    const width=card?.offsetWidth||280;const height=card?.offsetHeight||90;
    const x=Math.max(0,Math.min(ref.x+25,(canvas?.clientWidth||width+32)-width-12));
    let y=ref.y+15;
    const peers=draft.references.map((other,i)=>({other,i})).filter(row=>row.i!==index).sort((a,b)=>a.other.y-b.other.y);
    for(const {other,i} of peers){
      const peer=canvas?.children[i] as HTMLElement|undefined;
      if(x<other.x+(peer?.offsetWidth||280)&&x+width>other.x
        &&y<other.y+(peer?.offsetHeight||90)&&y+height>other.y){
        y=other.y+(peer?.offsetHeight||90)+20;
      }
    }
    change({...draft,references:draft.references.map((r,i)=>i===index?{...r,x,y}:r)});
  }
  const currentCollection=collection(documents,pack.id);
  const savedTemplates=documents.filter(d=>readableBinding(d));
  const incoming=selected?backlinks(documents,selected.document_id):[];
  return <section aria-label="学科模板工作区">
    <label>学科<select value={discipline} disabled={busy||uncertain} onChange={event=>setDiscipline(event.target.value)}>{DISCIPLINES.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
    <label>模板<select value={template} disabled={busy||uncertain} onChange={event=>setTemplate(event.target.value)}>{TEMPLATES.map(t=><option key={t.id} value={t.id}>{t.name}</option>)}</select></label>
    <button disabled={busy||uncertain||dirty.current} onClick={()=>void action(create)}>创建学科对象</button>
    <button disabled={busy||uncertain||dirty.current} onClick={()=>void action(async()=>{await refresh();})}>重新读取模板集合</button>
    {uncertain?<><button disabled={busy} onClick={()=>void action(()=>finishWrite())}>重试冻结模板请求</button><button disabled={busy} onClick={()=>void action(()=>finishWrite(true))}>核对冻结模板请求</button><p>当前请求尚未确认；不会生成新请求或自动清除后续修改。</p></>:null}
    <p>{unreadable?"集合读取未完成，下列计数不代表真实数量。":`集合从已保存文档重建；本次完整读回 ${documents.length} 个文档对象，其中 ${savedTemplates.length} 个带可解析模板属性；逐条绑定读取时的文档版本${bounded?"，结果可能不完整":""}。`}</p>
    <TemplateCapabilityRequirements templateId={draft?.template_id??template} read={capabilityRead} pending={capabilityPending} busy={busy} onRefresh={()=>setCapabilityEpoch(value=>value+1)} onOpenCapability={onOpenCapability} />
    <label>查找已保存模板<input type="search" value={titleFilter} maxLength={256} onChange={event=>setTitleFilter(event.target.value)}/></label>
    <nav aria-label="已保存模板" tabIndex={0}>{savedTemplates.filter(d=>d.title.toLocaleLowerCase().includes(titleFilter.trim().toLocaleLowerCase())).map(d=><button key={d.document_id} disabled={busy||uncertain} onClick={()=>select(d)}>{d.title} · v{d.version}</button>)}
      {!unreadable&&savedTemplates.length>0&&!savedTemplates.some(d=>d.title.toLocaleLowerCase().includes(titleFilter.trim().toLocaleLowerCase()))?<p>没有匹配的模板标题；清除筛选可查看全部模板。</p>:null}
      {unreadable?<p className="template-list-state">模板集合未能完整读回；此前对象仅供保留草稿，当前集合是否为空未知。</p>:savedTemplates.length?null:<p className="template-list-state">{documents.length?`已读回的 ${documents.length} 个文档对象中，没有带可解析模板属性的对象。`:"尚无已保存的模板对象；选择学科与模板后创建第一个。"}</p>}
    </nav>
    {documents.length>savedTemplates.length?<p>无效模板属性不参与集合汇总；原文仍可在资料库打开。</p>:null}
    {selected&&draft?<>
      <h3 ref={editorHeadingRef} tabIndex={-1}>{selected.title}</h3><button disabled={busy||uncertain} onClick={()=>openDocument(selected.document_id)}>打开真实文档与正文</button>
      <p>{pack.activity}；评价：{pack.evaluation}。普通笔记与假设允许保存，复习间隔不证明实操掌握。</p>
      {["status",...pack.fields].map(field=><label key={field}>{field}<input disabled={busy} value={draft.fields[field]??""} onChange={event=>change({...draft,fields:{...draft.fields,[field]:event.target.value}})}/></label>)}
      <label>关联学习项<input disabled={busy} value={draft.learning_item_key??""} onChange={event=>change({...draft,learning_item_key:event.target.value||null})}/></label>
      <button disabled={busy||uncertain||!dirty.current} onClick={()=>void action(save)}>保存模板属性与关系</button>
      {unreadable?<p>集合刷新未完成；保留此前文档，当前数量与关系未知。</p>:<p>当前学科集合 {currentCollection.members.length} 个对象，{currentCollection.relations} 条关系；{Object.entries(currentCollection.statuses).map(([state,count])=>`${state}：${count}`).join("；")}</p>}
      <label>关系目标<select value={target} disabled={busy} onChange={event=>setTarget(event.target.value)}><option value="">选择已有文档</option>{documents.map(d=><option key={d.document_id} value={d.document_id}>{d.title}</option>)}</select></label>
      <label>目标块 ID（可空）<input disabled={busy} value={targetBlock} onChange={event=>setTargetBlock(event.target.value)}/></label>
      <label>关系类型<input disabled={busy} value={relation} placeholder={pack.relations[0]} onChange={event=>setRelation(event.target.value)}/></label>
      <button disabled={busy||!target||draft.references.length>=100} onClick={()=>void action(addReference)}>加入版本绑定引用</button>
      <div aria-label="局部图谱">{draft.references.map((ref,index)=><button key={index} disabled={busy} onClick={()=>void action(async()=>{const generation=epoch.current,request=++referenceEpoch.current;const result=await resolveReference(ref);if(mounted.current&&generation===epoch.current&&request===referenceEpoch.current)setResolved(result);})}>{ref.relation} → {documents.find(d=>d.document_id===ref.document_id)?.title??ref.document_id} · v{ref.version}{ref.block_id?` · ${ref.block_id}`:""}</button>)}</div>
      <div ref={canvasRef} aria-label="引用式画布" style={{position:"relative",minHeight:canvasHeight,overflow:"auto"}}>{draft.references.map((ref,index)=><div key={index} style={{position:"absolute",left:ref.x,top:ref.y,border:"1px solid var(--ax-border-strong)",padding:8,background:"var(--ax-panel)",width:280,maxWidth:`calc(100% - ${ref.x+12}px)`,boxSizing:"border-box",display:"grid",gridTemplateColumns:"1fr 1fr",gap:6}}><button style={{gridColumn:"1 / -1",minWidth:0,whiteSpace:"normal",overflowWrap:"anywhere"}} disabled={busy} onClick={()=>void action(async()=>{const generation=epoch.current,request=++referenceEpoch.current;const result=await resolveReference(ref);if(mounted.current&&generation===epoch.current&&request===referenceEpoch.current)setResolved(result);})}>{documents.find(d=>d.document_id===ref.document_id)?.title??ref.document_id} · 引用 v{ref.version}</button><button aria-label={`移动引用卡片 ${index+1}`} disabled={busy} onClick={()=>moveReference(index)}>移动</button><button aria-label={`删除引用 ${index+1}`} disabled={busy} onClick={()=>change({...draft,references:draft.references.filter((_,i)=>i!==index)})}>移除</button></div>)}</div>
      {resolved?<aside aria-label="引用原文"><h4>{resolved.document.title} · v{resolved.document.version}</h4><pre>{resolved.text}</pre><button disabled={busy||uncertain} onClick={()=>openDocument(resolved.document.document_id)}>打开引用对象当前正文</button><p>上方是绑定的历史版本；打开正文显示当前版本。</p></aside>:null}
      <section aria-label="反向引用"><h4>反向引用及上下文</h4>{unreadable?<p>集合刷新未完成，当前反向引用未知。</p>:incoming.length?incoming.map((item,index)=><p key={index}><button disabled={busy||uncertain} onClick={()=>openDocument(item.document.document_id)}>{item.document.title}</button> · {item.reference.relation} · 指向 v{item.reference.version}：{item.context}</p>):<p>当前读取范围没有已保存的反向引用。</p>}</section>
      {draft.template_id==="T3"&&draft.learning_item_key&&!dirty.current?<CanonicalLearningSpace initialItemKey={draft.learning_item_key}/>:draft.template_id==="T3"?<p>绑定已有学习项并保存后，可读取真实作答、反馈与复习状态。课程仅沿用 general 合同；学科标签不会启用专属课程引擎。</p>:null}
    </>:null}
    <p role="status">{message}</p>
  </section>;
}
