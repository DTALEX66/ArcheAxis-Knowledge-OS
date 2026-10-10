import { coreCommand } from "../api/core";
import type { DocumentDto } from "../api/generated/core-contract";
import { assertAiAssetDto, type AiAsset, type AssetContextGrant, type AssetPacketRequest, type AssetSnapshot } from "../api/generated/ai-asset-contract";
const record=(value:unknown):Record<string,unknown>=>{if(!value||typeof value!=="object"||Array.isArray(value))throw new Error("资产对象不兼容");return value as Record<string,unknown>;};
const snap=(d:DocumentDto):AssetSnapshot=>({document_id:d.document_id,version:d.version,content_sha256:d.content_sha256});
export const sameAssetPin=(a:AssetSnapshot,b:AssetSnapshot)=>a.document_id===b.document_id&&a.version===b.version&&a.content_sha256===b.content_sha256;
export function readAsset(d:DocumentDto):AiAsset{return assertAiAssetDto<AiAsset>("AiAsset",record(record(d.editor_json).attrs).archeaxis_ai_asset);}
export function readAssetGrant(d:DocumentDto):AssetContextGrant{return assertAiAssetDto<AssetContextGrant>("AssetContextGrant",record(record(d.editor_json).attrs).archeaxis_asset_context_grant);}
export type AssetConsumption={request:AssetPacketRequest;grant:AssetContextGrant;asset:AiAsset;current:boolean};
/** Preflight uses actual current get snapshots. Core repeats all authorization checks. */
export async function readAssetConsumption(grantPin:AssetSnapshot,operation:"answer"|"retest",expected?:AssetPacketRequest):Promise<AssetConsumption>{
 const doc=await coreCommand<DocumentDto>("document_get",{document_id:grantPin.document_id});
 if(!sameAssetPin(snap(doc),grantPin))throw new Error("资产授权版本已变化，不能自动换版");
 const grant=readAssetGrant(doc);
 if(grant.state!=="granted"||grant.consumer!=="local-machine"||!grant.operations.includes(operation)||!grant.purpose.trim()||(grant.expires_at!=null&&grant.expires_at<=Math.floor(Date.now()/1000)))throw new Error("资产授权撤回、过期或用途操作不匹配");
 const assetDoc=await coreCommand<DocumentDto>("document_get",{document_id:grant.asset.document_id});
 if(!sameAssetPin(snap(assetDoc),grant.asset))throw new Error("资产已换版，旧授权不自动升级");
 const seen=new Set<string>();
 async function visit(pin:AssetSnapshot,d:DocumentDto,depth:number):Promise<AiAsset>{
  if(depth>4||seen.size>=128||seen.has(pin.document_id))throw new Error("知识包成员循环、重复或超出有限范围");
  seen.add(pin.document_id);
  if(!sameAssetPin(snap(d),pin))throw new Error("知识包成员版本已变化");
  const v=readAsset(d);
  if(v.state!=="adopted"||(v.expires_at!=null&&v.expires_at<=Math.floor(Date.now()/1000)))throw new Error(depth?"知识包成员不可消费":"资产未采用、已撤回或过期");
  if(v.conflicts.length)throw new Error("资产或知识包成员有未解决冲突，请先保存重新审核的版本");
  for(const member of v.members){await visit(member,await coreCommand<DocumentDto>("document_get",{document_id:member.document_id}),depth+1);}
  return v;
 }
 const asset=await visit(grant.asset,assetDoc,0);
 const request:AssetPacketRequest={request_id:expected?.request_id??`assetuse_${crypto.randomUUID()}`,asset:structuredClone(grant.asset),grant:snap(doc),purpose:grant.purpose,consumer:"local-machine",operation};
 if(expected&&(!sameAssetPin(expected.asset,request.asset)||!sameAssetPin(expected.grant,request.grant)||expected.purpose!==request.purpose||expected.consumer!==request.consumer||expected.operation!==request.operation))throw new Error("消费快照用途或固定对象已改变");
 return {request,grant,asset,current:true};
}
