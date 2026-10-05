import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import { DataTable, Section } from "./RealData";
function record(value:unknown):Record<string,unknown>{if(!value||typeof value!=="object"||Array.isArray(value))throw new Error("invalid response");return value as Record<string,unknown>;}
function StructurePreview({structure,text}:{structure:unknown;text:string}) {
 const [page,setPage]=useState(0);
 const nodes=Array.isArray(structure)?structure:[];
 const characters=Array.from(text);
 const rows=nodes.map((value)=>{
  const node=value&&typeof value==="object"?value as Record<string,unknown>:{};
  const start=node.char_start,end=node.char_end;
  const valid=Number.isInteger(start)&&Number.isInteger(end)&&Number(start)>=0&&Number(end)>=Number(start)&&Number(end)<=characters.length;
  return {path:Array.isArray(node.path)?node.path.join(" / "):typeof node.path==="string"?node.path:"位置未提供",kind:typeof node.kind==="string"?node.kind:"结构类型未提供",content:valid?characters.slice(Number(start),Number(end)).join(""):typeof node.text==="string"?node.text:"正文范围未提供或未匹配"};
 });
 return <Section title="结构化结果预览"><p className="muted">位置来自转换产物，正文按其字符范围读取；不等同原件定位已核实。</p><DataTable columns={[{key:"path",label:"工作表 / 页 / 路径"},{key:"kind",label:"结构"},{key:"content",label:"单元格 / 段落内容"}]} rows={rows.slice(page*30,(page+1)*30)} empty="此产物没有可显示的结构条目；原始记录仍保留。"/>{rows.length>30?<div><button disabled={page===0} onClick={()=>setPage(value=>value-1)}>上一组结构</button><span>{page+1} / {Math.ceil(rows.length/30)}</span><button disabled={(page+1)*30>=rows.length} onClick={()=>setPage(value=>value+1)}>下一组结构</button></div>:null}</Section>;
}
export function JobContent({sourceId,name,onKnowledge}:{sourceId:string;name:string;onKnowledge?:()=>void}) {
 const [text,setText]=useState(""); const [proof,setProof]=useState<unknown>(null); const [capabilities,setCapabilities]=useState<unknown>(null); const [message,setMessage]=useState(""); const [busy,setBusy]=useState(false); const [job,setJob]=useState(""); const alive=useRef(true);
 const extension=name.split(".").pop()?.toLowerCase();
 const [latestState,setLatestState]=useState<unknown>(null);
 const [transform,setTransform]=useState<Record<string,unknown>|null>(null);const [selection,setSelection]=useState({start:0,end:0});const [candidateBody,setCandidateBody]=useState("");const [candidateId,setCandidateId]=useState("");
 const routes:Record<string,string>={xlsx:"office",pptx:"office",docx:"office",html:"html",htm:"html",xhtml:"html",pdf:"pdf",png:"image",jpg:"image",jpeg:"image",tif:"image",tiff:"image",webp:"image",bmp:"image",zip:"archive",canvas:"canvas",srt:"subtitles",vtt:"subtitles",wav:"media",mp4:"media",txt:"text",md:"text",csv:"text",tsv:"text",json:"text",jsonl:"text",yaml:"text",yml:"text",toml:"text",xml:"text",epub:"text",eml:"text"};
 const kind=extension?routes[extension]??null:null;
 useEffect(()=>{alive.current=true;coreCommand("capabilities_list").then(value=>{if(alive.current)setCapabilities(value);}).catch(()=>{if(alive.current)setMessage("能力握手读取失败；真实执行结果仍须单独核验。");});return()=>{alive.current=false;};},[]);
 async function execute(){
  if(!kind||busy)return;setBusy(true);setLatestState({state:"starting"});setMessage("正在启动真实转换…");
  const job_id=`read_${crypto.randomUUID()}`;setJob(job_id);
  try{
   const queue=record(await coreCommand("job_enqueue",{body:{job_id,kind,input_ref:sourceId}}));if(queue.job_id!==job_id)throw new Error("job identity mismatch");
   window.dispatchEvent(new Event("archeaxis-job-changed"));
   await coreCommand("job_execute",{job_id,body:{deadline_ms:60000}});
   let state:Record<string,unknown>|null=null;const deadline=Date.now()+90000;
   while(alive.current&&Date.now()<deadline){state=record(await coreCommand("jobs_get",{job_id}));if(["succeeded","failed","cancelled","rejected"].includes(String(state.state)))break;await new Promise(resolve=>setTimeout(resolve,300));}
   if(!alive.current)return;
   if(!state||state.state!=="succeeded"){setLatestState(state);throw new Error("job did not succeed");}
   const [rawText,structure,loss,quality]=await Promise.all([coreCommand("job_output",{job_id,kind:"text"}),coreCommand("job_output",{job_id,kind:"document_structure"}),coreCommand("job_output",{job_id,kind:"loss_report"}),coreCommand("job_quality",{job_id})]);
   const result=record(rawText);if(typeof result.content!=="string")throw new Error("invalid text output");
   const structureOutput=record(structure), lossOutput=record(loss);
   if(typeof structureOutput.content!=="string"||typeof lossOutput.content!=="string")throw new Error("invalid structured output");
   const parsedStructure=JSON.parse(structureOutput.content), parsedLoss=JSON.parse(lossOutput.content);
   const sourceTransform=record(await coreCommand("source_job_transform",{source_id:sourceId,job_id}));
   if(sourceTransform.source_id!==sourceId||sourceTransform.job_id!==job_id||typeof sourceTransform.transform_id!=="number"||sourceTransform.content!==result.content)throw new Error("source transform mismatch");
   if(alive.current){setText(result.content);setTransform(sourceTransform);setCandidateId("");setSelection({start:0,end:0});setLatestState(state);setProof({structure:parsedStructure,loss:parsedLoss,quality});setMessage("真实转换已完成；下方文本、结构、损失及引擎回执均来自 Core。");}
  }catch{if(alive.current)setMessage("转换未完成或产物读取失败。不会把失败或未知状态当作成功。");}
  finally{window.dispatchEvent(new Event("archeaxis-job-changed"));if(alive.current)setBusy(false);}
 }
 async function createCandidate(){
  if(!transform||busy||selection.end<=selection.start||!candidateBody.trim())return;setBusy(true);
  try{
   const receipt=record(await coreCommand("knowledge_from_transform",{body:{knowledge_type:"source_note",body:candidateBody.trim(),source_id:sourceId,job_id:transform.job_id,transform_id:transform.transform_id,selection_start_utf16:selection.start,selection_end_utf16:selection.end,quote:text.slice(selection.start,selection.end)}}));
   if(receipt.status!=="candidate"||typeof receipt.knowledge_id!=="string"||typeof receipt.anchor_id!=="string")throw new Error("invalid candidate receipt");
   if(alive.current){setCandidateId(receipt.knowledge_id);setMessage("已创建来源与引文绑定的知识候选，尚未接受。");}
  }catch{if(alive.current)setMessage("知识候选创建未确认，请保留正文与选区重试。");}finally{if(alive.current)setBusy(false);}
 }
 return <section aria-label="真实转换产物"><p>能力目录只证明握手。引擎身份与结果以实际 job 的质量回执为准。</p>{kind==="media"?<p>仅探测媒体头信息；不表示已解码、转写或核对时间段内容。</p>:kind==="archive"?<p>容器清点与成员正文处理分别记录；清点成功不表示所有成员已读取。</p>:null}<details><summary>当前能力握手</summary><pre>{JSON.stringify(capabilities,null,2)}</pre></details>{kind?<button disabled={busy} onClick={()=>void execute()}>{kind==="media"?"执行媒体头信息探测":kind==="archive"?"清点容器与登记成员":"执行真实内容转换"}</button>:<p>此格式尚无当前阅读转换通路，原件已保留。</p>}{job?<p>最新任务 {job}</p>:null}{latestState?<details><summary>最新处理状态与错误记录</summary><pre>{JSON.stringify(latestState,null,2)}</pre></details>:null}{message?<p role="status">{message}</p>:null}{text?<><pre aria-label="Core 提取正文">{text}</pre><label>选择实际引文 <textarea readOnly value={text} onSelect={event=>setSelection({start:event.currentTarget.selectionStart,end:event.currentTarget.selectionEnd})}/></label><p>已选引文：{text.slice(selection.start,selection.end)}</p><label>知识候选正文 <textarea value={candidateBody} disabled={busy} onChange={event=>setCandidateBody(event.target.value)}/></label><button disabled={busy||!transform||selection.end<=selection.start||!candidateBody.trim()} onClick={()=>void createCandidate()}>创建知识候选</button>{candidateId?<p>候选 {candidateId} <button onClick={onKnowledge}>前往知识库审核</button></p>:null}</>:null}{proof&&typeof proof==="object"&&"structure" in proof?<StructurePreview key={job} structure={proof.structure} text={text}/>:null}{proof?<details><summary>更多信息：损失、引擎与处理记录</summary><p>损失记录与引擎身份来自本次实际任务；握手声明不代替执行证据。</p><pre>{JSON.stringify(proof,null,2)}</pre></details>:null}</section>;
}
