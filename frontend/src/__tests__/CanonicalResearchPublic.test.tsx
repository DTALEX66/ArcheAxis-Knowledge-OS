import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { CanonicalResearchSpace } from "../spaces/CanonicalResearchSpace";
import type { DocumentDto, PublicResearchRequest, PublicResearchReceiptDto } from "../api/generated/core-contract";
import { assertUiWorkingState, type UiWorkingStateRead } from "../api/generated/ui-working-state-contract";
import { DocumentBusinessProvider, DocumentBusinessSessions } from "../workspace/documentSessions";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const scope={workspace_id:"0123456789abcdef0123456789abcdef",restore_epoch:"initial"};
const ui:UiWorkingStateRead={schema:"archeaxis.ui-working-state/v1",...scope,state_revision:0,state:{drafts:{},opened_documents:[],active_document:null,page_id:null},draft_digests:{},recovery_candidates:null,recovery_requires_confirmation:false,pending_document_id:null};
const raw={kind:"source" as const,source_id:"raw_public",sha256:"a".repeat(64)},derived={kind:"source" as const,source_id:"derived_public",sha256:"b".repeat(64)};
const hit={id:"https://openalex.org/W123",family:"research" as const,provider:"openalex" as const,title:"Public metadata",url:"https://openalex.org/W123",retrieved_at:"2026-10-21T00:00:00Z",content:"metadata" as const,excerpt:"",locator:null,license:null,free_access:"unknown" as const,upstream_revision:null,representation:"metadata" as const,truncated:false};
function doc(id:string):DocumentDto{return {document_id:id,title:id,version:1,content_sha256:"c".repeat(64),source_id:null,source_revision:null,text_projection:"private research",blocks:[],editor_json:{type:"doc",content:[],attrs:{archeaxis_research:{schema:"archeaxis.research/v1",question:"private research body",materials:[],hypotheses:[],methods:[],experiments:[],counterevidence:[],conclusions:[],unresolved:[]}}}};}
let docs:Map<string,DocumentDto>,saved:unknown[],request:PublicResearchRequest;

