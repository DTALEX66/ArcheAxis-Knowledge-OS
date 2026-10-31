import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { FrozenCapabilityRecovery } from "../components/FrozenCapabilityRecovery";
import type { JobAdmissionRefusal } from "../api/client";
import { DiagnosticConsole } from "../components/DiagnosticConsole";
import { clearDiagnostics } from "../presentation/diagnostics";
const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const attempt={job_id:"job",request_id:"frozen",body:{deadline_ms:5000,split:false,words:false}};
const proof:JobAdmissionRefusal={schema:"archeaxis.job-admission-refusal/v1",code:"AAK-CAP-001",job_id:"job",request_id:"frozen",input_ref:"source",kind:"text",capability:"text.extract",budget:attempt.body,admission_state:"NOT_ADMITTED",request_consumed:false,active_execution:false,enabled:false,same_request_retry_allowed:true};
const row=(enabled:boolean)=>({capability:"text.extract",enabled,enabled_basis:"the workspace's capability record; an absent record means enabled"});
const view=(receipt=proof,key="frozen")=><FrozenCapabilityRecovery key={key} proof={receipt} attempt={attempt} source="source" kind="text" disabled={false} current={()=>true} onBusyChange={vi.fn()}/>;
describe("SIMULATED onsite capability decision, frozen identity retained",()=>{
  beforeEach(()=>{bridge.call.mockReset();clearDiagnostics();});
  it.each([{...proof,request_id:"sibling"},{...proof,input_ref:"other"},{...proof,kind:"office"},{...proof,budget:{...attempt.body,split:true}}])("rejects a proof for another frozen identity %#",receipt=>{
    render(view(receipt));expect(screen.queryByRole("button",{name:"启用文字解析"})).toBeNull();expect(bridge.call).not.toHaveBeenCalled();
  });
  it("lost enable ACK freezes the decision until explicit independent read, without resending or executing",async()=>{
    let enabled=false;
    bridge.call.mockImplementation(async(op:string)=>{
      if(op==="capabilities_list")return {capabilities:[row(enabled)]};
      if(op==="capability_set_enabled"){enabled=true;throw new Error("SIMULATED durable setting, lost ACK");}
      throw new Error(`unexpected ${op}`);
    });
    render(view());fireEvent.click(screen.getByRole("button",{name:"启用文字解析"}));await screen.findByText(/能力设置结果待确认/);
    expect(screen.getByRole("button",{name:"启用文字解析"})).toBeDisabled();
    expect(bridge.call.mock.calls.filter(([op])=>op==="capability_set_enabled")).toHaveLength(1);
    fireEvent.click(screen.getByRole("button",{name:"核对文字解析设置"}));await screen.findByText(/该能力已启用，并已重新核对工作区设置/);
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
    render(view());fireEvent.click(screen.getByRole("button",{name:"启用文字解析"}));await screen.findByText(/能力设置结果待确认/);
    expect(screen.queryByText(/该能力已启用，并已重新核对工作区设置/)).toBeNull();
    expect(bridge.call.mock.calls.filter(([op])=>op==="capability_set_enabled")).toHaveLength(fault==="duplicate list"?0:1);
  });
  it("claims single flight; an old ACK cannot read or update a replacement request",async()=>{
    let resolve!:(v:unknown)=>void;
    bridge.call.mockImplementation(async(op:string)=>op==="capabilities_list"?{capabilities:[row(false)]}:new Promise(r=>{resolve=r;}));
    const shown=render(view());const enable=screen.getByRole("button",{name:"启用文字解析"});
    act(()=>{fireEvent.click(enable);fireEvent.click(enable);});await waitFor(()=>expect(resolve).toBeDefined());
    expect(bridge.call.mock.calls.filter(([op])=>op==="capability_set_enabled")).toHaveLength(1);
    shown.rerender(<FrozenCapabilityRecovery key="replacement" proof={{...proof,request_id:"replacement"}} attempt={{...attempt,request_id:"replacement"}} source="source" kind="text" disabled={false} current={()=>true} onBusyChange={vi.fn()}/>);await act(async()=>resolve({capability:row(true)}));
    expect(screen.queryByText(/该能力已启用，并已重新核对工作区设置/)).toBeNull();
    expect(bridge.call.mock.calls.filter(([op])=>op==="capabilities_list")).toHaveLength(1);
    expect(screen.getByRole("button",{name:"启用文字解析"})).toBeEnabled();
  });
  it("uses an actionable capability name and keeps the complete original identity in diagnostics only",()=>{
    render(<>{view()}<DiagnosticConsole/></>);
    const panel=screen.getByRole("region",{name:"处理能力恢复"});
    expect(panel).toHaveTextContent("本地服务已确认本次处理请求未受理");
    expect(within(panel).getByRole("button",{name:"启用文字解析"})).toBeEnabled();
    expect(panel).not.toHaveTextContent(/Core|UNKNOWN|text\.extract|冻结/);
    fireEvent.click(within(panel).getByRole("button",{name:"状态与诊断：未受理请求与能力记录"}));
    const raw=within(screen.getByRole("region",{name:"诊断控制台"})).getByText(/"NOT_ADMITTED"/,{selector:"pre"});
    expect(JSON.parse(raw.textContent!)).toEqual({proof,attempt});
    expect(bridge.call).not.toHaveBeenCalled();
  });
});
