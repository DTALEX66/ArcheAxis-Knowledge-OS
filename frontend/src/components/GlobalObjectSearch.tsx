import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import type { OriginalDto, SearchDto } from "../api/generated/core-contract";
import type { ObjectReference } from "../api/generated/research-contract";
import { coreFailureReason } from "../presentation/labels";

type Result = { key:string;label:string;detail:string;reference?:ObjectReference;sourceId?:string;contentSha?:string };
export function GlobalObjectSearch({query,composing=false,onOpen}:{query:string;composing?:boolean;onOpen:(reference:ObjectReference,contentSha?:string)=>void}) {
  const [results,setResults]=useState<Result[]>([]),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const [searched,setSearched]=useState(false);
  const epoch=useRef(0),composition=useRef(composing);composition.current=composing;
  useEffect(()=>{epoch.current++;setResults([]);setError("");setBusy(false);setSearched(false);},[query]);
  useEffect(()=>()=>{epoch.current++;},[]);
  async function search() {
    if(composition.current)return;
    const value=query.trim(),request=++epoch.current;setResults([]);setError("");setSearched(false);
    if(!value)return;
    if(new TextEncoder().encode(value).length>512){setError("搜索文字超过本地检索长度限制，请缩短后重试。");return;}
    setBusy(true);
    try {
      const data=await coreCommand<SearchDto>("search",{q:value,active_only:false});
      if(!Array.isArray(data.documents)||!Array.isArray(data.items)||!Array.isArray(data.transforms)
        ||data.document_count!==data.documents.length||data.count!==data.items.length||data.transform_count!==data.transforms.length
        ||[data.documents,data.items,data.transforms].some(rows=>rows.length>20)
        ||data.documents.some(row=>typeof row.document_id!=="string"||!row.document_id||typeof row.title!=="string"||typeof row.head!=="string"||!Number.isSafeInteger(row.version)||row.version<1||!/^[a-f0-9]{64}$/.test(row.content_sha256))
        ||data.items.some(row=>typeof row.knowledge_id!=="string"||!row.knowledge_id||typeof row.head!=="string"||typeof row.status!=="string"||typeof row.active!=="boolean")
        ||data.transforms.some(row=>!Number.isSafeInteger(row.transform_id)||row.transform_id<1||typeof row.source_id!=="string"||!row.source_id||typeof row.head!=="string"||typeof row.engine!=="string"))throw new Error("搜索结果身份或数量不兼容。");
      const rows:Result[]=[
        ...data.documents.map(row=>({key:`document:${row.document_id}`,label:`文档 · ${row.title} · v${row.version}`,detail:row.head,contentSha:row.content_sha256,reference:{kind:"document" as const,document_id:row.document_id,version:row.version}})),
        ...data.items.map(row=>({key:`knowledge:${row.knowledge_id}`,label:`知识 · ${row.head}`,detail:`${row.status} · ${row.active?"有效":"非有效"} · ${row.knowledge_id}`,reference:{kind:"knowledge" as const,knowledge_id:row.knowledge_id}})),
        ...data.transforms.map(row=>({key:`transform:${row.transform_id}`,label:`提取文本 · ${row.head}`,detail:`来源 ${row.source_id} · 引擎 ${row.engine} · 提取 ${row.transform_id}；打开原件，未声明精确选区定位。`,sourceId:row.source_id})),
      ];
      if(new Set(rows.map(row=>row.key)).size!==rows.length)throw new Error("搜索结果包含重复身份。");
      if(request===epoch.current){setResults(rows);setSearched(true);}
    } catch(reason){if(request===epoch.current)setError(coreFailureReason(reason)??"本地内容搜索失败，请重试。");}
    finally{if(request===epoch.current)setBusy(false);}
  }
  async function open(row:Result) {
    const request=++epoch.current;setError("");setBusy(true);
    try {
      let reference=row.reference;
      if(!reference) {
        const original=await coreCommand<OriginalDto>("source_original",{source_id:row.sourceId});
        if(original.source_id!==row.sourceId||!/^[a-f0-9]{64}$/.test(original.sha256))throw new Error("原件身份不匹配。");
        reference={kind:"source",source_id:original.source_id,sha256:original.sha256};
      }
      if(request===epoch.current)onOpen(reference,row.contentSha);
    } catch(reason){if(request===epoch.current)setError(coreFailureReason(reason)??"对象打开未完成，请重试。");}
    finally{if(request===epoch.current)setBusy(false);}
  }
  return <section aria-label="全局本地对象搜索"><button type="button" disabled={busy||composing||!query.trim()} onClick={()=>void search()}>搜索本地内容</button>
    <p>按当前文字查找本地文档、知识与提取文本，每类最多 20 项；与 AI 语义检索分开。</p>
    {busy?<p role="status">正在读取本地对象…</p>:null}{error?<p role="alert">{error}</p>:null}
    {searched?<p role="status">{results.length} 个对象结果；单类达到 20 项时请缩小范围。</p>:null}
    <ul aria-label="全局本地对象结果">{results.map(row=><li key={row.key}><button disabled={busy} onClick={()=>void open(row)}>{row.label}</button><small>{row.detail}</small></li>)}</ul>
  </section>;
}
