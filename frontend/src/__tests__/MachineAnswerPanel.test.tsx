import { within } from "@testing-library/react";
import {createHash} from "node:crypto";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MachineAnswerPanel } from "../components/MachineAnswerPanel";
import { ApiError } from "../api/client";
import { resetDiagnostics,useDiagnostics } from "../presentation/diagnostics";
import { renderHook } from "@testing-library/react";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:(op:string,...args:unknown[])=>op==="model_configuration_get"?Promise.resolve({schema:"archeaxis.model-configuration/v1",revision:0,workspace_id:"a".repeat(32),restore_epoch:"initial",profiles:{},bindings:[]}):bridge.call(op,...args)}));
const answer={schema:"archeaxis.machine-answer/v1",answer_id:"answer1",knowledge_id:"k1",question:"实际问题",answer:{answer:"实际机器回答",model:"local-model"},authority:"candidate"};
const retestReceipt={schema:"archeaxis.machine-retest/v1",retest_task_id:"retest1",answer_id:"retest1",retest_of:"evaluation_answer1",knowledge_id:"correction1",question:"实际问题",answer:{answer:"纠正后复测回答",model:"local-model"},authority:"candidate",prior:{},request:{retest_of:"evaluation_answer1",knowledge_id:"correction1",question:"实际问题",max_tokens:2048},execution_request:{schema:"archeaxis.machine-retest-execution/v1",timeout_s:120,request:{retest_of:"evaluation_answer1",knowledge_id:"correction1",question:"实际问题",max_tokens:2048}},note:"human compares"};
function task(doc:typeof answer|typeof retestReceipt,scope="runtime.answer") {return {task_id:doc.answer_id,conditions:JSON.stringify(doc),scope,knowledge_version:doc.knowledge_id+"@v1",model_version:doc.answer.model,outcome:"unmeasured",retest_of:scope==="runtime.retest"?"evaluation_answer1":null};}
describe("SIMULATED machine candidate UI with Core bridge fixtures",()=>{
 beforeEach(()=>{bridge.call.mockReset();});
 it("keeps failed answer measurements in the shared diagnostic center and preserves input without retry",async()=>{
  resetDiagnostics();const diagnostics={finish_reason:"length",elapsed_s:2.5,usage:{output_tokens:2048}};
  bridge.call.mockRejectedValue(new ApiError(503,"模型未返回最终答案","unavailable",undefined,undefined,undefined,{reason_code:"NO_FINAL_ANSWER",execution_state:"UNVERIFIED",answer_published:false,diagnostics}));
  const entries=renderHook(useDiagnostics);const debug=vi.spyOn(console,"debug").mockImplementation(()=>{});
  render(<MachineAnswerPanel knowledgeId="k1"/>);const user=userEvent.setup();
  await user.type(screen.getByLabelText("实际问题"),"保留原问题");await user.click(screen.getByRole("button",{name:"执行本地机器回答"}));
  const detail=await screen.findByRole("button",{name:"状态与诊断：回答失败脱敏诊断"});
  expect(screen.getByLabelText("实际问题")).toHaveValue("保留原问题");
  expect(screen.getByRole("button",{name:"重试同一回答请求"})).toBeDisabled();
  expect(bridge.call.mock.calls.filter(([op])=>op==="machine_answer")).toHaveLength(1);
  await user.click(detail);expect(entries.result.current.at(-1)?.payload).toEqual({reason_code:"NO_FINAL_ANSWER",execution_state:"UNVERIFIED",answer_published:false,diagnostics});
  expect(debug).not.toHaveBeenCalled();debug.mockRestore();
 });
 it("reads a persisted answer and requires explicit human correction fields without accepting",async()=>{
  let liveAnswer:typeof answer & Record<string,unknown>=answer;
  let candidateStatus="candidate",candidateVersion="correction-v1";
  bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>={})=>{
   if(op==="machine_answer"){const body=payload.body as Record<string,unknown>;liveAnswer={...answer,answer_id:"answer_req_"+createHash("sha256").update(String(body.client_request_id)).digest("hex"),client_request_id:body.client_request_id,request:{...body,schema:"archeaxis.machine-answer-request/v1",context_grant:null,context_sha256:"a".repeat(64)}};return liveAnswer;}
   if(op==="machine_task_get" && payload.task_id==="retest1")return task(retestReceipt,"runtime.retest");
   if(op==="machine_task_get")return task(liveAnswer);
   if(op==="machine_correction")return {answer_id:liveAnswer.answer_id,failed_task_id:"evaluation_answer1",correction_candidate_id:"correction1",status:"candidate",authority:"candidate",corrects_knowledge_id:"k1",question:"实际问题",machine_answer:"实际机器回答",corrected_answer:"使用者纠正",error_note:"具体错误依据",reviewer:"实际使用者"};
   if(op==="machine_retest")return retestReceipt;
   if(op==="knowledge_get")return {knowledge_id:"correction1",body:"使用者纠正",version:candidateVersion,status:candidateStatus};
   if(op==="knowledge_review"){candidateStatus=(payload.body as Record<string,unknown>).action as string;candidateVersion=candidateVersion==="correction-v1"?"correction-v2":"correction-v3";return {knowledge_id:"correction1",version:candidateVersion};}
   if (op === undefined) return undefined;
   throw new Error(`unexpected Core command: ${String(op)} ${JSON.stringify(payload)}`);
  });
  render(<MachineAnswerPanel knowledgeId="k1"/>);const user=userEvent.setup();await user.type(screen.getByLabelText("实际问题"),"实际问题");await user.click(screen.getByRole("button",{name:"执行本地机器回答"}));
  expect(await screen.findByLabelText("真实机器回答")).toHaveTextContent("实际机器回答");expect(screen.getByRole("button",{name:"记录使用者纠正候选"})).toBeDisabled();
  await user.type(screen.getByLabelText("正确答案"),"使用者纠正");await user.type(screen.getByLabelText("具体错误依据"),"具体错误依据");await user.type(screen.getByLabelText("纠正提交者"),"实际使用者");await user.click(screen.getByRole("button",{name:"记录使用者纠正候选"}));
  await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("machine_correction",{body:{answer_id:liveAnswer.answer_id,knowledge_id:"k1",question:"实际问题",machine_answer:"实际机器回答",corrected_answer:"使用者纠正",error_note:"具体错误依据",reviewer:"实际使用者"}}));
  expect(await screen.findByText("待审核")).toBeInTheDocument();expect(screen.getByRole("region",{name:"纠正候选审核"})).toBeInTheDocument();
  expect(screen.getByText("已保存的纠正正文").parentElement).toHaveTextContent("使用者纠正");
  expect(screen.getByText("纠正候选修订").parentElement).toHaveTextContent("correction-v1");
  expect(bridge.call.mock.calls.some(([op])=>op==="knowledge_review")).toBe(false);
  expect(screen.queryByRole("button",{name:"以已接受纠正知识运行独立复测"})).not.toBeInTheDocument();
  await user.type(screen.getByLabelText("审核依据"),"已对照专业来源");await user.click(screen.getByRole("button",{name:"接受纠正知识"}));
  await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("knowledge_review",{id:"correction1",body:{action:"accepted",reviewer:"实际使用者",note:"已对照专业来源",expected_version:"correction-v1"}}));
  await user.click(await screen.findByRole("button",{name:"以已接受纠正知识运行独立复测"}));
  await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("machine_retest",{body:{retest_of:"evaluation_answer1",knowledge_id:"correction1",question:"实际问题",max_tokens:2048,timeout_s:120}}));
  expect(await screen.findByLabelText("独立复测机器回答")).toHaveTextContent("纠正后复测回答");
  expect(screen.getByRole("region",{name:"独立复测结果对照"})).toHaveTextContent("结果尚未由真人比较。");
  await user.click(screen.getByRole("button",{name:"撤回已接受纠正（标记为弃用）"}));
  await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("knowledge_review",{id:"correction1",body:{action:"deprecated",reviewer:"实际使用者",note:"已对照专业来源",expected_version:"correction-v2"}}));
  expect(screen.getByRole("region",{name:"独立复测结果对照"})).toHaveTextContent("纠正后复测回答");
 });
 it("withholds an answer when the persistent task readback differs",async()=>{
  bridge.call.mockImplementation(async(op:string)=>op==="machine_answer"?answer:{task_id:"answer1",conditions:JSON.stringify({...answer,answer:{answer:"different"}})});
  render(<MachineAnswerPanel knowledgeId="k1"/>);const user=userEvent.setup();await user.type(screen.getByLabelText("实际问题"),"实际问题");await user.click(screen.getByRole("button",{name:"执行本地机器回答"}));
  expect(await screen.findByText(/持久化读回未确认/)).toBeInTheDocument();expect(screen.queryByLabelText("真实机器回答")).not.toBeInTheDocument();
 });
});

