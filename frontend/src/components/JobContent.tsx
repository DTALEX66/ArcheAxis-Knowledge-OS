import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import { estimateMediaWork, formatEstimate, MEDIA_CEILING_MS, MEDIA_REALTIME_FACTOR } from "../presentation/mediaEstimate";
import { RawReceiptButton } from "./DiagnosticConsole";
import { DataTable, Section } from "./RealData";
import { TranscriptionCues, transcriptionProof, type TranscriptionProof } from "./TranscriptionCues";
import { EpubParagraphs, epubProof, type EpubProof, type EpubPosition } from "./EpubParagraphs";
import type { AnchorDto } from "../api/generated/core-contract";

function record(value:unknown):Record<string,unknown>{if(!value||typeof value!=="object"||Array.isArray(value))throw new Error("invalid response");return value as Record<string,unknown>;}
export interface SplitProgress {status:string;expected:number;present:number;missing:number[];resumed:number[];}
/**
 * What a split run actually finished, read from the job's own loss receipt.
 *
 * The receipt is the only place this may come from: the number of windows a recording needs is
 * decided by the worker from the file's real duration, so a count computed here would be a second,
 * disagreeing opinion. `null` means the receipt carried no split record at all — not that nothing
 * ran.
 */
export function splitProgressOf(loss:Record<string,unknown>):SplitProgress|null {
 const output=(loss as {params?:{worker_output?:Record<string,unknown>}}).params?.worker_output;
 const windows=output?.windows;
 if(!windows||typeof windows!=="object"||Array.isArray(windows))return null;
 const value=windows as Record<string,unknown>;
 const count=(input:unknown)=>Array.isArray(input)&&input.every(item=>Number.isSafeInteger(item))?input as number[]:[];
 if(!Number.isSafeInteger(value.windows_expected)||!Number.isSafeInteger(value.windows_present))return null;
 return {status:String(value.status??"unknown"),expected:Number(value.windows_expected),present:Number(value.windows_present),
  missing:count(value.windows_missing),resumed:count(value.windows_resumed)};
}
export function describeSplit(progress:SplitProgress):string {
 const {status,expected,present,missing,resumed}=progress;
 if(status==="complete")return `分段全部完成（${present} / ${expected} 段${resumed.length?`，其中本次复用了 ${resumed.length} 段`:""}）。`;
 return `分段尚未全部完成（${present} / ${expected} 段${resumed.length?`，复用了 ${resumed.length} 段`:""}；未完成段 ${missing.length?missing.join("、"):"未提供"}）；正文只包含已完成分段，未完成部分没有被省略记录。`;
}
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
export function JobContent({sourceId,name,onKnowledge,sourceRevision,onTimeSeek,onAnchor,epubSeek,onEpubSeek,mediaDurationSeconds}:{sourceId:string;name:string;onKnowledge?:()=>void;sourceRevision?:string;onTimeSeek?:(seconds:number)=>void;onAnchor?:(anchor:AnchorDto)=>void;epubSeek?:EpubPosition;onEpubSeek?:(position:EpubPosition)=>void;mediaDurationSeconds?:number}) {
 const [epub,setEpub]=useState<EpubProof|null>(null);
 const [transcription,setTranscription]=useState<TranscriptionProof|null>(null);
 const loadGeneration=useRef(0);

 const [text,setText]=useState(""); const [proof,setProof]=useState<unknown>(null); const [capabilities,setCapabilities]=useState<unknown>(null); const [message,setMessage]=useState(""); const [busy,setBusy]=useState(false); const [job,setJob]=useState(""); const alive=useRef(true);
 const extension=name.split(".").pop()?.toLowerCase();
 const [latestState,setLatestState]=useState<unknown>(null);
 const [splitProgress,setSplitProgress]=useState<SplitProgress|null>(null);
 const [transform,setTransform]=useState<Record<string,unknown>|null>(null);const [selection,setSelection]=useState({start:0,end:0});const [candidateBody,setCandidateBody]=useState("");const [candidateId,setCandidateId]=useState("");
 const routes:Record<string,string>={xlsx:"office",pptx:"office",docx:"office",html:"html",htm:"html",xhtml:"html",pdf:"pdf",png:"image",jpg:"image",jpeg:"image",tif:"image",tiff:"image",webp:"image",bmp:"image",zip:"archive",tar:"archive",canvas:"canvas",srt:"subtitles",vtt:"subtitles",wav:"transcribe",mp3:"transcribe",m4a:"transcribe",flac:"transcribe",ogg:"transcribe",opus:"transcribe",mp4:"video",mov:"video",mkv:"video",webm:"video",txt:"text",md:"text",csv:"text",tsv:"text",json:"text",jsonl:"text",yaml:"text",yml:"text",toml:"text",xml:"text",epub:"text",eml:"text"};
 const kind=extension?routes[extension]??null:null;
 // The Core refuses a job deadline above the ceiling, so the user is told what the current
 // recording is expected to cost before anything is executed.
 const mediaEstimate=mediaDurationSeconds&&(kind==="transcribe"||kind==="video")?estimateMediaWork(Math.round(mediaDurationSeconds*1000)):null;
 const identity=`${sourceId}:${sourceRevision??""}:${extension??""}`;const currentIdentity=useRef(identity);currentIdentity.current=identity;

 useEffect(()=>{
  let active=true;const generation=++loadGeneration.current;
  setEpub(null);setTranscription(null);setText("");setTransform(null);setProof(null);setLatestState(null);setSplitProgress(null);setJob("");setBusy(false);setMessage("");setCandidateId("");setSelection({start:0,end:0});
  if(!sourceRevision)return()=>{active=false;};
  const current=()=>active&&generation===loadGeneration.current;
  (async()=>{
   const listing=record(await coreCommand("source_jobs",{source_id:sourceId}));
   if(listing.source_id!==sourceId||!Array.isArray(listing.jobs)||listing.jobs.length>50)throw new Error("bounded source jobs mismatch");
   const rows=listing.jobs as Array<Record<string,unknown>>;
   if(rows.some(row=>row.input_ref!==sourceId))throw new Error("source jobs identity mismatch");
   const latest=rows.find(row=>row.kind===(extension==="epub"?"text":kind==="video"?"video":"transcribe"));
   const successful=rows.find(row=>row.kind===(extension==="epub"?"text":kind==="video"?"video":"transcribe")&&row.state==="succeeded");
   if(!successful){if(current()){if(latest){setLatestState(latest);setMessage(`最近一次转换任务状态为 ${String(latest.state)}；未找到成功产物，不表示此前结果不存在。`);}if(listing.jobs_capped===true)setMessage("仅检查最近 50 个来源任务；未找到其中的成功转写，不表示更早结果不存在。");}return;}
   if(typeof successful.job_id!=="string")throw new Error("persisted job identity missing");
   const id=successful.job_id;
   const [stateValue,rawText,structureValue,lossValue,quality,transformValue]=await Promise.all([
    coreCommand("jobs_get",{job_id:id}),coreCommand("job_output",{job_id:id,kind:"text"}),
    coreCommand("job_output",{job_id:id,kind:"document_structure"}),coreCommand("job_output",{job_id:id,kind:"loss_report"}),
    coreCommand("job_quality",{job_id:id}),coreCommand("source_job_transform",{source_id:sourceId,job_id:id})]);
   const state=record(stateValue),textOutput=record(rawText),structure=record(structureValue),loss=record(lossValue),saved=record(transformValue);
   if(typeof textOutput.content!=="string"||typeof structure.content!=="string"||typeof loss.content!=="string"
    ||saved.source_id!==sourceId||saved.job_id!==id||typeof saved.transform_id!=="number"||saved.content!==textOutput.content)throw new Error("persisted transform mismatch");
   const verifiedEpub=extension==="epub"?await epubProof(sourceId,sourceRevision,id,state,loss,successful):null;
   const verified=extension!=="epub"?await transcriptionProof(sourceId,sourceRevision,id,state,loss,successful,kind==="video"?"video":"transcribe"):null;
   const parsedStructure=JSON.parse(structure.content),parsedLoss=JSON.parse(loss.content);
   if(!current())return;
   if(verified)setTranscription(verified);if(verifiedEpub)setEpub(verifiedEpub);setText(textOutput.content);setTransform(saved);setProof({structure:parsedStructure,loss:parsedLoss,quality});
   setJob(typeof latest?.job_id==="string"?latest.job_id:id);setLatestState(latest??state);
   setMessage(`已读回持久化转写；最新处理状态与已成功的内容分别保留。${listing.jobs_capped===true?"仅检查最近 50 个来源任务。":""}`);
  })().catch(()=>{if(current())setMessage("持久化转写读回未完成；不会自动重新转写。");});
  return()=>{active=false;};
 },[sourceId,sourceRevision,extension]);

 useEffect(()=>{alive.current=true;coreCommand("capabilities_list").then(value=>{if(alive.current)setCapabilities(value);}).catch(()=>{if(alive.current)setMessage("能力握手读取失败；真实执行结果仍须单独核验。");});return()=>{alive.current=false;};},[]);
 /** Run one job to a terminal state and publish whatever it produced.
  *
  * Returns the parsed loss receipt so a split caller can read its own progress from the same
  * receipt it publishes; nothing here invents a second opinion about what completed.
  */
 async function runAndPublish(executionKind:string,job_id:string,body:Record<string,unknown>,waitMs:number,current:()=>boolean):Promise<Record<string,unknown>|null>{
  const queue=record(await coreCommand("job_enqueue",{body:{job_id,kind:executionKind,input_ref:sourceId}}));if(!current())return null;if(queue.job_id!==job_id)throw new Error("job identity mismatch");
  window.dispatchEvent(new Event("archeaxis-job-changed"));
  await coreCommand("job_execute",{job_id,body});
  let state:Record<string,unknown>|null=null;const deadline=Date.now()+waitMs;
  while(current()&&Date.now()<deadline){state=record(await coreCommand("jobs_get",{job_id}));if(["succeeded","failed","cancelled","rejected"].includes(String(state.state)))break;await new Promise(resolve=>setTimeout(resolve,300));}
  if(!current())return null;
  if(!state||state.state!=="succeeded"){setLatestState(state);throw new Error("job did not succeed");}
  const [rawText,structure,loss,quality]=await Promise.all([coreCommand("job_output",{job_id,kind:"text"}),coreCommand("job_output",{job_id,kind:"document_structure"}),coreCommand("job_output",{job_id,kind:"loss_report"}),coreCommand("job_quality",{job_id})]);
  const result=record(rawText);if(typeof result.content!=="string")throw new Error("invalid text output");
  const structureOutput=record(structure), lossOutput=record(loss);
  if(typeof structureOutput.content!=="string"||typeof lossOutput.content!=="string")throw new Error("invalid structured output");
  const parsedStructure=JSON.parse(structureOutput.content), parsedLoss=JSON.parse(lossOutput.content);
  let actualSourceJob:Record<string,unknown>|null=null;
  if(executionKind==="transcribe"||executionKind==="video"||extension==="epub"){
   const listing=record(await coreCommand("source_jobs",{source_id:sourceId}));
   if(listing.source_id!==sourceId||!Array.isArray(listing.jobs)||listing.jobs.length>50)throw new Error("bounded source jobs mismatch");
   const rows=listing.jobs.map(record);
   if(rows.some(row=>row.input_ref!==sourceId))throw new Error("source jobs identity mismatch");
   const matches=rows.filter(row=>row.job_id===job_id);
   if(matches.length!==1)throw new Error("successful source job missing or ambiguous");
   actualSourceJob=matches[0];
  }
  const verifiedEpub=extension==="epub"?await epubProof(sourceId,sourceRevision,job_id,state,lossOutput,actualSourceJob!):null;
  const verifiedTranscription=(executionKind==="transcribe"||executionKind==="video")?await transcriptionProof(sourceId,sourceRevision,job_id,state,lossOutput,actualSourceJob!,executionKind):null;
  const sourceTransform=record(await coreCommand("source_job_transform",{source_id:sourceId,job_id}));
  if(sourceTransform.source_id!==sourceId||sourceTransform.job_id!==job_id||typeof sourceTransform.transform_id!=="number"||sourceTransform.content!==result.content)throw new Error("source transform mismatch");
  if(current()){if(verifiedTranscription)setTranscription(verifiedTranscription);if(verifiedEpub)setEpub(verifiedEpub);setText(result.content);setTransform(sourceTransform);setCandidateId("");setSelection({start:0,end:0});setLatestState(state);setProof({structure:parsedStructure,loss:parsedLoss,quality});}
  return record(parsedLoss);
 }
 async function execute(executionKind=kind){
  if(!executionKind||busy)return;const generation=++loadGeneration.current;const boundIdentity=identity;const current=()=>alive.current&&currentIdentity.current===boundIdentity&&loadGeneration.current===generation;setBusy(true);setSplitProgress(null);setLatestState({state:"starting"});setMessage("正在启动真实转换…");
  const job_id=`read_${crypto.randomUUID()}`;setJob(job_id);
  try{
   const media=executionKind==="transcribe"||executionKind==="video";
   await runAndPublish(executionKind,job_id,{deadline_ms:media?300000:60000},media?310000:90000,current);
   if(current())setMessage("真实转换已完成；下方文本、结构、损失及引擎回执均来自 Core。");
  }catch{if(current())setMessage("转换未完成或产物读取失败。不会把失败或未知状态当作成功。");}
  finally{window.dispatchEvent(new Event("archeaxis-job-changed"));if(current())setBusy(false);}
 }
 /** Transcribe a recording too long for one job, across as many bounded invocations as it needs.
  *
  * Each round is its own job, so a failure or a stop costs one round rather than the recording;
  * windows already finished are kept under the recording's own digest and reused by the next
  * round. Every round publishes what it produced, and the loop stops when the receipt says all
  * windows are done — never because a round count was reached.
  */
 async function executeSplit(){
  const executionKind=kind;
  if(!executionKind||busy||!mediaEstimate)return;
  const generation=++loadGeneration.current;const boundIdentity=identity;const current=()=>alive.current&&currentIdentity.current===boundIdentity&&loadGeneration.current===generation;
  setBusy(true);setSplitProgress(null);setLatestState({state:"starting"});
  // A round finishes at least one window, so the recording cannot need more rounds than it has
  // windows. The cap exists only so a wedged engine cannot loop forever, and running into it is
  // reported as a failure rather than as a completion.
  const cap=mediaEstimate.windowsTotal+1;
  try{
   for(let round=1;round<=cap&&current();round+=1){
    const job_id=`split_${crypto.randomUUID()}`;setJob(job_id);
    setMessage(`分段执行第 ${round} 次（单次上限 ${formatEstimate(MEDIA_CEILING_MS)}）；已完成的分段会在下一次直接复用，不会重跑。`);
    const loss=await runAndPublish(executionKind,job_id,{deadline_ms:MEDIA_CEILING_MS,split:true},MEDIA_CEILING_MS+10000,current);
    if(!loss||!current())return;
    const progress=splitProgressOf(loss);
    setSplitProgress(progress);
    if(progress&&progress.status==="complete"){setMessage(`分段转写已完成：${describeSplit(progress)}文本、结构、损失及引擎回执均来自 Core。`);return;}
    setMessage(`第 ${round} 次未覆盖整段录音。${progress?describeSplit(progress):"分段记录未随回执返回。"}继续下一轮。`);
   }
   throw new Error("split did not complete within the planned rounds");
  }catch{if(current())setMessage("分段转写未完成或产物读取失败。不会把失败或未知状态当作成功。");}
  finally{window.dispatchEvent(new Event("archeaxis-job-changed"));if(current())setBusy(false);}
 }
 async function createCandidate(){
  if(!transform||busy||selection.end<=selection.start||!candidateBody.trim())return;const boundIdentity=identity;const generation=loadGeneration.current;const current=()=>alive.current&&currentIdentity.current===boundIdentity&&loadGeneration.current===generation;setBusy(true);
  try{
   const receipt=record(await coreCommand("knowledge_from_transform",{body:{knowledge_type:"source_note",body:candidateBody.trim(),source_id:sourceId,job_id:transform.job_id,transform_id:transform.transform_id,selection_start_utf16:selection.start,selection_end_utf16:selection.end,quote:text.slice(selection.start,selection.end)}}));
   if(receipt.status!=="candidate"||typeof receipt.knowledge_id!=="string"||typeof receipt.anchor_id!=="string")throw new Error("invalid candidate receipt");
   if(current()){setCandidateId(receipt.knowledge_id);setMessage("已创建来源与引文绑定的知识候选，尚未接受。");}
  }catch{if(current())setMessage("知识候选创建未确认，请保留正文与选区重试。");}finally{if(current())setBusy(false);}
 }
 return <section aria-label="真实转换产物"><p>能力目录只证明握手。引擎身份与结果以实际 job 的质量回执为准。</p>{["transcribe","video"].includes(kind??"")?<p>媒体头信息探测不表示已解码、转写或核对时间段内容。</p>:null}{kind==="media"?<p>仅探测媒体头信息；不表示已解码、转写或核对时间段内容。</p>:kind==="archive"?<p>容器清点与成员正文处理分别记录；清点成功不表示所有成员已读取。</p>:null}<RawReceiptButton label="当前能力握手" payload={capabilities} />{mediaEstimate?<div className="media-estimate"><p>原件时长 {formatEstimate(Math.round((mediaDurationSeconds??0)*1000))}；按当前声明策略（CPU 系数 {MEDIA_REALTIME_FACTOR}、单作业上限 {formatEstimate(MEDIA_CEILING_MS)}）整体执行预计 {formatEstimate(mediaEstimate.wholeEstimatedMs)}。</p>{mediaEstimate.wholeExceedsCeiling?<p role="status">整体执行预计 {formatEstimate(mediaEstimate.wholeEstimatedMs)}，已超过单作业上限，无法在一次执行内完成；此原件需分 {mediaEstimate.windowsTotal} 段（每段约 {formatEstimate(mediaEstimate.windowAudioMs)} 音频，单段预计 {formatEstimate(mediaEstimate.windows[0].estimatedMs)}）。请选择“切分执行”；整体执行会在 {formatEstimate(MEDIA_CEILING_MS)} 处被中止。</p>:<p>整体执行在上限内，可直接执行；也可由你选择切分执行——分段按录音自身的时长在同一策略下划分，结果同源。</p>}{splitProgress?<p role="status">{describeSplit(splitProgress)}</p>:null}</div>:null}{mediaEstimate?<><button disabled={busy||mediaEstimate.wholeExceedsCeiling} onClick={()=>void execute()}>{mediaEstimate.wholeExceedsCeiling?"整体执行（超过单作业上限，已停用）":"整体执行"}</button><button disabled={busy} onClick={()=>void executeSplit()}>切分执行（{mediaEstimate.windowsTotal} 段，可续跑）</button></>:kind?<button disabled={busy} onClick={()=>void execute()}>{kind==="media"?"执行媒体头信息探测":kind==="archive"?"清点容器与登记成员":kind==="transcribe"?"执行真实语音转写":kind==="video"?"执行真实视频分析":"执行真实内容转换"}</button>:<p>此格式尚无当前阅读转换通路，原件已保留。</p>}{["transcribe","video"].includes(kind??"")?<button disabled={busy} onClick={()=>void execute("media")}>执行媒体头信息探测</button>:null}{epub?<EpubParagraphs proof={epub} seek={epubSeek} onSeek={onEpubSeek} onAnchor={onAnchor}/>:null}{transcription?<TranscriptionCues proof={transcription} onTimeSeek={onTimeSeek} onAnchor={onAnchor}/>:null}{job?<p>最新任务 {job}</p>:null}{latestState?<RawReceiptButton label="最新处理状态与错误记录" payload={latestState} />:null}{message?<p role="status">{message}</p>:null}{text?<><pre aria-label="Core 提取正文">{text}</pre><label>选择实际引文 <textarea readOnly value={text} onSelect={event=>setSelection({start:event.currentTarget.selectionStart,end:event.currentTarget.selectionEnd})}/></label><p>已选引文：{text.slice(selection.start,selection.end)}</p><label>知识候选正文 <textarea value={candidateBody} disabled={busy} onChange={event=>setCandidateBody(event.target.value)}/></label><button disabled={busy||!transform||selection.end<=selection.start||!candidateBody.trim()} onClick={()=>void createCandidate()}>创建知识候选</button>{candidateId?<p>候选 {candidateId} <button onClick={onKnowledge}>前往知识库审核</button></p>:null}</>:null}{proof&&typeof proof==="object"&&"structure" in proof?<StructurePreview key={job} structure={proof.structure} text={text}/>:null}{proof?<><p>损失记录与引擎身份来自本次实际任务；握手声明不代替执行证据。</p><RawReceiptButton label="损失、引擎与处理记录" payload={proof} /></>:null}</section>;
}
