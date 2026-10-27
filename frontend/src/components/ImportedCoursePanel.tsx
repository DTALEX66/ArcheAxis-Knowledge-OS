import { userErrorMessage } from "../presentation/labels";
import { RawReceiptButton } from "./DiagnosticConsole";
import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import type { DocumentSummaryDto, DocumentsListDto } from "../api/generated/core-contract";
import { COURSE_IMPORT_MAX_BYTES } from "../adapters/openmaicCourse";
import { referenceFeedback, type CourseImportDraft, type ImportedQuestion } from "../presentation/importedCourse";
import { prepareCourseImport, reopenCourseImport, saveCourseImport,
  type PreparedCourseImport, type StoredCourseImport } from "../presentation/importedCourseStorage";
import "./ImportedCoursePanel.css";

function courseFailureMessage(failure: string, pendingSave: boolean) {
  const summary = userErrorMessage(failure);
  return summary !== userErrorMessage(null) ? summary : pendingSave
    ? "课程保存结果仍待核对；请保留当前选择，使用同一次保存重试或打开运行诊断。"
    : "课程内容暂时无法读取，请核对文件格式；具体原因见运行诊断。";
}

function Question({ question, group }: { question: ImportedQuestion; group: string }) {
  const [selected, setSelected] = useState<string[]>([]), [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<string>();
  const labels = { invalid_response: "请选择有效选项后核对。", no_reference: "此题未提供可用参考答案，请自行复核。",
    review_required: "短答需要自行复核，不自动判对。", matches_reference: "与课件参考答案一致；不代表掌握，也未记录复习成绩。",
    differs_from_reference: "与课件参考答案不同；请复核原件和解析。" };
  return <fieldset><legend>{question.question}</legend>
    {question.type === "short_answer" ? <label>你的回答<textarea value={answer} onChange={event => { setAnswer(event.target.value); setFeedback(undefined); }} /></label>
      : question.options?.map(option => <label key={option.value} className="imported-course-option"><input
        type={question.type === "single" ? "radio" : "checkbox"} name={group} checked={selected.includes(option.value)}
        onChange={event => { setFeedback(undefined); setSelected(previous => question.type === "single" ? [option.value]
          : event.target.checked ? [...previous, option.value] : previous.filter(v => v !== option.value)); }} />{option.label}</label>)}
    <button onClick={() => setFeedback(labels[referenceFeedback(question, question.type === "short_answer" ? [answer] : selected)])}>核对课件参考答案</button>
    {feedback ? <div role="status"><p>{feedback}</p>{question.hasAnswer !== false && question.answer?.length ? <p>课件参考答案：{question.answer.map(v => question.options?.find(o => o.value === v)?.label ?? v).join("；")}</p> : null}
      {question.analysis ? <p>课件解析：{question.analysis}</p> : null}</div> : null}
  </fieldset>;
}
function CoursePreview({ course, identity }: { course: CourseImportDraft; identity: string }) {
  return <article aria-label="外部课程候选预览"><h4>{course.title}</h4>
    <p>外部课程候选 · 来源与参考答案未核验 · 不记录掌握或复习成绩</p>
    <details><summary>转换与呈现说明</summary><ul>{course.report.map(item => <li key={item}>{item}</li>)}</ul></details>
    {[...course.scenes].sort((a, b) => a.order - b.order).map(scene => <section key={scene.order}><h5>{scene.title}</h5>
      {scene.questions.map(q => <Question key={`${identity}:${scene.order}:${q.id}`} group={`${identity}:${scene.order}:${q.id}`} question={q} />)}</section>)}
  </article>;
}

/** Optional content adapter UI, mounted by the existing learning space; no new product shell. */
export function ImportedCoursePanel() {
  const [prepared, setPrepared] = useState<PreparedCourseImport>();
  const [stored, setStored] = useState<StoredCourseImport>();
  const [busy, setBusy] = useState(false), [attempted, setAttempted] = useState(false);
  const [message, setMessage] = useState(""), [failure, setFailure] = useState("");
  const [rows, setRows] = useState<DocumentSummaryDto[]>([]), [cursor, setCursor] = useState<string | null>(null), [listed, setListed] = useState(false);
  const locked = useRef(false), epoch = useRef(0), seenCursors = useRef(new Set<string>());
  useEffect(() => () => { epoch.current++; }, []);
  async function action(work: (current: () => boolean) => Promise<void>) {
    if (locked.current) return;
    locked.current = true; setBusy(true); setFailure(""); setMessage(""); const request = epoch.current;
    try { await work(() => request === epoch.current); }
    catch (error) { if (request === epoch.current) { setMessage(""); setFailure(error instanceof Error ? error.message : "操作未完成，请保留文件后重试。"); } }
    finally { locked.current = false; if (request === epoch.current) setBusy(false); }
  }
  async function select(file: File) {
    await action(async current => {
      setPrepared(undefined); setStored(undefined); setAttempted(false);
      if (file.size > COURSE_IMPORT_MAX_BYTES) throw new Error("文件超过 256 KiB；未读取或截断。");
      const selected = await prepareCourseImport(new Uint8Array(await file.arrayBuffer()), file.name);
      if (current()) { setPrepared(selected); setMessage("预览就绪，尚未保全或保存。请核对后确认。"); }
    });
  }
  async function save() {
    if (!prepared) return;
    await action(async current => {
      setAttempted(true);
      const saved = await saveCourseImport(prepared, phase => {
        if (current()) setMessage(phase === "original_confirmed" ? "原件已保全，正在保存课程候选…" : "课程保存已提交，正在核对结果…");
      });
      if (current()) { setStored(saved); setPrepared(undefined); setMessage("候选已保存并读回核对；内容与参考答案仍待复核。"); }
    });
  }
  async function list(more = false) {
    await action(async current => {
      const next = more ? cursor : null;
      if (next && seenCursors.current.has(next)) throw new Error("分页已重复；请从首页刷新文档列表。");
      let page: DocumentsListDto;
      try { page = await coreCommand<DocumentsListDto>("documents_list", next ? { cursor: next } : {}); }
      catch { throw new Error("文档列表读取失败；未当作没有已保存文档。"); }
      if (!Array.isArray(page.documents) || !(page.next_cursor === null || typeof page.next_cursor === "string")
        || page.documents.some(row => typeof row.document_id !== "string" || !row.document_id || typeof row.title !== "string")) throw new Error("文档列表格式无法核对。");
      if (current()) {
        if (!more) seenCursors.current.clear();
        if (next) seenCursors.current.add(next);
        setRows(previous => more ? [...previous, ...page.documents.filter(row => !previous.some(old => old.document_id === row.document_id))] : page.documents);
        setCursor(page.next_cursor); setListed(true);
      }
    });
  }
  async function open(id: string) {
    await action(async current => {
      setStored(undefined); setPrepared(undefined);
      try {
        const saved = await reopenCourseImport(id);
        if (current()) { setStored(saved); setAttempted(false); setMessage("已从保存的原件与文档重新核对；仍是未核验课程候选。"); }
      } catch { throw new Error("此文档不是可核对的外部课程候选，或原件、版本、内容已变化。未替换已保存内容。"); }
    });
  }
  return <section className="imported-course-panel" aria-label="外部课程候选">
    <p>导入 OpenMAIC 导出的 manifest.json，当前支持单选、多选与短答。完整 ZIP、幻灯片、媒体和互动课堂尚未接入。</p>
    <label>选择课程 manifest.json<input type="file" accept=".json,application/json" disabled={busy} onChange={event => {
      const file = event.target.files?.[0]; event.target.value = ""; if (file) void select(file);
    }} /></label>
    {prepared ? <div><button disabled={busy} onClick={() => void save()}>{attempted ? "同请求重试保存" : "保全原件并保存课程候选"}</button>
      <button disabled={busy} onClick={() => { setPrepared(undefined); setMessage("已清除预览；不会删除已保全原件或撤销已提交保存。"); setFailure(""); }}>清除预览</button></div> : null}
    {busy ? <p role="status">正在核对课程；关闭面板不会撤销已经提交的保存。</p> : null}
    {message ? <p role="status">{message}</p> : null}{failure ? <><p role="alert">{courseFailureMessage(failure, attempted)}</p><RawReceiptButton label="课程导入错误详细信息" payload={{error:failure}}/></> : null}
    {stored || prepared ? <CoursePreview key={stored?.document.document_id ?? prepared?.requestId} course={(stored?.course ?? prepared!.draft)} identity={stored?.document.document_id ?? prepared!.requestId} /> : null}
    {stored ? <button disabled={busy} onClick={() => void open(stored.document.document_id)}>重新核对已保存课程</button> : null}
    <details><summary>重新打开已保存候选</summary><p>从现有文档中选择，打开时核对课程格式与原件。列表也可能包含普通文档，不凭标题认定课程身份。</p>
      <button disabled={busy} onClick={() => void list()}>浏览已保存文档</button>
      {listed && !rows.length ? <p>没有已保存文档。</p> : null}
      <ul>{rows.map(row => <li key={row.document_id}><button disabled={busy} onClick={() => void open(row.document_id)}>打开 {row.title}</button></li>)}</ul>
      {cursor ? <button disabled={busy} onClick={() => void list(true)}>读取更多文档</button> : null}
    </details>
  </section>;
}
