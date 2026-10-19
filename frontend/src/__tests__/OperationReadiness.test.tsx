import {afterEach,it,expect,vi} from "vitest";
import {act,render,screen} from "@testing-library/react";
import {CanonicalCapabilitiesSpace} from "../spaces/CanonicalCapabilitiesSpace";
import {scopedReadiness} from "../test/fixtures/readiness";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
afterEach(()=>{vi.useRealTimers();bridge.call.mockReset();});
it("SIMULATED selected-view readiness never probes all engines and expires to UNKNOWN",async()=>{vi.useFakeTimers();bridge.call.mockImplementation(async(op:string,p:{body:{scope:string,operations:string[]}})=>{expect(op).toBe("operation_readiness");return scopedReadiness(p.body,Date.now(),1000);});await act(async()=>{render(<CanonicalCapabilitiesSpace onNavigate={vi.fn()} selectedCapabilityId="CAP-0050"/>);});expect(bridge.call).toHaveBeenCalledTimes(1);expect(bridge.call.mock.calls[0][1].body.scope).toBe("view:CAP-0050");expect(screen.getByRole("status")).toHaveTextContent("不加载模型");await act(async()=>{vi.advanceTimersByTime(1001);});expect(screen.getByRole("status")).toHaveTextContent("状态已过期");expect(screen.getByText(/连接\/权限/)).toHaveTextContent("未知");expect(bridge.call).toHaveBeenCalledTimes(1);});
it("SIMULATED wrong scope response is rejected instead of reusing a ready child",async()=>{bridge.call.mockResolvedValue({schema:"archeaxis.operation-readiness/v1",scope:"other-view",expires_at_ms:Date.now()+30000,models_loaded:false,network_performed:false,execution_authorized:false,operations:[{operation:"machine.answer",permission:"ENABLED",connection:"READY"}]});render(<CanonicalCapabilitiesSpace onNavigate={vi.fn()} selectedCapabilityId="CAP-0050"/>);expect(await screen.findByText(/显示未知/)).toBeInTheDocument();expect(screen.getByText(/连接\/权限/)).toHaveTextContent("未知");});

it("SIMULATED PDF static UNKNOWN is observed and keeps the guarded product entrance reachable", async()=>{
  const navigate=vi.fn();
  bridge.call.mockImplementation(async(_op:string,p:{body:{scope:string,operations:string[]}})=>{
    const snapshot=scopedReadiness(p.body);
    snapshot.operations.forEach(row=>{if(row.operation === "pdf.extract") {row.dependencies="UNKNOWN";row.reasons=["PDF_ENGINE_NOT_OBSERVED"];}});
    return snapshot;
  });
  await act(async()=>{render(<CanonicalCapabilitiesSpace onNavigate={navigate} selectedCapabilityId="CAP-0020"/>);});
  expect(screen.getByRole("status")).toHaveTextContent("已读取当前视图");
  expect(screen.getByText(/运行资格：.*PDF_ENGINE_NOT_OBSERVED/)).toBeInTheDocument();
  const entry=screen.getByRole("button",{name:"打开当前产品入口"});
  expect(entry).toBeEnabled();
  await act(async()=>{entry.click();});
  expect(navigate).toHaveBeenCalledTimes(1);
  expect(bridge.call).toHaveBeenCalledTimes(1);
});
