import { webcrypto } from "node:crypto";
import { beforeEach,describe,expect,it,vi } from "vitest";
import { freezeManualAttempt,pinnedSuccess,verifiedJobOutput,verifiedSplitProgress } from "../presentation/jobContentExecution";
import { outputReceipt } from "./fixtures/jobContentCoreFixture";
describe("SIMULATED manual result integrity",()=>{
 beforeEach(()=>vi.stubGlobal("crypto",webcrypto));
 it("requires actual source hash and freezes distinct request IDs with route budgets",()=>{expect(()=>freezeManualAttempt("s",undefined,"office","i",false)).toThrow();const one=freezeManualAttempt("s","a".repeat(64),"office","i",false),two=freezeManualAttempt("s","a".repeat(64),"transcribe","i",true);expect(one.body.deadline_ms).toBe(60000);expect(two.body).toEqual({deadline_ms:300000,split:true,words:false});expect(one.request_id).not.toBe(two.request_id);expect(Object.isFrozen(two.body)).toBe(true);});
 it.each(["text","document_structure","loss_report"] as const)("checks exact UTF8 bytes and digest of %s rather than JSON reserialization",async(kind)=>{const good=outputReceipt(kind," 中文😀 1.0\n");await expect(verifiedJobOutput(good,kind)).resolves.toEqual(good);for(const delta of [{kind:"wrong"},{sha256:"b".repeat(64)},{byte_length:good.metadata.byte_length+1}])await expect(verifiedJobOutput({...good,metadata:{...good.metadata,...delta}},kind)).rejects.toThrow();await expect(verifiedJobOutput({content:good.content},kind)).rejects.toThrow();});
 it.each([undefined,null,"",0])("requires a nonempty actual request identity for pinned success %j",request_id=>{expect(()=>pinnedSuccess({job_id:"j",input_ref:"s",state:"succeeded",attempt:1,request_id},"j","s")).toThrow();});
 it("does not call missing/unknown/inconsistent window evidence complete or ready for next round",()=>{
  const loss=(windows:unknown)=>({params:{worker_output:{windows}}});expect(verifiedSplitProgress({})).toBeNull();
  expect(verifiedSplitProgress(loss({status:"unknown",windows_expected:2,windows_present:1,windows_missing:[1]}))).toBeNull();
  expect(verifiedSplitProgress(loss({status:"complete",windows_expected:2,windows_present:1,windows_missing:[1]}))).toBeNull();
  expect(verifiedSplitProgress(loss({status:"partial",windows_expected:2,windows_present:1,windows_missing:[1],windows_resumed:[]}))).toMatchObject({status:"partial"});
  expect(verifiedSplitProgress(loss({status:"complete",windows_expected:2,windows_present:2,windows_missing:[],windows_resumed:[0]}))).toMatchObject({status:"complete"});
 });
});
