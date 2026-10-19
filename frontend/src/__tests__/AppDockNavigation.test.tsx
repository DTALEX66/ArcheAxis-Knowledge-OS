import {act,fireEvent,render,screen,waitFor} from "@testing-library/react";
import {afterEach,beforeEach,expect,it,vi} from "vitest";
import {useState} from "react";
import {webcrypto} from "node:crypto";
import {App} from "../app/App";
import {getRecoveryStatus} from "../api/workspace";
import {verifyCanonicalCore} from "../api/core";
import type {WorkingRead,WorkingState} from "../presentation/coreWorkingState";
import {layoutPresets} from "../workspace/WorkspaceController";

const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call,verifyCanonicalCore:vi.fn().mockResolvedValue(undefined)}));
vi.mock("../api/workspace",async original=>({...await original<typeof import("../api/workspace")>(),getRecoveryStatus:vi.fn().mockResolvedValue({state:"ready",safe_mode:false,backend_available:true,message:"SIMULATED ready",backups:[],external_dev:false})}));
vi.mock("../spaces/SpaceView",async original=>({...await original<typeof import("../spaces/SpaceView")>(),SpaceView:(props:{uiPageId?:string;initialDocumentId?:string;onOpenDocument?:(id:string)=>void;onOpenPage?:(id:string)=>void})=>{
 const [draft,setDraft]=useState("");
 return <section aria-label={`SIMULATED view ${props.uiPageId}`}><output data-testid="dock-document">{props.initialDocumentId}</output><input aria-label={`draft-${props.uiPageId}`} value={draft} onChange={event=>setDraft(event.target.value)}/><button onClick={()=>props.onOpenDocument?.("doc_a")}>模拟打开A</button><button onClick={()=>props.onOpenDocument?.("doc_b")}>模拟打开B</button><button onClick={()=>props.onOpenPage?.("22")}>模拟查看回执</button><button onClick={()=>props.onOpenPage?.("14")}>SIMULATED goto 14</button></section>;
}}));
class ResizeObserverStub{observe(){}unobserve(){}disconnect(){}}
let read:WorkingRead;
let resolveLayout:(value:unknown)=>void;
const layoutReply=()=>({status:200,body:{workspace_id:read.workspace_id,restore_epoch:"initial",device_id:"device_1",revision:0,layout:layoutPresets.default,recovery_reason:null}});
beforeEach(()=>{
 vi.mocked(getRecoveryStatus).mockResolvedValue({state:"ready",safe_mode:false,backend_available:true,message:"SIMULATED ready",backups:[],external_dev:false});vi.mocked(verifyCanonicalCore).mockResolvedValue(undefined);
 vi.stubGlobal("ResizeObserver",ResizeObserverStub);vi.stubGlobal("crypto",webcrypto);
 window.history.replaceState(null,"","#page=01");
 read={schema:"archeaxis.ui-working-state/v1",workspace_id:"a".repeat(32),restore_epoch:"initial",state_revision:0,state:{drafts:{},opened_documents:[],active_document:null,page_id:"01",pending_original:null},draft_digests:{},pending_document_id:null,recovery_candidates:null,recovery_requires_confirmation:false};
 bridge.call.mockReset();bridge.call.mockImplementation(async(op:string,p:{body?:{state:WorkingState}}={})=>{if(op==="ui_state_read")return structuredClone(read);if(op==="ui_state_write"){read={...read,state_revision:read.state_revision+1,state:structuredClone(p.body!.state)};return structuredClone(read);}return {};});
 const layout=new Promise(resolve=>{resolveLayout=resolve;});window.__TAURI__={core:{invoke:vi.fn().mockReturnValue(layout)}};
});
afterEach(()=>{delete window.__TAURI__;vi.unstubAllGlobals();vi.restoreAllMocks();window.history.replaceState(null,"","#page=01");});
async function start(hydrate=true){const view=render(<App/>);await waitFor(()=>expect(screen.getByLabelText("draft-01")).toBeVisible());if(hydrate){await act(async()=>resolveLayout(layoutReply()));await waitFor(()=>expect(screen.getByLabelText("draft-01")).toBeVisible());}return view;}
async function page(id:string){fireEvent.click(document.querySelector(`.navigation-sidebar button[data-page-id="${id}"]`)??screen.getByRole("button",{name:`SIMULATED goto ${id}`}));await waitFor(()=>expect(document.querySelector(".app-shell")).toHaveAttribute("data-cabin-page",id));}
function tab(name:string){return screen.getByRole("tab",{name});}
function select(name:string){tab(name).focus();fireEvent.keyDown(tab(name),{key:"Enter"});}
function dirty(value:boolean){act(()=>window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner:"dock-regression",dirty:value}})));}

