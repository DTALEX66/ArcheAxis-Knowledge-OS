import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createHash, webcrypto } from "node:crypto";
import { JobContent } from "../components/JobContent";
import { outputReceipt } from "./fixtures/jobContentCoreFixture";

const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));

type NativeLocation={kind:string;path:string;value:string;[key:string]:unknown};
const examples:ReadonlyArray<readonly [string,NativeLocation]>=[
 ["tsv",{kind:"table_cell",path:"tsv!B2",value:"6371",row:2,column:2,coordinate:"B2"}],
 ["jsonl",{kind:"object_path",path:"/radius",value:"6371",record:1}],
 ["yaml",{kind:"object_path",path:"/radius",value:"6371"}],
 ["yml",{kind:"object_path",path:"/radius",value:"6371"}],
 ["toml",{kind:"object_path",path:"/radius",value:"6371"}],
 ["xml",{kind:"xml_path",path:"/earth[1]/radius[1]",value:"6371"}],
 ["eml",{kind:"mail_mime_part",path:"/parts/1",value:"半径 6371 千米"}],
 ["odt",{kind:"odf_paragraph",path:"paragraph",value:"半径 6371 千米",position:1}],
 ["ods",{kind:"odf_table_cell",path:"Earth/r2c2",value:"6371",sheet:"Earth",row:2,column:2}],
 ["odp",{kind:"odf_page",path:"Earth",value:"Earth",position:1}],
 ["rtf",{kind:"rtf_paragraph",path:"/paragraphs/1",value:"半径 6371 千米",position:1}],
 ["py",{kind:"python_symbol",path:"/symbols/load",value:"def load():",symbol_kind:"function",line:1}],
];
const revision=createHash("sha256").update("SIMULATED original source bytes").digest("hex");
const sourceId="light-format-source",jobId="saved-light-format",attempt=2;
type Controls={locations:unknown;state:string;sourceId:string;driftHash:boolean;refuseAnchor:boolean};

beforeEach(()=>{bridge.call.mockReset();vi.stubGlobal("crypto",webcrypto);vi.stubGlobal("__TAURI__",undefined);});
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllGlobals();});

function savedTransport(extension:string,node:NativeLocation){
 const body=`Extracted value: ${node.value}\n`;
 const controls:Controls={locations:[node],state:"succeeded",sourceId,driftHash:false,refuseAnchor:false};
 bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>={})=>{
  if(op==="capabilities_list")return {};
  if(op==="source_jobs")return {source_id:sourceId,jobs:[{job_id:jobId,kind:"text",input_ref:sourceId,state:"succeeded",attempt}],jobs_capped:false};
  if(op==="jobs_get")return {job_id:jobId,kind:"text",input_ref:controls.sourceId,state:controls.state,attempt,request_id:"saved-request"};
  if(op==="job_output"){
   const content=p.kind==="text"?body:JSON.stringify(p.kind==="loss_report"
    ?{engine:"python-worker-text",engine_version:"0.1.0",params:{format:{format:extension,parsed:true,locations:controls.locations}},loss_note:"SIMULATED native values; no visual layout claim"}
    :[{kind:"line",path:["line-1"],char_start:0,char_end:Array.from(body).length}]);
   const output=outputReceipt(p.kind,content);
   if(controls.driftHash&&p.kind==="loss_report")output.metadata.sha256="f".repeat(64);
   return output;
  }
  if(op==="job_quality")return {job_id:jobId,loss_count:1};
  if(op==="source_job_transform")return {source_id:sourceId,job_id:jobId,raw_sha256:revision,transform_id:1,content:body};
  if(op==="anchor_create"){
   if(controls.refuseAnchor)throw new Error("SIMULATED Core refuses ambiguous native location");
   const input=p.body as {revision:string;position:string;checksum:string};
   return {anchor_id:"saved-anchor",source_id:sourceId,source_revision:input.revision,location_status:"located",position:JSON.stringify({...JSON.parse(input.position),checksum:input.checksum})};
  }
  if(op==="anchor_resolve")return {anchor_id:"saved-anchor",source_id:sourceId,source_revision:revision,current_source_revision:revision,status:"CURRENT",scope:"locator_provenance_only"};
  throw new Error(`Unexpected mock operation: ${op}`);
 });
 return {controls,body};
}

