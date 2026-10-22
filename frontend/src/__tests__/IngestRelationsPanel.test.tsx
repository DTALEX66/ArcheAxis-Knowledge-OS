import {beforeEach,describe,expect,it,vi} from "vitest";
import {act,fireEvent,render,screen,waitFor} from "@testing-library/react";
import {IngestRelationsPanel} from "../components/IngestRelationsPanel";
import {freezeRelations,readRelationBatch,selectedFragments,verifiedSource,verifyRelationReceipt,type RelationRead} from "../presentation/ingestRelations";
import type {DocumentDto,IngestBatchDto,IngestRelationsDto} from "../api/generated/core-contract";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const a="a".repeat(64),b="b".repeat(64),c="c".repeat(64);
const selection={batch_id:"batch",ordinal:0,workspace_id:"workspace",restore_epoch:"initial",source_id:"src_a",source_revision:a};
const doc:DocumentDto={document_id:"doc_a",version:1,source_id:"src_a",source_revision:a,title:"Note",content_sha256:c,text_projection:"saved body",blocks:[],editor_json:{type:"doc",content:[]}};
const batch:IngestBatchDto={schema:"archeaxis.ingest-batch/v1",workspace_id:"workspace",restore_epoch:"initial",batch_id:"batch",folder_label:"folder",expected_members:2,registered_members:2,complete:true,created_at:"now",next_ordinal:null,members:[
 {ordinal:0,relative_path:"note.md",byte_length:20,disposition:"pending",source_id:"src_a",source_revision:a,job_id:null,kind:null,job_state:null},
 {ordinal:1,relative_path:"image.svg",byte_length:10,disposition:"pending",source_id:"src_b",source_revision:b,job_id:null,kind:null,job_state:null},
]};
const saved={...doc,version:2,content_sha256:b};
const receipt:IngestRelationsDto={schema:"archeaxis.ingest-relations/v1",...selection,input_kind:"immutable_original_markdown",relative_path:"note.md",document:saved,added_relations:1,links:[{ordinal:0,target:"image.svg",label:null,syntax:"wiki",embed:true,fragment:null,fragment_is_block:false,status:"resolved_reference",reason:"embed_rendering_not_supported",relation_id:"ingest_ref",target_ordinal:1}],loss:["original_source_links_not_current_document_body"]};
let onApplied=vi.fn(),pending=vi.fn();
function props(dirty=false){return {selection,document:doc,documents:[doc],dirty,canWrite:true,write:async<T,>(action:()=>Promise<T>)=>action(),onApplied,onPendingChange:pending,onOpenDocument:vi.fn(),onMore:vi.fn(),hasMore:false};}
beforeEach(()=>{onApplied=vi.fn();pending=vi.fn();bridge.call.mockReset();bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>)=>{
 if(op==="ingest_batch_get")return structuredClone(batch);
 if(op==="ingest_member_relations_apply")return structuredClone(receipt);
 if(op==="document_version")return p.version===2?structuredClone(saved):structuredClone(doc);
 if(op==="document_get")return structuredClone(saved);
 if(op==="document_graph")return {center:{document_id:"doc_a",version:2,content_sha256:b},edges:[]};
 throw new Error(op);
});});
async function ready(){fireEvent.click(screen.getByRole("button",{name:"读取完整批次映射"}));await screen.findByLabelText("链接目标 image.svg");fireEvent.change(screen.getByLabelText("链接目标 image.svg"),{target:{value:"source"}});}
describe("SYNTHETIC explicit folder relation consumer",()=>{
 it("sends selected source identity once, reads exact saved version and existing graph",async()=>{
  render(<IngestRelationsPanel {...props()}/>);await ready();fireEvent.click(screen.getByRole("button",{name:"确认映射并保存原件关系"}));
  await waitFor(()=>expect(onApplied).toHaveBeenCalledWith(saved));
  expect(bridge.call).toHaveBeenCalledWith("ingest_member_relations_apply",{batch_id:"batch",ordinal:0,body:{workspace_id:"workspace",restore_epoch:"initial",source_id:"src_a",source_revision:a,document_id:"doc_a",expected_version:1,content_sha256:c,targets:[{ordinal:1,source_id:"src_b",source_revision:b}]}});
  expect(bridge.call).toHaveBeenCalledWith("document_version",{document_id:"doc_a",version:2});
  await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("document_graph",{document_id:"doc_a",version:2}));
  expect(pending.mock.calls.map(c=>c[0])).toEqual([true,false]);
 });
 it("retains lost ACK request, reads UNKNOWN without resending or rebasing",async()=>{
  const normal=bridge.call.getMockImplementation()!;bridge.call.mockImplementation((op,p)=>op==="ingest_member_relations_apply"?Promise.reject(new Error("ACK lost")):normal(op,p));
  render(<IngestRelationsPanel {...props()}/>);await ready();fireEvent.click(screen.getByRole("button",{name:"确认映射并保存原件关系"}));await screen.findByRole("alert");
  fireEvent.click(screen.getByRole("button",{name:"只读核对原关系请求"}));await screen.findByText(/缺少原操作回执，仍为 UNKNOWN/);
  expect(bridge.call.mock.calls.filter(([op])=>op==="ingest_member_relations_apply")).toHaveLength(1);
  expect(onApplied).not.toHaveBeenCalled();expect(pending.mock.calls.map(c=>c[0])).toEqual([true]);
  expect(screen.getByRole("button",{name:"确认映射并保存原件关系"})).toBeDisabled();
 });
 it("blocks dirty and source-mismatched documents",async()=>{
  const view=render(<IngestRelationsPanel {...props(true)}/>);await ready();expect(screen.getByRole("button",{name:"确认映射并保存原件关系"})).toBeDisabled();
  view.rerender(<IngestRelationsPanel {...props()} document={{...doc,source_id:"foreign"}}/>);expect(screen.getByRole("button",{name:"确认映射并保存原件关系"})).toBeDisabled();expect(bridge.call.mock.calls.some(([op])=>op==="ingest_member_relations_apply")).toBe(false);
 });
 it("rechecks restore epoch immediately before applying and sends no write",async()=>{
  render(<IngestRelationsPanel {...props()}/>);await ready();const normal=bridge.call.getMockImplementation()!;bridge.call.mockImplementation((op,p)=>op==="ingest_batch_get"?Promise.resolve({...batch,restore_epoch:"restored"}):normal(op,p));
  fireEvent.click(screen.getByRole("button",{name:"确认映射并保存原件关系"}));await screen.findByText(/批次或恢复身份已变化/);expect(bridge.call.mock.calls.some(([op])=>op==="ingest_member_relations_apply")).toBe(false);
 });
 it("does not publish a response carrying a different source or version",async()=>{
  const normal=bridge.call.getMockImplementation()!;bridge.call.mockImplementation((op,p)=>op==="ingest_member_relations_apply"?Promise.resolve({...receipt,source_id:"foreign"}):normal(op,p));
  render(<IngestRelationsPanel {...props()}/>);await ready();fireEvent.click(screen.getByRole("button",{name:"确认映射并保存原件关系"}));await screen.findByText(/关系回执与固定版本读回不符/);expect(onApplied).not.toHaveBeenCalled();expect(screen.getByRole("alert")).toHaveTextContent("UNKNOWN");
 });
 it("does not submit when editing begins during the fresh batch read",async()=>{
  const view=render(<IngestRelationsPanel {...props()}/>);await ready();let release!:(v:IngestBatchDto)=>void;bridge.call.mockImplementation(()=>new Promise(resolve=>{release=resolve;}));
  fireEvent.click(screen.getByRole("button",{name:"确认映射并保存原件关系"}));view.rerender(<IngestRelationsPanel {...props(true)}/>);await act(async()=>release(batch));
  await screen.findByText(/准备期间文档或草稿改变/);expect(bridge.call.mock.calls.some(([op])=>op==="ingest_member_relations_apply")).toBe(false);
 });
});
describe("fixed identity guards",()=>{
 it("explicit fragments bind only the chosen pinned document block and retain the original link identity",()=>{
  const peer:DocumentDto={...doc,document_id:"peer",source_id:"src_b",source_revision:b,blocks:[{block_id:"selected",kind:"paragraph",ordinal:0,node_json:{},text_projection:"Target",codec_status:"known"}]};
  const targets=[{ordinal:1,source_id:"src_b",source_revision:b,document:{document_id:"peer",version:1,content_sha256:c}}];
  const r={...receipt,links:[{...receipt.links[0],fragment:"Heading",fragment_is_block:false,target_ordinal:1}]};
  expect(selectedFragments(r,{0:"selected"},targets,{1:peer})).toEqual([{link_ordinal:0,target_ordinal:1,fragment:"Heading",fragment_is_block:false,block_id:"selected"}]);
  expect(selectedFragments(r,{},targets,{1:peer})).toEqual([]);
  for(const snapshot of [{...peer,version:2},{...peer,content_sha256:a},{...peer,document_id:"wrong"},{...peer,blocks:[]}])expect(()=>selectedFragments(r,{0:"selected"},targets,{1:snapshot})).toThrow();
  expect(()=>selectedFragments(r,{99:"selected"},targets,{1:peer})).toThrow();
  expect(()=>selectedFragments(r,{0:"selected"},[],{1:peer})).toThrow();
 });
 it("refuses source substitution and stale or incomplete batch pagination",async()=>{
  expect(()=>verifiedSource({source_id:"other",source_revision:a,sha256:a,original_name:"same",imported_at:"now"},"src_a",a)).toThrow();
  for(const value of [{...batch,complete:false},{...batch,workspace_id:"other"},{...batch,members:[batch.members[0],batch.members[0]]},{...batch,members:[batch.members[0]],next_ordinal:null}])await expect(readRelationBatch((async()=>value) as RelationRead,selection)).rejects.toThrow();
 });
 it("requires same-batch targets, saved document binding and a clean draft",()=>{
  expect(()=>freezeRelations(selection,batch,doc,[],true)).toThrow();
  expect(()=>freezeRelations(selection,batch,doc,[{ordinal:1,source_id:"foreign",source_revision:b}],false)).toThrow();
  expect(()=>freezeRelations(selection,batch,doc,[{ordinal:0,source_id:"src_a",source_revision:a}],false)).toThrow();
  const f=freezeRelations(selection,batch,doc,[],false);expect(()=>verifyRelationReceipt(f,receipt,{...saved,version:3})).toThrow();
 });
});

