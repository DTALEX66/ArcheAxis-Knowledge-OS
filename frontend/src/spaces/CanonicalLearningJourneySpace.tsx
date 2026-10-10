import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import { coreFailureReason } from "../presentation/labels";
import { KnowledgeCoursePanel } from "../components/KnowledgeCoursePanel";
import { CanonicalLearningSpace } from "./CanonicalLearningSpace";
import type { ObjectTrailLevel } from "../components/NavTrail";

type CourseRow = { manifest_id: string; title: string; stale: boolean; status: "candidate"; human_review_required: true };
type KnowledgeRow = { knowledge_id: string; head: string };
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
export function CanonicalLearningJourneySpace({ pageId = "06", onOpenPage, onTrail, initialItemKey }: {
  pageId?: string; onOpenPage?: (id: string) => void; onTrail?: (levels: readonly ObjectTrailLevel[]) => void;
  initialItemKey?: string;
}) {
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
  const [itemKey, setItemKey] = useState<string | undefined>(initialItemKey);
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
        setKnowledgeId(row.knowledge_id); setKnowledgeTitle(row.head); setCourseId(undefined); setItemKey(undefined); setMessage("");
        onOpenPage?.("07");
      }
    } catch (error) { if (epoch === sourceEpoch.current) { setMessage("此知识暂不能用于生成课程；普通笔记仍可保存，课程绑定条件单独核实。"); setFailure(coreFailureReason(error)); } }
    finally { if (epoch === sourceEpoch.current) setSearching(false); }
  }
  function chooseCourse(row: CourseRow) {
    sourceEpoch.current++; setSearching(false); setKnowledgeId(undefined); setCourseId(row.manifest_id); setItemKey(undefined); setMessage(""); setFailure(null);
    onOpenPage?.("07");
  }
  return <section className="ui-learning-journey" aria-label={pageId === "07" ? "课程与视觉教学" : "学习路径"}>
    <div className="ui-content-tabs"><button aria-pressed={pageId === "06"} onClick={() => onOpenPage?.("06")}>学习路径</button><button aria-pressed={pageId === "07"} onClick={() => onOpenPage?.("07")}>课程与课时</button></div>
    <div className="ui-content-main-side">
      <div className="ui-content-panel">
        <h2>{pageId === "07" ? "从知识到课程与练习" : "继续你的学习路径"}</h2>
        <p>选择已保存课程，读取绑定的知识版本，再进入真实练习。课程候选、复习记录和掌握资格分别记录。</p>
        <ol className="ui-learning-steps" aria-label="学习旅程"><li>选择知识或课程</li><li>阅读绑定版本与学习目标</li><li>独立作答和核对</li><li>记录反馈，按真实安排复习</li></ol>
        <section aria-label="已保存课程"><div className="ui-library-toolbar"><h3>已保存课程</h3><button disabled={loading} onClick={() => void load()}>刷新课程</button></div>
          {loading ? <p role="status">正在读取课程…</p> : null}
          {loaded && !loading && courses.length === 0 ? <p>尚无已保存课程。从已接受知识生成第一份课程候选。</p> : null}
          <ul className="ui-course-list">{courses.map(course => <li key={course.manifest_id}><button aria-pressed={course.manifest_id === courseId} onClick={() => chooseCourse(course)}>{course.title}</button><small>{course.stale ? "来源已变化 · 历史只读" : "绑定版本待打开核实"} · 候选 · 待复核</small></li>)}</ul>
          {cursor ? <button disabled={loading} onClick={() => void load(cursor)}>读取更多课程</button> : null}
        </section>
        <form className="ui-library-toolbar" onSubmit={event => { event.preventDefault(); void search(); }}><label>查找课程来源知识<input value={query} onChange={event => setQuery(event.target.value)} /></label><button disabled={searching}>搜索知识</button></form>
        {searched && !results.length ? <p>没有匹配的知识。可先去知识库保存内容，再独立整理课程来源。</p> : null}
        <ul aria-label="课程来源搜索结果">{results.map(row => <li key={row.knowledge_id}><button disabled={searching} onClick={() => void chooseKnowledge(row)}>{row.head}</button></li>)}</ul>
        {courseId || knowledgeId ? <KnowledgeCoursePanel key={courseId ?? knowledgeId} courseId={courseId} knowledgeId={knowledgeId}
          onCourseCreated={() => { void load(); }} onLearning={key => { setItemKey(key); onOpenPage?.("06"); }} /> : null}
        {knowledgeId ? <p>课程来源：{knowledgeTitle}。生成不会改写原知识，也不会直接记录掌握。</p> : null}
        {message ? <p role="status">{message}</p> : null}{failure ? <p className="state-reason">{failure}</p> : null}
      </div>
      <aside className="ui-content-panel" aria-label="学习边界与后续能力"><h3>学习计划与能力</h3><p>当前先完成已有课程、课时和复习事件的真实路径。没有模型或证据的项目明确保留为后续缺口。</p>
        <details><summary>诊断、先修与负荷计划</summary><p>知识诊断、跨课程先修缺口、负荷配额和自动计划尚无接通的 Core 合同，不显示推测的学习画像或进度。</p></details>
        <details><summary>训练、Teach-back 与元认知</summary><p>本页可进入绑定版本的真实作答与复习；Teach-back、训练任务和反馈画像由 UF07 继续承接，不等同已完成。</p></details>
        <details><summary>视觉教学与扩展渲染</summary><p>当前接通 native-lesson 文本课时。其他 renderer 名称只是能力意图，不能当成已安装的教学引擎。</p></details>
        <button onClick={() => onOpenPage?.("17")}>查看完整能力与依赖</button>
      </aside>
    </div>
    {pageId === "06" || itemKey ? <div className="ui-content-panel ui-learning-review"><CanonicalLearningSpace onTrail={onTrail} initialItemKey={itemKey} /></div> : null}
  </section>;
}
