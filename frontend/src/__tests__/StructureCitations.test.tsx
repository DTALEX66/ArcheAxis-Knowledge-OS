import {beforeEach,describe,expect,it,vi} from "vitest";
import {render,screen,waitFor} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {StructureCitations} from "../components/StructureCitations";
import {utf8Sha256} from "../components/TranscriptionCues";
const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const revision="a".repeat(64),node={kind:"paragraph",path:["paragraph-1"],char_start:0,char_end:2};
async function output(kind:string,content:string){return {content,metadata:{kind,sha256:await utf8Sha256(content),byte_length:new TextEncoder().encode(content).length}};}
describe("SIMULATED structure citations",()=>{
 beforeEach(()=>{bridge.call.mockReset();});
 it.each(["worker_structure","format_location"].flatMap(kind=>["valid","source","failed","digest","position","checksum","resolution","second","out-of-range","preview-change"].map(mutation=>[kind,mutation] as const)))("%s %s preserves explicit task and source boundaries",async (kind,mutation)=>{
  const text=await output("text","甲😀乙"),structure=await output("document_structure",JSON.stringify([node,{...node,path:["paragraph-2"],char_start:2,char_end:3}])),loss=await output("loss_report",JSON.stringify({params:{worker_structure:[node,{...node,path:["paragraph-2"],char_start:2,char_end:3}],format:{locations:[{kind:"json_value",path:"$.lesson.title",value:"甲😀"},{kind:"json_value",path:"$.lesson.second",value:"乙"}]}}}));
  if(mutation==="digest")text.metadata.sha256="b".repeat(64);
  bridge.call.mockImplementation(async(op:string,payload:any)=>{
   if(op==="jobs_get")return {job_id:"job",input_ref:mutation==="source"?"other":"source",state:mutation==="failed"?"failed":"succeeded",attempt:2};
   if(op==="job_output")return {text,document_structure:structure,loss_report:loss}[payload.kind as "text"];
   if(op==="anchor_create")return {anchor_id:"anchor",source_id:"source",source_revision:revision,location_status:"located",position:JSON.stringify({...JSON.parse(payload.body.position),attempt:mutation==="position"?3:2,checksum:mutation==="checksum"?"wrong":payload.body.checksum})};
   if(op==="anchor_resolve")return {anchor_id:"anchor",source_id:mutation==="resolution"?"other":"source",source_revision:revision,current_source_revision:revision,status:"CURRENT",scope:"locator_provenance_only"};
   throw new Error(`unexpected operation ${op}`);
  });
  const adopted=vi.fn();render(<StructureCitations sourceId="source" revision={revision} jobId="job" kind={kind as "worker_structure"|"format_location"} onAnchor={adopted}/>);
  expect(bridge.call).not.toHaveBeenCalled();
  if(mutation==="second"||mutation==="out-of-range"){await userEvent.clear(screen.getByRole("spinbutton",{name:"引用位置序号"}));await userEvent.type(screen.getByRole("spinbutton",{name:"引用位置序号"}),mutation==="second"?"2":"99");}
  if(mutation==="valid"||mutation==="second"||mutation==="preview-change"){await userEvent.click(screen.getByRole("button",{name:"预览所选引用"}));expect(await screen.findByLabelText("所选引用预览")).toHaveTextContent(mutation==="second"?"乙":"甲😀");expect(bridge.call.mock.calls.some(([op])=>op==="anchor_create")).toBe(false);}
  if(mutation==="preview-change"){Object.assign(text,await output("text","丙😀乙"));Object.assign(loss,await output("loss_report",JSON.stringify({params:{worker_structure:[node],format:{locations:[{kind:"json_value",path:"$.lesson.title",value:"丙😀"}]}}})));}
  await userEvent.click(screen.getByRole("button",{name:"引用所选结构位置"}));
  if(mutation==="valid"||mutation==="second"){
   // Preview already created this status element; wait for the saved state.
   await waitFor(()=>expect(screen.getByRole("status")).toHaveTextContent("已保存并解析"));expect(adopted).toHaveBeenCalledOnce();
   const body=bridge.call.mock.calls.find(([op])=>op==="anchor_create")![1].body;
   expect(body.checksum).toBe(await utf8Sha256(mutation==="second"?"乙":"甲😀"));expect(JSON.parse(body.position)).toEqual(kind==="format_location"?{type:kind,job_id:"job",attempt:2,kind:"json_value",path:mutation==="second"?"$.lesson.second":"$.lesson.title"}:{type:kind,job_id:"job",attempt:2,kind:"paragraph",path:mutation==="second"?["paragraph-2"]:["paragraph-1"]});
  }else{await waitFor(()=>expect(screen.getByRole("status")).toHaveTextContent("未确认"));expect(adopted).not.toHaveBeenCalled();}
  if(["source","failed","digest","out-of-range","preview-change"].includes(mutation))expect(bridge.call.mock.calls.some(([op])=>op==="anchor_create")).toBe(false);
  expect(bridge.call.mock.calls.some(([op])=>String(op).startsWith("knowledge_")||op==="document_draft")).toBe(false);
 });
});




