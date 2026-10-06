import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import { RawReceiptButton } from "./DiagnosticConsole";
function record(value:unknown):Record<string,unknown>{if(!value||typeof value!=="object"||Array.isArray(value))throw new Error("invalid response");return value as Record<string,unknown>;}
export function MachineAnswerPanel({knowledgeId}:{knowledgeId:string}) {
 const [question,setQuestion]=useState("");const [answer,setAnswer]=useState<Record<string,unknown>|null>(null);const [task,setTask]=useState<unknown>(null);const [corrected,setCorrected]=useState("");const [note,setNote]=useState("");const [reviewer,setReviewer]=useState("");const [correction,setCorrection]=useState<unknown>(null);const [message,setMessage]=useState("");const [busy,setBusy]=useState(false);const alive=useRef(true);
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);
 async function ask(){
  if(!question.trim()||busy)return;setBusy(true);setAnswer(null);setTask(null);setCorrection(null);setCorrected("");setNote("");setMessage("正在执行本地机器回答，等待真实回执…");
  try{
   const response=record(await coreCommand("machine_answer",{body:{knowledge_id:knowledgeId,question:question.trim(),max_tokens:2048,timeout_s:120}}));
   const rawAnswer=record(response.answer);
   if(response.knowledge_id!==knowledgeId||typeof response.answer_id!=="string"||typeof response.question!=="string"||typeof rawAnswer.answer!=="string"||!rawAnswer.answer.trim()||response.authority!=="candidate")throw new Error("invalid answer receipt");
   const proof=record(await coreCommand("machine_task_get",{task_id:response.answer_id}));
   if(proof.task_id!==response.answer_id||typeof proof.conditions!=="string")throw new Error("invalid task readback");
   const stored=record(JSON.parse(proof.conditions));
   if(stored.answer_id!==response.answer_id||record(stored.answer).answer!==rawAnswer.answer)throw new Error("answer readback mismatch");
   if(alive.current){setAnswer(response);setTask(proof);setMessage("本地回答已持久化读回。它仍是候选，不是已接受知识或能力评分。");}
  }catch{if(alive.current)setMessage("回答未完成或持久化读回未确认。不会显示推测的成功结果。");}
  finally{if(alive.current)setBusy(false);}
 }
 async function correct(){
  if(!answer||busy||!corrected.trim()||!note.trim()||!reviewer.trim())return;setBusy(true);
  try{
   const receipt=record(await coreCommand("machine_correction",{body:{answer_id:answer.answer_id,knowledge_id:knowledgeId,question:answer.question,machine_answer:record(answer.answer).answer,corrected_answer:corrected.trim(),error_note:note.trim(),reviewer:reviewer.trim()}}));
   if(receipt.answer_id!==answer.answer_id||receipt.status!=="candidate"||typeof receipt.correction_candidate_id!=="string")throw new Error("invalid correction receipt");
   if(alive.current){setCorrection(receipt);setMessage("使用者纠正已记录为候选；尚未接受，不会自动替代知识。");}
  }catch{if(alive.current)setMessage("纠正未确认，请保留输入。不会把未确认操作当作成功。");}
  finally{if(alive.current)setBusy(false);}
 }
 return <section aria-label="知识到机器回答"><h4>基于当前知识的本地回答</h4><label>实际问题 <textarea value={question} disabled={busy} onChange={event=>setQuestion(event.target.value)}/></label><button disabled={busy||!question.trim()} onClick={()=>void ask()}>执行本地机器回答</button>{message?<p role="status">{message}</p>:null}
 {answer?<><h4>机器回答候选</h4><pre aria-label="真实机器回答">{String(record(answer.answer).answer)}</pre><p>持久化任务与模型回执见诊断控制台。</p><RawReceiptButton label="持久化任务与模型回执" payload={task} /><p>若你实际发现错误，可填写下方纠正；没有错误无需提交。</p><label>正确答案 <textarea value={corrected} disabled={busy} onChange={event=>setCorrected(event.target.value)}/></label><label>具体错误 <textarea value={note} disabled={busy} onChange={event=>setNote(event.target.value)}/></label><label>纠正审核者 <input value={reviewer} disabled={busy} onChange={event=>setReviewer(event.target.value)}/></label><button disabled={busy||!corrected.trim()||!note.trim()||!reviewer.trim()} onClick={()=>void correct()}>记录使用者纠正候选</button>{correction?<pre aria-label="纠正候选回执">{JSON.stringify(correction,null,2)}</pre>:null}</>:null}</section>;
}
