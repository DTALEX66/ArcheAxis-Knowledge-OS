import type {ModelConfiguration,ResolvedModel} from "../api/generated/model-configuration-contract";
import {useEffect,useRef,useState} from "react";
import {coreCommand} from "../api/core";
import type {MaterialContextDto,MaterialQuestionRequestDto} from "../api/generated/material-question";
import {RawReceiptButton} from "./DiagnosticConsole";
import {textareaOriginalRange} from "../presentation/originalTextSelection";
async function hash(text:string){return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(text)))).map(b=>b.toString(16).padStart(2,"0")).join("");}
function materialKey(value:unknown){return value&&typeof value==="object"?JSON.stringify(Object.fromEntries(Object.entries(value).sort(([a],[b])=>a.localeCompare(b)))):"";}
export function MaterialQuestionPanel({material,text}:{material:MaterialContextDto;text:string}){
 const [question,setQuestion]=useState(""),[purpose,setPurpose]=useState("理解当前材料"),[range,setRange]=useState({start:0,end:0}),[plan,setPlan]=useState<Record<string,unknown>|null>(null),[receipt,setReceipt]=useState<Record<string,unknown>|null>(null),[message,setMessage]=useState(""),[busy,setBusy]=useState(false);
 const frozen=useRef<MaterialQuestionRequestDto|null>(null),epoch=useRef(0),active=useRef<string|null>(null);
 const contextKey=JSON.stringify(material);
 useEffect(()=>{epoch.current++;frozen.current=null;setPlan(null);setReceipt(null);setRange({start:0,end:0});setMessage("");setBusy(false);return()=>{epoch.current++;active.current=null;};},[contextKey,text]);
 function invalidate(){frozen.current=null;setPlan(null);setReceipt(null);}
 function select(area:HTMLTextAreaElement){invalidate();try{setRange(textareaOriginalRange(text,area.selectionStart,area.selectionEnd));}catch{setRange({start:0,end:0});}}
 async function prepare(){const e=epoch.current;setBusy(true);try{
  const body:MaterialQuestionRequestDto={request_id:crypto.randomUUID(),material,selection:range.end>range.start?{start_utf16:range.start,end_utf16:range.end,quote_sha256:await hash(text.slice(range.start,range.end))}:null,question,purpose,model:null,max_tokens:2048,timeout_s:120,preview:true,confirmed_plan_sha256:null};
  const configuration=await coreCommand<ModelConfiguration>("model_configuration_get");
  if(configuration.revision>0){const resolved=await coreCommand<ResolvedModel>("model_configuration_resolve",{body:{purpose:"material",lane:"fast"}});body.model_configuration=resolved;body.model=resolved.profile.model;body.max_tokens=Math.min(body.max_tokens,resolved.profile.max_tokens);body.timeout_s=resolved.profile.timeout_s;}
  const result=await coreCommand<Record<string,unknown>>("material_question",{body});if(e!==epoch.current)return;
  if(result.schema!=="archeaxis.material-question-preview/v1"||typeof result.plan_sha256!=="string")throw new Error("preview");frozen.current={...body,preview:false,confirmed_plan_sha256:result.plan_sha256};setPlan(result);setMessage("核对问题、范围、用途和本地模型目的地后确认提问。");
 }catch{if(e===epoch.current)setMessage("材料准备失败：请核对已保存版本、提取结果与本地模型配置。");}finally{if(e===epoch.current)setBusy(false);}}
 async function execute(){const body=frozen.current;if(!body)return;const e=epoch.current;active.current=body.request_id;setBusy(true);try{const result=await coreCommand<Record<string,unknown>>("material_question",{body});if(e!==epoch.current)return;if(result.request_id!==body.request_id||result.schema!=="archeaxis.material-answer/v1")throw new Error("receipt");setReceipt(result);setMessage(result.outcome==="succeeded"?"回答已记录，仍是待判断的模型候选。":"执行失败或取消，原请求和材料保留。");}catch{if(e===epoch.current)setMessage("结果未确认；保留同一请求重试，不另发新请求。");}finally{if(active.current===body.request_id)active.current=null;if(e===epoch.current)setBusy(false);}}
 async function cancel(){if(active.current){const e=epoch.current;await coreCommand("material_question_cancel",{body:{request_id:active.current}});if(e!==epoch.current)return;setMessage("取消已请求，等待实际回执；提供者停止状态未确认。");}}
 async function recover(){const e=epoch.current;setBusy(true);try{
   const journal=await coreCommand<Record<string,unknown>>("material_question_status",{body:{request_id:null}});if(e!==epoch.current)return;
   if(journal.schema!=="archeaxis.material-question-journal/v1"||!Array.isArray(journal.plans))throw new Error("journal");
   const saved=journal.plans.find(p=>p&&typeof p==="object"&&materialKey(p.request?.material)===materialKey(material));
   if(!saved){setMessage("最近 16 个材料请求中没有当前版本；未创建新推理。");return;}
   const body=saved.request as MaterialQuestionRequestDto;const digest=await hash(JSON.stringify(saved));if(e!==epoch.current)return;
   frozen.current={...body,preview:false,confirmed_plan_sha256:digest};setPlan({schema:"archeaxis.material-question-preview/v1",plan:saved,plan_sha256:digest});setQuestion(body.question);setPurpose(body.purpose);
   const result=await coreCommand<Record<string,unknown>>("material_question_status",{body:{request_id:body.request_id}});if(e!==epoch.current)return;
   if(result.request_id!==body.request_id)throw new Error("journal identity");setReceipt(result);setMessage(result.schema==="archeaxis.material-answer/v1"?"原请求历史回执已读回；没有再次推理。":"原执行状态 UNKNOWN；保留原请求，不推断成功或重复调用。");
 }catch{if(e===epoch.current)setMessage("材料请求历史未确认，当前输入保留。");}finally{if(e===epoch.current)setBusy(false);}}
 const answer=receipt?.answer as Record<string,unknown>|undefined;
 return <section aria-label="固定版本材料问答"><h4>材料问答</h4><p>只发送当前固定版本或所选文本到本地模型；不需要把材料接受为知识。</p><label>材料问答选区<textarea readOnly value={text.replace(/\r\n?/g,"\n")} disabled={busy} onSelect={e=>select(e.currentTarget)}/></label><p>{range.end>range.start?`选区 ${range.start}–${range.end} UTF-16`:"整个已保存材料"}</p><label>材料问题<input value={question} disabled={busy} onChange={e=>{invalidate();setQuestion(e.target.value);}}/></label><label>提问用途<input value={purpose} disabled={busy} onChange={e=>{invalidate();setPurpose(e.target.value);}}/></label><button disabled={busy||!question.trim()||!purpose.trim()} onClick={()=>void prepare()}>预览材料提问</button><button disabled={busy} onClick={()=>void recover()}>恢复最近同版本材料请求</button>{plan?<><p>请求 ID：{frozen.current?.request_id} · 本地模型结果未预先断言</p><RawReceiptButton label="提问材料与目的地计划" payload={plan}/><button disabled={busy} onClick={()=>void execute()}>确认并提问或读回同一请求</button></>:null}{busy&&active.current?<button onClick={()=>void cancel()}>取消材料提问</button>:null}{typeof answer?.answer==="string"?<p style={{whiteSpace:"pre-wrap"}}>{answer.answer}</p>:null}{receipt?<RawReceiptButton label="来源与实际模型回执" payload={receipt}/>:null}{message?<p role="status">{message}</p>:null}</section>;
}
