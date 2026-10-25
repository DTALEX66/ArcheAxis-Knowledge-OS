import {materialModelFailureMessage} from "../api/machineFailure";
import {resolveProductModel,ModelBindingRequiredError} from "../runtime/modelBinding";
import type {ModelLane,ResolvedModel} from "../api/generated/model-configuration-contract";
import {useEffect,useRef,useState} from "react";
import {coreCommand} from "../api/core";
import {assertMaterialQuestionDto} from "../api/generated/material-question";
import type {MaterialContextDto,MaterialQuestionRequestDto} from "../api/generated/material-question";
import {RawReceiptButton} from "./DiagnosticConsole";
import {FrozenRequestSummary} from "./FrozenRequestSummary";
import {ModelConfigurationPanel} from "./ModelConfigurationPanel";
import {textareaOriginalRange} from "../presentation/originalTextSelection";
async function hash(text:string){return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(text)))).map(b=>b.toString(16).padStart(2,"0")).join("");}
function materialKey(value:unknown){return value&&typeof value==="object"?JSON.stringify(Object.fromEntries(Object.entries(value).sort(([a],[b])=>a.localeCompare(b)))):"";}
export function MaterialQuestionPanel({material,text,materialTitle}:{material:MaterialContextDto;text:string;materialTitle?:string}){
 const [question,setQuestion]=useState(""),[purpose,setPurpose]=useState("理解当前材料"),[range,setRange]=useState({start:0,end:0}),[plan,setPlan]=useState<Record<string,unknown>|null>(null),[receipt,setReceipt]=useState<Record<string,unknown>|null>(null),[message,setMessage]=useState(""),[busy,setBusy]=useState(false);
 const [unconfirmedId,setUnconfirmedId]=useState<string|null>(null);
 const [lane,setLane]=useState<ModelLane>("fast");
 const [budgetEditorOpen,setBudgetEditorOpen]=useState(false),[budgetNeedsPreview,setBudgetNeedsPreview]=useState(false);
 const [asynchronous,setAsynchronous]=useState(false);
 const [cloudProfile,setCloudProfile]=useState<ResolvedModel|null>(null);
 const [cloudUpload,setCloudUpload]=useState(false),[cloudCost,setCloudCost]=useState(false);
 const frozen=useRef<MaterialQuestionRequestDto|null>(null),epoch=useRef(0),active=useRef<string|null>(null),cancelRequest=useRef<string|null>(null);
 const contextKey=JSON.stringify(material);
 useEffect(()=>{epoch.current++;frozen.current=null;setPlan(null);setReceipt(null);setRange({start:0,end:0});setUnconfirmedId(null);setMessage("");setBusy(false);setBudgetEditorOpen(false);setBudgetNeedsPreview(false);setCloudProfile(null);setCloudUpload(false);setCloudCost(false);return()=>{epoch.current++;active.current=null;};},[contextKey,text]);
 function invalidate(resetCloud=true){frozen.current=null;setPlan(null);setReceipt(null);setBudgetEditorOpen(false);setBudgetNeedsPreview(false);if(resetCloud){setCloudProfile(null);setCloudUpload(false);setCloudCost(false);}}
 function select(area:HTMLTextAreaElement){invalidate();try{setRange(textareaOriginalRange(text,area.selectionStart,area.selectionEnd));}catch{setRange({start:0,end:0});}}
 async function prepare(){if(unconfirmedId)return;const e=epoch.current;setBusy(true);try{
  const body:MaterialQuestionRequestDto={request_id:crypto.randomUUID(),material,selection:range.end>range.start?{start_utf16:range.start,end_utf16:range.end,quote_sha256:await hash(text.slice(range.start,range.end))}:null,question,purpose,model:null,max_tokens:2048,timeout_s:120,preview:true,confirmed_plan_sha256:null,cloud_upload_confirmed:false,cloud_unknown_cost_confirmed:false};
  if(asynchronous)body.execution_mode="async";
  const resolved=await resolveProductModel("material",lane);if(e!==epoch.current)return;
  if(resolved?.profile.protocol==="openai-buffered"){
   body.execution_mode="async";setAsynchronous(true);
   if(JSON.stringify(cloudProfile)!==JSON.stringify(resolved)){setCloudProfile(resolved);setCloudUpload(false);setCloudCost(false);setMessage("请核对云端目的地和材料，并确认上传与未知费用后重新预览。");return;}
   if(!cloudUpload||!cloudCost){setMessage("请先确认材料上传和未知费用。");return;}
   body.cloud_upload_confirmed=true;body.cloud_unknown_cost_confirmed=true;
  }else{setCloudProfile(null);setCloudUpload(false);setCloudCost(false);}
  if(resolved){body.model_configuration=resolved;body.model=resolved.profile.model;body.max_tokens=resolved.profile.max_tokens;body.timeout_s=resolved.profile.timeout_s;}
  const result=await coreCommand<Record<string,unknown>>("material_question",{body});if(e!==epoch.current)return;
  if(result.schema!=="archeaxis.material-question-preview/v1"||typeof result.plan_sha256!=="string")throw new Error("preview");frozen.current={...body,preview:false,confirmed_plan_sha256:result.plan_sha256};setPlan(result);setBudgetEditorOpen(false);setBudgetNeedsPreview(false);setReceipt(null);setMessage("核对问题、范围、用途和模型目的地后确认提问。");
 }catch(error){if(e===epoch.current)setMessage(error instanceof ModelBindingRequiredError?error.message:"材料准备失败：请核对已保存版本、提取结果与模型配置。");}finally{if(e===epoch.current)setBusy(false);}}
 function terminal(value:Record<string,unknown>,id:string){
  if(value.request_id!==id||value.schema!=="archeaxis.material-answer/v1"||!["succeeded","failed"].includes(String(value.outcome)))throw new Error("receipt");
  setReceipt(value);setUnconfirmedId(null);setMessage(value.outcome==="succeeded"?"回答已记录，仍是待判断的模型候选。":(materialModelFailureMessage(value.reason_code,value.diagnostics)??"执行失败或取消，原请求和材料保留。"));
 }
 async function poll(body:MaterialQuestionRequestDto,e:number){
  const deadline=Date.now()+body.timeout_s*1000+5000;
  while(e===epoch.current&&active.current===body.request_id&&Date.now()<deadline){
   const value=await coreCommand<Record<string,unknown>>("material_question_status",{body:{request_id:body.request_id}});
   if(e!==epoch.current||active.current!==body.request_id)return;
   if(value.schema==="archeaxis.material-answer/v1"){terminal(value,body.request_id);return;}
   assertMaterialQuestionDto("MaterialQuestionPendingDto",value);
   if(value.request_id!==body.request_id||!value.plan||await hash(JSON.stringify(value.plan))!==body.confirmed_plan_sha256)throw new Error("pending identity");
   if(e!==epoch.current||active.current!==body.request_id)return;
   setReceipt(value);
   if(value.execution_state!=="RUNNING"){setMessage("执行状态未确认，保留原请求；可显式查询，没有自动重试。");return;}
   setMessage("正在处理原材料请求；关闭页面只停止等待，不会自动取消。");
   await new Promise(resolve=>setTimeout(resolve,300));
  }
  if(e===epoch.current&&active.current===body.request_id)setMessage("等待终态的时限已到；原请求保留，请显式查询，没有自动重试。");
 }
 async function execute(){const body=frozen.current;if(!body||unconfirmedId||budgetNeedsPreview||(body.model_configuration?.profile.protocol==="openai-buffered"&&(!body.cloud_upload_confirmed||!body.cloud_unknown_cost_confirmed)))return;const e=epoch.current;active.current=body.request_id;setUnconfirmedId(body.request_id);setBusy(true);try{
  const result=await coreCommand<Record<string,unknown>>(body.execution_mode==="async"?"material_question_submit":"material_question",{body});if(e!==epoch.current)return;
  if(result.schema==="archeaxis.material-answer/v1"){terminal(result,body.request_id);return;}
  if(body.execution_mode!=="async")throw new Error("receipt");
  assertMaterialQuestionDto("MaterialQuestionAdmissionDto",result);
  if(result.request_id!==body.request_id||result.plan_sha256!==body.confirmed_plan_sha256||result.task_id!=="material_answer_"+await hash(body.request_id)||result.restore_epoch!==(plan?.plan as Record<string,unknown>|undefined)?.restore_epoch||result.workspace_id!==(plan?.plan as Record<string,unknown>|undefined)?.workspace_id)throw new Error("admission identity");
  if(e!==epoch.current)return;
  setReceipt(result);setMessage("材料请求已受理；尚未取得最终回答。");await poll(body,e);
 }catch{if(e===epoch.current)setMessage("结果未确认；请查询原请求状态，不另发新请求。");}finally{if(active.current===body.request_id)active.current=null;if(e===epoch.current)setBusy(false);}}

 async function cancel(){const request_id=active.current;if(!request_id||cancelRequest.current===request_id)return;const e=epoch.current;cancelRequest.current=request_id;
  try{const result=await coreCommand<Record<string,unknown>>("material_question_cancel",{body:{request_id}});if(result.request_id!==request_id||typeof result.cancel_requested!=="boolean")throw new Error("cancel identity");if(e===epoch.current&&active.current===request_id)setMessage(result.cancel_requested?"取消已请求，等待实际回执；提供者停止状态未确认。":"该请求已不接受取消，请查询原请求终态。");}
  catch{if(e===epoch.current&&active.current===request_id)setMessage("取消未确认；原请求仍保留，可重试取消或等待实际回执。");}
  finally{if(cancelRequest.current===request_id)cancelRequest.current=null;}}
 async function recover(){if(unconfirmedId)return;const e=epoch.current;setBusy(true);try{
   const journal=await coreCommand<Record<string,unknown>>("material_question_status",{body:{request_id:null}});if(e!==epoch.current)return;
   if(journal.schema!=="archeaxis.material-question-journal/v1"||!Array.isArray(journal.plans))throw new Error("journal");
   const saved=journal.plans.find(p=>p&&typeof p==="object"&&materialKey(p.request?.material)===materialKey(material));
   if(!saved){setMessage("最近 16 个材料请求中没有当前版本；未创建新推理。");return;}
   const body=saved.request as MaterialQuestionRequestDto;const selection=body.selection;
   if(typeof body.request_id!=="string"||!body.request_id||typeof body.question!=="string"||typeof body.purpose!=="string")throw new Error("journal request");
   if(selection&&( !Number.isSafeInteger(selection.start_utf16)||!Number.isSafeInteger(selection.end_utf16)||selection.start_utf16<0||selection.end_utf16<=selection.start_utf16||selection.end_utf16>text.length||await hash(text.slice(selection.start_utf16,selection.end_utf16))!==selection.quote_sha256))throw new Error("journal selection");
   const digest=await hash(JSON.stringify(saved));if(e!==epoch.current)return;
   frozen.current={...body,preview:false,confirmed_plan_sha256:digest};setUnconfirmedId(body.request_id);setReceipt(null);setPlan({schema:"archeaxis.material-question-preview/v1",plan:saved,plan_sha256:digest});setQuestion(body.question);setPurpose(body.purpose);setLane(body.model_configuration?.lane??"fast");setAsynchronous(body.execution_mode==="async");setCloudProfile(body.model_configuration?.profile.protocol==="openai-buffered"?body.model_configuration:null);setCloudUpload(body.cloud_upload_confirmed===true);setCloudCost(body.cloud_unknown_cost_confirmed===true);setRange(selection?{start:selection.start_utf16,end:selection.end_utf16}:{start:0,end:0});
   const result=await coreCommand<Record<string,unknown>>("material_question_status",{body:{request_id:body.request_id}});if(e!==epoch.current)return;
   if(result.request_id!==body.request_id)throw new Error("journal identity");const terminal=result.schema==="archeaxis.material-answer/v1"&&["succeeded","failed"].includes(String(result.outcome));if(result.schema==="archeaxis.material-answer/v1"&&!terminal)throw new Error("journal outcome");setReceipt(result);setUnconfirmedId(terminal||result.execution_state==="NOT_EXECUTED"?null:body.request_id);setMessage(terminal?(result.outcome==="failed"?materialModelFailureMessage(result.reason_code,result.diagnostics)??"原请求执行失败，历史回执已读回；没有再次推理。":"原请求历史回执已读回；没有再次推理。"):result.execution_state==="NOT_EXECUTED"?"已确认原请求尚未执行，可以确认原计划。":"执行结果尚未确认，请继续查询原请求。");
   if(body.execution_mode==="async"&&result.execution_state==="RUNNING"){active.current=body.request_id;try{await poll(frozen.current!,e);}finally{if(active.current===body.request_id)active.current=null;}}
 }catch{if(e===epoch.current)setMessage("材料请求历史未确认，当前输入保留。");}finally{if(e===epoch.current)setBusy(false);}}
 async function readUnconfirmed(){const request_id=unconfirmedId;if(!request_id)return;const e=epoch.current;setBusy(true);try{const value=await coreCommand<Record<string,unknown>>("material_question_status",{body:{request_id}});if(e!==epoch.current)return;if(value.request_id!==request_id)throw new Error("request identity");setReceipt(value);if((value.schema==="archeaxis.material-answer/v1"&&["succeeded","failed"].includes(String(value.outcome)))||value.execution_state==="NOT_EXECUTED"){setUnconfirmedId(null);setMessage(value.outcome==="failed"?materialModelFailureMessage(value.reason_code,value.diagnostics)??"原请求执行失败，状态已读回，没有再次推理。":"原请求状态已读回，没有再次推理。");}else if(value.execution_state==="RUNNING"&&frozen.current?.execution_mode==="async"){active.current=request_id;try{await poll(frozen.current,e);}finally{if(active.current===request_id)active.current=null;}}else setMessage("原请求结果仍未确认，请继续查询。");}catch{if(e===epoch.current)setMessage("原请求状态未确认，冻结请求保留。");}finally{if(e===epoch.current)setBusy(false);}}
 const answer=receipt?.answer as Record<string,unknown>|undefined;
 return <section aria-label="固定版本材料问答"><h4>材料问答</h4><p>发送当前固定版本或所选文本到所选模型；云端发送需要单独确认，不需要把材料接受为知识。</p><label>材料问答选区<textarea readOnly value={text.replace(/\r\n?/g,"\n")} disabled={busy||!!unconfirmedId} onSelect={e=>select(e.currentTarget)}/></label><p>{range.end>range.start?`已选文本：${text.slice(range.start,range.end)}`:"整个已保存材料"}</p><label>材料模型通道<select disabled={busy||!!unconfirmedId} value={lane} onChange={e=>{invalidate();setLane(e.target.value as ModelLane);}}><option value="fast">快速</option><option value="deep">深度</option></select></label><label><input type="checkbox" aria-label="离开此页后继续提问" checked={asynchronous} disabled={busy||!!unconfirmedId||!!cloudProfile} onChange={e=>{invalidate();setAsynchronous(e.target.checked);}}/>离开此页后继续提问（程序保持运行时有效，仍受本次时限约束）</label><label>材料问题<input value={question} disabled={busy||!!unconfirmedId} onChange={e=>{invalidate();setQuestion(e.target.value);}}/></label><label>提问用途<input value={purpose} disabled={busy||!!unconfirmedId} onChange={e=>{invalidate();setPurpose(e.target.value);}}/></label>{cloudProfile?<section aria-label="云端材料发送确认"><p>目的地：{cloudProfile.profile.endpoint}（PUBLIC_HTTPS）</p><p>材料：{materialTitle||"当前已保存材料"}，{range.end>range.start?"仅所选片段":"当前固定版本全文"}；同时发送问题与用途。</p><p>费用未知（unknown cost）；当前没有价格估算。</p><label><input type="checkbox" checked={cloudUpload} disabled={busy||!!unconfirmedId} onChange={e=>{invalidate(false);setCloudUpload(e.target.checked);}}/>我确认向上述云端目的地上传本次材料与问题</label><label><input type="checkbox" checked={cloudCost} disabled={busy||!!unconfirmedId} onChange={e=>{invalidate(false);setCloudCost(e.target.checked);}}/>我确认费用未知并继续本次请求</label></section>:null}<button disabled={busy||!!unconfirmedId||!question.trim()||!purpose.trim()} onClick={()=>void prepare()}>预览材料提问</button><button disabled={busy||!!unconfirmedId} onClick={()=>void recover()}>恢复本版材料的上次提问</button>{plan?<>{frozen.current?<FrozenRequestSummary request={frozen.current} materialPresentation={materialTitle?{identity:material,title:materialTitle}:undefined} destinationCandidates={(plan.plan as {destination_candidates?:string[]}|undefined)?.destination_candidates}/>:null}<RawReceiptButton label="提问材料与目的地计划" payload={plan} category="runtime"/><button disabled={busy||!!unconfirmedId||budgetNeedsPreview||!!cloudProfile&&(!cloudUpload||!cloudCost)} onClick={()=>void execute()}>确认提问或查询原请求</button></>:null}{busy&&active.current?<button onClick={()=>void cancel()}>取消材料提问</button>:null}{unconfirmedId?<><p role="status">材料请求状态未确认，请查询原请求。</p><button disabled={busy} onClick={()=>void readUnconfirmed()}>查询未确认材料请求</button></>:null}{typeof answer?.answer==="string"?<p style={{whiteSpace:"pre-wrap"}}>{answer.answer}</p>:null}{receipt?<RawReceiptButton label="来源与实际模型回执" payload={receipt}/>:null}{message?<p role="status">{message}</p>:null}{receipt?.outcome==="failed"&&receipt.reason_code==="material_no_final_answer"?<><button type="button" disabled={busy||!!unconfirmedId} aria-expanded={budgetEditorOpen} onClick={()=>{setBudgetEditorOpen(!budgetEditorOpen);setBudgetNeedsPreview(true);}}>{budgetEditorOpen?"收起材料输出预算":"调整材料模型输出预算"}</button>{budgetEditorOpen?<ModelConfigurationPanel key={frozen.current?.model_configuration?.lane??lane} materialBudgetLane={frozen.current?.model_configuration?.lane??lane}/>:null}</>:null}</section>;
}
