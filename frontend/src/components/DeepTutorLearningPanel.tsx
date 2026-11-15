import { useEffect, useRef, useState } from "react";
import type { DocumentDto } from "../api/generated/core-contract";
import { DeepTutorJourneySession, journeyEditor, journeyRecoveryCopy, parseJourney, snapshot, type JourneyAction } from "../presentation/deepTutorJourney";
import { useOptionalCoreWorkingState } from "../presentation/useCoreWorkingState";
import { useDraftOwner } from "../workspace/draftProtection";
import { useDraftRecoverySource } from "../workspace/draftRecovery";
import { useDocumentWriteLease } from "../workspace/documentSessions";
import { RawReceiptButton } from "./DiagnosticConsole";
import { downloadBytes, object, sameValue } from "../presentation/exchangeProof";

/** Model answer options may arrive as a keyed object or as an ordered list. The human
    review control has to show every option in both shapes; a silent empty select would
    make the answer key unverifiable. */
function optionEntries(raw:unknown):[string,unknown][]{
  if(Array.isArray(raw))return raw.map((text,index)=>[String.fromCharCode(65+index),text]);
  if(raw&&typeof raw==="object")return Object.entries(raw as Record<string,unknown>);
  return [];
}

/** Existing reading workspace's bounded teaching slice. It neither changes the shell nor infers mastery. */
export function DeepTutorLearningPanel({ document, onDirtyChange }: { document: DocumentDto; onDirtyChange?: (dirty:boolean)=>void }) {
  const working = useOptionalCoreWorkingState();
  const identity = working?.server;
  const [session,setSession] = useState<DeepTutorJourneySession|null>(null);
  const [busy,setBusy] = useState(false),[ready,setReady] = useState(false),[message,setMessage] = useState("");
  const [initialReading,setInitialReading] = useState(false);
  const [cancelling,setCancelling] = useState(false),[cancelMessage,setCancelMessage] = useState("");
  const [failure,setFailure] = useState<unknown>(),[dirty,setDirty] = useState(false);
  const [materialConsent,setMaterialConsent] = useState(false),[questionConsent,setQuestionConsent] = useState(false),[reviewed,setReviewed] = useState(false);
  const [,redraw] = useState(0);
  const lock = useRef(false),epoch = useRef(0),dirtyRef = useRef(false),latest = useRef(session);
  latest.current = session; dirtyRef.current = dirty;
  const owner = useDraftOwner("deeptutor-learning");
  const lease = useDocumentWriteLease(session?.document?.document_id??session?.journalDocumentId);
  const workingRef = useRef(working);workingRef.current=working;
  const dirtyCallback = useRef(onDirtyChange);dirtyCallback.current=onDirtyChange;
  const candidateIdentity=JSON.stringify(session?.value.candidate??null),questionIdentity=JSON.stringify(session?.value.question??null);
  const pendingRequestIdentity=JSON.stringify(session?.value.pending?.payload??null);
  useEffect(()=>{setCancelMessage("");},[pendingRequestIdentity]);
  useEffect(()=>{setReviewed(false);setQuestionConsent(false);},[candidateIdentity,questionIdentity]);
  useDraftRecoverySource(owner,"材料练习草稿",()=>latest.current && (dirtyRef.current||latest.current.unresolved)
    ?[{label:"材料练习 · "+document.title,text:JSON.stringify(journeyEditor(latest.current.value),null,2)}]:[]);
  useEffect(()=>{
    const value=dirty||busy||cancelling||!!session?.unresolved;
    dirtyCallback.current?.(value);
    window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner,dirty:value}}));
  },[dirty,busy,cancelling,session?.unresolved,owner]);
  useEffect(()=>()=>{dirtyCallback.current?.(false);window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner,dirty:false}}));},[owner]);
  useEffect(()=>{
    const current=++epoch.current;
    lock.current=false;setBusy(false);setReady(false);setInitialReading(false);setMaterialConsent(false);setQuestionConsent(false);setReviewed(false);setDirty(false);setMessage("");setFailure(undefined);
    setCancelling(false);setCancelMessage("");
    if(!identity || identity.recovery_requires_confirmation){setSession(null);return;}
    setInitialReading(true);
    const next:DeepTutorJourneySession=new DeepTutorJourneySession(snapshot(document),identity,undefined,async(id,editor,baseVersion)=>{
      if(current!==epoch.current)throw new Error("工作区已切换；未保存或发送新请求。");
      const drafts=workingRef.current?.session;
      if(!drafts||baseVersion===0)return;
      const prior=drafts.getSnapshot().state.drafts[id];
      if(prior&&prior.base_version!==baseVersion){
        if(prior.base_version+1!==baseVersion||!sameValue(prior.editor_json,next.document?.editor_json))throw new Error("学习草稿与保存版本不符；请先核对原文。");
        if(!await drafts.clearSaved(id,prior,baseVersion))throw new Error("原保存草稿清理未确认。");
      }
      const sent={base_version:baseVersion,editor_json:editor};
      drafts.rememberDraft(id,editor,baseVersion);await drafts.flush();
      return async saved=>{
        if(current!==epoch.current)throw new Error("工作区已切换；已保存记录保留待查询。");
        if(!await drafts.clearSaved(id,sent,saved.version))throw new Error("学习草稿已变化；新输入保留，请核对保存记录。");
      };
    },()=>{if(current===epoch.current)redraw(x=>x+1);});setSession(next);
    void next.load().then(async()=>{
      if(current!==epoch.current)return;
      const draft=next.document && workingRef.current?.state.drafts[next.document.document_id];
      if(draft){
        if(draft.base_version===next.document!.version-1&&sameValue(draft.editor_json,next.document!.editor_json)) {
          if(!await workingRef.current?.session.clearSaved(next.document!.document_id,draft,next.document!.version))throw new Error("已保存草稿清理尚未确认；原文保留。");
        } else {
          if(draft.base_version!==next.document!.version)throw new Error("学习草稿的保存版本已变化；先在恢复工具保留并比较原文。");
          const recovered=parseJourney({...next.document!,editor_json:draft.editor_json},snapshot(document));
          // The working draft owns editable input, never grant, candidate, activity or request state.
          for(const key of ["purpose","correct_answer","explanation","answer","reflection"] as const)next.value[key]=recovered[key];
          setDirty(true);
        }
      }
      if(current!==epoch.current)return;
      setReady(true);setMessage(next.value.pending?"找到原请求；请查询结果，不会自动重发。":next.document?"已读取此材料的学习记录，可从保存的阶段继续。":"本版本尚无学习记录；填写目标后可保存或开始材料授权。");
      redraw(x=>x+1);
    }).catch(error=>{if(current===epoch.current){setFailure(error);setMessage(error instanceof Error?error.message:"学习记录暂无法读取。 ");}})
      .finally(()=>{if(current===epoch.current)setInitialReading(false);});
    return()=>{epoch.current++;next.deactivate();};
  },[document.document_id,document.version,document.content_sha256,identity?.workspace_id,identity?.restore_epoch,identity?.recovery_requires_confirmation]);
  function edit(field:"purpose"|"correct_answer"|"explanation"|"answer"|"reflection",value:string){
    if(!session||busy||session.unresolved||!lease.canWrite)return;
    session.value={...session.value,[field]:value};setDirty(true);redraw(x=>x+1);
    if(field==="correct_answer"||field==="explanation")setReviewed(false);
    if(session.document)working?.session.rememberDraft(session.document.document_id,journeyEditor(session.value),session.document.version);
  }
  async function run(action:()=>Promise<void>){
    if(lock.current||initialReading||cancelling||!session||!lease.canWrite)return;
    lock.current=true;setBusy(true);setFailure(undefined);const current=epoch.current;
    try{
      await lease.write(action);
      if(current!==epoch.current)return;
      const saved=session.document,drafts=workingRef.current?.session;
      const committed=saved&&drafts?.getSnapshot().state.drafts[saved.document_id];
      if(saved&&committed&&committed.base_version+1===saved.version&&sameValue(committed.editor_json,saved.editor_json)){
        if(!await drafts!.clearSaved(saved.document_id,committed,saved.version))throw new Error("已保存输入的清理尚未确认；草稿保留。");
      }
      if(current!==epoch.current)return;
      setDirty(false);setReady(true);setMessage(session.recoveryState?journeyRecoveryCopy[session.recoveryState].title:"已保存并读回本次学习记录。作答和反馈不等于独立掌握。");
      redraw(x=>x+1);
    }catch(error){if(current===epoch.current){session.recordFailure(error);setFailure(error);setMessage(error instanceof Error?error.message:"结果尚未确认，请保留原记录并查询。");redraw(x=>x+1);}}
    finally{if(current===epoch.current){lock.current=false;setBusy(false);}}
  }
  function act(kind:JourneyAction){
    if(!session)return;
    if(kind==="material_grant"&&!materialConsent || kind==="question_grant"&&!questionConsent || kind==="accept"&&!reviewed)return;
    if(kind==="generate")setCancelMessage("");
    void run(()=>session.act(kind,kind==="material_grant"?"本人明确允许 DeepTutor 使用所示材料固定版本进行本地出题与练习。":kind==="question_grant"?"本人明确允许 DeepTutor 使用所示已接纳题目固定版本进行本地评分。":""));
  }
  async function cancelGeneration(){
    if(!session||initialReading||cancelling||!session.canCancelGeneration||!lease.canWrite)return;
    const current=epoch.current;setCancelling(true);setCancelMessage("");
    try{
      const receipt=await session.cancelGeneration();
      if(current!==epoch.current)return;
      setCancelMessage(receipt.cancel_requested?"已禁止此请求后续发布。模型服务是否停止仍未知；原请求保留，可继续查询。"
        :receipt.state==="COMPLETED"?"取消前已有完成结果；可查询并核对固定版本，未删除已保存内容。"
        :receipt.state==="FAILED"?"原请求已失败；可以查询并保留失败记录。"
        :"尚未找到原请求的登记，未确认停止；原请求可能稍后登记，请查询后再决定是否取消。");
    }catch(error){if(current===epoch.current){setFailure(error);setCancelMessage(error instanceof Error?error.message:"取消尚未确认；原请求保留，未重新生成。");}}
    finally{if(current===epoch.current){setCancelling(false);redraw(x=>x+1);}}
  }
  const value=session?.value;
  const recoveryState=session?.recoveryState;
  const recoveryCopy=recoveryState?journeyRecoveryCopy[recoveryState]:null;
  const frozenGoal=value?.pending?.kind==="generate"?object(value.pending.payload.body).requirement:undefined;
  const newTaskAfterFailure=!!value?.closed_requests?.length&&!value.candidate;
  const blocked=busy||cancelling||!ready||!lease.canWrite||!!session?.unresolved||!!working?.server?.recovery_requires_confirmation||["blocked","recovery","loading"].includes(working?.status??"loading");
  const candidate=session?.candidate;
  const question=session?.question?.question ? object(session.question.question):candidate;
  const options=optionEntries(question?.options);
  const result=session?.result?.result ? object(session.result.result):null;
  const observations=session?.guidance?.teaching_observations;
  const guidance=observations&&typeof observations==="object"&&!Array.isArray(observations)?Object.values(observations).map(row=>row&&typeof row==="object"?(row as Record<string,unknown>).text:null).filter((text):text is string=>typeof text==="string"):[];
  const focus=session?.guidance?.teaching_focus;
  const strategies=[session?.guidance?.teaching_guidance,focus&&typeof focus==="object"&&!Array.isArray(focus)?(focus as Record<string,unknown>).instruction:undefined].filter((text):text is string=>typeof text==="string");
  return <section aria-label="围绕材料学习与练习" className="imported-course-panel">
    <h3>围绕此材料练习</h3>
    <p>材料：{document.title} · 第 {document.version} 版。先生成候选、由你复核答案，再练习与反馈。基础阅读和笔记不需要执行这些步骤。</p>
    {!identity?<p role="status">正在核对本地工作区身份；普通阅读仍可继续。</p>:null}
    {!lease.canWrite?<p role="status">此学习记录已有编辑视图；当前只读，草稿保留。</p>:null}
    <label>本次学习目标<textarea maxLength={4000} disabled={blocked||!!value?.candidate} value={value?.purpose??""} onChange={e=>edit("purpose",e.target.value)}/></label>
    {!value?.material_grant?<fieldset disabled={blocked}><legend>材料授权</legend><label><input type="checkbox" checked={materialConsent} onChange={e=>setMaterialConsent(e.target.checked)}/>允许使用此材料固定版本进行本地出题与练习</label><button type="button" disabled={!materialConsent} onClick={()=>act("material_grant")}>保存材料授权</button></fieldset>:<p>已保存材料版本的练习授权；每次操作仍由 Core 核对是否有效。</p>}
    {!value?.candidate?<button type="button" disabled={blocked||!value?.material_grant||!value.purpose.trim()||!!value.unknown_requests.length} onClick={()=>act("generate")}>{newTaskAfterFailure?"开始新任务并重新生成题目":"生成一道题目候选"}</button>:null}
    {value?.pending?.kind==="generate"?<button type="button" disabled={initialReading||cancelling||!session?.canCancelGeneration||!lease.canWrite} onClick={()=>void cancelGeneration()}>{cancelling?"正在请求取消…":"取消本次生成"}</button>:null}
    {cancelMessage?<p role="status">{cancelMessage}</p>:null}
    {newTaskAfterFailure&&!session?.unresolved?<p>原失败记录已保留。可先修改目标；点击重新生成会创建新任务并再次调用本地模型。</p>:null}
    {question?<article aria-label="题目内容"><h4>{typeof question.question==="string"?question.question:"题目内容尚未核对"}</h4><ul>{options.map(([key,text])=><li key={key}>{key} · {typeof text==="string"?text:"不支持的选项内容"}</li>)}</ul></article>:null}
    {value?.candidate&&!value.question?<fieldset disabled={blocked}><legend>人工复核题目</legend><p>候选由模型生成，不能把模型给出的答案自动当作标准答案。</p>{options.length?<label>你确认的正确选项<select value={value.correct_answer} onChange={e=>edit("correct_answer",e.target.value)}><option value="">请选择</option>{options.map(([key])=><option key={key} value={key} data-value={key}>{key}</option>)}</select></label>:<p role="status">候选未提供可选项；请保留原文并重新生成题目，此处无法确认答案键。</p>}<label>你核对后的解释<textarea maxLength={8000} value={value.explanation} onChange={e=>edit("explanation",e.target.value)}/></label><label><input type="checkbox" checked={reviewed} onChange={e=>setReviewed(e.target.checked)}/>我已核对题目和答案，作为人工声明的答案键保存</label><button type="button" disabled={!reviewed||!value.correct_answer} onClick={()=>act("accept")}>接纳为练习题</button></fieldset>:null}
    {value?.question?<>
      <p>你已在复核中看过答案；本次是带参考自测，不作为独立评测或掌握证明。</p>
      {!value.question_grant?<fieldset disabled={blocked}><legend>题目评分授权</legend><label><input type="checkbox" checked={questionConsent} onChange={e=>setQuestionConsent(e.target.checked)}/>允许使用此接纳题目固定版本进行本地评分</label><button type="button" disabled={!questionConsent} onClick={()=>act("question_grant")}>保存题目授权</button></fieldset>:null}
      {!value.activity?<button type="button" disabled={blocked||!value.question_grant} onClick={()=>act("activity")}>建立本次材料练习</button>:null}
      {value.activity&&!value.attempt_id?<button type="button" disabled={blocked} onClick={()=>act("start")}>开始本次作答</button>:null}
      {value.attempt_id?<fieldset disabled={blocked||session?.result?.state==="submitted"}><legend>我的作答</legend><label>作答选项<select value={value.answer} onChange={e=>edit("answer",e.target.value)}><option value="">请选择</option>{options.map(([key])=><option key={key} value={key} data-value={key}>{key}</option>)}</select></label><button type="button" disabled={!value.answer} onClick={()=>act("grade")}>保存作答并评分</button></fieldset>:null}
      {result?<p role="status">本地供体评分：{result.provider_correct===true?"与人工答案键一致":result.provider_correct===false?"与人工答案键不同":"尚未确认"}。这不表示独立掌握，未自动安排复习。</p>:null}
    </>:null}
    {value?.attempt_id?<fieldset disabled={blocked}><legend>反馈与下一步学习</legend><label>本人的反馈与学习需要<textarea maxLength={300} value={value.reflection} onChange={e=>edit("reflection",e.target.value)}/></label><p>300字以内。作为本人自报观察交给教学规则，保留未核验状态；不会自动增加掌握度或写入复习成绩。</p><button type="button" disabled={!value.reflection.trim()} onClick={()=>act("feedback")}>保存反馈与教学策略</button>{guidance.length?<div aria-label="已保存的本人反馈"><h4>已保存的本人反馈</h4>{guidance.map((text,index)=><p key={index}>{text}</p>)}</div>:null}{strategies.length?<details><summary>DeepTutor 返回的教学策略原文</summary><p>这是供体规则返回的策略提示，不是新生成的讲解正文，也不证明已经学会。</p>{strategies.map((text,index)=><p key={index}>{text}</p>)}</details>:null}</fieldset>:null}
    {recoveryCopy?<section aria-label="原请求恢复状态" aria-live="polite"><h4>{recoveryCopy.title}</h4><p>{recoveryCopy.detail}</p>{typeof frozenGoal==="string"?<p>原学习目标：{frozenGoal}</p>:null}{recoveryState==="failed"?<button type="button" disabled={busy||!lease.canWrite} onClick={()=>void run(()=>session!.closeFailedRequest())}>保留失败记录并结束本次任务</button>:null}</section>:null}
    <div><button type="button" disabled={blocked} onClick={()=>void run(()=>session!.save())}>保存学习草稿</button>
      <button type="button" disabled={initialReading||busy||cancelling||!session||dirty&&!session.unresolved||!lease.canWrite} onClick={()=>void run(()=>session!.recover())}>查询原请求与已保存记录</button>
      <button type="button" disabled={!session} onClick={()=>{if(session)downloadBytes(session.recoveryRecord(),`DeepTutor-恢复-${document.document_id}-v${document.version}.json`,"application/json");}}>保全恢复记录到文件</button>
      {session?.document?<button type="button" disabled={blocked||!session.canStartNewRound} onClick={()=>{if(window.confirm("保留已保存题目和作答，新建一轮材料练习，确定吗？")){setCancelMessage("");void run(()=>session.newRound());}}}>保留历史并开始新一轮</button>:null}
    </div>
    {session?.unresolved?<p role="alert">原请求或保存结果尚未确认。只可查询和保全；不会重发生成、接纳或评分，也不能更换编号开始新一轮。</p>:null}
    {value?.unknown_requests.length?<details><summary>核对 {value.unknown_requests.length} 个未确认的历史请求</summary><p>接回旧请求只用于查询。当前轮次会先保存为历史，不会执行旧请求。</p>{value.unknown_requests.map((pending,index)=>pending.kind==="generate"?<button key={pending.document_id??index} type="button" disabled={busy||!!session?.unresolved||!lease.canWrite||!ready} onClick={()=>void run(()=>session!.resumeHistoricalRequest(index))}>接回第 {index+1} 个历史请求并查询</button>:<p key={index}>第 {index+1} 个历史操作需要原学习活动上下文；请保全恢复记录并核对原学习文档版本，不会重发。</p>)}</details>:null}
    {message&&!recoveryCopy?<p role="status">{message}</p>:null}
    {failure?<RawReceiptButton label="材料练习操作详情" payload={{error:failure instanceof Error?failure.message:String(failure),pending:value?.pending}}/>:null}
  </section>;
}
