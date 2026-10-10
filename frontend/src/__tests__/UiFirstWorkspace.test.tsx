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
    await screen.findByText("还没有已保存文档，可从新建笔记开始。");
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
