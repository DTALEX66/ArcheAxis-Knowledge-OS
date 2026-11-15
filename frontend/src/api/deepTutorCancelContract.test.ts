import { afterEach, expect, it, vi } from "vitest";
import { coreCommand } from "./core";
import { assertCoreDto } from "./generated/core-contract";
vi.mock("../presentation/diagnostics",()=>({beginDiagnosticObservation:vi.fn(),recordDiagnosticFailure:vi.fn()}));
afterEach(()=>{delete window.__TAURI__;});
const body={create_request_id:"cancel_original",material:{document_id:"material",version:1,content_sha256:"a".repeat(64)},requirement:"原目标",model:null};
const receipt={request_id:body.create_request_id,request_sha256:"b".repeat(64),state:"UNKNOWN",result_document_id:null,result_version:null,result_content_sha256:null,
  current_invocation:{worker_invoked:false,model_invoked:false},cancel_requested:true,provider_stop_state:"UNKNOWN"};
it("validates the original cancel request before invoking a finite native operation",async()=>{
  const invoke=vi.fn().mockResolvedValue({status:200,body:receipt});window.__TAURI__={core:{invoke}};
  await expect(coreCommand("learning_deeptutor_question_turn_cancel",{body,endpoint:"https://example.invalid"})).rejects.toMatchObject({status:422});
  expect(invoke).not.toHaveBeenCalled();
  await expect(coreCommand("learning_deeptutor_question_turn_cancel",{body})).resolves.toEqual(receipt);
  expect(invoke).toHaveBeenCalledWith("core_command",{request:{operation:"learning_deeptutor_question_turn_cancel",payload:{body}}});
  invoke.mockResolvedValueOnce({status:200,body:{...receipt,provider_stop_state:"STOPPED"}});
  await expect(coreCommand("learning_deeptutor_question_turn_cancel",{body})).rejects.toMatchObject({status:502,code:"incompatible"});
});
it("accepts the distinct Canvas envelope without inventing a Markdown projection digest",()=>{
  const canvas={document_id:"scene",version:1,format:"canvas",source_revision:"a".repeat(64),files:[
    {path:"document.canvas",media_type:"application/json",content:'{"nodes":[],"edges":[]}'},
    {path:"manifest.json",media_type:"application/json",content:'{}'}]};
  expect(assertCoreDto("DocumentExportDto",canvas)).toEqual(canvas);
  for(const change of [{source_revision:null},{files:[canvas.files[0]]},{files:[{...canvas.files[0],path:"document.md"},canvas.files[1]]},
    {files:[{...canvas.files[0],media_type:"text/html"},canvas.files[1]]}]){
    expect(()=>assertCoreDto("DocumentExportDto",{...canvas,...change})).toThrow("CORE_DTO_INVALID");
  }
});
