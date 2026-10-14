import { describe,expect,it,vi } from "vitest";
import { WorkspaceController,layoutPresets } from "../workspace/WorkspaceController";
import { businessPanelId,PanelRegistry } from "../workspace/PanelRegistry";
import type { LayoutSnapshot } from "../api/generated/layout-contract";
const snapshot=(revision=0):LayoutSnapshot=>({workspace_id:"a".repeat(32),restore_epoch:"initial",device_id:"device_1",revision,layout:layoutPresets.reading,recovery_reason:null});
describe("CAS layout controller and independent business ownership",()=>{
 it("retains pending layout on conflict and never clears drafts or submits model calls",async()=>{
  const transport={read:vi.fn().mockResolvedValue(snapshot()),write:vi.fn().mockRejectedValue(new Error("409 conflict")),recover:vi.fn()};
  const controller=new WorkspaceController(transport);await controller.read();controller.stage(layoutPresets.learning);
  await expect(controller.save()).rejects.toThrow("409");expect(controller.pending).toEqual(layoutPresets.learning);expect(controller.snapshot?.revision).toBe(0);
  expect(transport.write).toHaveBeenCalledWith(snapshot(),layoutPresets.learning);expect(transport.recover).not.toHaveBeenCalled();
 });
 it("uses exact revision, supports restart readback, and rejects workspace/epoch receipt drift",async()=>{
  const transport={read:vi.fn().mockResolvedValue(snapshot()),write:vi.fn().mockResolvedValue({...snapshot(1),layout:layoutPresets.learning}),recover:vi.fn()};
  const controller=new WorkspaceController(transport);await controller.read();controller.stage(layoutPresets.learning);await controller.save();expect(controller.pending).toBeNull();expect(controller.snapshot?.revision).toBe(1);
  transport.read.mockResolvedValue(controller.snapshot!);const restarted=new WorkspaceController(transport);expect((await restarted.read()).layout).toEqual(layoutPresets.learning);
  transport.write.mockResolvedValue({...snapshot(2),restore_epoch:"b".repeat(32)});controller.stage(layoutPresets.default);await expect(controller.save()).rejects.toThrow("身份");expect(controller.pending).toEqual(layoutPresets.default);
 });
 it("holds one canonical reader/model/catalog host and uses stable workspace/object/session identities",()=>{
  expect(businessPanelId("02")).toBe("03");expect(businessPanelId("20")).toBe("03");expect(businessPanelId("14")).toBe("13");expect(businessPanelId("18")).toBe("17");
  const registry=new PanelRegistry("a".repeat(32),"initial");expect(registry.host("02")).toBe(registry.host("03"));expect(registry.host("14")).toBe(registry.host("13"));expect(registry.key("03","doc_1")).not.toBe(registry.key("03","doc_2"));
 });
 it("does not accept a late layout save after workspace invalidation",async()=>{
  let resolve!:(value:LayoutSnapshot)=>void;const transport={read:vi.fn().mockResolvedValue(snapshot()),write:vi.fn(()=>new Promise<LayoutSnapshot>(done=>{resolve=done;})),recover:vi.fn()};
  const controller=new WorkspaceController(transport);await controller.read();controller.stage(layoutPresets.default);const save=controller.save();controller.invalidate();resolve(snapshot(1));await expect(save).rejects.toThrow("身份");expect(controller.snapshot).toBeNull();expect(controller.pending).toEqual(layoutPresets.default);
 });
 it("rejects a read from another workspace before accepting a writable CAS basis",async()=>{
  const transport={read:vi.fn().mockResolvedValue(snapshot()),write:vi.fn(),recover:vi.fn()};const controller=new WorkspaceController(transport,()=>{},{workspace_id:"b".repeat(32),restore_epoch:"initial"});await expect(controller.read()).rejects.toThrow("身份");expect(controller.snapshot).toBeNull();controller.stage(layoutPresets.default);await expect(controller.save()).rejects.toThrow("读回");expect(transport.write).not.toHaveBeenCalled();
 });
});
