import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createHash, webcrypto } from "node:crypto";
import { StructureCitations } from "../components/StructureCitations";
import { outputReceipt } from "./fixtures/jobContentCoreFixture";

const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
type Entry=Record<string,unknown>;
type Controls={entries:Entry[];text:string;lossNote:string;omitWhere:boolean;whereFault?:"extra"|"wrong-value"|"wrong-type";readGate?:Promise<void>;writeGate?:Promise<void>};
const revision="a".repeat(64),sourceId="original-source",jobId="saved-job";
const cases:ReadonlyArray<readonly [string,Entry[],Entry]>=[
 ["JSONL equal text in different records",[{kind:"object_path",path:"/name",value:"same",record:1},{kind:"object_path",path:"/name",value:"same",record:2}],{record:2}],
 ["ODF equal paragraphs in different positions",[{kind:"odf_paragraph",path:"paragraph",value:"same",position:1},{kind:"odf_paragraph",path:"paragraph",value:"same",position:2}],{position:2}],
 ["Python equal names on different lines",[{kind:"python_symbol",path:"/symbols/import",value:"import os",name:"os",line:1,symbol_kind:"import"},{kind:"python_symbol",path:"/symbols/import",value:"import os",name:"os",line:3,symbol_kind:"import"}],{name:"os",line:3,symbol_kind:"import"}],
];
beforeEach(()=>{
 bridge.call.mockReset();vi.stubGlobal("crypto",webcrypto);
 // Real SHA-256 bytes with deterministic Promise settlement, so act drains the
 // deliberately late reads instead of relying on native crypto thread timing.
 vi.spyOn(webcrypto.subtle,"digest").mockImplementation(async(algorithm,data)=>{
  if(algorithm!=="SHA-256")throw new Error("unexpected digest algorithm");
  const bytes=ArrayBuffer.isView(data)?new Uint8Array(data.buffer,data.byteOffset,data.byteLength):new Uint8Array(data);
  return Uint8Array.from(createHash("sha256").update(bytes).digest()).buffer;
 });
});
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllGlobals();});

function transport(entries:Entry[]):Controls {
 const controls:Controls={entries:structuredClone(entries),text:entries.map(entry=>String(entry.value)).join("\n"),lossNote:"SIMULATED worker receipt",omitWhere:false};
 bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>)=>{
  if(op==="jobs_get"){
   if(controls.readGate)await controls.readGate;
   return {job_id:jobId,input_ref:sourceId,state:"succeeded",attempt:2};
  }
  if(op==="job_output")return outputReceipt(p.kind,p.kind==="text"?controls.text:JSON.stringify(p.kind==="loss_report"
   ?{params:{format:{locations:controls.entries}},loss_note:controls.lossNote}
   :[{kind:"line",path:["line-1"],char_start:0,char_end:Array.from(controls.text).length}]));
  if(op==="anchor_create"){
   const body=p.body as {revision:string;position:string;checksum:string};
   const position=JSON.parse(body.position) as Record<string,unknown>;
   // Core serializes serde_json maps in key order, not UI insertion order.
   if(position.where){
    const where=Object.fromEntries(Object.entries(position.where as Entry).sort(([left],[right])=>left<right?-1:left>right?1:0));
    if(controls.whereFault==="extra")where.unrequested="extra";
    if(controls.whereFault==="wrong-value")where.record=99;
    if(controls.whereFault==="wrong-type")where.record="2";
    position.where=where;
   }
   if(controls.omitWhere)delete position.where;
   if(controls.writeGate)await controls.writeGate;
   return {anchor_id:"anchor",source_id:sourceId,source_revision:body.revision,location_status:"located",position:JSON.stringify({...position,checksum:body.checksum})};
  }
  if(op==="anchor_resolve")return {anchor_id:"anchor",source_id:sourceId,source_revision:revision,current_source_revision:revision,status:"CURRENT",scope:"locator_provenance_only"};
  throw new Error(`Unexpected mock operation: ${op}`);
 });
 return controls;
}
function show(adopted=vi.fn()){
 return render(<StructureCitations sourceId={sourceId} revision={revision} jobId={jobId} kind="format_location" onAnchor={adopted}/>);
}
function second(){fireEvent.change(screen.getByRole("spinbutton",{name:"引用位置序号"}),{target:{value:"2"}});}
function preview(){fireEvent.click(screen.getByRole("button",{name:"预览所选引用"}));}
function save(){fireEvent.click(screen.getByRole("button",{name:"引用所选结构位置"}));}
function hasWrite(){return bridge.call.mock.calls.some(([op])=>op==="anchor_create");}

