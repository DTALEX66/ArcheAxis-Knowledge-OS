import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import type { DocumentDto } from "../api/generated/core-contract";
import { CanonicalLearningSpace } from "../spaces/CanonicalLearningSpace";
import { DISCIPLINES, TEMPLATES } from "./disciplines";
import { backlinks, binding, collection, createTemplate, loadTemplateDocuments, readableBinding, resolveReference, saveBinding, type TemplateBinding } from "./bindings";

export function TemplateLauncher({onOpen,onDirtyChange}:{onOpen:(id:string)=>void;onDirtyChange?:(value:boolean)=>void}) {
  const [open,setOpen]=useState(false);
  const dirty=useRef(false);
  return <details className="template-launcher" onToggle={event=>{
    if(!event.currentTarget.open&&dirty.current&&!window.confirm("模板属性尚未保存，是否放弃这些属性修改？")){event.currentTarget.open=true;return;}
    setOpen(event.currentTarget.open);
  }}><summary>学科模板 · 知识网络 / 研究与项目 / 学习与实践</summary>
    {open?<TemplateWorkspace onOpen={onOpen} onDirtyChange={value=>{dirty.current=value;onDirtyChange?.(value);}}/>:null}
  </details>;
}
export function TemplateWorkspace({onOpen,onDirtyChange}:{onOpen:(id:string)=>void;onDirtyChange?:(value:boolean)=>void}) {
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
  const dirty=useRef(false);const callbacks=useRef(onDirtyChange);callbacks.current=onDirtyChange;
  const pack=DISCIPLINES.find(p=>p.id===(draft?.discipline_id??discipline))!;
  function change(next:TemplateBinding){dirty.current=true;callbacks.current?.(true);setDraft(next);}
  async function refresh(){const data=await loadTemplateDocuments();setUnreadable(false);setDocuments(data.documents);setBounded(data.bounded);return data.documents;}
  useEffect(()=>{let live=true;loadTemplateDocuments().then(data=>{if(live){setUnreadable(false);setDocuments(data.documents);setBounded(data.bounded);}}).catch(()=>{if(live){setUnreadable(true);setMessage("模板对象读取失败，请重试。");}});return()=>{live=false;epoch.current++;callbacks.current?.(false);};},[]);
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
