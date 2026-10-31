import {expect,it} from "vitest";
import {materialModelFailureMessage,readMachineFailureDiagnostics} from "../api/machineFailure";

it("explains only a known material final-answer failure and never copies arbitrary diagnostics",()=>{
 const length=materialModelFailureMessage("material_no_final_answer",{finish_reason:"length",reasoning_content:"PRIVATE",max_tokens:2048});
 expect(length).toContain("输出上限");expect(length).not.toContain("PRIVATE");
 for(const diagnostics of [null,[],"PRIVATE",{finish_reason:"stop"},{finish_reason:"PRIVATE"}]) {
  const message=materialModelFailureMessage("material_no_final_answer",diagnostics);
  expect(message).toContain("模型未返回最终回答");expect(message).not.toContain("输出上限");expect(message).not.toContain("PRIVATE");
 }
 expect(materialModelFailureMessage("material_model_timeout")).toContain("模型调用超时");
 expect(materialModelFailureMessage("UNKNOWN",{finish_reason:"length"})).toBeUndefined();
});

it("rejects invalid or private measurement values without fabricating unknown fields",()=>{
  expect(readMachineFailureDiagnostics({requested_model:"bad\\model",observed_model:null,finish_reason:"PRIVATE",max_tokens:true,timeout_s:-1,elapsed_s:Infinity,http_status:600,usage:{input_tokens:0,output_tokens:-1,total_tokens:Number.MAX_SAFE_INTEGER+1,raw:"PRIVATE"},stderr:"PRIVATE"})).toEqual({observed_model:null,usage:{input_tokens:0}});
  for(const raw of [null,[],"PRIVATE",{}, {elapsed_s:NaN},{requested_model:"x".repeat(257)}])expect(readMachineFailureDiagnostics(raw)).toBeUndefined();
  expect(readMachineFailureDiagnostics({requested_model:"aaos-deep-27b-mtp",elapsed_s:0,http_status:503,error_type:"HTTPError"})).toEqual({requested_model:"aaos-deep-27b-mtp",elapsed_s:0,http_status:503,error_type:"HTTPError"});
});

it("retains finite timeout stages and discovery measurements only",()=>{
  for(const request_stage of ["service_discovery","model_request","response_deadline","worker_deadline"])
    expect(readMachineFailureDiagnostics({request_stage,discovery_elapsed_s:0.25,stderr:"PRIVATE"})).toEqual({request_stage,discovery_elapsed_s:0.25});
  for(const raw of [{request_stage:"PRIVATE"},{discovery_elapsed_s:-1},{discovery_elapsed_s:true},{discovery_elapsed_s:Infinity}])
    expect(readMachineFailureDiagnostics(raw)).toBeUndefined();
});

it("retains bounded HTTP phase timings and byte counts without pretending TTFT or server stop",()=>{
  for(const request_phase of ["http_open","body_read","json_parse","response_validation"])
    expect(readMachineFailureDiagnostics({request_stage:"model_request",request_phase,http_open_elapsed_s:0.25,body_read_elapsed_s:0,json_parse_elapsed_s:1,prompt_utf8_bytes:0,serialized_request_bytes:753,response_bytes:4194305,prompt:"PRIVATE",headers:{secret:"PRIVATE"},ttft_s:0,provider_stop_state:"STOPPED"})).toEqual({request_stage:"model_request",request_phase,http_open_elapsed_s:0.25,body_read_elapsed_s:0,json_parse_elapsed_s:1,prompt_utf8_bytes:0,serialized_request_bytes:753,response_bytes:4194305});
  for(const key of ["prompt_utf8_bytes","serialized_request_bytes","response_bytes"])
    for(const value of [true,-1,1.5,Number.MAX_SAFE_INTEGER+1,"PRIVATE"])
      expect(readMachineFailureDiagnostics({[key]:value})).toBeUndefined();
  for(const key of ["http_open_elapsed_s","body_read_elapsed_s","json_parse_elapsed_s"])
    for(const value of [true,-1,NaN,Infinity,Number.MAX_SAFE_INTEGER+1,"PRIVATE"])
      expect(readMachineFailureDiagnostics({[key]:value})).toBeUndefined();
  expect(readMachineFailureDiagnostics({request_phase:"PRIVATE"})).toBeUndefined();
});
