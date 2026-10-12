import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import type { DocumentDto, KnowledgeDto, OriginalDto, SourcesListDto } from "../api/generated/core-contract";
import type { ObjectReference } from "../api/generated/research-contract";
import { MediaReader } from "./MediaReader";
import { RawReceiptButton } from "./DiagnosticConsole";
const PdfReader = lazy(() => import("./PdfReader").then(m => ({ default: m.PdfReader })));
type Original = { dto: OriginalDto; bytes: Uint8Array; text: string | null };
function OriginalView({ value }: { value: Original }) {
  const [url,setUrl]=useState("");const [page,setPage]=useState(1);
  useEffect(()=>{
    if (!["image/png","image/jpeg","image/webp","image/gif"].includes(value.dto.media_type)) return;
    const owned=URL.createObjectURL(new Blob([value.bytes.slice().buffer],{type:value.dto.media_type}));setUrl(owned);
    return()=>URL.revokeObjectURL(owned);
  },[value]);
  const mime=value.dto.media_type;
  return <><p>{value.dto.name} · {mime} · {value.bytes.length} bytes</p><code>{value.dto.sha256}</code>
    {url ? <img src={url} alt={`原件 ${value.dto.name}`} /> : mime==="application/pdf" ? <Suspense fallback={<p role="status">正在加载原件阅读器…</p>}><PdfReader bytes={value.bytes} page={page} onPageChange={setPage}/></Suspense> : ["audio/mpeg","audio/wav","video/mp4","video/webm"].includes(mime) ? <MediaReader bytes={value.bytes} mediaType={mime}/> : value.text!==null ? <pre>{value.text}</pre> : <p>原件已校验；此格式暂无内嵌阅读器。</p>}
  </>;
}

