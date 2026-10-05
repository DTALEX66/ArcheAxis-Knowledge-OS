import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CheckPanel, checkExecutionLabel } from "../components/CheckPanel";
import type { DocumentDto } from "../api/generated/core-contract";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const document:DocumentDto={document_id:"d",source_id:null,source_revision:null,title:"原创",version:2,content_sha256:"hash",editor_json:{type:"doc"},text_projection:"正文",blocks:[]};
const check={check_id:"c",document_id:"d",version:2,content_sha256:"hash",dimension:"recognition_fidelity",provider_mode:"cloud",status:"pending",actor:"human",execution_verified:false,execution_state:"not_executed",reason:"worker_not_configured"};
describe("independent document checks",()=>{
 beforeEach(()=>{bridge.call.mockReset();});
 it("SIMULATED: displays failed original model output as inert text without successful verification",async()=>{
  const raw="<img src=x onerror=alert(1)> invalid JSON";
  bridge.call.mockResolvedValue({document_id:"d",version:2,content_sha256:"hash",historical:false,default_status:"unverified",checks_capped:false,next_offset:null,checks:[{...check,actor:"machine",status:"failed",execution_state:"failed",execution_verified:false,raw_response:raw,engine_receipt:{finish_reason:"length",raw_response_stored:true},reason:"model_response_truncated"}]});
  const {container}=render(<CheckPanel document={document} onRevisionBasis={vi.fn()}/>);
  expect(await screen.findByText(raw)).toBeInTheDocument();
  expect(container.querySelector("img")).toBeNull();
  expect(screen.getByText(/任务执行失败/)).toBeInTheDocument();
  expect(screen.queryByText(/云端任务已执行/)).not.toBeInTheDocument();
 });
 it("reads the next page for the selected historical version",async()=>{
  bridge.call.mockImplementation(async(_op:string,payload:Record<string,unknown>)=>({document_id:"d",version:payload.version,content_sha256:"hash",historical:payload.version===1,default_status:"unverified",checks_capped:!payload.offset,next_offset:payload.offset?null:1000,checks:[]}));
  render(<CheckPanel document={document} onRevisionBasis={vi.fn()}/>);const user=userEvent.setup();
  await user.click(await screen.findByRole("button",{name:"读取下一页核验记录"}));
  expect(bridge.call).toHaveBeenCalledWith("document_checks",{document_id:"d",version:2,offset:1000});
  await waitFor(()=>expect(screen.queryByRole("button",{name:"读取下一页核验记录"})).not.toBeInTheDocument());
 });
 it("records cloud pending without claiming execution and keeps dimensions separate",async()=>{
  let checks:unknown[]=[];
  bridge.call.mockImplementation(async(op:string)=>{if(op==="document_checks")return {document_id:"d",version:2,content_sha256:"hash",historical:false,default_status:"unverified",checks_capped:false,next_offset:null,checks};checks=[check];return check;});
  render(<CheckPanel document={document} onRevisionBasis={vi.fn()}/>);
  await waitFor(()=>expect(screen.getAllByText("该版本尚无核验记录。")).toHaveLength(2));
  await userEvent.setup().click(screen.getByRole("button",{name:"申请识别云端核验"}));
  expect(await screen.findByText("申请已记录；云端核验尚未执行。")).toBeInTheDocument();
  expect(within(screen.getByLabelText("识别忠实度")).getByText(/云端尚未执行/)).toBeInTheDocument();
  expect(within(screen.getByLabelText("专业依据")).getByText("该版本尚无核验记录。")).toBeInTheDocument();
  expect(bridge.call).toHaveBeenCalledWith("document_check_record",{document_id:"d",body:{version:2,dimension:"recognition_fidelity",provider_mode:"cloud"}});
 });
 it("requires an explicit manual action and retains its fields when human permission is denied",async()=>{
  bridge.call.mockImplementation(async(op:string)=>{if(op==="document_checks")return {document_id:"d",version:2,content_sha256:"hash",historical:false,default_status:"unverified",checks_capped:false,next_offset:null,checks:[]};throw new Error("403");});
  render(<CheckPanel document={document} onRevisionBasis={vi.fn()}/>);
  const user=userEvent.setup();await user.type(screen.getByLabelText("核验说明"),"实际疑点");
  expect(bridge.call.mock.calls.filter(([op])=>op==="document_check_record")).toHaveLength(0);
  await user.click(within(screen.getByLabelText("专业依据")).getByRole("button",{name:"明确提交手动核验记录"}));
  expect(await screen.findByText(/核验记录未确认/)).toBeInTheDocument();expect(screen.getByLabelText("核验说明")).toHaveValue("实际疑点");
 });
 it("reads historical checks without restoring text and explicitly selects a revision rationale",async()=>{
  bridge.call.mockImplementation(async(_op:string,payload:Record<string,unknown>)=>({document_id:"d",version:payload.version,content_sha256:"hash",historical:payload.version===1,default_status:"unverified",checks_capped:false,next_offset:null,checks:[{...check,version:payload.version}]}));
  const selected=vi.fn();render(<CheckPanel document={document} onRevisionBasis={selected}/>);const user=userEvent.setup();
  await user.clear(screen.getByLabelText("查看核验版本"));await user.type(screen.getByLabelText("查看核验版本"),"1");await user.click(screen.getByRole("button",{name:"读取版本记录"}));
  expect(await screen.findByText(/正在查看旧版本 1/)).toBeInTheDocument();
  await user.type(screen.getByLabelText("下一次修订理由"),"修正疑点");await user.click(screen.getByRole("button",{name:"用于下一次修订"}));
  expect(selected).toHaveBeenCalledWith({rationale:"修正疑点",reference_version:1,check_id:"c"});
  expect(bridge.call.mock.calls.some(([op])=>op==="document_restore"||op==="document_draft")).toBe(false);
 });
 it("SIMULATED: explicit unconfigured execute and retry retain actual request and attempt identity",async()=>{
  let checks:any[]=[check];let n=0;
  bridge.call.mockImplementation(async(op:string)=>{
   if(op==="document_checks")return {document_id:"d",version:2,content_sha256:"hash",historical:false,default_status:"unverified",checks_capped:false,next_offset:null,checks};
   if(op!=="document_check_execute")throw new Error("unexpected operation");
   const previous=n?"doccheck_1":null;n++;
   const receipt={...check,check_id:`terminal_${n}`,request_check_id:"c",attempt_id:`doccheck_${n}`,retry_of_task_id:previous,status:"failed",reason:"not_configured",actor:"machine",execution_state:"not_executed",execution_verified:false,engine_receipt:null,retrieval_receipts:[]};checks=[receipt];return receipt;
  });
  render(<CheckPanel document={document} onRevisionBasis={vi.fn()}/>);const user=userEvent.setup();
  await user.click(await screen.findByRole("button",{name:"明确执行核验"}));
  expect(await screen.findByText(/执行尝试已记录为失败/)).toBeInTheDocument();
  expect(bridge.call).toHaveBeenCalledWith("document_check_execute",{document_id:"d",body:{check_id:"c",expected_content_sha256:"hash"}});
  await user.click(await screen.findByRole("button",{name:"明确重试执行核验"}));
  expect(bridge.call).toHaveBeenCalledWith("document_check_execute",{document_id:"d",body:{check_id:"c",expected_content_sha256:"hash",retry_of_task_id:"doccheck_1"}});
  expect(bridge.call.mock.calls.some(([op])=>op==="document_draft"||op==="knowledge_review"||op==="jobs_get")).toBe(false);
 });
 it("SIMULATED: permission refusal does not manufacture execution success",async()=>{
  bridge.call.mockImplementation(async(op:string)=>{if(op==="document_checks")return {document_id:"d",version:2,content_sha256:"hash",historical:false,default_status:"unverified",checks_capped:false,next_offset:null,checks:[check]};throw new Error("403");});
  render(<CheckPanel document={document} onRevisionBasis={vi.fn()}/>);
  await userEvent.setup().click(await screen.findByRole("button",{name:"明确执行核验"}));
  expect(await screen.findByText(/执行回执未确认/)).toBeInTheDocument();expect(screen.queryByText(/云端已执行/)).not.toBeInTheDocument();
 });

 it("SIMULATED: delayed old execute cannot replace a newly selected document",async()=>{
  let release!:(value:unknown)=>void;
  bridge.call.mockImplementation((op:string,p:any)=>{
   if(op==="document_check_execute")return new Promise(resolve=>{release=resolve;});
   return Promise.resolve({document_id:p.document_id,version:p.version,content_sha256:p.document_id==="d"?"hash":"newhash",historical:false,default_status:"unverified",checks_capped:false,next_offset:null,checks:p.document_id==="d"?[check]:[]});
  });
  const view=render(<CheckPanel document={document} onRevisionBasis={vi.fn()}/>);
  await userEvent.setup().click(await screen.findByRole("button",{name:"明确执行核验"}));
  view.rerender(<CheckPanel document={{...document,document_id:"new",version:3,content_sha256:"newhash"}} onRevisionBasis={vi.fn()}/>);
  await waitFor(()=>expect(screen.getAllByText("该版本尚无核验记录。")).toHaveLength(2));
  release({...check,check_id:"terminal",request_check_id:"c",attempt_id:"doccheck_old",retry_of_task_id:null,status:"failed",reason:"not_configured",actor:"machine",execution_verified:false,execution_state:"not_executed"});
  await new Promise(resolve=>setTimeout(resolve,20));
  expect(screen.queryByText(/执行尝试已记录为失败/)).not.toBeInTheDocument();expect(screen.getAllByText("该版本尚无核验记录。")).toHaveLength(2);
 });

 it("SIMULATED: dimension-specific executed verdicts remain distinct from human approval",()=>{
  const engine={provider:"configured-fixture",requested_model:"fixture-v1",model:"fixture-v1",prompt_sha256:"a".repeat(64),response_sha256:"b".repeat(64),tokens_used:12,finish_reason:"stop"};
  const executed={...check,execution_verified:true,execution_state:"executed",engine_receipt:engine,retrieval_receipts:[]};
  for(const status of ["faithful","mismatch","uncertain","original_unclear","conflicting"]){expect(checkExecutionLabel({...executed,status} as any)).toMatch(/真实核验任务已执行/);}
  for(const status of ["supported","refuted","uncertain","conflicting"]){expect(checkExecutionLabel({...executed,dimension:"professional_basis",status} as any)).toMatch(/专业依据与真人认可分别记录/);}
  expect(()=>checkExecutionLabel({...executed,status:"supported"} as any)).toThrow();
  expect(()=>checkExecutionLabel({...executed,status:"faithful",engine_receipt:{...engine,model:"unknown"}} as any)).toThrow();
  expect(()=>checkExecutionLabel({...executed,status:"faithful",execution_verified:false} as any)).toThrow();
  expect(checkExecutionLabel({...check,status:"failed",execution_state:"failed",reason:"retrieval_empty",reported_status:"uncertain"} as any)).toMatch(/失败当作内容判断/);
 });
 it("SIMULATED: an actual executed uncertain receipt is displayed and cannot be retried as failed",async()=>{
  let checks:any[]=[check];
  const receipt={...check,check_id:"terminal",request_check_id:"c",attempt_id:"doccheck_verified",retry_of_task_id:null,status:"uncertain",execution_state:"executed",execution_verified:true,engine_receipt:{provider:"configured-fixture",requested_model:"fixture-v1",model:"fixture-v1",prompt_sha256:"a".repeat(64),response_sha256:"b".repeat(64),tokens_used:12,finish_reason:"stop"},retrieval_receipts:[]};
  bridge.call.mockImplementation(async(op:string)=>{if(op==="document_checks")return {document_id:"d",version:2,content_sha256:"hash",historical:false,default_status:"unverified",checks_capped:false,next_offset:null,checks};if(op==="document_check_execute"){checks=[receipt];return receipt;}throw new Error("unexpected operation");});
  render(<CheckPanel document={document} onRevisionBasis={vi.fn()}/>);
  await userEvent.setup().click(await screen.findByRole("button",{name:"明确执行核验"}));
  expect(await screen.findByText(/真实核验任务已执行：不确定/)).toBeInTheDocument();
  expect(screen.queryByRole("button",{name:"明确重试执行核验"})).not.toBeInTheDocument();
  expect(bridge.call.mock.calls.some(([op])=>op==="knowledge_review"||op==="document_draft")).toBe(false);
 });
 it("SIMULATED: late historical read cannot overwrite a new document version",async()=>{
  let release!:(value:unknown)=>void;
  bridge.call.mockImplementation((_op:string,p:any)=>{if(p.document_id==="d"&&p.version===1)return new Promise(resolve=>{release=resolve;});return Promise.resolve({document_id:p.document_id,version:p.version,content_sha256:p.document_id==="d"?"hash":"newhash",historical:false,default_status:"unverified",checks_capped:false,next_offset:null,checks:[]});});
  const view=render(<CheckPanel document={document} onRevisionBasis={vi.fn()}/>);const user=userEvent.setup();await user.clear(screen.getByLabelText("查看核验版本"));await user.type(screen.getByLabelText("查看核验版本"),"1");await user.click(screen.getByRole("button",{name:"读取版本记录"}));
  view.rerender(<CheckPanel document={{...document,document_id:"new",version:3,content_sha256:"newhash"}} onRevisionBasis={vi.fn()}/>);
  await waitFor(()=>expect(screen.getByLabelText("查看核验版本")).toHaveValue(3));release({document_id:"d",version:1,content_sha256:"oldhash",historical:true,default_status:"unverified",checks_capped:false,next_offset:null,checks:[{...check,version:1}]});
  await new Promise(resolve=>setTimeout(resolve,20));expect(screen.queryByText(/正在查看旧版本/)).not.toBeInTheDocument();
 });

 it.each([null,1000])("SIMULATED: ascending history only offers latest failed retry on complete final page (%s)",async(nextOffset)=>{
  const first={...check,check_id:"old-terminal",request_check_id:"c",attempt_id:"doccheck_old",status:"failed",reason:"not_configured"};
  const last={...first,check_id:"new-terminal",attempt_id:"doccheck_latest",retry_of_task_id:"doccheck_old"};
  bridge.call.mockImplementation(async(op:string)=>{if(op==="document_checks")return {document_id:"d",version:2,content_sha256:"hash",historical:false,default_status:"unverified",checks_capped:nextOffset!==null,next_offset:nextOffset,checks:[check,first,last]};throw new Error("403");});
  render(<CheckPanel document={document} onRevisionBasis={vi.fn()}/>);
  await screen.findByText(/等待核验/);
  expect(screen.queryByRole("button",{name:"明确执行核验"})).not.toBeInTheDocument();
  if(nextOffset===null){await userEvent.setup().click(screen.getByRole("button",{name:"明确重试执行核验"}));expect(bridge.call).toHaveBeenCalledWith("document_check_execute",{document_id:"d",body:{check_id:"c",expected_content_sha256:"hash",retry_of_task_id:"doccheck_latest"}});}
  else expect(screen.queryByRole("button",{name:"明确重试执行核验"})).not.toBeInTheDocument();
 });

});
