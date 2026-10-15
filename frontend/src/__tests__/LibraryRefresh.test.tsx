import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { createHash, webcrypto } from "node:crypto";
import { DockWorkspace } from "../workspace/DockWorkspace";
import { CanonicalLibrarySpace } from "../spaces/CanonicalLibrarySpace";
const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
vi.mock("../spaces/CanonicalWorkspaceSpace",()=>({CanonicalWorkspaceSpace:()=> <p>SIMULATED 工作台</p>}));
vi.mock("../templates/TemplateWorkspace",()=>({TemplateLauncher:()=>null}));
vi.mock("../components/FolderIngest",()=>({FolderIngest:()=>null}));
class ResizeObserverStub {observe(){} unobserve(){} disconnect(){}}
const hash=createHash("sha256").update("原始导入内容").digest("hex");
const source={source_id:"imported-source",source_revision:hash,sha256:hash,original_name:"WebDriver证据.txt",imported_at:"2026-10-15"};
const documentRow=(id:string)=>({document_id:id,source_id:null,source_revision:null,title:id,version:1,content_sha256:hash});
let imported=false;
beforeEach(()=>{
  vi.stubGlobal("ResizeObserver",ResizeObserverStub);vi.stubGlobal("crypto",webcrypto);bridge.call.mockReset();imported=false;
  bridge.call.mockImplementation(async(op:string)=>{
    if(op==="sources_list")return {sources:imported?[source]:[]};
    if(op==="documents_list")return {documents:[],next_cursor:null,snapshot_count:0};
    if(op==="source_original")return {source_id:source.source_id,name:source.original_name,media_type:"text/plain",sha256:hash,content_base64:Buffer.from("原始导入内容").toString("base64")};
    if(op==="anchors_list")return {anchors:[]};
    if(op==="jobs_list")return {jobs:[]};
    throw new Error(op);
  });
});
afterEach(()=>vi.unstubAllGlobals());
const dockProps={spaceId:"library" as const,onInspect:vi.fn(),onNavigate:vi.fn()};
it("rereads the retained real library when a Dockview panel becomes visible after an outside import",async()=>{
  const view=render(<DockWorkspace {...dockProps}/>);
  await waitFor(()=>expect(bridge.call.mock.calls.some(([op])=>op==="sources_list")).toBe(true));
  const input=screen.getByLabelText("导入原件");
  view.rerender(<DockWorkspace {...dockProps} spaceId="workspace"/>);await screen.findByText("SIMULATED 工作台");
  imported=true;
  view.rerender(<DockWorkspace {...dockProps}/>);
  fireEvent.click(await screen.findByRole("button",{name:"WebDriver证据.txt"}));
  await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("source_original",{source_id:source.source_id}));
  expect(screen.getByLabelText("导入原件")).toBe(input);
});
it("rereads list metadata when a different importer announces a completed batch",async()=>{
  render(<CanonicalLibrarySpace/>);await waitFor(()=>expect(bridge.call.mock.calls.some(([op])=>op==="sources_list")).toBe(true));
  imported=true;act(()=>window.dispatchEvent(new Event("archeaxis-job-changed")));
  expect(await screen.findByRole("button",{name:"WebDriver证据.txt"})).toBeInTheDocument();
});
it("refreshes a closed and reopened retained panel without replacing its mounted content",async()=>{
  const view=render(<DockWorkspace {...dockProps}/>);const input=await screen.findByLabelText("导入原件");
  fireEvent.click(screen.getByRole("button",{name:"关闭当前视图"}));imported=true;
  view.rerender(<DockWorkspace {...dockProps} spaceId="workspace"/>);await screen.findByText("SIMULATED 工作台");view.rerender(<DockWorkspace {...dockProps}/>);
  await screen.findByRole("button",{name:"WebDriver证据.txt"});expect(screen.getByLabelText("导入原件")).toBe(input);
});
it("keeps the loaded lists on refresh failure and exposes an explicit retry",async()=>{
  imported=true;render(<CanonicalLibrarySpace/>);await screen.findByRole("button",{name:"WebDriver证据.txt"});
  bridge.call.mockRejectedValueOnce(new Error("temporary source list failure"));fireEvent.click(screen.getByRole("button",{name:"刷新资料列表"}));
  await screen.findByText(/资料列表刷新失败/);expect(screen.getByRole("button",{name:"WebDriver证据.txt"})).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button",{name:"刷新资料列表"}));await waitFor(()=>expect(screen.queryByText(/资料列表刷新失败/)).not.toBeInTheDocument());
  expect(screen.getByRole("button",{name:"WebDriver证据.txt"})).toBeInTheDocument();
});
it("ignores a delayed earlier list read after a newer activation snapshot",async()=>{
  let release!:(value:unknown)=>void;let first=true;
  bridge.call.mockImplementation(async(op:string)=>{if(op==="sources_list")return {sources:[]};if(first){first=false;return new Promise(resolve=>{release=resolve;});}return {documents:[documentRow("new snapshot")],next_cursor:null,snapshot_count:1};});
  const view=render(<CanonicalLibrarySpace activationRevision={1}/>);view.rerender(<CanonicalLibrarySpace activationRevision={2}/>);
  await screen.findByRole("button",{name:"new snapshot · 文档"});
  await act(async()=>release({documents:[documentRow("late old snapshot")],next_cursor:"old",snapshot_count:2}));
  expect(screen.queryByRole("button",{name:"late old snapshot · 文档"})).not.toBeInTheDocument();expect(screen.queryByRole("button",{name:"加载更多文档"})).not.toBeInTheDocument();
});
it("isolates old pagination results and finalizers from the refreshed snapshot",async()=>{
  let fresh=false,oldPage!:(value:unknown)=>void,newPage!:(value:unknown)=>void;
  bridge.call.mockImplementation(async(op:string,payload?:{cursor?:string})=>{
    if(op==="sources_list")return {sources:[]};
    if(payload?.cursor==="old")return new Promise(resolve=>{oldPage=resolve;});
    if(payload?.cursor==="new")return new Promise(resolve=>{newPage=resolve;});
    return {documents:[documentRow(fresh?"new first":"old first")],next_cursor:fresh?"new":"old",snapshot_count:fresh?3:2};
  });
  render(<CanonicalLibrarySpace/>);fireEvent.click(await screen.findByRole("button",{name:"加载更多文档"}));fresh=true;
  act(()=>window.dispatchEvent(new Event("archeaxis-job-changed")));await screen.findByRole("button",{name:"new first · 文档"});
  fireEvent.click(screen.getByRole("button",{name:"加载更多文档"}));
  await act(async()=>oldPage({documents:[documentRow("late old page")],next_cursor:null,snapshot_count:2}));
  expect(screen.getByRole("button",{name:"正在加载文档…"})).toBeDisabled();expect(screen.queryByRole("button",{name:"late old page · 文档"})).not.toBeInTheDocument();
  await act(async()=>newPage({documents:[documentRow("new second")],next_cursor:null,snapshot_count:3}));
  expect(screen.getByRole("button",{name:"new second · 文档"})).toBeInTheDocument();expect(screen.queryByRole("button",{name:"加载更多文档"})).not.toBeInTheDocument();
});

