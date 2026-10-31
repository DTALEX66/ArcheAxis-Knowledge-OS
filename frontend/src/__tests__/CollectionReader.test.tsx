import {webcrypto} from "node:crypto";
import {beforeEach,expect,it,vi} from "vitest";
import {act,fireEvent,render,screen,waitFor,within} from "@testing-library/react";
import {CollectionPanel} from "../components/CollectionPanel";
import {CanonicalLibrarySpace} from "../spaces/CanonicalLibrarySpace";
import type {DocumentDto} from "../api/generated/core-contract";
import type {Collection} from "../api/generated/collection-contract";
const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
vi.mock("../components/DocumentEditor",()=>({DocumentEditor:()=> <p>保存正文</p>}));
vi.mock("../components/DocumentEmbeds",()=>({DocumentEmbeds:()=>null}));
const definition:Collection={schema:"archeaxis.collection/v1",properties:[{property_id:"name",name:"名称",kind:"text"},{property_id:"state",name:"状态",kind:"select",options:["待整理"]},{property_id:"day",name:"日期",kind:"date"}],records:[{record_id:"row-engine-id",reference:{kind:"document",document_id:"target-real",version:1},values:{name:"实际条目",state:"待整理",day:"2026-10-22"}}],views:["table","list","board","calendar","gallery"].map(kind=>({view_id:kind,name:kind,kind:kind as "table",...(kind==="board"?{group_by:"state"}:kind==="calendar"?{date_property:"day"}:{})})),source_payload:{foreign:{retain:true}}};
const doc:DocumentDto={document_id:"collection-doc",version:3,content_sha256:"a".repeat(64),title:"资料集合",source_id:null,source_revision:null,editor_json:{type:"doc",attrs:{archeaxis_collection:definition,foreign:{keep:true}},content:[]},text_projection:"保存正文",blocks:[]};
function response(d=doc,id="table"){return {schema:"archeaxis.collection-projection/v1",document_id:d.document_id,version:d.version,content_sha256:d.content_sha256,engine_version:"archeaxis.bounded-formula/v1",view:definition.views.find(v=>v.view_id===id),definition,total:1,items:definition.records.map(r=>({...r,formula_errors:{},formulas:[]})),group_counts:{},next_offset:null,canonical_writer:"Document",full_media_package:false};}
beforeEach(()=>{
 vi.stubGlobal("crypto",webcrypto);bridge.call.mockReset();bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>={})=>{
  if(op==="sources_list")return {sources:[]};if(op==="documents_list")return {documents:[doc],snapshot_count:1,next_cursor:null};if(op==="document_get")return doc;
  if(op==="document_checks")return {document_id:doc.document_id,version:3,content_sha256:doc.content_sha256,default_status:"unverified",historical:false,checks:[],checks_capped:false,next_offset:null};
  if(op==="collection_query")return response(doc,String(p.view_id));throw new Error("Unexpected "+op);
 });
});
it.each(["table","list","board","calendar","gallery"])("SYNTHETIC reader %s uses the saved Core view and exposes no definition editors",async kind=>{
 const onChange=vi.fn();render(<CollectionPanel document={doc} value={definition} onChange={onChange} presentation="reader"/>);
 expect(screen.queryByText("添加属性")).toBeNull();expect(screen.queryByRole("textbox")).toBeNull();
 fireEvent.change(screen.getByRole("combobox",{name:"读取保存版视图"}),{target:{value:kind}});
 fireEvent.click(screen.getByRole("button",{name:"读取已保存视图"}));
 expect(await screen.findByText("实际条目")).toBeVisible();expect(bridge.call).toHaveBeenLastCalledWith("collection_query",{document_id:doc.document_id,version:3,view_id:kind,offset:0,limit:20});
 expect(onChange).not.toHaveBeenCalled();expect(screen.queryByText("row-engine-id")).toBeNull();
});
it("SYNTHETIC normal reader consumes its saved collection and opens the exact fixed record reference",async()=>{
 const open=vi.fn();render(<CanonicalLibrarySpace purpose="reader" initialDocumentId={doc.document_id} onOpenReference={open}/>);
 const panel=await screen.findByRole("region",{name:"集合属性与视图"});
 fireEvent.click(within(panel).getByRole("button",{name:"读取已保存视图"}));
 await within(panel).findByText("实际条目");
 fireEvent.click(within(panel).getByRole("button",{name:"查看文档 v1"}));
 expect(open).toHaveBeenCalledWith({kind:"document",document_id:"target-real",version:1});
 expect(bridge.call.mock.calls.some(([op])=>["document_create","document_draft"].includes(op))).toBe(false);
});
it("SYNTHETIC rejects another saved version instead of showing it as the selected view",async()=>{
 bridge.call.mockResolvedValue({...response(),version:2});render(<CollectionPanel document={doc} value={definition} onChange={vi.fn()} presentation="reader"/>);
 fireEvent.click(screen.getByRole("button",{name:"读取已保存视图"}));
 expect(await screen.findByRole("alert")).toHaveTextContent("已保存快照不一致");expect(screen.queryByText("实际条目")).toBeNull();
});
it("SYNTHETIC late projection cannot replace a newly selected document",async()=>{
 let resolve!:(v:unknown)=>void;bridge.call.mockImplementation(()=>new Promise(r=>{resolve=r;}));
 const view=render(<CollectionPanel document={doc} value={definition} onChange={vi.fn()} presentation="reader"/>);
 fireEvent.click(screen.getByRole("button",{name:"读取已保存视图"}));await waitFor(()=>expect(resolve).toBeTypeOf("function"));
 view.rerender(<CollectionPanel document={{...doc,document_id:"other",content_sha256:"b".repeat(64)}} value={definition} onChange={vi.fn()} presentation="reader"/>);
 await act(async()=>{resolve(response());});expect(screen.queryByText("实际条目")).toBeNull();
 expect(screen.getByRole("button",{name:"读取已保存视图"})).toBeEnabled();
});