it.each(examples)("SIMULATED: %s reader previews and saves its existing native location bound to the original and exact job",async(extension,node)=>{
 const {body}=savedTransport(extension,node);const adopted=vi.fn();
 render(<JobContent sourceId={sourceId} sourceRevision={revision} name={`source.${extension}`} readOnly onAnchor={adopted}/>);
 expect(await screen.findByLabelText("Core 提取正文")).toHaveTextContent(body.trim());
 fireEvent.click(screen.getByRole("button",{name:"预览所选引用"}));
 expect(await screen.findByLabelText("所选引用预览")).toHaveTextContent(node.path);
 expect(screen.getByLabelText("所选引用预览")).toHaveTextContent(node.value);
 expect(bridge.call.mock.calls.some(([op])=>op==="anchor_create")).toBe(false);
 fireEvent.click(screen.getByRole("button",{name:"引用所选结构位置"}));
 await waitFor(()=>expect(adopted).toHaveBeenCalledOnce());
 expect(bridge.call).toHaveBeenCalledWith("anchor_create",{source_id:sourceId,body:{revision,
  position:JSON.stringify({type:"format_location",job_id:jobId,attempt,kind:node.kind,path:node.path}),
  checksum:createHash("sha256").update(node.value).digest("hex")}});
 expect(bridge.call).toHaveBeenCalledWith("anchor_resolve",{source_id:sourceId,anchor_id:"saved-anchor"});
 expect(bridge.call.mock.calls.filter(([op])=>["job_enqueue","job_execute","document_draft","knowledge_create"].includes(op))).toHaveLength(0);
});

it.each(["missing","empty","unknown-shape","non-text-scalar"])("SIMULATED: %s native locations preserve readable body without inventing a citation",async fault=>{
 const [extension,node]=examples[7];const {controls}=savedTransport(extension,node);
 controls.locations=fault==="missing"?undefined:fault==="empty"?[]:fault==="non-text-scalar"?[{kind:"object_path",path:"/radius",value:6371}]:[{kind:"unknown",path:["not-a-native-value-path"],value:node.value}];
 render(<JobContent sourceId={sourceId} sourceRevision={revision} name={`source.${extension}`} readOnly/>);
 await screen.findByLabelText("Core 提取正文");
 fireEvent.click(screen.getByRole("button",{name:"预览所选引用"}));
 await screen.findByText("结构位置引用未确认；保留原件和任务结果后重试。");
 expect(screen.queryByLabelText("所选引用预览")).not.toBeInTheDocument();
 expect(bridge.call.mock.calls.some(([op])=>op==="anchor_create"||op==="job_execute")).toBe(false);
});

it.each(["source-drift","unknown-task","output-digest"])("SIMULATED: %s during explicit citation read refuses any location write",async fault=>{
 const [extension,node]=examples[8];const {controls}=savedTransport(extension,node);
 render(<JobContent sourceId={sourceId} sourceRevision={revision} name={`source.${extension}`} readOnly/>);
 await screen.findByLabelText("Core 提取正文");
 if(fault==="source-drift")controls.sourceId="other-original";
 else if(fault==="unknown-task")controls.state="unknown";
 else controls.driftHash=true;
 fireEvent.click(screen.getByRole("button",{name:"引用所选结构位置"}));
 await screen.findByText("结构位置引用未确认；保留原件和任务结果后重试。");
 expect(bridge.call.mock.calls.some(([op])=>op==="anchor_create"||op==="job_execute")).toBe(false);
});

it("SIMULATED: repeated JSONL paths use their reported record to save the selected original location once",async()=>{
 const [extension,node]=examples[1];const {controls}=savedTransport(extension,node);controls.locations=[node,{...node,record:2}];
 const adopted=vi.fn();render(<JobContent sourceId={sourceId} sourceRevision={revision} name="source.jsonl" readOnly onAnchor={adopted}/>);
 await screen.findByLabelText("Core 提取正文");
 fireEvent.change(screen.getByRole("spinbutton",{name:"引用位置序号"}),{target:{value:"2"}});
 fireEvent.click(screen.getByRole("button",{name:"引用所选结构位置"}));
 await waitFor(()=>expect(adopted).toHaveBeenCalledOnce());
 expect(bridge.call).toHaveBeenCalledWith("anchor_create",{source_id:sourceId,body:{revision,
  position:JSON.stringify({type:"format_location",job_id:jobId,attempt,kind:node.kind,path:node.path,where:{record:2}}),
  checksum:createHash("sha256").update(node.value).digest("hex")}});
 expect(bridge.call.mock.calls.filter(([op])=>op==="anchor_create")).toHaveLength(1);
 expect(bridge.call).toHaveBeenCalledWith("anchor_resolve",{source_id:sourceId,anchor_id:"saved-anchor"});
 expect(bridge.call.mock.calls.some(([op])=>op==="job_execute")).toBe(false);
});
