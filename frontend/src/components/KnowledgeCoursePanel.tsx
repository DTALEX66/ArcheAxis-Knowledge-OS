import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import { coreFailureReason } from "../presentation/labels";
import { RawReceiptButton } from "./DiagnosticConsole";

function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("invalid course response");
  return value as Record<string, unknown>;
}
function nonempty(value: unknown): value is string { return typeof value === "string" && value.length > 0; }
export type Course = { id: string; artifactId: string; title: string; sourceId: string; sourceRevision: string;
  knowledgeId: string; stale: boolean; components: { title: string; statement: string }[]; objectives: string[] };
export function readCourse(value: unknown, knowledgeId?: string, expected?: Course, allowStale = false): Course {
  const course = record(value), manifest = record(course.manifest);
  if (course.status !== "candidate" || course.human_review_required !== true || typeof course.stale !== "boolean" || (!allowStale && course.stale)
    || manifest.schema !== "archeaxis.course-manifest/v1" || manifest.status !== "candidate"
    || !nonempty(manifest.title) || typeof manifest.manifest_id !== "string" || !/^[A-Za-z0-9][A-Za-z0-9_.-]{0,255}$/.test(manifest.manifest_id)
    || !Array.isArray(course.bindings) || course.bindings.length !== 1
    || !Array.isArray(manifest.artifacts) || manifest.artifacts.length !== 1) throw new Error("invalid or stale course");
  const binding = record(course.bindings[0]), artifact = record(manifest.artifacts[0]);
  // Course Core binds an immutable knowledge ID as its version, not the review receipt hash.
  if (!nonempty(binding.knowledge_id) || (knowledgeId !== undefined && binding.knowledge_id !== knowledgeId) || binding.knowledge_version !== binding.knowledge_id || binding.stale !== course.stale
    || !nonempty(binding.source_id) || !nonempty(binding.source_revision)
    || typeof artifact.artifact_id !== "string" || !/^[A-Za-z0-9][A-Za-z0-9_.-]{0,255}$/.test(artifact.artifact_id)
    || artifact.artifact_type !== "lesson" || artifact.renderer !== "native-lesson"
    || artifact.status !== "candidate" || artifact.derived_only !== true || artifact.human_review_required !== true) throw new Error("invalid course binding");
  if (!nonempty(binding.component_id) || !Array.isArray(artifact.knowledge_ids) || artifact.knowledge_ids.length !== 1
    || artifact.knowledge_ids[0] !== binding.component_id || !Array.isArray(manifest.knowledge_components)
    || !Array.isArray(manifest.learning_objectives)) throw new Error("invalid lesson curriculum");
  const components = manifest.knowledge_components.map(record).filter(item => item.component_id === binding.component_id);
  const objectives = manifest.learning_objectives.map(record).filter(item => Array.isArray(item.knowledge_component_ids)
    && item.knowledge_component_ids.includes(binding.component_id));
  if (components.length !== 1 || components.some(item => !nonempty(item.title) || !nonempty(item.statement))
    || objectives.length === 0 || objectives.some(item => !nonempty(item.statement))) throw new Error("missing lesson material");
  const result: Course = { id: manifest.manifest_id, artifactId: artifact.artifact_id, title: manifest.title, sourceId: binding.source_id, sourceRevision: binding.source_revision,
    knowledgeId: binding.knowledge_id, stale: course.stale, components: components.map(item => ({ title: item.title as string, statement: item.statement as string })),
    objectives: objectives.map(item => item.statement as string) };
  if (expected && (result.id !== expected.id || result.knowledgeId !== expected.knowledgeId || result.artifactId !== expected.artifactId
    || result.sourceId !== expected.sourceId || result.sourceRevision !== expected.sourceRevision
    || JSON.stringify(result.components) !== JSON.stringify(expected.components)
    || JSON.stringify(result.objectives) !== JSON.stringify(expected.objectives))) throw new Error("course identity changed");
  return result;
}
function itemKey(course: Course): string { return `course:${course.id}:artifact:${course.artifactId}`; }

