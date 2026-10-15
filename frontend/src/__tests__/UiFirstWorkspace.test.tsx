import { CommandPalette } from "../components/CommandPalette";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { CanonicalWorkspaceSpace } from "../spaces/CanonicalWorkspaceSpace";
import { resolveNavigationHash } from "../presentation/navigation";
import { UI_PAGES } from "../presentation/uiPages";
const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
afterEach(()=>{cleanup();bridge.call.mockReset();});
describe("UI-first real object entry",()=>{
  it("SIMULATED: alternate hero and quick actions preserve real objects and route through existing callbacks", async()=>{
    bridge.call.mockImplementation(async(operation:string)=>operation==="documents_list"?{documents:[{document_id:"kept_doc",title:"保留文档",version:2,source_id:null,source_revision:null,content_sha256:"hash"}]}:{items:[{item_key:"due_item",next_review:"2020-01-01T00:00:00Z"}]});
    const navigate=vi.fn(),open=vi.fn(),review=vi.fn();
    render(<div className="cabin-shell" data-navigation-appearance="top"><CanonicalWorkspaceSpace onNavigate={navigate} onOpenDocument={open} onReviewItem={review}/></div>);
    fireEvent.click(await screen.findByRole("button",{name:"保留文档 · v2"}));expect(open).toHaveBeenCalledWith("kept_doc");
    fireEvent.click(screen.getByRole("button",{name:"due_item"}));expect(review).toHaveBeenCalledWith("due_item");
    fireEvent.click(screen.getByRole("button",{name:/开始使用/}));expect(navigate).toHaveBeenLastCalledWith("intake");
    fireEvent.click(screen.getByRole("button",{name:"打开学习空间"}));expect(navigate).toHaveBeenLastCalledWith("learning");
    fireEvent.click(screen.getByRole("button",{name:"查找本地文档"}));
    expect(screen.getByRole("searchbox")).toHaveFocus();
    expect(screen.getByText("搜索本地文档",{selector:"summary"}).parentElement).toHaveAttribute("open");
    expect(bridge.call.mock.calls.map(([operation])=>operation)).toEqual(["documents_list","learning_items"]);
  });
  it.each([false,true])("keeps local search usable after an empty retained snapshot or unrelated learning failure: %s",async(failed)=>{
    bridge.call.mockImplementation(async(operation:string)=>{
      if(operation==="documents_list")return {documents:[]};
      if(operation==="learning_items"){if(failed)throw new Error("learning unavailable");return {items:[]};}
      if(operation==="search")return {documents:[{document_id:"new_doc",title:"随后保存的笔记",head:"本地正文",version:1,source_id:null,content_sha256:"a".repeat(64)}],document_count:1};
      throw new Error(operation);
    });
    const open=vi.fn();render(<CanonicalWorkspaceSpace onNavigate={vi.fn()} onOpenDocument={open}/>);
    if(failed)await screen.findByRole("alert");else await screen.findByRole("heading",{name:"从第一份资料开始"});
    fireEvent.click(screen.getByText("搜索本地文档",{selector:"summary"}));
    fireEvent.change(screen.getByRole("searchbox"),{target:{value:"随后保存"}});
    fireEvent.click(screen.getByRole("button",{name:"搜索文档"}));
    fireEvent.click(await screen.findByRole("button",{name:"随后保存的笔记 · v1"}));
    expect(open).toHaveBeenCalledWith("new_doc");
    expect(bridge.call).toHaveBeenCalledWith("search",{q:"随后保存",active_only:false});
  });
  it("shows the first-material entry only after a confirmed empty read and routes both real actions",async()=>{
    let finish:(value:unknown)=>void=()=>{};
    bridge.call.mockImplementation((operation:string)=>operation==="documents_list"?new Promise(resolve=>{finish=resolve;}):Promise.resolve({items:[]}));
    const navigate=vi.fn();render(<CanonicalWorkspaceSpace onNavigate={navigate}/>);
    expect(screen.queryByRole("heading",{name:"从第一份资料开始"})).toBeNull();
    finish({documents:[]});await screen.findByRole("heading",{name:"从第一份资料开始"});
    fireEvent.click(screen.getByRole("button",{name:/导入第一份资料/}));
    fireEvent.click(screen.getByRole("button",{name:/新建笔记与阅读/}));
    expect(navigate.mock.calls).toEqual([["intake"],["library"]]);
    expect(screen.queryByText(/到期复习/)).toBeNull();
    expect(bridge.call.mock.calls.map(([operation])=>operation)).toEqual(["documents_list","learning_items"]);
  });
  it("SIMULATED: opens the returned stable document ID without a save or model call",async()=>{
    bridge.call.mockImplementation(async(operation:string)=>operation==="documents_list"?{documents:[{document_id:"doc_actual",title:"中文笔记",version:4,source_id:null,source_revision:null,content_sha256:"hash"}]}:{items:[]});
    const open=vi.fn();render(<CanonicalWorkspaceSpace onNavigate={vi.fn()} onOpenDocument={open}/>);
    fireEvent.click(await screen.findByRole("button",{name:"中文笔记 · v4"}));
    expect(open).toHaveBeenCalledWith("doc_actual");
    expect(bridge.call.mock.calls.map(([operation])=>operation)).toEqual(["documents_list","learning_items"]);
  });
  it("SIMULATED: a refused Core read remains unavailable and retries instead of displaying an empty workspace",async()=>{
    bridge.call.mockRejectedValue(new Error("offline"));
    render(<CanonicalWorkspaceSpace onNavigate={vi.fn()}/>);
    await screen.findByRole("alert");
    expect(screen.queryByText("还没有已保存文档，可从新建笔记开始。")).toBeNull();
    bridge.call.mockResolvedValue({documents:[],items:[]});
    fireEvent.click(screen.getByRole("button",{name:"重新读取工作区"}));
    await waitFor(()=>expect(screen.queryByRole("alert")).toBeNull());
    await screen.findByRole("heading",{name:"从第一份资料开始"});
  });
  it("finds a new semantic page through global commands without treating its backing space as the page",async()=>{
    const onPage=vi.fn(); const onNavigate=vi.fn();
    render(<CommandPalette onNavigate={onNavigate} onPage={onPage}/>);
    fireEvent.click(screen.getByRole("button",{name:"打开全局命令"}));
    fireEvent.change(screen.getByRole("searchbox"),{target:{value:"纠正、评测与复测"}});
    fireEvent.click(await screen.findByRole("option"));
    expect(onPage).toHaveBeenCalledWith("14");
    expect(onNavigate).not.toHaveBeenCalled();
    expect(screen.queryByRole("dialog")).toBeNull();
  });  it("keeps old hash identities while resolving every new semantic page",()=>{
    expect(resolveNavigationHash("#space=library")).toEqual({spaceId:"library",capabilityId:null});
    expect(resolveNavigationHash("#home")).toEqual({spaceId:"workspace",capabilityId:null});
    for(const page of UI_PAGES)expect(resolveNavigationHash(`#page=${page.id}`)).toEqual({spaceId:page.space,capabilityId:null,pageId:page.id});
    expect(resolveNavigationHash("#page=99")).toBeNull();
  });
});
