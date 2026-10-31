import { describe, expect, it } from "vitest";
import { conversionRecovery } from "../presentation/conversionRecovery";
import { asrModelFailure } from "./fixtures/asrModelFailure";

const identity = {job_id:"job_asr",request_id:"request_asr",attempt:1};
const status = () => ({...identity,input_ref:"source",state:"failed",error:JSON.stringify(asrModelFailure(identity))});

describe("bound conversion component recovery",()=>{
  it("maps the actual missing-model Core error shape without exposing its local path",()=>{
    expect(conversionRecovery(status())).toEqual({reason:"asr_model_missing",title:"缺少语音转写模型",summary:"缺少语音转写模型，本次转写未完成。"});
  });
  it("names incomplete weights separately",()=>{
    expect(conversionRecovery({...status(),error:JSON.stringify(asrModelFailure(identity,"ASR model directory has no model.bin: C:/registered/asr"))})?.reason).toBe("asr_model_incomplete");
  });
  it("supports the bounded source_jobs DTO which omits request_id while binding job and attempt",()=>{
    const {request_id:_,...listing}=status();
    expect(conversionRecovery(listing)?.reason).toBe("asr_model_missing");
  });
  it.each(["schema","type","status","job_id","request_id","attempt"])("rejects a mismatched embedded %s",field=>{
    expect(conversionRecovery({...status(),error:JSON.stringify({...asrModelFailure(identity),[field]:field==="attempt"?2:"unrelated"})})).toBeNull();
  });
  it.each([null,{},[],{...status(),state:"running"},{...status(),state:"succeeded"},{...status(),attempt:0},{...status(),request_id:null},{...status(),error:"ASR model directory not found: C:/unbound"},{...status(),error:"{"}])("leaves unknown or unbound statuses neutral %#",value=>{
    expect(conversionRecovery(value)).toBeNull();
  });
  it.each([{code:"OTHER",message:"ASR model directory not found: C:/x",retryable:false},
    {code:"AAK-WORKER-003",message:"asr_failed",retryable:false},
    {code:"AAK-WORKER-003",message:"No module named other_engine",retryable:false},
    {code:"AAK-WORKER-003",message:"ASR model directory not found: C:/x",retryable:"false"}])("never invents model absence from generic errors %#",error=>{
    expect(conversionRecovery({...status(),error:JSON.stringify({...asrModelFailure(identity),error})})).toBeNull();
  });
});
