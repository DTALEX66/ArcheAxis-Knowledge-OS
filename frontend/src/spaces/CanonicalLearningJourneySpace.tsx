import { lazy, Suspense, useEffect, useLayoutEffect, useRef, useState } from "react";
import { courseLearningTarget } from "../presentation/courseLearningTarget";
import { coreCommand } from "../api/core";
import { coreFailureReason } from "../presentation/labels";
import { KnowledgeCoursePanel } from "../components/KnowledgeCoursePanel";
import { CanonicalLearningSpace } from "./CanonicalLearningSpace";
import { useOptionalCoreWorkingState } from "../presentation/useCoreWorkingState";
import type { ObjectTrailLevel } from "../components/NavTrail";
import "./stitch-learning.css";

type CourseRow = { manifest_id: string; title: string; stale: boolean; status: "candidate"; human_review_required: true };
type KnowledgeRow = { knowledge_id: string; head: string };
const ImportedCoursePanel = lazy(() => import("../components/ImportedCoursePanel").then(module => ({ default: module.ImportedCoursePanel })));
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("invalid learning projection");
  return value as Record<string, unknown>;
}
function coursePage(value: unknown): { items: CourseRow[]; next: string | null } {
  const result = record(value);
  if (!Array.isArray(result.items) || result.items.length > 20 || !(result.next_cursor === null || typeof result.next_cursor === "string")) throw new Error("invalid course page");
  const items = result.items.map(record);
  if (items.some(item => typeof item.manifest_id !== "string" || !item.manifest_id || typeof item.title !== "string"
    || typeof item.stale !== "boolean" || item.status !== "candidate" || item.human_review_required !== true)
    || new Set(items.map(item => item.manifest_id)).size !== items.length) throw new Error("invalid course identity");
  return { items: items as CourseRow[], next: result.next_cursor as string | null };
}

