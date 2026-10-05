import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import type { AnchorDto } from "../api/generated/core-contract";
import { Section } from "./RealData";

// A bounded view of a verified job receipt, never a second persistence DTO.
export interface TranscriptionProof {
  sourceId: string; revision: string; jobId: string; attempt: number; resultSha256: string;
  durationMs: number; cues: Array<{ start_ms: number; end_ms: number; text: string }>;
}
export async function utf8Sha256(text: string): Promise<string> {
  const bytes = new TextEncoder().encode(text);
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(hash), value => value.toString(16).padStart(2, "0")).join("");
}
export async function transcriptionProof(sourceId:string, revision:string|undefined,
  jobId:string, state:Record<string,unknown>, lossOutput:Record<string,unknown>):Promise<TranscriptionProof> {
  if (!revision || !/^[a-f0-9]{64}$/i.test(revision) || state.job_id!==jobId || state.input_ref!==sourceId
    || !Number.isSafeInteger(state.attempt) || Number(state.attempt)<1 || state.state!=="succeeded" || state.kind!=="transcribe"
    || typeof lossOutput.content!=="string") throw new Error("transcription identity missing");
  const metadata=lossOutput.metadata as Record<string,unknown>|undefined;
  if (!metadata || metadata.kind!=="loss_report" || metadata.sha256!==await utf8Sha256(lossOutput.content)
    || metadata.byte_length!==new TextEncoder().encode(lossOutput.content).byteLength) throw new Error("transcription receipt digest mismatch");
  const output=JSON.parse(lossOutput.content)?.params?.worker_output;
  if (!output || !Number.isSafeInteger(output.duration_ms) || output.duration_ms<0 || !Array.isArray(output.cues)
    || output.cues.some((cue:any)=>!Number.isSafeInteger(cue.start_ms)||!Number.isSafeInteger(cue.end_ms)
      ||cue.start_ms<0||cue.start_ms>=cue.end_ms||cue.end_ms>output.duration_ms||typeof cue.text!=="string")) throw new Error("invalid transcription cues");
  return {sourceId,revision,jobId,attempt:Number(state.attempt),resultSha256:String(metadata.sha256),durationMs:output.duration_ms,cues:output.cues};
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
    {proof.cues.length?<><table className="data-table"><thead><tr><th>时间</th><th>转写文本</th><th>操作</th></tr></thead><tbody>{proof.cues.slice(page*30,(page+1)*30).map((cue,offset)=>{const index=page*30+offset;return <tr key={index}><td>{(cue.start_ms/1000).toFixed(3)}–{(cue.end_ms/1000).toFixed(3)} 秒</td><td>{cue.text}</td><td>{onTimeSeek?<button onClick={()=>onTimeSeek(cue.start_ms/1000)}>定位到媒体时间</button>:null}<button disabled={busy} onClick={()=>void cite(index)}>引用时间段</button></td></tr>;})}</tbody></table>{proof.cues.length>30?<nav aria-label="转写时间段分页"><button disabled={page===0} onClick={()=>setPage(value=>value-1)}>上一组时间段</button><span>{page+1} / {Math.ceil(proof.cues.length/30)}</span><button disabled={(page+1)*30>=proof.cues.length} onClick={()=>setPage(value=>value+1)}>下一组时间段</button></nav>:null}</>:<p>实际转写没有语音片段；空结果不计作正文转写成功。</p>}
    {message?<p role="status">{message}</p>:null}</Section>;
}
