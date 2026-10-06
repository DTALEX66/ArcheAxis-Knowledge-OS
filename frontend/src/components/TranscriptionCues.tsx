import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import type { AnchorDto } from "../api/generated/core-contract";
import { Section } from "./RealData";

// A bounded view of a verified job receipt, never a second persistence DTO.
export interface TranscriptionProof {
  sourceId: string; revision: string; jobId: string; attempt: number; resultSha256: string;
  durationMs: number; cues: Array<{ start_ms: number; end_ms: number; text: string }>; pipeline?: Record<string,unknown>;
}
export async function utf8Sha256(text: string): Promise<string> {
  const bytes = new TextEncoder().encode(text);
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(hash), value => value.toString(16).padStart(2, "0")).join("");
}
export async function transcriptionProof(sourceId:string, revision:string|undefined,
  jobId:string, state:Record<string,unknown>, lossOutput:Record<string,unknown>, sourceJob:Record<string,unknown>, expectedKind:"transcribe"|"video"="transcribe"):Promise<TranscriptionProof> {
  if (!revision || !/^[a-f0-9]{64}$/i.test(revision) || state.job_id!==jobId || state.input_ref!==sourceId
    || !Number.isSafeInteger(state.attempt) || Number(state.attempt)<1 || state.state!=="succeeded"
    || typeof lossOutput.content!=="string") throw new Error("transcription identity missing");
  if (!sourceJob || sourceJob.job_id!==jobId || sourceJob.input_ref!==sourceId || sourceJob.kind!==expectedKind
    || sourceJob.state!=="succeeded" || sourceJob.attempt!==state.attempt) throw new Error("source job identity mismatch");
  const metadata=lossOutput.metadata as Record<string,unknown>|undefined;
  if (!metadata || metadata.kind!=="loss_report" || metadata.sha256!==await utf8Sha256(lossOutput.content)
    || metadata.byte_length!==new TextEncoder().encode(lossOutput.content).byteLength) throw new Error("transcription receipt digest mismatch");
  const output=JSON.parse(lossOutput.content)?.params?.worker_output;
  if (!output || !Number.isSafeInteger(output.duration_ms) || output.duration_ms<0 || !Array.isArray(output.cues)
    || output.cues.some((cue:any)=>!Number.isSafeInteger(cue.start_ms)||!Number.isSafeInteger(cue.end_ms)
      ||cue.start_ms<0||cue.start_ms>=cue.end_ms||cue.end_ms>output.duration_ms||typeof cue.text!=="string")) throw new Error("invalid transcription cues");
  return {sourceId,revision,jobId,attempt:Number(state.attempt),resultSha256:String(metadata.sha256),durationMs:output.duration_ms,cues:output.cues,pipeline:output};
}
export function TranscriptionCues({proof,onTimeSeek,onAnchor}:{proof:TranscriptionProof;onTimeSeek?:(seconds:number)=>void;onAnchor?:(anchor:AnchorDto)=>void}) {
  const [message,setMessage]=useState(""); const [busy,setBusy]=useState(false); const [page,setPage]=useState(0); const epoch=useRef(0);
  useEffect(()=>{epoch.current++;setMessage("");setBusy(false);setPage(0);return()=>{epoch.current++;};},[proof]);
  async function cite(index:number) {
    if(busy)return; const current=epoch.current; const cue=proof.cues[index];if(!cue)return;setBusy(true);
    try {
      const checksum=await utf8Sha256(cue.text);if(current!==epoch.current)return;
      const anchor=await coreCommand<AnchorDto>("anchor_create",{source_id:proof.sourceId,body:{revision:proof.revision,
        position:JSON.stringify({type:"time",job_id:proof.jobId,attempt:proof.attempt,cue_index:index,start_ms:cue.start_ms,end_ms:cue.end_ms,result_sha256:proof.resultSha256}),checksum}});
      if(current!==epoch.current)return;
      const located=JSON.parse(anchor.position);
      if(!anchor.anchor_id||anchor.source_id!==proof.sourceId||anchor.source_revision!==proof.revision
        ||located.type!=="time"||located.job_id!==proof.jobId||located.attempt!==proof.attempt
        ||located.cue_index!==index||located.start_ms!==cue.start_ms||located.end_ms!==cue.end_ms
        ||located.result_sha256!==proof.resultSha256||located.checksum!==checksum)throw new Error("anchor receipt identity mismatch");
      setMessage(anchor.location_status==="located"?"时间与转写回执关联已校验；识别忠实度仍需独立核验。":"时间引用已记录，定位尚未校验。");onAnchor?.(anchor);
    } catch {if(current===epoch.current)setMessage("时间引用未确认，请保留转写结果后重试。");}
    finally {if(current===epoch.current)setBusy(false);}
  }
  return <Section title="真实转写时间段"><p>来自成功任务 {proof.jobId}，尝试 {proof.attempt}；定位校验不代表识别正确。</p>
    {proof.cues.length?<><table className="data-table"><thead><tr><th>时间</th><th>转写文本</th><th>操作</th></tr></thead><tbody>{proof.cues.slice(page*30,(page+1)*30).map((cue,offset)=>{const index=page*30+offset;return <tr key={index}><td>{(cue.start_ms/1000).toFixed(3)}–{(cue.end_ms/1000).toFixed(3)} 秒</td><td>{cue.text}</td><td>{onTimeSeek?<button onClick={()=>onTimeSeek(cue.start_ms/1000)}>定位到媒体时间</button>:null}<button disabled={busy} onClick={()=>void cite(index)}>引用时间段</button></td></tr>;})}</tbody></table>{proof.cues.length>30?<nav aria-label="转写时间段分页"><button disabled={page===0} onClick={()=>setPage(value=>value-1)}>上一组时间段</button><span>{page+1} / {Math.ceil(proof.cues.length/30)}</span><button disabled={(page+1)*30>=proof.cues.length} onClick={()=>setPage(value=>value+1)}>下一组时间段</button></nav>:null}</>:<p>没有通过时间范围校验的语音片段；原始文本与无法定位记录仍在损失回执，不能据此判断没有语音。</p>}
    {proof.pipeline?<section aria-label={Array.isArray(proof.pipeline.visual_results)?"独立视频帧识别结果":"转写定位状态"}>
      <p>处理状态：{String(proof.pipeline.pipeline_state??proof.pipeline.processing_status??proof.pipeline.alignment_status??"未提供")}；未定位片段：{Array.isArray(proof.pipeline.alignment_issues)?proof.pipeline.alignment_issues.length:0}。</p>
      {Array.isArray(proof.pipeline.visual_results)?<><p>抽样帧描述与语音原文独立；请求时间近似，未覆盖区间没有视觉分析，不代表连续视频理解。</p><ul>{proof.pipeline.visual_results.map((entry:unknown,index:number)=>{const item=entry&&typeof entry==="object"?entry as Record<string,unknown>:{};return <li key={index}><p>帧 {index+1}：{String(item.state??"未提供")}；请求时间 {typeof item.sampling_seek_requested_ms==="number"&&Number.isFinite(item.sampling_seek_requested_ms)?(Number(item.sampling_seek_requested_ms)/1000).toFixed(3):"未知"} 秒（近似）。</p>{typeof item.description==="string"?<p>{item.description}</p>:null}{item.state!=="succeeded"?<p>疑点：{String(item.reason??"识别未完成")}；可用语音原文仍保留。</p>:<p>模型描述仍需语义核验。</p>}</li>;})}</ul></>:null}
      {Array.isArray(proof.pipeline.alignment_issues)&&proof.pipeline.alignment_issues.length?<p>原始转写含无法定位的片段；正文没有截断，不提供这些片段的时间引用。</p>:null}
      <details><summary>阶段与原始定位记录</summary><pre>{JSON.stringify({state:proof.pipeline.pipeline_state,stages:proof.pipeline.stages,processing_error:proof.pipeline.processing_error,alignment_issues:proof.pipeline.alignment_issues,visual_results:proof.pipeline.visual_results},null,2)}</pre></details>
    </section>:null}
    {message?<p role="status">{message}</p>:null}</Section>;
}
