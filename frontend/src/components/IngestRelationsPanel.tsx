import {useEffect,useRef,useState} from "react";
import {useDraftOwner} from "../workspace/draftProtection";
import {useDraftRecoverySource} from "../workspace/draftRecovery";
import {coreCommand} from "../api/core";
import type {DocumentDto,DocumentSummaryDto,IngestBatchDto,IngestRelationsDto,IngestRelationsLinkDto,IngestRelationsApplyInput,RelationProjectionDto} from "../api/generated/core-contract";
import {freezeRelations,markdownMember,readRelationBatch,selectedFragments,verifyRelationReceipt,type FolderMemberSelection,type RelationAttempt} from "../presentation/ingestRelations";
import {failureMessage} from "../presentation/labels";
import {RawReceiptButton} from "./DiagnosticConsole";

const linkReasons:Record<NonNullable<IngestRelationsLinkDto["reason"]>,string>={
 external_reference_not_followed:"外部链接未自动访问；请核对地址，按需手动打开。",
 unsafe_or_unsupported_target:"目标地址不安全或当前不支持，未建立关联；请检查目标，不要绕过保护。",
 ambiguous_target:"有多个可能目标，未自动选择；请核对并明确选择目标。",
 missing_target:"未找到目标；请先导入缺少的资料，再核对关联。",
 fragment_resolution_not_supported:"标题或段落位置尚不能自动确定；请先选择对应的已保存文档，再手动核对标题或段落位置。",
 target_binding_required:"尚未选择对应目标；请在链接目标中明确选择。",
 note_document_binding_required:"目标笔记尚未关联到已保存文档；请先创建或选择对应文档。",
 embed_rendering_not_supported:"当前不支持在正文中直接显示；附件原件与引用信息保留，可单独打开查看。",
 embed_presentation_requested:"已记录在正文中显示的请求；请打开对应固定版本核对实际显示效果。",
};
function linkStatusLabel(status:IngestRelationsLinkDto["status"]){return status==="resolved_reference"?"已建立固定引用":status==="unresolved"?"尚未关联":"关联结果待确认";}

