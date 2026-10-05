// Mock persisted receipts test reopen behavior; no ASR runtime claim.
import {beforeEach,describe,it,expect,vi} from "vitest";
import {render,screen,waitFor} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {JobContent} from "../components/JobContent";
import {utf8Sha256} from "../components/TranscriptionCues";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const revision="a".repeat(64);
async function fixture(listing?:unknown){
 const content=JSON.stringify({params:{worker_output:{duration_ms:1000,cues:[{start_ms:0,end_ms:900,text:"persisted cue"}]}}});const hash=await utf8Sha256(content);
 bridge.call.mockImplementation(async(op:string,p:any)=>{
  if(op==="source_jobs")return listing??{source_id:"s",jobs_capped:false,jobs:[{job_id:"new-failed",kind:"transcribe",state:"failed",input_ref:"s",error:"AAK-WORKER-003"},{job_id:"saved-job",kind:"transcribe",state:"succeeded",input_ref:"s",attempt:1}]};
  if(op==="jobs_get")return {job_id:p.job_id,input_ref:"s",attempt:1,state:p.job_id==="saved-job"?"succeeded":"failed"};
  if(op==="job_output")return p.kind==="text"?{content:"persisted cue"}:p.kind==="document_structure"?{content:"[]"}:{content,metadata:{kind:"loss_report",sha256:hash,byte_length:content.length}};
  if(op==="source_job_transform")return {source_id:"s",job_id:p.job_id,transform_id:1,content:"persisted cue"};
  if(op==="job_enqueue")return {job_id:p.body.job_id};return {};
 });
}
describe("persisted mock transcription reopen",()=>{
 beforeEach(()=>bridge.call.mockReset());
 it("loads old success while retaining latest failure, without new execution",async()=>{
  await fixture();render(<JobContent sourceId="s" sourceRevision={revision} name="speech.wav"/>);
  await screen.findByRole("button",{name:"引用时间段"});expect(screen.getByText(/AAK-WORKER-003/)).toBeInTheDocument();
  expect(bridge.call.mock.calls.some(([op])=>op==="job_execute"||op==="job_enqueue")).toBe(false);
 });
 it("refuses an unbounded list rather than following pages implicitly",async()=>{
  await fixture({source_id:"s",jobs:Array.from({length:51},()=>({input_ref:"s",kind:"transcribe",state:"succeeded",job_id:"saved-job"}))});
  render(<JobContent sourceId="s" sourceRevision={revision} name="speech.wav"/>);await screen.findByText(/持久化转写读回未完成/);
  expect(bridge.call.mock.calls.filter(([op])=>op==="source_jobs")).toHaveLength(1);expect(screen.queryByRole("button",{name:"引用时间段"})).not.toBeInTheDocument();
 });
 it("does not let old reopen readback overwrite a newer execution",async()=>{
  await fixture();const normal=bridge.call.getMockImplementation()!;let release:(value:unknown)=>void=()=>{};
  bridge.call.mockImplementation((op:string,p:any)=>op==="source_jobs"?new Promise(resolve=>{release=resolve;}):normal(op,p));
  render(<JobContent sourceId="s" sourceRevision={revision} name="speech.wav"/>);await userEvent.setup().click(screen.getByRole("button",{name:"执行真实语音转写"}));
  await screen.findByText(/转换未完成或产物读取失败/);release({source_id:"s",jobs:[{job_id:"saved-job",kind:"transcribe",state:"succeeded",input_ref:"s",attempt:1}]});
  await waitFor(()=>expect(bridge.call.mock.calls.some(([op,p])=>op==="jobs_get"&&p.job_id==="saved-job")).toBe(true));
  expect(screen.queryByRole("button",{name:"引用时间段"})).not.toBeInTheDocument();
 });
});
