import {useEffect,useState} from "react";
import {CanonicalContextSpace} from "./CanonicalContextSpace";
import {CanonicalAiJourneySpace} from "./CanonicalAiJourneySpace";
import {CanonicalMachineReceiptsSpace} from "./CanonicalMachineReceiptsSpace";
import {CanonicalAiAssetsSpace} from "./CanonicalAiAssetsSpace";
import {parseAiAsset,parseAssetGrant,prepareAssetPacket} from "../api/aiAssets";
import type {AssetPacketRequest} from "../api/generated/ai-asset-contract";
import type {ContextConsumptionDto} from "../api/generated/core-contract";
import type {ObjectReference} from "../api/generated/research-contract";

/** The three formal pages retain one journey; grants are still explicit Core documents. */
export function CanonicalControlledAiSpace({pageId,onOpenPage,onOpenReference,initialLearningItemKey}:{pageId:string;onOpenPage?:(id:string)=>void;onOpenReference?:(reference:ObjectReference)=>void;initialLearningItemKey?:string}){
 const [visited,setVisited]=useState(()=>new Set([pageId]));
 const [original,setOriginal]=useState<ContextConsumptionDto>();
 const [corrected,setCorrected]=useState<ContextConsumptionDto>();
 const [asset,setAsset]=useState<AssetPacketRequest>();
 const [slot,setSlot]=useState<"original"|"corrected">("original");
 const [proposedKnowledge,setProposedKnowledge]=useState<string>();
 const [boundKnowledge,setBoundKnowledge]=useState<string>();
 const [taskId,setTaskId]=useState<string>();
 const [error,setError]=useState<string|null>(null);
 useEffect(()=>{setVisited(previous=>new Set([...previous,pageId]));},[pageId]);
 function openContext(next:"original"|"corrected"="original",id?:string){setSlot(next);setProposedKnowledge(id);setBoundKnowledge(id);setError(null);onOpenPage?.("13");}
 return <>
  {(visited.has("13")||pageId==="13")?<div hidden={pageId!=="13"}>
   <CanonicalAiAssetsSpace onUseAsset={value=>{setAsset(structuredClone(value));onOpenPage?.("14");}} parseAsset={parseAiAsset} parseGrant={parseAssetGrant} packetCommand={prepareAssetPacket} onOpenReference={onOpenReference}/>
   {slot==="corrected"?<p>为纠正知识 {proposedKnowledge} 明确建立独立复测授权；原回答授权保留。</p>:null}
   <CanonicalContextSpace initialLearningItemKey={slot==="original"?initialLearningItemKey:undefined} proposedKnowledgeId={proposedKnowledge} onKnowledgeBound={setBoundKnowledge} onOpenReference={onOpenReference} onUse={(value,grant)=>{if(boundKnowledge&&grant.knowledge_id!==boundKnowledge){setError("所选上下文不是当前旅程指定知识的授权；请核对原对象。");return;}if(slot==="corrected"){if(!grant.operations.includes("retest")){setError("此授权未明确允许复测；不会复用原回答授权。");return;}setCorrected(value);}else setOriginal(value);setError(null);onOpenPage?.("14");}}/>
   {error?<p role="alert">{error}</p>:null}
  </div>:null}
  {(visited.has("14")||pageId==="14")?<div hidden={pageId!=="14"}><CanonicalAiJourneySpace initialConsumption={original} initialRetestConsumption={corrected} initialAssetConsumption={asset} onOpenContext={openContext} onTask={setTaskId} onOpenReceipts={id=>{setTaskId(id);onOpenPage?.("22");}}/></div>:null}
  {(visited.has("22")||pageId==="22")?<div hidden={pageId!=="22"}><CanonicalMachineReceiptsSpace initialTaskId={taskId}/><button onClick={()=>onOpenPage?.("14")}>返回同一纠正与复测旅程</button></div>:null}
 </>;
}
