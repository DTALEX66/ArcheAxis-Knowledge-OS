import { splitProgressOf, type SplitProgress } from "./mediaEstimate";
import { utf8Sha256 } from "../components/TranscriptionCues";
import { folderJobStatus, type FolderAttempt } from "./folderIngestExecution";
import type { JobStatus } from "../components/BoundedJobPanel";
export type ManualAttempt = FolderAttempt & Readonly<{source_id:string; source_revision:string; kind:string; identity:string; mode:"single"|"split"}>;
export function freezeManualAttempt(source_id:string,source_revision:string|undefined,kind:string,identity:string,split:boolean):ManualAttempt {
 if(!source_revision||!/^[a-f0-9]{64}$/.test(source_revision))throw new Error("原件指纹未核实，不能开始转换");
 const media=kind==="transcribe"||kind==="video";
 return Object.freeze({job_id:`${split?"split":"read"}_${crypto.randomUUID()}`,request_id:`read_run_${crypto.randomUUID()}`,source_id,source_revision,kind,identity,mode:split?"split":"single",body:Object.freeze({deadline_ms:media?300000:60000,split,words:false})});
}
export function manualStatus(value:unknown,a:ManualAttempt):JobStatus {
 const result=folderJobStatus(value,a.job_id,a.source_id,a);
 if(result.kind!==a.kind)throw new Error("转换种类与冻结请求不一致");
 return result;
}
export async function verifiedJobOutput(value:unknown,kind:"text"|"document_structure"|"loss_report"):Promise<{content:string;metadata:Record<string,unknown>}> {
 if(!value||typeof value!=="object"||Array.isArray(value))throw new Error("产物结构无效");
 const output=value as Record<string,unknown>;const m=output.metadata;
 if(typeof output.content!=="string"||!m||typeof m!=="object"||Array.isArray(m))throw new Error("产物指纹未提供");
 const metadata=m as Record<string,unknown>;
 if(metadata.kind!==kind||metadata.sha256!==await utf8Sha256(output.content)||metadata.byte_length!==new TextEncoder().encode(output.content).byteLength)throw new Error("产物种类、SHA256或UTF8字节长度不匹配");
 return {content:output.content,metadata};
}
export function pinnedSuccess(value:Record<string,unknown>,job:string,source:string):void {
 if(value.job_id!==job||value.input_ref!==source||value.state!=="succeeded"||!Number.isSafeInteger(value.attempt)||Number(value.attempt)<1||typeof value.request_id!=="string"||!value.request_id.trim())throw new Error("成功产物的尝试身份未提供");
}

export function verifiedSplitProgress(loss:Record<string,unknown>):SplitProgress|null {
 const p=splitProgressOf(loss);if(!p||!["complete","partial"].includes(p.status)||p.expected<1||p.present<1||p.present>p.expected)return null;
 if(new Set(p.missing).size!==p.missing.length||p.missing.some(n=>n<0||n>=p.expected)||p.resumed.some(n=>n<0||n>=p.expected)||p.present+p.missing.length!==p.expected)return null;
 if(p.status==="complete"&&(p.present!==p.expected||p.missing.length!==0))return null;
 if(p.status==="partial"&&p.missing.length===0)return null;
 return p;
}
