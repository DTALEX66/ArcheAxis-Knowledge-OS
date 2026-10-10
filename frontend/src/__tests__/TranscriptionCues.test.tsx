import { describe,it,expect,vi,beforeEach } from "vitest";
import { render,screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TranscriptionCues,transcriptionProof,utf8Sha256 } from "../components/TranscriptionCues";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const proof={sourceId:"s",revision:"a".repeat(64),jobId:"successful-job",attempt:2,resultSha256:"b".repeat(64),durationMs:2000,cues:[{start_ms:100,end_ms:1000,text:"数值37"}]};
async function anchor(status:string) {return {anchor_id:"a",source_id:"s",source_revision:proof.revision,location_status:status,position:JSON.stringify({type:"time",job_id:proof.jobId,attempt:proof.attempt,cue_index:0,start_ms:100,end_ms:1000,result_sha256:proof.resultSha256,checksum:await utf8Sha256("数值37")})};}
describe("receipt-bound transcription cues",()=>{
 beforeEach(()=>{bridge.call.mockReset();});
 it("binds original successful job and UTF8 cue checksum without autoplay",async()=>{
  bridge.call.mockResolvedValue(await anchor("located"));const seek=vi.fn();render(<TranscriptionCues proof={proof} onTimeSeek={seek}/>);
  expect(seek).not.toHaveBeenCalled();await userEvent.setup().click(screen.getByRole("button",{name:"引用时间段"}));
  await screen.findByText(/识别忠实度仍需独立核验/);
  expect(bridge.call).toHaveBeenCalledWith("anchor_create",{source_id:"s",body:{revision:proof.revision,position:JSON.stringify({type:"time",job_id:"successful-job",attempt:2,cue_index:0,start_ms:100,end_ms:1000,result_sha256:proof.resultSha256}),checksum:await utf8Sha256("数值37")}});
 });
 it("does not infer silence from no verified cue and never offers an anchor",()=>{render(<TranscriptionCues proof={{...proof,cues:[]}}/>);expect(screen.getByText(/没有通过时间范围校验的语音片段/)).toBeInTheDocument();expect(screen.queryByRole("button",{name:"引用时间段"})).not.toBeInTheDocument();});
 it("does not convert API refusal into located",async()=>{bridge.call.mockRejectedValue(new Error("400"));render(<TranscriptionCues proof={proof}/>);await userEvent.setup().click(screen.getByRole("button",{name:"引用时间段"}));await screen.findByText(/时间引用未确认/);expect(screen.queryByText(/关联已校验/)).not.toBeInTheDocument();});
 it("displays unverified explicitly",async()=>{bridge.call.mockResolvedValue(await anchor("unverified"));render(<TranscriptionCues proof={proof}/>);await userEvent.setup().click(screen.getByRole("button",{name:"引用时间段"}));await screen.findByText(/定位尚未校验/);expect(screen.queryByText(/关联已校验/)).not.toBeInTheDocument();});
 it("rejects wrong identity,digest and illegal times",async()=>{
  const content=JSON.stringify({params:{worker_output:{duration_ms:2000,cues:proof.cues}}});const output={content,metadata:{kind:"loss_report",sha256:await utf8Sha256(content),byte_length:new TextEncoder().encode(content).length}};
  const state={job_id:proof.jobId,input_ref:"s",attempt:2,state:"succeeded"};
  const sourceJob={...state,kind:"transcribe"};
  await expect(transcriptionProof("s",proof.revision,proof.jobId,state,output,sourceJob)).resolves.toMatchObject({jobId:proof.jobId});
  await expect(transcriptionProof("other",proof.revision,proof.jobId,state,output,sourceJob)).rejects.toThrow();
  await expect(transcriptionProof("s",proof.revision,proof.jobId,state,{...output,metadata:{...output.metadata,sha256:"wrong"}},sourceJob)).rejects.toThrow();
  for(const changed of [{kind:"media"},{job_id:"other"},{input_ref:"other"},{attempt:3},{state:"failed"}])await expect(transcriptionProof("s",proof.revision,proof.jobId,state,output,{...sourceJob,...changed})).rejects.toThrow();
  const invalid=JSON.stringify({params:{worker_output:{duration_ms:2000,cues:[{start_ms:0,end_ms:2001,text:"bad"}]}}});
  await expect(transcriptionProof("s",proof.revision,proof.jobId,state,{content:invalid,metadata:{kind:"loss_report",sha256:await utf8Sha256(invalid),byte_length:invalid.length}},sourceJob)).rejects.toThrow();
 });
 it("preserves all-unlocated audio without a video title or anchor",()=>{
  render(<TranscriptionCues proof={{...proof,cues:[],pipeline:{alignment_status:"partial",raw_cues:[{start_ms:87290,end_ms:88290,text:"original tail"}],alignment_issues:[{index:0,start_ms:87290,end_ms:88290,location_status:"unlocated"}]}}}/>);
  expect(screen.getByLabelText("转写定位状态")).toHaveTextContent("partial");
  expect(screen.getByText(/原始转写含无法定位/)).toBeInTheDocument();
  expect(screen.queryByLabelText("独立视频帧识别结果")).not.toBeInTheDocument();
  expect(screen.queryByRole("button",{name:"引用时间段"})).not.toBeInTheDocument();
  expect(bridge.call).not.toHaveBeenCalled();
 });
 it("reads video partial stages as independent descriptions and never anchors frames",()=>{
  render(<TranscriptionCues proof={{...proof,cues:[],pipeline:{pipeline_state:"partial",visual_results:[{state:"succeeded",sampling_seek_requested_ms:27000,description:"independent frame description"},{state:"failed",sampling_seek_requested_ms:54000,reason:"visual_sample_failed"}]}}}/>);
  expect(screen.getByLabelText("独立视频帧识别结果")).toHaveTextContent("27.000");
  expect(screen.getByText("independent frame description")).toBeInTheDocument();
  expect(screen.getByText(/疑点：visual_sample_failed/)).toBeInTheDocument();
  expect(screen.queryByRole("button",{name:"引用时间段"})).not.toBeInTheDocument();
  expect(bridge.call).not.toHaveBeenCalled();
 });
 it("accepts only explicitly requested video job proof, not an audio identity",async()=>{
  const content=JSON.stringify({params:{worker_output:{duration_ms:2000,cues:[],pipeline_state:"partial",visual_results:[]}}});
  const output={content,metadata:{kind:"loss_report",sha256:await utf8Sha256(content),byte_length:new TextEncoder().encode(content).length}};
  const state={job_id:proof.jobId,input_ref:"s",attempt:2,state:"succeeded"};
  await expect(transcriptionProof("s",proof.revision,proof.jobId,state,output,{...state,kind:"video"},"video")).resolves.toMatchObject({pipeline:{pipeline_state:"partial"}});
  await expect(transcriptionProof("s",proof.revision,proof.jobId,state,output,{...state,kind:"transcribe"},"video")).rejects.toThrow();
 });

 it("shows processing partial even when yielded cue alignment is complete",()=>{
  render(<TranscriptionCues proof={{...proof,pipeline:{processing_status:"partial",alignment_status:"complete",processing_error:{stage:"segment_iteration",error_type:"RuntimeError"},alignment_issues:[]}}}/>);
  expect(screen.getByLabelText("转写定位状态")).toHaveTextContent("处理状态：partial");
  expect(screen.getByRole("cell",{name:"数值37"})).toBeInTheDocument();
  expect(screen.getByRole("button",{name:"引用时间段"})).toBeInTheDocument();
  expect(bridge.call).not.toHaveBeenCalled();
 });

});
