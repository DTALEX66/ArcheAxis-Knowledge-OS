import {beforeEach,expect,it,vi} from "vitest";
import {resolveProductModel} from "../runtime/modelBinding";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const configuration={revision:3,workspace_id:"a".repeat(32),restore_epoch:"initial"};
const resolved={...configuration,configuration_revision:3,purpose:"material",lane:"deep",profile:{model:"aaos-deep-27b-mtp"}};
beforeEach(()=>bridge.call.mockReset());
it("allows the legacy FAST path without resolving but refuses an unconfigured DEEP request",async()=>{
 bridge.call.mockResolvedValue({revision:0});
 expect(await resolveProductModel("material","fast")).toBeNull();
 await expect(resolveProductModel("material","deep")).rejects.toThrow(/DEEP 尚未配置/);
 expect(bridge.call.mock.calls.every(([op])=>op==="model_configuration_get")).toBe(true);
});
it.each([{lane:"fast"},{purpose:"embedding"},{configuration_revision:4},{workspace_id:"b".repeat(32)},{restore_epoch:"changed"}])("refuses changed destination identity %j",async changed=>{
 bridge.call.mockImplementation(async(op:string)=>op==="model_configuration_get"?configuration:{...resolved,...changed});
 await expect(resolveProductModel("material","deep")).rejects.toThrow("MODEL_CONFIGURATION_IDENTITY_CHANGED");
});
