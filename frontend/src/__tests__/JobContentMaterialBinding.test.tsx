import {webcrypto} from "node:crypto";
import {beforeEach,describe,expect,it,vi} from "vitest";
import {fireEvent,render,screen,waitFor} from "@testing-library/react";
import {JobContent} from "../components/JobContent";
import {outputReceipt} from "./fixtures/jobContentCoreFixture";

const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const revision="a".repeat(64),content="已保存的成功转换正文 😀";

// SYNTHETIC bridge fixtures; exercise the real reader and material-preview consumer.
function fixture(latestState:string,nextSucceeded=false){
 let queued="",request="",budget:unknown;
 bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>={})=>{
  if(op==="capabilities_list")return {};
  if(op==="source_jobs")return {source_id:"source",jobs:[
   {job_id:"newer",input_ref:"source",kind:"office",state:latestState,attempt:1},
   {job_id:"saved",input_ref:"source",kind:"office",state:"succeeded",attempt:2},
  ],jobs_capped:false};
  if(op==="jobs_get")return {job_id:"saved",input_ref:"source",state:"succeeded",attempt:2,request_id:"saved-request",error:null};
  if(op==="job_output")return outputReceipt(p.kind,p.kind==="text"?(p.job_id===queued?"新的成功正文":content):p.kind==="document_structure"?"[]":"{}");
  if(op==="job_quality")return {job_id:p.job_id,engine:"SYNTHETIC",loss_count:0};
  if(op==="source_job_transform")return {source_id:"source",job_id:p.job_id,transform_id:p.job_id===queued?3:2,raw_sha256:revision,content:p.job_id===queued?"新的成功正文":content};
  if(op==="model_configuration_get")return {revision:0};
  if(op==="material_question"){
   if((p.body as Record<string,unknown>).preview!==true)throw Error("No inference authorized by this fixture");
   return {schema:"archeaxis.material-question-preview/v1",plan_sha256:"b".repeat(64)};
  }
  if(op==="job_enqueue"){queued=String((p.body as Record<string,unknown>).job_id);return {job_id:queued,state:"queued"};}
  if(op==="job_execute"){request=String(p.request_id);budget=p.body;return {job_id:queued,request_id:request,state:"running",replayed:false};}
  if(op==="job_execution_status"){const state=nextSucceeded?"succeeded":"failed";return {job_id:queued,input_ref:"source",kind:"office",state,attempt:1,request_id:request,error:nextSucceeded?null:"SYNTHETIC_CONVERSION_FAILURE",attempts:[{attempt:1,request_id:request,state,budget,continuation:{new_attempt_eligible_state:!nextSucceeded}}]};}
  throw Error(`Unexpected operation ${op}`);
 });
}

describe("reader material identity after a newer unsuccessful conversion",()=>{
 beforeEach(()=>{bridge.call.mockReset();vi.stubGlobal("crypto",webcrypto);});
 it.each(["failed","cancelled","leased"])("previews the displayed successful transform when the latest job is %s",async state=>{
  fixture(state);render(<JobContent sourceId="source" sourceRevision={revision} name="report.xlsx"/>);
  await screen.findByLabelText("Core 提取正文");
  fireEvent.change(await screen.findByLabelText("材料问题"),{target:{value:"请解释这份正文"}});
  fireEvent.click(screen.getByRole("button",{name:"预览材料提问"}));
  await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("material_question",{body:expect.objectContaining({preview:true,material:expect.objectContaining({job_id:"saved",transform_id:2,raw_sha256:revision})})}));
  expect(screen.getByText("最新任务 newer")).toBeInTheDocument();
  expect(bridge.call.mock.calls.some(([op])=>op==="job_enqueue"||op==="job_execute")).toBe(false);
 });
 it("preserves the question and preview while a subsequent conversion fails",async()=>{
  fixture("failed");render(<JobContent sourceId="source" sourceRevision={revision} name="report.xlsx"/>);
  await screen.findByLabelText("Core 提取正文");
  fireEvent.change(await screen.findByLabelText("材料问题"),{target:{value:"保留这次问题"}});
  fireEvent.click(screen.getByRole("button",{name:"预览材料提问"}));
  await screen.findByRole("button",{name:"确认提问或查询原请求"});
  fireEvent.click(screen.getByRole("button",{name:"执行真实内容转换"}));
  await screen.findByText(/转换未完成或产物读取失败/);
  expect(screen.getByLabelText("Core 提取正文")).toHaveTextContent(content);
  expect(screen.getByLabelText("材料问题")).toHaveValue("保留这次问题");
  expect(screen.getByRole("button",{name:"确认提问或查询原请求"})).toBeInTheDocument();
  expect(bridge.call.mock.calls.filter(([op])=>op==="material_question")).toHaveLength(1);
 });
 it("invalidates the old preview and uses the new identity after a successful conversion",async()=>{
  fixture("failed",true);render(<JobContent sourceId="source" sourceRevision={revision} name="report.xlsx"/>);
  fireEvent.change(await screen.findByLabelText("材料问题"),{target:{value:"旧正文的问题"}});
  fireEvent.click(screen.getByRole("button",{name:"预览材料提问"}));
  await screen.findByRole("button",{name:"确认提问或查询原请求"});
  fireEvent.click(screen.getByRole("button",{name:"执行真实内容转换"}));
  await waitFor(()=>expect(screen.getByLabelText("Core 提取正文")).toHaveTextContent("新的成功正文"));
  await waitFor(()=>expect(screen.getByLabelText("材料问题")).toHaveValue(""));
  expect(screen.queryByRole("button",{name:"确认提问或查询原请求"})).toBeNull();
  fireEvent.change(screen.getByLabelText("材料问题"),{target:{value:"新正文的问题"}});
  fireEvent.click(screen.getByRole("button",{name:"预览材料提问"}));
  const newJob=(bridge.call.mock.calls.find(([op])=>op==="job_enqueue")![1].body as Record<string,unknown>).job_id;
  await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("material_question",{body:expect.objectContaining({preview:true,material:expect.objectContaining({job_id:newJob,transform_id:3,raw_sha256:revision})})}));
  expect(bridge.call.mock.calls.filter(([op])=>op==="material_question")).toHaveLength(2);
 });
});
