import {useEffect,useRef,useState} from "react";
import {coreCommand} from "../api/core";
import type {AnchorDto} from "../api/generated/core-contract";
import {originalTextSelection,textareaOriginalRange} from "../presentation/originalTextSelection";

export function OriginalTextCitation({sourceId,revision,bytes,onAnchor}:{sourceId:string;revision:string;bytes:Uint8Array;onAnchor?:(anchor:AnchorDto)=>void}){
 const [range,setRange]=useState({start:0,end:0}),[busy,setBusy]=useState(false),[message,setMessage]=useState("");const epoch=useRef(0);
 useEffect(()=>{epoch.current++;setRange({start:0,end:0});setMessage("");setBusy(false);return()=>{epoch.current++;};},[sourceId,revision,bytes]);
 let text="";try{text=new TextDecoder("utf-8",{fatal:true,ignoreBOM:true}).decode(bytes);}catch{return <p>原件编码未确认为 UTF-8，不能建立文本范围引用；原件仍保留。</p>;}
 function select(area:HTMLTextAreaElement){try{setRange(textareaOriginalRange(text,area.selectionStart,area.selectionEnd));}catch{setRange({start:0,end:0});}setMessage("");}
 async function cite(){if(busy)return;const current=epoch.current;setBusy(true);try{
  const selected=originalTextSelection(bytes,range.start,range.end);
  const digest=await crypto.subtle.digest("SHA-256",selected.bytes.slice().buffer);
  const checksum=Array.from(new Uint8Array(digest),value=>value.toString(16).padStart(2,"0")).join("");if(current!==epoch.current)return;
  const anchor=await coreCommand<AnchorDto>("anchor_create",{source_id:sourceId,body:{revision,position:JSON.stringify({type:"text",start:selected.start,end:selected.end}),checksum}});if(current!==epoch.current)return;
  const position=JSON.parse(anchor.position);
  if(!anchor.anchor_id||anchor.source_id!==sourceId||anchor.source_revision!==revision||anchor.location_status!=="located"||position.type!=="text"||position.start!==selected.start||position.end!==selected.end||position.checksum!==checksum)throw new Error("original citation mismatch");
  const resolved=await coreCommand<Record<string,unknown>>("anchor_resolve",{source_id:sourceId,anchor_id:anchor.anchor_id});if(current!==epoch.current)return;
  if(resolved.status!=="CURRENT"||resolved.source_id!==sourceId||resolved.anchor_id!==anchor.anchor_id||resolved.source_revision!==revision||resolved.current_source_revision!==revision||resolved.scope!=="locator_provenance_only")throw new Error("original resolution mismatch");
  setMessage("所选原件字节范围已引用并解析；不表示内容已证实。");onAnchor?.(anchor);
 }catch{if(current===epoch.current)setMessage("原件范围引用未确认，请保留原件后重试。");}finally{if(current===epoch.current)setBusy(false);}}
 return <section aria-label="原件文本范围引用"><label>选择原件引用文字 <textarea readOnly value={text.replace(/\r\n?/g,"\n")} disabled={busy} onSelect={event=>select(event.currentTarget)} onKeyUp={event=>select(event.currentTarget)} onMouseUp={event=>select(event.currentTarget)}/></label><p>所选原文：{text.slice(range.start,range.end)}</p><button disabled={busy||range.end<=range.start} onClick={()=>void cite()}>引用所选原文</button>{message?<p role="status">{message}</p>:null}</section>;
}
