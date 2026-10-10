import { webcrypto } from "node:crypto";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { JobContent } from "../components/JobContent";
import { ApiError, type JobAdmissionRefusal } from "../api/client";
import { outputReceipt } from "./fixtures/jobContentCoreFixture";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const revision="a".repeat(64);const content="真实夹具正文 😀";
function fixture(options:{lost?:boolean;wrongAck?:boolean;state?:string;kind?:string;windows?:unknown[]}={}) {
 let id="",request="",body:Record<string,unknown>={},state=options.state??"succeeded",sends=0;const kind=options.kind??"office";
 const status=()=>({job_id:id,input_ref:"source",kind,state,attempt:1,request_id:request,error:null,attempts:[{attempt:1,request_id:request,state,budget:body,continuation:{new_attempt_eligible_state:["failed","cancelled"].includes(state)}}]});
 bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>={})=>{
  if(op==="capabilities_list")return {};
  if(op==="source_jobs")return {source_id:"source",jobs:id?[status()]:[],jobs_capped:false};
  if(op==="job_enqueue"){id=String((p.body as Record<string,unknown>).job_id);return {job_id:id,state:"queued"};}
  if(op==="job_execute"){request=String(p.request_id);body=p.body as Record<string,unknown>;sends++;if(options.lost&&sends===1)throw new Error("SIMULATED lost ACK");return {job_id:id,request_id:options.wrongAck?"other":request,state:"running",replayed:sends>1};}
  if(op==="job_execution_status"||op==="jobs_get")return status();
  if(op==="job_execution_cancel")return {job_id:id,request_id:request,cancel_requested:true};
  if(op==="job_output")return outputReceipt(p.kind,p.kind==="text"?content:p.kind==="document_structure"?"[]":JSON.stringify({engine:"SIMULATED",engine_version:"fixture",loss_note:"夹具未独立验证识别质量",params:{worker_output:{duration_ms:300000,cues:[],...(options.windows?{windows:options.windows[Math.min(sends-1,options.windows.length-1)]}:{})}}}));
  if(op==="job_quality")return {job_id:id,engine:"SIMULATED",engine_version:"fixture",loss_count:0};
  if(op==="source_job_transform")return {source_id:"source",job_id:id,raw_sha256:revision,transform_id:1,content};
  if(op==="knowledge_from_transform")throw new Error("SIMULATED lost candidate ACK");
  throw new Error(`Unexpected ${op}`);
 });
 return {setState:(value:string)=>{state=value;},status};
}
const view=(extra:Record<string,unknown>={})=><JobContent sourceId="source" sourceRevision={revision} name="report.xlsx" {...extra}/>;
describe("SIMULATED manual finite execution boundaries",()=>{
 beforeEach(()=>{bridge.call.mockReset();vi.stubGlobal("crypto",webcrypto);});
 it("explicitly resumes the exact unconsumed request after a typed disabled refusal",async()=>{
  fixture();const previous=bridge.call.getMockImplementation()!;let disabled=true;
  bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>)=>{
   if(op==="job_execute"&&disabled){const receipt={schema:"archeaxis.job-admission-refusal/v1",code:"AAK-CAP-001",job_id:p.job_id,request_id:p.request_id,input_ref:"source",kind:"office",capability:"office.structure",budget:p.body,admission_state:"NOT_ADMITTED",request_consumed:false,active_execution:false,enabled:false,same_request_retry_allowed:true} as JobAdmissionRefusal;throw new ApiError(409,"disabled","unavailable",undefined,receipt);}
   return previous(op,p);
  });
  render(view());fireEvent.click(screen.getByRole("button",{name:"执行真实内容转换"}));await screen.findByText(/结果 UNKNOWN/);
  const first=bridge.call.mock.calls.find(([op])=>op==="job_execute")![1];expect(screen.getByRole("button",{name:"同请求重试转换"})).toBeEnabled();
  disabled=false;fireEvent.click(screen.getByRole("button",{name:"同请求重试转换"}));await screen.findByLabelText("Core 提取正文");
  const sends=bridge.call.mock.calls.filter(([op])=>op==="job_execute");expect(sends).toHaveLength(2);expect(sends[1][1]).toEqual(first);expect(bridge.call.mock.calls.filter(([op])=>op==="job_enqueue")).toHaveLength(1);
 });
 it("queued readback cannot unlock a generic permission refusal",async()=>{
  fixture();const previous=bridge.call.getMockImplementation()!;
  bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>)=>{if(op==="job_execute")throw new ApiError(403,"denied");if(op==="job_execution_status")return {job_id:p.job_id,input_ref:"source",kind:"office",state:"queued",attempt:null,request_id:null,error:null,attempts:[]};return previous(op,p);});
  render(view());fireEvent.click(screen.getByRole("button",{name:"执行真实内容转换"}));await screen.findByText(/结果 UNKNOWN/);expect(screen.getByRole("button",{name:"同请求重试转换"})).toBeDisabled();
  fireEvent.click(screen.getByRole("button",{name:"读取冻结转换状态"}));await screen.findByText(/尚未读回冻结执行身份/);expect(screen.getByRole("button",{name:"同请求重试转换"})).toBeDisabled();
 });
 it("claims singleflight before React flush and sends the actual finite request identity",async()=>{
  fixture();render(view());const button=screen.getByRole("button",{name:"执行真实内容转换"});act(()=>{fireEvent.click(button);fireEvent.click(button);});
  await screen.findByLabelText("Core 提取正文");expect(bridge.call.mock.calls.filter(([op])=>op==="job_enqueue")).toHaveLength(1);
  const payload=bridge.call.mock.calls.find(([op])=>op==="job_execute")![1];expect(payload).toMatchObject({job_id:expect.stringMatching(/^read_/),request_id:expect.stringMatching(/^read_run_/),body:{deadline_ms:60000,split:false,words:false}});
 });
 it("lost execute ACK freezes all identity, same retry replays and does not enqueue a new job",async()=>{
  fixture({lost:true});render(view());fireEvent.click(screen.getByRole("button",{name:"执行真实内容转换"}));await screen.findByText(/结果 UNKNOWN/);
  expect(screen.getByRole("button",{name:"执行真实内容转换"})).toBeDisabled();fireEvent.click(screen.getByRole("button",{name:"同请求重试转换"}));await screen.findByLabelText("Core 提取正文");
  const calls=bridge.call.mock.calls.filter(([op])=>op==="job_execute");expect(calls).toHaveLength(2);expect(calls[0][1]).toEqual(calls[1][1]);expect(bridge.call.mock.calls.filter(([op])=>op==="job_enqueue")).toHaveLength(1);
 });
 it("UNKNOWN reconciles without resending execution",async()=>{
  fixture({lost:true});render(view());fireEvent.click(screen.getByRole("button",{name:"执行真实内容转换"}));await screen.findByText(/结果 UNKNOWN/);fireEvent.click(screen.getByRole("button",{name:"读取冻结转换状态"}));await screen.findByLabelText("Core 提取正文");expect(bridge.call.mock.calls.filter(([op])=>op==="job_execute")).toHaveLength(1);
 });
 it("wrong ACK cannot settle a request or publish output",async()=>{
  fixture({wrongAck:true});render(view());fireEvent.click(screen.getByRole("button",{name:"执行真实内容转换"}));await screen.findByText(/结果 UNKNOWN/);expect(screen.queryByLabelText("Core 提取正文")).toBeNull();expect(bridge.call.mock.calls.some(([op])=>op==="job_output")).toBe(false);
 });
 it.each(["source","request","kind","budget"])("wrong %s readback cannot settle the frozen request",async(field)=>{
  fixture();const previous=bridge.call.getMockImplementation()!;bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>)=>{const result=await previous(op,p);if(op!=="job_execution_status")return result;if(field==="budget")return {...result,attempts:[{...result.attempts[0],budget:{...result.attempts[0].budget,deadline_ms:1}}]};return {...result,...(field==="source"?{input_ref:"other"}:field==="request"?{request_id:"other"}:{kind:"text"})};});render(view());fireEvent.click(screen.getByRole("button",{name:"执行真实内容转换"}));await screen.findByText(/结果 UNKNOWN/);expect(screen.queryByLabelText("Core 提取正文")).toBeNull();expect(bridge.call.mock.calls.some(([op])=>op==="job_output")).toBe(false);
 });
 it("cancel 202 is pending and actual success wins the cancellation race",async()=>{
  const f=fixture({state:"running"});render(view());fireEvent.click(screen.getByRole("button",{name:"执行真实内容转换"}));await waitFor(()=>expect(bridge.call.mock.calls.some(([op])=>op==="job_execution_status")).toBe(true));
  fireEvent.click(screen.getByRole("button",{name:"请求取消当前转换"}));await screen.findByText(/202 不等于已取消/);expect(screen.queryByLabelText("Core 提取正文")).toBeNull();
  const execution=bridge.call.mock.calls.find(([op])=>op==="job_execute")![1];expect(bridge.call).toHaveBeenCalledWith("job_execution_cancel",{job_id:execution.job_id,request_id:execution.request_id});f.setState("succeeded");await screen.findByLabelText("Core 提取正文");
 });
 it("split success without a window record never creates the next job",async()=>{
  fixture({kind:"transcribe"});render(view({name:"recording.wav",mediaDurationSeconds:300}));fireEvent.click(screen.getByRole("button",{name:/切分执行/}));await screen.findByText(/分段记录未提供/);expect(bridge.call.mock.calls.filter(([op])=>op==="job_enqueue")).toHaveLength(1);expect(screen.getByRole("button",{name:/切分执行/})).toBeDisabled();
 });
 it("split valid partial windows proceed to a new bounded round and reuse completion evidence",async()=>{
  fixture({kind:"transcribe",windows:[{status:"partial",windows_expected:2,windows_present:1,windows_missing:[1],windows_resumed:[]},{status:"complete",windows_expected:2,windows_present:2,windows_missing:[],windows_resumed:[0]}]});render(view({name:"recording.wav",mediaDurationSeconds:300}));fireEvent.click(screen.getByRole("button",{name:/切分执行/}));await screen.findByText(/分段转写已完成/);const calls=bridge.call.mock.calls.filter(([op])=>op==="job_execute");expect(calls).toHaveLength(2);expect(calls[0][1].request_id).not.toBe(calls[1][1].request_id);for(const [,request] of calls)expect(request.body).toEqual({deadline_ms:300000,split:true,words:false});expect(screen.getAllByText(/本次复用了 1 段/).length).toBeGreaterThan(0);
 });
 it("candidate text and UNKNOWN candidate write stay dirty and retain their input",async()=>{
  fixture();const dirty=vi.fn();render(view({onDirtyChange:dirty}));fireEvent.click(screen.getByRole("button",{name:"执行真实内容转换"}));await screen.findByLabelText("Core 提取正文");
  fireEvent.select(screen.getByLabelText("选择实际引文"),{target:{selectionStart:0,selectionEnd:2}});fireEvent.change(screen.getByLabelText("知识候选正文"),{target:{value:"独立人类草稿"}});expect(dirty).toHaveBeenLastCalledWith(true);
  fireEvent.click(screen.getByRole("button",{name:"创建知识候选"}));await screen.findByText(/知识候选创建未确认/);expect(screen.getByLabelText("知识候选正文")).toHaveValue("独立人类草稿");expect(dirty).toHaveBeenLastCalledWith(true);
 });
 it("old execute ACK cannot overwrite another source or publish after unmount",async()=>{
  fixture();const previous=bridge.call.getMockImplementation()!;let resolve!:(v:unknown)=>void;
  bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>)=>op==="job_execute"?new Promise(r=>{resolve=r;}):previous(op,p));const rendered=render(view());fireEvent.click(screen.getByRole("button",{name:"执行真实内容转换"}));await waitFor(()=>expect(resolve).toBeDefined());rendered.unmount();await act(async()=>resolve({job_id:"wrong",request_id:"wrong",state:"succeeded",replayed:false}));expect(bridge.call.mock.calls.some(([op])=>op==="job_output")).toBe(false);
 });
});
