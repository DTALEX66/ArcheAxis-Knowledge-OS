import { afterEach,beforeEach,describe,expect,it,vi } from "vitest";
import { act,fireEvent,render,screen,waitFor } from "@testing-library/react";
import { useContext,useState } from "react";
import { createPortal } from "react-dom";
import { StitchResearchOutlet } from "../components/StitchWorkspaceChrome";
import { DockWorkspace } from "../workspace/DockWorkspace";
import {useDocumentWriteLease} from "../workspace/documentSessions";
import {layoutPresets} from "../workspace/WorkspaceController";
const counters=vi.hoisted(()=>({mounts:0,closes:0,working:null as null|{server:{workspace_id:string;restore_epoch:string};state:{active_document:null}}}));
vi.mock("../presentation/useCoreWorkingState",()=>({useOptionalCoreWorkingState:()=>counters.working}));
vi.mock("../spaces/SpaceView",()=>({SpaceView:({uiPageId,initialDocumentId}:{uiPageId:string;initialDocumentId?:string})=>{const [draft,setDraft]=useState(()=>{counters.mounts++;return "";});const outlet=useContext(StitchResearchOutlet);const lease=useDocumentWriteLease(initialDocumentId);return <><label>文档草稿 {uiPageId}<input aria-label={`draft-${uiPageId}${initialDocumentId?":"+initialDocumentId:""}`} disabled={!lease.canWrite} value={draft} onChange={e=>setDraft(e.target.value)}/></label>{uiPageId==="05"&&outlet?.host?createPortal(<span>SIMULATED related 05</span>,outlet.host):null}</>;}}));
const observers=new Set<ResizeObserverStub>();
class ResizeObserverStub{
 targets=new Set<Element>();
 constructor(readonly callback:ResizeObserverCallback){observers.add(this);}
 observe(target:Element){this.targets.add(target);}unobserve(target:Element){this.targets.delete(target);}disconnect(){this.targets.clear();}
}
function resizeSurface(width:number,height:number){for(const observer of observers)for(const target of observer.targets)if(target.classList.contains("dock-surface"))observer.callback([{target,contentRect:{width,height}} as ResizeObserverEntry],observer as unknown as ResizeObserver);}
beforeEach(()=>{observers.clear();vi.stubGlobal("ResizeObserver",ResizeObserverStub);counters.mounts=0;counters.working=null;});
afterEach(()=>{vi.unstubAllGlobals();delete window.__TAURI__;});
const props={spaceId:"library" as const,uiPageId:"03",onInspect:vi.fn(),onNavigate:vi.fn(),onOpenPage:vi.fn()};
describe("actual Dockview retained business consumer",()=>{
 it("removes the closed last research tab's portal and reopens its exact retained draft",async()=>{
  const host=document.createElement("div");document.body.append(host);
  const outlet={host,onLocate:vi.fn()};
  const tree=(revision:number)=><StitchResearchOutlet.Provider value={outlet}><DockWorkspace {...props} uiPageId="05" spaceId="vault" navigationRevision={revision}/></StitchResearchOutlet.Provider>;
  const view=render(tree(0));
  try{
   const draft=await screen.findByLabelText("draft-05");fireEvent.change(draft,{target:{value:"保留研究草稿"}});
   await waitFor(()=>expect(host).toHaveTextContent("SIMULATED related 05"));
   fireEvent.click(screen.getByRole("button",{name:"关闭视图 研究空间"}));
   await waitFor(()=>expect(host).toBeEmptyDOMElement());expect(screen.queryByRole("tab",{name:"研究空间"})).not.toBeInTheDocument();
   expect(draft).toBeInTheDocument();expect(draft).not.toBeVisible();
   view.rerender(tree(1));await waitFor(()=>expect(host).toHaveTextContent("SIMULATED related 05"));
   expect(screen.getByLabelText("draft-05")).toBe(draft);expect(draft).toBeVisible();expect(draft).toHaveValue("保留研究草稿");expect(counters.mounts).toBe(1);
  }finally{view.unmount();host.remove();}
 });
 it("SIMULATED rejected saved layout keeps the mounted draft visible",async()=>{
  counters.working={server:{workspace_id:"a".repeat(32),restore_epoch:"initial"},state:{active_document:null}};
  let resolve!:(value:unknown)=>void;const reply=new Promise(done=>{resolve=done;});window.__TAURI__={core:{invoke:vi.fn().mockReturnValue(reply)}};
  render(<DockWorkspace {...props}/>);const draft=await screen.findByLabelText("draft-03");fireEvent.change(draft,{target:{value:"rejected layout preserves reader"}});
  resolve({status:200,body:{workspace_id:"a".repeat(32),restore_epoch:"initial",device_id:"device_1",revision:0,recovery_reason:null,layout:{...layoutPresets.default,registered_panels:["02","03"],dock_tree:{kind:"tabs",panels:["02","03"],active:"03"}}}});
  await screen.findByText(/旧布局存在重复业务宿主/);expect(screen.getByLabelText("draft-03")).toBe(draft);expect(draft).toBeVisible();expect(draft).toHaveValue("rejected layout preserves reader");expect(counters.mounts).toBe(1);
 });
 it("splits an already open tab and changes the split axis without creating another business session",async()=>{
  const view=render(<DockWorkspace {...props}/>);const draft=await screen.findByLabelText("draft-03");fireEvent.change(draft,{target:{value:"split retained draft"}});
  view.rerender(<DockWorkspace {...props} uiPageId="17" spaceId="settings"/>);await screen.findByLabelText("draft-17");
  view.rerender(<DockWorkspace {...props}/>);await waitFor(()=>expect(draft).toBeVisible());
  expect(view.container.querySelectorAll(".dv-groupview")).toHaveLength(1);
  fireEvent.click(screen.getByText("布局与面板"));fireEvent.click(screen.getByRole("button",{name:"左右分栏"}));
  await waitFor(()=>expect(view.container.querySelectorAll(".dv-groupview")).toHaveLength(2));
  expect(draft).toBeVisible();expect(screen.getByLabelText("draft-17")).toBeVisible();
  fireEvent.click(screen.getByRole("button",{name:"上下分栏"}));
  expect(view.container.querySelectorAll(".dv-groupview")).toHaveLength(2);
  expect(screen.getByLabelText("draft-03")).toBe(draft);expect(draft).toHaveValue("split retained draft");expect(counters.mounts).toBe(2);
 });
 it("uses the actual dock surface to fold a split into tabs, then restores it without losing drafts",async()=>{
  const view=render(<DockWorkspace {...props}/>);const draft=await screen.findByLabelText("draft-03");fireEvent.change(draft,{target:{value:"narrow retained draft"}});
  fireEvent.click(screen.getByText("布局与面板"));fireEvent.click(screen.getByRole("button",{name:"左右分栏"}));await screen.findByLabelText("draft-17");
  expect(view.container.querySelectorAll(".dv-groupview")).toHaveLength(2);
  act(()=>resizeSurface(550,210));
  await waitFor(()=>expect(view.container.querySelectorAll(".dv-groupview")).toHaveLength(1));
  expect(screen.getByText(/空间不足，已改为标签/)).toBeVisible();
  expect(draft).toHaveValue("narrow retained draft");
  fireEvent.keyDown(screen.getByRole("tab",{name:"阅读与编辑"}),{key:"Enter"});expect(screen.getByLabelText("draft-03")).toBe(draft);expect(draft).toBeVisible();
  act(()=>resizeSurface(1200,700));
  await waitFor(()=>expect(view.container.querySelectorAll(".dv-groupview")).toHaveLength(2));
  expect(draft).toBeVisible();expect(draft).toHaveValue("narrow retained draft");expect(counters.mounts).toBe(2);
 });
 it("does not resurrect a tab deliberately closed while the split is compacted",async()=>{
  const view=render(<DockWorkspace {...props}/>);await screen.findByLabelText("draft-03");
  fireEvent.click(screen.getByText("布局与面板"));fireEvent.click(screen.getByRole("button",{name:"左右分栏"}));
  const other=await screen.findByLabelText("draft-17");fireEvent.change(other,{target:{value:"closed narrow draft"}});
  act(()=>resizeSurface(550,210));await waitFor(()=>expect(view.container.querySelectorAll(".dv-groupview")).toHaveLength(1));
  fireEvent.keyDown(screen.getByRole("tab",{name:"全部能力与未来蓝图"}),{key:"Enter"});fireEvent.click(screen.getByRole("button",{name:"关闭视图 全部能力与未来蓝图"}));
  act(()=>resizeSurface(1200,700));expect(screen.queryByRole("tab",{name:"全部能力与未来蓝图"})).not.toBeInTheDocument();expect(view.container.querySelectorAll(".dv-groupview")).toHaveLength(1);
  view.rerender(<DockWorkspace {...props} uiPageId="17" spaceId="settings"/>);await waitFor(()=>expect(screen.getByLabelText("draft-17")).toBeVisible());
  expect(screen.getByLabelText("draft-17")).toBe(other);expect(other).toHaveValue("closed narrow draft");expect(counters.mounts).toBe(2);
 });
 it("SIMULATED layout save preserves the expanded preference while the narrow display uses tabs",async()=>{
  counters.working={server:{workspace_id:"a".repeat(32),restore_epoch:"initial"},state:{active_document:null}};
  const identity={workspace_id:"a".repeat(32),restore_epoch:"initial",device_id:"device_1",recovery_reason:null};
  let revision=0;const invoke=vi.fn().mockImplementation((_command,{request})=>Promise.resolve({status:200,body:request.operation==="layout_write"?{...identity,device_id:request.payload.body.device_id,revision:++revision,layout:request.payload.body.layout}:{...identity,revision:0,layout:layoutPresets.reading}}));window.__TAURI__={core:{invoke}};
  const view=render(<DockWorkspace {...props}/>);await screen.findByRole("tab",{name:"全部能力与未来蓝图"});
  fireEvent.click(screen.getByText("布局与面板"));fireEvent.click(screen.getByRole("button",{name:"保存布局"}));
  await waitFor(()=>expect(revision).toBe(1));const expanded=invoke.mock.calls.find(call=>call[1].request.operation==="layout_write")![1].request.payload.body.layout;
  act(()=>resizeSurface(550,210));await waitFor(()=>expect(view.container.querySelectorAll(".dv-groupview")).toHaveLength(1));
  fireEvent.click(screen.getByRole("button",{name:"保存布局"}));await waitFor(()=>expect(revision).toBe(2));
  const writes=invoke.mock.calls.filter(call=>call[1].request.operation==="layout_write");
  expect(writes[1][1].request.payload.body.layout).toEqual(expanded);expect(expanded.dock_tree.kind).toBe("split");expect(expanded.registered_panels).toEqual(["03","17"]);
  act(()=>resizeSurface(1200,700));await waitFor(()=>expect(view.container.querySelectorAll(".dv-groupview")).toHaveLength(2));
 });
 it.each([
  {spaceId:"ai-assets" as const,pages:[["13","项目记忆与上下文"],["14","纠正、评测与复测"],["22","任务与记录"]]},
  {spaceId:"library" as const,pages:[["02","知识库"],["03","阅读与编辑"],["20","版本、来源与历史"]]},
  {spaceId:"learning" as const,pages:[["06","学习路径"],["07","课程与视觉教学"]]},
 ])("labels accepted semantic pages in a single retained $spaceId business host",async({spaceId,pages})=>{
  const activate=vi.fn(()=>true);
  const view=render(<DockWorkspace {...props} spaceId={spaceId} uiPageId={pages[0][0]} onActivateView={activate}/>);
  const draft=await screen.findByLabelText(`draft-${pages[0][0]}`);fireEvent.change(draft,{target:{value:"same retained semantic draft"}});
  for(const [page,title] of pages){
   view.rerender(<DockWorkspace {...props} spaceId={spaceId} uiPageId={page} onActivateView={activate}/>);
   await waitFor(()=>expect(screen.getByRole("tab",{name:title})).toHaveAttribute("aria-selected","true"));
   expect(screen.getByRole("button",{name:`关闭视图 ${title}`})).toBeInTheDocument();
   expect(screen.getByLabelText(`draft-${page}`)).toBe(draft);expect(draft).toHaveValue("same retained semantic draft");
  }
  expect(counters.mounts).toBe(1);expect(view.container.querySelector(".dock-workspace")).toHaveAttribute("data-panel-count","1");expect(activate).not.toHaveBeenCalled();
 });
 it.each([["14","ai-assets","纠正、评测与复测"],["20","library","版本、来源与历史"]] as const)("keeps initial %s titles through close, reopen and explicit layout restoration",async(page,spaceId,title)=>{
  const view=render(<DockWorkspace {...props} uiPageId={page} spaceId={spaceId}/>);
  const draft=await screen.findByLabelText(`draft-${page}`);fireEvent.change(draft,{target:{value:"semantic reopen draft"}});
  expect(screen.getByRole("tab",{name:title})).toHaveAttribute("aria-selected","true");
  fireEvent.click(screen.getByRole("button",{name:`关闭视图 ${title}`}));
  expect(screen.queryByRole("tab",{name:title})).not.toBeInTheDocument();
  view.rerender(<DockWorkspace {...props} uiPageId={page} spaceId={spaceId} navigationRevision={1}/>);
  await waitFor(()=>expect(screen.getByRole("tab",{name:title})).toHaveAttribute("aria-selected","true"));expect(draft).toHaveValue("semantic reopen draft");
  fireEvent.click(screen.getByText("布局与面板"));fireEvent.click(screen.getByRole("button",{name:"重置视图布局"}));
  view.rerender(<DockWorkspace {...props} uiPageId={page} spaceId={spaceId} navigationRevision={2}/>);
  await waitFor(()=>expect(screen.getByRole("tab",{name:title})).toHaveAttribute("aria-selected","true"));expect(screen.getByLabelText(`draft-${page}`)).toBe(draft);expect(draft).toHaveValue("semantic reopen draft");
 });
 it("keeps the accepted semantic title and draft when a native activation is refused",async()=>{
  const activate=vi.fn(()=>false);const view=render(<DockWorkspace {...props} spaceId="ai-assets" uiPageId="14" onActivateView={activate}/>);
  const draft=await screen.findByLabelText("draft-14");fireEvent.change(draft,{target:{value:"refusal retains accepted semantic page"}});
  view.rerender(<DockWorkspace {...props} spaceId="settings" uiPageId="17" onActivateView={activate}/>);await screen.findByRole("tab",{name:"全部能力与未来蓝图"});
  activate.mockClear();const target=screen.getByRole("tab",{name:"纠正、评测与复测"});target.focus();fireEvent.keyDown(target,{key:"Enter"});
  await waitFor(()=>expect(screen.getByRole("tab",{name:"全部能力与未来蓝图"})).toHaveAttribute("aria-selected","true"));
  expect(activate).toHaveBeenCalledTimes(1);expect(activate).toHaveBeenCalledWith(expect.objectContaining({panelId:"13",uiPageId:"14"}));
  expect(screen.getByRole("tab",{name:"纠正、评测与复测"})).toBeInTheDocument();expect(draft).toHaveValue("refusal retains accepted semantic page");
 });
 it("keeps object document titles distinct while the singleton changes semantic page and layout is restored",async()=>{
  const view=render(<DockWorkspace {...props} initialDocumentId="doc-a"/>);await screen.findByLabelText("draft-03:doc-a");
  fireEvent.click(screen.getByText("布局与面板"));fireEvent.click(screen.getByRole("button",{name:"并排打开当前文档"}));
  await screen.findByRole("tab",{name:"文档 doc-a"});
  view.rerender(<DockWorkspace {...props} uiPageId="20" initialDocumentId="doc-b"/>);
  await screen.findByRole("tab",{name:"版本、来源与历史"});expect(screen.getByRole("tab",{name:"文档 doc-a"})).toBeInTheDocument();expect(screen.getByLabelText("draft-03:doc-a")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button",{name:"重置视图布局"}));
  fireEvent.click(screen.getByRole("button",{name:"重开文档 doc-a"}));
  await waitFor(()=>expect(screen.getByRole("tab",{name:"文档 doc-a"})).toHaveAttribute("aria-selected","true"));expect(screen.queryByRole("tab",{name:"document.doc-a"})).not.toBeInTheDocument();
 });

 it("opens ordinary navigation in the current tab group instead of creating an unsolicited split",async()=>{
  const view=render(<DockWorkspace {...props}/>);
  const draft=await screen.findByLabelText("draft-03");
  fireEvent.change(draft,{target:{value:"navigation draft"}});
  view.rerender(<DockWorkspace {...props} uiPageId="17" spaceId="settings"/>);
  await screen.findByLabelText("draft-17");
  expect(view.container.querySelectorAll(".dv-groupview")).toHaveLength(1);
  view.rerender(<DockWorkspace {...props}/>);
  await waitFor(()=>expect(draft).toBeVisible());expect(draft).toHaveValue("navigation draft");
 });
 it("keeps tabs free of nested controls and closes the owning group without losing drafts",async()=>{
  const view=render(<DockWorkspace {...props}/>);
  const draft=await screen.findByLabelText("draft-03");
  fireEvent.change(draft,{target:{value:"audit retained draft"}});
  fireEvent.click(screen.getByText("布局与面板"));
  fireEvent.click(screen.getByRole("button",{name:"左右分栏"}));
  await screen.findByLabelText("draft-17");
  for(const tab of view.container.querySelectorAll('[role="tab"]')) expect(tab.querySelector('button,[role="button"],input,a[href]')).toBeNull();
  // 此时全局活动面板在右侧；关闭左组必须使用左组自己的 activePanel。
  fireEvent.click(screen.getByRole("button",{name:"关闭视图 阅读与编辑"}));
  expect(screen.queryByRole("tab",{name:"阅读与编辑"})).not.toBeInTheDocument();
  expect(screen.getByRole("tab",{name:"全部能力与未来蓝图"})).toBeInTheDocument();
  expect(screen.getByLabelText("draft-17")).toBeVisible();
  view.rerender(<DockWorkspace {...props} uiPageId="17"/>);
  view.rerender(<DockWorkspace {...props}/>);
  await waitFor(()=>expect(screen.getByLabelText("draft-03")).toBeVisible());
  expect(screen.getByLabelText("draft-03")).toBe(draft);
  expect(draft).toHaveValue("audit retained draft");
  expect(counters.mounts).toBe(2);
 });
 it("returns focus to layout controls when the final group close removes its button",async()=>{
  render(<DockWorkspace {...props}/>);
  const close=await screen.findByRole("button",{name:"关闭视图 阅读与编辑"});
  close.focus();fireEvent.click(close);
  await waitFor(()=>expect(screen.getByText("布局与面板")).toHaveFocus());
  expect(screen.queryByRole("tab",{name:"阅读与编辑"})).not.toBeInTheDocument();
 });
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
  await screen.findByRole("tab",{name:"今日工作台"});
  expect(screen.getByRole("tab",{name:"纠正、评测与复测"})).toHaveAttribute("aria-selected","true");
  expect(screen.getByLabelText("draft-14")).toBeVisible();
  expect(document.querySelectorAll(".dv-groupview")).toHaveLength(1);
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
  await screen.findByRole("tab",{name:"今日工作台"});
  expect(screen.getByRole("tab",{name:"纠正、评测与复测"})).toHaveAttribute("aria-selected","true");
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
  await screen.findByRole("tab",{name:"今日工作台"});
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
