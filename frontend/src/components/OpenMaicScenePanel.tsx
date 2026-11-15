import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import type { DocumentsListDto, DocumentSummaryDto } from "../api/generated/core-contract";
import { readSceneCandidate, ScenePosition, type SavedScene } from "../presentation/openMaicSceneReader";
import { useOptionalCoreWorkingState } from "../presentation/useCoreWorkingState";
import { Question, TextSlide } from "./ImportedCoursePanel";

/** A human-selected view of stored Core candidates; no generation or active HTML execution. */
export function OpenMaicScenePanel() {
  const working = useOptionalCoreWorkingState(), identity = working?.server;
  const [rows, setRows] = useState<DocumentSummaryDto[]>([]), [cursor, setCursor] = useState<string | null>(null);
  const [scene, setScene] = useState<SavedScene | null>(null), [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false), [message, setMessage] = useState(""), [error, setError] = useState("");
  const [dirty, setDirty] = useState(false);
  const [positionReady, setPositionReady] = useState(false), [answersDirty, setAnswersDirty] = useState(false);
  const dirtyQuestions = useRef(new Set<string>());
  const position = useRef<ScenePosition | null>(null), epoch = useRef(0), lock = useRef(false);
  const owner = useRef(`openmaic-scene:${crypto.randomUUID()}`).current;
  const seen = useRef(new Set<string>());
  useEffect(() => {
    epoch.current++; position.current = null; setScene(null); setStep(0); setBusy(false); lock.current = false;
    setDirty(false); setPositionReady(false); setAnswersDirty(false); dirtyQuestions.current.clear(); setMessage(""); setError(""); setRows([]); setCursor(null); seen.current.clear();
    return () => { epoch.current++; };
  }, [identity?.workspace_id, identity?.restore_epoch, identity?.recovery_requires_confirmation]);
  useEffect(() => { window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: { owner, dirty: dirty || answersDirty || busy || Boolean(position.current?.unresolved) } })); }, [owner, dirty, answersDirty, busy]);
  useEffect(() => () => { window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: { owner, dirty: false } })); }, [owner]);
  async function act(work: (current: () => boolean) => Promise<void>) {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError(""); const token = epoch.current;
    const current = () => token === epoch.current;
    try { await work(current); }
    catch (e) { if (current()) setError(e instanceof Error ? e.message : "操作未确认；原内容仍保留。"); }
    finally { if (current()) { lock.current = false; setBusy(false); } }
  }
  async function list(more = false) {
    await act(async current => {
      const next = more ? cursor : null;
      if (next && seen.current.has(next)) throw new Error("文档分页重复，请刷新列表。");
      const page = await coreCommand<DocumentsListDto>("documents_list", next ? { cursor: next } : {});
      if (!current()) return;
      if (!Array.isArray(page.documents) || new Set(page.documents.map(r => r.document_id)).size !== page.documents.length) throw new Error("文档列表无法核对。");
      if (!more) seen.current.clear();
      if (next) seen.current.add(next);
      setRows(old => more ? [...old, ...page.documents.filter(row => !old.some(x => x.document_id === row.document_id))] : page.documents);
      setCursor(page.next_cursor); setMessage(page.documents.length ? "选择已保存的生成场景；打开时会核对实际格式和版本。" : "这一页没有文档。");
    });
  }
  async function open(id: string) {
    if (dirty || answersDirty || position.current?.unresolved) { setError("先保存或核对当前作答与阅读位置，再切换场景。"); return; }
    await act(async current => {
      const read = await readSceneCandidate(id);
      if (!current()) return;
      let savedPosition: ScenePosition | null = null, savedStep = 0, knownPosition = false;
      if (identity && working?.status === "ready" && !identity.recovery_requires_confirmation) {
        savedPosition = await ScenePosition.open(read, identity.workspace_id);
        if (!current()) return;
        try { savedStep = await savedPosition.read(); knownPosition = true; }
        catch { if (current()) setError("课件已读取，但阅读位置无法核对；可以阅读课件，暂不覆盖位置记录。"); }
        if (!current()) return;
      }
      if (dirtyQuestions.current.size) throw new Error("原场景出现未保存作答，保留原场景；先保存或核对作答。");
      setScene(read); position.current = savedPosition; setStep(savedStep); setDirty(false); setPositionReady(knownPosition);
      setMessage(knownPosition ? "已打开固定场景版本与保存的阅读位置。" : "已打开固定版本课件；位置记录与工作区状态核对后才能保存阅读位置。");
    });
  }
  async function save() {
    await act(async current => {
      const p = position.current;
      if (!p || !identity || working?.status !== "ready" || !positionReady || identity.recovery_requires_confirmation) throw new Error("请先确认当前工作区与阅读位置状态。");
      await p.save(step);
      if (current()) { setDirty(false); setMessage("阅读位置已保存并读回；未记录成绩或掌握。"); }
    });
  }
  async function resume() {
    await act(async current => {
      if (!position.current) throw new Error("当前工作区没有可读取的位置记录。");
      const read = await position.current.read();
      if (current()) { setStep(read); setDirty(false); setPositionReady(true); setMessage("已读取固定场景版本的保存位置。"); }
    });
  }
  const action = scene?.steps[step];
  return <section className="imported-course-panel" aria-label="已生成课件">
    <h4>已生成课件</h4><p>打开 Core 保存的场景候选，阅读讲解或练习；不会重新调用模型。</p>
    <button type="button" disabled={busy} onClick={() => void list()}>浏览生成场景文档</button>
    <ul>{rows.map(row => <li key={row.document_id}><button type="button" disabled={busy || dirty || answersDirty || Boolean(position.current?.unresolved)} onClick={() => void open(row.document_id)}>打开场景 {row.title}</button></li>)}</ul>
    {cursor ? <button type="button" disabled={busy} onClick={() => void list(true)}>读取更多场景文档</button> : null}
    {scene ? <article aria-label="固定版本课件"><h5>{scene.title}</h5>
      <p>场景版本 {scene.document.version} · {scene.sourceStatus === "current" ? "绑定材料仍为当前版本" : scene.sourceStatus === "historical" ? "绑定历史材料，未自动改用新版" : "材料当前性暂未核对"}</p>
      <details><summary>呈现范围</summary><ul>{scene.limitations.map(text => <li key={text}>{text}</li>)}</ul></details>
      {scene.fallback ? <p role="status">{scene.fallback}</p> : <>
        {scene.slide ? <TextSlide slide={scene.slide} focusElement={action?.elementId} /> : null}
        {scene.questions.length ? <fieldset disabled={busy}><legend>课件作答</legend>{scene.questions.map(q => <Question key={`${scene.document.document_id}:${scene.document.version}:${q.id}`} question={q}
          group={`${scene.document.document_id}:${q.id}`} stored={{ document: scene.document }} order={scene.order}
          onDirtyChange={value => { const key = `${scene.document.document_id}:${scene.document.version}:${q.id}`;
            if (value) dirtyQuestions.current.add(key); else dirtyQuestions.current.delete(key); setAnswersDirty(dirtyQuestions.current.size > 0); }} />)}</fieldset> : null}
        {scene.steps.length ? <section aria-label="逐步讲解"><p>讲解文字与静态聚焦；不播放音频或执行其他动作。</p>
          <p aria-live="polite">{action?.text}</p>
          <nav aria-label="讲解步骤"><button type="button" disabled={busy || step === 0 || Boolean(position.current?.unresolved)} onClick={() => { setStep(v => v - 1); if (positionReady) setDirty(true); }}>上一步讲解</button>
            <span>第 {step + 1} / {scene.steps.length} 步</span>
            <button type="button" disabled={busy || step === scene.steps.length - 1 || Boolean(position.current?.unresolved)} onClick={() => { setStep(v => v + 1); if (positionReady) setDirty(true); }}>下一步讲解</button></nav>
        </section> : <p>此场景没有讲解步骤。</p>}
        <button type="button" disabled={busy || !positionReady || working?.status !== "ready" || !position.current || Boolean(position.current.unresolved)} onClick={() => void save()}>保存阅读位置</button>
        <button type="button" disabled={busy || !position.current} onClick={() => void resume()}>读取已保存位置</button>
        {dirty && !position.current?.unresolved ? <button type="button" disabled={busy} onClick={() => { setDirty(false); setMessage("本地阅读位置未保存；原保存位置未改变。"); }}>不保存本地阅读位置</button> : null}
      </>}
    </article> : null}
    {busy ? <p role="status">正在读取或保存…</p> : null}
    {message ? <p role="status">{message}</p> : null}{error ? <p role="alert">{error}</p> : null}
  </section>;
}
