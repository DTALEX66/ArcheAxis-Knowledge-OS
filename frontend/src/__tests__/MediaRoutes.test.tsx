import {beforeEach,describe,it,expect,vi} from "vitest";
import {render,screen,waitFor} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {JobContent} from "../components/JobContent";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
describe("actual media defaults and independent header probe",()=>{
 beforeEach(()=>bridge.call.mockReset());
 it.each([["speech.wav","transcribe","执行真实语音转写"],["lesson.mp4","video","执行真实视频分析"]])("routes %s once then retains independent probe",async(name,kind,label)=>{
  bridge.call.mockImplementation(async(op:string,p:any)=>op==="job_enqueue"?{job_id:p.body.job_id}:op==="jobs_get"?{state:"failed"}:{});
  render(<JobContent sourceId="s" name={name}/>);const user=userEvent.setup();
  expect(screen.getAllByRole("button",{name:label})).toHaveLength(1);
  await user.click(screen.getByRole("button",{name:label}));await screen.findByText(/转换未完成或产物读取失败/);
  expect(bridge.call).toHaveBeenCalledWith("job_enqueue",{body:{job_id:expect.any(String),kind,input_ref:"s"}});
  expect(bridge.call).toHaveBeenCalledWith("job_execute",{job_id:expect.any(String),body:{deadline_ms:300000}});
  await user.click(screen.getByRole("button",{name:"执行媒体头信息探测"}));
  await waitFor(()=>expect(bridge.call.mock.calls.filter(([op])=>op==="job_enqueue")).toHaveLength(2));
  expect(bridge.call).toHaveBeenLastCalledWith("jobs_get",expect.anything());
  expect(bridge.call.mock.calls.filter(([op])=>op==="job_enqueue")[1][1].body.kind).toBe("media");
 });
});
