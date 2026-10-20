import {createHash,webcrypto} from "node:crypto";
import {existsSync,readFileSync} from "node:fs";
import {resolve} from "node:path";
import {useState} from "react";
import {beforeEach,expect,it,vi} from "vitest";
import {act,fireEvent,render,renderHook,screen,waitFor,within} from "@testing-library/react";
import type {Editor} from "@tiptap/core";
import {SpaceView} from "../spaces/SpaceView";
import {DocumentEditor} from "../components/DocumentEditor";
import {DockWorkspace} from "../workspace/DockWorkspace";
import {outputReceipt} from "./fixtures/jobContentCoreFixture";
import {resetDiagnostics,useDiagnosticState} from "../presentation/diagnostics";
const bridge=vi.hoisted(()=>({call:vi.fn()}));
// Read the same canonical vocabulary that generates Rust KNOWLEDGE_TYPES.
// This remains a SIMULATED transport, but may not accept a type Core rejects.
const repoRoot=process.env.ARCHEAXIS_WORKTREE_ROOT??(existsSync(resolve(process.cwd(),"packages/contracts"))?process.cwd():resolve(process.cwd(),".."));
const vocabulary=JSON.parse(readFileSync(resolve(repoRoot,"packages/contracts/v1/assessment-vocabulary.schema.json"),"utf8")) as {$defs:{knowledge_type:{enum:string[]}}};
const allowedKnowledgeTypes=vocabulary.$defs.knowledge_type.enum;
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
vi.mock("../components/FolderIngest",()=>({FolderIngest:({onOpenSource}:{onOpenSource:(id:string,job:string)=>void})=><><button onClick={()=>onOpenSource("source-exact","job-exact")}>选择已完成批量原件</button><button onClick={()=>onOpenSource("source-other","job-other")}>选择另一个批量原件</button></>}));
vi.mock("../components/KnowledgeCoursePanel",()=>({KnowledgeCoursePanel:()=>null}));
const text="真实来源的引文正文",hash=createHash("sha256").update(text).digest("hex");
const source={source_id:"source-exact",source_revision:hash,sha256:hash,original_name:"source.txt",imported_at:"2026-10-11"};
const position=JSON.stringify({type:"text",start:0,end:6});
const anchor={anchor_id:"anchor-exact",source_id:source.source_id,source_revision:hash,position,location_status:"located"};
const candidateAnchor={...anchor,anchor_id:"candidate-anchor-exact",position:JSON.stringify({schema:"archeaxis.transform-text-selection/v1",job_id:"job-exact",transform_id:17,selection_start_utf16:0,selection_end_utf16:4,quote:text.slice(0,4)})};
const content={type:"doc",content:[{type:"paragraph",attrs:{block_id:"p"},content:[{type:"text",text:"已保存 "},{type:"evidenceReference",attrs:{...anchor,excerpt:"实际引文"}}]}]};
const doc={document_id:"doc-exact",source_id:source.source_id,source_revision:hash,title:"同源文档",version:1,editor_json:content,text_projection:"已保存",content_sha256:hash,blocks:[]};
function mockCore(mismatch=false,candidateStatus="CURRENT"){let accepted=false,knowledgeReads=0;bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>={})=>{
 const state={job_id:"job-exact",input_ref:source.source_id,kind:"text",state:"succeeded",attempt:1,request_id:"request-exact"};
 switch(op){
 case "sources_list":return {sources:[source]};case "documents_list":return {documents:[doc]};
 case "source_original":return {source_id:source.source_id,name:source.original_name,media_type:"text/plain",sha256:hash,content_base64:Buffer.from(text).toString("base64")};
 case "document_get":return doc;case "anchors_list":return {anchors:[anchor]};case "capabilities_list":return {};
 case "jobs_get":case "job_execution_status":return state;
 case "job_output":return outputReceipt(p.kind,p.kind==="text"?text:"[]");case "job_quality":return {job_id:"job-exact",engine:"fixture"};
 case "source_job_transform":return {source_id:source.source_id,job_id:"job-exact",raw_sha256:hash,transform_id:17,content:text};
 case "knowledge_from_transform":if(!allowedKnowledgeTypes.includes(String((p.body as Record<string,unknown>).knowledge_type)))throw new Error("400 unknown knowledge_type (canonical vocabulary)");return {knowledge_id:"knowledge-exact",anchor_id:candidateAnchor.anchor_id,status:"candidate",source_id:source.source_id,raw_sha256:hash,job_id:"job-exact",transform_id:17};
 case "knowledge_get":knowledgeReads++;return {knowledge_id:"knowledge-exact",anchor_id:candidateAnchor.anchor_id,source_id:mismatch&&knowledgeReads>1?"other-source":source.source_id,version:"knowledge-v1",title:"知识候选",body:"人工整理",status:accepted?"accepted":"candidate"};
 case "knowledge_qualification":return {knowledge_id:"knowledge-exact",requires_human_review:true};
 case "knowledge_review":accepted=true;return {knowledge_id:"knowledge-exact",version:"knowledge-v1"};
 case "anchor_resolve":{const selected=p.anchor_id===candidateAnchor.anchor_id?candidateAnchor:anchor;return {source_id:source.source_id,anchor_id:selected.anchor_id,source_revision:hash,current_source_revision:hash,status:selected===candidateAnchor?candidateStatus:"CURRENT",scope:"locator_provenance_only",position:selected.position};}
 default:throw new Error(`unconfigured ${op}`);
 }
});}
function expectSourceDiagnostic(region:HTMLElement, expectedId:string){
 expect(region).not.toHaveTextContent(expectedId);
 const diagnostics=renderHook(useDiagnosticState);
 fireEvent.click(within(region).getByRole("button",{name:"查看诊断详情：原件编号与版本详细信息"}));
 expect(diagnostics.result.current.entries[0].payload).toEqual({source_id:expectedId,source_revision:hash});
 diagnostics.unmount();
}
function Journey(){const[page,setPage]=useState("16");return <SpaceView spaceId={page==="16"?"exchange":"library"} uiPageId={page} onInspect={()=>{}} onNavigate={()=>{throw new Error("legacy navigation forbidden");}} onOpenPage={setPage}/>;}
function DockJourney({initialPage="16",refuse=false,documentId}:{initialPage?:string;refuse?:boolean;documentId?:string}){const[page,setPage]=useState(initialPage);return <><nav><button onClick={()=>setPage("16")}>手动进入导入页</button><button onClick={()=>setPage("03")}>手动进入阅读页</button></nav><DockWorkspace spaceId={page==="16"?"exchange":"library"} uiPageId={page} initialDocumentId={documentId} onInspect={()=>{}} onNavigate={()=>{throw new Error("legacy navigation forbidden");}} onOpenPage={id=>{if(!refuse)setPage(id);}}/></>;}
class ResizeObserverStub{observe(){}unobserve(){}disconnect(){}}
beforeEach(()=>{resetDiagnostics();bridge.call.mockReset();vi.stubGlobal("crypto",webcrypto);vi.stubGlobal("ResizeObserver",ResizeObserverStub);});
it.each(["16","03"])("SIMULATED real Dockview transfers the exact source/job into a distinct reader host (initial page %s)",async initialPage=>{
 mockCore();render(<DockJourney initialPage={initialPage}/>);
 fireEvent.click(screen.getByRole("button",{name:"手动进入导入页"}));
 const exchange=await screen.findByRole("region",{name:"导入、导出与互通"});
 fireEvent.change(within(exchange).getByLabelText("筛选已读原件"),{target:{value:"保留批量页筛选"}});
 fireEvent.click(within(exchange).getByRole("button",{name:"选择已完成批量原件"}));
 fireEvent.click(await within(exchange).findByRole("button",{name:"阅读此原件与整理知识候选"}));
 const reader=await screen.findByRole("region",{name:"阅读与编辑文档视图"});
 const preparation=await within(reader).findByRole("region",{name:"同源知识整理"});
 expectSourceDiagnostic(preparation,source.source_id);expect(preparation).not.toHaveTextContent(hash);
 expect(bridge.call).toHaveBeenCalledWith("source_original",{source_id:source.source_id});
 fireEvent.click(within(preparation).getByRole("button",{name:"整理此来源为知识候选"}));
 expect(await within(reader).findByRole("textbox",{name:"选择实际引文"})).toHaveValue(text);
 expect(bridge.call).toHaveBeenCalledWith("source_job_transform",expect.objectContaining({source_id:source.source_id,job_id:"job-exact"}));
 fireEvent.click(screen.getByRole("button",{name:"手动进入导入页"}));
 expect(within(screen.getByRole("region",{name:"导入、导出与互通"})).getByLabelText("筛选已读原件")).toHaveValue("保留批量页筛选");
 expect(bridge.call.mock.calls.some(([op])=>["job_enqueue","job_execute","document_draft"].includes(op))).toBe(false);
});
it("SIMULATED refused Dock navigation leaves the retained reader unchanged and discards the pending source",async()=>{
 mockCore();const previous=bridge.call.getMockImplementation()!;
 const other={...source,source_id:"source-other",original_name:"other.txt"};
 bridge.call.mockImplementation((op:string,p:Record<string,unknown>={})=>op==="sources_list"?Promise.resolve({sources:[source,other]}):op==="source_original"&&p.source_id===other.source_id?Promise.resolve({source_id:other.source_id,name:other.original_name,media_type:"text/plain",sha256:hash,content_base64:Buffer.from(text).toString("base64")}):previous(op,p));
 const view=render(<DockJourney/>);
 fireEvent.click(await screen.findByRole("button",{name:"选择已完成批量原件"}));
 fireEvent.click(await screen.findByRole("button",{name:"阅读此原件与整理知识候选"}));
 const reader=await screen.findByRole("region",{name:"阅读与编辑文档视图"});
 expectSourceDiagnostic(await within(reader).findByRole("region",{name:"同源知识整理"}),source.source_id);
 fireEvent.click(screen.getByRole("button",{name:"手动进入导入页"}));view.rerender(<DockJourney refuse/>);
 fireEvent.click(screen.getByRole("button",{name:"选择另一个批量原件"}));
 const read=await screen.findByRole("button",{name:"阅读此原件与整理知识候选"});
 const before=bridge.call.mock.calls.filter(([op,p])=>op==="source_original"&&p.source_id===other.source_id).length;
 fireEvent.click(read);
 expect(screen.getByRole("region",{name:"导入、导出与互通"})).toBeVisible();
 fireEvent.click(screen.getByRole("button",{name:"手动进入阅读页"}));
 expectSourceDiagnostic(within(screen.getByRole("region",{name:"阅读与编辑文档视图"})).getByRole("region",{name:"同源知识整理"}),source.source_id);
 expect(bridge.call.mock.calls.filter(([op,p])=>op==="source_original"&&p.source_id===other.source_id)).toHaveLength(before);
 fireEvent.click(screen.getByRole("button",{name:"手动进入导入页"}));view.rerender(<DockJourney/>);
 fireEvent.click(screen.getByRole("button",{name:"阅读此原件与整理知识候选"}));
 await waitFor(()=>expect(within(screen.getByRole("region",{name:"阅读与编辑文档视图"})).getByRole("region",{name:"同源知识整理"})).toHaveTextContent(other.original_name));
 expectSourceDiagnostic(within(screen.getByRole("region",{name:"阅读与编辑文档视图"})).getByRole("region",{name:"同源知识整理"}),other.source_id);
 expect(bridge.call.mock.calls.filter(([op,p])=>op==="source_original"&&p.source_id===other.source_id)).toHaveLength(before+1);
 view.rerender(<DockJourney documentId="doc-exact"/>);
 await waitFor(()=>expect(within(reader).getByRole("region",{name:"同源知识整理"}).closest("details")).toHaveClass("reader-source-tools"));
 expect(await within(reader).findByRole("textbox",{name:"文档草稿"})).toHaveTextContent("已保存");
});
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
 expect(bridge.call).toHaveBeenCalledWith("anchor_resolve",{source_id:source.source_id,anchor_id:candidateAnchor.anchor_id});
 expect(bridge.call.mock.calls.filter(([op])=>["job_enqueue","job_execute","knowledge_review"].includes(op))).toEqual([]);
 const request=bridge.call.mock.calls.find(([op])=>op==="knowledge_from_transform")![1];expect(request.body).toMatchObject({knowledge_type:"NOTE",source_id:source.source_id,job_id:"job-exact",transform_id:17,quote:text.slice(0,4)});
 fireEvent.change(screen.getByRole("textbox",{name:"审核者"}),{target:{value:"SYNTHETIC reviewer"}});fireEvent.click(accept);
 await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("knowledge_review",{id:"knowledge-exact",body:{action:"accepted",reviewer:"SYNTHETIC reviewer",note:"",expected_version:"knowledge-v1"}}));
});
it("SIMULATED refuses candidate readback bound to a different source and never grants review",async()=>{
 mockCore(true);render(<Journey/>);await createCandidate();await screen.findByText("候选或来源绑定读取失败，审核按钮不可用。");expect(screen.queryByRole("button",{name:"接受当前候选"})).toBeNull();expect(bridge.call.mock.calls.some(([op])=>op==="knowledge_review")).toBe(false);
});
it.each(["STALE","UNSUPPORTED"])("SIMULATED refuses %s candidate locator even when the reading locator is CURRENT",async status=>{
 mockCore(false,status);render(<Journey/>);await createCandidate();await screen.findByText("候选或来源绑定读取失败，审核按钮不可用。");expect(screen.queryByRole("button",{name:"接受当前候选"})).toBeNull();expect(bridge.call.mock.calls.some(([op])=>op==="knowledge_review")).toBe(false);
});
it("SIMULATED actual Tiptap transaction serializes the exact locator and click passes its immutable identities",async()=>{
 const save=vi.fn().mockResolvedValue({content,version:2}),activate=vi.fn();render(<DocumentEditor content={content} version={1} onSave={save} onReferenceActivate={activate}/>);
 const textbox=await screen.findByRole("textbox",{name:"文档草稿"});const editor=(textbox as HTMLElement&{editor:Editor}).editor;
 act(()=>{editor.commands.insertContent("编辑 ");});fireEvent.click(screen.getByRole("button",{name:"保存草稿"}));await waitFor(()=>expect(save).toHaveBeenCalled());
 const json=save.mock.calls[0][0];expect(JSON.stringify(json)).toContain(position.replace(/"/g,'\\"'));
 fireEvent.click(screen.getByRole("button",{name:"引用：实际引文"}));expect(activate).toHaveBeenCalledWith(expect.objectContaining({anchor_id:anchor.anchor_id,source_id:source.source_id,source_revision:hash,position}));
 activate.mockClear();fireEvent.keyDown(screen.getByRole("button",{name:"引用：实际引文"}),{key:"Enter"});expect(activate).toHaveBeenCalledWith(expect.objectContaining({position}));
});
