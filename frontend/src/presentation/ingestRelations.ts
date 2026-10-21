import type {CoreOperation, DocumentDto, IngestBatchDto, IngestBatchMemberDto, IngestRelationsApplyInput, IngestRelationsDto, IngestRelationFragmentBinding, SourceDto} from "../api/generated/core-contract";
import {sameValue} from "./exchangeProof";

export type FolderMemberSelection = {batch_id:string; ordinal:number; workspace_id:string; restore_epoch:string; source_id:string; source_revision:string};
export type RelationAttempt = {selection:FolderMemberSelection; body:IngestRelationsApplyInput; before:DocumentDto};
export type RelationRead = <T>(operation:CoreOperation,payload:Record<string,unknown>)=>Promise<T>;
export const markdownMember=(member:IngestBatchMemberDto)=>/\.(md|markdown)$/i.test(member.relative_path);

export function selectedFragments(receipt:IngestRelationsDto|null,choices:Record<number,string>,targets:IngestRelationsApplyInput["targets"],snapshots:Record<number,DocumentDto>):IngestRelationFragmentBinding[] {
 const result:IngestRelationFragmentBinding[]=[];
 for(const [ordinal,value] of Object.entries(choices)) {
  if(!value)continue;
  const link=receipt?.links.find(l=>l.ordinal===Number(ordinal));
  if(!link?.fragment||link.target_ordinal===null)throw new Error("原件定位尚未明确；未发送块映射");
  const target=targets.find(t=>t.ordinal===link.target_ordinal),snapshot=snapshots[link.target_ordinal];
  if(!target?.document||!snapshot||target.document.document_id!==snapshot.document_id||target.document.version!==snapshot.version||target.document.content_sha256!==snapshot.content_sha256||!snapshot.blocks.some(b=>b.block_id===value))throw new Error("选定块的固定版本已变化；请重新读取映射");
  result.push({link_ordinal:link.ordinal,target_ordinal:link.target_ordinal,fragment:link.fragment,fragment_is_block:link.fragment_is_block,block_id:value});
 }
 return result;
}

export function verifiedSource(source:SourceDto,id:string,revision:string) {
 if(source.source_id!==id||source.source_revision!==revision||source.sha256!==revision)throw new Error("来源身份与文件夹成员不符");
 return source;
}
export async function readRelationBatch(read:RelationRead,selection:FolderMemberSelection):Promise<IngestBatchDto> {
 let page=await read<IngestBatchDto>("ingest_batch_get",{batch_id:selection.batch_id});
 const first=page,members:IngestBatchMemberDto[]=[],seen=new Set<number>();
 while(true){
  if(page.batch_id!==selection.batch_id||page.workspace_id!==selection.workspace_id||page.restore_epoch!==selection.restore_epoch
   ||!page.complete||page.expected_members!==first.expected_members||page.registered_members!==first.expected_members)throw new Error("批次或恢复身份已变化，不能继续旧操作");
  for(const member of page.members){if(seen.has(member.ordinal)||members.length>=10000)throw new Error("批次分页身份重复或超限");seen.add(member.ordinal);members.push(member);}
  if(page.next_ordinal===null)break;
  if(!page.members.length||page.next_ordinal!==page.members.at(-1)?.ordinal)throw new Error("批次分页不完整");
  page=await read<IngestBatchDto>("ingest_batch_get",{batch_id:selection.batch_id,after_ordinal:page.next_ordinal});
 }
 if(members.length!==first.expected_members||members.some((m,i)=>m.ordinal!==i))throw new Error("完整成员清单未读回");
 const member=members[selection.ordinal];
 if(!member||member.source_id!==selection.source_id||member.source_revision!==selection.source_revision||!markdownMember(member))throw new Error("必须选择已导入的原始 Markdown 成员");
 return {...first,members,next_ordinal:null};
}
export function freezeRelations(selection:FolderMemberSelection,batch:IngestBatchDto,document:DocumentDto,targets:IngestRelationsApplyInput["targets"],dirty:boolean,fragments:IngestRelationFragmentBinding[]=[]):RelationAttempt {
 if(dirty)throw new Error("当前文档有草稿或未确认写入，请先处理");
 if(batch.workspace_id!==selection.workspace_id||batch.restore_epoch!==selection.restore_epoch||batch.batch_id!==selection.batch_id||!batch.complete)throw new Error("批次身份不符");
 if(document.source_id!==selection.source_id||document.source_revision!==selection.source_revision)throw new Error("请显式打开此成员绑定的已保存文档");
 if(targets.length>200||new Set(targets.map(t=>t.ordinal)).size!==targets.length)throw new Error("目标数量或身份重复");
 for(const t of targets){const m=batch.members.find(m=>m.ordinal===t.ordinal);
  if(!m||!t.source_id||m.source_id!==t.source_id||m.source_revision!==t.source_revision||m.disposition!=="pending")throw new Error("目标不是本批次的已导入原件");
  if(markdownMember(m)&&(!t.document||(m.job_id&&m.job_state!=="succeeded")))throw new Error("笔记目标须显式选择固定文档，已有转换须成功");
 }
 const member=batch.members.find(m=>m.ordinal===selection.ordinal);
 if(!member||member.source_id!==selection.source_id||member.source_revision!==selection.source_revision||(member.job_id&&member.job_state!=="succeeded"))throw new Error("原始成员身份或转换状态未确认");
 return structuredClone({selection,before:document,body:{workspace_id:selection.workspace_id,restore_epoch:selection.restore_epoch,source_id:selection.source_id,source_revision:selection.source_revision,document_id:document.document_id,expected_version:document.version,content_sha256:document.content_sha256,targets,...(fragments.length?{fragment_bindings:fragments}:{})}});
}
export function verifyRelationReceipt(attempt:RelationAttempt,receipt:IngestRelationsDto,readback:DocumentDto) {
 const s=attempt.selection,b=attempt.body,d=receipt.document;
 if(receipt.batch_id!==s.batch_id||receipt.ordinal!==s.ordinal||receipt.workspace_id!==s.workspace_id||receipt.restore_epoch!==s.restore_epoch||receipt.source_id!==s.source_id||receipt.source_revision!==s.source_revision
  ||d.document_id!==b.document_id||d.source_id!==b.source_id||d.source_revision!==b.source_revision||d.version!==b.expected_version+(receipt.added_relations?1:0)||!sameValue(d,readback))throw new Error("关系回执与固定版本读回不符；原请求仍待核对");
 return d;
}