it("actual App/Dock sync native activation and close fallback without reopening the closed tab",async()=>{
 await start();await page("17");select("今日工作台");
 await waitFor(()=>expect(window.location.hash).toBe("#page=01"));expect(screen.getByLabelText("draft-01")).toBeVisible();
 select("全部能力与未来蓝图");await waitFor(()=>expect(window.location.hash).toBe("#page=17"));
 fireEvent.click(screen.getByRole("button",{name:"关闭视图 全部能力与未来蓝图"}));
 await waitFor(()=>expect(document.querySelector(".app-shell")).toHaveAttribute("data-cabin-page","01"));
 expect(screen.queryByRole("tab",{name:"全部能力与未来蓝图"})).not.toBeInTheDocument();expect(window.location.hash).toBe("#page=01");
});
it("same-page navigation reopens the final closed view with the exact retained draft",async()=>{
 await start();const draft=screen.getByLabelText("draft-01");fireEvent.change(draft,{target:{value:"retained final draft"}});
 fireEvent.click(screen.getByRole("button",{name:"关闭视图 今日工作台"}));expect(screen.queryByRole("tab",{name:"今日工作台"})).not.toBeInTheDocument();
 await page("01");await waitFor(()=>expect(draft).toBeVisible());expect(screen.getByLabelText("draft-01")).toBe(draft);expect(draft).toHaveValue("retained final draft");
});
it("refused, composing and restoring native tab changes retain the accepted view and draft",async()=>{
 await start();await page("17");const draft=screen.getByLabelText("draft-17");fireEvent.change(draft,{target:{value:"never discarded"}});
 const confirm=vi.spyOn(window,"confirm").mockReturnValue(false);dirty(true);select("今日工作台");
 await waitFor(()=>expect(draft).toBeVisible());expect(confirm).toHaveBeenCalledTimes(1);expect(window.location.hash).toBe("#page=17");
 fireEvent.click(screen.getByRole("button",{name:"关闭视图 全部能力与未来蓝图"}));await waitFor(()=>expect(draft).toBeVisible());expect(tab("全部能力与未来蓝图")).toHaveAttribute("aria-selected","true");
 dirty(false);fireEvent.compositionStart(window);select("今日工作台");await waitFor(()=>expect(draft).toBeVisible());fireEvent.compositionEnd(window);
 act(()=>window.dispatchEvent(new Event("workspace-restore-start")));select("今日工作台");expect(draft).toBeVisible();act(()=>window.dispatchEvent(new Event("workspace-restore-finish")));
 expect(draft).toHaveValue("never discarded");expect(window.location.hash).toBe("#page=17");
  await screen.findByRole("tab",{name:"今日工作台"});select("今日工作台");await waitFor(()=>expect(window.location.hash).toBe("#page=01"));
});
it("late layout hydration cannot reopen a final view the user has already closed",async()=>{
 await start(false);const draft=screen.getByLabelText("draft-01");fireEvent.change(draft,{target:{value:"closed during read"}});
 fireEvent.click(screen.getByRole("button",{name:"关闭视图 今日工作台"}));
 await act(async()=>resolveLayout(layoutReply()));
 expect(screen.queryByRole("tab",{name:"今日工作台"})).not.toBeInTheDocument();expect(screen.getByText(/已读取已保存的布局；保留当前视图/)).toBeInTheDocument();
 await page("01");await waitFor(()=>expect(draft).toBeVisible());expect(draft).toHaveValue("closed during read");
});
it("late layout hydration keeps the accepted object presentation instead of replacing it with singleton 03",async()=>{
 await start(false);fireEvent.click(screen.getByRole("button",{name:"模拟打开A"}));await screen.findByLabelText("draft-03");
 fireEvent.click(screen.getByText("布局与面板"));fireEvent.click(screen.getByRole("button",{name:"并排打开当前文档"}));
 await waitFor(()=>expect(tab("文档 doc_a")).toHaveAttribute("aria-selected","true"));
 await act(async()=>resolveLayout(layoutReply()));expect(tab("文档 doc_a")).toHaveAttribute("aria-selected","true");expect(screen.getByText(/已读取已保存的布局；保留当前视图/)).toBeInTheDocument();
});
it("native return to an AI family restores the last requested receipt page and retained session",async()=>{
 await start();await page("14");const draft=screen.getByLabelText("draft-14");fireEvent.change(draft,{target:{value:"frozen request"}});dirty(true);
 const confirm=vi.spyOn(window,"confirm").mockReturnValue(false);fireEvent.click(screen.getByRole("button",{name:"模拟查看回执"}));
 await waitFor(()=>expect(window.location.hash).toBe("#page=22"));expect(confirm).not.toHaveBeenCalled();expect(screen.getByLabelText("draft-22")).toBe(draft);
 dirty(false);await page("17");select("任务与记录");
 await waitFor(()=>expect(window.location.hash).toBe("#page=22"));expect(screen.getByLabelText("draft-22")).toBe(draft);expect(draft).toHaveValue("frozen request");
});
it("native object activation preserves full document identity and does not overwrite the singleton reader",async()=>{
 await start();fireEvent.click(screen.getByRole("button",{name:"模拟打开A"}));await screen.findByLabelText("draft-03");
 const main=screen.getByLabelText("draft-03");fireEvent.change(main,{target:{value:"singleton A"}});
 fireEvent.click(screen.getByText("布局与面板"));fireEvent.click(screen.getByRole("button",{name:"并排打开当前文档"}));
 await waitFor(()=>expect(screen.getAllByLabelText("draft-03")).toHaveLength(2));
 const object=screen.getAllByLabelText("draft-03").find(input=>input!==main)!;fireEvent.change(object,{target:{value:"object A"}});
 await page("17");select("文档 doc_a");await waitFor(()=>expect(window.location.hash).toBe("#page=03"));
 expect(object).toBeVisible();expect(object).toHaveValue("object A");expect(tab("文档 doc_a")).toHaveAttribute("aria-selected","true");
 select("阅读与编辑");await waitFor(()=>expect(main).toBeVisible());expect(main).toHaveValue("singleton A");expect(screen.getAllByTestId("dock-document").filter(node=>node.textContent==="doc_a").length).toBeGreaterThanOrEqual(2);
});

