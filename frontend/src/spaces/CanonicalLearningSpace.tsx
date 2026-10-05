import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import { Section } from "../components/RealData";
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("invalid response");
  return value as Record<string, unknown>;
}
export function CanonicalLearningSpace() {
  const [items, setItems] = useState<Record<string, unknown>[]>([]);
  const [itemKey, setItemKey] = useState("");
  const [state, setState] = useState<Record<string, unknown>|null>(null);
  const [history, setHistory] = useState<unknown>(null);
  const [answer, setAnswer] = useState("");
  const [rating, setRating] = useState(1);
  const [message, setMessage] = useState("");
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
    } catch {setMessage("学习队列读取失败，请重试。");}
  }
  useEffect(()=>{void refresh();return()=>{epoch.current+=1;};},[]);
  async function open(key: string) {
    const current = ++epoch.current; setState(null);setHistory(null);setItemKey(key);setAnswer("");eventId.current=null;
    try {
      const [raw, events] = await Promise.all([coreCommand("learning_state",{item_key:key}),coreCommand("learning_history",{item_key:key})]);
      const data = record(raw);
      if (data.item_key !== key || !data.learner || !data.machine) throw new Error("invalid learning state");
      if (current === epoch.current) {setState(data);setHistory(events);setMessage("");}
    } catch {setMessage("学习记录读取失败，暂时不能提交结果。");}
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
      const body:Record<string,unknown> = {item_key:itemKey,client_event_id:eventId.current,correct:rating!==1,rating,answer};
      if (assessment) {
        for (const field of ["assessment_id","question_version","knowledge_version"] as const) if (typeof assessment[field] === "string") body[field]=assessment[field];
      }
      const receipt = record(await coreCommand("learning_review",{body}));
      if (current === epoch.current) {await open(itemKey);setMessage("复习结果已记录，时间安排以 Core 回执为准。");setHistory((previous:unknown)=>({receipt,history:previous}));await refresh();}
    } catch {setMessage("复习提交未确认，请保留答案并重试；不会假定成功。");}
    finally {setBusy(false);}
  }
  return <Section title="学习"><p>学习者记录与机器能力分别显示。记录复习结果不会自动证明机器能力或知识正确性。</p><button onClick={()=>void refresh()}>刷新学习队列</button>
    <ul>{items.map(item=><li key={String(item.item_key)}><button disabled={busy} onClick={()=>void open(String(item.item_key))}>{String(item.item_key)}</button> · 下次复习 {typeof item.next_review === "string" ? item.next_review : "未安排"}</li>)}</ul>
    <form onSubmit={event=>{event.preventDefault();void open(itemKey);}}><label>学习项目键 <input value={itemKey} disabled={busy} onChange={event=>{epoch.current+=1;setItemKey(event.target.value);setState(null);}} /></label><button disabled={!itemKey.trim()||busy}>读取项目</button></form>
    {state?<article><h4>学习者与实际问题</h4><pre>{JSON.stringify(state.learner,null,2)}</pre><h4>机器能力</h4><pre>{JSON.stringify(state.machine,null,2)}</pre><label>本次答案 <textarea value={answer} disabled={busy} onChange={event=>{setAnswer(event.target.value);eventId.current=null;}} /></label><label>自评结果 <select value={rating} disabled={busy} onChange={event=>{setRating(Number(event.target.value));eventId.current=null;}}><option value={1}>忘记 / 错误</option><option value={2}>困难但正确</option><option value={3}>正确</option><option value={4}>轻松正确</option></select></label><button disabled={busy||!record(state.learner).assessment} onClick={()=>void review()}>记录复习结果</button><details><summary>历史与回执</summary><pre>{JSON.stringify(history,null,2)}</pre></details></article>:null}
    {message?<p role="status">{message}</p>:null}</Section>;
}
