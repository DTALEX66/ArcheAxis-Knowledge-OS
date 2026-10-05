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
 it("keeps silence empty and never offers an anchor",()=>{render(<TranscriptionCues proof={{...proof,cues:[]}}/>);expect(screen.getByText(/没有语音片段/)).toBeInTheDocument();expect(screen.queryByRole("button",{name:"引用时间段"})).not.toBeInTheDocument();});
 it("does not convert API refusal into located",async()=>{bridge.call.mockRejectedValue(new Error("400"));render(<TranscriptionCues proof={proof}/>);await userEvent.setup().click(screen.getByRole("button",{name:"引用时间段"}));await screen.findByText(/时间引用未确认/);expect(screen.queryByText(/关联已校验/)).not.toBeInTheDocument();});
 it("displays unverified explicitly",async()=>{bridge.call.mockResolvedValue(await anchor("unverified"));render(<TranscriptionCues proof={proof}/>);await userEvent.setup().click(screen.getByRole("button",{name:"引用时间段"}));await screen.findByText(/定位尚未校验/);expect(screen.queryByText(/关联已校验/)).not.toBeInTheDocument();});
 it("rejects wrong identity,digest and illegal times",async()=>{
  const content=JSON.stringify({params:{worker_output:{duration_ms:2000,cues:proof.cues}}});const output={content,metadata:{kind:"loss_report",sha256:await utf8Sha256(content),byte_length:new TextEncoder().encode(content).length}};
  const state={job_id:proof.jobId,input_ref:"s",attempt:2,state:"succeeded",kind:"transcribe"};
  await expect(transcriptionProof("s",proof.revision,proof.jobId,state,output)).resolves.toMatchObject({jobId:proof.jobId});
  await expect(transcriptionProof("other",proof.revision,proof.jobId,state,output)).rejects.toThrow();
  await expect(transcriptionProof("s",proof.revision,proof.jobId,state,{...output,metadata:{...output.metadata,sha256:"wrong"}})).rejects.toThrow();
  const invalid=JSON.stringify({params:{worker_output:{duration_ms:2000,cues:[{start_ms:0,end_ms:2001,text:"bad"}]}}});
  await expect(transcriptionProof("s",proof.revision,proof.jobId,state,{content:invalid,metadata:{kind:"loss_report",sha256:await utf8Sha256(invalid),byte_length:invalid.length}})).rejects.toThrow();
 });
});
