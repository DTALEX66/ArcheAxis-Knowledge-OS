import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import type { DocumentDto, DocumentSummaryDto, DocumentsListDto, SourcesListDto, SourceDto, SearchDto, KnowledgeDto } from "../api/generated/core-contract";
import type { ObjectReference } from "../api/generated/research-contract";
import { failureMessage } from "../presentation/labels";
import { RawReceiptButton } from "./DiagnosticConsole";
export type PickedSnapshot = Pick<DocumentDto,"document_id"|"version"|"content_sha256">;
/** Existing Core object selection; caller chooses what the pinned reference means. */
export function ObjectReferencePicker({ onPick, onSnapshot, onOpenReference, disabled=false }: {
  onPick?: (reference:ObjectReference)=>void; onSnapshot?: (snapshot:PickedSnapshot,document:DocumentDto)=>void;
  onOpenReference?: (reference:ObjectReference)=>void; disabled?:boolean;
}) {
  const [documents,setDocuments]=useState<DocumentSummaryDto[]>([]),[sources,setSources]=useState<SourceDto[]>([]),[cursor,setCursor]=useState<string|null>(null);
  const [query,setQuery]=useState(""),[hits,setHits]=useState<SearchDto["items"]>([]),[doc,setDoc]=useState<DocumentDto|null>(null);
  const [picked,setPicked]=useState<ObjectReference|null>(null),[message,setMessage]=useState<string|null>(null),[busy,setBusy]=useState(false);
  const epoch=useRef(0),mounted=useRef(true),session=useRef(0);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;epoch.current++;session.current++;};},[]);
  useEffect(()=>{session.current++;setPicked(null);setDoc(null);},[disabled]);
  const live=(seq:number)=>mounted.current&&epoch.current===seq;
  async function list(more=false){const seq=++epoch.current;setBusy(true);setMessage(null);
    try{const page=await coreCommand<DocumentsListDto>("documents_list",more&&cursor?{cursor}:{});
      if(new Set(page.documents.map(d=>d.document_id)).size!==page.documents.length||(more&&page.next_cursor===cursor&&cursor!==null))throw new Error("文档分页身份不兼容");
      if(live(seq)){setDocuments(old=>more?[...old,...page.documents.filter(d=>!old.some(x=>x.document_id===d.document_id))]:page.documents);setCursor(page.next_cursor);}}
    catch(reason){if(live(seq))setMessage(failureMessage(reason));}finally{if(live(seq))setBusy(false);}}
  async function readSources(){const seq=++epoch.current;setBusy(true);try{const page=await coreCommand<SourcesListDto>("sources_list");if(live(seq))setSources(page.sources);}catch(reason){if(live(seq))setMessage(failureMessage(reason));}finally{if(live(seq))setBusy(false);}}
  async function search(){const seq=++epoch.current;setBusy(true);try{const page=await coreCommand<SearchDto>("search",{q:query,active_only:false});if(live(seq))setHits(page.items);}catch(reason){if(live(seq))setMessage(failureMessage(reason));}finally{if(live(seq))setBusy(false);}}
  async function chooseDocument(id:string){if(!id){epoch.current++;setBusy(false);setPicked(null);setDoc(null);return;}const seq=++epoch.current,expectedSession=session.current;setBusy(true);setPicked(null);setDoc(null);
    try{const value=await coreCommand<DocumentDto>("document_get",{document_id:id});if(value.document_id!==id)throw new Error("引用文档身份不符");
      if(live(seq)&&expectedSession===session.current&&!disabled){setDoc(value);setPicked({kind:"document",document_id:id,version:value.version,block_id:null});}}
    catch(reason){if(live(seq))setMessage(failureMessage(reason));}finally{if(live(seq))setBusy(false);}}
  async function chooseKnowledge(id:string){const seq=++epoch.current,expectedSession=session.current;setBusy(true);setPicked(null);setDoc(null);
    try{const value=await coreCommand<KnowledgeDto>("knowledge_get",{id});if(value.knowledge_id!==id)throw new Error("引用知识身份不符");if(live(seq)&&expectedSession===session.current&&!disabled)setPicked({kind:"knowledge",knowledge_id:id});}
    catch(reason){if(live(seq))setMessage(failureMessage(reason));}finally{if(live(seq))setBusy(false);}}
  return <section aria-label="选择实际对象引用" className="semantic-panel"><p>从已保存的资料中选择引用。选择不会创建、采用或执行内容；引用始终保留你选定的版本。</p>
    <fieldset disabled={disabled||busy}><legend>已保存资料</legend><button onClick={()=>void list()}>浏览已保存文档</button>{cursor?<button onClick={()=>void list(true)}>更多文档</button>:null}
      <label>选择文档<select value={doc?.document_id??""} onChange={e=>void chooseDocument(e.target.value)}><option value="">尚未选择</option>{documents.map(d=><option key={d.document_id} value={d.document_id}>{d.title} · 第 {d.version} 版</option>)}</select></label>
      {doc?<label>选择文档片段<select value={picked?.kind==="document"?picked.block_id??"":""} onChange={e=>setPicked({kind:"document",document_id:doc.document_id,version:doc.version,block_id:e.target.value||null})}><option value="">完整文档</option>{doc.blocks.map((b,index)=><option key={b.block_id} value={b.block_id}>片段 {index+1} · {b.text_projection.slice(0,100)||"无可显示文字"}</option>)}</select></label>:null}
      {onPick?<><button onClick={()=>void readSources()}>浏览来源原件</button><label>选择来源原件<select value={picked?.kind==="source"?picked.source_id:""} onChange={e=>{const source=sources.find(s=>s.source_id===e.target.value);setDoc(null);setPicked(source?{kind:"source",source_id:source.source_id,sha256:source.sha256}:null);}}><option value="">尚未选择</option>{sources.map(s=><option key={s.source_id} value={s.source_id}>{s.original_name} · {s.source_id.slice(-8)}</option>)}</select></label>
        <label>查找本地知识<input value={query} onChange={e=>setQuery(e.target.value)}/></label><button disabled={!query.trim()} onClick={()=>void search()}>查找知识</button>{hits.map(h=><button key={h.knowledge_id} onClick={()=>void chooseKnowledge(h.knowledge_id)}>{h.head} · {h.knowledge_id.slice(-8)}</button>)}</>:null}
    </fieldset>{busy?<p role="status">正在核对真实对象…</p>:null}{message?<p role="alert">{message}</p>:null}
    {picked?<><p>{picked.kind==="document"?`${doc?.title||"已保存文档"} · 第 ${picked.version} 版 · ${picked.block_id?"已选片段":"全文"}`:picked.kind==="source"?`${sources.find(source=>source.source_id===picked.source_id)?.original_name||"来源原件"} · ${picked.source_id.slice(-8)}`:`${hits.find(hit=>hit.knowledge_id===picked.knowledge_id)?.head||"已保存知识"} · ${picked.knowledge_id.slice(-8)}`}</p><RawReceiptButton label="所选引用完整身份" category="data" payload={picked}/>
      {onOpenReference?<button disabled={busy} onClick={()=>onOpenReference(picked)}>只读查看所选引用</button>:null}
      {onPick?<button disabled={disabled||busy} onClick={()=>{onPick(structuredClone(picked));setPicked(null);setDoc(null);}}>加入此固定引用</button>:null}
      {onSnapshot&&doc?<button disabled={disabled||busy} onClick={()=>{onSnapshot({document_id:doc.document_id,version:doc.version,content_sha256:doc.content_sha256},doc);setPicked(null);setDoc(null);}}>加入此文档版本</button>:null}
    </>:null}
  </section>;
}
