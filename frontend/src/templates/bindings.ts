import { coreCommand } from "../api/core";
import type { DocumentDto, DocumentSummaryDto } from "../api/generated/core-contract";
import { DISCIPLINES, TEMPLATES } from "./disciplines";

export type ObjectReference = { document_id:string; version:number; block_id:string|null; relation:string; x:number; y:number };
export type TemplateBinding = { schema:"archeaxis.template/v1"; template_id:string; discipline_id:string; fields:Record<string,string>; references:ObjectReference[]; learning_item_key:string|null };
type Editor = {type:string; attrs?:Record<string,unknown>; content?:unknown[]};
export function binding(doc:DocumentDto):TemplateBinding|null {
  const editor = doc.editor_json as Editor;
  const raw = editor?.attrs?.archeaxis_template as TemplateBinding | undefined;
  if (!raw || raw.schema !== "archeaxis.template/v1") return null;
  if (!TEMPLATES.some(t=>t.id===raw.template_id) || !DISCIPLINES.some(d=>d.id===raw.discipline_id)
    || !raw.fields || typeof raw.fields!=="object" || Array.isArray(raw.fields)
    || Object.values(raw.fields).some(v=>typeof v!=="string") || !Array.isArray(raw.references)
    || raw.references.length>100 || raw.references.some(r=>!r || typeof r.document_id!=="string" || !r.document_id
      || !Number.isInteger(r.version) || r.version<1 || !(r.block_id===null || typeof r.block_id==="string")
      || typeof r.relation!=="string" || !Number.isFinite(r.x) || !Number.isFinite(r.y))
    || !(raw.learning_item_key===null || typeof raw.learning_item_key==="string")) throw new Error("模板配置无效；原文仍保留，请在资料库查看。");
  return raw;
}
export function readableBinding(doc:DocumentDto):TemplateBinding|null {
  try { return binding(doc); } catch { return null; }
}
export async function createTemplate(template_id:string,discipline_id:string):Promise<DocumentDto> {
  const pack=DISCIPLINES.find(p=>p.id===discipline_id);const template=TEMPLATES.find(t=>t.id===template_id);
  if(!pack||!template)throw new Error("未知模板或学科");
  const metadata:TemplateBinding={schema:"archeaxis.template/v1",template_id,discipline_id,fields:{status:"unevaluated",...Object.fromEntries(pack.fields.map(k=>[k,""]))},references:[],learning_item_key:null};
  return coreCommand<DocumentDto>("document_create",{body:{title:`${pack.name} · ${template.name}`,editor_json:{type:"doc",attrs:{archeaxis_template:metadata},content:[{type:"paragraph",content:[{type:"text",text:pack.sample}]}]}}});
}
export async function saveBinding(doc:DocumentDto,next:TemplateBinding):Promise<DocumentDto> {
  const candidate={...doc,editor_json:{...(doc.editor_json as Editor),attrs:{...(doc.editor_json as Editor).attrs,archeaxis_template:next}}};
  binding(candidate); // Reject malformed state before any write; Core owns version/integrity.
  for(const ref of next.references) await resolveReference(ref);
  if(next.learning_item_key) {
    const state=await coreCommand<{item_key:string}>("learning_state",{item_key:next.learning_item_key});
    if(state.item_key!==next.learning_item_key)throw new Error("学习对象未解析");
  }
  return coreCommand<DocumentDto>("document_draft",{document_id:doc.document_id,body:{expected_version:doc.version,editor_json:candidate.editor_json}});
}
export async function resolveReference(ref:ObjectReference):Promise<{document:DocumentDto;text:string}> {
  const document=await coreCommand<DocumentDto>("document_version",{document_id:ref.document_id,version:ref.version});
  if(document.document_id!==ref.document_id||document.version!==ref.version)throw new Error("引用版本不匹配");
  const block=ref.block_id ? document.blocks.find(b=>b.block_id===ref.block_id) : null;
  if(ref.block_id&&!block)throw new Error("引用块未找到；保留旧引用，需重新定位");
  return {document,text:block?.text_projection??document.text_projection};
}
export async function loadTemplateDocuments():Promise<{documents:DocumentDto[];bounded:boolean}> {
  const list=await coreCommand<{documents:DocumentSummaryDto[]}>("documents_list");
  // Derived view over canonical documents, never a second store; show the limit.
  const documents=await Promise.all(list.documents.slice(0,100).map(d=>coreCommand<DocumentDto>("document_get",{document_id:d.document_id})));
  return {documents,bounded:list.documents.length>=100};
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
