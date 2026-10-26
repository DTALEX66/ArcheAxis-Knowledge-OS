import { useEffect, useRef, useState } from "react";
import {useOptionalCoreWorkingState} from "../presentation/useCoreWorkingState";
import type {LearningDraft, PendingReview} from "../presentation/coreWorkingState";
import { courseLearningTarget } from "../presentation/courseLearningTarget";
import { coreCommand } from "../api/core";
import type {LearningItemsDto} from "../api/generated/core-contract";
import {learningTitle} from "../presentation/learningTitle";
import { ApiError } from "../api/client";
import { RawReceiptButton } from "../components/DiagnosticConsole";
import type { ObjectTrailLevel } from "../components/NavTrail";
import { coreFailureReason, failureMessage } from "../presentation/labels";
import "./stitch-learning.css";
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
import {assertJourneyAssessment,type LearningJourneyTarget} from "../presentation/learningJourney";

export function CanonicalLearningSpace({active=true,onTrail, initialItemKey, expectedJourney, onItemSelected, onReturnCourse}:{active?:boolean;onReturnCourse?:(key:string,knowledgeId:string,knowledgeVersion:string)=>void;onItemSelected?:(key:string)=>void;expectedJourney?:LearningJourneyTarget;onTrail?:(levels:readonly ObjectTrailLevel[])=>void; initialItemKey?:string} = {}) {
  const working=useOptionalCoreWorkingState();
  const journalReview=useRef<PendingReview|null>(null);
  const journalWorkspace=useRef<{workspace_id:string;restore_epoch:string}|null>(null);
  const localDrafts=useRef<Record<string,LearningDraft>>({});
  const draftAtReview=useRef<LearningDraft|undefined>(undefined);
  const [focusMode, setFocusMode] = useState(false);
  useEffect(()=>{if(!active&&focusMode){setFocusMode(false);window.dispatchEvent(new CustomEvent("archeaxis-learning-focus",{detail:false}));}},[active,focusMode]);
  const [items, setItems] = useState<LearningItemsDto["items"]>([]);
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
  const [failureDetails, setFailureDetails] = useState<{message:string;status?:number;code?:string}|null>(null);
  function captureFailure(error: unknown) {
    setFailureDetails({message:error instanceof Error?error.message:String(error),...(error instanceof ApiError?{status:error.status,code:error.code}:{})});
  }
  const [busy, setBusy] = useState(false);
  const epoch = useRef(0);
  const eventId = useRef<string|null>(null);
  const frozenReview = useRef<Record<string,unknown>|null>(null);
  const [reviewPending,setReviewPending] = useState(false);
  const initialSelectionContext=useRef<{workspaceId?:string;restoreEpoch?:string;recovery?:boolean}|null>(null);
  const dirtyOwner = useRef(`learning-review:${crypto.randomUUID()}`).current;
  const learningDrafts=working?.state.learning_drafts??localDrafts.current;
  useEffect(()=>{window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner:dirtyOwner,dirty:reviewPending||busy||Object.keys(learningDrafts).length>0}}));},[reviewPending,busy,learningDrafts,answer,rating,dirtyOwner]);
  useEffect(()=>()=>{window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner:dirtyOwner,dirty:false}}));},[dirtyOwner]);
  async function refresh() {
    try {
      const list = await coreCommand<LearningItemsDto>("learning_items");
      if (!Array.isArray(list.items)) throw new Error("invalid items");
      if (list.items.some(row=>typeof row.item_key !== "string")) throw new Error("invalid item key");
      setItems(list.items);
    } catch (error) {setMessage("学习队列读取失败，请重试。");setFailureReason(coreFailureReason(error));}
  }
  useEffect(()=>{void refresh();return()=>{epoch.current+=1;};},[]);
  useEffect(()=>{
    const context={workspaceId:working?.server?.workspace_id,restoreEpoch:working?.server?.restore_epoch,recovery:working?.server?.recovery_requires_confirmation};
    const previous=initialSelectionContext.current;
    const sameContext=previous!==null&&previous.workspaceId===context.workspaceId&&previous.restoreEpoch===context.restoreEpoch&&previous.recovery===context.recovery;
    initialSelectionContext.current=context;
    // A shell callback echoes our successful selection through initialItemKey.
    // Skip only that already-loaded identity; a new workspace/restore must reread.
    if(initialItemKey&&(!working||working.server&&!working.server.recovery_requires_confirmation)
      &&!(sameContext&&itemKey===initialItemKey&&state?.item_key===initialItemKey))void open(initialItemKey);
  },[initialItemKey,working?.server?.workspace_id,working?.server?.restore_epoch,working?.server?.recovery_requires_confirmation]);
  const pendingReviews=Object.values(working?.state.pending_reviews??{});
  useEffect(()=>{const entries=Object.values(working?.state.pending_reviews??{});const entry=initialItemKey?entries.find(row=>row.item_key===initialItemKey):entries.length===1?entries[0]:undefined;if(entry&&!frozenReview.current)void open(entry.item_key,entry);},[working?.state.pending_reviews,initialItemKey]);
  useEffect(()=>{
    const entry=journalReview.current,basis=journalWorkspace.current,server=working?.server;
    if(!working||busy||!entry||!basis||!server||working.status==="blocked"||working.status==="recovery"||server.recovery_requires_confirmation
      ||server.workspace_id!==basis.workspace_id||server.restore_epoch!==basis.restore_epoch
      ||working.state.pending_reviews?.[entry.client_event_id]||server.state.pending_reviews?.[entry.client_event_id]
      ||frozenReview.current?.client_event_id!==entry.client_event_id)return;
    // Another retained view confirmed this exact request in this controller's
    // context. A preserved request may legitimately retain an older origin epoch.
    // Reopen shared raw drafts instead of copying this view's old answer.
    journalReview.current=null;journalWorkspace.current=null;frozenReview.current=null;eventId.current=null;draftAtReview.current=undefined;setReviewPending(false);
    void open(itemKey);
  },[working?.state.pending_reviews,working?.server,working?.status,busy,itemKey]);
  useEffect(() => {
    const levels: ObjectTrailLevel[] = [];
    if (itemKey && state) {
      const item = items.find((row) => row.item_key === itemKey);
      levels.push(
        { id: "section:review", label: "复习队列", region: "review" },
        { id: `item:${itemKey}`, label: learningTitle(item?.display_title, expectedJourney?.display_title, "学习项目（标题尚未核对）"), detail: typeof item?.next_review === "string" ? `下次复习 ${item.next_review}` : "下次复习未安排", region: "review" },
      );
    }
    onTrail?.(levels);
  }, [itemKey, state, items, onTrail, expectedJourney?.display_title]);
  function currentDrafts(){return working?.session.getSnapshot().state.learning_drafts??localDrafts.current;}
  async function discardDraft(draft:LearningDraft) {
    if(busy||Object.values(working?.session.getSnapshot().state.pending_reviews??{}).some(entry=>entry.item_key===draft.item_key)||frozenReview.current&&itemKey===draft.item_key)return;
    if(!window.confirm(`丢弃 ${draft.item_key}（${draft.knowledge_version}）的未提交答案？此操作不会创建复习记录。`))return;
    const current=++epoch.current;setBusy(true);
    try{
      if(working)await working.session.discardLearningDraft(draft);
      else if(localDrafts.current[draft.assessment_id]===draft){const next={...localDrafts.current};delete next[draft.assessment_id];localDrafts.current=next;}
      const assessment=state&&record(state.learner).assessment;
      if(current===epoch.current&&assessment&&record(assessment).assessment_id===draft.assessment_id&&!currentDrafts()[draft.assessment_id]){setAnswer("");setRating("");setCheckedCorrect(null);setAnswerRevealed(false);draftAtReview.current=undefined;}
      setMessage(currentDrafts()[draft.assessment_id]?"原草稿已丢弃，较新的本地输入仍保留。":working?"已丢弃这份学习草稿。":"已丢弃本次页面中的学习草稿。");
    }catch(error){captureFailure(error);setMessage(`${failureMessage(error)} 丢弃未确认，原答案保留。`);}finally{setBusy(false);}
  }
  function edit(patch:Partial<Pick<LearningDraft,"answer"|"rating"|"checked_correct"|"answer_revealed">>) {
    if(!state||busy||reviewPending||frozenReview.current)return;
    const assessment=record(record(state.learner).assessment);
    if(typeof assessment.assessment_id!=="string"||typeof assessment.knowledge_version!=="string")return;
    const draft:LearningDraft={item_key:itemKey,assessment_id:assessment.assessment_id,knowledge_version:assessment.knowledge_version,
      ...(typeof assessment.question_version==="string"?{question_version:assessment.question_version}:{}),
      answer,rating:rating?Number(rating):null,checked_correct:checkedCorrect,answer_revealed:answerRevealed,...patch};
    try {
      if(working)working.session.rememberLearningDraft(draft);else localDrafts.current={...localDrafts.current,[draft.assessment_id]:draft};
      setAnswer(draft.answer);setRating(draft.rating===null?"":String(draft.rating));setCheckedCorrect(draft.checked_correct);setAnswerRevealed(draft.answer_revealed);eventId.current=null;
    }catch(error){captureFailure(error);setMessage(`${failureMessage(error)} 学习草稿保存未确认，原答案保留。`);}
  }
  async function open(key: string, restored?:PendingReview) {
    if(busy&&frozenReview.current)return;
    restored??=Object.values(working?.session.getSnapshot().state.pending_reviews??{}).find(row=>row.item_key===key);
    const retained=journalReview.current&&working?.session.getSnapshot().state.pending_reviews?.[journalReview.current.client_event_id];
    if(frozenReview.current&&(!restored||!retained)){setMessage("复习结果尚未确认；请重试同一次提交。原答案仍保留。");return;}
    if(restored){journalReview.current=restored;const server=working?.session.getSnapshot().server;journalWorkspace.current=server?{workspace_id:server.workspace_id,restore_epoch:server.restore_epoch}:null;frozenReview.current=structuredClone(restored.body);eventId.current=restored.client_event_id;setReviewPending(true);}
    const current = ++epoch.current; setState(null);setHistory(null);setItemKey(key);setFailureReason(null);setFailureDetails(null);if(!restored)eventId.current=null;
    try {
      const [raw, events] = await Promise.all([coreCommand("learning_state",{item_key:key}),coreCommand("learning_history",{item_key:key})]);
      const data = record(raw);
      if (data.item_key !== key || !data.learner || !data.machine) throw new Error("invalid learning state");
      if(restored){const assessment=record(record(data.learner).assessment);if(assessment.assessment_id!==restored.body.assessment_id||assessment.knowledge_version!==restored.body.knowledge_version)throw new Error("frozen assessment changed");}
      if(expectedJourney){if(key!==expectedJourney.item_key)throw new Error("different pinned learning item");assertJourneyAssessment(record(data.learner).assessment,expectedJourney);}
      if (current === epoch.current) {
        const assessment=record(data.learner).assessment;
        const bound=assessment&&typeof assessment==="object"?assessment as Record<string,unknown>:null;
        const candidate=bound&&typeof bound.assessment_id==="string"?currentDrafts()[bound.assessment_id]:undefined;
        const draft=candidate&&candidate.item_key===key&&candidate.knowledge_version===bound?.knowledge_version&&candidate.question_version===(typeof bound?.question_version==="string"?bound.question_version:undefined)?candidate:undefined;
        draftAtReview.current=draft;
        setAnswer(restored?.body.answer??draft?.answer??"");setRating(restored?String(restored.body.rating):draft?.rating?String(draft.rating):"");setCheckedCorrect(restored?.body.correct??draft?.checked_correct??null);setAnswerRevealed(!!restored||!!draft?.answer_revealed);
        setState(data);setHistory(events);setMessage(candidate&&!draft?"已有草稿与当前题目修订不同；原答案单独保留，未套入当前题目。":"");if(key!==initialItemKey)onItemSelected?.(key);
      }
    } catch (error) {if(current===epoch.current){setMessage("学习记录读取失败，暂时不能提交结果。");setFailureReason(coreFailureReason(error));}}
  }
  async function review() {
    if (!state || busy) return;
    const current = epoch.current;setBusy(true);setFailureDetails(null);
    // Keep the same event key for retries of the same answer, preventing duplicates.
    eventId.current ??= crypto.randomUUID();
    try {
      const learner = record(state.learner);
      const assessment = learner.assessment ? record(learner.assessment) : null;
      if (!assessment || typeof assessment.assessment_id !== "string" || typeof assessment.question !== "string" || typeof assessment.knowledge_version !== "string") throw new Error("a real assessment is required");
      if(expectedJourney){assertJourneyAssessment(assessment,expectedJourney);if(itemKey!==expectedJourney.item_key)throw new Error("different pinned learning item");}
      if (!answer.trim() || checkedCorrect === null || !rating) throw new Error("answer, answer check and self-rating are required");
      if (!ratingConsistent) throw new Error("The Core review contract requires rating 1 for an incorrect answer, and rating 2-4 for a correct answer.");
      const body:Record<string,unknown> = {item_key:itemKey,client_event_id:eventId.current,correct:checkedCorrect,rating:Number(rating),answer:answer.trim()};
      if (assessment) {
        for (const field of ["assessment_id","question_version","knowledge_version"] as const) if (typeof assessment[field] === "string") body[field]=assessment[field];
      }
      if(!frozenReview.current)draftAtReview.current=currentDrafts()[String(body.assessment_id)];
      frozenReview.current ??= structuredClone(body);setReviewPending(true);
      if(working){const server=working.session.getSnapshot().server;if(!server)throw new Error("工作日志尚未读回，未发送复习。");journalReview.current??={item_key:itemKey,client_event_id:String(frozenReview.current.client_event_id),body:structuredClone(frozenReview.current) as PendingReview["body"],origin_restore_epoch:server.restore_epoch};journalWorkspace.current??={workspace_id:server.workspace_id,restore_epoch:server.restore_epoch};
        try{await working.session.freezeReview(journalReview.current);}catch(error){
          // A local preflight refusal has no frozen Core intent to retry. Unknown write ACKs retain their journal.
          if(!working.session.getSnapshot().state.pending_reviews?.[journalReview.current.client_event_id]){journalReview.current=null;journalWorkspace.current=null;frozenReview.current=null;eventId.current=null;setReviewPending(false);}
          throw error;
        }
      }
      const receipt = record(await coreCommand("learning_review",{body:structuredClone(frozenReview.current)}));
      if(working&&journalReview.current)await working.session.finishReview(journalReview.current,draftAtReview.current);
      else if(draftAtReview.current&&localDrafts.current[draftAtReview.current.assessment_id]===draftAtReview.current){const next={...localDrafts.current};delete next[draftAtReview.current.assessment_id];localDrafts.current=next;}
      draftAtReview.current=undefined;
      journalReview.current=null;journalWorkspace.current=null;frozenReview.current=null;setReviewPending(false);
      if (current === epoch.current) {await open(itemKey);const scheduled=typeof receipt.next_review==="string"?`下次复习：${receipt.next_review}`:receipt.next_review_days===-1?"学习记录已保存；暂时无法安排下次复习。":"学习记录已保存；下次复习时间未提供。";setMessage(`复习记录已保存。${scheduled}`);setHistory((previous:unknown)=>({receipt,history:previous}));await refresh();}
    } catch (error) {captureFailure(error);if(working&&!journalReview.current&&!frozenReview.current){setMessage(`${failureMessage(error)} 未发送复习，答案仍可编辑。`);return;}if(!journalReview.current&&error instanceof ApiError && error.status>=400 && error.status<500){frozenReview.current=null;setReviewPending(false);}setMessage(error instanceof ApiError && error.status >= 400 && error.status < 500
      ? `复习提交未完成。${failureMessage(error)} 请检查答案与自评，答案仍保留。`
      : "复习提交未确认，请保留答案并用同一条目重试；不会假定成功。");}
    finally {setBusy(false);}
  }
  const queue = <>{!focusMode?<button onClick={()=>void refresh()}>刷新学习队列</button>:null}
    <ul className="stitch-learning-queue" tabIndex={-1} data-section="review" aria-label="复习队列">{items.map(item=><li key={String(item.item_key)}><button aria-pressed={itemKey===item.item_key} data-learning-item-key={item.item_key} disabled={busy} onClick={()=>void open(item.item_key)}>{learningTitle(item.display_title, "学习项目（标题尚未核对）")}</button> · 下次复习 {typeof item.next_review === "string" ? item.next_review : "未安排"}</li>)}</ul></>;
  return <section className="stitch-learning-review" data-focus={focusMode} aria-label={expectedJourney?"练习与复习":"学习"}><header className="stitch-learning-review-heading"><div><p className="stitch-learning-eyebrow">学习项目 · 绑定题目与版本</p><h2>{expectedJourney?"练习与复习":"学习"}</h2></div><button type="button" aria-pressed={focusMode} onClick={()=>{const next=!focusMode;setFocusMode(next);window.dispatchEvent(new CustomEvent("archeaxis-learning-focus",{detail:next}));}}>{focusMode?"退出聚焦模式":"进入聚焦模式"}</button></header>
    {Object.values(learningDrafts).length>0?<section className="stitch-learning-drafts stitch-learning-glass" aria-label="未提交学习草稿"><p>以下答案尚未提交复习；题目修订分别保留。</p>{Object.values(learningDrafts).map(draft=><details key={draft.assessment_id}><summary>学习草稿 · {learningTitle(items.find(item=>item.item_key===draft.item_key)?.display_title, expectedJourney?.item_key===draft.item_key?expectedJourney.display_title:undefined, "学习项目（标题尚未核对）")}</summary><p>学习项目键 {draft.item_key} · 知识修订 {draft.knowledge_version}</p><label>保留的学习答案 {draft.assessment_id}<textarea readOnly value={draft.answer}/></label><button disabled={busy} onClick={()=>void open(draft.item_key)}>打开草稿题目 {draft.item_key}</button><button disabled={busy||pendingReviews.some(entry=>entry.item_key===draft.item_key)||reviewPending&&itemKey===draft.item_key} onClick={()=>void discardDraft(draft)}>丢弃草稿 {draft.item_key}</button></details>)}</section>:null}
    {pendingReviews.length>1?<section className="stitch-learning-glass" aria-label="未确认复习请求"><p>有多个未确认的复习请求，请明确选择；其他请求仍保留。</p>{pendingReviews.map(entry=><button key={entry.client_event_id} disabled={busy} onClick={()=>void open(entry.item_key)}>恢复复习请求 {entry.item_key}</button>)}</section>:null}
    <section className="stitch-learning-glass" aria-label="学习项目目录"><header className="stitch-learning-card-heading"><h3>学习队列</h3><span>当前已读 {items.length} 项</span></header>{expectedJourney?<details aria-label="学习队列工具"><summary>学习队列</summary>{queue}</details>:queue}</section>
    <details className="stitch-learning-locator" aria-label="按键定位学习项目"><summary>按学习项目键定位</summary><form onSubmit={event=>{event.preventDefault();void open(itemKey);}}><label>学习项目键 <input value={itemKey} disabled={busy||reviewPending} onChange={event=>{epoch.current+=1;setItemKey(event.target.value);setState(null);}} /></label><button disabled={!itemKey.trim()||busy} title={!itemKey.trim()?"需要先输入学习项目键":undefined}>读取项目</button></form></details>
    {state?<article className="stitch-learning-assessment stitch-learning-glass">{(()=>{const learner=record(state.learner);const assessment=learner.assessment?record(learner.assessment):null;return <>
      {!expectedJourney?<p aria-label="当前学习项目">{learningTitle(items.find(item=>item.item_key===itemKey)?.display_title, "学习项目（标题尚未核对）")}</p>:null}
      <h3>复习题</h3>
      {onReturnCourse && courseLearningTarget(itemKey) && assessment && typeof assessment.knowledge_id === "string" && assessment.knowledge_id.length > 0 && assessment.knowledge_version === assessment.knowledge_id ? <button type="button" disabled={busy||reviewPending} onClick={()=>onReturnCourse(itemKey, assessment.knowledge_id as string, assessment.knowledge_version as string)}>返回原课程与绑定版本</button> : null}
      {assessment&&typeof assessment.question==="string"?<p>{assessment.question}</p>:<p>此学习项目没有可用的真实题目。请从知识页面创建学习题后再来复习。</p>}
      <RawReceiptButton label="学习项目与题目版本" category="data" payload={{item_key:state.item_key,...Object.fromEntries(["assessment_id","question_version","knowledge_id","knowledge_version","source_id","anchor_id"].filter(field=>assessment?.[field]!==undefined).map(field=>[field,assessment![field]]))}} />
      <section className="stitch-learning-answer"><h4>先独立作答</h4><label>本次答案 <textarea value={answer} disabled={busy||reviewPending||!assessment||!!working&&!working.server} onChange={event=>edit({answer:event.target.value,checked_correct:null,rating:null})} /></label>
      <button type="button" disabled={busy||!assessment||!answer.trim()} onClick={()=>edit({answer_revealed:true})}>{answerRevealed?"已显示核对内容":"查看答案与核对内容"}</button></section>
      {answerRevealed&&assessment&&typeof assessment.content==="string"?<section className="stitch-learning-revealed" aria-label="答案与核对内容"><h4>答案与核对内容</h4><p>{assessment.content}</p><small>来自本题绑定的知识修订快照</small></section>:null}
      <div className="stitch-learning-review-controls"><fieldset disabled={busy||reviewPending||!answerRevealed}><legend>按答案核对</legend><label><input type="radio" name="learning-correct" checked={checkedCorrect===true} onChange={()=>edit({checked_correct:true})} /> 回答正确</label><label><input type="radio" name="learning-correct" checked={checkedCorrect===false} onChange={()=>edit({checked_correct:false})} /> 回答不正确</label></fieldset>
      <label>学习者自评 <select value={rating} disabled={busy||reviewPending||!answerRevealed} onChange={event=>edit({rating:event.target.value?Number(event.target.value):null})}><option value="">选择本次难度</option><option value="1">忘记</option><option value="2">困难</option><option value="3">一般</option><option value="4">轻松</option></select></label>
      <p>对错反馈与难度自评分别选择；当前复习规则要求答错选“忘记”，答对选“困难 / 一般 / 轻松”。两者均不会证明知识正确或机器能力。</p>
      {rating&&checkedCorrect!==null&&!ratingConsistent?<p role="alert">所选难度与对错不符合当前复习规则；答错选“忘记”，答对选择其他难度。</p>:null}
      <button disabled={busy||!assessment||!answer.trim()||!ratingConsistent} onClick={()=>void review()}>记录复习结果</button></div>
      <section className="stitch-learning-machine"><h4>机器能力状态</h4><p>{record(state.machine).status==="not_recorded"?"尚无机器能力记录。": "机器能力有单独记录，请查看详情。"}</p><RawReceiptButton label="机器能力详细记录" payload={state.machine} /></section>
    </>})()}<details className="stitch-learning-history" tabIndex={-1} data-section="record" aria-label="复习记录与回执"><summary>历史与回执</summary><p>{historySummary(history)}</p><RawReceiptButton label="复习历史与提交详情" payload={history} /></details></article>:null}
    {message?<p role="status">{message}</p>:null}
    {failureDetails?<RawReceiptButton label="学习操作错误详情" payload={failureDetails}/>:null}
    {failureReason ? <p className="state-reason">{failureReason}</p> : null}</section>;
}
