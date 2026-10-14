import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CanonicalCapabilitiesSpace } from "../spaces/CanonicalCapabilitiesSpace";
import { ABSORPTION_SURFACE_BY_CAPABILITY } from "../api/generated/absorption-surface";

const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));

function scopedReadiness(body:{scope:string;operations:readonly string[]}) {
 const expires=Date.now()+30_000;
 return {schema:"archeaxis.operation-readiness/v1",scope:body.scope,observed_at_ms:Date.now(),expires_at_ms:expires,aggregate:"UNVERIFIED",network_performed:false,models_loaded:false,execution_authorized:false,operations:body.operations.map(operation=>({operation,implementation:"IMPLEMENTED",dependencies:"AVAILABLE",connection:"UNKNOWN",qualification:"UNVERIFIED",permission:"ENABLED",status:"UNVERIFIED",reasons:["CONNECTION_NOT_PROBED","RUNTIME_QUALIFICATION_UNVERIFIED"],expires_at_ms:expires}))};
}

describe("existing capability donor projection", () => {
  beforeEach(() => { bridge.call.mockReset();bridge.call.mockImplementation(async(operation:string,payload:{body:{scope:string;operations:readonly string[]}})=>{expect(operation).toBe("operation_readiness");return scopedReadiness(payload.body);}); });
  it("retains the existing11 source rows and shows its actual stable ID join", async () => {
    expect(Object.values(ABSORPTION_SURFACE_BY_CAPABILITY).flat()).toHaveLength(11);
    render(<CanonicalCapabilitiesSpace onNavigate={vi.fn()} selectedCapabilityId="CAP-0020"/>);
    expect(screen.getByText(/以下供体来源由现有稳定能力 ID 投影联接/)).toBeInTheDocument();
    expect(screen.getByText("SYSTRAN/faster-whisper")).toBeInTheDocument();
    expect(screen.queryByText(/供体映射未建立/)).not.toBeInTheDocument();
    await screen.findByText(/已读取当前视图的范围化状态/);
    expect(bridge.call.mock.calls[0][0]).toBe("operation_readiness");expect(bridge.call.mock.calls[0][1].body.scope).toBe("view:CAP-0020");
  });
  it("keeps unbound future capability honest without a guessed donor join", () => {
    render(<CanonicalCapabilitiesSpace onNavigate={vi.fn()} selectedCapabilityId="CAP-0080"/>);
    expect(screen.getByText(/供体映射未建立/)).toBeInTheDocument();
    expect(screen.queryByText(/以下供体来源由现有稳定能力 ID 投影联接/)).not.toBeInTheDocument();
  });
});
