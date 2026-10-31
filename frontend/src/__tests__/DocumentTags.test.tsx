import {beforeEach,expect,it,vi} from "vitest";
import {fireEvent,render,screen,waitFor} from "@testing-library/react";
import {CanonicalLibrarySpace} from "../spaces/CanonicalLibrarySpace";
import {SavedDocumentMetadata,TagNavigation} from "../components/DocumentTags";
import {assertCoreDto,type DocumentDto} from "../api/generated/core-contract";
const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const summary={document_id:"first",title:"第一篇",version:1,source_id:null,source_revision:null,content_sha256:"a".repeat(64),tags:[{name:"Read/Next",key:"read/next"}],metadata_status:"COMPLETE" as const};
const other={...summary,document_id:"second",title:"第二篇",tags:[{name:"read",key:"read"}]};
beforeEach(()=>{
 bridge.call.mockReset();bridge.call.mockImplementation(async(op:string)=>{
  if(op==="sources_list")return {sources:[]};
  if(op==="documents_list")return {documents:[summary,other,{...summary,document_id:"empty",title:"无标签",tags:[]}],snapshot_count:3,next_cursor:null};
  throw new Error("Unexpected "+op);
 });
});
it("SYNTHETIC typed saved properties remain inert and partial metadata is visible",()=>{
 const onTag=vi.fn();
 const document={...summary,editor_json:{type:"doc",content:[]},text_projection:"",blocks:[],properties:{done:false,count:2,comment:"<script>never()</script>",nested:{keep:true}},metadata_status:"PARTIAL",metadata_issues:["INVALID_TAG"]} as DocumentDto;
 render(<SavedDocumentMetadata document={document} onTag={onTag}/>);
 expect(screen.getByRole("status")).toHaveTextContent("原文保持不变");
 fireEvent.click(screen.getByText("保存版属性（4项）"));
 expect(screen.getByText("false")).toBeVisible();expect(screen.getByText("<script>never()</script>")).toBeVisible();
 fireEvent.click(screen.getByRole("button",{name:"查看标签 Read/Next 的文档"}));expect(onTag).toHaveBeenCalledWith("read/next");
 expect(window.document.querySelector("script")).toBeNull();
});
it("SYNTHETIC metadata contract accepts older producers but rejects malformed tag assertions",()=>{
 expect(()=>assertCoreDto("DocumentSummaryDto",summary)).not.toThrow();
 for(const value of [null,["tag"],[{name:"tag",key:7}]])expect(()=>assertCoreDto("DocumentSummaryDto",{...summary,tags:value})).toThrow();
 expect(()=>assertCoreDto("DocumentSummaryDto",{...summary,metadata_status:"PASS"})).toThrow();
});
it("SYNTHETIC tag semantics include child tags, use Core keys and open the saved document ID",async()=>{
 const open=vi.fn();render(<CanonicalLibrarySpace purpose="library" onOpenDocument={open}/>);
 await screen.findByRole("button",{name:"打开文档 无标签"});
 fireEvent.change(screen.getByRole("searchbox",{name:"按标签筛选，包含下级标签"}),{target:{value:"#READ"}});
 expect(screen.getByRole("button",{name:"打开文档 第一篇"})).toBeVisible();
 expect(screen.getByRole("button",{name:"打开文档 第二篇"})).toBeVisible();
 expect(screen.queryByRole("button",{name:"打开文档 无标签"})).toBeNull();
 fireEvent.click(screen.getByRole("button",{name:"筛选标签 Read/Next，1篇已加载文档"}));
 expect(screen.queryByRole("button",{name:"打开文档 第二篇"})).toBeNull();
 fireEvent.click(screen.getByRole("button",{name:"打开文档 第一篇"}));expect(open).toHaveBeenCalledWith("first");
 expect(bridge.call.mock.calls.every(([op])=>["documents_list","sources_list"].includes(op))).toBe(true);
});
it("SYNTHETIC missing or partial metadata stays unknown and does not assert an empty tag library",async()=>{
 bridge.call.mockImplementation(async(op:string)=>op==="sources_list"?{sources:[]}:{documents:[{document_id:"old",title:"旧文档",version:1,source_id:null,source_revision:null,content_sha256:"b".repeat(64)}],snapshot_count:1,next_cursor:null});
 render(<CanonicalLibrarySpace purpose="library"/>);await screen.findByRole("button",{name:"打开文档 旧文档"});
 fireEvent.change(screen.getByRole("searchbox",{name:"按标签筛选，包含下级标签"}),{target:{value:"missing"}});
 expect(screen.getByText("部分已加载文档的标签信息未知或不完整；当前结果不能证明全库没有此标签。")).toBeVisible();
 expect(screen.queryByText("已加载文档中没有匹配标签。")).toBeNull();
});
it("SYNTHETIC combined title and tag filters do not claim an existing tag is missing",async()=>{
 render(<CanonicalLibrarySpace purpose="library"/>);await screen.findByRole("button",{name:"打开文档 第一篇"});
 fireEvent.change(screen.getByRole("searchbox",{name:"按标签筛选，包含下级标签"}),{target:{value:"read"}});
 fireEvent.change(screen.getByRole("searchbox",{name:"筛选已加载文档标题与来源"}),{target:{value:"无此标题"}});
 expect(screen.getByText("已加载文档中没有同时匹配当前筛选的内容。")).toBeVisible();
 expect(screen.queryByText("已加载文档中没有匹配标签。")).toBeNull();
});
it("SYNTHETIC cursor pagination and refresh use the saved version metadata",async()=>{
 bridge.call.mockImplementation(async(op:string,p?:{cursor?:string})=>op==="sources_list"?{sources:[]}:p?.cursor?{documents:[other],snapshot_count:2,next_cursor:null}:{documents:[summary],snapshot_count:2,next_cursor:"two"});
 render(<CanonicalLibrarySpace purpose="library"/>);await screen.findByRole("button",{name:"打开文档 第一篇"});
 fireEvent.change(screen.getByRole("searchbox",{name:"按标签筛选，包含下级标签"}),{target:{value:"read"}});
 fireEvent.click(screen.getByRole("button",{name:"加载更多文档"}));await screen.findByRole("button",{name:"打开文档 第二篇"});
 bridge.call.mockImplementation(async(op:string)=>op==="sources_list"?{sources:[]}:{documents:[{...summary,version:2,tags:[]}],snapshot_count:1,next_cursor:null});
 fireEvent.click(screen.getByRole("button",{name:"刷新资料列表"}));
 await waitFor(()=>expect(screen.queryByRole("button",{name:"打开文档 第一篇"})).toBeNull());
 expect(screen.getByText("已加载文档中没有匹配标签。")).toBeVisible();
});
it("SYNTHETIC tag navigation sorts by distinct document count and preserves the selected Core key",()=>{
 const onChange=vi.fn();
 render(<TagNavigation documents={[summary,{...other,tags:[{name:"Work",key:"work"},{name:"Work/Next",key:"work/next"}]},{...other,document_id:"third",tags:[{name:"Work/Next",key:"work/next"}]}]} value="" onChange={onChange}/>);
 fireEvent.change(screen.getByRole("combobox",{name:"标签排序方式"}),{target:{value:"count"}});
 const buttons=screen.getAllByRole("button",{name:/^筛选标签 /});
 expect(buttons[0]).toHaveAccessibleName("筛选标签 Work，2篇已加载文档");
 expect(buttons[1]).toHaveAccessibleName("筛选标签 Work/Next，2篇已加载文档");
 fireEvent.click(buttons[0]);expect(onChange).toHaveBeenCalledWith("work");
 expect(screen.getByText(/父级计数包含下级/)).toBeVisible();
});
it("SYNTHETIC hierarchical tag branches collapse independently of filtering and can return to flat view",()=>{
 const onChange=vi.fn();
 const {rerender}=render(<TagNavigation documents={[summary,other]} value="read/next" onChange={onChange}/>);
 fireEvent.change(screen.getByRole("combobox",{name:"标签显示方式"}),{target:{value:"tree"}});
 const branch=screen.getByRole("button",{name:"收起 Read 的下级标签"});
 expect(branch).toHaveAttribute("aria-expanded","true");
 expect(screen.getByRole("button",{name:"筛选标签 Read/Next，1篇已加载文档"})).toHaveAttribute("aria-pressed","true");
 fireEvent.click(branch);expect(screen.queryByRole("button",{name:"筛选标签 Read/Next，1篇已加载文档"})).toBeNull();
 expect(onChange).not.toHaveBeenCalled();
 fireEvent.change(screen.getByRole("combobox",{name:"标签显示方式"}),{target:{value:"flat"}});
 expect(screen.getByRole("button",{name:"筛选标签 Read/Next，1篇已加载文档"})).toBeVisible();
 rerender(<TagNavigation documents={[{...summary,tags:[],metadata_status:"PARTIAL"}]} value="read/next" onChange={onChange}/>);
 expect(screen.queryByRole("button",{name:/^筛选标签 /})).toBeNull();
 expect(screen.getByText(/当前结果不能证明全库没有此标签/)).toBeVisible();
});
