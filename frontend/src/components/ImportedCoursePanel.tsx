import { userErrorMessage } from "../presentation/labels";
import { RawReceiptButton } from "./DiagnosticConsole";
import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import type { DocumentSummaryDto, DocumentsListDto } from "../api/generated/core-contract";
import { COURSE_IMPORT_MAX_BYTES } from "../adapters/openmaicCourse";
import { referenceFeedback, slideText, type CourseImportDraft, type ImportedQuestion, type ImportedTextSlide } from "../presentation/importedCourse";
import { cancelCourseAttempt, courseActivity, courseAnswerValues, freezeCourseAnswer, newCourseAttempt, readCourseHistory,
  startCourseAttempt, submitCourseAttempt, type CourseAttempt, type CourseHistoryRow, type MaterialStatus } from "../presentation/importedCourseAttempts";
import { prepareCourseImport, preserveCourseOriginal, reopenCourseImport, saveCourseImport,
  type PreparedCourseImport, type StoredCourseImport } from "../presentation/importedCourseStorage";
import "./ImportedCoursePanel.css";

function courseFailureMessage(failure: string, pendingSave: boolean) {
  const summary = userErrorMessage(failure);
  return summary !== userErrorMessage(null) ? summary : pendingSave
    ? "课程保存结果仍待核对；请保留当前选择，使用同一次保存重试或打开运行诊断。"
    : "课程内容暂时无法读取，请核对文件格式；具体原因见运行诊断。";
}

const feedbackLabels = { invalid_response: "请选择有效选项后核对。", no_reference: "此题未提供可用参考答案，请自行复核。",
  review_required: "短答需要自行复核，不自动判对。", matches_reference: "与课件参考答案一致；不代表掌握，也未记录复习成绩。",
  differs_from_reference: "与课件参考答案不同；请复核原件和解析。" };
