import { coreCommand } from "../api/core";
import { assertCoreDto, type AnchorDto, type AnchorResolutionDto, type OriginalDto, type PublicResearchHitDto, type PublicResearchReceiptDto, type PublicResearchScope, type PublicResearchSelectionDto } from "../api/generated/core-contract";
import type { DocumentRelations, ResearchCitation, ResearchDocument } from "../api/generated/research-contract";

export const comparisonStances = { unclassified:"尚未判断", supports:"支持", opposes:"反对", conflict:"存在冲突", uncertain:"不确定" };
export type ComparisonStance = keyof typeof comparisonStances;
export type ComparisonChoice = { family:PublicResearchHitDto["family"]; id:string; stance:ComparisonStance };
export type EvidenceComparison = { id:string; query:string; stance:ComparisonStance; hit:PublicResearchHitDto; selection:PublicResearchSelectionDto; citation:ResearchCitation };
const same = (a:unknown,b:unknown):boolean => {
  if(Array.isArray(a))return Array.isArray(b)&&a.length===b.length&&a.every((v,i)=>same(v,b[i]));
  if(a&&typeof a==="object")return !!b&&typeof b==="object"&&!Array.isArray(b)&&Object.keys(a).length===Object.keys(b).length&&Object.entries(a).every(([k,v])=>same(v,(b as Record<string,unknown>)[k]));
  return a===b;
};
export async function evidenceHash(bytes:Uint8Array):Promise<string> {
  return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",bytes.slice().buffer)),b=>b.toString(16).padStart(2,"0")).join("");
}

// Selection is by the exact frozen hit identity, never by URL grouping or a title.
// guard rechecks the view generation and actor workspace before every Core call.
export async function captureEvidenceComparisons(receipt:PublicResearchReceiptDto, choices:readonly ComparisonChoice[], actor:PublicResearchScope, guard:()=>Promise<void>):Promise<EvidenceComparison[]> {
  if(!["complete","partial"].includes(receipt.state)||!choices.length||choices.length>18)throw Error("comparison selection bounds");
  const seen=new Set<string>(),result:EvidenceComparison[]=[];
  for(const choice of choices){
    const key=JSON.stringify([choice.family,choice.id]);
    if(seen.has(key)||!Object.hasOwn(comparisonStances,choice.stance))throw Error("comparison selection identity");
    seen.add(key);
    const channels=receipt.channels?.filter(c=>c.family===choice.family);
    const hits=channels?.flatMap(c=>c.hits.filter(h=>h.id===choice.id));
    if(channels?.length!==1||hits?.length!==1||!channels[0].raw_source)throw Error("comparison hit missing");
    const hit=hits[0],raw=channels[0].raw_source;
    await guard();
    // The caller supplies fresh actor scope; it can differ from the historical receipt epoch.
    const selected=await coreCommand<PublicResearchSelectionDto>("public_research_materialize",{body:{...actor,request_id:receipt.request_id,family:hit.family,hit_id:hit.id}});
    const selection=assertCoreDto<PublicResearchSelectionDto>("PublicResearchSelectionDto",selected);
    if(selection.request_id!==receipt.request_id||selection.family!==hit.family||selection.hit_id!==hit.id||selection.title!==hit.title||selection.representation!==hit.representation||selection.truncated!==hit.truncated||!same(selection.raw_reference,raw))throw Error("comparison materialization mismatch");
    await guard();
    const original=await coreCommand<OriginalDto>("source_original",{source_id:selection.reference.source_id});
    if(original.source_id!==selection.reference.source_id||original.sha256!==selection.reference.sha256||!original.media_type.startsWith("text/"))throw Error("comparison source mismatch");
    const bytes=Uint8Array.from(atob(original.content_base64),c=>c.charCodeAt(0));
    // No silent truncation: this citation locates the complete derived snapshot,
    // not an offset into raw API JSON, nor an asserted upstream page location.
    if(!bytes.length||bytes.length>16384||await evidenceHash(bytes)!==selection.reference.sha256)throw Error("comparison snapshot bounds or hash");
    const quote=new TextDecoder("utf-8",{fatal:true,ignoreBOM:true}).decode(bytes);
    const checksum=await evidenceHash(bytes);
    await guard();
    const anchor=await coreCommand<AnchorDto>("anchor_create",{source_id:original.source_id,body:{revision:original.sha256,position:JSON.stringify({type:"text",start:0,end:bytes.length}),checksum}});
    const position=JSON.parse(anchor.position);
    if(!anchor.anchor_id||anchor.source_id!==original.source_id||anchor.source_revision!==original.sha256||anchor.location_status!=="located"||position.type!=="text"||position.start!==0||position.end!==bytes.length||position.checksum!==checksum||position.location_status!=="located")throw Error("comparison anchor mismatch");
    await guard();
    const resolved=await coreCommand<AnchorResolutionDto>("anchor_resolve",{source_id:original.source_id,anchor_id:anchor.anchor_id});
    if(resolved.status!=="CURRENT"||resolved.source_id!==original.source_id||resolved.anchor_id!==anchor.anchor_id||resolved.source_revision!==original.sha256||resolved.current_source_revision!==original.sha256||resolved.scope!=="locator_provenance_only"||resolved.position!==anchor.position)throw Error("comparison anchor unresolved");
    const citation:ResearchCitation={schema:"archeaxis.research-citation/v1",anchor_id:anchor.anchor_id,source_sha256:original.sha256,anchor_position_sha256:await evidenceHash(new TextEncoder().encode(anchor.position)),quote,quote_sha256:checksum,read_snapshot_sha256:original.sha256};
    const id=await evidenceHash(new TextEncoder().encode(JSON.stringify([receipt.request_id,hit.family,hit.id,selection.reference,citation.quote_sha256])));
    result.push({id,query:receipt.query,stance:choice.stance,hit:structuredClone(hit),selection:structuredClone(selection),citation});
  }
  await guard();
  return result;
}

