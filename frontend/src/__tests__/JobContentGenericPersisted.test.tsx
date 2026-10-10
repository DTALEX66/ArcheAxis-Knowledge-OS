import { webcrypto } from "node:crypto";
import { beforeEach,describe,expect,it,vi } from "vitest";
import { render,screen } from "@testing-library/react";
import { JobContent } from "../components/JobContent";
import { jobContentCoreFixture,outputReceipt } from "./fixtures/jobContentCoreFixture";
import { verifiedJobOutput } from "../presentation/jobContentExecution";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const revision="a".repeat(64);const state={job_id:"saved",input_ref:"source",state:"succeeded",attempt:2,request_id:"saved-request",error:null};
function fixture(change:{state?:Record<string,unknown>;saved?:Record<string,unknown>;listed?:Record<string,unknown>}={}){
 bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>={})=>{
  if(op==="capabilities_list")return {};
  // Real source_jobs projection does not carry request_id. Keep the fixture honest.
  if(op==="source_jobs")return {source_id:"source",jobs:[{job_id:"saved",input_ref:"source",kind:"office",state:"succeeded",attempt:2,...change.listed}],jobs_capped:false};
  if(op==="jobs_get")return {...state,...change.state};
  if(op==="job_output")return outputReceipt(p.kind,p.kind==="text"?"旧版本😀原产物":p.kind==="document_structure"?"[]":"{}");
  if(op==="job_quality")return {job_id:"saved",engine:"SIMULATED",engine_version:"fixture"};
  if(op==="source_job_transform")return {source_id:"source",job_id:"saved",transform_id:2,raw_sha256:revision,content:"旧版本😀原产物",...change.saved};
  throw new Error(`Unexpected operation ${op}`);
 });
}
const view=()=>render(<JobContent sourceId="source" sourceRevision={revision} name="report.xlsx" readOnly/>);
describe("SIMULATED generic persisted source-and-attempt binding",()=>{
 beforeEach(()=>{bridge.call.mockReset();vi.stubGlobal("crypto",webcrypto);});
 it("reopens valid office without executing and enables only verified saved downloads",async()=>{
  fixture();view();expect(await screen.findByLabelText("Core 提取正文")).toHaveTextContent("旧版本😀原产物");expect(screen.getByRole("button",{name:"下载派生正文.txt"})).toBeInTheDocument();expect(bridge.call.mock.calls.some(([op])=>["job_enqueue","job_execute"].includes(op))).toBe(false);
 });
 it.each([{job_id:"other"},{input_ref:"other"},{state:"failed"},{attempt:0},{attempt:1},{attempt:null},{request_id:null},{request_id:""}])("rejects mismatched generic status %j",async(change)=>{
  fixture({state:change});view();await screen.findByText(/持久化结果读回未完成/);expect(screen.queryByLabelText("Core 提取正文")).toBeNull();expect(screen.queryByRole("button",{name:/下载派生正文/})).toBeNull();expect(bridge.call.mock.calls.some(([op])=>op==="job_execute")).toBe(false);
 });
 it.each([{raw_sha256:"b".repeat(64)},{raw_sha256:undefined},{transform_id:0},{transform_id:1.5},{transform_id:Number.NaN},{content:"another version"}])("rejects original revision or transform corruption %j",async(change)=>{
  fixture({saved:change});view();await screen.findByText(/持久化结果读回未完成/);expect(screen.queryByLabelText("Core 提取正文")).toBeNull();expect(screen.queryByRole("button",{name:/下载派生正文/})).toBeNull();
 });
 it.each([undefined,null,0])("requires real source-list attempt rather than inventing a download pin %j",async(attempt)=>{
  fixture({listed:{attempt}});view();await screen.findByText(/持久化结果读回未完成/);expect(screen.queryByLabelText("Core 提取正文")).toBeNull();
 });
 it("legacy fixture upgrade preserves existing wrong metadata so digest negative tests remain effective",async()=>{
  const adapter=jobContentCoreFixture(async()=>({content:"unchanged",metadata:{kind:"text",sha256:"f".repeat(64),byte_length:9}}));const dto=await adapter("job_output",{kind:"text"});await expect(verifiedJobOutput(dto,"text")).rejects.toThrow();
 });
});
