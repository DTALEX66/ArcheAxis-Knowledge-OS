import { afterEach, describe, expect, it, vi } from "vitest";
import { coreCommand } from "../api/core";
import { ApiError } from "../api/client";
import { jobAdmissionRefusal, recoverableJobRefusal } from "../api/jobAdmission";
const attempt = {job_id:"job",request_id:"same",body:{deadline_ms:5000,split:false,words:false}};
const proof = {schema:"archeaxis.job-admission-refusal/v1",code:"AAK-CAP-001",job_id:"job",request_id:"same",input_ref:"source",kind:"text",capability:"text.extract",budget:attempt.body,admission_state:"NOT_ADMITTED",request_consumed:false,active_execution:false,enabled:false,same_request_retry_allowed:true};
afterEach(()=>{delete window.__TAURI__;});
describe("exact Core job non-admission proof",()=>{
  it("retains a matching proof only for job_execute",async()=>{
    window.__TAURI__={core:{invoke:vi.fn().mockResolvedValue({status:409,body:proof})}};
    await expect(coreCommand("job_execute",attempt)).rejects.toMatchObject({jobAdmission:proof});
    await expect(coreCommand("job_output",attempt)).rejects.toMatchObject({jobAdmission:undefined});
  });
  it.each([{}, {...proof,request_consumed:true}, {...proof,active_execution:true}, {...proof,request_id:"other"}, {...proof,budget:{...attempt.body,words:true}}, {...proof,budget:null}, {...proof,enabled:true}])("does not unlock an incomplete or contradictory refusal %#",async(value)=>{
    expect(jobAdmissionRefusal(value,attempt)).toBeUndefined();
    window.__TAURI__={core:{invoke:vi.fn().mockResolvedValue({status:409,body:value})}};
    await expect(coreCommand("job_execute",attempt)).rejects.toMatchObject({jobAdmission:undefined});
  });
  it("binds recovery to source, kind and exact budget; generic 4xx stays refused",()=>{
    const receipt=jobAdmissionRefusal(proof,attempt)!;
    const error=new ApiError(409,"disabled","unavailable",undefined,receipt);
    expect(recoverableJobRefusal(error,attempt,"source","text")).toBe(true);
    expect(recoverableJobRefusal(error,attempt,"other","text")).toBe(false);
    expect(recoverableJobRefusal(error,attempt,"source","office")).toBe(false);
    expect(recoverableJobRefusal(new ApiError(409,"disabled"),attempt,"source","text")).toBe(false);
    expect(recoverableJobRefusal(new ApiError(502,"lost ACK"),attempt,"source","text")).toBe(false);
  });
});
