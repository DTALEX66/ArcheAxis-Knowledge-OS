import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import { ApiError } from "../api/client";
import { RawReceiptButton } from "../components/DiagnosticConsole";
import { Section } from "../components/RealData";
import type { ObjectTrailLevel } from "../components/NavTrail";
import { coreFailureReason } from "../presentation/labels";
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("invalid response");
  return value as Record<string, unknown>;
}
/**
 * Reading surface for the history readback: what is known, in plain terms, and nothing invented.
 * The untouched payload never appears here — it goes to the diagnostic console via RawReceiptButton,
 * the same channel this file already uses for the machine-capability receipt. The state is either the
 * bare `learning_history` readback or a submitted receipt wrapping the readback it was taken with, so
 * the event count is looked for in both shapes rather than guessed at.
 */
function eventCount(value: Record<string, unknown>): number | null {
  if (Array.isArray(value.events)) return value.events.length;
  const nested = value.history;
  if (nested && typeof nested === "object" && !Array.isArray(nested)) return eventCount(nested as Record<string, unknown>);
  return null;
}
function historySummary(history: unknown): string {
  if (history === null || history === undefined) return "尚未读回复习历史。";
  if (typeof history !== "object" || Array.isArray(history)) return "复习历史已读回，这条记录无法在此摘要；未改写的回执见诊断控制台。";
  const value = history as Record<string, unknown>;
  const events = eventCount(value);
  const parts: string[] = [events === null ? "本次回执未附带可数的复习事件记录。" : `已读回 ${events} 条复习事件记录。`];
  if (value.receipt !== undefined && value.receipt !== null) parts.push("已记录本次提交的 Core 回执。");
  return parts.join("");
}
export function CanonicalLearningSpace({onTrail, initialItemKey}:{onTrail?:(levels:readonly ObjectTrailLevel[])=>void; initialItemKey?:string} = {}) {
  const [focusMode, setFocusMode] = useState(false);
  const [items, setItems] = useState<Record<string, unknown>[]>([]);
  const [itemKey, setItemKey] = useState("");
  const [state, setState] = useState<Record<string, unknown>|null>(null);
  const [history, setHistory] = useState<unknown>(null);
  const [answer, setAnswer] = useState("");
  const [rating, setRating] = useState("");
  const [checkedCorrect, setCheckedCorrect] = useState<boolean|null>(null);
  const [answerRevealed, setAnswerRevealed] = useState(false);
  const ratingConsistent = rating !== "" && checkedCorrect !== null && ((Number(rating) === 1) === !checkedCorrect);
  const [message, setMessage] = useState("");
  const [failureReason, setFailureReason] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const epoch = useRef(0);
  const eventId = useRef<string|null>(null);
  async function refresh() {
    try {
      const list = record(await coreCommand("learning_items"));
      if (!Array.isArray(list.items)) throw new Error("invalid items");
      const rows = list.items.map(record);
      if (rows.some(row=>typeof row.item_key !== "string")) throw new Error("invalid item key");
      setItems(rows);
    } catch (error) {setMessage("学习队列读取失败，请重试。");setFailureReason(coreFailureReason(error));}
  }
  useEffect(()=>{void refresh();return()=>{epoch.current+=1;};},[]);
  useEffect(()=>{if(initialItemKey)void open(initialItemKey);},[initialItemKey]);
  useEffect(() => {
    const levels: ObjectTrailLevel[] = [];
    if (itemKey && state) {
      const item = items.find((row) => row.item_key === itemKey);
      levels.push(
        { id: "section:review", label: "复习队列", region: "review" },
        { id: `item:${itemKey}`, label: itemKey, detail: typeof item?.next_review === "string" ? `下次复习 ${item.next_review}` : "下次复习未安排", region: "review" },
      );
    }
    onTrail?.(levels);
  }, [itemKey, state, items, onTrail]);
  async function open(key: string) {
    const current = ++epoch.current; setState(null);setHistory(null);setItemKey(key);setAnswer("");setRating("");setCheckedCorrect(null);setAnswerRevealed(false);eventId.current=null;
    try {
      const [raw, events] = await Promise.all([coreCommand("learning_state",{item_key:key}),coreCommand("learning_history",{item_key:key})]);
      const data = record(raw);
      if (data.item_key !== key || !data.learner || !data.machine) throw new Error("invalid learning state");
      if (current === epoch.current) {setState(data);setHistory(events);setMessage("");}
    } catch (error) {setMessage("学习记录读取失败，暂时不能提交结果。");setFailureReason(coreFailureReason(error));}
  }
  async function review() {
    if (!state || busy) return;
    const current = epoch.current;setBusy(true);
    // Keep the same event key for retries of the same answer, preventing duplicates.
    eventId.current ??= crypto.randomUUID();
    try {
      const learner = record(state.learner);
      const assessment = learner.assessment ? record(learner.assessment) : null;
      if (!assessment || typeof assessment.assessment_id !== "string" || typeof assessment.question !== "string" || typeof assessment.knowledge_version !== "string") throw new Error("a real assessment is required");
      if (!answer.trim() || checkedCorrect === null || !rating) throw new Error("answer, answer check and self-rating are required");
      if (!ratingConsistent) throw new Error("The Core review contract requires rating 1 for an incorrect answer, and rating 2-4 for a correct answer.");
      const body:Record<string,unknown> = {item_key:itemKey,client_event_id:eventId.current,correct:checkedCorrect,rating:Number(rating),answer:answer.trim()};
      if (assessment) {
        for (const field of ["assessment_id","question_version","knowledge_version"] as const) if (typeof assessment[field] === "string") body[field]=assessment[field];
      }
      const receipt = record(await coreCommand("learning_review",{body}));
      if (current === epoch.current) {await open(itemKey);const scheduled=typeof receipt.next_review==="string"?`下次复习：${receipt.next_review}`:receipt.next_review_days===-1?"学习记录已保存；Core 未能安排下次复习。":"学习记录已保存；下次复习时间未提供。";setMessage(`Core 已确认复习记录。${scheduled}`);setHistory((previous:unknown)=>({receipt,history:previous}));await refresh();}
    } catch (error) {setMessage(error instanceof ApiError && error.status >= 400 && error.status < 500
      ? `Core 拒绝了复习记录（${error.status}）。${(error as Error).message} 请检查答案与自评，答案仍保留。`
      : "复习提交未确认，请保留答案并用同一条目重试；不会假定成功。");}
    finally {setBusy(false);}
  }
  return <Section title="学习"><button type="button" aria-pressed={focusMode} onClick={()=>{setFocusMode(value=>{const next=!value;window.dispatchEvent(new CustomEvent("archeaxis-learning-focus",{detail:next}));return next;});}}>{focusMode?"退出聚焦模式":"进入聚焦模式"}</button><p>学习者记录与机器能力分别显示。记录复习结果不会自动证明机器能力或知识正确性。</p>{!focusMode?<button onClick={()=>void refresh()}>刷新学习队列</button>:null}
    <ul tabIndex={-1} data-section="review" aria-label="复习队列">{items.map(item=><li key={String(item.item_key)}><button disabled={busy} onClick={()=>void open(String(item.item_key))}>{String(item.item_key)}</button> · 下次复习 {typeof item.next_review === "string" ? item.next_review : "未安排"}</li>)}</ul>
    <form onSubmit={event=>{event.preventDefault();void open(itemKey);}}><label>学习项目键 <input value={itemKey} disabled={busy} onChange={event=>{epoch.current+=1;setItemKey(event.target.value);setState(null);}} /></label><button disabled={!itemKey.trim()||busy}>读取项目</button></form>
    {state?<article>{(()=>{const learner=record(state.learner);const assessment=learner.assessment?record(learner.assessment):null;return <>
      <h3>复习题</h3>
      {assessment&&typeof assessment.question==="string"?<p>{assessment.question}</p>:<p>此学习项目没有可用的真实题目。请从知识页面创建学习题后再来复习。</p>}
      {assessment&&typeof assessment.knowledge_version==="string"?<small>知识修订：{assessment.knowledge_version}</small>:null}
      <h4>先独立作答</h4><label>本次答案 <textarea value={answer} disabled={busy||!assessment} onChange={event=>{setAnswer(event.target.value);setCheckedCorrect(null);setRating("");eventId.current=null;}} /></label>
      <button type="button" disabled={busy||!assessment||!answer.trim()} onClick={()=>setAnswerRevealed(true)}>{answerRevealed?"已显示核对内容":"查看答案与核对内容"}</button>
      {answerRevealed&&assessment&&typeof assessment.content==="string"?<section aria-label="答案与核对内容"><h4>答案与核对内容</h4><p>{assessment.content}</p><small>来自本题绑定的知识修订快照</small></section>:null}
      <fieldset disabled={busy||!answerRevealed}><legend>按答案核对</legend><label><input type="radio" name="learning-correct" checked={checkedCorrect===true} onChange={()=>{setCheckedCorrect(true);eventId.current=null;}} /> 回答正确</label><label><input type="radio" name="learning-correct" checked={checkedCorrect===false} onChange={()=>{setCheckedCorrect(false);eventId.current=null;}} /> 回答不正确</label></fieldset>
      <label>学习者自评 <select value={rating} disabled={busy||!answerRevealed} onChange={event=>{setRating(event.target.value);eventId.current=null;}}><option value="">选择本次难度</option><option value="1">忘记</option><option value="2">困难</option><option value="3">一般</option><option value="4">轻松</option></select></label>
      <p>对错反馈与难度自评分别选择；当前 Core 复习合同要求答错选“忘记”，答对选“困难 / 一般 / 轻松”。两者均不会证明知识正确或机器能力。</p>
      {rating&&checkedCorrect!==null&&!ratingConsistent?<p role="alert">所选难度与对错不符合当前 Core 规则；答错选“忘记”，答对选择其他难度。</p>:null}
      <button disabled={busy||!assessment||!answer.trim()||!ratingConsistent} onClick={()=>void review()}>记录复习结果</button>
      <h4>机器能力状态</h4><p>{record(state.machine).status==="not_recorded"?"尚无机器能力记录。": "机器能力按 Core 回执单独记录。"}</p><RawReceiptButton label="机器能力记录回执" payload={state.machine} />
    </>})()}<details tabIndex={-1} data-section="record" aria-label="复习记录与回执"><summary>历史与回执</summary><p>{historySummary(history)}</p><RawReceiptButton label="复习历史与 Core 提交回执" payload={history} /></details></article>:null}
    {message?<p role="status">{message}</p>:null}
    {failureReason ? <p className="state-reason">{failureReason}</p> : null}</Section>;
}
