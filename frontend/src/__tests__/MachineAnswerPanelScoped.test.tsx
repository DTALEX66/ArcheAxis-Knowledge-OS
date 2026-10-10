import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createHash, webcrypto } from "node:crypto";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MachineAnswerPanel } from "../components/MachineAnswerPanel";
import { ApiError } from "../api/client";
import type { ContextConsumptionDto } from "../api/generated/core-contract";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
type J=Record<string,unknown>;
const grant:ContextConsumptionDto={document_id:"grant",version:2,content_sha256:"a".repeat(64),purpose:"固定原用途"};
const changed:ContextConsumptionDto={...grant,version:3,purpose:"不同用途"};
function answer(request:J){return {schema:"archeaxis.machine-answer/v1",answer_id:"answer_req_"+createHash("sha256").update(String(request.client_request_id)).digest("hex"),client_request_id:request.client_request_id,knowledge_id:request.knowledge_id,question:request.question,answer:{answer:"SIMULATED实际返回",model:"fixture-model"},authority:"candidate",request:{schema:"archeaxis.machine-answer-request/v1",knowledge_id:request.knowledge_id,question:request.question,max_tokens:request.max_tokens,timeout_s:request.timeout_s,context_grant:request.context_grant,context_sha256:"b".repeat(64)}};}
function task(doc:J,scope="runtime.answer"){return {task_id:doc.answer_id,conditions:JSON.stringify(doc),scope,knowledge_version:String(doc.knowledge_id)+"@v1",model_version:(doc.answer as J).model,outcome:"unmeasured",retest_of:scope==="runtime.retest"?doc.retest_of:null,principal:"machine",recorded_at:"SIMULATED",method_version:null,tool_version:null,failure:null};}
async function enterQuestion(){const user=userEvent.setup();await user.type(screen.getByLabelText("实际问题"),"固定问题");await user.click(screen.getByRole("button",{name:"执行本地机器回答"}));return user;}
describe("SIMULATED real scoped Panel lostACK contracts",()=>{
 beforeEach(()=>{bridge.call.mockReset();vi.stubGlobal("crypto",webcrypto);});afterEach(()=>vi.unstubAllGlobals());
 it.each(["RECORDED","FAILED"] as const)("executed withheld %s disables retry until a new explicit decision",async(audit_status)=>{
  bridge.call.mockRejectedValue(new ApiError(audit_status==="RECORDED"?403:500,"executed", "unavailable",{execution_state:"EXECUTED_BUT_WITHHELD",answer_published:false,audit_status,audit_task_id:audit_status==="RECORDED"?`withheld_${"a".repeat(64)}`:null}));
  render(<MachineAnswerPanel knowledgeId="k1" scoped contextGrant={grant}/>);await enterQuestion();await screen.findByRole("button",{name:"结束已执行但未发布的请求，保留草稿"});
  expect(screen.getByRole("button",{name:"执行本地机器回答"})).toBeDisabled();expect(screen.getByLabelText("实际问题")).toHaveValue("固定问题");expect(bridge.call).toHaveBeenCalledTimes(1);
  expect(screen.queryByRole("button",{name:"重试同一回答请求"})).not.toBeInTheDocument();expect(screen.queryByLabelText("真实机器回答")).not.toBeInTheDocument();
 });
 it("keeps exact request identity and original context across an unknown acknowledgment",async()=>{
  const calls:J[]=[];let saved:J|null=null;
  bridge.call.mockImplementation(async(op:string,p:J={})=>{
   if(op==="machine_answer"){calls.push(structuredClone(p.body as J));saved=answer(p.body as J);if(calls.length===1)throw new ApiError(502,"lost ACK");return saved;}
   if(op==="machine_task_get")return task(saved!);throw new Error("unexpected "+op);
  });
  const ui=render(<MachineAnswerPanel knowledgeId="k1" scoped contextGrant={grant}/>);const user=await enterQuestion();await screen.findByText(/状态 UNKNOWN。请读取历史核对/);
  ui.rerender(<MachineAnswerPanel knowledgeId="k1" scoped contextGrant={changed}/>);
  await user.clear(screen.getByLabelText("实际问题"));await user.type(screen.getByLabelText("实际问题"),"后续不同草稿");await user.click(screen.getByRole("button",{name:"重试同一回答请求"}));
  expect(await screen.findByLabelText("真实机器回答")).toHaveTextContent("SIMULATED实际返回");expect(calls).toHaveLength(2);expect(calls[1]).toEqual(calls[0]);expect((calls[1].context_grant as J).purpose).toBe("固定原用途");
  expect(screen.getByLabelText("实际问题")).toHaveValue("后续不同草稿");
 });
 it("withholds publication when Core returns another deterministic request identity",async()=>{
  bridge.call.mockImplementation(async(op:string,p:J={})=>op==="machine_answer"?{...answer(p.body as J),answer_id:"wrong"}:Promise.reject(new Error("must not read false identity")));
  render(<MachineAnswerPanel knowledgeId="k1" scoped contextGrant={grant}/>);await enterQuestion();await screen.findByText(/状态 UNKNOWN。请读取历史核对/);
  expect(screen.queryByLabelText("真实机器回答")).not.toBeInTheDocument();expect(bridge.call).toHaveBeenCalledTimes(1);
 });
 it("does not call inference after current answer permission disappears",async()=>{
  const ui=render(<MachineAnswerPanel knowledgeId="k1" scoped contextGrant={grant}/>);const user=userEvent.setup();await user.type(screen.getByLabelText("实际问题"),"问题");
  ui.rerender(<MachineAnswerPanel knowledgeId="k1" scoped/>);expect(screen.getByRole("button",{name:"执行本地机器回答"})).toBeDisabled();expect(screen.getByRole("button",{name:"读取机器学习历史"})).toBeEnabled();expect(bridge.call).not.toHaveBeenCalled();
 });
 it("executed-but-unconfirmed response remains UNKNOWN, never NOT_RUN or automatic retry",async()=>{
  bridge.call.mockRejectedValue(new ApiError(502,"executed response withheld, confirmation unavailable"));render(<MachineAnswerPanel knowledgeId="k1" scoped contextGrant={grant}/>);await enterQuestion();await screen.findByText(/状态 UNKNOWN。请读取历史核对/);
  expect(bridge.call).toHaveBeenCalledTimes(1);expect(screen.queryByText(/NOT_RUN|未执行模型/)).not.toBeInTheDocument();expect(screen.queryByLabelText("真实机器回答")).not.toBeInTheDocument();
 });
 it("history restoration cannot replace an unfinished question",async()=>{
  const saved={schema:"archeaxis.machine-answer/v1",answer_id:"old",knowledge_id:"k1",question:"旧问题",answer:{answer:"旧回答",model:"fixture-model"},authority:"candidate"};const row=task(saved);
  bridge.call.mockImplementation(async(op:string)=>op==="machine_tasks_list"?{items:[row],next_cursor:null}:op==="machine_task_get"?row:Promise.reject(new Error("unexpected write")));
  render(<MachineAnswerPanel knowledgeId="k1" scoped contextGrant={grant}/>);const user=userEvent.setup();await user.click(screen.getByRole("button",{name:"读取机器学习历史"}));await screen.findByRole("button",{name:"读取此任务旅程 old"});
  await user.type(screen.getByLabelText("实际问题"),"未提交新问题");await user.click(screen.getByRole("button",{name:"读取此任务旅程 old"}));
  expect(screen.getByLabelText("实际问题")).toHaveValue("未提交新问题");expect(screen.queryByLabelText("真实机器回答")).not.toBeInTheDocument();
 });
 it("lost retest acknowledgment freezes the original purpose even when props change",async()=>{
  const original={schema:"archeaxis.machine-answer/v1",answer_id:"old",knowledge_id:"k1",question:"旧问题",answer:{answer:"旧回答",model:"fixture-model"},authority:"candidate"};
  const correction={schema:"archeaxis.machine-correction/v1",answer_id:"old",failed_task_id:"evaluation_old",correction_candidate_id:"correction1",corrects_knowledge_id:"k1",question:"旧问题",machine_answer:"旧回答",corrected_answer:"修正",error_note:"实际依据",reviewer:"human",status:"candidate",authority:"candidate"};
  const evaluation={...original,correction};const failed={...task(evaluation),task_id:"evaluation_old",conditions:JSON.stringify(evaluation),scope:"runtime.evaluation.failed",outcome:"failed",failure:"实际依据"};
  const requests:J[]=[];let retest:J|null=null;
  bridge.call.mockImplementation(async(op:string,p:J={})=>{
   if(op==="machine_tasks_list")return {items:[failed],next_cursor:null};
   if(op==="knowledge_get")return {knowledge_id:"correction1",body:"修正",version:"hash-v2",status:"accepted"};
   if(op==="machine_retest"){const b=p.body as J;requests.push(structuredClone(b));retest={schema:"archeaxis.machine-retest/v1",retest_task_id:"retest1",answer_id:"retest1",retest_of:b.retest_of,knowledge_id:b.knowledge_id,question:b.question,answer:{answer:"复测回答",model:"fixture-model"},authority:"candidate",request:{retest_of:b.retest_of,knowledge_id:b.knowledge_id,question:b.question,max_tokens:b.max_tokens,context_grant:b.context_grant}};if(requests.length===1)throw new ApiError(502,"lostACK");return retest;}
   if(op==="machine_task_get")return p.task_id==="old"?task(original):p.task_id==="evaluation_old"?failed:task(retest!,"runtime.retest");
   throw new Error("unexpected "+op);
  });
  const ui=render(<MachineAnswerPanel knowledgeId="k1" scoped contextGrant={grant} retestContextGrant={grant}/>);const user=userEvent.setup();await user.click(screen.getByRole("button",{name:"读取机器学习历史"}));await user.click(await screen.findByRole("button",{name:"读取此任务旅程 evaluation_old"}));
  await user.click(await screen.findByRole("button",{name:"以已接受纠正知识运行独立复测"}));await screen.findByText(/复测未完成或持久化读回未确认/);
  ui.rerender(<MachineAnswerPanel knowledgeId="k1" scoped contextGrant={grant} retestContextGrant={changed}/>);await user.click(screen.getByRole("button",{name:"重试同一冻结复测请求"}));
  await waitFor(()=>expect(requests).toHaveLength(2));expect(requests[1]).toEqual(requests[0]);
 });
});
