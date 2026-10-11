import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import { verifiedJobOutput } from "../presentation/jobContentExecution";
import { utf8Sha256 } from "./TranscriptionCues";
import type { AnchorDto } from "../api/generated/core-contract";

export function StructureCitations({sourceId, revision, jobId, kind, onAnchor}:{sourceId:string;revision:string;jobId:string;kind:"worker_structure"|"pdf_line"|"ocr_line"|"format_location";onAnchor?:(anchor:AnchorDto)=>void}) {
 const [busy,setBusy]=useState(false),[message,setMessage]=useState("");const epoch=useRef(0);
 const [ordinal,setOrdinal]=useState("1");
 const [preview,setPreview]=useState<{path:string;content:string;binding:string}|null>(null);
 useEffect(()=>{epoch.current++;setBusy(false);setMessage("");setOrdinal("1");setPreview(null);return()=>{epoch.current++;};},[sourceId,revision,jobId,kind]);
 async function cite(previewOnly=false){
  if(busy)return;const current=epoch.current;setBusy(true);
  try{
   const [state,textRaw,structureRaw,lossRaw]=await Promise.all([coreCommand<Record<string,unknown>>("jobs_get",{job_id:jobId}),coreCommand("job_output",{job_id:jobId,kind:"text"}),coreCommand("job_output",{job_id:jobId,kind:"document_structure"}),coreCommand("job_output",{job_id:jobId,kind:"loss_report"})]);
   const [text,structure,loss]=await Promise.all([verifiedJobOutput(textRaw,"text"),verifiedJobOutput(structureRaw,"document_structure"),verifiedJobOutput(lossRaw,"loss_report")]);
   if(current!==epoch.current)return;
   if(state.job_id!==jobId||state.input_ref!==sourceId||state.state!=="succeeded"||!Number.isSafeInteger(state.attempt)||Number(state.attempt)<1)throw new Error("task identity");
   const entries=kind==="format_location"?JSON.parse(loss.content)?.params?.format?.locations:kind==="worker_structure"?JSON.parse(loss.content)?.params?.worker_structure:JSON.parse(structure.content);
   const chars=Array.from(text.content);
   if(!Array.isArray(entries))throw new Error("structure missing");
   const valid=entries.filter(n=>kind==="format_location"?n&&typeof n.kind==="string"&&typeof n.path==="string"&&n.path&&typeof n.value==="string"&&n.value.trim():n&&typeof n.kind==="string"&&Array.isArray(n.path)&&n.path.length&&Number.isSafeInteger(n.char_start)&&Number.isSafeInteger(n.char_end)&&n.char_start>=0&&n.char_end>n.char_start&&n.char_end<=chars.length&&chars.slice(n.char_start,n.char_end).join("").trim());
   const index=Number(ordinal)-1;if(!Number.isSafeInteger(index)||index<0)throw new Error("invalid selection");
   const node=valid[index];
   if(!node)throw new Error("locatable content missing");
   const checksum=await utf8Sha256(kind==="format_location"?node.value:chars.slice(node.char_start,node.char_end).join(""));
   const position:Record<string,unknown>={type:kind,job_id:jobId,attempt:state.attempt,kind:node.kind,path:node.path};
   if(kind==="pdf_line"||kind==="ocr_line")Object.assign(position,{char_start:node.char_start,char_end:node.char_end,result_sha256:structure.metadata.sha256});
   if(kind==="ocr_line")position.loss_sha256=loss.metadata.sha256;
   if(current!==epoch.current)return;
   const binding=JSON.stringify({position,checksum});
   if(previewOnly){setPreview({path:Array.isArray(node.path)?node.path.join(" / "):node.path,content:kind==="format_location"?node.value:chars.slice(node.char_start,node.char_end).join(""),binding});setMessage("所选位置已读取，尚未保存引用。");return;}
   if(preview&&preview.binding!==binding)throw new Error("preview changed");
   const anchor=await coreCommand<AnchorDto>("anchor_create",{source_id:sourceId,body:{revision,position:JSON.stringify(position),checksum}});
   if(current!==epoch.current)return;
   const saved=JSON.parse(anchor.position);
   if(!anchor.anchor_id||anchor.source_id!==sourceId||anchor.source_revision!==revision||anchor.location_status!=="located"
    ||saved.checksum!==checksum||Object.entries(position).some(([key,value])=>JSON.stringify(saved[key])!==JSON.stringify(value)))throw new Error("anchor identity");
   const resolved=await coreCommand<Record<string,unknown>>("anchor_resolve",{source_id:sourceId,anchor_id:anchor.anchor_id});
   if(current!==epoch.current)return;
   if(resolved.status!=="CURRENT"||resolved.scope!=="locator_provenance_only"||resolved.source_id!==sourceId||resolved.anchor_id!==anchor.anchor_id||resolved.source_revision!==revision||resolved.current_source_revision!==revision)throw new Error("resolution unverified");
   setMessage(`第 ${index+1} 个非空结构位置引用已保存并解析；定位校验不代表内容正确。`);onAnchor?.(anchor);
  }catch{if(current===epoch.current)setMessage("结构位置引用未确认；保留原件和任务结果后重试。");}
  finally{if(current===epoch.current)setBusy(false);}
 }
 return <section aria-label="转换结构引用"><p>选择本次任务中非空结构位置的顺序，原件、任务与尝试由 Core 核对。</p><label>引用位置序号 <input type="number" min="1" step="1" value={ordinal} disabled={busy} onChange={event=>{setOrdinal(event.target.value);setPreview(null);setMessage("");}}/></label><button disabled={busy} onClick={()=>void cite(true)}>预览所选引用</button>{preview?<div aria-label="所选引用预览"><p>{preview.path}</p><pre>{preview.content}</pre><p>尚未保存；引用时再次核对内容。</p></div>:null}<button disabled={busy} onClick={()=>void cite()}>引用所选结构位置</button>{message?<p role="status">{message}</p>:null}</section>;
}
