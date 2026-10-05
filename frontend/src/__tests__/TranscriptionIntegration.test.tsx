// Mock bridge receipts verify UI binding, not ASR execution or human accuracy.
import { beforeEach,describe,expect,it,vi } from "vitest";
import { render,screen,waitFor,within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { JobContent } from "../components/JobContent";
import { TranscriptionCues,utf8Sha256 } from "../components/TranscriptionCues";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const revision="a".repeat(64);
describe("mock transcription UI integration",()=>{
 beforeEach(()=>bridge.call.mockReset());
 it("keeps header probing separate from transcription",async()=>{
  bridge.call.mockImplementation(async(op:string,p:any)=>op==="job_enqueue"?{job_id:p.body.job_id}:op==="jobs_get"?{state:"failed"}:{});
  render(<JobContent sourceId="source" sourceRevision={revision} name="speech.wav"/>);const user=userEvent.setup();
  await user.click(screen.getByRole("button",{name:"执行媒体头信息探测"}));await screen.findByText(/转换未完成或产物读取失败/);
  await user.click(screen.getByRole("button",{name:"执行真实语音转写"}));
  await waitFor(()=>expect(bridge.call.mock.calls.filter(([op])=>op==="job_enqueue")).toHaveLength(2));
  const jobs=bridge.call.mock.calls.filter(([op])=>op==="job_enqueue");expect(jobs[0][1].body.kind).toBe("media");expect(jobs[1][1].body.kind).toBe("transcribe");
 });
 it("retains successful cues after failure and cites their original receipt",async()=>{
  const content=JSON.stringify({params:{worker_output:{duration_ms:2000,cues:[{start_ms:100,end_ms:900,text:"数值37"}]}}});const sha=await utf8Sha256(content);
  let job="";let successful="";let executions=0;
  bridge.call.mockImplementation(async(op:string,p:any)=>{
   if(op==="job_enqueue"){job=p.body.job_id;return {job_id:job};}
   if(op==="job_execute"){executions++;if(executions===1)successful=job;return {};}
   if(op==="source_jobs")return {source_id:"source",jobs:job?[{job_id:job,input_ref:"source",kind:"transcribe",state:"succeeded",attempt:3}]:[]};
   if(op==="jobs_get")return {job_id:job,input_ref:"source",attempt:3,state:executions===1?"succeeded":"failed",error:executions===1?null:"AAK-WORKER-003"};
   if(op==="job_output")return p.kind==="text"?{content:"数值37"}:p.kind==="document_structure"?{content:"[]"}:{content,metadata:{kind:"loss_report",sha256:sha,byte_length:new TextEncoder().encode(content).length}};
   if(op==="source_job_transform")return {source_id:"source",job_id:job,transform_id:1,content:"数值37"};
   if(op==="anchor_create")return {anchor_id:"anchor",source_id:p.source_id,source_revision:p.body.revision,position:JSON.stringify({...JSON.parse(p.body.position),checksum:p.body.checksum}),location_status:"located"};
   return {};
  });
  render(<JobContent sourceId="source" sourceRevision={revision} name="speech.wav"/>);const user=userEvent.setup();
  await user.click(screen.getByRole("button",{name:"执行真实语音转写"}));await screen.findByRole("button",{name:"引用时间段"});
  await user.click(screen.getByRole("button",{name:"执行真实语音转写"}));await screen.findByText(/转换未完成或产物读取失败/);
  await user.click(screen.getByRole("button",{name:"引用时间段"}));await screen.findByText(/识别忠实度仍需独立核验/);
  const call=bridge.call.mock.calls.find(([op])=>op==="anchor_create")!;const position=JSON.parse(call[1].body.position);
  expect(job).not.toBe(successful);expect(position).toEqual({type:"time",job_id:successful,attempt:3,cue_index:0,start_ms:100,end_ms:900,result_sha256:sha});expect(call[1].body.checksum).toBe(await utf8Sha256("数值37"));
 });
 it("preserves the global cue index across pagination and rejects wrong anchor source",async()=>{
  const cues=Array.from({length:31},(_,i)=>({start_ms:i*100,end_ms:i*100+50,text:`cue ${i}`}));
  bridge.call.mockResolvedValue({anchor_id:"wrong",source_id:"other",source_revision:revision,position:"{}",location_status:"located"});
  render(<TranscriptionCues proof={{sourceId:"source",revision,jobId:"original-job",attempt:1,resultSha256:"b".repeat(64),durationMs:4000,cues}}/>);const user=userEvent.setup();
  await user.click(screen.getByRole("button",{name:/下一/}));const row=screen.getByRole("cell",{name:"cue 30"}).closest("tr")!;
  await user.click(within(row).getByRole("button",{name:"引用时间段"}));await screen.findByText(/时间引用未确认/);
  expect(JSON.parse(bridge.call.mock.calls[0][1].body.position).cue_index).toBe(30);expect(screen.queryByText(/关联已校验/)).not.toBeInTheDocument();
 });
});
