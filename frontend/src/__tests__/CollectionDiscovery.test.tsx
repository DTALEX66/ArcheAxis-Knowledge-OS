import {beforeEach,expect,it,vi} from "vitest";
import {fireEvent,render,screen,waitFor,within} from "@testing-library/react";
import {CanonicalLibrarySpace} from "../spaces/CanonicalLibrarySpace";
import {assertCoreDto,type DocumentSummaryDto} from "../api/generated/core-contract";
const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const note:DocumentSummaryDto={document_id:"ordinary",title:"普通笔记",version:2,source_id:null,source_revision:null,content_sha256:"a".repeat(64),has_collection:false};
const collection:DocumentSummaryDto={...note,document_id:"collection",title:"读书集合",version:3,has_collection:true};
beforeEach(()=>{
 bridge.call.mockReset();bridge.call.mockImplementation(async(op:string)=>{
  if(op==="sources_list")return {sources:[]};
  if(op==="documents_list")return {documents:[note,collection],snapshot_count:2,next_cursor:null};
  throw new Error("Unexpected "+op);
 });
});
it("SYNTHETIC discovers saved collection documents and opens their real ID without fetching every body",async()=>{
 const open=vi.fn();render(<CanonicalLibrarySpace purpose="library" onOpenDocument={open}/>);
 await screen.findByRole("button",{name:"打开文档 普通笔记"});
 fireEvent.click(screen.getByRole("button",{name:"集合文档"}));
 expect(screen.queryByRole("button",{name:"打开文档 普通笔记"})).toBeNull();
 fireEvent.click(screen.getByRole("button",{name:"打开文档 读书集合"}));
 expect(open).toHaveBeenCalledWith("collection");
 expect(bridge.call.mock.calls.every(([op])=>["documents_list","sources_list"].includes(op))).toBe(true);
});
it("SYNTHETIC missing legacy summary metadata is unknown, never a confirmed empty collection list",async()=>{
 const {has_collection:_,...legacy}=note;
 bridge.call.mockImplementation(async(op:string)=>op==="sources_list"?{sources:[]}:{documents:[legacy],snapshot_count:1,next_cursor:null});
 render(<CanonicalLibrarySpace purpose="library"/>);
 await screen.findByRole("button",{name:"打开文档 普通笔记"});
 fireEvent.click(screen.getByRole("button",{name:"集合文档"}));
 expect(within(screen.getByRole("navigation",{name:"已保存文档"})).getByRole("status")).toHaveTextContent("部分已加载文档未提供集合信息");
 expect(screen.queryByText("当前列表没有集合文档。")).toBeNull();
});
it("SYNTHETIC collection discovery shares the document cursor and can find a collection on a later page",async()=>{
 bridge.call.mockImplementation(async(op:string,p?:{cursor?:string})=>op==="sources_list"?{sources:[]}:p?.cursor?{documents:[collection],snapshot_count:2,next_cursor:null}:{documents:[note],snapshot_count:2,next_cursor:"page_two"});
 render(<CanonicalLibrarySpace purpose="library"/>);
 await screen.findByRole("button",{name:"打开文档 普通笔记"});
 fireEvent.click(screen.getByRole("button",{name:"集合文档"}));
 expect(screen.getByText("已加载文档中没有集合；可继续加载更多文档。")).toBeVisible();
 fireEvent.click(screen.getByRole("button",{name:"加载更多文档"}));
 expect(await screen.findByRole("button",{name:"打开文档 读书集合"})).toBeVisible();
 expect(bridge.call).toHaveBeenCalledWith("documents_list",{cursor:"page_two"});
 expect(screen.getByRole("button",{name:"集合文档"})).toHaveAttribute("aria-pressed","true");
});
it("SYNTHETIC a paging failure retains already discovered collections and allows retry",async()=>{
 bridge.call.mockImplementation(async(op:string,p?:{cursor?:string})=>{
  if(op==="sources_list")return {sources:[]};if(p?.cursor)throw new Error("offline");
  return {documents:[collection],snapshot_count:2,next_cursor:"page_two"};
 });
 render(<CanonicalLibrarySpace purpose="library"/>);
 await screen.findByRole("button",{name:"打开文档 读书集合"});
 fireEvent.click(screen.getByRole("button",{name:"集合文档"}));
 fireEvent.click(screen.getByRole("button",{name:"加载更多文档"}));
 expect(await screen.findByRole("alert")).toHaveTextContent("已加载文档与草稿仍保留");
 expect(screen.getByRole("button",{name:"打开文档 读书集合"})).toBeVisible();
 expect(screen.getByRole("button",{name:"加载更多文档"})).toBeEnabled();
});
it("SYNTHETIC refresh uses the latest saved summary without deleting or editing the document",async()=>{
 render(<CanonicalLibrarySpace purpose="library"/>);
 await screen.findByRole("button",{name:"打开文档 读书集合"});
 fireEvent.click(screen.getByRole("button",{name:"集合文档"}));
 bridge.call.mockImplementation(async(op:string)=>op==="sources_list"?{sources:[]}:{documents:[{...collection,version:4,has_collection:false}],snapshot_count:1,next_cursor:null});
 fireEvent.click(screen.getByRole("button",{name:"刷新资料列表"}));
 await waitFor(()=>expect(screen.queryByRole("button",{name:"打开文档 读书集合"})).toBeNull());
 expect(screen.getByText("当前列表没有集合文档。")).toBeVisible();
 fireEvent.click(screen.getByRole("button",{name:"全部内容"}));
 expect(screen.getByRole("button",{name:"打开文档 读书集合"})).toBeVisible();
 expect(within(screen.getByRole("navigation",{name:"已保存文档"})).getByText("v4")).toBeVisible();
 expect(bridge.call.mock.calls.every(([op])=>["documents_list","sources_list"].includes(op))).toBe(true);
});
it("SYNTHETIC summary contract accepts optional boolean presence, rejects invalid claims",()=>{
 expect(()=>assertCoreDto("DocumentSummaryDto",collection)).not.toThrow();
 const {has_collection:_,...legacy}=note;expect(()=>assertCoreDto("DocumentSummaryDto",legacy)).not.toThrow();
 for(const value of [null,"true",1])expect(()=>assertCoreDto("DocumentSummaryDto",{...note,has_collection:value})).toThrow();
});
it("SYNTHETIC title filtering does not turn an unmatched saved collection into a claim that none exists",async()=>{
 render(<CanonicalLibrarySpace purpose="library"/>);
 await screen.findByRole("button",{name:"打开文档 读书集合"});
 fireEvent.click(screen.getByRole("button",{name:"集合文档"}));
 fireEvent.change(screen.getByRole("searchbox",{name:"筛选已加载文档标题与来源"}),{target:{value:"不存在的标题"}});
 expect(screen.getByText("已加载集合中没有匹配文档。")).toBeVisible();
 expect(screen.queryByText("当前列表没有集合文档。")).toBeNull();
});