it("passes a changed forum site through the real research view callback without using private research text",async()=>{
 render(<CanonicalResearchSpace/>);const panel=await search();
 fireEvent.change(within(panel).getByRole("combobox",{name:"社区论坛站点"}),{target:{value:"stats"}});
 fireEvent.click(within(panel).getByRole("button",{name:"检索公开资料"}));
 await waitFor(()=>expect(request).toMatchObject({community_site:"stats",query:"public",limit:3}));
 expect(JSON.stringify(request)).not.toContain("private research");expect(saved).toHaveLength(0);
});
function receipt():PublicResearchReceiptDto{return {schema:"archeaxis.public-research-receipt/v1",...request,state:"complete",channels:request.families.map(family=>({family,provider:family==="research"?"openalex":family==="community"?"stackexchange":"wikipedia",status:"complete",retrieved_at:hit.retrieved_at,request_url:family==="research"?"https://api.openalex.org/works?search=public&per-page=1":family==="community"?"https://api.stackexchange.com/2.3/search/advanced?q=public":"https://en.wikipedia.org/w/api.php?action=query",retry_after_seconds:null,error_code:null,hits:family==="research"?[hit]:[],raw_source:family==="research"?raw:null,raw_representation:"http_entity_body_bytes"})),reason_code:null,provider_stop_state:"unknown",knowledge_admission:"not_executed"};}
function selection(){return {schema:"archeaxis.public-research-selection/v1",request_id:request.request_id,family:"research",hit_id:hit.id,reference:derived,raw_reference:raw,title:hit.title,representation:hit.representation,truncated:false,note:"仅元数据，未核验",knowledge_admission:"not_executed"};}
beforeEach(()=>{assertUiWorkingState("Read",ui);docs=new Map([["doc_a",doc("doc_a")],["doc_b",doc("doc_b")]]);saved=[];bridge.call.mockReset();bridge.call.mockImplementation(async(op:string,p:any={})=>{if(op==="documents_list")return {documents:[...docs.values()],next_cursor:null,snapshot_count:docs.size};if(op==="document_get")return structuredClone(docs.get(p.document_id));if(op==="ui_state_read")return ui;if(op==="public_research_search"){request=p.body;return receipt();}if(op==="public_research_materialize")return selection();if(op==="document_draft"){saved.push(structuredClone(p));const old=docs.get(p.document_id)!;const next={...old,version:old.version+1,editor_json:structuredClone(p.body.editor_json)};docs.set(p.document_id,next);return next;}throw Error(op);});});
async function search(){fireEvent.click(screen.getByText("研究文档与版本"));await screen.findByRole("button",{name:"doc_a · 版本 1"});fireEvent.click(screen.getByRole("button",{name:"doc_a · 版本 1"}));await waitFor(()=>expect(screen.getByRole("textbox",{name:"研究问题"})).toHaveValue("private research body"));const panel=screen.getByRole("region",{name:"公开资料检索"});expect(within(panel).getByRole("textbox",{name:"公开检索关键词"})).toHaveValue("");fireEvent.change(within(panel).getByRole("textbox",{name:"公开检索关键词"}),{target:{value:"public"}});fireEvent.click(within(panel).getByRole("button",{name:"检索公开资料"}));await screen.findByRole("heading",{name:hit.title});fireEvent.click(within(panel).getByText("查看结果 1 详情 · 相同地址 1 条记录"));return panel;}
it("materializes derived and raw fixed references as two unverified materials, then saves via the existing draft operation",async()=>{const open=vi.fn();render(<CanonicalResearchSpace onOpenReference={open}/>);const panel=await search();expect(request.query).toBe("public");expect(JSON.stringify(request)).not.toContain("private research");expect(saved).toEqual([]);fireEvent.click(within(panel).getByRole("button",{name:"读取科研原始 API 原件"}));expect(open).toHaveBeenCalledWith(raw);fireEvent.click(within(panel).getByRole("button",{name:`将${hit.title}固定快照与原始 API 加入材料`}));fireEvent.click(await screen.findByRole("button",{name:"证据对比 (2)"}));fireEvent.click(screen.getByRole("button",{name:"材料 2 · 选择对照"}));await screen.findByRole("textbox",{name:"材料说明 2"});fireEvent.click(screen.getByRole("button",{name:"材料 1 · 选择对照"}));expect((screen.getByRole("textbox",{name:"材料说明 1"}) as HTMLTextAreaElement).value).toContain("仅元数据");fireEvent.click(screen.getByRole("button",{name:"材料 2 · 选择对照"}));expect((screen.getByRole("textbox",{name:"材料说明 2"}) as HTMLTextAreaElement).value).toContain("原始 API 响应字节已保全");expect(saved).toEqual([]);fireEvent.click(screen.getByRole("button",{name:"保存研究草稿"}));await waitFor(()=>expect(saved).toHaveLength(1));const materials=(saved[0] as any).body.editor_json.attrs.archeaxis_research.materials;expect(materials.map((m:any)=>m.reference)).toEqual([derived,raw]);expect(materials[0].id).not.toBe(materials[1].id);expect(materials.every((m:any)=>m.citation===undefined)).toBe(true);expect(bridge.call.mock.calls.some(([op])=>String(op).includes("knowledge"))).toBe(false);});
it("keeps results readable but blocks material writes when another view owns the lease",async()=>{const sessions=new DocumentBusinessSessions(scope.workspace_id,"initial");sessions.acquire("doc_a","writer");render(<DocumentBusinessProvider sessions={sessions} viewId="reader"><CanonicalResearchSpace/></DocumentBusinessProvider>);const panel=await search();expect(within(panel).getByRole("button",{name:`将${hit.title}固定快照与原始 API 加入材料`})).toBeDisabled();expect(within(panel).getByRole("button",{name:"读取科研原始 API 原件"})).toBeEnabled();expect(saved).toHaveLength(0);});
it("does not append a late materialization into another research page",async()=>{let resolve!:(v:unknown)=>void;const original=bridge.call.getMockImplementation()!;bridge.call.mockImplementation((op:string,p:any)=>op==="public_research_materialize"?new Promise(r=>{resolve=r;}):original(op,p));render(<CanonicalResearchSpace/>);const panel=await search();fireEvent.click(within(panel).getByRole("button",{name:`将${hit.title}固定快照与原始 API 加入材料`}));await waitFor(()=>expect(bridge.call.mock.calls.some(([op])=>op==="public_research_materialize")).toBe(true));fireEvent.click(screen.getByText("研究文档与版本"));fireEvent.click(screen.getByRole("button",{name:"doc_b · 版本 1"}));await waitFor(()=>expect(screen.getByText("doc_b · 当前基准版本 1")).toBeInTheDocument());await act(async()=>resolve(selection()));expect(screen.queryByRole("textbox",{name:"材料说明 1"})).not.toBeInTheDocument();expect(saved).toHaveLength(0);});