it("offers fixed blocks after the real relation receipt and sends the explicit selection through the same operation",async()=>{
 const peer:DocumentDto={...doc,document_id:"peer",source_id:"src_b",source_revision:b,title:"Peer",blocks:[{block_id:"chosen",kind:"paragraph",ordinal:0,node_json:{},text_projection:"Chosen content",codec_status:"known"}]};
 const notes={...batch,members:[batch.members[0],{...batch.members[1],relative_path:"peer.md"}]};
 const unresolved={...receipt,document:doc,added_relations:0,links:[{...receipt.links[0],target:"peer",embed:false,fragment:"Heading",fragment_is_block:false,status:"unresolved",reason:"fragment_resolution_not_supported",relation_id:null}]};
 let applies=0;
 bridge.call.mockImplementation(async(op,p)=>{
  if(op==="ingest_batch_get")return notes;
  if(op==="document_version")return p.document_id==="peer"?peer:p.version===2?saved:doc;
  if(op==="ingest_member_relations_apply")return ++applies===1?unresolved:{...unresolved,document:saved,added_relations:1};
  if(op==="document_graph")return {center:{document_id:"doc_a",version:p.version,content_sha256:p.version===1?c:b},edges:[]};
  throw new Error(op);
 });
 render(<IngestRelationsPanel {...props()} documents={[doc,peer]}/>);
 fireEvent.click(screen.getByRole("button",{name:"读取完整批次映射"}));await screen.findByLabelText("链接目标 peer.md");
 fireEvent.change(screen.getByLabelText("链接目标 peer.md"),{target:{value:"peer"}});
 fireEvent.click(screen.getByRole("button",{name:"确认映射并保存原件关系"}));await screen.findByLabelText("固定块映射 0");
 await waitFor(()=>expect(screen.getByLabelText("固定块映射 0")).toBeEnabled());
 fireEvent.change(screen.getByLabelText("固定块映射 0"),{target:{value:"chosen"}});
 fireEvent.click(screen.getByRole("button",{name:"确认映射并保存原件关系"}));await waitFor(()=>expect(applies).toBe(2));
 const calls=bridge.call.mock.calls.filter(([op])=>op==="ingest_member_relations_apply");
 expect(calls[0][1].body.fragment_bindings).toBeUndefined();
 expect(calls[1][1].body.fragment_bindings).toEqual([{link_ordinal:0,target_ordinal:1,fragment:"Heading",fragment_is_block:false,block_id:"chosen"}]);
 await waitFor(()=>expect(onApplied).toHaveBeenLastCalledWith(saved));
});

it("accepts an embed-only upgrade version increment and rejects an unadvanced version", async()=>{
 const attempt=freezeRelations(selection,batch,doc,[{ordinal:1,source_id:"src_b",source_revision:b}],false);
 const upgrade={...receipt,added_relations:0,updated_relations:1};
 expect(verifyRelationReceipt(attempt,upgrade,saved)).toEqual(saved);
 expect(()=>verifyRelationReceipt(attempt,{...upgrade,document:doc},doc)).toThrow("关系回执");
});