export function KnowledgeCoursePanel({ knowledgeId, courseId, onCourseCreated, onLearning }: {
  knowledgeId?: string; courseId?: string;
  onCourseCreated?: (courseId: string) => void; onLearning?: (itemKey: string) => void;
}) {
  const [course, setCourse] = useState<Course | null>(null);
  const [lesson, setLesson] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [failure, setFailure] = useState<string | null>(null);
  const epoch = useRef(0);
  const current = (request: number) => request === epoch.current;
  async function renderCourse(value: Course, request: number) {
    const rendered = record(await coreCommand("course_render", { course_id: value.id, body: { artifact_id: value.artifactId } }));
    if (!current(request)) return null;
    readCourse(rendered.course, value.knowledgeId, value);
    if (rendered.derived_only !== true || rendered.canonical_bindings_verified !== true || rendered.human_review_required !== true) throw new Error("invalid lesson authority");
    const derived = record(rendered.render), projection = record(derived.lesson), frontmatter = record(projection.frontmatter);
    if (derived.derived_only !== true || derived.human_review_required !== true || !nonempty(projection.content)
      || frontmatter.manifest_id !== value.id || frontmatter.artifact_id !== value.artifactId) throw new Error("invalid lesson projection");
    return rendered;
  }
  async function loadStored(id: string, request: number) {
    setBusy(true);
    try {
      const saved = readCourse(await coreCommand("course_get", { course_id: id }), knowledgeId, undefined, true);
      if (!current(request)) return;
      if (saved.id !== id) throw new Error("stored course identity changed");
      if (saved.stale) {
        setCourse(saved); setMessage("来源绑定已失效：保留原课程与知识版本，仅供历史阅读。不会自动升级、渲染或建立新学习问题。");
        return;
      }
      const rendered = await renderCourse(saved, request);
      if (current(request) && rendered) {setCourse(saved);setLesson(rendered);setMessage("已读取保存的课程候选，仍需人工复核。");}
    } catch (error) {if (current(request)) {setMessage("课程未能读取。保存的版本不会被替换，请重试。");setFailure(coreFailureReason(error));}}
    finally {if (current(request)) setBusy(false);}
  }
  useEffect(() => {
    const request = ++epoch.current;
    setCourse(null);setLesson(null);setMessage("");setFailure(null);setBusy(false);
    if (courseId) void loadStored(courseId, request);
    return () => {epoch.current += 1;};
  }, [knowledgeId, courseId]);
  async function generate() {
    if (busy || !knowledgeId) return;
    const request = ++epoch.current;
    setBusy(true);setCourse(null);setLesson(null);setMessage("");setFailure(null);
    try {
      const created = record(await coreCommand("course_from_knowledge", { body: { knowledge_id: knowledgeId } }));
      if (!current(request)) return;
      if (created.human_review_required !== true) throw new Error("missing human review boundary");
      const candidate = readCourse(created.course, knowledgeId), suggested = record(created.suggested_learning_item);
      if (suggested.item_key !== itemKey(candidate) || suggested.course_id !== candidate.id || suggested.artifact_id !== candidate.artifactId
        || suggested.knowledge_id !== knowledgeId || suggested.knowledge_version !== knowledgeId
        || suggested.source_id !== candidate.sourceId || suggested.source_revision !== candidate.sourceRevision) throw new Error("invalid suggested learning binding");
      const saved = readCourse(await coreCommand("course_get", { course_id: candidate.id }), knowledgeId, candidate);
      if (!current(request)) return;
      const rendered = await renderCourse(saved, request);
      if (current(request) && rendered) {setCourse(saved);setLesson(rendered);setMessage("课程候选与课时已读取，仍需人工复核。");onCourseCreated?.(saved.id);}
    } catch (error) {if (current(request)) {setMessage("课程未能读取。请重新读取知识后重试；失效版本不能继续学习。");setFailure(coreFailureReason(error));}}
    finally {if (current(request)) setBusy(false);}
  }
  async function study() {
    if (!course || course.stale || !lesson || busy) return;
    const request = epoch.current;
    setBusy(true);setMessage("");setFailure(null);
    try {
      const saved = readCourse(await coreCommand("course_get", { course_id: course.id }), course.knowledgeId, course, true);
      if (!current(request)) return;
      if (saved.stale) {
        setCourse(saved);setLesson(null);setMessage("来源绑定已失效：原课程只读，不建立新学习问题，未记录复习成绩。");return;
      }
      const key = itemKey(saved);
      await coreCommand("learning_reference", { item_key: key, body: { knowledge_id: saved.knowledgeId } });
      if (!current(request)) return;
      const assessment = record(await coreCommand("assessment_create", { item_key: key, body: { knowledge_id: saved.knowledgeId } }));
      if (!current(request)) return;
      if (assessment.item_key !== key || assessment.knowledge_id !== saved.knowledgeId || assessment.knowledge_version !== saved.knowledgeId
        || !nonempty(assessment.assessment_id) || !nonempty(assessment.question)) throw new Error("invalid assessment");
      setMessage("已建立绑定此课程课时的学习问题，请在学习队列打开。");onLearning?.(key);
    } catch (error) {if (current(request)) {setCourse(null);setLesson(null);setMessage("学习问题未完成，请重新读取课程。未记录复习成绩。");setFailure(coreFailureReason(error));}}
    finally {if (current(request)) setBusy(false);}
  }
  return <section aria-label="课程与课时">
    <h4>课程与课时</h4><p>由已接受知识生成课程候选；课时是派生阅读内容，生成不等于人工接受或掌握。</p>
    {knowledgeId && !courseId ? <button disabled={busy} onClick={() => void generate()}>从当前知识生成课程与课时</button> : null}
    {courseId ? <button disabled={busy} onClick={() => {const request=++epoch.current;setCourse(null);setLesson(null);setMessage("");setFailure(null);void loadStored(courseId,request);}}>重新读取保存的课程</button> : null}
    {course && (lesson !== null || course.stale) ? <article className="library-document" aria-label="课程候选课时"><h5>{course.title}</h5><p>{course.stale ? "历史课程 · 来源绑定失效 · 只读" : "课程候选 · 需人工复核 · 来源版本已由 Core 校验"}</p>
      <h6>知识要点</h6>{course.components.map((component, index) => <div key={index}><strong>{component.title}</strong><p className="course-statement">{component.statement}</p></div>)}
      <h6>学习目标</h6><ul>{course.objectives.map((objective, index) => <li key={index}>{objective}</li>)}</ul>
      <p>绑定知识版本：{course.knowledgeId} · 来源修订：{course.sourceRevision}</p>
      {lesson ? <RawReceiptButton label="课程课时渲染回执" payload={lesson} /> : null}
      {!course.stale && lesson ? <button disabled={busy} onClick={() => void study()}>由课程课时建立学习问题</button> : null}</article> : null}
    {message ? <p role="status">{message}</p> : null}{failure ? <p className="state-reason">{failure}</p> : null}
  </section>;
}