describe("machine identity and history regressions",()=>{
 beforeEach(()=>{bridge.call.mockReset();});
 it("rejects the wrong original question and blocks UNKNOWN inference retry",async()=>{
  bridge.call.mockResolvedValue({...answer,question:"错问题"});render(<MachineAnswerPanel knowledgeId="k1"/>);
  const user=userEvent.setup();await user.type(screen.getByLabelText("实际问题"),"实际问题");await user.click(screen.getByRole("button",{name:"执行本地机器回答"}));
  expect(await screen.findByText(/状态尚未确认。请读取历史核对/)).toBeInTheDocument();expect(screen.queryByLabelText("真实机器回答")).not.toBeInTheDocument();
  expect(bridge.call).toHaveBeenCalledTimes(1);expect(screen.queryByRole("button",{name:"执行本地机器回答"})).not.toBeInTheDocument();expect(screen.getByRole("button",{name:"重试同一回答请求"})).toBeDisabled();await user.click(screen.getByRole("button",{name:"重试同一回答请求"}));expect(bridge.call).toHaveBeenCalledTimes(1);
 });
 it("rejects wrong task knowledge with matching answer text",async()=>{
  bridge.call.mockImplementation(async(op:string)=>op==="machine_answer"?answer:task({...answer,knowledge_id:"other"}));
  render(<MachineAnswerPanel knowledgeId="k1"/>);const user=userEvent.setup();await user.type(screen.getByLabelText("实际问题"),"实际问题");await user.click(screen.getByRole("button",{name:"执行本地机器回答"}));
  expect(await screen.findByText(/状态尚未确认。请读取历史核对/)).toBeInTheDocument();expect(screen.queryByLabelText("真实机器回答")).not.toBeInTheDocument();
 });
 it("restores a saved answer from paged Core history without inference",async()=>{
  const receipt={...task(answer),principal:"machine",recorded_at:"2026-10-10",method_version:null,tool_version:null,failure:null};
  bridge.call.mockImplementation(async(op:string)=>op==="machine_tasks_list"?{items:[receipt],next_cursor:null}:op==="machine_task_get"?receipt:Promise.reject(new Error("unexpected write")));
  render(<MachineAnswerPanel knowledgeId="k1"/>);const user=userEvent.setup();await user.click(screen.getByRole("button",{name:"读取机器学习历史"}));
  await user.click(await savedTaskButton("answer1"));
  expect(await screen.findByLabelText("真实机器回答")).toHaveTextContent("实际机器回答");expect(bridge.call.mock.calls.every(([op])=>["machine_tasks_list","machine_task_get"].includes(op))).toBe(true);
 });
 it("late answer cannot contaminate another knowledge selection",async()=>{
  let resolve!:(value:unknown)=>void;bridge.call.mockImplementation(async(op:string)=>op==="machine_answer"?new Promise(done=>{resolve=done;}):task(answer));
  const ui=render(<MachineAnswerPanel knowledgeId="k1"/>);const user=userEvent.setup();await user.type(screen.getByLabelText("实际问题"),"实际问题");await user.click(screen.getByRole("button",{name:"执行本地机器回答"}));
  ui.rerender(<MachineAnswerPanel knowledgeId="k2"/>);resolve(answer);await waitFor(()=>expect(screen.getByLabelText("实际问题")).toHaveValue(""));expect(screen.queryByLabelText("真实机器回答")).not.toBeInTheDocument();
 });
});

