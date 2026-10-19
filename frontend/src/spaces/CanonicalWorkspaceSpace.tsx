import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import type { DocumentSummaryDto, LearningItemsDto } from "../api/generated/core-contract";
import { coreFailureReason } from "../presentation/labels";
import type { SpaceId } from "./spaces";
import { LocalDocumentSearch } from "../components/LocalDocumentSearch";
import { workspaceReviews } from "../presentation/workspaceReview";
import {learningTitle} from "../presentation/learningTitle";
import { AaosIcon } from "../components/AaosIcon";
import { BrandHeader } from "../components/BrandHeader";
import {ConversationPanel} from "../components/ConversationPanel";
import "../styles/workspace-enhanced.css";
export function CanonicalWorkspaceSpace({onNavigate,onOpenDocument,onReviewItem}:{onNavigate:(space:SpaceId)=>void;onOpenDocument?:(id:string)=>void;onReviewItem?:(key:string)=>void}) {
  const searchOptions = useRef<HTMLDetailsElement>(null);
  const [documents,setDocuments] = useState<DocumentSummaryDto[]>([]);
  const [learning,setLearning] = useState<LearningItemsDto["items"]>([]);
  const [state,setState] = useState("正在读取本地工作区…");
  const [failed,setFailed] = useState(false);
  const [retry,setRetry] = useState(0);
  const [clock,setClock] = useState(Date.now);
  useEffect(()=>{
    const timer=window.setInterval(()=>setClock(Date.now()),60_000);
    return()=>window.clearInterval(timer);
  },[]);
  useEffect(()=>{
    let alive=true;
    setState("正在读取本地工作区…");setFailed(false);
    Promise.all([coreCommand<{documents:DocumentSummaryDto[]}>("documents_list"),coreCommand<LearningItemsDto>("learning_items")])
      .then(([docs,items])=>{
        if (!Array.isArray(docs.documents) || !Array.isArray(items.items)) throw new Error("工作区内容结构不兼容");
        if(alive){setDocuments(docs.documents);setLearning(items.items);setState("");}
      })
      .catch(error=>{if(alive){setState(coreFailureReason(error) ?? "本地工作区暂时无法读取，请重试。");setFailed(true);}});
    return()=>{alive=false;};
  },[retry]);
  const reviews=workspaceReviews(learning,clock);
  const empty=!failed&&!state&&documents.length===0&&learning.length===0;
  return <section className={`ui-workspace cabin-workspace${empty?" cabin-workspace-empty":""}`} aria-label="今日工作台">
    <BrandHeader
      title="今日工作台"
      subtitle="导入资料，或先记下一个想法"
      showQuickActions={true}
      onImportFile={() => onNavigate("intake")}
      onNewDocument={() => onNavigate("library")}
    />
    <div className="workspace-start">
      <p className="workspace-top-only workspace-start-label">开始</p>
      <div className="workspace-start-copy">
        <h2>{empty?"从第一份资料开始":"你的知识空间"}</h2>
        <p>导入资料，或先记下一个想法。</p>
      </div>
      <div className="workspace-entry-cards">
        <section className="workspace-entry-card workspace-entry-card-primary"><AaosIcon name="ImportDocument" size={56}/><h3>导入资料</h3><p>文档、图片、音视频</p><button className="primary" onClick={()=>onNavigate("intake")}>导入第一份资料</button></section>
        <section className="workspace-entry-card"><AaosIcon name="Write" size={56}/><h3>新建笔记</h3><p>记录想法，稍后整理</p><button aria-label="新建笔记与阅读" onClick={()=>onNavigate("library")}>新建笔记</button></section>
      </div>
      <div className="workspace-top-only workspace-quick-actions" aria-label="工作台快捷操作">
        <button type="button" aria-label="查找本地文档" onClick={()=>{if(searchOptions.current){searchOptions.current.open=true;searchOptions.current.querySelector<HTMLInputElement>("input[type='search']")?.focus();}}}><AaosIcon name="Source" size={26}/></button>
        <button type="button" aria-label="打开学习空间" onClick={()=>onNavigate("learning")}><AaosIcon name="Review" size={26}/></button>
      </div>
      <p className="workspace-local-note"><AaosIcon name="Lock" size={20}/>内容保存在本地</p>
    </div>
    <section className="workspace-top-only workspace-planet-hero" aria-label="开始使用知识空间">
      <div><h2>你的知识空间</h2><p>从一份资料，或一个想法开始。</p><button type="button" onClick={()=>onNavigate("intake")}>开始使用<span aria-hidden="true"> →</span></button></div>
    </section>
    <details className="companion-home"><summary>与小栖继续会话</summary><ConversationPanel slot="home"/></details>
    <details ref={searchOptions} className="workspace-search-options"><summary>搜索本地文档</summary><LocalDocumentSearch onOpenDocument={onOpenDocument}/></details>
    {state?<p role={failed?"alert":"status"}>{state}</p>:null}
    {failed?<button onClick={()=>setRetry(value=>value+1)}>重新读取工作区</button>:null}
    {!failed&&!state&&!empty?<><div className="ui-workspace-grid">
      <section data-section="documents" tabIndex={-1}><div className="workspace-section-heading"><AaosIcon name="Source"/><h2>继续阅读与编辑</h2></div><p>本地已保存文档。列表不代表最近编辑排序。</p>{documents.length?<ul>{documents.slice(0,8).map(document=><li key={document.document_id}><button onClick={()=>onOpenDocument?.(document.document_id)}>{document.title} · v{document.version}</button><small>{document.source_id?"关联来源原件":"原创文档 · 未绑定来源"}</small></li>)}</ul>:<div className="workspace-empty"><AaosIcon name="Knowledge" size={28}/><p>还没有已保存文档，可从新建笔记开始。</p></div>}</section>
      <section data-section="review" tabIndex={-1}><div className="workspace-section-heading"><AaosIcon name="Review"/><h2>到期复习</h2></div><p>{reviews.due.length} 个已到期 · {reviews.unscheduled} 个未安排 · {reviews.unverified} 个日期待核实</p>
        {reviews.due.length?<ul>{reviews.due.slice(0,8).map(item=><li key={item.item_key}><button data-learning-item-key={item.item_key} disabled={!onReviewItem} onClick={()=>onReviewItem?.(item.item_key)}>{learningTitle(item.display_title)}</button><small>到期 {item.next_review}（UTC）</small></li>)}</ul>:<p>{learning.length?"当前没有已核实的到期复习。":"当前没有本地学习条目。"}</p>}
        {reviews.due.length>8?<p>先显示最早到期的 8 个，全部条目可进入学习查看。</p>:null}<button onClick={()=>onNavigate("learning")}>查看全部学习条目</button>
      </section>
    </div></>:null}
  </section>;
}
