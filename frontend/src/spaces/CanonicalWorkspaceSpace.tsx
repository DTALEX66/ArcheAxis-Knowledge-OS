import { useEffect, useState } from "react";
import { coreCommand } from "../api/core";
import type { DocumentSummaryDto } from "../api/generated/core-contract";
import { coreFailureReason } from "../presentation/labels";
import type { SpaceId } from "./spaces";
import { LocalDocumentSearch } from "../components/LocalDocumentSearch";
import { workspaceReviews } from "../presentation/workspaceReview";
export function CanonicalWorkspaceSpace({onNavigate,onOpenDocument,onReviewItem}:{onNavigate:(space:SpaceId)=>void;onOpenDocument?:(id:string)=>void;onReviewItem?:(key:string)=>void}) {
  const [documents,setDocuments] = useState<DocumentSummaryDto[]>([]);
  const [learning,setLearning] = useState<{item_key:string;next_review:string|null}[]>([]);
  const [state,setState] = useState("正在读取本地工作区…");
  const [failed,setFailed] = useState(false);
  const [retry,setRetry] = useState(0);
  const [welcomeExpanded,setWelcomeExpanded] = useState(false);
  const [clock,setClock] = useState(Date.now);
  useEffect(()=>{
    const timer=window.setInterval(()=>setClock(Date.now()),60_000);
    return()=>window.clearInterval(timer);
  },[]);
  useEffect(()=>{
    let alive=true;
    setState("正在读取本地工作区…");setFailed(false);
    Promise.all([coreCommand<{documents:DocumentSummaryDto[]}>("documents_list"),coreCommand<{items:{item_key:string;next_review:string|null}[]}>("learning_items")])
      .then(([docs,items])=>{
        if (!Array.isArray(docs.documents) || !Array.isArray(items.items)) throw new Error("工作区内容合同不兼容");
        if(alive){setDocuments(docs.documents);setLearning(items.items);setState("");}
      })
      .catch(error=>{if(alive){setState(coreFailureReason(error) ?? "本地工作区暂时无法读取，请重试。");setFailed(true);}});
    return()=>{alive=false;};
  },[retry]);
  const reviews=workspaceReviews(learning,clock);
  return <section className="ui-workspace" aria-label="今日工作台">
    <div className={`ui-workspace-hero${welcomeExpanded?"":" ui-workspace-hero-compact"}`}><small>ARCHEAXIS KNOWLEDGE</small><h2>{welcomeExpanded?"把知识带回自己的工作区":"今日工作台"}</h2>
      <button aria-expanded={welcomeExpanded} aria-controls="workspace-welcome" onClick={()=>setWelcomeExpanded(value=>!value)}>{welcomeExpanded?"收起欢迎说明":"展开欢迎说明"}</button>
      {welcomeExpanded?<p id="workspace-welcome">从阅读、记录与学习开始。普通笔记无需专业依据即可保存。</p>:null}
    </div>
    <div className="ui-workspace-actions"><button className="primary" onClick={()=>onNavigate("library")}>新建笔记与阅读</button><button onClick={()=>onNavigate("intake")}>导入原件</button><button onClick={()=>onNavigate("settings")}>全部能力与系统</button></div>
    <LocalDocumentSearch onOpenDocument={onOpenDocument}/>
    {state?<p role={failed?"alert":"status"}>{state}</p>:null}
    {failed?<button onClick={()=>setRetry(value=>value+1)}>重新读取工作区</button>:null}
    {!failed&&!state?<div className="ui-workspace-grid">
      <section data-section="documents" tabIndex={-1}><h2>继续阅读与编辑</h2><p>本地已保存文档。列表不代表最近编辑排序。</p>{documents.length?<ul>{documents.slice(0,8).map(document=><li key={document.document_id}><button onClick={()=>onOpenDocument?.(document.document_id)}>{document.title} · v{document.version}</button><small>{document.source_id?"关联来源原件":"原创文档 · 未绑定来源"}</small></li>)}</ul>:<p>还没有已保存文档，可从新建笔记开始。</p>}</section>
      <section data-section="review" tabIndex={-1}><h2>到期复习</h2><p>{reviews.due.length} 个已到期 · {reviews.unscheduled} 个未安排 · {reviews.unverified} 个日期待核实</p>
        {reviews.due.length?<ul>{reviews.due.slice(0,8).map(item=><li key={item.item_key}><button disabled={!onReviewItem} onClick={()=>onReviewItem?.(item.item_key)}>{item.item_key}</button><small>到期 {item.next_review}（UTC）</small></li>)}</ul>:<p>{learning.length?"当前没有已核实的到期复习。":"当前没有本地学习条目。"}</p>}
        {reviews.due.length>8?<p>先显示最早到期的 8 个，全部条目可进入学习查看。</p>:null}<button onClick={()=>onNavigate("learning")}>查看全部学习条目</button>
      </section>
    </div>:null}
  </section>;
}