it("binds authored comparison to materialized source hashes and a Core anchor before the ordinary save",async()=>{
 const original=bridge.call.getMockImplementation()!;
 const text="Synthetic fixed metadata snapshot\r\nPublic metadata", bytes=new TextEncoder().encode(text);
 const hash=async(data:Uint8Array)=>Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",data.slice().buffer)),b=>b.toString(16).padStart(2,"0")).join("");
 const sha=await hash(bytes), reference={...derived,sha256:sha};
 bridge.call.mockImplementation(async(op:string,p:any)=>{
  if(op==="public_research_materialize")return {...selection(),reference};
  if(op==="source_original")return {source_id:reference.source_id,sha256:sha,name:"derived.txt",media_type:"text/plain",content_base64:btoa(String.fromCharCode(...bytes))};
  if(op==="anchor_create")return {anchor_id:"comparison_anchor",source_id:reference.source_id,source_revision:sha,location_status:"located",position:JSON.stringify({...JSON.parse(p.body.position),checksum:p.body.checksum,location_status:"located"})};
  if(op==="anchor_resolve")return {anchor_id:"comparison_anchor",source_id:reference.source_id,source_revision:sha,current_source_revision:sha,status:"CURRENT",scope:"locator_provenance_only",position:JSON.stringify({type:"text",start:0,end:bytes.length,checksum:sha,location_status:"located"})};
  return original(op,p);
 });
 render(<CanonicalResearchSpace/>);const panel=await search();
 fireEvent.click(within(panel).getByRole("checkbox",{name:"对照结果 1"}));
 fireEvent.change(within(panel).getByRole("combobox",{name:"对照 1 判断"}),{target:{value:"supports"}});
 fireEvent.click(within(panel).getByRole("button",{name:"把对照记录加入未决草稿"}));
 await waitFor(()=>expect(within(panel).getByRole("button",{name:"把对照记录加入未决草稿"})).toBeDisabled());
 fireEvent.click(await screen.findByRole("button",{name:"证据对比 (2)"}));fireEvent.click(screen.getByRole("button",{name:"材料 2 · 选择对照"}));await screen.findByRole("textbox",{name:"材料说明 2"});
 fireEvent.click(screen.getByRole("button",{name:"保存研究草稿"}));await waitFor(()=>expect(saved).toHaveLength(1));
 const attrs=(saved[0] as any).body.editor_json.attrs, research=attrs.archeaxis_research;
 expect(research.materials.map((m:any)=>m.reference)).toEqual([reference,raw]);
 expect(research.materials[0].citation).toMatchObject({anchor_id:"comparison_anchor",source_sha256:sha,quote:text});
 expect(research.unresolved.at(-1).references).toEqual([reference,raw]);
 expect(research.unresolved.at(-1).text).toContain("独立性：UNKNOWN");
 expect(attrs.archeaxis_relations.relations.at(-1)).toMatchObject({kind:"supports",target:reference});
 expect(bridge.call.mock.calls.some(([op])=>String(op).includes("knowledge"))).toBe(false);
});

async function savedPublicMaterial(onReadSource:(target:any)=>boolean|void){
 render(<CanonicalResearchSpace onReadSource={onReadSource}/>);const panel=await search();
 fireEvent.click(within(panel).getByRole("button",{name:`将${hit.title}固定快照与原始 API 加入材料`}));
 fireEvent.click(await screen.findByRole("button",{name:"证据对比 (2)"}));
 const next=screen.getByRole("button",{name:"在阅读页整理材料 1"});
 expect(next).toBeDisabled();expect(onReadSource).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole("button",{name:"保存研究草稿"}));
 await waitFor(()=>expect(next).toBeEnabled());return next;
}

