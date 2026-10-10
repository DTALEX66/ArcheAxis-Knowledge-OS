import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { webcrypto } from "node:crypto";
import { coreCommand } from "../api/core";
import { machineAdmissionRequestSha, readMachineAdmissionRefusal } from "../api/machineAdmission";

const request={knowledge_id:"k",question:"私密问题",client_request_id:"client",context_grant:{document_id:"g",version:1,content_sha256:"a".repeat(64),purpose:"私密用途"}};
async function receipt(operation:"answer"|"retest"="answer",body:Record<string,unknown>=request) {
  return {schema:"archeaxis.context-admission-refusal/v1",reason_code:"RESTORED_GRANT_FENCED",execution_state:"NOT_EXECUTED",execution_scope:"CURRENT_INVOCATION",prior_request_execution:"UNVERIFIED",answer_published:false,
    operation,knowledge_id:body.knowledge_id,client_request_id:operation==="answer"?body.client_request_id:null,retest_of:operation==="retest"?body.retest_of:null,
    request_sha256:await machineAdmissionRequestSha(operation,body),grant:{document_id:"g",version:1,content_sha256:"a".repeat(64)}};
}
describe("SIMULATED finite bridge restored authorization admission receipt",()=>{
  beforeEach(()=>vi.stubGlobal("crypto",webcrypto));
  afterEach(()=>{delete window.__TAURI__;vi.unstubAllGlobals();});
  it("binds the whole normalized frozen request and exposes only redacted receipt fields",async()=>{
    const proof=await receipt();
    window.__TAURI__={core:{invoke:vi.fn().mockResolvedValue({status:403,body:{...proof,question:"must not leak"}})}};
    await expect(coreCommand("machine_answer",{body:request})).rejects.toMatchObject({status:403,machineAdmission:proof});
    const parsed=await readMachineAdmissionRefusal({...proof,question:"must not leak"},"answer",request);
    expect(parsed).toEqual(proof);expect(JSON.stringify(parsed)).not.toMatch(/私密|must not leak/);
    expect(await machineAdmissionRequestSha("answer",{...request,max_tokens:2048,timeout_s:120})).toEqual(proof.request_sha256);
  });
  it.each(["reason_code","execution_state","execution_scope","prior_request_execution","knowledge_id","client_request_id","request_sha256","grant"])("refuses mismatched %s without upgrading UNKNOWN",async(key)=>{
    const proof=await receipt();const invalid={...proof,[key]:key==="grant"?{...proof.grant,version:2}:"wrong"};
    window.__TAURI__={core:{invoke:vi.fn().mockResolvedValue({status:403,body:invalid})}};
    await expect(coreCommand("machine_answer",{body:request})).rejects.toMatchObject({status:502,code:"incompatible",machineAdmission:undefined});
  });
  it("rejects changed purpose, question, budget, assets, extra fields and the wrong operation",async()=>{
    const proof=await receipt();
    for(const body of [{...request,question:"other"},{...request,max_tokens:1},{...request,context_grant:{...request.context_grant,purpose:"other"}},
      {...request,asset_context_grant:{document_id:"asset"}},{...request,unexpected:true}]) {
      expect(await readMachineAdmissionRefusal(proof,"answer",body)).toBeUndefined();
    }
    expect(await readMachineAdmissionRefusal(proof,"retest",request)).toBeUndefined();
  });
  it("supports a separately bound retest and preserves generic403 and executed-but-withheld semantics",async()=>{
    const body={knowledge_id:"k",question:"question",retest_of:"failed",context_grant:request.context_grant};const proof=await receipt("retest",body);
    window.__TAURI__={core:{invoke:vi.fn().mockResolvedValue({status:403,body:proof})}};
    await expect(coreCommand("machine_retest",{body})).rejects.toMatchObject({machineAdmission:proof});
    window.__TAURI__.core!.invoke=vi.fn().mockResolvedValue({status:403,body:{message:"generic refusal"}});
    await expect(coreCommand("machine_answer",{body:request})).rejects.toMatchObject({status:403,machineAdmission:undefined});
    window.__TAURI__.core!.invoke=vi.fn().mockResolvedValue({status:403,body:{schema:"archeaxis.machine-execution-refusal/v1",execution_state:"EXECUTED_BUT_WITHHELD",answer_published:false,audit_status:"RECORDED",audit_task_id:`withheld_${"b".repeat(64)}`}});
    await expect(coreCommand("machine_answer",{body:request})).rejects.toMatchObject({execution:{execution_state:"EXECUTED_BUT_WITHHELD"},machineAdmission:undefined});
  });
});
