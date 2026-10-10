import { downloadBytes } from "../presentation/exchangeProof";
import { useEffect, useId, useRef, useState } from "react";
import { ApiError } from "../api/client";
import { freezeManualAttempt, manualStatus, pinnedSuccess, verifiedJobOutput, verifiedSplitProgress, type ManualAttempt } from "../presentation/jobContentExecution";
import { folderExecutionAck, folderCancelAck, terminalJobState } from "../presentation/folderIngestExecution";
import { coreCommand } from "../api/core";
import { conversionKindFor } from "../api/conversionKinds";
import { estimateMediaWork, formatEstimate, describeSplit, MEDIA_CEILING_MS, MEDIA_REALTIME_FACTOR, type SplitProgress } from "../presentation/mediaEstimate";
import { RawReceiptButton } from "./DiagnosticConsole";
import { DataTable, Section } from "./RealData";
import { TranscriptionCues, transcriptionProof, type TranscriptionProof } from "./TranscriptionCues";
import { EpubParagraphs, epubProof, type EpubProof, type EpubPosition } from "./EpubParagraphs";
import type { AnchorDto } from "../api/generated/core-contract";

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
function ResultTransparency({proof}:{proof:unknown}) {
 if(!proof||typeof proof!=="object"||Array.isArray(proof))return null;
 const p=proof as Record<string,unknown>;const q=p.quality&&typeof p.quality==="object"&&!Array.isArray(p.quality)?p.quality as Record<string,unknown>:{};
 const loss=p.loss&&typeof p.loss==="object"&&!Array.isArray(p.loss)?p.loss as Record<string,unknown>:{};
 const field=(value:unknown)=>typeof value==="string"&&value.trim()?value:"未提供 / UNVERIFIED";
 const count=Number.isSafeInteger(q.loss_count)&&Number(q.loss_count)>=0?String(q.loss_count):"未提供 / UNVERIFIED";
 return <Section title="转换与损失说明"><dl><dt>实际引擎</dt><dd>{field(q.engine)}</dd><dt>引擎版本（回执原值，未独立核验）</dt><dd>{field(q.engine_version)}</dd><dt>记录的损失数量</dt><dd>{count}</dd><dt>格式与内容损失</dt><dd>{field(loss.loss_note)}</dd></dl><p>结构中的页、段落或字符范围是转换提供的位置事实；未独立核验原件定位，也不表示专业内容正确。</p></Section>;
}
export function JobContent({sourceId,name,pinnedJobId,readOnly=false,onKnowledge,onDirtyChange,sourceRevision,onTimeSeek,onAnchor,epubSeek,onEpubSeek,mediaDurationSeconds}:{sourceId:string;name:string;pinnedJobId?:string;readOnly?:boolean;onKnowledge?:()=>void;onDirtyChange?:(dirty:boolean)=>void;sourceRevision?:string;onTimeSeek?:(seconds:number)=>void;onAnchor?:(anchor:AnchorDto)=>void;epubSeek?:EpubPosition;onEpubSeek?:(position:EpubPosition)=>void;mediaDurationSeconds?:number}) {
 const [epub,setEpub]=useState<EpubProof|null>(null);
 const [transcription,setTranscription]=useState<TranscriptionProof|null>(null);
 const loadGeneration=useRef(0);

 const [readbackFiles,setReadbackFiles]=useState<Array<{source_id:string;job_id:string;request_id:string;attempt:number;name:string;content:string;media_type:string}>>([]);
 const [text,setText]=useState(""); const [proof,setProof]=useState<unknown>(null); const [capabilities,setCapabilities]=useState<unknown>(null); const [message,setMessage]=useState(""); const [busy,setBusy]=useState(false); const [job,setJob]=useState(""); const alive=useRef(true);
 const extension=name.split(".").pop()?.toLowerCase();
 const [latestState,setLatestState]=useState<unknown>(null);
 const [splitProgress,setSplitProgress]=useState<SplitProgress|null>(null);
 const [transform,setTransform]=useState<Record<string,unknown>|null>(null);const [selection,setSelection]=useState({start:0,end:0});const [candidateBody,setCandidateBody]=useState("");const [candidateId,setCandidateId]=useState("");
 const owner=`job-content-${useId()}`; const dirtyCallback=useRef(onDirtyChange);dirtyCallback.current=onDirtyChange;
 const flight=useRef(false), cancelFlight=useRef(false), pending=useRef<ManualAttempt|null>(null), candidateRef=useRef("");
 const [frozen,setFrozen]=useState<ManualAttempt|null>(null),[cancelBusy,setCancelBusy]=useState(false),[refused,setRefused]=useState(false);
 const queued=useRef(new Set<string>()),committed=useRef(new Set<string>()),timers=useRef(new Map<number,()=>void>());
 function publishDirty(){if(!alive.current)return;const dirty=flight.current||cancelFlight.current||!!pending.current||!!candidateRef.current.trim();dirtyCallback.current?.(dirty);window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner,dirty}}));}
 function setAttempt(a:ManualAttempt|null){pending.current=a;setFrozen(a);publishDirty();}
 function finish(a:ManualAttempt){if(pending.current?.request_id===a.request_id)setAttempt(null);}
 function wait(ms:number):Promise<void>{return new Promise(resolve=>{const id=window.setTimeout(()=>{timers.current.delete(id);resolve();},ms);timers.current.set(id,resolve);});}
 useEffect(()=>()=>{for(const [id,resolve] of timers.current){window.clearTimeout(id);resolve();}timers.current.clear();dirtyCallback.current?.(false);window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner,dirty:false}}));},[owner]);
 const kind=conversionKindFor(name);
 // The Core refuses a job deadline above the ceiling, so the user is told what the current
 // recording is expected to cost before anything is executed.
 const mediaEstimate=mediaDurationSeconds&&(kind==="transcribe"||kind==="video")?estimateMediaWork(Math.round(mediaDurationSeconds*1000)):null;
 const identity=JSON.stringify([sourceId,sourceRevision??"",extension??"",pinnedJobId??""]);const currentIdentity=useRef(identity);currentIdentity.current=identity;

 useEffect(()=>{
  let active=true;const generation=++loadGeneration.current;
  flight.current=false;cancelFlight.current=false;pending.current=null;setFrozen(null);setRefused(false);setCancelBusy(false);candidateRef.current="";setCandidateBody("");publishDirty();
  setReadbackFiles([]);setEpub(null);setTranscription(null);setText("");setTransform(null);setProof(null);setLatestState(null);setSplitProgress(null);setJob("");setBusy(false);setMessage("");setCandidateId("");setSelection({start:0,end:0});
  if(!sourceRevision)return()=>{active=false;};
  const current=()=>active&&generation===loadGeneration.current;
  (async()=>{
   // An explicit batch result is read by its durable job ID, even when it is older
   // than the recent-source window. Never substitute a newer successful job.
   const pinned=pinnedJobId?record(await coreCommand("job_execution_status",{job_id:pinnedJobId})):null;
   if(pinned&&(pinned.job_id!==pinnedJobId||pinned.input_ref!==sourceId||typeof pinned.kind!=="string"))throw new Error("pinned job identity mismatch");
   const listing=pinned?{source_id:sourceId,jobs:[pinned],jobs_capped:false}:record(await coreCommand("source_jobs",{source_id:sourceId}));
   if(listing.source_id!==sourceId||!Array.isArray(listing.jobs)||listing.jobs.length>50)throw new Error("bounded source jobs mismatch");
   const rows=listing.jobs as Array<Record<string,unknown>>;
   if(rows.some(row=>row.input_ref!==sourceId))throw new Error("source jobs identity mismatch");
   // Read the persisted result back under the same route kind the conversion produced. A
   // text/office/pdf/html/image/archive result must reopen from storage without starting a job,
   // so it can no longer be searched for under a hardcoded "transcribe".
   const targetKind=pinned?String(pinned.kind):extension==="epub"?"text":kind;
   const isMediaRoute=targetKind==="transcribe"||targetKind==="video";
   const resultLabel=isMediaRoute?"转写":extension==="epub"?"章节内容":"转换结果";
   const latest=rows.find(row=>row.kind===targetKind);
   const successful=rows.find(row=>row.kind===targetKind&&row.state==="succeeded");
   if(!successful){if(current()){if(latest){setLatestState(latest);setMessage(`最近一次转换任务状态为 ${String(latest.state)}；未找到成功产物，不表示此前结果不存在。`);}if(listing.jobs_capped===true)setMessage(`仅检查最近 50 个来源任务；未找到其中的成功${resultLabel}，不表示更早结果不存在。`);}return;}
   if(typeof successful.job_id!=="string")throw new Error("persisted job identity missing");
   const id=successful.job_id;
   const [stateValue,rawText,structureValue,lossValue,quality,transformValue]=await Promise.all([
    coreCommand("jobs_get",{job_id:id}),coreCommand("job_output",{job_id:id,kind:"text"}),
    coreCommand("job_output",{job_id:id,kind:"document_structure"}),coreCommand("job_output",{job_id:id,kind:"loss_report"}),
    coreCommand("job_quality",{job_id:id}),coreCommand("source_job_transform",{source_id:sourceId,job_id:id})]);
   const state=record(stateValue),saved=record(transformValue);
   const [textOutput,structure,loss]=await Promise.all([verifiedJobOutput(rawText,"text"),verifiedJobOutput(structureValue,"document_structure"),verifiedJobOutput(lossValue,"loss_report")]);
   // All persisted routes must bind the successful attempt and original revision,
   // not only explicit pins. source_jobs supplies attempt but not request_id.
   pinnedSuccess(state,id,sourceId);
   if(!Number.isSafeInteger(successful.attempt)||Number(successful.attempt)<1||state.attempt!==successful.attempt
    ||saved.raw_sha256!==sourceRevision)throw new Error("persisted result changed or source revision mismatch");
   if(pinned){pinnedSuccess(pinned,id,sourceId);if(state.request_id!==pinned.request_id)throw new Error("pinned result request changed");}
   if(typeof textOutput.content!=="string"||typeof structure.content!=="string"||typeof loss.content!=="string"
    ||saved.source_id!==sourceId||saved.job_id!==id||!Number.isSafeInteger(saved.transform_id)||Number(saved.transform_id)<1||saved.content!==textOutput.content)throw new Error("persisted transform mismatch");
   const verifiedEpub=extension==="epub"?await epubProof(sourceId,sourceRevision,id,state,loss,successful):null;
   const verified=isMediaRoute?await transcriptionProof(sourceId,sourceRevision,id,state,loss,successful,targetKind==="video"?"video":"transcribe"):null;
   if(record(quality).job_id!==id)throw new Error("persisted quality job identity mismatch");
   const parsedStructure=JSON.parse(structure.content),parsedLoss=JSON.parse(loss.content);
   if(!current())return;
   if(verified)setTranscription(verified);if(verifiedEpub)setEpub(verifiedEpub);setText(textOutput.content);setTransform(saved);setProof({structure:parsedStructure,loss:parsedLoss,quality});
   setReadbackFiles([{source_id:sourceId,job_id:id,request_id:String(state.request_id),attempt:Number(state.attempt),name:"正文.txt",content:textOutput.content,media_type:"text/plain"},{source_id:sourceId,job_id:id,request_id:String(state.request_id),attempt:Number(state.attempt),name:"结构.json",content:structure.content,media_type:"application/json"},{source_id:sourceId,job_id:id,request_id:String(state.request_id),attempt:Number(state.attempt),name:"损失.json",content:loss.content,media_type:"application/json"},{source_id:sourceId,job_id:id,request_id:String(state.request_id),attempt:Number(state.attempt),name:"引擎回执.json",content:JSON.stringify(quality,null,2),media_type:"application/json"}]);
   setJob(typeof latest?.job_id==="string"?latest.job_id:id);setLatestState(latest??state);
   setMessage(`已读回持久化${resultLabel}；最新处理状态与已成功的内容分别保留。${listing.jobs_capped===true?"仅检查最近 50 个来源任务。":""}`);
  })().catch(()=>{if(current())setMessage("持久化结果读回未完成；不会自动重新执行任务。");});
  return()=>{active=false;};
 },[sourceId,sourceRevision,extension,pinnedJobId]);

 useEffect(()=>{alive.current=true;coreCommand("capabilities_list").then(value=>{if(alive.current)setCapabilities(value);}).catch(()=>{if(alive.current)setMessage("能力握手读取失败；真实执行结果仍须单独核验。");});return()=>{alive.current=false;};},[]);
 /** Run one job to a terminal state and publish whatever it produced.
  *
  * Returns the parsed loss receipt so a split caller can read its own progress from the same
  * receipt it publishes; nothing here invents a second opinion about what completed.
  */
 async function runAndPublish(a:ManualAttempt,send:boolean,current:()=>boolean):Promise<Record<string,unknown>|null>{
  const job_id=a.job_id,executionKind=a.kind;
  if(send&&!committed.current.has(a.request_id)){
   if(!queued.current.has(job_id)){
    const queue=record(await coreCommand("job_enqueue",{body:{job_id,kind:executionKind,input_ref:a.source_id}}));if(!current())return null;
    if(queue.job_id!==job_id||typeof queue.state!=="string"||!["queued","pending","running","leased","starting","succeeded","failed","cancelled","rejected"].includes(queue.state))throw new Error("job identity mismatch");queued.current.add(job_id);
   }
   window.dispatchEvent(new Event("archeaxis-job-changed"));
   const ack=await coreCommand("job_execute",{job_id,request_id:a.request_id,body:a.body});if(!current())return null;folderExecutionAck(ack,a);
  }
  let state:Record<string,unknown>|null=null;const deadline=Date.now()+a.body.deadline_ms+10000;
  while(current()&&Date.now()<deadline){const read=await coreCommand("job_execution_status",{job_id});if(!current())return null;state=manualStatus(read,a);setLatestState(state);if(terminalJobState(String(state.state)))break;await wait(300);}
  if(!current())return null;
  if(!state||!terminalJobState(String(state.state)))throw new Error("执行终态未确认；冻结请求保留");
  committed.current.add(a.request_id);if(state.state!=="succeeded"){finish(a);throw new Error("job did not succeed");}
  const [rawText,structureValue,lossValue,quality]=await Promise.all([coreCommand("job_output",{job_id,kind:"text"}),coreCommand("job_output",{job_id,kind:"document_structure"}),coreCommand("job_output",{job_id,kind:"loss_report"}),coreCommand("job_quality",{job_id})]);if(!current())return null;
  const [result,structureOutput,lossOutput]=await Promise.all([verifiedJobOutput(rawText,"text"),verifiedJobOutput(structureValue,"document_structure"),verifiedJobOutput(lossValue,"loss_report")]);if(!current())return null;
  if(record(quality).job_id!==job_id)throw new Error("quality job identity mismatch");
  const parsedStructure=JSON.parse(structureOutput.content),parsedLoss=JSON.parse(lossOutput.content);
  let actualSourceJob:Record<string,unknown>|null=null;
  if(executionKind==="transcribe"||executionKind==="video"||extension==="epub"){
   const listing=record(await coreCommand("source_jobs",{source_id:a.source_id}));if(listing.source_id!==a.source_id||!Array.isArray(listing.jobs)||listing.jobs.length>50)throw new Error("bounded source jobs mismatch");
   const rows=listing.jobs.map(record);if(rows.some(row=>row.input_ref!==a.source_id))throw new Error("source jobs identity mismatch");const matches=rows.filter(row=>row.job_id===job_id);if(matches.length!==1)throw new Error("successful source job missing or ambiguous");actualSourceJob=matches[0];
  }
  const verifiedEpub=extension==="epub"?await epubProof(a.source_id,a.source_revision,job_id,state,lossOutput,actualSourceJob!):null;
  const verifiedTranscription=(executionKind==="transcribe"||executionKind==="video")?await transcriptionProof(a.source_id,a.source_revision,job_id,state,lossOutput,actualSourceJob!,executionKind):null;
  const sourceTransform=record(await coreCommand("source_job_transform",{source_id:a.source_id,job_id}));
  if(sourceTransform.source_id!==a.source_id||sourceTransform.job_id!==job_id||sourceTransform.raw_sha256!==a.source_revision||!Number.isSafeInteger(sourceTransform.transform_id)||Number(sourceTransform.transform_id)<1||sourceTransform.content!==result.content)throw new Error("source transform mismatch");
  if(current()){if(verifiedTranscription)setTranscription(verifiedTranscription);if(verifiedEpub)setEpub(verifiedEpub);setText(result.content);setTransform(sourceTransform);setCandidateId("");setSelection({start:0,end:0});setLatestState(state);setProof({structure:parsedStructure,loss:parsedLoss,quality});setReadbackFiles([{source_id:a.source_id,job_id,request_id:a.request_id,attempt:Number(state.attempt),name:"正文.txt",content:result.content,media_type:"text/plain"},{source_id:a.source_id,job_id,request_id:a.request_id,attempt:Number(state.attempt),name:"结构.json",content:structureOutput.content,media_type:"application/json"},{source_id:a.source_id,job_id,request_id:a.request_id,attempt:Number(state.attempt),name:"损失.json",content:lossOutput.content,media_type:"application/json"},{source_id:a.source_id,job_id,request_id:a.request_id,attempt:Number(state.attempt),name:"引擎回执.json",content:JSON.stringify(quality,null,2),media_type:"application/json"}]);finish(a);}return record(parsedLoss);
 }
 async function drive(a:ManualAttempt,send:boolean,current:()=>boolean){
  let next=a;const cap=a.mode==="split"?(mediaEstimate?.windowsTotal??0)+1:1;
  for(let round=1;round<=cap&&current();round++){
   setJob(next.job_id);const loss=await runAndPublish(next,send,current);if(!loss||!current())return;
   if(next.mode!=="split"){setMessage("真实转换已完成；下方文本、结构、损失及引擎回执均来自 Core。");return;}
   const progress=verifiedSplitProgress(loss);setSplitProgress(progress);
   if(!progress){setAttempt(next);throw new Error("分段记录未提供；不能自动启动下一轮");}
   if(progress.status==="complete"){setMessage(`分段转写已完成：${describeSplit(progress)}文本、结构、损失及引擎回执均来自 Core。`);return;}
   if(round===cap)throw new Error("split did not complete within the planned rounds");
   next=freezeManualAttempt(a.source_id,a.source_revision,a.kind,a.identity,true);setAttempt(next);send=true;setMessage(`分段执行第 ${round+1} 次（单次上限 ${formatEstimate(MEDIA_CEILING_MS)}）；按已读回窗口记录复用完成的分段。`);
  }
 }
 async function perform(a:ManualAttempt,send:boolean){
  if(flight.current)return;flight.current=true;setBusy(true);setRefused(false);setAttempt(a);
  const generation=++loadGeneration.current;const current=()=>alive.current&&currentIdentity.current===a.identity&&loadGeneration.current===generation;publishDirty();
  try{await drive(a,send,current);}catch(error){if(current()){if(error instanceof ApiError&&error.status>=400&&error.status<500)setRefused(true);setMessage(`转换未完成或产物读取失败。${pending.current?"结果 UNKNOWN；保留冻结请求，只能同请求重试或读回。":"真实终态已保留，未展示未核验产物。"}${error instanceof Error?` ${error.message}`:""}`);}}
  finally{window.dispatchEvent(new Event("archeaxis-job-changed"));if(current()){flight.current=false;setBusy(false);publishDirty();}}
 }
 async function execute(executionKind=kind){
  if(readOnly||!executionKind||flight.current||cancelFlight.current||pending.current||candidateRef.current.trim())return;
  try{const a=freezeManualAttempt(sourceId,sourceRevision,executionKind,identity,false);setSplitProgress(null);setLatestState({state:"starting"});setMessage("正在启动真实转换…");await perform(a,true);}catch(error){setMessage(error instanceof Error?error.message:"原件身份未核实");}
 }
 async function executeSplit(){
  if(readOnly||!kind||flight.current||cancelFlight.current||pending.current||candidateRef.current.trim()||!mediaEstimate)return;
  try{const a=freezeManualAttempt(sourceId,sourceRevision,kind,identity,true);setSplitProgress(null);setLatestState({state:"starting"});setMessage(`分段执行第 1 次（单次上限 ${formatEstimate(MEDIA_CEILING_MS)}）；完成窗口仅以真实回执为准。`);await perform(a,true);}catch(error){setMessage(error instanceof Error?error.message:"原件身份未核实");}
 }
 async function cancelCurrent(){
  const a=pending.current;if(!a||cancelFlight.current)return;cancelFlight.current=true;setCancelBusy(true);publishDirty();
  const boundIdentity=a.identity;let generation=loadGeneration.current;const current=()=>alive.current&&currentIdentity.current===boundIdentity&&loadGeneration.current===generation&&pending.current?.request_id===a.request_id;
  try{const ack=await coreCommand("job_execution_cancel",{job_id:a.job_id,request_id:a.request_id});if(!current())return;folderCancelAck(ack,a);setMessage("取消请求已受理；202 不等于已取消，终态以 Core 读回为准。");if(!flight.current){const reconciliation=perform(a,false);generation=loadGeneration.current;await reconciliation;}}
  catch(error){if(current())setMessage(`取消未确认；冻结请求保留。${error instanceof Error?error.message:""}`);}
  finally{if(alive.current&&currentIdentity.current===boundIdentity&&loadGeneration.current===generation&&(!pending.current||pending.current.request_id===a.request_id)){cancelFlight.current=false;setCancelBusy(false);publishDirty();}}
 }
 async function createCandidate(){
  if(readOnly||!transform||flight.current||cancelFlight.current||pending.current||selection.end<=selection.start||!candidateBody.trim())return;flight.current=true;publishDirty();const boundIdentity=identity;const generation=loadGeneration.current;const current=()=>alive.current&&currentIdentity.current===boundIdentity&&loadGeneration.current===generation;setBusy(true);
  try{
   const receipt=record(await coreCommand("knowledge_from_transform",{body:{knowledge_type:"source_note",body:candidateBody.trim(),source_id:sourceId,job_id:transform.job_id,transform_id:transform.transform_id,selection_start_utf16:selection.start,selection_end_utf16:selection.end,quote:text.slice(selection.start,selection.end)}}));
   if(receipt.status!=="candidate"||typeof receipt.knowledge_id!=="string"||typeof receipt.anchor_id!=="string")throw new Error("invalid candidate receipt");
   if(current()){setCandidateId(receipt.knowledge_id);setMessage("已创建来源与引文绑定的知识候选，尚未接受。");}
  }catch{if(current())setMessage("知识候选创建未确认，请保留正文与选区重试。");}finally{if(current()){flight.current=false;setBusy(false);publishDirty();}}
 }
 return <section aria-label="真实转换产物">{readOnly?<p>结果审阅模式：转换执行和知识候选编辑关闭。已有引文定位按钮仍是独立保存证据位置的动作，由 Core 核验；此模式不代表禁止所有写入。</p>:null}{readOnly&&readbackFiles.length?<section aria-label="派生结果下载"><p>以下文件来自核验作业 {readbackFiles[0].job_id}、请求 {readbackFiles[0].request_id}、尝试 {readbackFiles[0].attempt>0?readbackFiles[0].attempt:"UNVERIFIED"} 的持久化输出；引擎回执为 Core JSON 展示导出。不是原件字节或所有媒体恢复包。</p>{readbackFiles.map(file=><button key={file.name} onClick={()=>{try{downloadBytes(file.content,`${file.source_id}-${file.job_id}-${file.request_id}-attempt-${file.attempt>0?file.attempt:"UNVERIFIED"}-${file.name}`,file.media_type);setMessage(`已请求浏览器下载派生${file.name}；磁盘落地未读回。`);}catch{setMessage("派生结果下载未完成；保留实际任务与输出。");}}}>下载派生{file.name}</button>)}</section>:null}<p>能力目录只证明握手。引擎身份与结果以实际 job 的质量回执为准。</p>{["transcribe","video"].includes(kind??"")?<p>媒体头信息探测不表示已解码、转写或核对时间段内容。</p>:null}{kind==="media"?<p>仅探测媒体头信息；不表示已解码、转写或核对时间段内容。</p>:kind==="archive"?<p>容器清点与成员正文处理分别记录；清点成功不表示所有成员已读取。</p>:null}<RawReceiptButton label="当前能力握手" payload={capabilities} />{mediaEstimate?<div className="media-estimate"><p>原件时长 {formatEstimate(Math.round((mediaDurationSeconds??0)*1000))}；按当前声明策略（CPU 系数 {MEDIA_REALTIME_FACTOR}、单作业上限 {formatEstimate(MEDIA_CEILING_MS)}）整体执行预计 {formatEstimate(mediaEstimate.wholeEstimatedMs)}。</p>{mediaEstimate.wholeExceedsCeiling?<p>整体执行预计 {formatEstimate(mediaEstimate.wholeEstimatedMs)}，已超过单作业上限，无法在一次执行内完成；此原件需分 {mediaEstimate.windowsTotal} 段（每段约 {formatEstimate(mediaEstimate.windowAudioMs)} 音频，单段预计 {formatEstimate(mediaEstimate.windows[0].estimatedMs)}）。请选择“切分执行”；整体执行会在 {formatEstimate(MEDIA_CEILING_MS)} 处被中止。</p>:<p>整体执行在上限内，可直接执行；也可由你选择切分执行——分段按录音自身的时长在同一策略下划分，结果同源。</p>}{splitProgress?<p>{describeSplit(splitProgress)}</p>:null}</div>:null}{!readOnly&&(mediaEstimate?<><button disabled={busy||cancelBusy||!!frozen||!!candidateBody.trim()||mediaEstimate.wholeExceedsCeiling} onClick={()=>void execute()}>{mediaEstimate.wholeExceedsCeiling?"整体执行（超过单作业上限，已停用）":"整体执行"}</button><button disabled={busy||cancelBusy||!!frozen||!!candidateBody.trim()} onClick={()=>void executeSplit()}>切分执行（{mediaEstimate.windowsTotal} 段，可续跑）</button></>:kind?<button disabled={busy||cancelBusy||!!frozen||!!candidateBody.trim()} onClick={()=>void execute()}>{kind==="media"?"执行媒体头信息探测":kind==="archive"?"清点容器与登记成员":kind==="transcribe"?"执行真实语音转写":kind==="video"?"执行真实视频分析":"执行真实内容转换"}</button>:<p>此格式尚无当前阅读转换通路，原件已保留。</p>)}{!readOnly&&["transcribe","video"].includes(kind??"")?<button disabled={busy||cancelBusy||!!frozen||!!candidateBody.trim()} onClick={()=>void execute("media")}>执行媒体头信息探测</button>:null}{!readOnly&&frozen?<div><p>执行请求已冻结：{frozen.request_id}；单次预算 {frozen.body.deadline_ms/1000}s。未知结果不会产生新作业。</p><button disabled={busy||cancelBusy||refused} onClick={()=>void perform(frozen,true)}>同请求重试转换</button><button disabled={busy||cancelBusy} onClick={()=>void perform(frozen,false)}>读取冻结转换状态</button><button disabled={cancelBusy} onClick={()=>void cancelCurrent()}>请求取消当前转换</button></div>:null}{epub?<EpubParagraphs proof={epub} seek={epubSeek} onSeek={onEpubSeek} onAnchor={onAnchor}/>:null}{transcription?<TranscriptionCues proof={transcription} onTimeSeek={onTimeSeek} onAnchor={onAnchor}/>:null}{job?<p>最新任务 {job}</p>:null}{latestState?<RawReceiptButton label="最新处理状态与错误记录" payload={latestState} />:null}{/* The one announce path of this surface: every round of execute / split-execute / candidate creation writes its loading, success or failure sentence here, and the persisted ceiling advisory and split readout above stay plain text, so one action is announced exactly once instead of three times. */}{message?<p role="status">{message}</p>:null}{text?<><pre aria-label="Core 提取正文">{text}</pre><label>选择实际引文 <textarea readOnly value={text} onSelect={event=>setSelection({start:event.currentTarget.selectionStart,end:event.currentTarget.selectionEnd})}/></label><p>已选引文：{text.slice(selection.start,selection.end)}</p>{!readOnly?<><label>知识候选正文 <textarea value={candidateBody} disabled={busy} onChange={event=>{candidateRef.current=event.target.value;setCandidateBody(event.target.value);publishDirty();}}/></label><button disabled={busy||cancelBusy||!!frozen||!transform||selection.end<=selection.start||!candidateBody.trim()} onClick={()=>void createCandidate()}>创建知识候选</button>{candidateId?<p>候选 {candidateId} <button onClick={onKnowledge}>前往知识库审核</button></p>:null}</>:null}</>:null}{proof&&typeof proof==="object"&&"structure" in proof?<StructurePreview key={job} structure={proof.structure} text={text}/>:null}{proof?<><ResultTransparency proof={proof}/><p>损失记录与引擎身份来自本次实际任务；握手声明不代替执行证据。</p><RawReceiptButton label="损失、引擎与处理记录" payload={proof} /></>:null}</section>;
}