it("opens the exact saved public material in the existing reader without conversion or knowledge admission",async()=>{
 const open=vi.fn(()=>true),previous=bridge.call.getMockImplementation()!;
 bridge.call.mockImplementation((op:string,p:any)=>op==="sources_list"?Promise.resolve({sources:[{source_id:derived.source_id,source_revision:derived.sha256,sha256:derived.sha256,original_name:"public-derived.txt"}]}):previous(op,p));
 const next=await savedPublicMaterial(open);fireEvent.click(next);
 await waitFor(()=>expect(open).toHaveBeenCalledOnce());expect(open).toHaveBeenCalledWith({source_id:derived.source_id,source_revision:derived.sha256,sha256:derived.sha256});
 expect(bridge.call.mock.calls.some(([op])=>["job_execute","knowledge_from_transform","knowledge_review","assessment_create"].includes(String(op)))).toBe(false);
});

it.each(["different-source","changed-sha","changed-revision","duplicate-source","read-failed"])("refuses %s when continuing a saved research material",async variant=>{
 const open=vi.fn(()=>true),previous=bridge.call.getMockImplementation()!;
 bridge.call.mockImplementation((op:string,p:any)=>{
  if(op!=="sources_list")return previous(op,p);
  if(variant==="read-failed")return Promise.reject(Error("offline"));
  const source={source_id:variant==="different-source"?"other_source":derived.source_id,source_revision:variant==="changed-revision"?"d".repeat(64):derived.sha256,sha256:variant==="changed-sha"?"d".repeat(64):derived.sha256};
  return Promise.resolve({sources:variant==="duplicate-source"?[source,source]:[source]});
 });
 const next=await savedPublicMaterial(open);fireEvent.click(next);
 await screen.findByText("材料来源读取或版本核对失败；未切换到其他原件。请保留研究后重试。");
 expect(open).not.toHaveBeenCalled();expect(next).toBeEnabled();expect(saved).toHaveLength(1);
});

it("keeps a newly edited research draft when a source read returns late",async()=>{
 const open=vi.fn(()=>true),previous=bridge.call.getMockImplementation()!;let finish!:(value:unknown)=>void;
 bridge.call.mockImplementation((op:string,p:any)=>op==="sources_list"?new Promise(resolve=>{finish=resolve;}):previous(op,p));
 const next=await savedPublicMaterial(open);fireEvent.click(next);
 fireEvent.change(screen.getByRole("textbox",{name:"材料说明 1"}),{target:{value:"后续人工说明未保存"}});
 await act(async()=>finish({sources:[{source_id:derived.source_id,source_revision:derived.sha256,sha256:derived.sha256}]}));
 expect(open).not.toHaveBeenCalled();expect(next).toBeDisabled();
 expect(screen.getByRole("textbox",{name:"材料说明 1"})).toHaveValue("后续人工说明未保存");
});

it("keeps saved material and research when the shell refuses the page change",async()=>{
 const open=vi.fn(()=>false),previous=bridge.call.getMockImplementation()!;
 bridge.call.mockImplementation((op:string,p:any)=>op==="sources_list"?Promise.resolve({sources:[{source_id:derived.source_id,source_revision:derived.sha256,sha256:derived.sha256}]}):previous(op,p));
 const next=await savedPublicMaterial(open);fireEvent.click(next);
 await screen.findByText("页面切换已取消；研究草稿和原材料保持不变。");
 expect(open).toHaveBeenCalledOnce();expect(saved).toHaveLength(1);expect((screen.getByRole("textbox",{name:"材料说明 1"}) as HTMLTextAreaElement).value).toContain("Public metadata");
});

it("does not turn a readonly saved reference into a current-version reader action",async()=>{
 const open=vi.fn(()=>true),savedDoc=docs.get("doc_a")!;
 (savedDoc.editor_json as any).attrs.archeaxis_research.materials=[{id:"readonly_material",reference:derived,note:"固定来源材料"}];
 const sessions=new DocumentBusinessSessions(scope.workspace_id,"initial");sessions.acquire("doc_a","writer");
 render(<DocumentBusinessProvider sessions={sessions} viewId="reader"><CanonicalResearchSpace onReadSource={open}/></DocumentBusinessProvider>);
 await search();fireEvent.click(screen.getByRole("button",{name:"证据对比 (1)"}));
 const next=screen.getByRole("button",{name:"在阅读页整理材料 1"});expect(next).toBeDisabled();fireEvent.click(next);
 expect(open).not.toHaveBeenCalled();expect(bridge.call.mock.calls.some(([op])=>op==="sources_list")).toBe(false);expect(saved).toHaveLength(0);
});
