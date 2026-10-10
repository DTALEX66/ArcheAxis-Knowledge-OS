import { coreCommand } from "../api/core";
import type { DocumentDto, DocumentSummaryDto, DocumentsListDto } from "../api/generated/core-contract";
import { DISCIPLINES, TEMPLATES } from "./disciplines";
import { documentRequestIdentity } from "../presentation/documentRequestIdentity";

export type ObjectReference = { document_id:string; version:number; block_id:string|null; relation:string; x:number; y:number };
export type TemplateBinding = { schema:"archeaxis.template/v1"; template_id:string; discipline_id:string; fields:Record<string,string>; references:ObjectReference[]; learning_item_key:string|null };
type Editor = {type:string; attrs?:Record<string,unknown>; content?:unknown[]};
export function binding(doc:DocumentDto):TemplateBinding|null {
  const editor = doc.editor_json as Editor;
  const raw = editor?.attrs?.archeaxis_template as TemplateBinding | undefined;
  if (!raw || raw.schema !== "archeaxis.template/v1") return null;
  if (Object.keys(raw).some(key=>!["schema","template_id","discipline_id","fields","references","learning_item_key"].includes(key))
    || !TEMPLATES.some(t=>t.id===raw.template_id) || !DISCIPLINES.some(d=>d.id===raw.discipline_id)
    || !raw.fields || typeof raw.fields!=="object" || Array.isArray(raw.fields)
    || Object.values(raw.fields).some(v=>typeof v!=="string") || !Array.isArray(raw.references)
    || raw.references.length>100 || raw.references.some(r=>!r || Object.keys(r).some(key=>!["document_id","version","block_id","relation","x","y"].includes(key)) || typeof r.document_id!=="string" || !r.document_id
      || !Number.isInteger(r.version) || r.version<1 || !(r.block_id===null || typeof r.block_id==="string")
      || typeof r.relation!=="string" || !Number.isFinite(r.x) || !Number.isFinite(r.y))
    || !(raw.learning_item_key===null || typeof raw.learning_item_key==="string")) throw new Error("模板配置无效；原文仍保留，请在资料库查看。");
  return raw;
}
export function readableBinding(doc:DocumentDto):TemplateBinding|null {
  try { return binding(doc); } catch { return null; }
}
export type TemplateWriteAttempt = { operation:"document_create"|"document_draft"; payload:Record<string,unknown>; editor:Editor; id:string; version:number; title:string; source_id:string|null; source_revision:string|null };
function canonical(value:unknown):string {
  if(Array.isArray(value))return `[${value.map(canonical).join(",")}]`;
  if(value&&typeof value==="object")return `{${Object.entries(value).sort(([a],[b])=>a.localeCompare(b)).map(([key,item])=>`${JSON.stringify(key)}:${canonical(item)}`).join(",")}}`;
  return JSON.stringify(value);
}
export async function prepareTemplateCreate(template_id:string,discipline_id:string,requestId=`template_${crypto.randomUUID()}`):Promise<TemplateWriteAttempt> {
  const pack=DISCIPLINES.find(p=>p.id===discipline_id);const template=TEMPLATES.find(t=>t.id===template_id);
  if(!pack||!template)throw new Error("未知模板或学科");
  const metadata:TemplateBinding={schema:"archeaxis.template/v1",template_id,discipline_id,fields:{status:"unevaluated",...Object.fromEntries(pack.fields.map(k=>[k,""]))},references:[],learning_item_key:null};
  const title=`${pack.name} · ${template.name}`;
  const editor:Editor={type:"doc",attrs:{archeaxis_template:metadata},content:[{type:"paragraph",content:[{type:"text",text:pack.sample}]}]};
  return {operation:"document_create",payload:{body:{create_request_id:requestId,title,editor_json:editor}},editor,id:await documentRequestIdentity(requestId),version:1,title,source_id:null,source_revision:null};
}
export async function prepareTemplateSave(doc:DocumentDto,next:TemplateBinding):Promise<TemplateWriteAttempt> {
  const candidate=structuredClone({...doc,editor_json:{...(doc.editor_json as Editor),attrs:{...(doc.editor_json as Editor).attrs,archeaxis_template:next}}});
  binding(candidate); // Reject malformed state before any write; Core owns version/integrity.
  for(const ref of next.references) await resolveReference(ref);
  if(next.learning_item_key) {
    const items=await coreCommand<{items:Array<{item_key:string}>;count:number}>("learning_items");
    if(!Array.isArray(items.items)||items.count!==items.items.length||!items.items.some(item=>item.item_key===next.learning_item_key))throw new Error("学习对象未出现在实际学习集合中；保留草稿。");
    const state=await coreCommand<{item_key:string}>("learning_state",{item_key:next.learning_item_key});
    if(state.item_key!==next.learning_item_key)throw new Error("学习对象未解析");
  }
  return {operation:"document_draft",payload:{document_id:doc.document_id,body:{expected_version:doc.version,editor_json:candidate.editor_json}},editor:candidate.editor_json,id:doc.document_id,version:doc.version+1,title:doc.title,source_id:doc.source_id,source_revision:doc.source_revision};
}
/** Core adds IDs to top-level blocks only. All requested content and existing IDs must survive. */
export function validateTemplateWrite(attempt:TemplateWriteAttempt,document:DocumentDto):void {
  if(document.document_id!==attempt.id||document.version!==attempt.version||document.title!==attempt.title
    || document.source_id!==attempt.source_id||document.source_revision!==attempt.source_revision
    || !/^[a-f0-9]{64}$/.test(document.content_sha256)||!binding(document))throw new Error("模板保存读回身份不匹配；冻结请求仍保留。");
  const editor=structuredClone(document.editor_json) as Editor;
  const nodes=editor.content;
  if(!Array.isArray(nodes)||!Array.isArray(attempt.editor.content)||nodes.length!==attempt.editor.content.length||document.blocks.length!==nodes.length)throw new Error("模板保存读回正文不完整。");
  const ids=new Set<string>();
  for(let index=0;index<nodes.length;index++){
    const node=nodes[index] as Editor;const expected=attempt.editor.content[index] as Editor;
    const id=node.attrs?.block_id;
    if(typeof id!=="string"||!id||ids.has(id)||document.blocks[index].block_id!==id||document.blocks[index].ordinal!==index
      ||canonical(document.blocks[index].node_json)!==canonical((document.editor_json as Editor).content![index]))throw new Error("模板保存读回块身份不完整。");
    ids.add(id);
    if(!Object.prototype.hasOwnProperty.call(expected.attrs??{},"block_id")){
      delete node.attrs!.block_id;
      if(!expected.attrs&&Object.keys(node.attrs!).length===0)delete node.attrs;
    }
  }
  if(canonical(editor)!==canonical(attempt.editor))throw new Error("模板保存读回内容不匹配；原草稿保留。");
}
export async function readTemplateWrite(attempt:TemplateWriteAttempt):Promise<DocumentDto> {
  const document=await coreCommand<DocumentDto>("document_version",{document_id:attempt.id,version:attempt.version});
  validateTemplateWrite(attempt,document);
  return document;
}
export async function executeTemplateWrite(attempt:TemplateWriteAttempt):Promise<DocumentDto> {
  const result=await coreCommand<DocumentDto>(attempt.operation,structuredClone(attempt.payload));
  validateTemplateWrite(attempt,result);
  const document=await readTemplateWrite(attempt);
  if(result.content_sha256!==document.content_sha256||canonical(result.editor_json)!==canonical(document.editor_json))throw new Error("模板保存ACK与版本读回不一致；请核对冻结请求。");
  return document;
}
export async function createTemplate(template_id:string,discipline_id:string):Promise<DocumentDto> {
  return executeTemplateWrite(await prepareTemplateCreate(template_id,discipline_id));
}
export async function saveBinding(doc:DocumentDto,next:TemplateBinding):Promise<DocumentDto> {
  return executeTemplateWrite(await prepareTemplateSave(doc,next));
}
export async function resolveReference(ref:ObjectReference):Promise<{document:DocumentDto;text:string}> {
  const document=await coreCommand<DocumentDto>("document_version",{document_id:ref.document_id,version:ref.version});
  if(document.document_id!==ref.document_id||document.version!==ref.version)throw new Error("引用版本不匹配");
  const block=ref.block_id ? document.blocks.find(b=>b.block_id===ref.block_id) : null;
  if(ref.block_id&&!block)throw new Error("引用块未找到；保留旧引用，需重新定位");
  return {document,text:block?.text_projection??document.text_projection};
}
export async function loadTemplateDocuments():Promise<{documents:DocumentDto[];bounded:boolean}> {
  const summaries:DocumentSummaryDto[]=[];const ids=new Set<string>(),cursors=new Set<string>();
  let cursor:string|undefined;let count:number|undefined;
  do {
    const page=await coreCommand<DocumentsListDto>("documents_list",cursor?{cursor}:{});
    if(!Array.isArray(page.documents)||!Number.isSafeInteger(page.snapshot_count)||page.snapshot_count<0
      || !(page.next_cursor===null || (typeof page.next_cursor==="string"&&/^[A-Za-z0-9_-]{1,1024}$/.test(page.next_cursor)))
      || (count!==undefined&&count!==page.snapshot_count))throw new Error("文档分页合同不完整，请更新本地核心或重新读取。");
    count=page.snapshot_count;
    for(const summary of page.documents){if(ids.has(summary.document_id))throw new Error("文档分页重复，集合未完成。");ids.add(summary.document_id);summaries.push(summary);}
    if(summaries.length>count|| (page.next_cursor!==null&&page.documents.length===0))throw new Error("文档分页数量不一致。");
    if(page.next_cursor!==null){if(cursors.has(page.next_cursor))throw new Error("文档分页未推进。");cursors.add(page.next_cursor);cursor=page.next_cursor;}else cursor=undefined;
  } while(cursor);
  if(summaries.length!==count)throw new Error("文档集合未完整读回。");
  const documents:DocumentDto[]=[];
  for(let index=0;index<summaries.length;index+=8){
    documents.push(...await Promise.all(summaries.slice(index,index+8).map(async summary=>{
      const document=await coreCommand<DocumentDto>("document_version",{document_id:summary.document_id,version:summary.version});
      if(document.document_id!==summary.document_id||document.version!==summary.version||document.content_sha256!==summary.content_sha256)throw new Error("文档摘要版本未能完整读回。");
      return document;
    })));
  }
  return {documents,bounded:false};
}
export function backlinks(documents:DocumentDto[],target:string) {
  return documents.flatMap(doc=>(readableBinding(doc)?.references??[]).filter(r=>r.document_id===target).map(reference=>({document:doc,reference,context:doc.text_projection.slice(0,160)})));
}
export function collection(documents:DocumentDto[],discipline:string) {
  const members=documents.filter(d=>readableBinding(d)?.discipline_id===discipline);
  const statuses:Record<string,number>=Object.create(null);
  let relations=0;
  for(const doc of members){const state=binding(doc)!;const status=state.fields.status||"unevaluated";statuses[status]=(statuses[status]??0)+1;relations+=state.references.length;}
  return {members,statuses,relations};
}
