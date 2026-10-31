import { useEffect, useMemo, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import { assertCoreDto, type PublicResearchRequest, type PublicResearchTarget, type PublicResearchReceiptDto, type PublicResearchJournalDto, type PublicResearchCancelDto, type PublicResearchSelectionDto, type PublicResearchHitDto } from "../api/generated/core-contract";
import { assertUiWorkingState, type UiWorkingStateRead } from "../api/generated/ui-working-state-contract";
import type { PublicResearchCommunitySite, PublicResearchFamily, PublicResearchSnapshot } from "../components/PublicResearchPanel";
import { captureEvidenceComparisons, type ComparisonChoice, type EvidenceComparison } from "./publicEvidenceComparison";

type Phase="idle"|"loading"|"read"|"failed"|"cancelled";
type State={phase:Phase;target:PublicResearchTarget|null;frozen:PublicResearchRequest|null;receipt:PublicResearchReceiptDto|null;journal:PublicResearchReceiptDto[];message:string;acting:boolean};
const initial=():State=>({phase:"idle",target:null,frozen:null,receipt:null,journal:[],message:"",acting:false});
const sameTarget=(a:PublicResearchTarget,b:PublicResearchTarget)=>a.workspace_id===b.workspace_id&&a.restore_epoch===b.restore_epoch&&a.request_id===b.request_id;
async function scope(){const state=assertUiWorkingState<UiWorkingStateRead>("Read",await coreCommand("ui_state_read"));if(state.recovery_requires_confirmation)throw Error("workspace recovery pending");return {workspace_id:state.workspace_id,restore_epoch:state.restore_epoch};}
function boundReceipt(value:unknown,target:PublicResearchTarget,frozen:PublicResearchRequest|null){const receipt=assertCoreDto<PublicResearchReceiptDto>("PublicResearchReceiptDto",value);if(!sameTarget(receipt,target))throw Error("receipt identity");if(frozen&&(receipt.query!==frozen.query||receipt.limit!==frozen.limit||(receipt.community_site??"academia")!==(frozen.community_site??"academia")||receipt.families.length!==frozen.families.length||!frozen.families.every(f=>receipt.families.includes(f))))throw Error("query identity");return receipt;}

// Every asynchronous continuation belongs to one view generation. Core owns the
// durable journal; mounting, page switches and cancellation never retry a query.
export function usePublicResearch(owner:string,onMaterialize:(selection:PublicResearchSelectionDto)=>boolean,onCompare?:(bindings:readonly EvidenceComparison[])=>boolean){
 const store=useRef(new Map<string,State>()),current=useRef(owner),generation=useRef(0),alive=useRef(true),callback=useRef(onMaterialize),comparisonCallback=useRef(onCompare);
 const [,redraw]=useState(0);callback.current=onMaterialize;comparisonCallback.current=onCompare;
 if(current.current!==owner){
  const previous=store.current.get(current.current);
  if(previous&&(previous.phase==="loading"||previous.acting)){previous.phase=previous.phase==="loading"?"failed":previous.phase;previous.acting=false;previous.message="页面已切换；原请求身份与结果保留，执行状态需显式回读。";}
  current.current=owner;generation.current++;
 }
 if(!store.current.has(owner))store.current.set(owner,initial());
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;generation.current++;};},[]);
 const state=store.current.get(owner)!;
 function update(patch:Partial<State>){Object.assign(state,patch);if(alive.current&&current.current===owner)redraw(n=>n+1);}
 function begin(){return {ticket:++generation.current,owner};}
 function valid(run:ReturnType<typeof begin>){return alive.current&&current.current===run.owner&&generation.current===run.ticket;}
 async function search(query:string,families:PublicResearchFamily[],communitySite:PublicResearchCommunitySite="academia"){
  if(state.phase==="loading"||state.acting)return;
  if(!query.trim()||[...query].length>1000||new TextEncoder().encode(query).length>4000||!families.length||new Set(families).size!==families.length||families.some(f=>!["encyclopedia","community","research"].includes(f))||!["academia","stats"].includes(communitySite)){update({message:"关键词或来源范围超过公开检索限制；没有发出请求。"});return;}
  const run=begin();update({phase:"loading",receipt:null,target:null,frozen:null,message:""});
  try{const identity=await scope();if(!valid(run))return;
   const request:PublicResearchRequest={...identity,request_id:crypto.randomUUID(),query,families:[...families],limit:3,...(families.includes("community")?{community_site:communitySite}:{})};
   update({target:{...identity,request_id:request.request_id},frozen:request});
   const receipt=boundReceipt(await coreCommand("public_research_search",{body:request}),request,request);
   if(valid(run))update({phase:"read",receipt});
  }catch{if(valid(run))update({phase:"failed",message:"公开检索未确认；保留请求身份，可显式回读。没有自动重试。"});}
 }
 async function cancel(){const target=state.target;if(state.phase!=="loading")return;const run=begin();update({phase:"cancelled",message:"本页已停止等待；远端是否停止仍未知。"});if(!target)return;
  try{const identity=await scope();if(identity.workspace_id!==target.workspace_id||identity.restore_epoch!==target.restore_epoch)throw Error("execution epoch changed");if(!valid(run))return;const result=assertCoreDto<PublicResearchCancelDto>("PublicResearchCancelDto",await coreCommand("public_research_cancel",{body:target}));if(result.request_id!==target.request_id)throw Error("cancel identity");if(valid(run))update({message:result.cancel_requested?"已请求取消；执行状态与远端停止状态仍未知，请显式回读。":"取消未确认；原请求身份保留，请显式回读。"});}catch{if(valid(run))update({message:"取消回执未确认；原请求身份保留，远端状态未知。"});}
 }
 async function read(candidate?:PublicResearchReceiptDto){const target=candidate?{workspace_id:candidate.workspace_id,restore_epoch:candidate.restore_epoch,request_id:candidate.request_id}:state.target;const frozen=candidate??state.frozen;if(!target||state.phase==="loading"||state.acting)return;const run=begin();update({acting:true,message:""});
  try{const identity=await scope();if(!valid(run))return;const receipt=boundReceipt(await coreCommand("public_research_read",{body:{...identity,request_id:target.request_id}}),target,frozen);if(valid(run))update({target,frozen:receipt,receipt,phase:"read"});}catch{if(valid(run))update({message:"回读未确认；保留原请求与已有结果，没有重新检索。"});}finally{if(valid(run))update({acting:false});}
 }
 async function list(){if(state.phase==="loading"||state.acting)return;const run=begin();update({acting:true,message:""});try{const identity=await scope();if(!valid(run))return;const result=assertCoreDto<PublicResearchJournalDto>("PublicResearchJournalDto",await coreCommand("public_research_list",{body:identity}));if(valid(run))update({journal:result.receipts,message:`已读取最近请求：${result.receipts.length} 条；没有重新检索。`});}catch{if(valid(run))update({message:"请求记录读取失败；已有请求与结果保留。"});}finally{if(valid(run))update({acting:false});}}
 async function materialize(hit:PublicResearchHitDto){const receipt=state.receipt;
  const matches=receipt?.channels?.flatMap(channel=>channel.family===hit.family?channel.hits.filter(row=>row.id===hit.id).map(row=>({channel,hit:row})):[])??[];
  if(!receipt||matches.length!==1||matches[0].hit.provider!==matches[0].channel.provider||matches[0].hit.family!==hit.family||state.acting||state.phase==="loading")return;
  const run=begin();update({acting:true,message:""});const target={workspace_id:receipt.workspace_id,restore_epoch:receipt.restore_epoch,request_id:receipt.request_id};
  try{const identity=await scope();if(!valid(run))return;
   const result=assertCoreDto<PublicResearchSelectionDto>("PublicResearchSelectionDto",await coreCommand("public_research_materialize",{body:{...identity,request_id:target.request_id,family:hit.family,hit_id:hit.id}}));
   const raw=matches[0].channel.raw_source;
   if(result.request_id!==target.request_id||result.family!==hit.family||result.hit_id!==hit.id||result.representation!==hit.representation||result.truncated!==hit.truncated||!raw||result.raw_reference.source_id!==raw.source_id||result.raw_reference.sha256!==raw.sha256)throw Error("selection identity");
   if(!valid(run))return;
   const beforeAppend=await scope();if(beforeAppend.workspace_id!==identity.workspace_id||beforeAppend.restore_epoch!==identity.restore_epoch)throw Error("draft scope changed");
   if(valid(run))update({message:callback.current(result)?"已将派生快照与原始 API 加入材料草稿；未核验，仍需保存。":"固定快照已保全，材料草稿未改变；请处理保存限制后显式再加入。"});
  }catch{if(valid(run))update({message:"固定材料加入未确认；输入与已取得结果保留，没有自动重试。"});}finally{if(valid(run))update({acting:false});}
 }
 async function compare(choices:readonly ComparisonChoice[]):Promise<boolean>{
  const receipt=state.receipt;if(!receipt||!comparisonCallback.current||state.acting||state.phase!=="read")return false;
  const run=begin();update({acting:true,message:"正在固定所选派生快照与定位；尚未追加比较草稿。"});
  try{
   const identity=await scope();if(!valid(run))return false;
   const guard=async()=>{if(!valid(run))throw Error("comparison view changed");const latest=await scope();if(!valid(run)||latest.workspace_id!==identity.workspace_id||latest.restore_epoch!==identity.restore_epoch)throw Error("comparison scope changed");};
   const bindings=await captureEvidenceComparisons(receipt,choices,identity,guard);
   await guard();
   if(!valid(run))return false;
   const kept=comparisonCallback.current?.(bindings)===true;
   update({message:kept?"人工判断已绑定固定来源与派生快照定位，加入未决草稿；仍需保存，独立性未知，未知识采用。":"固定来源已保全；草稿未追加，请处理保存限制后显式重试。"});return kept;
   }catch{if(valid(run))update({message:"比较来源或定位未确认（每段完整引文最多16KiB）；未追加研究记录。输入与选择保留，可显式重试。"});return false;}
  finally{if(valid(run))update({acting:false});}
 }
 const snapshot=useMemo<PublicResearchSnapshot>(()=>state.phase==="read"&&state.receipt?.channels?{status:"read",query:state.receipt.query,families:state.receipt.families,communitySite:state.receipt.community_site??"academia",channels:state.receipt.channels,hits:state.receipt.channels.flatMap(c=>c.hits.map(h=>({...h,retrievedAt:h.retrieved_at,freeAccess:h.free_access})))}:{status:state.phase==="read"?"failed":state.phase},[state.phase,state.receipt]);
 return {...state,snapshot,search,cancel,read,list,materialize,compare};
}
