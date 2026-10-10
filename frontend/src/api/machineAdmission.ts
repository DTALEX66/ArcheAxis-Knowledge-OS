import type { MachineAdmissionRefusal } from "./client";
import { sha256 } from "../presentation/exchangeProof";

/** Finite normalization mirrors runtime/context_refusal.rs, including absent/null defaults. */
export function normalizedMachineAdmissionRequest(operation:"answer"|"retest", request:Record<string,unknown>) {
  const keys=["knowledge_id","question","max_tokens","timeout_s","context_grant","asset_context_grant",operation==="answer"?"client_request_id":"retest_of"];
  if(Object.keys(request).some(key=>!keys.includes(key)))throw new Error("unknown frozen machine field");
  return {operation,request:{knowledge_id:request.knowledge_id,question:request.question,
    max_tokens:request.max_tokens??2048,timeout_s:request.timeout_s??120,
    context_grant:request.context_grant??null,asset_context_grant:request.asset_context_grant??null,
    client_request_id:operation==="answer"?(request.client_request_id??null):null,
    retest_of:operation==="retest"?request.retest_of:null}};
}
export async function machineAdmissionRequestSha(operation:"answer"|"retest", request:Record<string,unknown>):Promise<string> {
  const canonical=JSON.stringify(normalizedMachineAdmissionRequest(operation,request),(_key,item:unknown)=>
    item&&typeof item==="object"&&!Array.isArray(item)?Object.fromEntries(Object.entries(item as Record<string,unknown>).sort(([a],[b])=>a<b?-1:a>b?1:0)):item);
  return sha256(new TextEncoder().encode(canonical));
}
export async function readMachineAdmissionRefusal(value:unknown, operation:"answer"|"retest", request:Record<string,unknown>):Promise<MachineAdmissionRefusal|undefined> {
  if(!value||typeof value!=="object"||Array.isArray(value))return;
  const r=value as Record<string,unknown>,g=r.grant as Record<string,unknown>|undefined,c=request.context_grant as Record<string,unknown>|undefined;
  if(r.schema!=="archeaxis.context-admission-refusal/v1"||r.reason_code!=="RESTORED_GRANT_FENCED"
    ||r.execution_state!=="NOT_EXECUTED"||r.execution_scope!=="CURRENT_INVOCATION"||r.prior_request_execution!=="UNVERIFIED"||r.answer_published!==false
    ||r.operation!==operation||r.knowledge_id!==request.knowledge_id||typeof r.knowledge_id!=="string"||!r.knowledge_id
    ||r.client_request_id!==(operation==="answer"?(request.client_request_id??null):null)||r.retest_of!==(operation==="retest"?request.retest_of:null)
    ||!g||!c||Array.isArray(g)||Array.isArray(c)||g.document_id!==c.document_id||typeof g.document_id!=="string"||!g.document_id||g.document_id.length>256
    ||g.version!==c.version||!Number.isSafeInteger(g.version)||Number(g.version)<1
    ||g.content_sha256!==c.content_sha256||typeof g.content_sha256!=="string"||!/^[a-f0-9]{64}$/.test(g.content_sha256)
    ||typeof r.request_sha256!=="string"||!/^[a-f0-9]{64}$/.test(r.request_sha256))return;
  try {if(r.request_sha256!==await machineAdmissionRequestSha(operation,request))return;}catch{return;}
  // Only redacted fields enter ApiError and the UI observation surface.
  return {schema:"archeaxis.context-admission-refusal/v1",reason_code:"RESTORED_GRANT_FENCED",execution_state:"NOT_EXECUTED",execution_scope:"CURRENT_INVOCATION",prior_request_execution:"UNVERIFIED",answer_published:false,
    operation,knowledge_id:r.knowledge_id,client_request_id:r.client_request_id as string|null,retest_of:r.retest_of as string|null,request_sha256:r.request_sha256,
    grant:{document_id:g.document_id,version:g.version as number,content_sha256:g.content_sha256}};
}
