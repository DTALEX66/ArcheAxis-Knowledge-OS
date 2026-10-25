import type {ModelLane} from "../api/generated/model-configuration-contract";
import {useEffect,useRef,useState,useSyncExternalStore} from "react";
import type {MaterialContextDto,MaterialSelectionDto} from "../api/generated/conversation";
import {CompanionSession} from "../companion/CompanionSession";
import {useOptionalCompanionSession,useStandaloneCompanionSession,useCompanionIdentityVerification} from "../companion/CompanionSessionProvider";
import {RawReceiptButton} from "./DiagnosticConsole";
import {FrozenRequestSummary} from "./FrozenRequestSummary";
import {XiaoqiAvatar, type XiaoqiPresentation} from "./XiaoqiAvatar";
import {xiaoqiStateLabels, type XiaoqiState} from "../companion/xiaoqiAssets";
function answerText(value:unknown):string{if(!value||typeof value!=="object")return "";const answer=(value as Record<string,unknown>).answer;return typeof answer==="string"?answer:"";}
type Props={materialTitle?:string;material?:MaterialContextDto;selection?:MaterialSelectionDto;slot?:"home"|"reader"|"sidebar"|"full"};
export function ConversationPanel(props:Props){
 const shared=useOptionalCompanionSession();
 return shared?<ConversationView {...props} session={shared}/>:<StandaloneConversation {...props}/>;
}
function StandaloneConversation(props:Props){const session=useStandaloneCompanionSession();return <ConversationView {...props} session={session}/>;}
function ConversationView({material,materialTitle,selection,slot="full",session}:Props&{session:CompanionSession}){
 const [characterView,setCharacterView]=useState<XiaoqiPresentation>(()=>slot==="sidebar"&&window.innerWidth>=1280&&window.innerHeight>=800?"portrait":"avatar");
 const {sessions,current,question,lane,preview,result,message,busy,paused,active,outstandingId,confirmedReceipts}=useSyncExternalStore(session.subscribe,session.getSnapshot,session.getSnapshot);
 const verifyIdentity=useCompanionIdentityVerification();
 const view=useRef({});
 const contextKey=JSON.stringify({material,selection});
 useEffect(()=>{session.contextChanged(view.current,contextKey);},[session,contextKey]);
 const terminal=session.terminal(),uncertain=session.uncertain();
 const lastKind=current?.events.at(-1)?.kind;
 const visibleState:XiaoqiState=busy&&active?"thinking":terminal==="cancelled"?"interrupted":terminal==="failed"?"failed":terminal==="completed"?"completed":uncertain?"idle":preview?"awaiting_approval":lastKind==="cancelled"?"interrupted":lastKind==="failed"?"failed":lastKind==="completed"?"completed":"idle";
 const requestState = (state: string) => ({completed: "已完成", failed: "未完成", cancelled: "已取消", EXECUTING: "结果待确认"}[state] ?? "待核对");
 const characterHint=paused?"先核对工作区，确认后可继续。":uncertain?"结果尚未确认，请查询原请求。":busy&&active?"正在处理已确认的请求。":preview?"检查材料与请求后，再确认执行。":terminal==="completed"?"回答已返回，可以查看依据并指出错误。":terminal==="failed"?"本次未完成，可以查询原请求或查看诊断。":terminal==="cancelled"?"本次已中断，草稿和会话历史仍保留。":"可以从一段材料或一个问题开始。";
 return <section aria-label={slot==="full"?"正式陪伴会话":`${{home:"首页",reader:"阅读区",sidebar:"侧栏"}[slot]}小栖会话`} data-companion-slot={slot}>
  <div className={`companion-context-header${slot==="sidebar"?" companion-character-header":""}`} data-character-view={characterView}><XiaoqiAvatar state={visibleState} size="md" presentation={characterView}/><div className="companion-character-copy">{slot==="sidebar"?<><strong className="companion-character-name">小栖</strong><br/><span className="companion-character-state">{paused?"工作区待核对":uncertain?"请求待核对":xiaoqiStateLabels[visibleState]}</span></>:null}<h3>{material?"材料学习会话":"本地陪伴会话"}</h3>
  <p>{characterHint}</p>{slot==="sidebar"?<div className="companion-character-views" role="group" aria-label="小栖展示方式">{([["portrait","半身"],["figure","全幅"],["avatar","收起人物"]] as const).map(([value,label])=><button type="button" key={value} aria-pressed={characterView===value} onClick={()=>setCharacterView(value)}>{label}</button>)}</div>:null}</div></div>
  {paused&&verifyIdentity?<button onClick={()=>void verifyIdentity()}>核对陪伴工作区</button>:null}
  <div className="companion-session-actions"><button disabled={busy||paused} onClick={()=>void session.refreshCatalog()}>重读会话目录</button>
  <button className={!current?"companion-create-primary":undefined} disabled={busy||paused} onClick={()=>void session.create()}>新建陪伴会话</button></div>
  <label>已保存会话<select disabled={busy||paused} value={current?.session_id??""} onChange={e=>void session.load(e.target.value)}><option value="">选择会话</option>{sessions.map((s,index)=><option key={s.session_id} value={s.session_id}>{s.title} · {index+1}</option>)}</select></label>
  {current?<>
   <p>当前会话：{current.title}</p><RawReceiptButton label="会话运行记录" payload={current} visibleLabel="查看会话诊断"/>
   <button disabled={busy||paused} onClick={()=>void session.load(current.session_id)}>重读历史</button>
   {current.events.map(event=><div key={event.sequence}>
    {event.kind==="accepted"?<p>{"question" in event.data?event.data.question:""}</p>:null}
    {event.kind==="completed"&&"answer" in event.data&&answerText(event.data.answer)!==""?<p style={{whiteSpace:"pre-wrap"}}>{answerText(event.data.answer)}</p>:null}
    {event.kind==="failed"||event.kind==="cancelled"?<p>{requestState(event.kind)}，可以查看诊断或查询原请求。</p>:null}
   </div>)}
   {confirmedReceipts.filter(r=>r.state==="completed"&&answerText(r.answer)!==""&&!current.events.some(e=>e.request_id===r.request_id&&e.kind==="completed"&&"answer" in e.data&&answerText(e.data.answer)!=="")).map(r=><p key={r.request_id} style={{whiteSpace:"pre-wrap"}}>{answerText(r.answer)}</p>)}
   {(current.events.at(-1)?.sequence??0)<current.last_sequence?<button disabled={busy||paused} onClick={()=>void session.more()}>读取后续会话事件</button>:null}
   {current.requests.map((r,index)=><button key={r.request_id} disabled={busy||paused} onClick={()=>void session.readRequest(r.request_id)}>查询第 {index+1} 次提问 · {requestState(confirmedReceipts.find(receipt=>receipt.request_id===r.request_id)?.state??r.state)}</button>)}
   <label>会话模型通道<select disabled={busy||paused||uncertain} value={lane} onChange={e=>{session.setLane(e.target.value as ModelLane);}}><option value="fast">快速</option><option value="deep">深度</option></select></label>
   <label>会话问题<textarea disabled={busy||paused} value={question} onChange={e=>{session.setQuestion(e.target.value);}}/></label>
   <button disabled={busy||paused||uncertain||!question.trim()} onClick={()=>void session.prepare({material,selection},view.current)}>预览会话请求</button>
   {preview?<><FrozenRequestSummary request={preview.plan.request} materialPresentation={material&&materialTitle?{identity:material,title:materialTitle}:undefined} destinationCandidates={preview.plan.destination_candidates}/><RawReceiptButton label="会话冻结请求与目的地" payload={preview} category="runtime"/><button disabled={busy||paused||uncertain} onClick={()=>void session.execute()}>确认执行同一会话请求</button></>:null}
   {busy&&active?<button onClick={()=>void session.cancel()}>取消会话请求</button>:null}
  </>:null}
  {uncertain&&outstandingId?<><p role="status">请求状态未确认，请查询原请求。</p><button disabled={busy||paused} onClick={()=>void session.readRequest(outstandingId)}>查询未确认请求</button></>:null}
  {result?<RawReceiptButton label="原请求会话回执" payload={result}/>:null}
  {message?<p role="status">{message}</p>:null}
 </section>;
}