// Existing Research/Relations DTOs retain authored judgments and both CAS references.
// Pure merge: a failure leaves the caller's entire draft/envelope unchanged.
export function appendEvidenceComparisons(research:ResearchDocument, relations:unknown, bindings:readonly EvidenceComparison[]):{research:ResearchDocument;relations:DocumentRelations} {
  const next=structuredClone(research);
  const graph=relations===undefined?{schema:"archeaxis.relations/v1" as const,relations:[]}:structuredClone(assertCoreDto<DocumentRelations>("DocumentRelationsDto",relations));
  function append<T extends {id:string}>(rows:T[],item:T){const prior=rows.find(v=>v.id===item.id);if(prior){if(!same(prior,item))throw Error("comparison identity collision");}else rows.push(item);}
  for(const binding of bindings){
    const {id,query,stance,selection,citation,hit}=binding,ref=structuredClone(selection.reference),raw=structuredClone(selection.raw_reference);
    const judgment=`作者判断：${comparisonStances[stance]}（未核验，未知识采用）\n主题：${query}\n来源独立性：UNKNOWN；相同地址分组不是独立证据判定。\n内容范围：${hit.content} / ${selection.representation}${selection.truncated?"；上游返回已截断":""}\n标题：${hit.title}\n地址：${hit.url}\n取得时间：${hit.retrieved_at}\n许可：${hit.license??"未知"}\n定位仅指完整Core派生快照；不是原API字节偏移或原站定位。`;
    append(next.materials,{id:`cmp_material_${id}`,reference:ref,citation:structuredClone(citation),note:`公开资料派生快照（未核验，未知识采用）\n${selection.title}\n请求 ${selection.request_id} / ${selection.family} / ${selection.hit_id}\n对应原始API：${raw.source_id} / ${raw.sha256}\n定位仅指派生快照。`});
    append(next.materials,{id:`cmp_raw_${id}`,reference:raw,note:`原始 API 响应字节已保全（未核验；不是文章全文）\n请求 ${selection.request_id} / ${selection.family} / ${selection.hit_id}\n对应派生快照：${ref.source_id} / ${ref.sha256}`});
    // One entry per hit, not per URL. Conflicts/uncertainty remain explicitly unresolved.
    append(next.unresolved,{id:`cmp_judgment_${stance}_${id}`,text:judgment,references:[ref,raw]});
    // The complete query stays in the referenced authored entry. A stable ID
    // links this compact graph label to that entry without cutting the query.
    append(graph.relations,{id:`cmp_relation_${stance}_${id}`,kind:stance==="supports"?"supports":stance==="opposes"?"contradicts":"related",label:`作者判断：${comparisonStances[stance]}；未核验；独立性UNKNOWN；对照ID：${id}`,target:ref});
  }
  // Core's relation label limit is UTF-8 bytes (not the generic DTO's string
  // length). Validate the entire merged envelope before the caller mutates it.
  assertCoreDto<DocumentRelations>("DocumentRelationsDto",graph);
  const ids=new Set<string>(),token=(v:unknown,max=256):v is string=>typeof v==="string"&&v!=="."&&v!==".."&&v.length>0&&v.length<=max&&/^[A-Za-z0-9_.-]+$/.test(v);
  if(graph.relations.length>256)throw Error("comparison relation budget");
  for(const relation of graph.relations){
    if(Object.keys(relation).some(k=>!["id","kind","label","target"].includes(k))||!token(relation.id,128)||!/^[A-Za-z0-9_-]+$/.test(relation.id)||ids.has(relation.id)||new TextEncoder().encode(relation.label).length>1024)throw Error("comparison relation shape or byte budget");
    ids.add(relation.id);
    const ref=relation.target,allowed=ref.kind==="source"?["kind","source_id","sha256"]:ref.kind==="document"?["kind","document_id","version","block_id"]:["kind","knowledge_id"];
    if(Object.keys(ref).some(k=>!allowed.includes(k)))throw Error("comparison reference shape");
    if(ref.kind==="source"?(!token(ref.source_id)||!/^[a-f0-9]{64}$/.test(ref.sha256)):ref.kind==="document"?(!token(ref.document_id)||!Number.isSafeInteger(ref.version)||ref.version<1||!(ref.block_id==null||token(ref.block_id))):!token(ref.knowledge_id))throw Error("comparison reference identity");
  }
  return {research:next,relations:graph};
}
