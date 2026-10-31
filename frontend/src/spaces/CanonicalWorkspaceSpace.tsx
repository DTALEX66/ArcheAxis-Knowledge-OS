import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import type { DocumentSummaryDto, LearningItemsDto } from "../api/generated/core-contract";
import { coreFailureReason } from "../presentation/labels";
import type { SpaceId } from "./spaces";
import { LocalDocumentSearch } from "../components/LocalDocumentSearch";
import { workspaceReviews } from "../presentation/workspaceReview";
import { learningTitle } from "../presentation/learningTitle";
import { AaosIcon } from "../components/AaosIcon";
import "./stitch-workbench.css";

/** Stitch workbench presentation; existing Core readbacks remain the only source. */
export function CanonicalWorkspaceSpace({ onNavigate, onOpenDocument, onReviewItem }: {
  onNavigate: (space: SpaceId) => void;
  onOpenDocument?: (id: string) => void;
  onReviewItem?: (key: string) => void;
}) {
  const searchOptions = useRef<HTMLDetailsElement>(null);
  const [documents, setDocuments] = useState<DocumentSummaryDto[]>([]);
  const [learning, setLearning] = useState<LearningItemsDto["items"]>([]);
  const [state, setState] = useState("正在读取本地工作区…");
  const [failed, setFailed] = useState(false);
  const [retry, setRetry] = useState(0);
  const [clock, setClock] = useState(Date.now);
  useEffect(() => {
    const timer = window.setInterval(() => setClock(Date.now()), 60_000);
    return () => window.clearInterval(timer);
  }, []);
  useEffect(() => {
    let alive = true;
    setState("正在读取本地工作区…"); setFailed(false);
    Promise.all([
      coreCommand<{ documents: DocumentSummaryDto[] }>("documents_list"),
      coreCommand<LearningItemsDto>("learning_items"),
    ]).then(([docs, items]) => {
      if (!Array.isArray(docs.documents) || !Array.isArray(items.items)) throw new Error("工作区内容结构不兼容");
      if (alive) { setDocuments(docs.documents); setLearning(items.items); setState(""); }
    }).catch(error => {
      if (alive) { setState(coreFailureReason(error) ?? "本地工作区暂时无法读取，请重试。"); setFailed(true); }
    });
    return () => { alive = false; };
  }, [retry]);
  const reviews = workspaceReviews(learning, clock);
  const ready = !failed && !state;
  const empty = ready && documents.length === 0 && learning.length === 0;
  const focusSearch = () => {
    if (!searchOptions.current) return;
    searchOptions.current.open = true;
    searchOptions.current.querySelector<HTMLInputElement>("input[type='search']")?.focus();
  };

  return <section className="stitch-workbench" aria-label="今日工作台内容">
    <header className="stitch-workbench-summary" role="group" aria-label="工作台概览">
      <div className="stitch-workbench-topic">
        <p className="stitch-workbench-eyebrow">工作台 · 本地文档与学习</p>
        <h2>{empty ? "从第一份资料开始" : "今日工作台"}</h2>
        <p>{empty ? "导入资料，或先记下一个想法。" : "继续阅读已保存文档，处理已到期的复习。"}</p>
        <div className="stitch-workbench-actions" aria-label="工作台快捷操作">
          <button type="button" className="stitch-workbench-primary" onClick={() => onNavigate("intake")}><AaosIcon name="ImportDocument" size={16}/>{empty ? "导入第一份资料" : "导入资料"}</button>
          <button type="button" aria-label="新建笔记与阅读" onClick={() => onNavigate("library")}><AaosIcon name="Write" size={16}/>新建笔记</button>
          <button type="button" aria-label="查找本地文档" onClick={focusSearch}><AaosIcon name="Source" size={16}/>查找文档</button>
          <button type="button" aria-label="打开学习空间" onClick={() => onNavigate("learning")}><AaosIcon name="Review" size={16}/>学习</button>
        </div>
      </div>
      <div className="stitch-workbench-local" aria-label="本地工作区">
        <AaosIcon name="Knowledge" size={34}/>
        <span><AaosIcon name="Lock" size={14}/>内容保存在本地</span>
      </div>
    </header>

    <details ref={searchOptions} className="stitch-workbench-search"><summary>搜索本地文档</summary><LocalDocumentSearch onOpenDocument={onOpenDocument}/></details>
    {state ? <div className="stitch-workbench-status"><p role={failed ? "alert" : "status"}>{state}</p>{failed ? <button type="button" onClick={() => setRetry(value => value + 1)}>重新读取工作区</button> : null}</div> : null}
    {empty ? <p className="stitch-workbench-empty">尚无已保存文档或学习条目。导入资料、新建笔记后，再从这里继续。</p> : null}

    {ready && !empty ? <div className="stitch-workbench-grid">
      <section className="stitch-workbench-card" data-section="documents" tabIndex={-1} aria-labelledby="stitch-workbench-documents">
        <header><h2 id="stitch-workbench-documents"><AaosIcon name="Source" size={17}/>继续阅读与编辑</h2><button type="button" onClick={() => onNavigate("library")}>全部资料 →</button></header>
        <p className="stitch-workbench-caption">本地已保存文档。列表不代表最近编辑排序。</p>
        <div className="stitch-workbench-card-content">
          {documents.length ? <ul className="stitch-workbench-objects">{documents.slice(0, 8).map(document => <li key={document.document_id}>
            <button type="button" disabled={!onOpenDocument} onClick={() => onOpenDocument?.(document.document_id)}><span>{document.title} · v{document.version}</span><AaosIcon name="Source" size={15}/></button>
            <small>{document.source_id ? "关联来源原件" : "原创文档 · 未绑定来源"}</small>
          </li>)}</ul> : <p className="stitch-workbench-empty">还没有已保存文档，可从新建笔记开始。</p>}
        </div>
        <footer>本次读取 {documents.length} 个文档{documents.length > 8 ? " · 先显示 8 个" : ""}</footer>
      </section>

      <section className="stitch-workbench-card" data-section="review" tabIndex={-1} aria-labelledby="stitch-workbench-reviews">
        <header><h2 id="stitch-workbench-reviews"><AaosIcon name="Review" size={17}/>到期复习</h2><span className="stitch-workbench-card-kind">我的任务</span></header>
        <p className="stitch-workbench-caption">{reviews.due.length} 个已到期 · {reviews.unscheduled} 个未安排 · {reviews.unverified} 个日期待核实</p>
        <div className="stitch-workbench-card-content">
          {reviews.due.length ? <ul className="stitch-workbench-objects">{reviews.due.slice(0, 8).map(item => <li key={item.item_key}>
            <button type="button" data-learning-item-key={item.item_key} disabled={!onReviewItem} onClick={() => onReviewItem?.(item.item_key)}><span>{learningTitle(item.display_title)}</span><AaosIcon name="Review" size={15}/></button>
            <small>到期 {item.next_review}（UTC）</small>
          </li>)}</ul> : <p className="stitch-workbench-empty">{learning.length ? "当前没有已核实的到期复习。" : "当前没有本地学习条目。"}</p>}
        </div>
        <footer>{reviews.due.length > 8 ? <span>先显示最早到期的 8 个。</span> : null}<button type="button" onClick={() => onNavigate("learning")}>查看全部学习条目 →</button></footer>
      </section>
    </div> : null}
  </section>;
}
