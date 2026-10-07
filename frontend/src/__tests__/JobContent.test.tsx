import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { JobContent } from "../components/JobContent";
import { conversionKindFor } from "../api/conversionKinds";
import { describeSplit, splitProgressOf } from "../presentation/mediaEstimate";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
describe("Core job content",()=>{
 beforeEach(()=>{bridge.call.mockReset();});
 it.each([["sample.png","image","执行真实内容转换"],["sample.zip","archive","清点容器与登记成员"],["sample.tar","archive","清点容器与登记成员"],["sample.canvas","canvas","执行真实内容转换"],["sample.srt","subtitles","执行真实内容转换"],["sample.xml","text","执行真实内容转换"],["sample.py","text","执行真实内容转换"],["sample.wav","media","执行媒体头信息探测"],["sample.mp4","media","执行媒体头信息探测"]])("routes existing %s worker without claiming unexecuted success",async(name,kind,label)=>{
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
 it("publishes nothing when ASR is still leased at the wait deadline, and stays retryable",async()=>{
  // The wait loop has a deadline, not an error channel: a job that never reaches a terminal state
  // must not be reported as a failure of the product, and must not be reported as success either.
  const now=vi.spyOn(Date,"now");let step=0;now.mockImplementation(()=>((step+=100_000)-100_000));
  bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>{
   if(op==="capabilities_list")return {};
   if(op==="job_enqueue")return {job_id:(payload.body as Record<string,unknown>).job_id};
   if(op==="job_execute")return {};
   if(op==="jobs_get")return {job_id:String(payload.job_id),state:"leased",attempt:1};
   if(op==="job_output")throw new Error("a timed-out job has no product to read");
   return {};
  });
  render(<JobContent sourceId="src_asr" name="sample.wav"/>);
  const user=userEvent.setup();
  try{
   await user.click(screen.getByRole("button",{name:"执行真实语音转写"}));
   expect(await screen.findByText(/转换未完成或产物读取失败/)).toBeInTheDocument();
   expect(screen.queryByText(/真实转换已完成/)).not.toBeInTheDocument();
   expect(screen.queryByLabelText("Core 提取正文")).not.toBeInTheDocument();
   expect(bridge.call).not.toHaveBeenCalledWith("job_output",expect.anything());
   expect(step).toBeGreaterThan(310_000); // the deadline was reached, not skipped by an early terminal state
   // the unfinished state stays reachable verbatim, so the operator can see what was actually left running
   const debug=vi.spyOn(console,"debug").mockImplementation(()=>{});
   await user.click(screen.getByRole("button",{name:/最新处理状态与错误记录/}));
   expect(debug.mock.calls.some(([,label,payload])=>label==="最新处理状态与错误记录"&&JSON.stringify(payload).includes("leased"))).toBe(true);
   debug.mockRestore();
  }finally{
   now.mockRestore();
  }
  // releasing the busy flag is what keeps a timeout recoverable instead of a dead end
  await waitFor(()=>expect(screen.getByRole("button",{name:"执行真实语音转写"})).toBeEnabled());
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
  // The failed attempt stays reachable verbatim through the diagnostic channel, not inline in the reading column.
  const debug=vi.spyOn(console,"debug").mockImplementation(()=>{});
  await user.click(screen.getByRole("button",{name:/最新处理状态与错误记录/}));
  expect(debug.mock.calls.some(([,label,payload])=>label==="最新处理状态与错误记录"&&JSON.stringify(payload).includes("AAK-WORKER-003"))).toBe(true);
  expect(screen.queryByText(/AAK-WORKER-003/)).not.toBeInTheDocument();
  debug.mockRestore();
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
 expect(await screen.findByLabelText("Core 提取正文")).toHaveTextContent("真实单元格");
 const engineDebug=vi.spyOn(console,"debug").mockImplementation(()=>{});
 await userEvent.setup().click(screen.getByRole("button",{name:/损失、引擎与处理记录/}));
 expect(engineDebug.mock.calls.some(([,label,payload])=>label==="损失、引擎与处理记录"&&JSON.stringify(payload).includes("openpyxl"))).toBe(true);
 expect(screen.queryByText(/engine_version/)).not.toBeInTheDocument();
 engineDebug.mockRestore();
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
 expect(screen.getByRole("button",{name:/损失、引擎与处理记录/})).toBeInTheDocument();
 expect(screen.queryByText(/loss_note/)).not.toBeInTheDocument();
 });
 it("does not publish content when the actual job fails",async()=>{
 bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>op==="job_enqueue"?{job_id:(payload.body as Record<string,unknown>).job_id}:op==="jobs_get"?{state:"failed",error:"AAK-WORKER-003"}:{});
 render(<JobContent sourceId="src_bad" name="bad.pptx"/>);await userEvent.setup().click(screen.getByRole("button",{name:"执行真实内容转换"}));
 expect(await screen.findByText(/转换未完成/)).toBeInTheDocument();expect(screen.queryByLabelText("Core 提取正文")).not.toBeInTheDocument();expect(bridge.call.mock.calls.some(([op])=>op==="job_output")).toBe(false);
 });

 // SIMULATED late API receipts; the old request remains authorized on its source.
 it.each(["success","failure"])("ignores old knowledge candidate %s receipt after revision switches",async(outcome)=>{
  let resolveCandidate!:(value:unknown)=>void;
  let rejectCandidate!:(reason:Error)=>void;
  bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>{
   if(op==="source_jobs")return {source_id:payload.source_id,jobs:[],jobs_capped:false};
   if(op==="job_enqueue")return {job_id:(payload.body as Record<string,unknown>).job_id};
   if(op==="jobs_get")return {state:"succeeded"};
   if(op==="job_output")return {content:payload.kind==="text"?"Known candidate source":"[]"};
   if(op==="source_job_transform")return {source_id:payload.source_id,job_id:payload.job_id,transform_id:42,content:"Known candidate source"};
   if(op==="knowledge_from_transform")return new Promise((resolve,reject)=>{resolveCandidate=resolve;rejectCandidate=reject;});
   return {};
  });
  const view=render(<JobContent sourceId="source" sourceRevision={"a".repeat(64)} name="source.xlsx"/>);
  fireEvent.click(screen.getByRole("button",{name:"执行真实内容转换"}));
  await screen.findByLabelText("Core 提取正文");
  fireEvent.select(screen.getByLabelText("选择实际引文"),{target:{selectionStart:0,selectionEnd:5}});
  fireEvent.change(screen.getByLabelText("知识候选正文"),{target:{value:"candidate body"}});
  fireEvent.click(screen.getByRole("button",{name:"创建知识候选"}));
  await waitFor(()=>expect(resolveCandidate).toBeDefined());
  expect(bridge.call.mock.calls.filter(call=>call[0]==="knowledge_from_transform")).toHaveLength(1);
  view.rerender(<JobContent sourceId="source" sourceRevision={"b".repeat(64)} name="source.xlsx"/>);
  await act(async()=>{
   if(outcome==="success")resolveCandidate({status:"candidate",knowledge_id:"old-knowledge",anchor_id:"old-anchor"});
   else rejectCandidate(new Error("old request failure"));
  });
  expect(screen.queryByText("已创建来源与引文绑定的知识候选，尚未接受。")).toBeNull();
  expect(screen.queryByText("知识候选创建未确认，请保留正文与选区重试。")).toBeNull();
  expect(screen.queryByText(/候选 old-knowledge/)).toBeNull();
 });
 it("SIMULATED: tells the user the expected cost before executing media, and refuses to promise a whole job past the ceiling",async()=>{
  bridge.call.mockImplementation(async()=>({}));
  const {rerender}=render(<JobContent sourceId="s" name="speech.wav" mediaDurationSeconds={83}/>);
  expect(screen.getByText(/原件时长 约 1 分 23 秒/)).toBeInTheDocument();
  expect(screen.getByText(/整体执行在上限内，可直接执行/)).toBeInTheDocument();
  expect(screen.getByRole("button",{name:"整体执行"})).toBeEnabled();
  expect(screen.getByRole("button",{name:/切分执行（1 段/})).toBeInTheDocument();
  rerender(<JobContent sourceId="s" name="speech.wav" mediaDurationSeconds={720}/>);
  expect(screen.getByText(/原件时长 约 12 分 0 秒/)).toBeInTheDocument();
  const warning=screen.getByText(/请选择“切分执行”/);
  expect(warning).toHaveTextContent(/需分 6 段/);
  expect(warning).toHaveTextContent(/单段预计 约 5 分 0 秒/);
  // the whole-file action is offered but disabled, so the ceiling cannot be walked into by accident
  expect(screen.getByRole("button",{name:/整体执行（超过单作业上限，已停用）/})).toBeDisabled();
  expect(screen.getByRole("button",{name:/切分执行（6 段，可续跑）/})).toBeEnabled();
 });
 it("reads split progress from the receipt, and claims nothing when the receipt has none",()=>{
  const receipt=(windows:unknown)=>({params:{worker_output:{windows}}});
  expect(splitProgressOf(receipt({status:"complete",windows_expected:6,windows_present:6,windows_missing:[],windows_resumed:[0,1]})))
   .toEqual({status:"complete",expected:6,present:6,missing:[],resumed:[0,1]});
  expect(describeSplit({status:"complete",expected:6,present:6,missing:[],resumed:[0,1]})).toContain("复用了 2 段");
  // A partial receipt names the windows it did not reach instead of presenting the text as whole.
  const partial=splitProgressOf(receipt({status:"partial",windows_expected:6,windows_present:2,windows_missing:[2,3,4,5],windows_resumed:[]}))!;
  expect(describeSplit(partial)).toContain("2 / 6");
  expect(describeSplit(partial)).toContain("2、3、4、5");
  // No split record, or one that cannot be read, is not evidence that nothing ran.
  expect(splitProgressOf({})).toBeNull();
  expect(splitProgressOf(receipt({status:"complete",windows_expected:"6",windows_present:6}))).toBeNull();
 });
 it("SIMULATED: no estimate is shown for a format that has no local reading route",async()=>{
  bridge.call.mockImplementation(async()=>({}));
  render(<JobContent sourceId="s" name="budget.xlsx" mediaDurationSeconds={720}/>);
  expect(screen.queryByText(/原件时长/)).toBeNull();
 });
 // A05: reopening an ordinary conversion result must read it back from storage under its own route
 // kind, without starting a job or forcing it through the transcription-specific proof.
 it("reopens a persisted office result with no new job and no transcription proof",async()=>{
  const content="Sheet1 真实单元格已保存";
  bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>{
   if(op==="capabilities_list")return {};
   if(op==="source_jobs")return {source_id:payload.source_id,jobs:[{job_id:"job-office-1",kind:"office",input_ref:payload.source_id,state:"succeeded",attempt:1}],jobs_capped:false};
   if(op==="jobs_get")return {job_id:payload.job_id,state:"succeeded",attempt:1};
   if(op==="job_output"){
    if(payload.kind==="text")return {content};
    if(payload.kind==="document_structure")return {content:JSON.stringify([{kind:"sheet_row",path:["S1","r1"],char_start:0,char_end:5}])};
    return {content:"{}"};
   }
   if(op==="job_quality")return {engine:"openpyxl",engine_version:"3.1.5"};
   if(op==="source_job_transform")return {source_id:payload.source_id,job_id:payload.job_id,transform_id:7,content};
   throw new Error(`unexpected op ${op}`);
  });
  render(<JobContent sourceId="src_office_reopen" sourceRevision={"a".repeat(64)} name="report.xlsx"/>);
  expect(await screen.findByLabelText("Core 提取正文")).toHaveTextContent("真实单元格已保存");
  expect(screen.getByText(/已读回持久化转换结果/)).toBeInTheDocument();
  // No transcription cue section, and no fresh job was enqueued or executed.
  expect(screen.queryByText(/真实转写时间段/)).not.toBeInTheDocument();
  expect(bridge.call).not.toHaveBeenCalledWith("job_enqueue",expect.anything());
  expect(bridge.call).not.toHaveBeenCalledWith("job_execute",expect.anything());
  // The structure preview reflects the persisted transform, not a re-run.
  expect(await screen.findByRole("cell",{name:"S1 / r1"})).toBeInTheDocument();
 });
 // A04: source and config extensions with an existing text route must reach the UI instead of being
 // reported as read-only custody.
 it.each([["notes.py"],["main.rs"],["App.tsx"],["server.go"],["notes.log"],["settings.ini"],["query.sql"],["readme.markdown"]])("maps text-route source %s to the reading conversion action",async(name)=>{
  expect(conversionKindFor(name)).toBe("text");
 });
 it("keeps unregistered extensions without a conversion route",()=>{
  expect(conversionKindFor("archive.7z")).toBeNull();
  expect(conversionKindFor("vector.eps")).toBeNull();
 });
});
