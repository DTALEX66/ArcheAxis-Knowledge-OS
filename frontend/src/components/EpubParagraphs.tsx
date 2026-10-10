import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import type { AnchorDto } from "../api/generated/core-contract";
import { utf8Sha256 } from "./TranscriptionCues";
import { Section } from "./RealData";

export type EpubPosition = {type:"epub";job_id:string;attempt:number;result_sha256:string;path:string;chapter:number;paragraph:number};
export type EpubProof = {sourceId:string;revision:string;jobId:string;attempt:number;resultSha256:string;locations:Array<{kind:string;path:string;chapter:number;paragraph:number;value:string}>};
export async function epubProof(sourceId:string,revision:string|undefined,jobId:string,state:Record<string,unknown>,loss:Record<string,unknown>,sourceJob:Record<string,unknown>):Promise<EpubProof>{
 if(!revision||!/^[a-f0-9]{64}$/i.test(revision)||state.job_id!==jobId||state.input_ref!==sourceId||state.state!=="succeeded"||!Number.isSafeInteger(state.attempt)||Number(state.attempt)<1||typeof loss.content!=="string")throw new Error("EPUB identity mismatch");
 if(sourceJob.job_id!==jobId||sourceJob.input_ref!==sourceId||sourceJob.kind!=="text"||sourceJob.state!=="succeeded"||sourceJob.attempt!==state.attempt)throw new Error("EPUB source job mismatch");
 const meta=loss.metadata as Record<string,unknown>;
 if(!meta||meta.kind!=="loss_report"||meta.sha256!==await utf8Sha256(loss.content)||meta.byte_length!==new TextEncoder().encode(loss.content).byteLength)throw new Error("EPUB digest mismatch");
 const format=JSON.parse(loss.content)?.params?.format;
 if(format?.format!=="epub"||format.parsed!==true||!Array.isArray(format.locations)||format.locations.length===0||format.locations.length>10000)throw new Error("EPUB locations missing or over budget");
 const keys=new Set<string>();
 for(const row of format.locations){
  if(row.kind!=="epub_chapter_paragraph"||typeof row.path!=="string"||!row.path||row.path.startsWith("/")||row.path.includes("\\")||row.path.includes(":")||row.path.split("/").includes("..")||!Number.isSafeInteger(row.chapter)||row.chapter<1||!Number.isSafeInteger(row.paragraph)||row.paragraph<1||typeof row.value!=="string"||!row.value)throw new Error("EPUB location invalid");
  const key=JSON.stringify([row.path,row.chapter,row.paragraph]);if(keys.has(key))throw new Error("EPUB duplicate location");keys.add(key);
 }
 return {sourceId,revision,jobId,attempt:Number(state.attempt),resultSha256:String(meta.sha256),locations:format.locations};
}
export function EpubParagraphs({proof,seek,onSeek,onAnchor}:{proof:EpubProof;seek?:EpubPosition;onSeek?:(position:EpubPosition)=>void;onAnchor?:(anchor:AnchorDto)=>void}){
 const [page,setPage]=useState(0),[message,setMessage]=useState(""),[busy,setBusy]=useState(false),[focused,setFocused]=useState<number|null>(null);
 const epoch=useRef(0),nodes=useRef(new Map<number,HTMLParagraphElement>());
 useEffect(()=>{epoch.current++;setPage(0);setFocused(null);setMessage("");setBusy(false);return()=>{epoch.current++;};},[proof]);
 useEffect(()=>{
  if(!seek)return;
  if(seek.job_id!==proof.jobId||seek.attempt!==proof.attempt||seek.result_sha256!==proof.resultSha256){setMessage("引用属于另一成功解析回执，未自动迁移定位。");return;}
  const index=proof.locations.findIndex(row=>row.path===seek.path&&row.chapter===seek.chapter&&row.paragraph===seek.paragraph);
  if(index<0){setMessage("引用段落不在此回执中，保留原引用。");return;}
  setPage(Math.floor(index/30));setFocused(index);
 },[seek,proof]);
 useEffect(()=>{if(focused!==null){nodes.current.get(focused)?.focus();nodes.current.get(focused)?.scrollIntoView?.({block:"nearest"});}},[focused,page]);
 function position(index:number):EpubPosition{const row=proof.locations[index];return {type:"epub",job_id:proof.jobId,attempt:proof.attempt,result_sha256:proof.resultSha256,path:row.path,chapter:row.chapter,paragraph:row.paragraph};}
 async function cite(index:number){
  if(busy)return;const generation=epoch.current;setBusy(true);
  try{
   const locator=position(index),checksum=await utf8Sha256(proof.locations[index].value);if(generation!==epoch.current)return;
   const anchor=await coreCommand<AnchorDto>("anchor_create",{source_id:proof.sourceId,body:{revision:proof.revision,position:JSON.stringify(locator),checksum}});
   if(generation!==epoch.current)return;const actual=JSON.parse(anchor.position);
   if(!anchor.anchor_id||anchor.source_id!==proof.sourceId||anchor.source_revision!==proof.revision||anchor.location_status!=="located"||actual.checksum!==checksum||Object.entries(locator).some(([key,value])=>actual[key]!==value))throw new Error("EPUB anchor mismatch");
   onAnchor?.(anchor);setMessage("段落与解析回执关联已校验；不等同原件视觉布局或内容正确性认可。");
  }catch{if(generation===epoch.current)setMessage("EPUB 段落引用未确认。");}finally{if(generation===epoch.current)setBusy(false);}
 }
 return <Section title="EPUB 章节段落"><p>成功任务 {proof.jobId} / 尝试 {proof.attempt} 的正文；CSS、分页和图片布局未渲染。</p>{proof.locations.slice(page*30,(page+1)*30).map((row,offset)=>{const index=page*30+offset;return <div key={JSON.stringify([row.path,row.chapter,row.paragraph])}><p>第 {row.chapter} 章 / 段落 {row.paragraph} · {row.path}</p><p tabIndex={-1} data-epub-focused={focused===index} ref={node=>{if(node)nodes.current.set(index,node);else nodes.current.delete(index);}}>{row.value}</p>{onSeek?<button onClick={()=>onSeek(position(index))}>定位 EPUB 段落</button>:null}<button disabled={busy} onClick={()=>void cite(index)}>引用 EPUB 段落</button></div>;})}{proof.locations.length>30?<nav aria-label="EPUB 段落分页"><button disabled={!page} onClick={()=>setPage(value=>value-1)}>上一组段落</button><button disabled={(page+1)*30>=proof.locations.length} onClick={()=>setPage(value=>value+1)}>下一组段落</button></nav>:null}{message?<p role="status">{message}</p>:null}</Section>;
}
