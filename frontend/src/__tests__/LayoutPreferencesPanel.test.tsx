import { beforeEach, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { LayoutPreferencesPanel } from "../components/LayoutPreferencesPanel";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const initial=()=>({workspace_id:"a".repeat(32),device_id:"native_desktop",restore_epoch:"initial",revision:3,layout:{schema_version:1,preset_id:"default",registered_panels:["01"],dock_tree:{kind:"tabs",panels:["01"],active:"01"},floating_bounds:{}},recovery_reason:null});
beforeEach(()=>{bridge.call.mockReset();localStorage.setItem("archeaxis.layout.device.v1","native_desktop");});
it("saves a preset with the read CAS identity and opens persisted panels",async()=>{
 const first=initial();bridge.call.mockImplementation(async(op,p)=>op==="layout_read"?first:{...first,revision:4,layout:p.body.layout});
 render(<LayoutPreferencesPanel/>);fireEvent.click(await screen.findByRole("button",{name:"研究布局"}));
 await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("layout_write",{body:{workspace_id:first.workspace_id,device_id:first.device_id,restore_epoch:first.restore_epoch,expected_revision:3,layout:{schema_version:1,preset_id:"research",registered_panels:["05","04"],dock_tree:{kind:"tabs",panels:["05","04"],active:"05"},floating_bounds:{}}}}));
 expect(await screen.findByRole("link",{name:"研究空间"})).toHaveAttribute("href","#page=05");
 expect(bridge.call.mock.calls.every(([op])=>!op.startsWith("document_"))).toBe(true);
});
it("requires explicit recovery and retains stale CAS on refusal until reread",async()=>{
 const first={...initial(),recovery_reason:"LAYOUT_RESTORE_CONFIRMATION_REQUIRED"};bridge.call.mockImplementation(async(op)=>{if(op==="layout_read")return first;throw new Error("conflict");});
 render(<LayoutPreferencesPanel/>);expect(await screen.findByRole("button",{name:"研究布局"})).toBeDisabled();
 fireEvent.click(screen.getByRole("button",{name:"确认恢复布局"}));
 await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("layout_recover",{body:expect.objectContaining({expected_revision:3,restore_epoch:"initial",workspace_id:first.workspace_id})}));
 expect(screen.getByRole("button",{name:"研究布局"})).toBeDisabled();
});
it("ignores a late prior-workspace read",async()=>{
 let resolve:(v:unknown)=>void=()=>{};const old=new Promise(r=>resolve=r),next={...initial(),workspace_id:"b".repeat(32),revision:8};bridge.call.mockResolvedValueOnce(old).mockResolvedValue(next);
 render(<LayoutPreferencesPanel/>);window.dispatchEvent(new CustomEvent("workspace-invalidated",{detail:{confirmed:true}}));
 await screen.findByText(/修订 8/);resolve(initial());await Promise.resolve();expect(screen.queryByText(/修订 3/)).toBeNull();
});
