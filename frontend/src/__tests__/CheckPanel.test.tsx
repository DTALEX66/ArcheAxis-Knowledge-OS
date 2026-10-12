import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CheckPanel, checkExecutionLabel } from "../components/CheckPanel";
import type { DocumentDto } from "../api/generated/core-contract";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const document:DocumentDto={document_id:"d",source_id:null,source_revision:null,title:"原创",version:2,content_sha256:"hash",editor_json:{type:"doc"},text_projection:"正文",blocks:[]};
const check={check_id:"c",document_id:"d",version:2,content_sha256:"hash",dimension:"recognition_fidelity",provider_mode:"cloud",status:"pending",actor:"human",execution_verified:false,execution_state:"not_executed",reason:"worker_not_configured"};
function preview(item:any=check, text=document.text_projection, scope="full_saved_snapshot") {
 return {...item,check_id:item.request_check_id??item.check_id,actor:"human",status:"pending",execution_verified:false,execution_state:"not_executed",egress_sha256:"a".repeat(64),egress_plan:{
  schema:"archeaxis.document-check-egress/v1",document_id:item.document_id,version:item.version,content_sha256:item.content_sha256,
  request_check_id:item.request_check_id??item.check_id,purpose:item.dimension,scope,configuration:{endpoint:"https://fixture.invalid/v1"},model_destination:"https://fixture.invalid/v1",
  document_text:{text,bytes:new TextEncoder().encode(text).length,sha256:"b".repeat(64)},original:null,recognition:null,
  search_query:item.search_query??null,search_destination:item.search_query?"https://lite.duckduckgo.com/lite/":null,usage:"unknown",cost:"unknown"}};
}
describe("independent document checks",()=>{
 beforeEach(()=>{bridge.call.mockReset();});
 it("SIMULATED: local-only request is recorded without offering cloud execution",async()=>{
  let records:any[]=[];
  bridge.call.mockImplementation(async(op:string,p:any)=>{
   if(op==="document_checks")return {document_id:"d",version:2,content_sha256:"hash",historical:false,default_status:"unverified",checks_capped:false,next_offset:null,checks:records};
   expect(op).toBe("document_check_record");expect(p.body.local_only).toBe(true);
   records=[{...check,dimension:p.body.dimension,local_only:true}];return records[0];
  });
  render(<CheckPanel document={document} onRevisionBasis={vi.fn()}/>);const user=userEvent.setup();
  await user.click(screen.getByLabelText("本次申请仅本地，禁止联网"));
  await user.click(screen.getByRole("button",{name:"申请专业云端核验"}));
  expect(await screen.findByText("本次申请仅限本地；禁止云端执行和联网检索。")).toBeInTheDocument();
  expect(screen.queryByRole("button",{name:"明确执行核验"})).not.toBeInTheDocument();
  expect(bridge.call.mock.calls.some(([op])=>op==="document_check_execute")).toBe(false);
 });
 it("SIMULATED: withdraws a request durably and never executes the control event",async()=>{
  let records:any[]=[check];
  const event={...check,check_id:"withdrawal",actor:"human",status:"unverified",execution_state:"withdrawn",reason:"egress_withdrawn",event_kind:"egress_control",control:"withdraw_request",target_request_check_id:"c"};
  bridge.call.mockImplementation(async(op:string,p:any)=>{
   if(op==="document_checks")return {document_id:"d",version:2,content_sha256:"hash",historical:false,default_status:"unverified",checks_capped:false,next_offset:null,checks:records};
   expect(p.body).toEqual({check_id:"c",expected_content_sha256:"hash",withdraw:true});records=[check,event];return event;
  });
  const view=render(<CheckPanel document={document} onRevisionBasis={vi.fn()}/>);
  await userEvent.setup().click(await screen.findByRole("button",{name:"撤回此申请"}));
  await screen.findByText("申请已撤回；后续执行和重试已禁止。已发出的材料无法收回。");
  expect(screen.queryByRole("button",{name:"明确执行核验"})).not.toBeInTheDocument();
  view.unmount();render(<CheckPanel document={document} onRevisionBasis={vi.fn()}/>);
  await screen.findByText("该申请已撤回；重新联网需要新申请及重新确认。");
  expect(screen.queryByRole("button",{name:"明确执行核验"})).not.toBeInTheDocument();
  expect(bridge.call.mock.calls.filter(([op])=>op==="document_check_execute")).toHaveLength(1);
 });
 it.each(["resolve","reject"])("SIMULATED: active withdrawal remains visible after late execution %s",async(late)=>{
  let records:any[]=[check];let resolve!:(value:unknown)=>void;let reject!:(reason:Error)=>void;
  const event={...check,check_id:"withdrawal",actor:"human",status:"unverified",execution_state:"withdrawn",reason:"egress_withdrawn",event_kind:"egress_control",control:"withdraw_request",target_request_check_id:"c"};
  const receipt={...check,check_id:"terminal",request_check_id:"c",attempt_id:"doccheck_active",retry_of_task_id:null,status:"faithful",execution_state:"executed",execution_verified:true,engine_receipt:{provider:"fixture",requested_model:"fixture",model:"fixture",prompt_sha256:"a".repeat(64),response_sha256:"b".repeat(64),tokens_used:null,finish_reason:"stop"},retrieval_receipts:[]};
  bridge.call.mockImplementation(async(op:string,p:any)=>{
   if(op==="document_checks")return {document_id:"d",version:2,content_sha256:"hash",historical:false,default_status:"unverified",checks_capped:false,next_offset:null,checks:records};
   if(p.body.preview)return preview();
   if(p.body.withdraw){records=[check,event];return event;}
   return new Promise((yes,no)=>{resolve=yes;reject=no;});
  });
  render(<CheckPanel document={document} onRevisionBasis={vi.fn()}/>);const user=userEvent.setup();
  await user.click(await screen.findByRole("button",{name:"明确执行核验"}));
  await user.click(await screen.findByRole("button",{name:"确认这些材料并执行"}));
  await waitFor(()=>expect(resolve).toBeTypeOf("function"));
  expect(screen.getByRole("button",{name:"撤回此申请"})).toBeEnabled();
  await user.click(screen.getByRole("button",{name:"撤回此申请"}));
  await screen.findByText("申请已撤回；后续执行和重试已禁止。已发出的材料无法收回。");
  await act(async()=>{if(late==="resolve")resolve(receipt);else reject(new Error("synthetic lost ACK"));});
  expect(screen.getByText("申请已撤回；后续执行和重试已禁止。已发出的材料无法收回。")).toBeInTheDocument();
  expect(screen.queryByText(/真实核验任务已执行/)).not.toBeInTheDocument();
  expect(screen.queryByText(/执行回执未确认/)).not.toBeInTheDocument();
  expect(screen.queryByRole("button",{name:"明确执行核验"})).not.toBeInTheDocument();
  expect(bridge.call.mock.calls.filter(([op,p])=>op==="document_check_execute"&&p.body.confirmed_egress_sha256)).toHaveLength(1);
  expect(bridge.call.mock.calls.some(([op])=>op==="knowledge_review"||op==="document_draft")).toBe(false);
 });
 it("SIMULATED: returning to a document cannot revive its discarded confirmation",async()=>{
  bridge.call.mockImplementation(async(op:string,p:any)=>op==="document_check_execute"?preview():{
   document_id:p.document_id,version:p.version,content_sha256:p.document_id==="d"?"hash":"newhash",historical:false,default_status:"unverified",checks_capped:false,next_offset:null,checks:p.document_id==="d"?[check]:[]});
  const view=render(<CheckPanel document={document} onRevisionBasis={vi.fn()}/>);
  await userEvent.setup().click(await screen.findByRole("button",{name:"明确执行核验"}));
  expect(await screen.findByLabelText("本次外发确认")).toBeInTheDocument();
  view.rerender(<CheckPanel document={{...document,document_id:"new",version:3,content_sha256:"newhash"}} onRevisionBasis={vi.fn()}/>);
  await waitFor(()=>expect(screen.getAllByText("该版本尚无核验记录。")).toHaveLength(2));
  view.rerender(<CheckPanel document={document} onRevisionBasis={vi.fn()}/>);
  await screen.findByRole("button",{name:"明确执行核验"});
  expect(screen.queryByLabelText("本次外发确认")).not.toBeInTheDocument();
  expect(bridge.call.mock.calls.filter(([op])=>op==="document_check_execute")).toHaveLength(1);
 });
 it("SIMULATED: a failed replacement preview clears the previous confirmation",async()=>{
  let previews=0;
  bridge.call.mockImplementation(async(op:string)=>{
   if(op==="document_checks")return {document_id:"d",version:2,content_sha256:"hash",historical:false,default_status:"unverified",checks_capped:false,next_offset:null,checks:[check]};
   if(++previews===1)return preview();throw new Error("preview unavailable");
  });
  render(<CheckPanel document={document} onRevisionBasis={vi.fn()}/>);const user=userEvent.setup();
  await user.click(await screen.findByRole("button",{name:"明确执行核验"}));
  expect(await screen.findByLabelText("本次外发确认")).toBeInTheDocument();
  await user.click(screen.getByRole("button",{name:"明确执行核验"}));
  await screen.findByText(/执行回执未确认/);
  expect(screen.queryByRole("button",{name:"确认这些材料并执行"})).not.toBeInTheDocument();
  expect(bridge.call.mock.calls.filter(([op])=>op==="document_check_execute").every(([,p])=>p.body.preview===true)).toBe(true);
 });
 it.each(["dimension","material","destination","scope","plan_identity"])("SIMULATED: rejects inconsistent preview %s",async(field)=>{
  const value=preview();
  if(field==="dimension")value.dimension="professional_basis";
  if(field==="material")value.egress_plan.document_text.bytes=1;
  if(field==="destination")value.egress_plan.model_destination="https://changed.invalid/v1";
  if(field==="scope")value.egress_plan.scope="unrecognized";
  if(field==="plan_identity")value.egress_plan.document_id="foreign";
  bridge.call.mockImplementation(async(op:string)=>op==="document_check_execute"?value:{document_id:"d",version:2,content_sha256:"hash",historical:false,default_status:"unverified",checks_capped:false,next_offset:null,checks:[check]});
  render(<CheckPanel document={document} onRevisionBasis={vi.fn()}/>);
  await userEvent.setup().click(await screen.findByRole("button",{name:"明确执行核验"}));
  await screen.findByText(/执行回执未确认/);
  expect(screen.queryByRole("button",{name:"确认这些材料并执行"})).not.toBeInTheDocument();
 });
 it("SIMULATED: reloaded terminal keeps the selected excerpt scope visible",async()=>{
  const item={...preview({...check,dimension:"professional_basis"},"正文","selected_text"),check_id:"terminal",request_check_id:"c",attempt_id:"doccheck_failed",actor:"machine",status:"failed",execution_state:"failed",reason:"worker_failed"};
  bridge.call.mockResolvedValue({document_id:"d",version:2,content_sha256:"hash",historical:false,default_status:"unverified",checks_capped:false,next_offset:null,checks:[item]});
  render(<CheckPanel document={document} onRevisionBasis={vi.fn()}/>);
  expect(await screen.findByText("核验范围：仅限所选片段，不代表全文")).toBeInTheDocument();
  expect(screen.getByText("正文")).toBeInTheDocument();
 });
 it("SIMULATED: preview cancellation does not execute or adopt knowledge",async()=>{
  bridge.call.mockImplementation(async(op:string,payload:any)=>{
   if(op==="document_checks")return {document_id:"d",version:2,content_sha256:"hash",historical:false,default_status:"unverified",checks_capped:false,next_offset:null,checks:[check]};
   expect(payload.body.preview).toBe(true);
   return preview();
  });
  render(<CheckPanel document={document} onRevisionBasis={vi.fn()}/>);const user=userEvent.setup();
  await user.click(await screen.findByRole("button",{name:"明确执行核验"}));
  expect(await screen.findByLabelText("本次外发确认")).toBeInTheDocument();
  await user.click(screen.getByRole("button",{name:"取消本次外发"}));
  expect(screen.queryByLabelText("本次外发确认")).not.toBeInTheDocument();
  expect(bridge.call.mock.calls.filter(([op])=>op==="document_check_execute")).toHaveLength(1);
  expect(bridge.call.mock.calls.some(([op])=>op==="knowledge_review")).toBe(false);
 });
 it("SIMULATED: records the exact independent query without executing it",async()=>{
  let records:any[]=[];
  bridge.call.mockImplementation(async(op:string,payload:any)=>{
   if(op==="document_checks")return {document_id:"d",version:2,content_sha256:"hash",historical:false,default_status:"unverified",checks_capped:false,next_offset:null,checks:records};
   if(op!=="document_check_record")throw new Error("unexpected execution");
   const value={...check,dimension:payload.body.dimension,search_query:payload.body.search_query};records=[value];return value;
  });
  render(<CheckPanel document={document} onRevisionBasis={vi.fn()}/>);
  const user=userEvent.setup();
  await user.type(screen.getByLabelText("独立公开查询"),"public terminology");
  await user.click(screen.getByRole("button",{name:"申请专业云端核验"}));
  expect(await screen.findByText("本次独立公开查询：public terminology")).toBeInTheDocument();
  expect(bridge.call).toHaveBeenCalledWith("document_check_record",{document_id:"d",body:{version:2,dimension:"professional_basis",provider_mode:"cloud",search_query:"public terminology"}});
  expect(bridge.call.mock.calls.some(([op])=>op==="document_check_execute")).toBe(false);
 });
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
 it("SIMULATED: confirmed failed execution and retry retain request and attempt identity",async()=>{
  let checks:any[]=[check];let n=0;
  bridge.call.mockImplementation(async(op:string,payload:any)=>{
   if(op==="document_checks")return {document_id:"d",version:2,content_sha256:"hash",historical:false,default_status:"unverified",checks_capped:false,next_offset:null,checks};
   if(op!=="document_check_execute")throw new Error("unexpected operation");
   if(payload.body.preview)return preview();
   const previous=n?"doccheck_1":null;n++;
   const receipt={...check,check_id:`terminal_${n}`,request_check_id:"c",attempt_id:`doccheck_${n}`,retry_of_task_id:previous,status:"failed",reason:"worker_failed",actor:"machine",execution_state:"failed",execution_verified:false,engine_receipt:null,retrieval_receipts:[]};checks=[receipt];return receipt;
  });
  render(<CheckPanel document={document} onRevisionBasis={vi.fn()}/>);const user=userEvent.setup();
  await user.click(await screen.findByRole("button",{name:"明确执行核验"}));
  await user.click(await screen.findByRole("button",{name:"确认这些材料并执行"}));
  expect(await screen.findByText(/核验执行失败：worker_failed/)).toBeInTheDocument();
  expect(bridge.call).toHaveBeenCalledWith("document_check_execute",{document_id:"d",body:{check_id:"c",expected_content_sha256:"hash",confirmed_egress_sha256:"a".repeat(64)}});
  await user.click(await screen.findByRole("button",{name:"明确重试执行核验"}));
  await user.click(await screen.findByRole("button",{name:"确认这些材料并执行"}));
  expect(bridge.call).toHaveBeenCalledWith("document_check_execute",{document_id:"d",body:{check_id:"c",expected_content_sha256:"hash",retry_of_task_id:"doccheck_1",confirmed_egress_sha256:"a".repeat(64)}});
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
  release(preview());
  await new Promise(resolve=>setTimeout(resolve,20));
  expect(screen.queryByLabelText("本次外发确认")).not.toBeInTheDocument();expect(screen.getAllByText("该版本尚无核验记录。")).toHaveLength(2);
 });

 it("SIMULATED: dimension-specific executed verdicts remain distinct from human approval",()=>{
  const engine={provider:"configured-fixture",requested_model:"fixture-v1",model:"fixture-v1",prompt_sha256:"a".repeat(64),response_sha256:"b".repeat(64),tokens_used:12,finish_reason:"stop"};
  const executed={...check,execution_verified:true,execution_state:"executed",engine_receipt:engine,retrieval_receipts:[]};
  for(const status of ["faithful","mismatch","uncertain","original_unclear","conflicting"]){expect(checkExecutionLabel({...executed,status} as any)).toMatch(/真实核验任务已执行/);}
  for(const status of ["supported","refuted","uncertain","conflicting"]){expect(checkExecutionLabel({...executed,dimension:"professional_basis",status} as any)).toMatch(/专业依据与真人认可分别记录/);}
  expect(checkExecutionLabel({...executed,dimension:"professional_basis",status:"supported",egress_plan:{scope:"selected_text"}} as any)).toMatch(/只适用于所选片段，不代表全文/);
  expect(()=>checkExecutionLabel({...executed,status:"supported"} as any)).toThrow();
  expect(()=>checkExecutionLabel({...executed,status:"faithful",engine_receipt:{...engine,model:"unknown"}} as any)).toThrow();
  expect(()=>checkExecutionLabel({...executed,status:"faithful",engine_receipt:{...engine,tokens_used:null}} as any)).not.toThrow();
  expect(()=>checkExecutionLabel({...executed,status:"faithful",engine_receipt:{...engine,tokens_used:-1}} as any)).toThrow();
  expect(()=>checkExecutionLabel({...executed,status:"faithful",execution_verified:false} as any)).toThrow();
  expect(checkExecutionLabel({...check,status:"failed",execution_state:"failed",reason:"retrieval_empty",reported_status:"uncertain"} as any)).toMatch(/失败当作内容判断/);
 });
 it("SIMULATED: a durable manual record is not announced as unconfirmed when only its readback fails",async()=>{
  let reads=0;
  bridge.call.mockImplementation(async(op:string)=>{
   if(op==="document_checks"){reads++;if(reads>1)throw new Error("readback unavailable");return {document_id:"d",version:2,content_sha256:"hash",historical:false,default_status:"unverified",checks_capped:false,next_offset:null,checks:[]};}
   if(op==="document_check_record")return {...check,dimension:"professional_basis",provider_mode:"manual",status:"uncertain",execution_state:"not_executed",execution_verified:false};
   throw new Error("unexpected operation");
  });
  render(<CheckPanel document={document} onRevisionBasis={vi.fn()}/>);
  const user=userEvent.setup();
  await user.click(within(screen.getByLabelText("专业依据")).getByRole("button",{name:"明确提交手动核验记录"}));
  expect(await screen.findByText(/核验记录已保存/)).toBeInTheDocument();
  expect(screen.queryByText(/核验记录未确认/)).not.toBeInTheDocument();
  expect(bridge.call.mock.calls.filter(([op])=>op==="document_check_record")).toHaveLength(1);
 });
 it.each([null,0,12])("SIMULATED: executed uncertainty with token usage %s remains independent of retry and admission",async(tokens)=>{
  let checks:any[]=[check];
  const receipt={...check,check_id:"terminal",request_check_id:"c",attempt_id:"doccheck_verified",retry_of_task_id:null,status:"uncertain",execution_state:"executed",execution_verified:true,engine_receipt:{provider:"configured-fixture",requested_model:"fixture-v1",model:"fixture-v1",prompt_sha256:"a".repeat(64),response_sha256:"b".repeat(64),tokens_used:tokens,finish_reason:"stop"},retrieval_receipts:[]};
  bridge.call.mockImplementation(async(op:string,payload:any)=>{if(op==="document_checks")return {document_id:"d",version:2,content_sha256:"hash",historical:false,default_status:"unverified",checks_capped:false,next_offset:null,checks};if(op==="document_check_execute"){if(payload.body.preview)return preview();checks=[receipt];return receipt;}throw new Error("unexpected operation");});
  render(<CheckPanel document={document} onRevisionBasis={vi.fn()}/>);
  await userEvent.setup().click(await screen.findByRole("button",{name:"明确执行核验"}));
  await userEvent.setup().click(await screen.findByRole("button",{name:"确认这些材料并执行"}));
  expect(await screen.findByText(/真实核验任务已执行：不确定/)).toBeInTheDocument();
  expect(await screen.findByText(`供应商用量：${tokens===null?"未知":`${tokens} tokens`}；费用：未知。`)).toBeInTheDocument();
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
  if(nextOffset===null){await userEvent.setup().click(screen.getByRole("button",{name:"明确重试执行核验"}));expect(bridge.call).toHaveBeenCalledWith("document_check_execute",{document_id:"d",body:{check_id:"c",expected_content_sha256:"hash",retry_of_task_id:"doccheck_latest",preview:true}});}
  else expect(screen.queryByRole("button",{name:"明确重试执行核验"})).not.toBeInTheDocument();
 });

});
