import {afterEach,describe,expect,it,vi} from "vitest";
import {desktopLayoutTransport} from "../workspace/layoutPort";
import {layoutPresets} from "../workspace/WorkspaceController";
const snapshot={workspace_id:"a".repeat(32),restore_epoch:"initial",device_id:"device_1",revision:2,layout:layoutPresets.reading,recovery_reason:null};
afterEach(()=>{delete window.__TAURI__;localStorage.removeItem("aaos.layout.device-id");});
describe("BE02 finite native persistence consumer",()=>{
 it("consumes only exact native read write recover routes and binds CAS identities",async()=>{
  localStorage.setItem("aaos.layout.device-id","device_1");const invoke=vi.fn().mockResolvedValue({status:200,body:snapshot});window.__TAURI__={core:{invoke}};const transport=desktopLayoutTransport();
  await transport.read();expect(invoke).toHaveBeenLastCalledWith("core_command",{request:{operation:"layout_read",payload:{device_id:"device_1"}}});
  await transport.write(snapshot,layoutPresets.learning);expect(invoke).toHaveBeenLastCalledWith("core_command",{request:{operation:"layout_write",payload:{body:{workspace_id:snapshot.workspace_id,restore_epoch:"initial",device_id:"device_1",expected_revision:2,layout:layoutPresets.learning}}}});
  await transport.recover(snapshot,1000,700);expect(invoke).toHaveBeenLastCalledWith("core_command",{request:{operation:"layout_recover",payload:{body:{workspace_id:snapshot.workspace_id,restore_epoch:"initial",device_id:"device_1",expected_revision:2,viewport_width:1000,viewport_height:700}}}});
 });
 it("rejects unknown response fields and CAS refusals without fallback or automatic retry",async()=>{
  const invoke=vi.fn().mockResolvedValue({status:200,body:{...snapshot,untrusted_url:"https://invalid"}});window.__TAURI__={core:{invoke}};const transport=desktopLayoutTransport();await expect(transport.read()).rejects.toThrow("LAYOUT_DTO_INVALID");invoke.mockResolvedValue({status:409,body:{}});await expect(transport.write(snapshot,layoutPresets.default)).rejects.toThrow("冲突");expect(invoke).toHaveBeenCalledTimes(2);
 });
});