export function IngestRelationsPanel({selection,document,documents,dirty,canWrite,write,onApplied,onPendingChange,onOpenDocument,onMore,hasMore}:{
 selection:FolderMemberSelection;document:DocumentDto|null;documents:DocumentSummaryDto[];dirty:boolean;canWrite:boolean;
 write:<T>(action:()=>Promise<T>)=>Promise<T>;onApplied:(value:DocumentDto)=>void;onPendingChange:(pending:boolean)=>void;
 onOpenDocument:(id:string)=>void;onMore:()=>void;hasMore:boolean;
}) {
 const [batch,setBatch]=useState<IngestBatchDto|null>(null),[choices,setChoices]=useState<Record<number,string>>({});
 const [targetDocs,setTargetDocs]=useState<Record<number,DocumentDto>>({}),[fragmentChoices,setFragmentChoices]=useState<Record<number,string>>({});
 const [attempt,setAttempt]=useState<RelationAttempt|null>(null),[receipt,setReceipt]=useState<IngestRelationsDto|null>(null),[observed,setObserved]=useState<DocumentDto|null>(null),[graph,setGraph]=useState<RelationProjectionDto|null>(null);
 const [busy,setBusy]=useState(false),[message,setMessage]=useState("请读取本批次，再显式选择已保存文档和链接目标。"),[page,setPage]=useState(0);
  const [failure,setFailure]=useState<string|null>(null);
 const locked=useRef(false),alive=useRef(true),generation=useRef(0);const current=useRef({document,dirty,canWrite});current.current={document,dirty,canWrite};
 const recoveryOwner=useDraftOwner("ingest-relations-input");
 useDraftRecoverySource(recoveryOwner,"原件链接未确认输入",()=>attempt||Object.values(choices).some(Boolean)||Object.values(fragmentChoices).some(Boolean)?[{label:"原件链接未确认输入",text:JSON.stringify({selection,choices,fragmentChoices,...(attempt?{pending_request:attempt}:{})},null,2)}]:[]);
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;++generation.current;};},[]);
 const key=JSON.stringify(selection);
  useEffect(()=>{++generation.current;setBatch(null);setChoices({});setReceipt(null);setObserved(null);setGraph(null);setFailure(null);setPage(0);setTargetDocs({});setFragmentChoices({});},[key]);
  async function action(work:(epoch:number)=>Promise<void>){if(locked.current)return;locked.current=true;setBusy(true);setFailure(null);const epoch=generation.current;try{await work(epoch);}catch(error){if(alive.current&&epoch===generation.current){setFailure(error instanceof Error?error.message:String(error));setMessage(failureMessage(error));}}finally{locked.current=false;if(alive.current)setBusy(false);}}
 const valid=(epoch:number)=>alive.current&&epoch===generation.current;
  async function load(){await action(async e=>{const value=await readRelationBatch(coreCommand,selection);if(valid(e)){setBatch(value);setMessage("已读取完整导入批次。这里只整理原件中的链接，不代表当前编辑正文或内容已经审核。");}});}
 async function projection(d:DocumentDto,e:number){const p=await coreCommand<RelationProjectionDto>("document_graph",{document_id:d.document_id,version:d.version});if(p.center.document_id!==d.document_id||p.center.version!==d.version||p.center.content_sha256!==d.content_sha256)throw new Error("关系投影身份不符");if(valid(e))setGraph(p);}
 async function apply(){await action(async e=>{
  if(attempt||!batch||!current.current.document||!current.current.canWrite||current.current.dirty)throw new Error("请先处理草稿、只读状态或未确认请求");
  const base=current.current.document;
  await write(async()=>{
   const fresh=await readRelationBatch(coreCommand,selection);const targets:IngestRelationsApplyInput["targets"]=[];const snapshots:Record<number,DocumentDto>={};
   for(const member of fresh.members){const choice=choices[member.ordinal];if(!choice)continue;
    if(!member.source_id||!member.source_revision)throw new Error("目标原件尚未导入");
    const target:IngestRelationsApplyInput["targets"][number]={ordinal:member.ordinal,source_id:member.source_id,source_revision:member.source_revision};
    if(markdownMember(member)){
     const summary=documents.find(d=>d.document_id===choice&&d.source_id===member.source_id&&d.source_revision===member.source_revision);
     if(!summary)throw new Error("目标固定文档未明确选择");
     const pinned=await coreCommand<DocumentDto>("document_version",{document_id:summary.document_id,version:summary.version});
     if(pinned.document_id!==summary.document_id||pinned.version!==summary.version||pinned.content_sha256!==summary.content_sha256||pinned.source_id!==member.source_id||pinned.source_revision!==member.source_revision)throw new Error("目标文档版本身份不符");
     target.document={document_id:pinned.document_id,version:pinned.version,content_sha256:pinned.content_sha256};
     snapshots[member.ordinal]=pinned;
    }else if(choice!=="source")throw new Error("附件选择无效");
    targets.push(target);
   }
   if(!valid(e)||current.current.document?.document_id!==base.document_id||current.current.document.version!==base.version||current.current.document.content_sha256!==base.content_sha256||current.current.dirty||!current.current.canWrite)throw new Error("准备期间文档或草稿改变；未发送");
   const fragments=selectedFragments(receipt,fragmentChoices,targets,targetDocs);
   const frozen=freezeRelations(selection,fresh,base,targets,current.current.dirty,fragments);setAttempt(frozen);onPendingChange(true);
   // Exactly one write. Errors and lost acknowledgements never rebase or resend.
   const result=await coreCommand<IngestRelationsDto>("ingest_member_relations_apply",{batch_id:selection.batch_id,ordinal:selection.ordinal,body:frozen.body});
   const readback=await coreCommand<DocumentDto>("document_version",{document_id:frozen.body.document_id,version:result.document.version});
   await readRelationBatch(coreCommand,frozen.selection);
   const saved=verifyRelationReceipt(frozen,result,readback);
   if(!valid(e))return;
   setReceipt(result);setTargetDocs(snapshots);setObserved(saved);setAttempt(null);onPendingChange(false);onApplied(saved);
    setMessage(`已保存并核对第 ${saved.version} 版；新增 ${result.added_relations} 条关系，更新 ${result.updated_relations ?? 0} 条正文引用显示设置。未关联项与原始文本仍保留；请逐项核对下方结果。`);
   await projection(saved,e);
  });
 });}
 async function readUnknown(){await action(async e=>{
  if(!attempt)return;
  await readRelationBatch(coreCommand,attempt.selection);
  const d=await coreCommand<DocumentDto>("document_get",{document_id:attempt.body.document_id});
  if(d.document_id!==attempt.body.document_id||d.source_id!==attempt.body.source_id||d.source_revision!==attempt.body.source_revision)throw new Error("读回对象身份不符");
   if(valid(e)){setObserved(d);setMessage(`已只读取得当前保存的第 ${d.version} 版；缺少本次操作的确认记录，处理结果仍待确认。本次请求保留，没有重新发送，也没有改用其他版本重试。`);await projection(d,e);}
 });}
 const candidates=documents.filter(d=>d.source_id===selection.source_id&&d.source_revision===selection.source_revision);
 return <section aria-label="文件夹原件链接接入"><h4>接入原件中的链接与附件</h4><p>仅本批次身份映射。代码、外链、歧义、缺失或未支持语法不会猜测关联；附件嵌入仅保存引用。普通正文与手工关系保留。</p>
  <button disabled={busy||!!attempt} onClick={()=>void load()}>读取完整批次映射</button>
  <p>先显式打开此成员对应的已保存文档：</p>{candidates.map(d=><button key={d.document_id} disabled={busy||dirty||!!attempt} onClick={()=>onOpenDocument(d.document_id)}>{d.title} · v{d.version} · {d.document_id}</button>)}
  {!candidates.length?<p>已加载文档中没有匹配项；请先从原件创建已保存文档，或继续读取文档页。不会按同名建立关联。</p>:null}
  {hasMore?<button disabled={busy||!!attempt} onClick={onMore}>读取更多已保存文档</button>:null}
  {batch?<><p>批次 {batch.folder_label}；当前文档 {document?.document_id??"未选择"} v{document?.version??"—"}。目标最多显式选择 200 项。</p>
   {batch.members.slice(page*200,(page+1)*200).map(m=><label key={m.ordinal}>{m.relative_path}<select aria-label={`链接目标 ${m.relative_path}`} disabled={busy||!!attempt||!m.source_id} value={choices[m.ordinal]??""} onChange={e=>{setChoices(old=>({...old,[m.ordinal]:e.target.value}));setFragmentChoices({});setTargetDocs({});setReceipt(null);}}><option value="">不映射（保留未解析）</option>{markdownMember(m)?documents.filter(d=>d.source_id===m.source_id&&d.source_revision===m.source_revision).map(d=><option key={d.document_id} value={d.document_id}>{d.title} · v{d.version} · {d.document_id}</option>):<option value="source">固定原件 {m.source_revision}</option>}</select></label>)}
   <button disabled={busy||page===0} onClick={()=>setPage(p=>p-1)}>上一页成员</button><button disabled={busy||(page+1)*200>=batch.members.length} onClick={()=>setPage(p=>p+1)}>下一页成员</button>
   <button disabled={busy||!!attempt||dirty||!canWrite||!document||document.source_id!==selection.source_id||document.source_revision!==selection.source_revision} onClick={()=>void apply()}>确认映射并保存原件关系</button></>:null}
   {attempt?<><p role="alert">处理结果待确认：本次处理记录保留，请先只读核对；不会自动重发，也不会重复建立关系。</p><RawReceiptButton label="未确认关系请求" payload={attempt}/><button disabled={busy} onClick={()=>void readUnknown()}>只读核对原关系请求</button></>:null}
   {receipt?<><RawReceiptButton label="原件链接接入回执" payload={receipt}/><ul aria-label="链接处理结果">{receipt.links.map(l=><li key={l.ordinal}>{l.target}：{linkStatusLabel(l.status)}{l.reason?`；${linkReasons[l.reason]??"原因尚未确认，请查看详细记录；不要自行建立关联。"}`:l.status==="unresolved"?"；请核对目标，必要时手动选择。":""}</li>)}</ul></>:null}
  {receipt?.links.some(l=>l.fragment&&l.target_ordinal!==null&&targetDocs[l.target_ordinal])?<fieldset disabled={busy||!!attempt||dirty||!canWrite}><legend>人工映射标题或块引用</legend><p>先核对原件定位，再选择此固定版本中的块。这里保存你的明确映射，不自动推断标题或认定内容一致。未选择项仍保持未解析。</p>{receipt.links.filter(l=>l.fragment&&l.target_ordinal!==null&&targetDocs[l.target_ordinal]).map(l=>{const d=targetDocs[l.target_ordinal!];return <label key={l.ordinal}>{l.target}#{l.fragment_is_block?"^":""}{l.fragment}<select aria-label={`固定块映射 ${l.ordinal}`} value={fragmentChoices[l.ordinal]??""} onChange={e=>setFragmentChoices(old=>({...old,[l.ordinal]:e.target.value}))}><option value="">不映射</option>{d.blocks.map(b=><option key={b.block_id} value={b.block_id}>{d.title} · v{d.version} · {b.text_projection.slice(0,100)||b.kind} · {b.block_id}</option>)}</select></label>;})}</fieldset>:null}
  {observed?<RawReceiptButton label="关系文档实际读回" payload={observed}/>:null}
   {graph?<><p>已读取现有关系图：本页 {graph.edges.length} 条关系，仅限当前扫描范围，不代表全库。可在关系空间查看同一固定版本。</p><RawReceiptButton label="现有关系图投影" payload={graph}/></>:null}
   {failure?<RawReceiptButton label="原件链接处理错误详情" payload={{error:failure}}/>:null}
  <p role="status">{message}</p>
 </section>;
}
