import { webcrypto } from "node:crypto";
import { outputReceipt } from "./fixtures/jobContentCoreFixture";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import { JobContent } from "../components/JobContent";

const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const revision="a".repeat(64);
const status=(id:string)=>({job_id:id,input_ref:"source",kind:"office",state:"succeeded",attempt:2,request_id:`request-${id}`});
function mockRead(overrides:Record<string,unknown>={}) {
 bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>={})=>{
  const id=String(p.job_id);
  if(op==="capabilities_list")return {};
  if(op==="job_execution_status")return {...status(id),...overrides};
  if(op==="jobs_get")return status(id);
  if(op==="job_output")return outputReceipt(p.kind,p.kind==="text"?`保存正文 ${id}`:"[]");
  if(op==="job_quality")return {job_id:id,engine:"openpyxl"};
  if(op==="source_job_transform")return {source_id:"source",job_id:id,raw_sha256:revision,transform_id:7,content:`保存正文 ${id}`};
  throw new Error(`unexpected operation ${op}`);
 });
}
const view=(id:string)=><JobContent sourceId="source" sourceRevision={revision} name="report.xlsx" pinnedJobId={id}/>;
describe("SIMULATED exact batch result readback",()=>{
 beforeEach(()=>{bridge.call.mockReset();vi.stubGlobal("crypto",webcrypto);});
 it("reads an old explicit job independently of the recent 50 and never executes",async()=>{
  mockRead();render(view("older-than-50"));
  expect(await screen.findByLabelText("Core 提取正文")).toHaveTextContent("保存正文 older-than-50");
  expect(bridge.call).toHaveBeenCalledWith("job_execution_status",{job_id:"older-than-50"});
  expect(bridge.call.mock.calls.some(([op])=>["source_jobs","job_enqueue","job_execute"].includes(op))).toBe(false);
 });
 it.each([{job_id:"other"},{input_ref:"other"},{attempt:3},{request_id:"other"}])("refuses mismatched pinned identity %j",async(overrides)=>{
  mockRead(overrides);render(view("pinned"));
  await screen.findByText("持久化结果读回未完成；不会自动重新执行任务。");
  expect(screen.queryByLabelText("Core 提取正文")).toBeNull();
  expect(bridge.call.mock.calls.some(([op])=>op==="job_execute")).toBe(false);
 });
 it("keeps an explicitly failed job without falling back to another success",async()=>{
  mockRead({state:"failed"});render(view("failed"));
  await screen.findByText(/最近一次转换任务状态为 failed/);
  expect(bridge.call.mock.calls.some(([op])=>["source_jobs","job_output","job_execute"].includes(op))).toBe(false);
 });
 it("rejects a result bound to another original digest",async()=>{
  mockRead();const previous=bridge.call.getMockImplementation()!;
  bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>)=>op==="source_job_transform"?{...await previous(op,p),raw_sha256:"b".repeat(64)}:previous(op,p));
  render(view("pinned"));await screen.findByText(/持久化结果读回未完成/);
  expect(screen.queryByLabelText("Core 提取正文")).toBeNull();
 });
 it("ignores late output from the prior pinned job on the same source",async()=>{
  mockRead();const previous=bridge.call.getMockImplementation()!;
  let resolveOld!:(value:unknown)=>void;
  bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>)=>op==="job_output"&&p.job_id==="old"&&p.kind==="text"?new Promise(resolve=>{resolveOld=resolve;}):previous(op,p));
  const rendered=render(view("old"));
  await vi.waitFor(()=>expect(resolveOld).toBeDefined());
  rendered.rerender(view("new"));
  expect(await screen.findByLabelText("Core 提取正文")).toHaveTextContent("保存正文 new");
  await act(async()=>resolveOld(outputReceipt("text","保存正文 old")));
  expect(screen.getByLabelText("Core 提取正文")).toHaveTextContent("保存正文 new");
 });
 it.each([null,undefined,""])("rejects empty matching pinned request identity %j",async(request_id)=>{
  mockRead({request_id});const previous=bridge.call.getMockImplementation()!;bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>)=>op==="jobs_get"?{...await previous(op,p),request_id}:previous(op,p));render(view("pinned"));await screen.findByText(/持久化结果读回未完成/);expect(screen.queryByLabelText("Core 提取正文")).toBeNull();
 });
 it.each(["text","document_structure","loss_report"])("refuses corrupt %s output metadata",async(kind)=>{
  mockRead();const previous=bridge.call.getMockImplementation()!;bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>)=>{const result=await previous(op,p);return op==="job_output"&&p.kind===kind?{...result,metadata:{...result.metadata,sha256:"f".repeat(64)}}:result;});render(view("pinned"));await screen.findByText(/持久化结果读回未完成/);expect(screen.queryByLabelText("Core 提取正文")).toBeNull();
 });

});