const materialLabels: Record<MaterialStatus, string> = {
  current: "课件绑定的版本仍是当前版本。", historical: "课件绑定的是历史版本，记录不会转移到新版本。",
  unavailable: "课件当前版本暂无法核对；记录仍绑定原版本。",
};
function Question({ question, group, stored, order }: { question: ImportedQuestion; group: string; stored?: StoredCourseImport; order?: number }) {
  const [selected, setSelected] = useState<string[]>([]), [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<string>();
  const [phase, setPhase] = useState<"idle" | "starting" | "pending" | "submitting" | "saved" | "cancelling" | "cancelled">("idle");
  const [busy, setBusy] = useState(false), [saveMessage, setSaveMessage] = useState(""), [saveError, setSaveError] = useState("");
  const [history, setHistory] = useState<CourseHistoryRow[] | null>(null), [cursor, setCursor] = useState<string | null>(null);
  const attempt = useRef<CourseAttempt>(), lock = useRef(false), epoch = useRef(0), seenCursors = useRef(new Set<string>());
  useEffect(() => () => { epoch.current++; }, []);
  async function action(work: (current: () => boolean) => Promise<void>) {
    if (lock.current) return;
    lock.current = true; setBusy(true); setSaveError(""); const request = epoch.current;
    const current = () => epoch.current === request;
    try { await work(current); }
    catch (error) { if (current()) setSaveError(error instanceof Error && /^(请先填写|短答只能|请选择有效|答案超过)/.test(error.message)
      ? error.message : "作答操作结果未确认；保留当前请求，可同请求重试或读取已保存记录。"); }
    finally { lock.current = false; if (current()) setBusy(false); }
  }
  async function begin() {
    if (!stored || order === undefined) return;
    await action(async current => {
      if (phase === "idle" || phase === "saved" || phase === "cancelled") attempt.current = undefined;
      if (!attempt.current) {
        const activity = await courseActivity(stored.document, order, question);
        if (!current()) return;
        attempt.current = newCourseAttempt(activity);
      }
      setPhase("starting"); setSaveMessage("正在开始本次作答记录…");
      const status = await startCourseAttempt(attempt.current, current);
      if (status) { setPhase("pending"); setSaveMessage(`已开始记录；填写后可保存，也可取消。${materialLabels[status]}`); }
    });
  }
  async function submit() {
    if (!attempt.current) return;
    await action(async current => {
      attempt.current = freezeCourseAnswer(attempt.current!, question, question.type === "short_answer" ? [answer] : selected);
      setPhase("submitting"); setSaveMessage("正在保存并核对同一作答…");
      const status = await submitCourseAttempt(attempt.current, current);
      if (status) {
        setPhase("saved"); setSaveMessage(`本次作答已保存并读回核对；课件参考对照未核验，未建立独立掌握。${materialLabels[status]}`);
      }
    });
  }
  async function cancel() {
    if (!attempt.current) return;
    await action(async current => {
      setPhase("cancelling"); setSaveMessage("正在核对取消结果…");
      await cancelCourseAttempt(attempt.current!);
      if (current()) { setPhase("cancelled"); setSaveMessage("本次作答已取消；未将它当作已提交结果。"); }
    });
  }
  async function loadHistory(more = false) {
    if (!stored || order === undefined) return;
    await action(async current => {
      const activity = await courseActivity(stored.document, order, question);
      if (!current()) return;
      const next = more ? cursor ?? undefined : undefined;
      if (next && seenCursors.current.has(next)) throw new Error("重复分页");
      const page = await readCourseHistory(activity, next);
      if (!current()) return;
      if (!more) seenCursors.current.clear();
      if (next) seenCursors.current.add(next);
      setHistory(previous => more ? [...(previous ?? []), ...page.rows] : page.rows);
      setCursor(page.nextCursor);
      setSaveMessage(`已读取 Core 中此课件版本的作答记录；课件来源与参考答案仍未核验。${materialLabels[page.materialStatus]}`);
    });
  }
  function changed() {
    setFeedback(undefined);
    if (phase === "saved" || phase === "cancelled") { attempt.current = undefined; setPhase("idle"); setSaveMessage(""); }
  }
  const inputLocked = busy || phase === "submitting" || phase === "cancelling";
  return <fieldset><legend>{question.question}</legend>
    {question.type === "short_answer" ? <label>你的回答<textarea disabled={inputLocked} value={answer} onChange={event => { setAnswer(event.target.value); changed(); }} /></label>
      : question.options?.map(option => <label key={option.value} className="imported-course-option"><input
        type={question.type === "single" ? "radio" : "checkbox"} name={group} checked={selected.includes(option.value)} disabled={inputLocked}
        onChange={event => { changed(); setSelected(previous => question.type === "single" ? [option.value]
          : event.target.checked ? [...previous, option.value] : previous.filter(v => v !== option.value)); }} />{option.label}</label>)}
    <button onClick={() => setFeedback(feedbackLabels[referenceFeedback(question, question.type === "short_answer" ? [answer] : selected)])}>核对课件参考答案</button>
    {feedback ? <div role="status"><p>{feedback}</p>{question.hasAnswer !== false && question.answer?.length ? <p>课件参考答案：{question.answer.map(v => question.options?.find(o => o.value === v)?.label ?? v).join("；")}</p> : null}
      {question.analysis ? <p>课件解析：{question.analysis}</p> : null}</div> : null}
    {stored && order !== undefined ? <div className="imported-course-attempts">
      {phase === "idle" || phase === "saved" || phase === "cancelled" || phase === "starting" ? <button type="button" disabled={busy} onClick={() => void begin()}>
        {phase === "starting" ? "重试开始记录" : phase === "idle" ? "开始记录本次作答" : "开始新一次作答"}</button> : null}
      {phase === "pending" || phase === "submitting" || phase === "cancelling" ? <>
        <button type="button" disabled={busy || (phase === "cancelling" && !attempt.current?.submission)} onClick={() => void submit()}>
          {phase === "pending" ? "保存作答" : "重试保存同一作答"}</button>
        <button type="button" disabled={busy} onClick={() => void cancel()}>{phase === "cancelling" ? "重试取消" : "取消本次"}</button>
      </> : null}
      <button type="button" disabled={busy} onClick={() => void loadHistory()}>读取已保存作答</button>
      {saveMessage ? <p role="status">{saveMessage}</p> : null}{saveError ? <p role="alert">{saveError}</p> : null}
      {history ? <div><p>以下记录按尝试编号分页，课件参考对照不是供体评分或独立掌握。</p>
        {!history.length ? <p>此版本暂无记录。</p> : <ul>{history.map(row => {
          const values = row.answer === null ? null : courseAnswerValues(row.answer, question);
          return <li key={row.attemptId}>{row.state === "pending" ? "未提交" : row.state === "cancelled" ? "已取消" : "已提交"}
            {row.answer !== null ? values ? <>：{values.map(value => question.options?.find(option => option.value === value)?.label ?? value).join("；")}
              <p>{feedbackLabels[referenceFeedback(question, values)]} {row.selfReport ? "此记录为自报。" : "此记录未标记自报。"} {row.rating ? `自评：${row.rating}。` : "未记录自评。"}</p></>
              : "；此记录格式无法由本课程读取，原记录仍保留。" : null}</li>;
        })}</ul>}
        {cursor ? <button type="button" disabled={busy} onClick={() => void loadHistory(true)}>读取更多作答</button> : null}</div> : null}
    </div> : null}
  </fieldset>;
}
function CoursePreview({ course, identity, stored }: { course: CourseImportDraft; identity: string; stored?: StoredCourseImport }) {
  if (course.scenes.some(scene => scene.kind)) return <CoursePlayer course={course} identity={identity} stored={stored} />;
  return <article aria-label="外部课程候选预览"><h4>{course.title}</h4>
    <p>外部课程候选 · 来源与参考答案未核验 · 不记录掌握或复习成绩</p>
    <details><summary>转换与呈现说明</summary><ul>{course.report.map(item => <li key={item}>{item}</li>)}</ul></details>
    {[...course.scenes].sort((a, b) => a.order - b.order).map(scene => <section key={scene.order}><h5>{scene.title}</h5>
      {scene.questions.map(q => <Question key={`${identity}:${scene.order}:${q.id}`} group={`${identity}:${scene.order}:${q.id}`} question={q} />)}</section>)}
  </article>;
}
function TextSlide({ slide }: { slide: ImportedTextSlide }) {
  const background = slide.background as Record<string, unknown> | undefined;
  const backgroundColor = typeof background?.color === "string" ? background.color : String(slide.theme.backgroundColor);
  const height = slide.viewportSize * slide.viewportRatio;
  return <div className="imported-course-slide" aria-label="文本幻灯片" style={{ aspectRatio: `${1 / slide.viewportRatio}`, backgroundColor }}>
    {slide.elements.map(element => <div key={element.id} className="imported-course-slide-text" style={{
      left: `${element.left / slide.viewportSize * 100}%`, top: `${element.top / height * 100}%`,
      width: `${element.width / slide.viewportSize * 100}%`, height: `${element.height / height * 100}%`,
      transform: `rotate(${element.rotate}deg)`, color: element.defaultColor,
    }}>{slideText(element.content)}</div>)}
  </div>;
}
/** Limited text-canvas view. It does not execute HTML, media, narration, or animation. */
function CoursePlayer({ course, identity, stored }: { course: CourseImportDraft; identity: string; stored?: StoredCourseImport }) {
  const [current, setCurrent] = useState(0);
  const scenes = [...course.scenes].sort((a, b) => a.order - b.order);
  return <article aria-label="外部课程候选预览"><h4>{course.title}</h4>
    <p>外部课程候选 · 来源与参考答案未核验 · {stored ? "可记录作答，不记录掌握" : "预览作答暂不保存，也不记录掌握"}</p>
    <details><summary>转换与呈现说明</summary><ul>{course.report.map(item => <li key={item}>{item}</li>)}</ul></details>
    <nav aria-label="课程场景"><button type="button" disabled={current === 0} onClick={() => setCurrent(index => index - 1)}>上一节</button>
      <span aria-live="polite">第 {current + 1} / {scenes.length} 节</span>
      <button type="button" disabled={current === scenes.length - 1} onClick={() => setCurrent(index => index + 1)}>下一节</button></nav>
    {scenes.map((scene, index) => <section key={scene.order} hidden={index !== current}><h5>{scene.title}</h5>
      {scene.kind === "slide" && scene.slide ? <TextSlide slide={scene.slide} /> : null}
      {scene.kind === "quiz" ? scene.questions.map(q => <Question key={`${identity}:${scene.order}:${q.id}`}
        group={`${identity}:${scene.order}:${q.id}`} question={q} stored={stored} order={scene.order} />) : null}</section>)}
  </article>;
}

/** Optional content adapter UI, mounted by the existing learning space; no new product shell. */
export function ImportedCoursePanel() {
  const [prepared, setPrepared] = useState<PreparedCourseImport>();
  const [stored, setStored] = useState<StoredCourseImport>();
  const [unsupported, setUnsupported] = useState<{ bytes: Uint8Array; fileName: string }>();
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
      setPrepared(undefined); setStored(undefined); setUnsupported(undefined); setAttempted(false);
      if (file.size > COURSE_IMPORT_MAX_BYTES) throw new Error("文件超过 256 KiB；未读取或截断。");
      const bytes = new Uint8Array(await file.arrayBuffer());
      let selected: PreparedCourseImport;
      try { selected = await prepareCourseImport(bytes, file.name); }
      catch (error) { if (current() && bytes.length) setUnsupported({ bytes: bytes.slice(), fileName: file.name }); throw error; }
      if (current()) { setPrepared(selected); setMessage("预览就绪，尚未保全或保存。请核对后确认。"); }
    });
  }
  async function preserveOriginal() {
    if (!unsupported) return;
    await action(async current => {
      const receipt = await preserveCourseOriginal(unsupported.bytes, unsupported.fileName);
      if (current()) { setUnsupported(undefined); setMessage(`原件已保全并读回核对（来源 ${receipt.sourceId}）；未创建课程或执行不支持的内容。`); }
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
      setStored(undefined); setPrepared(undefined); setUnsupported(undefined);
      try {
        const saved = await reopenCourseImport(id);
        if (current()) { setStored(saved); setAttempted(false); setMessage("已从保存的原件与文档重新核对；仍是未核验课程候选。"); }
      } catch { throw new Error("此文档不是可核对的外部课程候选，或原件、版本、内容已变化。未替换已保存内容。"); }
    });
  }
  return <section className="imported-course-panel" aria-label="外部课程候选">
    <p>导入 OpenMAIC 导出的 manifest.json。支持测验及 1.3.0 文本幻灯片的有限呈现；完整 ZIP、媒体、互动与讲解尚未接入。保存课程后可记录作答。</p>
    <label>选择课程 manifest.json<input type="file" accept=".json,application/json" disabled={busy} onChange={event => {
      const file = event.target.files?.[0]; event.target.value = ""; if (file) void select(file);
    }} /></label>
    {prepared ? <div><button disabled={busy} onClick={() => void save()}>{attempted ? "同请求重试保存" : "保全原件并保存课程候选"}</button>
      <button disabled={busy} onClick={() => { setPrepared(undefined); setMessage("已清除预览；不会删除已保全原件或撤销已提交保存。"); setFailure(""); }}>清除预览</button></div> : null}
    {busy ? <p role="status">正在核对课程；关闭面板不会撤销已经提交的保存。</p> : null}
    {message ? <p role="status">{message}</p> : null}{failure ? <><p role="alert">{courseFailureMessage(failure, attempted)}</p><RawReceiptButton label="课程导入错误详细信息" payload={{error:failure}}/></> : null}
    {unsupported ? <div><p>课程无法按当前支持范围转换。可单独保全所选原件；这不会创建课程或执行其中的内容。</p>
      <button disabled={busy} onClick={() => void preserveOriginal()}>仅保全课程原件</button></div> : null}
    {stored || prepared ? <CoursePreview key={stored?.document.document_id ?? prepared?.requestId} course={(stored?.course ?? prepared!.draft)}
      identity={stored?.document.document_id ?? prepared!.requestId} stored={stored?.course.schema === "archeaxis.imported-course/v2" ? stored : undefined} /> : null}
    {stored ? <button disabled={busy} onClick={() => void open(stored.document.document_id)}>重新核对已保存课程</button> : null}
    <details><summary>重新打开已保存候选</summary><p>从现有文档中选择，打开时核对课程格式与原件。列表也可能包含普通文档，不凭标题认定课程身份。</p>
      <button disabled={busy} onClick={() => void list()}>浏览已保存文档</button>
      {listed && !rows.length ? <p>没有已保存文档。</p> : null}
      <ul>{rows.map(row => <li key={row.document_id}><button disabled={busy} onClick={() => void open(row.document_id)}>打开 {row.title}</button></li>)}</ul>
      {cursor ? <button disabled={busy} onClick={() => void list(true)}>读取更多文档</button> : null}
    </details>
  </section>;
}