it("resolves a new source navigation target from a fresh snapshot only once",async()=>{
  const view=render(<CanonicalLibrarySpace activationRevision={1}/>);await waitFor(()=>expect(screen.getByRole("button",{name:"刷新资料列表"})).toBeEnabled());
  imported=true;const target={source_id:source.source_id,source_revision:hash,sha256:hash};
  view.rerender(<CanonicalLibrarySpace activationRevision={2} initialSourceTarget={target}/>);
  expect(await screen.findByLabelText("原件正文")).toHaveTextContent("原始导入内容");
  const reads=bridge.call.mock.calls.filter(([op])=>op==="source_original").length;
  act(()=>window.dispatchEvent(new Event("archeaxis-job-changed")));await waitFor(()=>expect(screen.getByRole("button",{name:"刷新资料列表"})).toBeEnabled());
  expect(bridge.call.mock.calls.filter(([op])=>op==="source_original")).toHaveLength(reads);
});

it("retries an unresolved source navigation after list failure without using old metadata",async()=>{
  const view=render(<CanonicalLibrarySpace/>);await waitFor(()=>expect(screen.getByRole("button",{name:"刷新资料列表"})).toBeEnabled());
  imported=true;bridge.call.mockRejectedValueOnce(new Error("source list unavailable"));
  view.rerender(<CanonicalLibrarySpace initialSourceTarget={{source_id:source.source_id,source_revision:hash,sha256:hash}}/>);
  await screen.findByText(/资料列表刷新失败/);expect(bridge.call.mock.calls.some(([op])=>op==="source_original")).toBe(false);
  fireEvent.click(screen.getByRole("button",{name:"刷新资料列表"}));expect(await screen.findByLabelText("原件正文")).toHaveTextContent("原始导入内容");
});
it("a manual source selection wins over a delayed navigation snapshot",async()=>{
  imported=true;const view=render(<CanonicalLibrarySpace/>);await screen.findByRole("button",{name:"WebDriver证据.txt"});
  const originalCall=bridge.call.getMockImplementation()!;let release!:(value:unknown)=>void;
  const other={...source,source_id:"later-source",original_name:"later.txt"};
  bridge.call.mockImplementation(async(op,payload)=>op==="sources_list"?new Promise(resolve=>{release=resolve;}):originalCall(op,payload));
  view.rerender(<CanonicalLibrarySpace initialSourceTarget={{source_id:other.source_id,source_revision:hash,sha256:hash}}/>);
  fireEvent.click(screen.getByRole("button",{name:"WebDriver证据.txt"}));await screen.findByLabelText("原件正文");
  await act(async()=>release({sources:[source,other]}));expect(bridge.call).not.toHaveBeenCalledWith("source_original",{source_id:other.source_id});
  expect(screen.getByLabelText("原件正文")).toHaveTextContent("原始导入内容");
});

it("retries a failed source read from the reader refresh control and consumes only success",async()=>{
  imported=true;let fail=true;const served=bridge.call.getMockImplementation()!;
  bridge.call.mockImplementation(async(op,payload)=>{if(op==="source_original"&&fail){fail=false;throw new Error("original temporarily unavailable");}return served(op,payload);});
  render(<CanonicalLibrarySpace purpose="reader" initialSourceTarget={{source_id:source.source_id,source_revision:hash,sha256:hash}}/>);
  await screen.findByText(/读取未完成/);expect(bridge.call.mock.calls.filter(([op])=>op==="source_original")).toHaveLength(1);
  fireEvent.click(screen.getByRole("button",{name:"刷新资料列表"}));expect(await screen.findByLabelText("并排原件正文")).toHaveTextContent("原始导入内容");
  fireEvent.click(screen.getByRole("button",{name:"刷新资料列表"}));await waitFor(()=>expect(screen.getByRole("button",{name:"刷新资料列表"})).toBeEnabled());
  expect(bridge.call.mock.calls.filter(([op])=>op==="source_original")).toHaveLength(2);
});
