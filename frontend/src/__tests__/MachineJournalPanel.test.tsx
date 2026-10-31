import { waitFor } from "@testing-library/react";
import { within } from "@testing-library/react";
import {expect,it,vi} from "vitest";
import {render,screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {webcrypto} from "node:crypto";
import {act} from "@testing-library/react";
import {MachineAnswerPanel} from "../components/MachineAnswerPanel";
import {CoreWorkingStateSession,type WorkingRead,type WorkingTransport} from "../presentation/coreWorkingState";
import {CoreWorkingStateProvider} from "../presentation/useCoreWorkingState";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
it.each(["FAILED","UNKNOWN","ACK_LOSS","CANCELLED_LOCAL_WORKER"])("SIMULATED cold failure status %s preserves drafts and never invokes inference",async(mode)=>{
  bridge.call.mockReset();
  const entry={journal_id:"failed_fixed",owner_knowledge_id:"k1",operation:"answer" as const,origin_restore_epoch:"initial",body:{knowledge_id:"k1",question:"Synthetic failed question",max_tokens:2048,timeout_s:120,client_request_id:"failed_fixed"}};
  let server:WorkingRead={schema:"archeaxis.ui-working-state/v1",workspace_id:"a".repeat(32),restore_epoch:"initial",state_revision:1,state:{drafts:{},opened_documents:[],active_document:null,page_id:null,pending_original:null,pending_machine:{failed_fixed:entry}},draft_digests:{},pending_document_id:null,recovery_candidates:null,recovery_requires_confirmation:false};
  const clear=vi.fn(async()=>{const state={...server.state};delete state.pending_machine;server={...server,state_revision:2,state};if(mode==="ACK_LOSS")throw new Error("lost clear ACK");return structuredClone(server);});
  const session=new CoreWorkingStateSession({read:async()=>structuredClone(server),write:vi.fn(),clearSaved:vi.fn(),recover:vi.fn(),clearMachine:clear});await session.load();
  bridge.call.mockImplementation(async(op:string,p:{body:{journal_id:string}})=>{
    expect(["ui_state_machine_status","ui_state_cancel_machine"]).toContain(op);expect(p.body.journal_id).toBe(entry.journal_id);
    if(op==="ui_state_cancel_machine")return {schema:"archeaxis.machine-cancel-receipt/v1",journal_id:entry.journal_id,cancel_requested:true,attempt:2,execution_state:"UNKNOWN",provider_stop_state:"UNKNOWN"};
    return {schema:"archeaxis.machine-journal-status/v1",journal_id:entry.journal_id,status:mode==="UNKNOWN"?"UNKNOWN":mode==="CANCELLED_LOCAL_WORKER"?mode:"FAILED",can_clear:mode!=="UNKNOWN",task_id:mode==="UNKNOWN"?null:"failure_exact",attempt:mode==="UNKNOWN"?null:2,max_attempts:3,provider_stop_state:"UNKNOWN"};
  });
  render(<CoreWorkingStateProvider session={session}><MachineAnswerPanel knowledgeId="k1"/></CoreWorkingStateProvider>);
  const user=userEvent.setup();await screen.findByText(/已恢复未确认/);
  if(mode==="CANCELLED_LOCAL_WORKER"){
    await user.click(screen.getByRole("button",{name:"请求取消本次本地生成"}));
    await screen.findByText(/取消请求已接收；尚未确认停止/);
    expect(clear).not.toHaveBeenCalled();expect(session.getSnapshot().state.pending_machine?.failed_fixed).toEqual(entry);
  }
  await user.click(screen.getByRole("button",{name:"检查上次调用结果"}));
  if(mode==="UNKNOWN"){
    await screen.findByText(/未确认当前请求的失败终态/);expect(screen.queryByRole("button",{name:"结束失败请求，保留草稿"})).not.toBeInTheDocument();expect(clear).not.toHaveBeenCalled();
    expect(session.getSnapshot().state.pending_machine?.failed_fixed).toEqual(entry);expect(screen.getByRole("button",{name:"重试同一回答请求"})).toBeDisabled();
  }else{
    await user.click(await screen.findByRole("button",{name:"结束失败请求，保留草稿"}));
    if(mode==="ACK_LOSS"){await screen.findByText(/结束回执未确认/);await act(async()=>{await session.load();});}
    expect(session.getSnapshot().state.pending_machine?.failed_fixed).toBeUndefined();expect(clear).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText("实际问题")).toHaveValue(entry.body.question);expect(screen.getByRole("button",{name:"执行本地机器回答"})).toBeEnabled();
  }
  expect(bridge.call).toHaveBeenCalledTimes(mode==="CANCELLED_LOCAL_WORKER"?2:1);
});
it.each(["success","committed_ack_loss","uncommitted_ack_loss"])("SIMULATED exact withheld retirement %s never repeats inference",async(mode)=>{
  vi.stubGlobal("crypto",webcrypto);bridge.call.mockClear();
  try {
    const entry={journal_id:"withheld_fixed",owner_knowledge_id:"k1",operation:"answer" as const,origin_restore_epoch:"initial",body:{knowledge_id:"k1",question:"Synthetic withheld question",max_tokens:2048,timeout_s:120,client_request_id:"withheld_fixed"}};
    const normalized={operation:"answer",request:{...entry.body,context_grant:null,asset_context_grant:null,retest_of:null}};
    const sorted=JSON.stringify(normalized,(_key,item)=>item&&typeof item==="object"&&!Array.isArray(item)?Object.fromEntries(Object.entries(item).sort(([a],[b])=>a<b?-1:a>b?1:0)):item);
    const hash=Array.from(new Uint8Array(await webcrypto.subtle.digest("SHA-256",new TextEncoder().encode(sorted))),b=>b.toString(16).padStart(2,"0")).join("");
    const doc={schema:"archeaxis.machine-execution-withheld/v1",audit_task_id:"withheld_audit",execution_state:"EXECUTED_BUT_WITHHELD",operation:"answer",knowledge_id:"k1",client_request_id:entry.journal_id,retest_of:null,answer_published:false,authority:"historical_execution_audit",admission_request_sha256:hash};
    const row={task_id:doc.audit_task_id,principal:"machine",conditions:JSON.stringify(doc),model_version:"synthetic",scope:"runtime.execution.withheld",recorded_at:"synthetic",outcome:"failed",knowledge_version:null,method_version:null,tool_version:null,failure:"SYNTHETIC",retest_of:null};
    bridge.call.mockImplementation(async(op:string)=>{if(op==="machine_tasks_list")return {items:[row],next_cursor:null};if(op==="machine_task_get")return row;throw new Error("Unexpected inference or command "+op);});
    let server:WorkingRead={schema:"archeaxis.ui-working-state/v1",workspace_id:"a".repeat(32),restore_epoch:"initial",state_revision:1,state:{drafts:{},opened_documents:[],active_document:null,page_id:null,pending_original:null,pending_machine:{withheld_fixed:entry}},draft_digests:{},pending_document_id:null,recovery_candidates:null,recovery_requires_confirmation:false};
    const clear=vi.fn(async()=>{if(mode!=="uncommitted_ack_loss"){const state={...server.state};delete state.pending_machine;server={...server,state_revision:2,state};}if(mode!=="success")throw new Error("SIMULATED clear ACK loss");return structuredClone(server);});
    const session=new CoreWorkingStateSession({read:async()=>structuredClone(server),write:vi.fn(),clearSaved:vi.fn(),recover:vi.fn(),clearMachine:clear});await session.load();
    render(<CoreWorkingStateProvider session={session}><MachineAnswerPanel knowledgeId="k1"/></CoreWorkingStateProvider>);
    const user=userEvent.setup();await screen.findByText(/已恢复未确认/);await user.click(screen.getByRole("button",{name:"读取机器学习历史"}));
    await user.click(await savedTaskButton("withheld_audit"));
    const finish=await screen.findByRole("button",{name:"结束已执行但未发布的请求，保留草稿"});expect(finish).toBeEnabled();await user.click(finish);
    if(mode!=="success"){await screen.findByText(/结束回执未确认/);expect(screen.getByRole("button",{name:/同一回答请求/})).toBeDisabled();await act(async()=>{await session.load();});}
    if(mode==="uncommitted_ack_loss"){expect(session.getSnapshot().state.pending_machine?.withheld_fixed).toEqual(entry);expect(screen.getByRole("button",{name:/同一回答请求/})).toBeDisabled();}
    else {expect(session.getSnapshot().state.pending_machine?.withheld_fixed).toBeUndefined();expect(screen.getByRole("button",{name:"执行本地机器回答"})).toBeEnabled();}
    expect(clear).toHaveBeenCalledTimes(1);expect(bridge.call.mock.calls.every(([op])=>op!=="machine_answer"&&op!=="machine_retest")).toBe(true);
  }finally{vi.unstubAllGlobals();}
});
it("SIMULATED multiple unresolved requests prevent a fresh inference",async()=>{
  bridge.call.mockClear();
  const pending_machine=Object.fromEntries(["pending_a","pending_b"].map(journal_id=>[journal_id,{journal_id,owner_knowledge_id:"k1",operation:"answer" as const,origin_restore_epoch:"initial",body:{knowledge_id:"k1",question:"Synthetic unresolved question",max_tokens:2048,timeout_s:120,client_request_id:journal_id}}]));
  const server:WorkingRead={schema:"archeaxis.ui-working-state/v1",workspace_id:"a".repeat(32),restore_epoch:"initial",state_revision:1,state:{drafts:{},opened_documents:[],active_document:null,page_id:null,pending_original:null,pending_machine},draft_digests:{},pending_document_id:null,recovery_candidates:null,recovery_requires_confirmation:false};
  const session=new CoreWorkingStateSession({read:async()=>structuredClone(server),write:vi.fn(),clearSaved:vi.fn(),recover:vi.fn()});await session.load();
  render(<CoreWorkingStateProvider session={session}><MachineAnswerPanel knowledgeId="k1"/></CoreWorkingStateProvider>);
  await screen.findByText(/多条未确认机器请求/);
  expect(screen.getByRole("button",{name:"执行本地机器回答"})).toBeDisabled();expect(bridge.call).not.toHaveBeenCalled();
});
it("SIMULATED journal ACK loss prevents inference and reopening restores a read-only pending answer",async()=>{
  bridge.call.mockImplementation(async(op:string)=>{if(op==="model_configuration_get")return {schema:"archeaxis.model-configuration/v1",revision:0,profiles:{},bindings:[],workspace_id:"a".repeat(32),restore_epoch:"initial"};throw new Error("Unexpected inference or command "+op);});
  vi.stubGlobal("crypto",webcrypto);
  try {
    let server:WorkingRead={schema:"archeaxis.ui-working-state/v1",workspace_id:"a".repeat(32),restore_epoch:"initial",state_revision:0,state:{drafts:{},opened_documents:[],active_document:null,page_id:null,pending_original:null},draft_digests:{},pending_document_id:null,recovery_candidates:null,recovery_requires_confirmation:false};
    const transport:WorkingTransport={read:async()=>structuredClone(server),write:async body=>{server={...server,state_revision:server.state_revision+1,state:structuredClone(body.state)};throw new Error("SIMULATED lost journal ACK");},clearSaved:vi.fn(),recover:vi.fn()};
    const session=new CoreWorkingStateSession(transport);await session.load();
    const ui=render(<CoreWorkingStateProvider session={session}><MachineAnswerPanel knowledgeId="k1"/></CoreWorkingStateProvider>);
    const user=userEvent.setup();await user.type(screen.getByLabelText("实际问题"),"Frozen synthetic question");await user.click(screen.getByRole("button",{name:"执行本地机器回答"}));
    await screen.findByText(/回答未完成或持久化读回未确认/);expect(bridge.call.mock.calls.map(([op])=>op)).toEqual(["model_configuration_get"]);
    const entries=Object.values(server.state.pending_machine??{});expect(entries).toHaveLength(1);expect(entries[0].body.client_request_id).toBe(entries[0].journal_id);
    ui.unmount();const reopened=new CoreWorkingStateSession(transport);await reopened.load();
    render(<CoreWorkingStateProvider session={reopened}><MachineAnswerPanel knowledgeId="k1"/></CoreWorkingStateProvider>);
    await screen.findByText(/已恢复未确认的机器请求/);expect(screen.getByLabelText("实际问题")).toHaveValue("Frozen synthetic question");
    expect(screen.getByRole("button",{name:"重试同一回答请求"})).toBeDisabled();expect(bridge.call.mock.calls.map(([op])=>op)).toEqual(["model_configuration_get"]);
  } finally {vi.unstubAllGlobals();}
});
it.each([false,true])("SIMULATED duplicate frozen requests retire individually with external clear %s",async(externalClear)=>{
  vi.stubGlobal("crypto",webcrypto);bridge.call.mockClear();
  try {
    const body={knowledge_id:"k1",question:"Synthetic duplicate question",max_tokens:2048,timeout_s:120,client_request_id:"shared_request"};
    const pending_machine=Object.fromEntries(["journal_a","journal_b"].map(journal_id=>[journal_id,{journal_id,owner_knowledge_id:"k1",operation:"answer" as const,origin_restore_epoch:"initial",body}]));
    const normalized={operation:"answer",request:{...body,context_grant:null,asset_context_grant:null,retest_of:null}};
    const sorted=JSON.stringify(normalized,(_key,item)=>item&&typeof item==="object"&&!Array.isArray(item)?Object.fromEntries(Object.entries(item).sort(([a],[b])=>a<b?-1:a>b?1:0)):item);
    const hash=Array.from(new Uint8Array(await webcrypto.subtle.digest("SHA-256",new TextEncoder().encode(sorted))),b=>b.toString(16).padStart(2,"0")).join("");
    const doc={schema:"archeaxis.machine-execution-withheld/v1",audit_task_id:"duplicate_audit",execution_state:"EXECUTED_BUT_WITHHELD",operation:"answer",knowledge_id:"k1",client_request_id:body.client_request_id,retest_of:null,answer_published:false,authority:"historical_execution_audit",admission_request_sha256:hash};
    const row={task_id:doc.audit_task_id,principal:"machine",conditions:JSON.stringify(doc),model_version:"synthetic",scope:"runtime.execution.withheld",recorded_at:"synthetic",outcome:"failed",knowledge_version:null,method_version:null,tool_version:null,failure:"SYNTHETIC",retest_of:null};
    bridge.call.mockImplementation(async(op:string)=>{if(op==="machine_tasks_list")return {items:[row],next_cursor:null};if(op==="machine_task_get")return row;throw new Error("Unexpected inference "+op);});
    let server:WorkingRead={schema:"archeaxis.ui-working-state/v1",workspace_id:"a".repeat(32),restore_epoch:"initial",state_revision:1,state:{drafts:{},opened_documents:[],active_document:null,page_id:null,pending_original:null,pending_machine},draft_digests:{},pending_document_id:null,recovery_candidates:null,recovery_requires_confirmation:false};
    const clear=vi.fn(async(input)=>{const remaining={...server.state.pending_machine};delete remaining[input.journal_id];const state={...server.state};if(Object.keys(remaining).length)state.pending_machine=remaining;else delete state.pending_machine;server={...server,state_revision:server.state_revision+1,state};return structuredClone(server);});
    const session=new CoreWorkingStateSession({read:async()=>structuredClone(server),write:vi.fn(),clearSaved:vi.fn(),recover:vi.fn(),clearMachine:clear});await session.load();
    render(<CoreWorkingStateProvider session={session}><MachineAnswerPanel knowledgeId="k1"/></CoreWorkingStateProvider>);
    const user=userEvent.setup();await screen.findByText(/多条未确认机器请求/);
    await user.selectOptions(screen.getByLabelText("待核对机器请求"),"journal_a");
    if(externalClear){server={...server,state_revision:2,state:{...server.state,pending_machine:{journal_b:pending_machine.journal_b}}};await act(async()=>{await session.load();});}
    await user.click(screen.getByRole("button",{name:"读取机器学习历史"}));
    await user.click(await savedTaskButton("duplicate_audit"));
    await user.click(await screen.findByRole("button",{name:"结束已执行但未发布的请求，保留草稿"}));
    if(!externalClear){expect(Object.keys(session.getSnapshot().state.pending_machine??{})).toEqual(["journal_b"]);
      await user.click(await savedTaskButton("duplicate_audit"));
      await user.click(await screen.findByRole("button",{name:"结束已执行但未发布的请求，保留草稿"}));}
    expect(session.getSnapshot().state.pending_machine).toBeUndefined();expect(clear).toHaveBeenCalledTimes(externalClear?1:2);
    expect(screen.getByRole("button",{name:"执行本地机器回答"})).toBeEnabled();
    expect(bridge.call.mock.calls.every(([op])=>op!=="machine_answer"&&op!=="machine_retest")).toBe(true);
  }finally{vi.unstubAllGlobals();}
});

async function savedTaskButton(taskId: string) {
  return waitFor(() => {
    const rows = [...document.querySelectorAll('[aria-label="既有机器学习任务"] li[data-task-id]')]
      .filter(row => row.getAttribute("data-task-id") === taskId);
    expect(rows).toHaveLength(1);
    return within(rows[0] as HTMLElement).getByRole("button", { name: "查看这次任务" });
  });
}
