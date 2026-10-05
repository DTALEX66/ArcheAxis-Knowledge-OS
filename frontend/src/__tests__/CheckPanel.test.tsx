import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CheckPanel } from "../components/CheckPanel";
import type { DocumentDto } from "../api/generated/core-contract";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const document:DocumentDto={document_id:"d",source_id:null,source_revision:null,title:"原创",version:2,content_sha256:"hash",editor_json:{type:"doc"},text_projection:"正文",blocks:[]};
const check={check_id:"c",document_id:"d",version:2,content_sha256:"hash",dimension:"recognition_fidelity",provider_mode:"cloud",status:"pending",actor:"human",execution_verified:false,execution_state:"not_executed",reason:"worker_not_configured"};
describe("independent document checks",()=>{
 beforeEach(()=>{bridge.call.mockReset();});
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
  await userEvent.setup().click(screen.getByRole("button",{name:"申请或重试识别云端核验"}));
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
});
