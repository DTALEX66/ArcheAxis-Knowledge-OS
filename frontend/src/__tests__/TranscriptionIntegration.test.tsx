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
  render(<JobContent sourceId="source" sourceRevision={revision} name="speech.wav" mediaDurationSeconds={83}/>);const user=userEvent.setup();
  await user.click(screen.getByRole("button",{name:"执行媒体头信息探测"}));await screen.findByText(/转换未完成或产物读取失败/);
  await user.click(screen.getByRole("button",{name:"整体执行"}));
  await waitFor(()=>expect(bridge.call.mock.calls.filter(([op])=>op==="job_enqueue")).toHaveLength(2));
  const jobs=bridge.call.mock.calls.filter(([op])=>op==="job_enqueue");expect(jobs[0][1].body.kind).toBe("media");expect(jobs[1][1].body.kind).toBe("transcribe");
 });

 it("transcribes a long recording in bounded rounds and stops when the receipt says every window is done",async()=>{
  const revision="a".repeat(64);let round=0;const executions:Array<Record<string,unknown>>=[];const jobs:string[]=[];
  bridge.call.mockImplementation(async(op:string,p:any)=>{
   if(op==="source_jobs")return {source_id:"source",jobs:jobs.map(job_id=>({job_id,input_ref:"source",kind:"transcribe",state:"succeeded",attempt:1})),jobs_capped:false};
   if(op==="job_enqueue"){jobs.push(p.body.job_id);return {job_id:p.body.job_id};}
   if(op==="job_execute"){executions.push(p.body);round+=1;return {state:"running"};}
   if(op==="jobs_get")return {job_id:jobs[jobs.length-1],input_ref:"source",attempt:1,state:"succeeded",error:null};
   if(op==="job_output"){
    const content=p.kind==="text"?`第${round}段`:"[]";
    if(p.kind!=="loss_report")return {content};
    // Round 1 covered one of two windows; only round 2 says the recording is whole.
    const windows={status:round<2?"partial":"complete",windows_expected:2,windows_present:round<2?1:2,
     windows_missing:round<2?[1]:[],windows_resumed:round<2?[]:[0]};
    const report=JSON.stringify({params:{worker_output:{duration_ms:2000,cues:[{start_ms:100,end_ms:900,text:`第${round}段`}],windows}}});
    return {content:report,metadata:{kind:"loss_report",sha256:await utf8Sha256(report),byte_length:new TextEncoder().encode(report).length}};
   }
   if(op==="job_quality")return {engine:"faster-whisper"};
   if(op==="source_job_transform")return {source_id:"source",job_id:p.job_id,transform_id:round,content:`第${round}段`};
   return {};
  });
  render(<JobContent sourceId="source" sourceRevision={revision} name="speech.wav" mediaDurationSeconds={720}/>);const user=userEvent.setup();
  await user.click(screen.getByRole("button",{name:/切分执行（6 段/}));
  await screen.findByText(/分段转写已完成/);
  // Two bounded rounds, each a distinct job so a stop costs one round rather than the recording.
  expect(executions).toEqual([{deadline_ms:300000,split:true},{deadline_ms:300000,split:true}]);
  expect(new Set(jobs).size).toBe(2);
  // The partial round says what it did not reach instead of presenting its text as the recording.
  expect(screen.getByText(/分段转写已完成/)).toHaveTextContent("复用了 1 段");
  expect(screen.getByLabelText("Core 提取正文")).toHaveTextContent("第2段");
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