/** One canonical course/learning journey shared by semantic pages 06 and 07. */
export function CanonicalLearningJourneySpace({ pageId = "06", onOpenPage, onTrail, initialItemKey, onLearningItem }: {
  pageId?: string; onOpenPage?: (id: string) => void; onTrail?: (levels: readonly ObjectTrailLevel[]) => void;
  initialItemKey?: string; onLearningItem?:(key:string)=>void;
}) {
  const [learningPane, setLearningPane] = useState<"courses"|"review"|"sources"|"imports"|"context">(pageId === "07" ? "courses" : "review");
  useEffect(() => { setLearningPane(pageId === "07" ? "courses" : "review"); }, [pageId]);
  const stageContent=useRef<HTMLDivElement>(null),paneOpener=useRef<HTMLElement|null>(null);
  function showLearningPane(next:typeof learningPane){
    if(next===learningPane)return;
    const focused=document.activeElement;
    paneOpener.current=focused instanceof HTMLElement&&stageContent.current?.contains(focused)?focused:null;
    setLearningPane(next);
  }
  useLayoutEffect(()=>{
    const opener=paneOpener.current;paneOpener.current=null;
    if(opener?.closest(".stitch-learning-stage[hidden]")&&stageContent.current?.contains(opener))stageContent.current.querySelector<HTMLElement>(".stitch-learning-stage:not([hidden])")?.focus({preventScroll:true});
  },[learningPane]);
  const [courses, setCourses] = useState<CourseRow[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<KnowledgeRow[]>([]);
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);
  const [knowledgeId, setKnowledgeId] = useState<string>();
  const [knowledgeTitle, setKnowledgeTitle] = useState("");
  const [courseId, setCourseId] = useState<string>();
  const [returnItemKey, setReturnItemKey] = useState<string>();
  const [courseRead, setCourseRead] = useState(0);
  const [externalCourseOpen, setExternalCourseOpen] = useState(false);
  const [itemKey, setItemKey] = useState<string | undefined>(initialItemKey);
  const working = useOptionalCoreWorkingState();
  useEffect(() => {
    if (itemKey) return;
    const pending = Object.values(working?.state.pending_reviews ?? {});
    if (pending.length === 1) setItemKey(pending[0].item_key);
  }, [itemKey, working?.state.pending_reviews]);
  useEffect(()=>{if(initialItemKey)setItemKey(initialItemKey);},[initialItemKey]);
  const [message, setMessage] = useState("");
  const [failure, setFailure] = useState<string | null>(null);
  const catalogEpoch = useRef(0), sourceEpoch = useRef(0);
  async function load(next?: string) {
    const epoch = ++catalogEpoch.current;
    setLoading(true); setFailure(null);
    try {
      const page = coursePage(await coreCommand("course_list", next ? { cursor: next } : {}));
      if (epoch !== catalogEpoch.current) return;
      setCourses(previous => next ? [...previous, ...page.items.filter(item => !previous.some(row => row.manifest_id === item.manifest_id))] : page.items);
      setCursor(page.next); setLoaded(true); setMessage("");
    } catch (error) {
      if (epoch === catalogEpoch.current) { setMessage("课程列表读取失败；不会把失败显示为没有课程。"); setFailure(coreFailureReason(error)); }
    } finally { if (epoch === catalogEpoch.current) setLoading(false); }
  }
  useEffect(() => { void load(); return () => { catalogEpoch.current++; sourceEpoch.current++; }; }, []);
  async function search() {
    const epoch = ++sourceEpoch.current; setSearching(true); setFailure(null); setSearched(false);
    try {
      const value = record(await coreCommand("search", { q: query, active_only: true }));
      if (!Array.isArray(value.items)) throw new Error("invalid knowledge results");
      const found = value.items.map(record);
      if (found.some(item => typeof item.knowledge_id !== "string" || typeof item.head !== "string")) throw new Error("invalid knowledge identity");
      if (epoch === sourceEpoch.current) { setResults(found as KnowledgeRow[]); setSearched(true); setMessage(""); }
    } catch (error) { if (epoch === sourceEpoch.current) { setMessage("知识搜索未完成，请重试。"); setFailure(coreFailureReason(error)); } }
    finally { if (epoch === sourceEpoch.current) setSearching(false); }
  }
  async function chooseKnowledge(row: KnowledgeRow) {
    const epoch = ++sourceEpoch.current; setSearching(true); setFailure(null);
    try {
      const knowledge = record(await coreCommand("knowledge_get", { id: row.knowledge_id }));
      if (knowledge.knowledge_id !== row.knowledge_id || knowledge.status !== "accepted") throw new Error("course requires accepted knowledge");
      if (epoch === sourceEpoch.current) {
        setReturnItemKey(undefined); setKnowledgeId(row.knowledge_id); setKnowledgeTitle(row.head); setCourseId(undefined); setItemKey(undefined); setMessage("");
        showLearningPane("courses");onOpenPage?.("07");
      }
    } catch (error) { if (epoch === sourceEpoch.current) { setMessage("此知识暂不能用于生成课程；普通笔记仍可保存，课程绑定条件单独核实。"); setFailure(coreFailureReason(error)); } }
    finally { if (epoch === sourceEpoch.current) setSearching(false); }
  }
  function chooseCourse(row: CourseRow) {
    sourceEpoch.current++; setReturnItemKey(undefined); setSearching(false); setKnowledgeId(undefined); setCourseId(row.manifest_id); setItemKey(undefined); setMessage(""); setFailure(null);
    onOpenPage?.("07");
  }
  function returnCourse(key: string, knowledgeId: string, knowledgeVersion: string) {
    const target = courseLearningTarget(key);
    if (!target || !knowledgeId || knowledgeVersion !== knowledgeId) return;
    sourceEpoch.current++; setSearching(false); setKnowledgeId(knowledgeId); setKnowledgeTitle("");
    setCourseId(target.courseId); setReturnItemKey(key); setCourseRead(value => value + 1);
    setMessage(""); setFailure(null); showLearningPane("courses");onOpenPage?.("07");
  }
  const topic = courses.find(course => course.manifest_id === courseId)?.title || knowledgeTitle || (pageId === "07" ? "课程与课时" : "学习路径");
  return <section className="stitch-learning-family" aria-label={pageId === "07" ? "课程与视觉教学内容" : "学习路径内容"} data-learning-pane={learningPane}>
    <header className="stitch-learning-topic">
      <div><p className="stitch-learning-eyebrow">学习空间 · 已有课程与复习</p><h2>{topic}</h2><p>读取绑定版本，独立作答，再记录本次复习。</p></div>
      <div className="stitch-learning-topic-state"><span>{loaded ? "已读课程 · "+courses.length : "课程目录待读取"}</span>{itemKey ? <span>已选学习项目</span> : null}</div>
    </header>
    <nav className="stitch-learning-navigation" aria-label="学习内容导航">
      <button type="button" aria-pressed={learningPane === "review"} onClick={() => {showLearningPane("review");onOpenPage?.("06");}}>学习路径</button>
      <button type="button" aria-pressed={learningPane === "courses"} onClick={() => {showLearningPane("courses");onOpenPage?.("07");}}>课程与课时</button>
      <button type="button" aria-pressed={learningPane === "sources"} onClick={() => showLearningPane("sources")}>课程来源</button>
      <button type="button" aria-pressed={learningPane === "imports"} onClick={() => showLearningPane("imports")}>外部课程</button>
      <button type="button" aria-pressed={learningPane === "context"} onClick={() => showLearningPane("context")}>学习说明</button>
    </nav>
    {message || failure ? <div className="stitch-learning-notice">{message ? <p role="status">{message}</p> : null}{failure ? <p className="state-reason">{failure}</p> : null}</div> : null}
    <div className="stitch-learning-stage-content" ref={stageContent}>
      <section tabIndex={-1} hidden={learningPane !== "courses"} className="stitch-learning-stage" aria-label="课程内容槽">
        <section className="stitch-learning-glass" aria-label="已保存课程"><header className="stitch-learning-card-heading"><h3>已保存课程</h3><button disabled={loading} onClick={() => void load()}>刷新课程</button></header>
          {loading ? <p role="status">正在读取课程…</p> : null}
          {loaded && !loading && courses.length === 0 ? <p className="stitch-learning-empty">尚无已保存课程。从已接受知识生成第一份课程候选。</p> : null}
          <ul className="stitch-learning-course-list">{courses.map(course => <li key={course.manifest_id} data-selected={course.manifest_id === courseId}><button aria-pressed={course.manifest_id === courseId} onClick={() => {showLearningPane("courses");chooseCourse(course);}}>{course.title}</button><small>{course.stale ? "来源已变化 · 历史只读" : "绑定版本待打开核实"} · 候选 · 待复核</small></li>)}</ul>
          {cursor ? <button disabled={loading} onClick={() => void load(cursor)}>读取更多课程</button> : null}
        </section>
        <div className="stitch-learning-course-detail">{courseId || knowledgeId ? <KnowledgeCoursePanel key={(courseId ?? knowledgeId)+":"+courseRead} courseId={courseId} knowledgeId={knowledgeId} expectedItemKey={returnItemKey}
          onCourseCreated={id => { setCourseId(id); void load(); }} onLearning={key => { setItemKey(key);showLearningPane("review"); onLearningItem?.(key); onOpenPage?.("06"); }} /> : <section className="stitch-learning-glass stitch-learning-empty"><h3>打开一份课程</h3><p>选择已保存课程，或在“课程来源”中读取真实知识版本。</p><button type="button" onClick={() => showLearningPane("sources")}>选择课程来源</button></section>}
          {knowledgeId ? <p className="stitch-learning-caption">课程来源：{knowledgeTitle}。生成不会改写原知识，也不会直接记录掌握。</p> : null}
        </div>
      </section>
      <section tabIndex={-1} hidden={learningPane !== "review"} className="stitch-learning-stage" aria-label="练习内容槽">
        <div className="stitch-learning-item-actions"><button disabled={!itemKey} onClick={()=>{if(itemKey){onLearningItem?.(itemKey);onOpenPage?.("11");}}}>练习此学习项目</button><button disabled={!itemKey} onClick={()=>{if(itemKey){onLearningItem?.(itemKey);onOpenPage?.("12");}}}>复习此学习项目</button></div>{!itemKey?<p className="muted">先选择或读取一个学习项目，练习与复习才会启用。</p>:null}
        {!itemKey?<p className="stitch-learning-caption">先在上方课程或学习队列选择一个学习项目，练习与复习按钮才可用。</p>:null}
        {pageId === "06" || itemKey ? <CanonicalLearningSpace active={learningPane === "review"} onReturnCourse={returnCourse} onTrail={onTrail} initialItemKey={itemKey} onItemSelected={key=>{setItemKey(key);onLearningItem?.(key);}} /> : <section className="stitch-learning-glass stitch-learning-empty"><h3>选择本次学习项目</h3><p>从课程中的实际课时建立学习问题后，再继续作答和复习。</p><button type="button" onClick={() => showLearningPane("courses")}>查看已保存课程</button></section>}
      </section>
      <section tabIndex={-1} hidden={learningPane !== "sources"} className="stitch-learning-stage stitch-learning-glass" aria-label="课程来源选择"><h3>从真实知识继续</h3>
        <form className="stitch-learning-source-search" onSubmit={event => { event.preventDefault(); void search(); }}><label>查找课程来源知识<input value={query} onChange={event => setQuery(event.target.value)} /></label><button disabled={searching}>搜索知识</button></form>
        {searched && !results.length ? <p>没有匹配的知识。可先去知识库保存内容，再独立整理课程来源。</p> : null}
        <ul className="stitch-learning-course-list" aria-label="课程来源搜索结果">{results.map(row => <li key={row.knowledge_id}><button disabled={searching} onClick={() => void chooseKnowledge(row)}>{row.head}</button></li>)}</ul>
      </section>
      <section tabIndex={-1} hidden={learningPane !== "imports"} className="stitch-learning-stage stitch-learning-glass" aria-label="外部课程内容槽"><h3>外部课程与测验</h3><details onToggle={event => setExternalCourseOpen(event.currentTarget.open)}><summary>外部课程与测验</summary>{externalCourseOpen ? <Suspense fallback={<p role="status">正在打开课程导入…</p>}><ImportedCoursePanel /></Suspense> : null}</details></section>
      <section tabIndex={-1} hidden={learningPane !== "context"} className="stitch-learning-stage stitch-learning-glass" aria-label="学习边界与后续能力"><h3>学习计划与能力</h3><p>当前先完成已有课程、课时和复习事件的真实路径。没有模型或证据的项目明确保留为后续缺口。</p>
        <ol className="stitch-learning-steps" aria-label="学习旅程"><li>选择知识或课程</li><li>阅读绑定版本与学习目标</li><li>独立作答和核对</li><li>记录反馈，按真实安排复习</li></ol>
        <details><summary>诊断、先修与负荷计划</summary><p>知识诊断、跨课程先修检查和自动计划尚不可用，因此这里不推测你的学习情况或进度。</p></details>
        <details><summary>训练、Teach-back 与元认知</summary><p>本页可进入绑定版本的真实作答与复习；Teach-back、训练任务和反馈画像由 UF07 继续承接，不等同已完成。</p></details>
        <details><summary>视觉教学与扩展渲染</summary><p>当前接通 native-lesson 文本课时。其他 renderer 名称只是能力意图，不能当成已安装的教学引擎。</p></details>
        <button onClick={() => onOpenPage?.("17")}>查看完整能力与依赖</button>
      </section>
    </div>
  </section>;
}
