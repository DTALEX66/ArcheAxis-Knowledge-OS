import { beforeEach, describe, expect, it, vi } from "vitest";
import { coreCommand } from "../api/core";
import { uiHostRead } from "../api/uiHost";
import { UI_HOST_CONTRACT_DIGEST, assertUiHostRequest, assertUiHostResponse, type UiHostRequest } from "../api/generated/ui-host-contract";
vi.mock("../api/core",()=>({coreCommand:vi.fn()}));
const request=():UiHostRequest=>({schema:"archeaxis.ui-host-request/v2",contract_digest:UI_HOST_CONTRACT_DIGEST,request_id:"trace_1",workspace_id:"a".repeat(32),restore_epoch:"initial",operation:"capability.catalog.read",input:{}});
const result=(r:UiHostRequest)=>({schema:"archeaxis.ui-host-response/v2",contract_digest:UI_HOST_CONTRACT_DIGEST,request_id:r.request_id,workspace_id:r.workspace_id,restore_epoch:r.restore_epoch,operation:r.operation,outcome:"READ_OK",reason_code:null,core_status:200,checked_at:1,build_identity:{host_version:"test",source_revision:null},result_ref:{schema:"archeaxis.capabilities/v1",capabilities:[]}});
describe("finite host v2 consumer",()=>{
 beforeEach(()=>{vi.mocked(coreCommand).mockReset();vi.mocked(coreCommand).mockResolvedValue({workspace_id:"a".repeat(32),restore_epoch:"initial"});});
 it("rejects unknown operations, arbitrary inputs, extra grants and stale digests",()=>{
  for(const patch of [{operation:"shell.exec"},{input:{credential:"synthetic"}},{scope_ref:"grant"},{contract_digest:"b".repeat(64)}])expect(()=>assertUiHostRequest({...request(),...patch})).toThrow();
 });
 it("binds replies to request workspace epoch operation version and outcome",()=>{
  for(const patch of [{request_id:"other"},{workspace_id:"b".repeat(32)},{restore_epoch:"b".repeat(32)},{operation:"model.inventory.read"},{contract_digest:"b".repeat(64)},{reason_code:"HOST_CONTRACT_MISSING"},{outcome:"UNAVAILABLE"}])expect(()=>assertUiHostResponse({...result(request()),...patch},request())).toThrow();
 });
 it("uses the native mapped catalog and never sends URLs tokens or scope claims",async()=>{
  const invoke=vi.fn().mockImplementation(async(_command,args)=>result(args.request));
  window.__TAURI__={core:{invoke}};
  await expect(uiHostRead("capability.catalog.read")).resolves.toEqual({schema:"archeaxis.capabilities/v1",capabilities:[]});
  expect(coreCommand).toHaveBeenCalledWith("ui_state_read");
  expect(invoke).toHaveBeenCalledTimes(1);expect(invoke.mock.calls[0][0]).toBe("ui_host_command");
  assertUiHostRequest(invoke.mock.calls[0][1].request);
 });
 it("reports unavailable and transport loss without retrying or generic fallback",async()=>{
  const invoke=vi.fn().mockImplementation(async(_command,args)=>({...result(args.request),outcome:"UNAVAILABLE",reason_code:"HOST_CONTRACT_MISSING",core_status:null,result_ref:null}));
  window.__TAURI__={core:{invoke}};
  await expect(uiHostRead("companion.send")).rejects.toThrow("HOST_CONTRACT_MISSING");expect(invoke).toHaveBeenCalledTimes(1);
  invoke.mockRejectedValue(new Error("lost reply"));await expect(uiHostRead("model.inventory.read")).rejects.toThrow("lost reply");expect(invoke).toHaveBeenCalledTimes(2);
 });
});