it.each(cases)("SIMULATED: %s uses only reported fields to preserve selected identity across preview, write and resolution",async(_label,entries,where)=>{
 transport(entries);const adopted=vi.fn();show(adopted);second();preview();
 expect(await screen.findByLabelText("所选引用预览")).toHaveTextContent(String(entries[1].value));
 expect(hasWrite()).toBe(false);save();
 await waitFor(()=>expect(adopted).toHaveBeenCalledOnce());
 expect(bridge.call).toHaveBeenCalledWith("anchor_create",{source_id:sourceId,body:{revision,
  position:JSON.stringify({type:"format_location",job_id:jobId,attempt:2,kind:entries[1].kind,path:entries[1].path,where}),
  checksum:createHash("sha256").update(String(entries[1].value)).digest("hex")}});
 expect(bridge.call).toHaveBeenCalledWith("anchor_resolve",{source_id:sourceId,anchor_id:"anchor"});
});

it("SIMULATED: completely repeated entries cannot be selected by UI ordinal",async()=>{
 const node={kind:"odf_paragraph",path:"paragraph",value:"same",position:1};transport([node,{...node}]);show();second();preview();
 await screen.findByText("结构位置引用未确认；保留原件和任务结果后重试。");
 expect(screen.queryByLabelText("所选引用预览")).not.toBeInTheDocument();expect(hasWrite()).toBe(false);
});

it("SIMULATED: uniqueness includes a matching entry whose value cannot be displayed",async()=>{
 transport([{kind:"object_path",path:"/name",value:"same"},{kind:"object_path",path:"/name",value:123}]);show();save();
 await screen.findByText("结构位置引用未确认；保留原件和任务结果后重试。");
 expect(hasWrite()).toBe(false);
});

it("SIMULATED: a reported discriminator changing after preview refuses the write",async()=>{
 const controls=transport(cases[0][1]);show();second();preview();await screen.findByLabelText("所选引用预览");
 controls.entries[1].record=3;save();
 await screen.findByText("结构位置引用未确认；保留原件和任务结果后重试。");expect(hasWrite()).toBe(false);
});

it("SIMULATED: changed output bytes are not accepted as the previously previewed receipt",async()=>{
 const controls=transport(cases[0][1]);show();second();preview();await screen.findByLabelText("所选引用预览");
 controls.lossNote="different receipt, same selected value";save();
 await screen.findByText("结构位置引用未确认；保留原件和任务结果后重试。");expect(hasWrite()).toBe(false);
});

it("SIMULATED: an ACK omitting the exact where selector is not adopted or resolved",async()=>{
 const controls=transport(cases[0][1]);controls.omitWhere=true;const adopted=vi.fn();show(adopted);second();save();
 await screen.findByText("结构位置引用未确认；保留原件和任务结果后重试。");
 expect(adopted).not.toHaveBeenCalled();expect(bridge.call.mock.calls.some(([op])=>op==="anchor_resolve")).toBe(false);
});

it.each(["extra","wrong-value","wrong-type"] as const)("SIMULATED: ACK where %s is rejected despite carrying the expected path and text checksum",async fault=>{
 const controls=transport(cases[0][1]);controls.whereFault=fault;const adopted=vi.fn();show(adopted);second();save();
 await screen.findByText("结构位置引用未确认；保留原件和任务结果后重试。");
 expect(adopted).not.toHaveBeenCalled();expect(bridge.call.mock.calls.some(([op])=>op==="anchor_resolve")).toBe(false);
});

it("SIMULATED: a late read from the old source cannot publish a preview or dispatch a write",async()=>{
 const controls=transport(cases[0][1]);let release!:()=>void;controls.readGate=new Promise<void>(resolve=>{release=resolve;});
 const view=show();second();preview();
 await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("jobs_get",{job_id:jobId}));
 view.rerender(<StructureCitations sourceId="new-source" revision={"b".repeat(64)} jobId="new-job" kind="format_location"/>);
 await act(async()=>{release();await controls.readGate;});
 expect(screen.queryByLabelText("所选引用预览")).not.toBeInTheDocument();expect(hasWrite()).toBe(false);
});

it("SIMULATED: a late write ACK from the old source is not adopted or followed by resolution",async()=>{
 const controls=transport(cases[0][1]);let release!:()=>void;controls.writeGate=new Promise<void>(resolve=>{release=resolve;});
 const adopted=vi.fn();const view=show(adopted);second();save();
 await waitFor(()=>expect(hasWrite()).toBe(true));
 view.rerender(<StructureCitations sourceId="new-source" revision={"b".repeat(64)} jobId="new-job" kind="format_location" onAnchor={adopted}/>);
 await act(async()=>{release();await controls.writeGate;});
 expect(adopted).not.toHaveBeenCalled();expect(bridge.call.mock.calls.some(([op])=>op==="anchor_resolve")).toBe(false);
});

it("SIMULATED: native text absent from the projected body cannot become a preview or citation",async()=>{
 const controls=transport(cases[0][1]);controls.text="different body";show();second();preview();
 await screen.findByText("结构位置引用未确认；保留原件和任务结果后重试。");
 expect(screen.queryByLabelText("所选引用预览")).not.toBeInTheDocument();expect(hasWrite()).toBe(false);
});