/** Read-only object jump in the current surface. Never switches a pinned version to current. */
export function PinnedReferencePanel({ reference, onClose, onOpenReference, expectedDocumentSha }: { reference:ObjectReference;onClose:()=>void;onOpenReference?:(reference:ObjectReference)=>void;expectedDocumentSha?:string }) {
  const region=useRef<HTMLElement>(null);
  const selection=useRef(0),sourceLock=useRef(false);
  const [document,setDocument]=useState<DocumentDto|null>(null),[knowledge,setKnowledge]=useState<KnowledgeDto|null>(null),[original,setOriginal]=useState<Original|null>(null);
  const [error,setError]=useState<string|null>(null),[retry,setRetry]=useState(0),[loading,setLoading]=useState(true);
  const [sourceBusy,setSourceBusy]=useState(false),[sourceError,setSourceError]=useState<string|null>(null);
  const identity=JSON.stringify([reference,expectedDocumentSha]);
  useEffect(()=>{region.current?.focus();region.current?.scrollIntoView?.({block:"nearest"});},[identity]);
  useEffect(()=>{
    selection.current++;sourceLock.current=false;setSourceBusy(false);setSourceError(null);
    let alive=true;setLoading(true);setError(null);setDocument(null);setKnowledge(null);setOriginal(null);
    async function load() {
      if (reference.kind==="document") {
        const d=await coreCommand<DocumentDto>("document_version",{document_id:reference.document_id,version:reference.version});
        if(d.document_id!==reference.document_id || d.version!==reference.version) throw new Error("返回对象与固定版本引用不符。");
        if(expectedDocumentSha&&d.content_sha256!==expectedDocumentSha)throw new Error("固定版本指纹与搜索观察不一致；未替换为其他版本。");
        if(reference.block_id && !d.blocks.some(b=>b.block_id===reference.block_id)) throw new Error("此固定版本没有引用的块；未替换为当前版本。");
        if(alive)setDocument(d);
      } else if(reference.kind==="knowledge") {
        const k=await coreCommand<KnowledgeDto>("knowledge_get",{knowledge_id:reference.knowledge_id});
        if(k.knowledge_id!==reference.knowledge_id)throw new Error("知识身份不符。");
        if(alive)setKnowledge(k);
      } else {
        const o=await coreCommand<OriginalDto>("source_original",{source_id:reference.source_id});
        if(o.source_id!==reference.source_id || o.sha256!==reference.sha256)throw new Error("原件身份或 SHA 与引用不符。");
        const bytes=Uint8Array.from(atob(o.content_base64),c=>c.charCodeAt(0));
        const digest=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",bytes))).map(x=>x.toString(16).padStart(2,"0")).join("");
        if(digest!==reference.sha256)throw new Error("原件字节校验失败。");
        let text:string|null=null;
        if(o.media_type.startsWith("text/") || ["application/json","application/xml"].includes(o.media_type)) {
          try{text=new TextDecoder("utf-8",{fatal:true}).decode(bytes);}catch{/* Original remains verified bytes, no fabricated decoding. */}
        }
        if(alive)setOriginal({dto:o,bytes,text});
      }
    }
    load().catch(e=>{if(alive)setError(e instanceof Error?e.message:"引用读取失败。");}).finally(()=>{if(alive)setLoading(false);});
    return()=>{alive=false;selection.current++;};
  },[identity,retry]);
  async function openKnowledgeSource() {
    if(!knowledge?.source_id || !onOpenReference || sourceLock.current)return;
    const generation=selection.current,id=knowledge.source_id;sourceLock.current=true;setSourceBusy(true);setSourceError(null);
    try {
      const list=await coreCommand<SourcesListDto>("sources_list");
      const source=list.sources.find(s=>s.source_id===id);
      if(!source || !/^[a-f0-9]{64}$/.test(source.sha256))throw new Error("知识绑定的来源记录不可用；未换成其他原件。");
      if(selection.current===generation)onOpenReference({kind:"source",source_id:id,sha256:source.sha256});
    } catch(reason) {if(selection.current===generation)setSourceError(reason instanceof Error?reason.message:"来源读取失败。");}
    finally {if(selection.current===generation){sourceLock.current=false;setSourceBusy(false);}}
  }
  return <aside ref={region} tabIndex={-1} className="ui-pinned-reference" aria-label="固定版本引用阅读">
    <header><h2>引用对象</h2><button type="button" onClick={onClose}>关闭引用</button></header>
    <p>此处只读，研究和关系草稿仍保留。</p>
    {loading?<p role="status">正在读取固定引用…</p>:error?<><p role="alert">{error}</p><button type="button" onClick={()=>setRetry(v=>v+1)}>重试引用</button></>:null}
    {document?<><h3>{document.title} · v{document.version}</h3><code>{document.document_id}</code><p>版本 SHA：<code>{document.content_sha256}</code></p>
      {reference.kind==="document" && reference.block_id ? <section aria-label="引用块"><h4>块 {reference.block_id}</h4><pre>{document.blocks.find(b=>b.block_id===reference.block_id)?.text_projection}</pre></section>:<pre>{document.text_projection}</pre>}
      {document.source_id && document.source_revision?<button type="button" disabled={!onOpenReference} onClick={()=>onOpenReference?.({kind:"source",source_id:document.source_id!,sha256:document.source_revision!})}>读取此版本的来源原件</button>:<p>此版本为独立文档，无来源原件绑定。</p>}
      <RawReceiptButton label={`固定文档 ${document.document_id} v${document.version}`} payload={document}/>
    </>:null}
    {knowledge?<><h3>知识 {knowledge.knowledge_id}</h3><p>不可变身份 · {knowledge.version} · {knowledge.status}</p><pre>{knowledge.body}</pre><p>来源：{knowledge.source_id??"无来源绑定"}；锚点：{knowledge.anchor_id??"无锚点"}</p>
      {knowledge.source_id && <button type="button" disabled={sourceBusy || !onOpenReference} onClick={()=>void openKnowledgeSource()}>读取知识绑定的来源原件</button>}
      {sourceBusy && <p role="status">正在核对知识来源身份…</p>}{sourceError && <p role="alert">{sourceError}</p>}
    </>:null}
    {original?<OriginalView value={original}/>:null}
  </aside>;
}
