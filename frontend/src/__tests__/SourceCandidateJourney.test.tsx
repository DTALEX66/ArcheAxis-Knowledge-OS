import {createHash,webcrypto} from "node:crypto";
import {existsSync,readFileSync} from "node:fs";
import {resolve} from "node:path";
import {useState} from "react";
import {beforeEach,expect,it,vi} from "vitest";
import {act,fireEvent,render,screen,waitFor} from "@testing-library/react";
import type {Editor} from "@tiptap/core";
import {SpaceView} from "../spaces/SpaceView";
import {DocumentEditor} from "../components/DocumentEditor";
import {outputReceipt} from "./fixtures/jobContentCoreFixture";
const bridge=vi.hoisted(()=>({call:vi.fn()}));
// Read the same canonical vocabulary that generates Rust KNOWLEDGE_TYPES.
// This remains a SIMULATED transport, but may not accept a type Core rejects.
const repoRoot=process.env.ARCHEAXIS_WORKTREE_ROOT??(existsSync(resolve(process.cwd(),"packages/contracts"))?process.cwd():resolve(process.cwd(),".."));
const vocabulary=JSON.parse(readFileSync(resolve(repoRoot,"packages/contracts/v1/assessment-vocabulary.schema.json"),"utf8")) as {$defs:{knowledge_type:{enum:string[]}}};
const allowedKnowledgeTypes=vocabulary.$defs.knowledge_type.enum;
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
vi.mock("../components/FolderIngest",()=>({FolderIngest:({onOpenSource}:{onOpenSource:(id:string,job:string)=>void})=><button onClick={()=>onOpenSource("source-exact","job-exact")}>选择已完成批量原件</button>}));
vi.mock("../components/KnowledgeCoursePanel",()=>({KnowledgeCoursePanel:()=>null}));
const text="真实来源的引文正文",hash=createHash("sha256").update(text).digest("hex");
const source={source_id:"source-exact",source_revision:hash,sha256:hash,original_name:"source.txt",imported_at:"2026-10-11"};
const position=JSON.stringify({type:"text",start:0,end:6});
const anchor={anchor_id:"anchor-exact",source_id:source.source_id,source_revision:hash,position,location_status:"located"};
const content={type:"doc",content:[{type:"paragraph",attrs:{block_id:"p"},content:[{type:"text",text:"已保存 "},{type:"evidenceReference",attrs:{...anchor,excerpt:"实际引文"}}]}]};
const doc={document_id:"doc-exact",source_id:source.source_id,source_revision:hash,title:"同源文档",version:1,editor_json:content,text_projection:"已保存",content_sha256:hash,blocks:[]};
function mockCore(mismatch=false){let accepted=false,knowledgeReads=0;bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>={})=>{
 const state={job_id:"job-exact",input_ref:source.source_id,kind:"text",state:"succeeded",attempt:1,request_id:"request-exact"};
 switch(op){
 case "sources_list":return {sources:[source]};case "documents_list":return {documents:[doc]};
 case "source_original":return {source_id:source.source_id,name:source.original_name,media_type:"text/plain",sha256:hash,content_base64:Buffer.from(text).toString("base64")};
 case "document_get":return doc;case "anchors_list":return {anchors:[anchor]};case "capabilities_list":return {};
 case "jobs_get":case "job_execution_status":return state;
 case "job_output":return outputReceipt(p.kind,p.kind==="text"?text:"[]");case "job_quality":return {job_id:"job-exact",engine:"fixture"};
 case "source_job_transform":return {source_id:source.source_id,job_id:"job-exact",raw_sha256:hash,transform_id:17,content:text};
 case "knowledge_from_transform":if(!allowedKnowledgeTypes.includes(String((p.body as Record<string,unknown>).knowledge_type)))throw new Error("400 unknown knowledge_type (canonical vocabulary)");return {knowledge_id:"knowledge-exact",anchor_id:anchor.anchor_id,status:"candidate",source_id:source.source_id,raw_sha256:hash,job_id:"job-exact",transform_id:17};
 case "knowledge_get":knowledgeReads++;return {knowledge_id:"knowledge-exact",anchor_id:anchor.anchor_id,source_id:mismatch&&knowledgeReads>1?"other-source":source.source_id,version:"knowledge-v1",title:"知识候选",body:"人工整理",status:accepted?"accepted":"candidate"};
 case "knowledge_qualification":return {knowledge_id:"knowledge-exact",requires_human_review:true};
 case "knowledge_review":accepted=true;return {knowledge_id:"knowledge-exact",version:"knowledge-v1"};
 case "anchor_resolve":return {source_id:source.source_id,anchor_id:anchor.anchor_id,source_revision:hash,current_source_revision:hash,status:"CURRENT",scope:"locator_provenance_only",position};
 default:throw new Error(`unconfigured ${op}`);
 }
});}
function Journey(){const[page,setPage]=useState("16");return <SpaceView spaceId={page==="16"?"exchange":"library"} uiPageId={page} onInspect={()=>{}} onNavigate={()=>{throw new Error("legacy navigation forbidden");}} onOpenPage={setPage}/>;}
beforeEach(()=>{bridge.call.mockReset();vi.stubGlobal("crypto",webcrypto);});
it("SIMULATED transport follows canonical knowledge enum and rejects the old source_note type",async()=>{
  expect(allowedKnowledgeTypes).toContain("NOTE");expect(allowedKnowledgeTypes).not.toContain("source_note");
  mockCore();await expect(bridge.call("knowledge_from_transform",{body:{knowledge_type:"source_note"}})).rejects.toThrow("400 unknown knowledge_type");
});
async function createCandidate(){
 fireEvent.click(await screen.findByRole("button",{name:"选择已完成批量原件"}));
 fireEvent.click(await screen.findByRole("button",{name:"阅读此原件与整理知识候选"}));
 fireEvent.click(await screen.findByRole("button",{name:"整理此来源为知识候选"}));
 const quote=await screen.findByRole("textbox",{name:"选择实际引文"});(quote as HTMLTextAreaElement).setSelectionRange(0,4);fireEvent.select(quote);
 fireEvent.change(screen.getByRole("textbox",{name:"知识候选正文"}),{target:{value:"人工整理"}});
 fireEvent.click(screen.getByRole("button",{name:"创建知识候选"}));
 fireEvent.click(await screen.findByRole("button",{name:"前往知识库审核"}));
}
it("SIMULATED page03 CURRENT locator focuses and selects the exact immutable original text",async()=>{
 mockCore();render(<Journey/>);
 fireEvent.click(await screen.findByRole("button",{name:"选择已完成批量原件"}));
 fireEvent.click(await screen.findByRole("button",{name:"阅读此原件与整理知识候选"}));
 const original=await screen.findByLabelText("并排原件正文");
 fireEvent.click(await screen.findByRole("button",{name:"引用：实际引文"}));
 await waitFor(()=>expect(original).toHaveFocus());
 expect(window.getSelection()?.toString()).toBe(new TextDecoder().decode(new TextEncoder().encode(text).slice(0,6)));
 expect(bridge.call).toHaveBeenCalledWith("anchor_resolve",{source_id:source.source_id,anchor_id:anchor.anchor_id});
});
it("SIMULATED mounted grouped UI preserves exact source/job/transform/anchor/candidate and requires explicit human review",async()=>{
 mockCore();render(<Journey/>);await createCandidate();
 const accept=await screen.findByRole("button",{name:"接受当前候选"});expect(accept).toBeDisabled();
 expect(bridge.call.mock.calls.filter(([op])=>["job_enqueue","job_execute","knowledge_review"].includes(op))).toEqual([]);
 const request=bridge.call.mock.calls.find(([op])=>op==="knowledge_from_transform")![1];expect(request.body).toMatchObject({knowledge_type:"NOTE",source_id:source.source_id,job_id:"job-exact",transform_id:17,quote:text.slice(0,4)});
 fireEvent.change(screen.getByRole("textbox",{name:"审核者"}),{target:{value:"SYNTHETIC reviewer"}});fireEvent.click(accept);
 await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("knowledge_review",{id:"knowledge-exact",body:{action:"accepted",reviewer:"SYNTHETIC reviewer",note:"",expected_version:"knowledge-v1"}}));
});
it("SIMULATED refuses candidate readback bound to a different source and never grants review",async()=>{
 mockCore(true);render(<Journey/>);await createCandidate();await screen.findByText("候选与证据读取失败，审核按钮不可用。");expect(screen.queryByRole("button",{name:"接受当前候选"})).toBeNull();expect(bridge.call.mock.calls.some(([op])=>op==="knowledge_review")).toBe(false);
});
it("SIMULATED actual Tiptap transaction serializes the exact locator and click passes its immutable identities",async()=>{
 const save=vi.fn().mockResolvedValue({content,version:2}),activate=vi.fn();render(<DocumentEditor content={content} version={1} onSave={save} onReferenceActivate={activate}/>);
 const textbox=await screen.findByRole("textbox",{name:"文档草稿"});const editor=(textbox as HTMLElement&{editor:Editor}).editor;
 act(()=>{editor.commands.insertContent("编辑 ");});fireEvent.click(screen.getByRole("button",{name:"保存草稿"}));await waitFor(()=>expect(save).toHaveBeenCalled());
 const json=save.mock.calls[0][0];expect(JSON.stringify(json)).toContain(position.replace(/"/g,'\\"'));
 fireEvent.click(screen.getByRole("button",{name:"引用：实际引文"}));expect(activate).toHaveBeenCalledWith(expect.objectContaining({anchor_id:anchor.anchor_id,source_id:source.source_id,source_revision:hash,position}));
 activate.mockClear();fireEvent.keyDown(screen.getByRole("button",{name:"引用：实际引文"}),{key:"Enter"});expect(activate).toHaveBeenCalledWith(expect.objectContaining({position}));
});
