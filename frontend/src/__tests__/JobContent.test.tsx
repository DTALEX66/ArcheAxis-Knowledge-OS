import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { JobContent } from "../components/JobContent";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
describe("Core job content",()=>{
 beforeEach(()=>{bridge.call.mockReset();});
 it.each([["sample.png","image","执行真实内容转换"],["sample.zip","archive","清点容器与登记成员"],["sample.tar","archive","清点容器与登记成员"],["sample.canvas","canvas","执行真实内容转换"],["sample.srt","subtitles","执行真实内容转换"],["sample.xml","text","执行真实内容转换"],["sample.wav","media","执行媒体头信息探测"],["sample.mp4","media","执行媒体头信息探测"]])("routes existing %s worker without claiming unexecuted success",async(name,kind,label)=>{
  bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>{
   if(op==="job_enqueue")return {job_id:(payload.body as Record<string,unknown>).job_id};
   if(op==="jobs_get")return {state:"failed",error_code:"AAK-WORKER-003"};
   return {};
  });
  render(<JobContent sourceId="src_format" name={name}/>);
  await userEvent.setup().click(screen.getByRole("button",{name:label}));
  await screen.findByText(/转换未完成或产物读取失败/);
  expect(bridge.call).toHaveBeenCalledWith("job_enqueue",{body:{job_id:expect.any(String),kind,input_ref:"src_format"}});
  expect(screen.queryByLabelText("Core 提取正文")).not.toBeInTheDocument();
  if(kind==="media")expect(screen.getByText(/不表示已解码、转写或核对时间段内容/)).toBeInTheDocument();
 });
 it("retains successful output when a later job fails and binds candidates to its successful transform",async()=>{
  let latest="";let executions=0;
  bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>{
   if(op==="capabilities_list")return {};
   if(op==="job_enqueue"){latest=String((payload.body as Record<string,unknown>).job_id);return {job_id:latest};}
   if(op==="job_execute"){executions++;return {};}
   if(op==="jobs_get")return executions===1?{state:"succeeded"}:{state:"failed",error_code:"AAK-WORKER-003"};
   if(op==="job_output")return {content:payload.kind==="text"?"保留正文": "[]"};
   if(op==="job_quality")return {engine:"real"};
   if(op==="source_job_transform")return {source_id:"s",job_id:latest,transform_id:42,content:"保留正文"};
  });
  render(<JobContent sourceId="s" name="sample.xlsx"/>);
  const user=userEvent.setup();await user.click(screen.getByRole("button",{name:"执行真实内容转换"}));
  expect(await screen.findByLabelText("Core 提取正文")).toHaveTextContent("保留正文");
  await user.click(screen.getByRole("button",{name:"执行真实内容转换"}));
  await screen.findByText(/转换未完成或产物读取失败/);
  expect(screen.getByLabelText("Core 提取正文")).toHaveTextContent("保留正文");
  expect(screen.getByText(/AAK-WORKER-003/)).toBeInTheDocument();
 });
 it("requires real completion and reads all persisted outputs with actual engine proof",async()=>{
 bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>{
  if(op==="capabilities_list")return {execution_verified:false};
  if(op==="job_enqueue")return {job_id:(payload.body as Record<string,unknown>).job_id,state:"queued"};
  if(op==="job_execute")return {state:"running"};
  if(op==="jobs_get")return {state:"succeeded"};
  if(op==="job_quality")return {engine:"openpyxl",engine_version:"3.1.5"};
  if(op==="source_job_transform")return {source_id:payload.source_id,job_id:payload.job_id,transform_id:42,content:"Sheet1 A1 真实单元格"};
  if(op==="knowledge_from_transform")return {status:"candidate",knowledge_id:"k1",anchor_id:"a1"};
  if(op==="job_output")return {metadata:{},content:payload.kind==="text"?"Sheet1 A1 真实单元格":JSON.stringify({kind:payload.kind})};
 });render(<JobContent sourceId="src_office" name="sample.xlsx"/>);await userEvent.setup().click(screen.getByRole("button",{name:"执行真实内容转换"}));
 expect(await screen.findByLabelText("Core 提取正文")).toHaveTextContent("真实单元格");expect(screen.getByText(/engine_version/)).toHaveTextContent("openpyxl");
 expect(bridge.call).toHaveBeenCalledWith("job_enqueue",{body:{job_id:expect.any(String),kind:"office",input_ref:"src_office"}});
 const selection=screen.getByLabelText("选择实际引文");fireEvent.select(selection,{target:{selectionStart:0,selectionEnd:6}});
 await userEvent.setup().type(screen.getByLabelText("知识候选正文"),"真实候选正文");await userEvent.setup().click(screen.getByRole("button",{name:"创建知识候选"}));
 await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("knowledge_from_transform",{body:{knowledge_type:"source_note",body:"真实候选正文",source_id:"src_office",job_id:expect.any(String),transform_id:42,selection_start_utf16:0,selection_end_utf16:6,quote:"Sheet1"}}));
 });
 it("shows readable native structure with Unicode scalar ranges and keeps loss diagnostics folded",async()=>{
 const content="😀 A1=已知值";
 bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>{
  if(op==="job_enqueue")return {job_id:(payload.body as Record<string,unknown>).job_id};
  if(op==="jobs_get")return {state:"succeeded"};
  if(op==="source_job_transform")return {source_id:payload.source_id,job_id:payload.job_id,transform_id:1,content};
  if(op==="job_output")return {content:payload.kind==="text"?content:JSON.stringify(payload.kind==="document_structure"?[{kind:"sheet_row",path:["sheet-预算","row-1"],char_start:2,char_end:8},{kind:"unknown",path:["unresolved"],char_start:999,char_end:1000}]:{loss_note:"formula text only"})};
  return {};
 });
 render(<JobContent sourceId="src_structure" name="预算.xlsx"/>);
 await userEvent.setup().click(screen.getByRole("button",{name:"执行真实内容转换"}));
 expect(await screen.findByRole("cell",{name:"sheet-预算 / row-1"})).toBeInTheDocument();
 expect(screen.getByRole("cell",{name:"A1=已知值"})).toBeInTheDocument();
 expect(screen.getByRole("cell",{name:"正文范围未提供或未匹配"})).toBeInTheDocument();
 expect(screen.getByText("更多信息：损失、引擎与处理记录").closest("details")).not.toHaveAttribute("open");
 });
 it("does not publish content when the actual job fails",async()=>{
 bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>op==="job_enqueue"?{job_id:(payload.body as Record<string,unknown>).job_id}:op==="jobs_get"?{state:"failed",error:"AAK-WORKER-003"}:{});
 render(<JobContent sourceId="src_bad" name="bad.pptx"/>);await userEvent.setup().click(screen.getByRole("button",{name:"执行真实内容转换"}));
 expect(await screen.findByText(/转换未完成/)).toBeInTheDocument();expect(screen.queryByLabelText("Core 提取正文")).not.toBeInTheDocument();expect(bridge.call.mock.calls.some(([op])=>op==="job_output")).toBe(false);
 });
});
