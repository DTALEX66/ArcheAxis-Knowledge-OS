import {createHash,webcrypto} from "node:crypto";
import {useState} from "react";
import {beforeEach,expect,it,vi} from "vitest";
import {act,fireEvent,render,screen,waitFor} from "@testing-library/react";
import {App} from "../app/App";
import {SpaceView} from "../spaces/SpaceView";
import {outputReceipt} from "./fixtures/jobContentCoreFixture";
const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
vi.mock("../components/FolderIngest",()=>({FolderIngest:({onOpenSource}:{onOpenSource:(id:string,job:string)=>void})=><button onClick={()=>onOpenSource("source-exact","job-exact")}>选择已完成批量原件</button>}));
vi.mock("../components/KnowledgeCoursePanel",()=>({KnowledgeCoursePanel:()=>null}));
const text="真实来源的引文正文",hash=createHash("sha256").update(text).digest("hex");
const source={source_id:"source-exact",source_revision:hash,sha256:hash,original_name:"source.txt",imported_at:"2026-10-11"};
const position=JSON.stringify({type:"text",start:0,end:6});
const anchor={anchor_id:"anchor-exact",source_id:source.source_id,source_revision:hash,position,location_status:"located"};
const content={type:"doc",content:[{type:"paragraph",attrs:{block_id:"p"},content:[{type:"text",text:"已保存 "},{type:"evidenceReference",attrs:{...anchor,excerpt:"实际引文"}}]}]};
const doc={document_id:"doc-exact",source_id:source.source_id,source_revision:hash,title:"同源文档",version:1,editor_json:content,text_projection:"已保存",content_sha256:hash,blocks:[]};
function mockCore(mismatch=false){let accepted=false;bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>={})=>{
 const state={job_id:"job-exact",input_ref:source.source_id,kind:"text",state:"succeeded",attempt:1,request_id:"request-exact"};
 switch(op){
 case "sources_list":return {sources:[source]};case "documents_list":return {documents:[doc]};
 case "source_original":return {source_id:source.source_id,name:source.original_name,media_type:"text/plain",sha256:hash,content_base64:Buffer.from(text).toString("base64")};
 case "document_get":return doc;case "anchors_list":return {anchors:[anchor]};case "capabilities_list":return {};
 case "jobs_get":case "job_execution_status":return state;
 case "job_output":return outputReceipt(p.kind,p.kind==="text"?text:"[]");case "job_quality":return {job_id:"job-exact",engine:"fixture"};
 case "source_job_transform":return {source_id:source.source_id,job_id:"job-exact",raw_sha256:hash,transform_id:17,content:text};
 case "knowledge_from_transform":return {knowledge_id:"knowledge-exact",anchor_id:anchor.anchor_id,status:"candidate",source_id:source.source_id,raw_sha256:hash,job_id:"job-exact",transform_id:17};
 case "knowledge_get":return {knowledge_id:"knowledge-exact",anchor_id:anchor.anchor_id,source_id:mismatch?"other-source":source.source_id,version:"knowledge-v1",title:"知识候选",body:"人工整理",status:accepted?"accepted":"candidate"};
 case "knowledge_qualification":return {knowledge_id:"knowledge-exact",requires_human_review:true};
 case "learning_reference":return {};case "assessment_create":return {item_key:p.item_key,assessment_id:"assessment-exact",question:"实际问题"};case "learning_items":return {items:[],count:0};case "knowledge_review":accepted=true;return {knowledge_id:"knowledge-exact",version:"knowledge-v1"};
 case "anchor_resolve":return {source_id:source.source_id,anchor_id:anchor.anchor_id,source_revision:hash,current_source_revision:hash,status:"CURRENT",scope:"locator_provenance_only",position};
 default:throw new Error(`unconfigured ${op}`);
 }
});}
function Journey(){const[page,setPage]=useState("16");return <SpaceView spaceId={page==="16"?"exchange":"library"} uiPageId={page} onInspect={()=>{}} onNavigate={()=>{throw new Error("legacy navigation forbidden");}} onOpenPage={setPage}/>;}
beforeEach(()=>{bridge.call.mockReset();vi.stubGlobal("crypto",webcrypto);window.location.hash="#page=16";delete window.__TAURI__;});
async function createCandidate(){
 fireEvent.click(await screen.findByRole("button",{name:"选择已完成批量原件"}));
 fireEvent.click(await screen.findByRole("button",{name:"阅读此原件与整理知识候选"}));
 fireEvent.click(await screen.findByRole("button",{name:"整理此来源为知识候选"}));
 const quote=await screen.findByRole("textbox",{name:"选择实际引文"});(quote as HTMLTextAreaElement).setSelectionRange(0,4);fireEvent.select(quote);
 fireEvent.change(screen.getByRole("textbox",{name:"知识候选正文"}),{target:{value:"人工整理"}});
 fireEvent.click(screen.getByRole("button",{name:"创建知识候选"}));
 fireEvent.click(await screen.findByRole("button",{name:"前往知识库审核"}));
}

