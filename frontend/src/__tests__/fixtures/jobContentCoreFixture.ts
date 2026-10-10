import { createHash } from "node:crypto";
type Row=Record<string,unknown>;
const revision="a".repeat(64);
export function outputReceipt(kind:unknown,content:string){return {content,metadata:{kind,sha256:createHash("sha256").update(content,"utf8").digest("hex"),byte_length:Buffer.byteLength(content,"utf8")}};}
/** SIMULATED compatibility upgrade for pre-contract fixtures, never a product parser. */
export function jobContentCoreFixture(legacy:(op:string,p:Row)=>unknown){
 const jobs=new Map<string,Row>();const requests=new Map<string,Row>();
 return async(op:string,p:Row={})=>{
  const id=String(p.job_id);
  if(op==="job_enqueue"){
   const body=p.body as Row;const value=await legacy(op,p) as Row;jobs.set(String(body.job_id),{kind:body.kind,input_ref:body.input_ref});
   return {state:"queued",...value};
  }
  if(op==="job_execute"){
   const value=await legacy(op,p) as Row;requests.set(id,{request_id:p.request_id,budget:p.body});
   return {job_id:id,request_id:p.request_id,replayed:false,state:"running",...(value??{})};
  }
  if(op==="source_jobs"){
   const value=await legacy(op,p) as Row;
   if(!Array.isArray(value?.jobs))return value;
   return {...value,jobs:value.jobs.map((raw:Row)=>{const row:Row={request_id:`persisted_${raw.job_id}`,...raw};jobs.set(String(row.job_id),row);return row;})};
  }
  if(op==="job_execution_status"||op==="jobs_get"){
   const value=await legacy("jobs_get",p) as Row;if(typeof value?.state!=="string")throw new Error("SIMULATED legacy fixture must specify actual job state");
   const job=jobs.get(id)??{};const request=requests.get(id);const request_id=request?.request_id??job.request_id??`persisted_${id}`;
   const row:Row={job_id:id,kind:job.kind,input_ref:job.input_ref,attempt:1,request_id,error:typeof value.error_code==="string"?value.error_code:null,...value};
   return op==="jobs_get"?row:{...row,attempts:[{attempt:row.attempt,request_id:row.request_id,state:row.state,budget:request?.budget??{deadline_ms:60000,split:false,words:false},continuation:{new_attempt_eligible_state:["failed","cancelled"].includes(String(row.state))}}]};
  }
  if(op==="job_output"){
   const value=await legacy(op,p) as Row;if(typeof value?.content!=="string")throw new Error("SIMULATED output fixture needs real content");const content=p.kind==="loss_report"&&value.content==="[]"?JSON.stringify({engine:"SIMULATED",engine_version:"fixture",params:{},loss_note:"SIMULATED"}):value.content;const fresh=outputReceipt(p.kind,content);const existing=value.metadata&&typeof value.metadata==="object"&&!Array.isArray(value.metadata)?value.metadata as Row:{};return {...value,content,metadata:{...fresh.metadata,...existing}};
  }
  if(op==="source_job_transform")return {raw_sha256:revision,...await legacy(op,p) as Row};
  if(op==="job_quality")return {job_id:id,...await legacy(op,p) as Row};
  return legacy(op,p);
 };
}
