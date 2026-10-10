import { beforeEach, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GlobalObjectSearch } from "../components/GlobalObjectSearch";
import { CommandPalette } from "../components/CommandPalette";
const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const sha="a".repeat(64);
const found={items:[{knowledge_id:"kn-fixed",status:"candidate",active:false,head:"中文知识"}],count:1,
  transforms:[{transform_id:7,source_id:"source-fixed",engine:"text",head:"中文提取"}],transform_count:1,
  documents:[{document_id:"document-fixed",title:"中文笔记",head:"内容",version:3,content_sha256:sha}],document_count:1};
beforeEach(()=>{bridge.call.mockReset();});
it("SIMULATED: opens exact document version/SHA and immutable knowledge identity using Core search",async()=>{
  bridge.call.mockResolvedValue(found);const open=vi.fn();render(<GlobalObjectSearch query="中文" onOpen={open}/>);
  const user=userEvent.setup();await user.click(screen.getByRole("button",{name:"搜索本地内容"}));
  await user.click(await screen.findByRole("button",{name:"文档 · 中文笔记 · v3"}));
  expect(open).toHaveBeenLastCalledWith({kind:"document",document_id:"document-fixed",version:3},sha);
  await user.click(screen.getByRole("button",{name:"知识 · 中文知识"}));
  expect(open).toHaveBeenLastCalledWith({kind:"knowledge",knowledge_id:"kn-fixed"},undefined);
  expect(bridge.call).toHaveBeenCalledWith("search",{q:"中文",active_only:false});
  expect(bridge.call.mock.calls.some(([op])=>op==="machine_answer")).toBe(false);
});
it("resolves extracted text to its actual original source SHA without inventing an anchor",async()=>{
  bridge.call.mockImplementation(async(op:string)=>op==="search"?found:{source_id:"source-fixed",sha256:sha});
  const open=vi.fn();render(<GlobalObjectSearch query="中文" onOpen={open}/>);const user=userEvent.setup();
  await user.click(screen.getByRole("button",{name:"搜索本地内容"}));await user.click(await screen.findByRole("button",{name:"提取文本 · 中文提取"}));
  expect(open).toHaveBeenCalledWith({kind:"source",source_id:"source-fixed",sha256:sha},undefined);
  expect(bridge.call).toHaveBeenCalledWith("source_original",{source_id:"source-fixed"});
});
it("never navigates a source identity mismatch",async()=>{
  bridge.call.mockImplementation(async(op:string)=>op==="search"?found:{source_id:"wrong",sha256:sha});
  const open=vi.fn();render(<GlobalObjectSearch query="中文" onOpen={open}/>);const user=userEvent.setup();
  await user.click(screen.getByRole("button",{name:"搜索本地内容"}));await user.click(await screen.findByRole("button",{name:"提取文本 · 中文提取"}));
  await screen.findByRole("alert");expect(open).not.toHaveBeenCalled();
});
it("does not turn unavailable or incompatible search into zero results",async()=>{
  bridge.call.mockRejectedValue(new Error("offline"));render(<GlobalObjectSearch query="中文" onOpen={()=>{}}/>);const user=userEvent.setup();
  await user.click(screen.getByRole("button",{name:"搜索本地内容"}));await screen.findByRole("alert");
  expect(screen.queryByText(/0 个对象结果/)).not.toBeInTheDocument();
  bridge.call.mockResolvedValue({...found,document_count:2});await user.click(screen.getByRole("button",{name:"搜索本地内容"}));
  await screen.findByRole("alert");expect(screen.queryByRole("button",{name:"文档 · 中文笔记 · v3"})).not.toBeInTheDocument();
});
it("rejects stale results after query changes and respects composition and UTF-8 bounds",async()=>{
  let finish!:(value:unknown)=>void;bridge.call.mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));
  const view=render(<GlobalObjectSearch query="旧" onOpen={()=>{}}/>);
  fireEvent.click(screen.getByRole("button",{name:"搜索本地内容"}));view.rerender(<GlobalObjectSearch query="新" composing onOpen={()=>{}}/>);
  await act(async()=>finish(found));expect(screen.queryByRole("button",{name:"文档 · 中文笔记 · v3"})).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button",{name:"搜索本地内容"}));expect(bridge.call).toHaveBeenCalledTimes(1);
  view.rerender(<GlobalObjectSearch query={"中".repeat(171)} onOpen={()=>{}}/>);
  fireEvent.click(screen.getByRole("button",{name:"搜索本地内容"}));await screen.findByRole("alert");expect(bridge.call).toHaveBeenCalledTimes(1);
});
it("mounts actual content search in the global command and closes after opening the selected object",async()=>{
  bridge.call.mockResolvedValue(found);const open=vi.fn();render(<CommandPalette onNavigate={()=>{}} onOpenObject={open}/>);
  const user=userEvent.setup();await user.click(screen.getByRole("button",{name:"打开全局命令"}));
  await user.type(screen.getByRole("searchbox"),"中文");await user.click(screen.getByRole("button",{name:"搜索本地内容"}));
  await user.click(await screen.findByRole("button",{name:"文档 · 中文笔记 · v3"}));
  expect(open).toHaveBeenCalledWith({kind:"document",document_id:"document-fixed",version:3},sha);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});
