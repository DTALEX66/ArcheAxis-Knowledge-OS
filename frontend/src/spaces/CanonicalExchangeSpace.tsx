import { useCallback, useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import type { DocumentDto, DocumentExportDto, DocumentsListDto, OriginalDto, SourceDto, SourcesListDto } from "../api/generated/core-contract";
import { FolderIngest } from "../components/FolderIngest";
import { JobContent } from "../components/JobContent";
import type { ObjectTrailLevel } from "../components/NavTrail";
import { CanonicalTeachingSpace } from "./CanonicalTeachingSpace";
import { downloadBytes, object, pinnedDocument, sameValue, verifiedExport, verifiedOriginal } from "../presentation/exchangeProof";
import "./exchange.css";

type Tab="originals"|"documents"|"teaching"|"qualification";
const tabs:readonly [Tab,string][]=[["originals","原件与转换"],["documents","文档导出"],["teaching","人工教学交换"],["qualification","互通资格"]];
type OriginalSelection={source:SourceDto; original:OriginalDto; bytes:Uint8Array; jobId?:string};
const reason=(error:unknown)=>error instanceof Error?error.message:"UNKNOWN：未获得可核验回执。";
const interoperability=[
  ["功能等价","PARTIAL","当前页可定位原件、读取转换产物与导出快照；各格式正文、结构、定位、损失和引擎仍需分别验收。"],
  ["数据兼容","PARTIAL","原件经身份与字节 SHA256 核验后下载；完整文档快照保留在 manifest.json。全格式、全平台、正式旧库未知字段无损资格未在本页证明。"],
  ["双向往返","PARTIAL","教学记录具备人工 JSON 预检与导入闭环；文档 Markdown / Obsidian 导出不代表外部软件往返无损。没有自动发送 peer。"],
  ["增量同步","NOT_EXECUTED","本页未接入外部双向增量同步。不会将导出、重复导入回执或人工交换包装为同步成功。"],
] as const;

/** Read-only source/document inspection plus existing canonical import and teaching actions. */
export function CanonicalExchangeSpace({initialDocumentId,onOpenDocument,onOpenPage,onTrail}:{initialDocumentId?:string;onOpenDocument?:(id:string)=>void;onOpenPage?:(id:string)=>void;onTrail?:(levels:readonly ObjectTrailLevel[])=>void}) {
  const [tab,setTab]=useState<Tab>(initialDocumentId?"documents":"originals"),tabRef=useRef(tab);tabRef.current=tab;
  const [sources,setSources]=useState<SourceDto[]>([]),[sourcesLoaded,setSourcesLoaded]=useState(false),[sourceListError,setSourceListError]=useState<string|null>(null);
  const [sourceFilter,setSourceFilter]=useState(""),[sourceId,setSourceId]=useState("");
  const [original,setOriginal]=useState<OriginalSelection|null>(null),[sourceBusy,setSourceBusy]=useState(false),[sourceError,setSourceError]=useState<string|null>(null),[sourceMessage,setSourceMessage]=useState("");
  const [documents,setDocuments]=useState<DocumentsListDto["documents"]>([]),[cursor,setCursor]=useState<string|null>(null),[count,setCount]=useState<number|null>(null),[docsLoaded,setDocsLoaded]=useState(false),[docsBusy,setDocsBusy]=useState(false),[docsError,setDocsError]=useState<string|null>(null);
  const [documentId,setDocumentId]=useState(initialDocumentId??""),[saved,setSaved]=useState<DocumentDto|null>(null),[documentBusy,setDocumentBusy]=useState(false),[documentError,setDocumentError]=useState<string|null>(null),[documentMessage,setDocumentMessage]=useState("");
  const [format,setFormat]=useState<"markdown"|"obsidian">("markdown"),[proof,setProof]=useState<DocumentExportDto|null>(null);
  const mounted=useRef(true),sourceEpoch=useRef(0),sourceListEpoch=useRef(0),documentEpoch=useRef(0),docListEpoch=useRef(0),docListLock=useRef(false),exportLock=useRef(false),seenCursors=useRef(new Set<string>()),snapshotCount=useRef<number|null>(null),docRows=useRef<DocumentsListDto["documents"]>([]);
  const currentSource=(epoch:number)=>mounted.current&&sourceEpoch.current===epoch;
  const currentDocument=(epoch:number)=>mounted.current&&documentEpoch.current===epoch;
  const teachingTrail=useCallback((levels:readonly ObjectTrailLevel[])=>{if(tabRef.current==="teaching")onTrail?.(levels);},[onTrail]);
  async function refreshSources() {
    const epoch=++sourceListEpoch.current;setSourceListError(null);
    try{const value=await coreCommand<SourcesListDto>("sources_list");
      if(!Array.isArray(value.sources)||new Set(value.sources.map(s=>s.source_id)).size!==value.sources.length)throw new Error("原件目录身份重复或不完整。");
      if(mounted.current&&epoch===sourceListEpoch.current){setSources(value.sources);setSourcesLoaded(true);}
    }catch(error){if(mounted.current&&epoch===sourceListEpoch.current){setSourceListError(reason(error));setSourcesLoaded(false);}}
  }
  async function loadDocuments(next?:string) {
    if(docListLock.current)return;docListLock.current=true;setDocsBusy(true);setDocsError(null);const epoch=++docListEpoch.current;
    try{const value=await coreCommand<DocumentsListDto>("documents_list",next?{cursor:next}:{});
      if(!Array.isArray(value.documents)||value.documents.length>500||!Number.isSafeInteger(value.snapshot_count)||value.snapshot_count<0||!(value.next_cursor===null||typeof value.next_cursor==="string")||new Set(value.documents.map(d=>d.document_id)).size!==value.documents.length)throw new Error("文档分页回执不完整。");
      if(next&&(snapshotCount.current!==value.snapshot_count||value.next_cursor===next||value.next_cursor!==null&&seenCursors.current.has(value.next_cursor)))throw new Error("分页身份或游标变化；保留已读页面，请刷新目录。");
      const previous=next?docRows.current:[];
      if(next&&value.documents.some(row=>previous.some(old=>old.document_id===row.document_id)))throw new Error("跨页文档身份重复；保留已读页面与原游标。");
      const combined=[...previous,...value.documents];
      if(value.next_cursor!==null&&(value.documents.length===0||combined.length>=value.snapshot_count)||combined.length>value.snapshot_count||value.next_cursor===null&&combined.length!==value.snapshot_count)throw new Error("分页数量或末页快照总数不一致；保留已读页面与原游标。");
      if(!mounted.current||epoch!==docListEpoch.current)return;
      if(!next){seenCursors.current.clear();snapshotCount.current=value.snapshot_count;}else seenCursors.current.add(next);
      docRows.current=combined;setDocuments(combined);
      setCursor(value.next_cursor);setCount(value.snapshot_count);setDocsLoaded(true);
    }catch(error){if(mounted.current&&epoch===docListEpoch.current)setDocsError(reason(error));}
    finally{if(epoch===docListEpoch.current){docListLock.current=false;if(mounted.current)setDocsBusy(false);}}
  }
  async function openSource(id:string,jobId?:string) {
    const epoch=++sourceEpoch.current;setTab("originals");setSourceId(id);setOriginal(null);setSourceError(null);setSourceMessage("");setSourceBusy(true);
    try{
      // Read the exact canonical identity, not a filename or the first recent job.
      const listing=await coreCommand<SourcesListDto>("sources_list");const matches=listing.sources.filter(row=>row.source_id===id);
      if(matches.length!==1)throw new Error("原件目录未唯一确认所选 source_id；不会替换为同名原件。请保留批量回执核对。");
      const source=matches[0],value=await coreCommand<OriginalDto>("source_original",{source_id:id});const bytes=await verifiedOriginal(source,value);
      if(!currentSource(epoch))return;
      setOriginal({source,original:value,bytes,jobId});setSourceMessage("原件身份与实际字节 SHA256 已核验。转换状态另读，原件保存不等同转换成功。");
    }catch(error){if(currentSource(epoch))setSourceError(reason(error));}
    finally{if(currentSource(epoch))setSourceBusy(false);}
  }
  async function openDocument(id:string) {
    if(exportLock.current)return;const epoch=++documentEpoch.current;setDocumentId(id);setSaved(null);setProof(null);setDocumentError(null);setDocumentMessage("");setDocumentBusy(true);
    try{const value=pinnedDocument(await coreCommand<DocumentDto>("document_get",{document_id:id}),id);if(currentDocument(epoch)){setSaved(value);setDocumentMessage("已读取当前持久化版本；本页不导出未保存草稿或历史查看版本。");}}
    catch(error){if(currentDocument(epoch))setDocumentError(reason(error));}finally{if(currentDocument(epoch))setDocumentBusy(false);}
  }
  async function prepareExport() {
    if(exportLock.current||!saved)return;exportLock.current=true;setDocumentBusy(true);setDocumentError(null);setProof(null);const epoch=documentEpoch.current,target=saved,targetFormat=format;
    try{
      const before=pinnedDocument(await coreCommand<DocumentDto>("document_get",{document_id:target.document_id}),target.document_id);
      if(!sameValue(before,target))throw new Error("已保存文档版本变化；请重新读取后审阅导出范围。");
      const result=await verifiedExport(target,await coreCommand<DocumentExportDto>("document_export",{document_id:target.document_id,format:targetFormat}),targetFormat);
      const after=pinnedDocument(await coreCommand<DocumentDto>("document_get",{document_id:target.document_id}),target.document_id);
      if(!sameValue(after,target))throw new Error("导出期间当前版本变化；未确认当前范围，完整快照不会作为成功发布。");
      if(currentDocument(epoch)){setProof(result);setDocumentMessage("Core 两文件投影已核验。请分别下载正文与完整快照；媒体为引用，不是全媒体恢复包。");}
    }catch(error){if(currentDocument(epoch))setDocumentError(reason(error));}
    finally{exportLock.current=false;if(currentDocument(epoch))setDocumentBusy(false);}
  }
  function downloadOriginal(){if(!original)return;try{downloadBytes(original.bytes,original.original.name,original.original.media_type);setSourceMessage("已请求浏览器下载核验原字节；磁盘落地未读回。转换正文未替代原件。");}catch(error){setSourceError(reason(error));}}
  function downloadFile(path:"document.md"|"manifest.json") {if(!proof)return;const file=proof.files.find(f=>f.path===path);if(!file)return;try{downloadBytes(file.content,`${proof.document_id}-v${proof.version}-${path}`,file.media_type);setDocumentMessage(`已请求浏览器下载 ${path}；磁盘落地未读回。请保留同版本的两个文件。`);}catch(error){setDocumentError(reason(error));}}
  useEffect(()=>{mounted.current=true;void refreshSources();void loadDocuments();return()=>{mounted.current=false;sourceEpoch.current++;sourceListEpoch.current++;documentEpoch.current++;docListEpoch.current++;docListLock.current=false;};},[]);
  useEffect(()=>{if(initialDocumentId){setTab("documents");void openDocument(initialDocumentId);}},[initialDocumentId]);
  useEffect(()=>{if(tab==="teaching")return;onTrail?.(tab==="originals"&&original?[{id:`source:${original.source.source_id}`,label:original.original.name,region:"exchange-original",detail:original.jobId??"原件"}]:tab==="documents"&&saved?[{id:`document:${saved.document_id}`,label:saved.title,region:"exchange-export",detail:`已保存 v${saved.version}`}]:[]);},[tab,original,saved,onTrail]);
  return <section className="ui-exchange-page" aria-label="导入、导出与互通">
    <header className="exchange-header"><div><h2>导入、导出与互通</h2><p>原件、转换产物、已保存文档与人工交换分别核对。</p></div><span>本地工作区 · 人工选择</span></header>
    <nav className="exchange-tabs" aria-label="导入导出区域">{tabs.map(([id,label])=><button key={id} aria-pressed={tab===id} onClick={()=>setTab(id)}>{label}</button>)}</nav>
    {/* Keep sessions mounted across tabs; theme updates never key or recreate an editor. */}
    <section hidden={tab!=="originals"} aria-label="原件与转换" id="exchange-original">
      <section className="exchange-card"><h3>导入用户选择的原件</h3><p>逐项保留原件与执行回执；部分成功、失败、取消分别显示。仅重试失败／取消项时使用新执行请求，未知回执先核对。</p><FolderIngest onOpenSource={(id,job)=>void openSource(id,job)}/></section>
      <div className="exchange-columns"><section className="exchange-card"><h3>原件目录</h3><button onClick={()=>void refreshSources()}>刷新原件目录</button>{sourceListError?<p role="alert">目录读取失败：{sourceListError}。保留旧目录，不表示空库。</p>:null}{!sourcesLoaded&&!sourceListError?<p role="status">正在读取原件目录…</p>:null}
        <label>筛选已读原件<input value={sourceFilter} onChange={e=>setSourceFilter(e.target.value)}/></label><ul className="exchange-object-list">{sources.filter(s=>`${s.original_name} ${s.source_id}`.includes(sourceFilter)).map(s=><li key={s.source_id}><button aria-pressed={original?.source.source_id===s.source_id} onClick={()=>void openSource(s.source_id)}>{s.original_name}<small>{s.source_id}</small></button></li>)}</ul>
        {sourcesLoaded&&!sources.length?<p>当前返回目录没有原件。</p>:null}<form onSubmit={e=>{e.preventDefault();if(sourceId.trim())void openSource(sourceId.trim());}}><label>按实际 source_id 定位<input value={sourceId} onChange={e=>setSourceId(e.target.value)}/></label><button disabled={!sourceId.trim()}>读取所选原件</button></form><p>目录没有分页合同；未返回的身份不能当成不存在或改用同名文件。</p>
      </section><section className="exchange-card" aria-label="原件及转换详情">{sourceBusy?<p role="status">读取与核验所选原件…</p>:null}{sourceError?<p role="alert">原件未核验：{sourceError}</p>:null}{sourceMessage?<p role="status">{sourceMessage}</p>:null}
        {original?<><h3>{original.original.name}</h3><dl><dt>原件身份</dt><dd>{original.source.source_id}</dd><dt>原始版本</dt><dd>{original.source.source_revision}</dd><dt>SHA256</dt><dd>{original.source.sha256}</dd><dt>实际字节</dt><dd>{original.bytes.byteLength}</dd><dt>转换作业</dt><dd>{original.jobId??"未指定；读取当前原件的实际作业列表"}</dd></dl><button onClick={downloadOriginal}>下载核验原字节</button><h3>派生正文、结构、定位与损失</h3><p>实际引擎与执行状态以 Core 回执为准；失败不会换成其他成功作业。</p><JobContent sourceId={original.source.source_id} sourceRevision={original.source.source_revision} name={original.original.name} pinnedJobId={original.jobId} readOnly/></>:!sourceBusy&&!sourceError?<p>从目录或批量结果选择原件，右侧分别读取原字节与转换产物。</p>:null}
      </section></div>
    </section>
    <section hidden={tab!=="documents"} aria-label="文档导出" id="exchange-export"><div className="exchange-columns"><section className="exchange-card"><h3>选择已保存文档</h3><button disabled={docsBusy} onClick={()=>void loadDocuments()}>刷新文档目录</button>{docsError?<p role="alert">文档目录读取失败：{docsError}。保留已读页面和游标。</p>:null}{docsBusy?<p role="status">正在读取文档页面…</p>:null}<p>已读 {documents.length} / {count??"UNKNOWN"}</p><ul className="exchange-object-list">{documents.map(d=><li key={d.document_id}><button disabled={documentBusy} aria-pressed={saved?.document_id===d.document_id} onClick={()=>void openDocument(d.document_id)}>{d.title}<small>v{d.version} · {d.document_id}</small></button></li>)}</ul>{cursor?<button disabled={docsBusy} onClick={()=>void loadDocuments(cursor)}>加载更多文档</button>:null}{docsLoaded&&!documents.length?<p>当前快照没有文档。</p>:null}<form onSubmit={e=>{e.preventDefault();if(documentId.trim())void openDocument(documentId.trim());}}><label>按 document_id 定位<input disabled={documentBusy} value={documentId} onChange={e=>setDocumentId(e.target.value)}/></label><button disabled={documentBusy||!documentId.trim()}>读取已保存文档</button></form></section>
      <section className="exchange-card" aria-label="导出范围审阅"><h3>审阅导出范围</h3>{documentBusy?<p role="status">读取或核验当前已保存版本…</p>:null}{documentError?<p role="alert">导出未确认：{documentError}</p>:null}{documentMessage?<p role="status">{documentMessage}</p>:null}{saved?<><h4>{saved.title}</h4><dl><dt>实际身份 / 版本</dt><dd>{saved.document_id} / v{saved.version}</dd><dt>内容 SHA256</dt><dd>{saved.content_sha256}</dd><dt>来源身份 / 版本</dt><dd>{saved.source_id??"无绑定原件"} / {saved.source_revision??"无原件版本"}</dd></dl><p className="exchange-projection">{saved.text_projection}</p><label>投影格式<select disabled={documentBusy} value={format} onChange={e=>{setFormat(e.target.value as "markdown"|"obsidian");setProof(null);setDocumentMessage("");}}><option value="markdown">Markdown</option><option value="obsidian">Obsidian Markdown + 身份头</option></select></label><button disabled={documentBusy} onClick={()=>void prepareExport()}>核验两文件导出</button>{onOpenDocument?<button disabled={documentBusy} onClick={()=>onOpenDocument(saved.document_id)}>打开文档继续编辑</button>:null}
      {proof?<section aria-label="核验导出结果"><p>已核验 {proof.document_id} · v{proof.version} · {proof.format}</p><button onClick={()=>downloadFile("document.md")}>下载 document.md</button><button onClick={()=>downloadFile("manifest.json")}>下载完整 manifest.json</button><h4>Core 损失说明</h4><ul>{(object(JSON.parse(proof.files.find(f=>f.path==="manifest.json")!.content)).loss as unknown[]).map((v,i)=><li key={i}>{String(object(v).code)}：{String(object(v).message)}</li>)}</ul></section>:null}<p>完整快照包含结构、未知节点及属性、证据位置与损失。Markdown 是派生投影；媒体只保留引用，不打包 CAS 原字节。不是完整恢复或外部双向同步。</p></>:!documentBusy?<p>先读取真实文档及当前版本，再核验导出；未保存草稿须回文档保存。</p>:null}</section></div></section>
    <section hidden={tab!=="teaching"} aria-label="人工教学交换"><h3>人工教学交换</h3><p>用户选择文件 → Core 预检 → 明确审阅确认 → 实际导入。授权记录可导出 JSON；不是自动 peer 同步。</p><CanonicalTeachingSpace pageId="16" onOpenPage={onOpenPage} onTrail={teachingTrail}/></section>
    <section hidden={tab!=="qualification"} aria-label="四类互通资格"><h3>分别核验四类互通目标</h3><div className="exchange-qualification">{interoperability.map(([name,status,detail])=><article className="exchange-card" key={name}><h4>{name}</h4><strong>{status}</strong><p>{detail}</p></article>)}</div><p>原始格式矩阵、当前 profile、适配器许可、实际安装、正式旧库迁移及回滚证据须分别提供。本页不读取正式旧库或私人来源，也不根据扩展名或模拟截图宣称资格达成。</p></section>
  </section>;
}