it("late automatic layout read cannot undo a user lock",async()=>{
 await start(false);fireEvent.click(screen.getByText("布局与面板"));const lock=screen.getByRole("button",{name:"锁定布局"});fireEvent.click(lock);expect(lock).toHaveAttribute("aria-pressed","true");
 await act(async()=>resolveLayout(layoutReply()));expect(lock).toHaveAttribute("aria-pressed","true");expect(screen.getByRole("button",{name:"左右分栏"})).toBeDisabled();expect(screen.getByText(/已读取已保存的布局；保留当前视图/)).toBeInTheDocument();
});
it("explicit working recovery adopts its scene without overwriting a retained document object host",async()=>{
 await start();const original=bridge.call.getMockImplementation()!;let rejectWrite:((error:Error)=>void)|undefined;let failedBase:WorkingRead|undefined;let recovery:WorkingRead|undefined;
 const candidate:WorkingState={drafts:{},opened_documents:["doc_b"],active_document:"doc_b",page_id:"17",pending_original:null};
 bridge.call.mockImplementation(async(op:string,p:any)=>{
  if(op==="ui_state_write"&&!failedBase){failedBase=structuredClone(read);return new Promise((_resolve,reject)=>{rejectWrite=reject;});}
  if(op==="ui_state_read"&&recovery)return structuredClone(recovery);
  if(op==="ui_state_recover"){read={...recovery!,state_revision:recovery!.state_revision+1,state:structuredClone(candidate),recovery_candidates:null,recovery_requires_confirmation:false};return structuredClone(read);}
  return original(op,p);
 });
 fireEvent.click(screen.getByRole("button",{name:"模拟打开A"}));await screen.findByLabelText("draft-03");const main=screen.getByLabelText("draft-03");
 fireEvent.click(screen.getByText("布局与面板"));fireEvent.click(screen.getByRole("button",{name:"并排打开当前文档"}));await waitFor(()=>expect(tab("文档 doc_a")).toHaveAttribute("aria-selected","true"));
 const object=screen.getAllByLabelText("draft-03").find(input=>input!==main)!;fireEvent.change(object,{target:{value:"object A is not page17"}});
 await waitFor(()=>expect(rejectWrite).toBeTypeOf("function"));await act(async()=>rejectWrite!(new Error("SIMULATED scene write acknowledgement lost")));
 recovery={...structuredClone(failedBase!),recovery_candidates:candidate,recovery_requires_confirmation:true};
 fireEvent.click(await screen.findByRole("button",{name:"核对工作状态"}));await screen.findByRole("button",{name:"保留恢复候选"});await act(async()=>{await Promise.resolve();});fireEvent.click(screen.getByRole("button",{name:"保留恢复候选"}));
 await waitFor(()=>expect(bridge.call.mock.calls.filter(([op])=>op==="ui_state_recover")).toHaveLength(1));
 await waitFor(()=>expect(tab("全部能力与未来蓝图")).toHaveAttribute("aria-selected","true"));expect(window.location.hash).toBe("#page=17");expect(object).toHaveAttribute("aria-label","draft-03");expect(object).toHaveValue("object A is not page17");
});
