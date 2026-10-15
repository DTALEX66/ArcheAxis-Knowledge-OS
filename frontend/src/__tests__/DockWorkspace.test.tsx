import { afterEach,beforeEach,describe,expect,it,vi } from "vitest";
import { fireEvent,render,screen,waitFor } from "@testing-library/react";
import { useState } from "react";
import { DockWorkspace } from "../workspace/DockWorkspace";
import {useDocumentWriteLease} from "../workspace/documentSessions";
import {layoutPresets} from "../workspace/WorkspaceController";
const counters=vi.hoisted(()=>({mounts:0,closes:0,working:null as null|{server:{workspace_id:string;restore_epoch:string};state:{active_document:null}}}));
vi.mock("../presentation/useCoreWorkingState",()=>({useOptionalCoreWorkingState:()=>counters.working}));
vi.mock("../spaces/SpaceView",()=>({SpaceView:({uiPageId,initialDocumentId}:{uiPageId:string;initialDocumentId?:string})=>{const [draft,setDraft]=useState(()=>{counters.mounts++;return "";});const lease=useDocumentWriteLease(initialDocumentId);return <label>文档草稿 {uiPageId}<input aria-label={`draft-${uiPageId}${initialDocumentId?":"+initialDocumentId:""}`} disabled={!lease.canWrite} value={draft} onChange={e=>setDraft(e.target.value)}/></label>;}}));
class ResizeObserverStub{observe(){}unobserve(){}disconnect(){}}
beforeEach(()=>{vi.stubGlobal("ResizeObserver",ResizeObserverStub);counters.mounts=0;counters.working=null;});
afterEach(()=>{vi.unstubAllGlobals();delete window.__TAURI__;});
const props={spaceId:"library" as const,uiPageId:"03",onInspect:vi.fn(),onNavigate:vi.fn(),onOpenPage:vi.fn()};
describe("actual Dockview retained business consumer",()=>{
 it("shows required layout recovery without opening layout controls",async()=>{
  counters.working={server:{workspace_id:"a".repeat(32),restore_epoch:"initial"},state:{active_document:null}};
  window.__TAURI__={core:{invoke:vi.fn().mockResolvedValue({status:200,body:{workspace_id:"a".repeat(32),restore_epoch:"initial",device_id:"device_1",revision:0,layout:layoutPresets.default,recovery_reason:"LAYOUT_RESTORE_CONFIRMATION_REQUIRED"}})}};
  const view=render(<DockWorkspace {...props}/>);
  const alert=await screen.findByText(/布局需要确认恢复.*请展开/);
  expect(alert).toHaveAttribute("role","alert");
  expect(alert).toBeVisible();
  expect(view.container.querySelector(".dock-layout-options")).not.toHaveAttribute("open");
 });
 it("SIMULATED native cold layout read keeps the requested business page visible instead of restoring another active tab",async()=>{
  counters.working={server:{workspace_id:"a".repeat(32),restore_epoch:"initial"},state:{active_document:null}};
  const invoke=vi.fn().mockResolvedValue({status:200,body:{workspace_id:"a".repeat(32),restore_epoch:"initial",device_id:"device_1",revision:0,layout:layoutPresets.default,recovery_reason:null}});window.__TAURI__={core:{invoke}};
  render(<DockWorkspace {...props} spaceId="settings" uiPageId="14"/>);
  await waitFor(()=>expect(screen.getByLabelText("draft-14")).toBeVisible());
  await waitFor(()=>expect(screen.getByLabelText("draft-01")).toBeInTheDocument());
  expect(screen.getByLabelText("draft-14")).toBeVisible();
  expect(invoke.mock.calls.map(call=>call[1].request.operation)).toEqual(["layout_read"]);
 });
 it("SIMULATED late layout hydration opens the latest navigation and retains existing business drafts",async()=>{
  counters.working={server:{workspace_id:"a".repeat(32),restore_epoch:"initial"},state:{active_document:null}};
  let resolve!:(value:unknown)=>void;const reply=new Promise(done=>{resolve=done;});const invoke=vi.fn().mockReturnValue(reply);window.__TAURI__={core:{invoke}};
  const view=render(<DockWorkspace {...props}/>);await waitFor(()=>expect(invoke).toHaveBeenCalledTimes(1));
  fireEvent.change(screen.getByLabelText("draft-03"),{target:{value:"retained during hydration"}});
  view.rerender(<DockWorkspace {...props} spaceId="settings" uiPageId="14"/>);
  await waitFor(()=>expect(screen.getByLabelText("draft-14")).toBeVisible());
  resolve({status:200,body:{workspace_id:"a".repeat(32),restore_epoch:"initial",device_id:"device_1",revision:0,layout:layoutPresets.default,recovery_reason:null}});
  await waitFor(()=>expect(screen.getByLabelText("draft-01")).toBeInTheDocument());
  expect(screen.getByLabelText("draft-14")).toBeVisible();expect(screen.getByLabelText("draft-03")).toHaveValue("retained during hydration");
  expect(invoke.mock.calls.map(call=>call[1].request.operation)).toEqual(["layout_read"]);
 });
 it("routes AI context, answer and receipts through one retained host with the requested page props",async()=>{
  const view=render(<DockWorkspace {...props} spaceId="settings" uiPageId="13"/>);
  const context=await screen.findByLabelText("draft-13");fireEvent.change(context,{target:{value:"same business session"}});
  view.rerender(<DockWorkspace {...props} spaceId="settings" uiPageId="14"/>);
  await waitFor(()=>expect(screen.getByLabelText("draft-14")).toHaveValue("same business session"));
  view.rerender(<DockWorkspace {...props} spaceId="settings" uiPageId="22"/>);
  await waitFor(()=>expect(screen.getByLabelText("draft-22")).toHaveValue("same business session"));
  expect(counters.mounts).toBe(1);
 });
 it("uses real Dockview groups and closing/reopening only detaches the persistent business view",async()=>{
  const view=render(<DockWorkspace {...props}/>);
  await waitFor(()=>expect(screen.getByLabelText("draft-03")).toBeInTheDocument());
  expect(view.container.querySelector(".dock-workspace")).toHaveAttribute("data-compact-reader","true");
  fireEvent.change(screen.getByLabelText("draft-03"),{target:{value:"unsaved retained"}});
  fireEvent.click(screen.getByText("布局与面板"));
  fireEvent.click(screen.getByRole("button",{name:"左右分栏"}));
  await waitFor(()=>expect(screen.getByLabelText("draft-17")).toBeInTheDocument());
  expect(view.container.querySelectorAll(".dv-groupview").length).toBeGreaterThanOrEqual(2);
  expect(view.container.querySelector(".dock-workspace")).not.toHaveAttribute("data-compact-reader");
  fireEvent.click(screen.getByRole("button",{name:"重置视图布局"}));
  await waitFor(()=>expect(screen.getByLabelText("draft-01")).toBeInTheDocument());
  view.rerender(<DockWorkspace {...props} uiPageId="17" spaceId="settings"/>);
  view.rerender(<DockWorkspace {...props}/>);
  await waitFor(()=>expect(screen.getByLabelText("draft-03")).toHaveValue("unsaved retained"));
  expect(counters.mounts).toBe(3);
 });
 it("keeps the floating group header available without remounting the reader",async()=>{
  const view=render(<DockWorkspace {...props}/>);
  const editor=await screen.findByLabelText("draft-03");
  fireEvent.change(editor,{target:{value:"floating draft"}});
  fireEvent.click(screen.getByText("布局与面板"));
  fireEvent.click(screen.getByRole("button",{name:"浮动当前面板"}));
  await waitFor(()=>expect(view.container.querySelector(".dock-workspace")).not.toHaveAttribute("data-compact-reader"));
  expect(screen.getByLabelText("draft-03")).toBe(editor);
  expect(editor).toHaveValue("floating draft");
  expect(counters.mounts).toBe(1);
 });
 it("locks layout controls while maintaining the same mounted business session",async()=>{
  render(<DockWorkspace {...props}/>);await waitFor(()=>expect(screen.getByLabelText("draft-03")).toBeInTheDocument());
  fireEvent.click(screen.getByText("布局与面板"));
  fireEvent.click(screen.getByRole("button",{name:"锁定布局"}));
  expect(screen.getByRole("button",{name:"左右分栏"})).toBeDisabled();
  expect(screen.getByRole("button",{name:"浮动当前面板"})).toBeDisabled();
  expect(counters.mounts).toBe(1);
 });
 it("opens stable parallel object views, enforces one object writer and closes only its presentation",async()=>{
  const view=render(<DockWorkspace {...props} initialDocumentId="doc-a"/>);await waitFor(()=>expect(screen.getByLabelText("draft-03:doc-a")).toBeEnabled());
  fireEvent.click(screen.getByText("布局与面板"));
  fireEvent.click(screen.getByRole("button",{name:"并排打开当前文档"}));await waitFor(()=>expect(screen.getAllByLabelText("draft-03:doc-a")).toHaveLength(2));expect(screen.getAllByLabelText("draft-03:doc-a").filter(input=>(input as HTMLInputElement).disabled)).toHaveLength(1);
  view.rerender(<DockWorkspace {...props} initialDocumentId="doc-b"/>);await waitFor(()=>expect(screen.getByLabelText("draft-03:doc-a")).toBeEnabled());fireEvent.change(screen.getByLabelText("draft-03:doc-a"),{target:{value:"object draft retained"}});
  fireEvent.click(screen.getByRole("button",{name:"关闭当前视图"}));fireEvent.click(screen.getByRole("button",{name:"重开文档 doc-a"}));await waitFor(()=>expect(screen.getByLabelText("draft-03:doc-a")).toHaveValue("object draft retained"));expect(counters.mounts).toBe(2);
  fireEvent.click(screen.getByRole("button",{name:"并排打开当前文档"}));await waitFor(()=>expect(screen.getAllByLabelText("draft-03:doc-b")).toHaveLength(2));expect(counters.mounts).toBe(3);
  fireEvent.click(screen.getByRole("button",{name:"保存布局"}));expect(await screen.findByText(/对象布局需真实工作区身份/)).toBeInTheDocument();
 });
});