describe("persisted correction and withdrawal history",()=>{
 beforeEach(()=>{bridge.call.mockReset();});
 const correction={schema:"archeaxis.machine-correction/v1",answer_id:"answer1",failed_task_id:"evaluation_answer1",correction_candidate_id:"correction1",corrects_knowledge_id:"k1",question:"实际问题",machine_answer:"实际机器回答",corrected_answer:"使用者纠正",error_note:"依据",reviewer:"human",status:"candidate",authority:"candidate"};
 const evaluation={...answer,correction};
 const savedRetest={...retestReceipt,prior:{conditions:evaluation}};
 const failed={...task(answer),task_id:"evaluation_answer1",conditions:JSON.stringify(evaluation),scope:"runtime.evaluation.failed",outcome:"failed"};
 it("presents a recorded correction without treating its storage outcome as independent model failure",async()=>{
  const row={...failed,principal:"machine",recorded_at:"2026-10-10",method_version:null,tool_version:null,failure:"依据"};
  bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>={})=>{
   if(op==="machine_tasks_list")return {items:[row,{...row,task_id:"actual_failure",scope:"runtime.answer"}],next_cursor:null};
   if(op==="machine_task_get")return payload.task_id==="evaluation_answer1"?row:task(answer);
   if(op==="knowledge_get")return {knowledge_id:"correction1",body:"使用者纠正",version:"review-v1",status:"candidate"};
   throw new Error("unexpected write");
  });
  render(<MachineAnswerPanel knowledgeId="k1"/>);const user=userEvent.setup();await user.click(screen.getByRole("button",{name:"读取机器学习历史"}));
  const history=await screen.findByRole("list",{name:"既有机器学习任务"});
  expect(history).toHaveTextContent("使用者纠正 · 已记录");expect(history).not.toHaveTextContent("评测失败");
  expect(history.querySelector('[data-task-id="actual_failure"]')).toHaveTextContent("回答 · 失败");
  await user.click(await savedTaskButton("evaluation_answer1"));
  expect(await screen.findByLabelText("真实机器回答")).toHaveTextContent("实际机器回答");
  expect(screen.getByText("纠正记录本身不证明原回答错误，请结合提交者与依据核验。")).toBeInTheDocument();
  expect(screen.getByText("纠正记录提交者").parentElement).toHaveTextContent("human");
  expect(screen.getByText("提交的纠正依据").parentElement).toHaveTextContent("依据");
  expect(bridge.call.mock.calls.every(([op])=>["machine_tasks_list","machine_task_get","knowledge_get"].includes(op))).toBe(true);
 });
 it("recovers the whole withdrawn chain with original answer and retest visible",async()=>{
  const row={...task(savedRetest,"runtime.retest"),principal:"machine",recorded_at:"2026-10-10",method_version:null,tool_version:null,failure:null};
  bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>={})=>{
   if(op==="machine_tasks_list")return {items:[row],next_cursor:null};
   if(op==="knowledge_get")return {knowledge_id:"correction1",body:"使用者纠正",version:"review-v3",status:"deprecated"};
   if(op==="machine_task_get")return payload.task_id==="retest1"?row:payload.task_id==="evaluation_answer1"?failed:task(answer);
   throw new Error("unexpected write");
  });
  render(<MachineAnswerPanel knowledgeId="k1"/>);const user=userEvent.setup();await user.click(screen.getByRole("button",{name:"读取机器学习历史"}));await screen.findAllByRole("button",{name:"查看这次任务"});await user.click(document.querySelector<HTMLButtonElement>('li[data-task-id="retest1"] button')!);
  expect(await screen.findByRole("region",{name:"独立复测结果对照"})).toHaveTextContent("纠正后复测回答");expect(screen.getByLabelText("真实机器回答")).toHaveTextContent("实际机器回答");
  expect(screen.queryByRole("button",{name:"以已接受纠正知识运行独立复测"})).not.toBeInTheDocument();expect(bridge.call.mock.calls.some(([op])=>op==="machine_retest")).toBe(false);
 });
 it("requested accepted action cannot be confirmed by a candidate readback",async()=>{
  let reviewed=false;
  const row={...failed,principal:"machine",recorded_at:"2026-10-10",method_version:null,tool_version:null,failure:"依据"};
  bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>={})=>{
   if(op==="machine_tasks_list")return {items:[row],next_cursor:null};
   if(op==="machine_task_get")return payload.task_id==="evaluation_answer1"?row:task(answer);
   if(op==="knowledge_get")return {knowledge_id:"correction1",body:"使用者纠正",version:reviewed?"v2":"v1",status:"candidate"};
   if(op==="knowledge_review"){reviewed=true;return {knowledge_id:"correction1",version:"v2"};}
   throw new Error("unexpected operation");
  });
  render(<MachineAnswerPanel knowledgeId="k1"/>);const user=userEvent.setup();await user.click(screen.getByRole("button",{name:"读取机器学习历史"}));await screen.findAllByRole("button",{name:"查看这次任务"});await user.click(document.querySelector<HTMLButtonElement>('li[data-task-id="evaluation_answer1"] button')!);
  await user.type(await screen.findByLabelText("审核者"),"human");await user.type(screen.getByLabelText("审核依据"),"fixed evidence");await user.click(screen.getByRole("button",{name:"接受纠正知识"}));
  expect(await screen.findByText(/纠正审核未完成/)).toBeInTheDocument();expect(screen.queryByRole("button",{name:"以已接受纠正知识运行独立复测"})).not.toBeInTheDocument();
 });
});

async function savedTaskButton(taskId: string) {
  return waitFor(() => {
    const rows = [...document.querySelectorAll('[aria-label="既有机器学习任务"] li[data-task-id]')]
      .filter(row => row.getAttribute("data-task-id") === taskId);
    expect(rows).toHaveLength(1);
    return within(rows[0] as HTMLElement).getByRole("button", { name: "查看这次任务" });
  });
}
