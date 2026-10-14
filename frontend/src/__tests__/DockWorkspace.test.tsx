import { afterEach,beforeEach,describe,expect,it,vi } from "vitest";
import { fireEvent,render,screen,waitFor } from "@testing-library/react";
import { useState } from "react";
import { DockWorkspace } from "../workspace/DockWorkspace";
import {useDocumentWriteLease} from "../workspace/documentSessions";
const counters=vi.hoisted(()=>({mounts:0,closes:0}));
vi.mock("../spaces/SpaceView",()=>({SpaceView:({uiPageId,initialDocumentId}:{uiPageId:string;initialDocumentId?:string})=>{const [draft,setDraft]=useState(()=>{counters.mounts++;return "";});const lease=useDocumentWriteLease(initialDocumentId);return <label>文档草稿 {uiPageId}<input aria-label={`draft-${uiPageId}${initialDocumentId?":"+initialDocumentId:""}`} disabled={!lease.canWrite} value={draft} onChange={e=>setDraft(e.target.value)}/></label>;}}));
class ResizeObserverStub{observe(){}unobserve(){}disconnect(){}}
beforeEach(()=>{vi.stubGlobal("ResizeObserver",ResizeObserverStub);counters.mounts=0;});
afterEach(()=>{vi.unstubAllGlobals();});
const props={spaceId:"library" as const,uiPageId:"03",onInspect:vi.fn(),onNavigate:vi.fn(),onOpenPage:vi.fn()};
describe("actual Dockview retained business consumer",()=>{
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
  fireEvent.change(screen.getByLabelText("draft-03"),{target:{value:"unsaved retained"}});
  fireEvent.click(screen.getByRole("button",{name:"左右分栏"}));
  await waitFor(()=>expect(screen.getByLabelText("draft-17")).toBeInTheDocument());
  expect(view.container.querySelectorAll(".dv-groupview").length).toBeGreaterThanOrEqual(2);
  fireEvent.click(screen.getByRole("button",{name:"重置视图布局"}));
  await waitFor(()=>expect(screen.getByLabelText("draft-01")).toBeInTheDocument());
  view.rerender(<DockWorkspace {...props} uiPageId="17" spaceId="settings"/>);
  view.rerender(<DockWorkspace {...props}/>);
  await waitFor(()=>expect(screen.getByLabelText("draft-03")).toHaveValue("unsaved retained"));
  expect(counters.mounts).toBe(3);
 });
 it("locks layout controls while maintaining the same mounted business session",async()=>{
  render(<DockWorkspace {...props}/>);await waitFor(()=>expect(screen.getByLabelText("draft-03")).toBeInTheDocument());
  fireEvent.click(screen.getByRole("button",{name:"锁定布局"}));
  expect(screen.getByRole("button",{name:"左右分栏"})).toBeDisabled();
  expect(screen.getByRole("button",{name:"浮动当前面板"})).toBeDisabled();
  expect(counters.mounts).toBe(1);
 });
 it("opens stable parallel object views, enforces one object writer and closes only its presentation",async()=>{
  const view=render(<DockWorkspace {...props} initialDocumentId="doc-a"/>);await waitFor(()=>expect(screen.getByLabelText("draft-03:doc-a")).toBeEnabled());
  fireEvent.click(screen.getByRole("button",{name:"并排打开当前文档"}));await waitFor(()=>expect(screen.getAllByLabelText("draft-03:doc-a")).toHaveLength(2));expect(screen.getAllByLabelText("draft-03:doc-a").filter(input=>(input as HTMLInputElement).disabled)).toHaveLength(1);
  view.rerender(<DockWorkspace {...props} initialDocumentId="doc-b"/>);await waitFor(()=>expect(screen.getByLabelText("draft-03:doc-a")).toBeEnabled());fireEvent.change(screen.getByLabelText("draft-03:doc-a"),{target:{value:"object draft retained"}});
  fireEvent.click(screen.getByRole("button",{name:"关闭当前视图"}));fireEvent.click(screen.getByRole("button",{name:"重开文档 doc-a"}));await waitFor(()=>expect(screen.getByLabelText("draft-03:doc-a")).toHaveValue("object draft retained"));expect(counters.mounts).toBe(2);
  fireEvent.click(screen.getByRole("button",{name:"并排打开当前文档"}));await waitFor(()=>expect(screen.getAllByLabelText("draft-03:doc-b")).toHaveLength(2));expect(counters.mounts).toBe(3);
  fireEvent.click(screen.getByRole("button",{name:"保存布局"}));expect(await screen.findByText(/对象布局需真实工作区身份/)).toBeInTheDocument();
 });
});
