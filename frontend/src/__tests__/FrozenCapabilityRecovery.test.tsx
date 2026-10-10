import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { FrozenCapabilityRecovery } from "../components/FrozenCapabilityRecovery";
import type { JobAdmissionRefusal } from "../api/client";
const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const attempt={job_id:"job",request_id:"frozen",body:{deadline_ms:5000,split:false,words:false}};
const proof:JobAdmissionRefusal={schema:"archeaxis.job-admission-refusal/v1",code:"AAK-CAP-001",job_id:"job",request_id:"frozen",input_ref:"source",kind:"text",capability:"text.extract",budget:attempt.body,admission_state:"NOT_ADMITTED",request_consumed:false,active_execution:false,enabled:false,same_request_retry_allowed:true};
const row=(enabled:boolean)=>({capability:"text.extract",enabled,enabled_basis:"the workspace's capability record; an absent record means enabled"});
const view=(receipt=proof,key="frozen")=><FrozenCapabilityRecovery key={key} proof={receipt} attempt={attempt} source="source" kind="text" disabled={false} current={()=>true} onBusyChange={vi.fn()}/>;
describe("SIMULATED onsite capability decision, frozen identity retained",()=>{
  beforeEach(()=>{bridge.call.mockReset();});
  it.each([{...proof,request_id:"sibling"},{...proof,input_ref:"other"},{...proof,kind:"office"},{...proof,budget:{...attempt.body,split:true}}])("rejects a proof for another frozen identity %#",receipt=>{
    render(view(receipt));expect(screen.queryByRole("button",{name:"启用 text.extract"})).toBeNull();expect(bridge.call).not.toHaveBeenCalled();
  });
  it("lost enable ACK freezes the decision until explicit independent read, without resending or executing",async()=>{
    let enabled=false;
    bridge.call.mockImplementation(async(op:string)=>{
      if(op==="capabilities_list")return {capabilities:[row(enabled)]};
      if(op==="capability_set_enabled"){enabled=true;throw new Error("SIMULATED durable setting, lost ACK");}
      throw new Error(`unexpected ${op}`);
    });
    render(view());fireEvent.click(screen.getByRole("button",{name:"启用 text.extract"}));await screen.findByText(/能力设置 UNKNOWN/);
    expect(screen.getByRole("button",{name:"启用 text.extract"})).toBeDisabled();
    expect(bridge.call.mock.calls.filter(([op])=>op==="capability_set_enabled")).toHaveLength(1);
    fireEvent.click(screen.getByRole("button",{name:"核对 text.extract 设置"}));await screen.findByText(/该能力已启用，工作区设置已读回/);
    expect(bridge.call.mock.calls.filter(([op])=>op==="capability_set_enabled")).toHaveLength(1);
    expect(bridge.call.mock.calls.some(([op])=>op==="job_execute")).toBe(false);
  });
  it.each(["wrong ACK","wrong readback","duplicate list"])("does not announce enabled on %s",async(fault)=>{
    let reads=0;
    bridge.call.mockImplementation(async(op:string)=>{
      if(op==="capabilities_list"){reads++;return {capabilities:fault==="duplicate list"?[row(false),row(false)]:[row(reads>1&&fault!=="wrong readback")]};}
      if(op==="capability_set_enabled")return {capability:{...row(true),...(fault==="wrong ACK"?{capability:"other"}:{})}};
      throw new Error(`unexpected ${op}`);
    });
    render(view());fireEvent.click(screen.getByRole("button",{name:"启用 text.extract"}));await screen.findByText(/能力设置 UNKNOWN/);
    expect(screen.queryByText(/该能力已启用，工作区设置已读回/)).toBeNull();
    expect(bridge.call.mock.calls.filter(([op])=>op==="capability_set_enabled")).toHaveLength(fault==="duplicate list"?0:1);
  });
  it("claims single flight; an old ACK cannot read or update a replacement request",async()=>{
    let resolve!:(v:unknown)=>void;
    bridge.call.mockImplementation(async(op:string)=>op==="capabilities_list"?{capabilities:[row(false)]}:new Promise(r=>{resolve=r;}));
    const shown=render(view());const enable=screen.getByRole("button",{name:"启用 text.extract"});
    act(()=>{fireEvent.click(enable);fireEvent.click(enable);});await waitFor(()=>expect(resolve).toBeDefined());
    expect(bridge.call.mock.calls.filter(([op])=>op==="capability_set_enabled")).toHaveLength(1);
    shown.rerender(<FrozenCapabilityRecovery key="replacement" proof={{...proof,request_id:"replacement"}} attempt={{...attempt,request_id:"replacement"}} source="source" kind="text" disabled={false} current={()=>true} onBusyChange={vi.fn()}/>);await act(async()=>resolve({capability:row(true)}));
    expect(screen.queryByText(/该能力已启用，工作区设置已读回/)).toBeNull();
    expect(bridge.call.mock.calls.filter(([op])=>op==="capabilities_list")).toHaveLength(1);
    expect(screen.getByRole("button",{name:"启用 text.extract"})).toBeEnabled();
  });
});