it("SIMULATED mounted App source candidate readback clears only saved draft and learning navigation needs no unsaved confirm",async()=>{
 mockCore();const confirm=vi.spyOn(window,"confirm").mockReturnValue(false);render(<App/>);await createCandidate();
 fireEvent.change(await screen.findByRole("textbox",{name:"审核者"}),{target:{value:"SYNTHETIC reviewer"}});
 fireEvent.click(await screen.findByRole("button",{name:"接受当前候选"}));
 fireEvent.click(await screen.findByRole("button",{name:"由当前知识建立学习问题"}));
 await waitFor(()=>expect(window.location.hash).toBe("#page=06"));expect(confirm).not.toHaveBeenCalled();confirm.mockRestore();
});
it.each(["lost ack","wrong provenance","wrong body"])("SIMULATED mounted candidate %s keeps its draft dirty",async(mode)=>{
 mockCore();const original=bridge.call.getMockImplementation()!;const dirty=vi.fn();
 bridge.call.mockImplementation(async(op,p)=>{if(op==="knowledge_from_transform"&&mode==="lost ack")throw new Error("ACK lost");const value=await original(op,p);if(op==="knowledge_from_transform"&&mode==="wrong provenance")return {...value,source_id:"other"};if(op==="knowledge_get"&&mode==="wrong body")return {...value,body:"other"};return value;});
 const listener=(e:Event)=>{const detail=(e as CustomEvent).detail;if(detail?.owner?.startsWith("job-content-"))dirty(detail.dirty);};window.addEventListener("archeaxis-draft-dirty",listener);
 try{render(<Journey/>);fireEvent.click(await screen.findByRole("button",{name:"选择已完成批量原件"}));fireEvent.click(await screen.findByRole("button",{name:"阅读此原件与整理知识候选"}));fireEvent.click(await screen.findByRole("button",{name:"整理此来源为知识候选"}));
 const quote=await screen.findByRole("textbox",{name:"选择实际引文"});(quote as HTMLTextAreaElement).setSelectionRange(0,4);fireEvent.select(quote);fireEvent.change(screen.getByRole("textbox",{name:"知识候选正文"}),{target:{value:"人工整理"}});fireEvent.click(screen.getByRole("button",{name:"创建知识候选"}));
 await screen.findByText("知识候选创建未确认，请保留正文与选区重试。");expect(screen.getByRole("textbox",{name:"知识候选正文"})).toHaveValue("人工整理");expect(dirty.mock.calls.at(-1)).toEqual([true]);expect(screen.queryByRole("button",{name:"前往知识库审核"})).toBeNull();
 }finally{window.removeEventListener("archeaxis-draft-dirty",listener);}
});
it("SIMULATED mounted delayed candidate body readback preserves later input and dirty owner",async()=>{
 mockCore();const original=bridge.call.getMockImplementation()!;let release!:(value:unknown)=>void;bridge.call.mockImplementation(async(op,p)=>op==="knowledge_get"?new Promise(resolve=>{release=resolve;}):original(op,p));const dirty=vi.fn();const listener=(e:Event)=>{const detail=(e as CustomEvent).detail;if(detail?.owner?.startsWith("job-content-"))dirty(detail.dirty);};window.addEventListener("archeaxis-draft-dirty",listener);
 try{render(<Journey/>);fireEvent.click(await screen.findByRole("button",{name:"选择已完成批量原件"}));fireEvent.click(await screen.findByRole("button",{name:"阅读此原件与整理知识候选"}));fireEvent.click(await screen.findByRole("button",{name:"整理此来源为知识候选"}));const quote=await screen.findByRole("textbox",{name:"选择实际引文"});(quote as HTMLTextAreaElement).setSelectionRange(0,4);fireEvent.select(quote);const body=screen.getByRole("textbox",{name:"知识候选正文"});fireEvent.change(body,{target:{value:"人工整理"}});fireEvent.click(screen.getByRole("button",{name:"创建知识候选"}));await waitFor(()=>expect(release).toBeDefined());
 // A queued editor event arriving while the readback is pending must survive.
 fireEvent.change(body,{target:{value:"人工整理 后来编辑"}});await act(async()=>{release(await original("knowledge_get",{id:"knowledge-exact"}));});await screen.findByRole("button",{name:"前往知识库审核"});expect(body).toHaveValue("人工整理 后来编辑");expect(dirty.mock.calls.at(-1)).toEqual([true]);
 }finally{window.removeEventListener("archeaxis-draft-dirty",listener);}
});
