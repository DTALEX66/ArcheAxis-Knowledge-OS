import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MachineAnswerPanel } from "../components/MachineAnswerPanel";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const answer={answer_id:"answer1",knowledge_id:"k1",question:"实际问题",answer:{answer:"实际机器回答",model:"local-model"},authority:"candidate"};
describe("SIMULATED machine candidate UI with Core bridge fixtures",()=>{
 beforeEach(()=>bridge.call.mockReset());
 it("reads a persisted answer and requires explicit human correction fields without accepting",async()=>{
  let candidateStatus="candidate",candidateVersion="correction-v1";
  bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>={})=>{
   if(op==="machine_answer")return answer;
   if(op==="machine_task_get" && payload.task_id==="retest1")return {task_id:"retest1",conditions:JSON.stringify({retest_of:"evaluation_answer1",knowledge_id:"correction1",answer:{answer:"纠正后复测回答"}}),model_version:"local-model",outcome:"unmeasured"};
   if(op==="machine_task_get")return {task_id:"answer1",conditions:JSON.stringify(answer),model_version:"local-model",outcome:"unmeasured"};
   if(op==="machine_correction")return {answer_id:"answer1",failed_task_id:"evaluation_answer1",correction_candidate_id:"correction1",status:"candidate",authority:"candidate",corrects_knowledge_id:"k1",question:"实际问题",machine_answer:"实际机器回答",corrected_answer:"使用者纠正",error_note:"具体错误依据",reviewer:"实际使用者"};
   if(op==="machine_retest")return {schema:"archeaxis.machine-retest/v1",retest_task_id:"retest1",answer_id:"retest1",retest_of:"evaluation_answer1",knowledge_id:"correction1",question:"实际问题",answer:{answer:"纠正后复测回答",model:"local-model"},authority:"candidate",prior:{},request:{},note:"human compares"};
   if(op==="knowledge_get")return {knowledge_id:"correction1",body:"使用者纠正",version:candidateVersion,status:candidateStatus};
   if(op==="knowledge_review"){candidateStatus=(payload.body as Record<string,unknown>).action as string;candidateVersion=candidateVersion==="correction-v1"?"correction-v2":"correction-v3";return {knowledge_id:"correction1",version:candidateVersion};}
   if (op === undefined) return undefined;
   throw new Error(`unexpected Core command: ${String(op)} ${JSON.stringify(payload)}`);
  });
  render(<MachineAnswerPanel knowledgeId="k1"/>);const user=userEvent.setup();await user.type(screen.getByLabelText("实际问题"),"实际问题");await user.click(screen.getByRole("button",{name:"执行本地机器回答"}));
  expect(await screen.findByLabelText("真实机器回答")).toHaveTextContent("实际机器回答");expect(screen.getByRole("button",{name:"记录使用者纠正候选"})).toBeDisabled();
  await user.type(screen.getByLabelText("正确答案"),"使用者纠正");await user.type(screen.getByLabelText("具体错误依据"),"具体错误依据");await user.type(screen.getByLabelText("纠正提交者"),"实际使用者");await user.click(screen.getByRole("button",{name:"记录使用者纠正候选"}));
  await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("machine_correction",{body:{answer_id:"answer1",knowledge_id:"k1",question:"实际问题",machine_answer:"实际机器回答",corrected_answer:"使用者纠正",error_note:"具体错误依据",reviewer:"实际使用者"}}));
  expect(await screen.findByText("candidate")).toBeInTheDocument();expect(screen.getByRole("region",{name:"纠正候选审核"})).toBeInTheDocument();
  expect(screen.getByText("Core 候选正文读回").parentElement).toHaveTextContent("使用者纠正");
  expect(screen.getByText("纠正候选修订").parentElement).toHaveTextContent("correction-v1");
  expect(bridge.call.mock.calls.some(([op])=>op==="knowledge_review")).toBe(false);
  expect(screen.queryByRole("button",{name:"以已接受纠正知识运行独立复测"})).not.toBeInTheDocument();
  await user.type(screen.getByLabelText("审核依据"),"已对照专业来源");await user.click(screen.getByRole("button",{name:"接受纠正知识"}));
  await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("knowledge_review",{id:"correction1",body:{action:"accepted",reviewer:"实际使用者",note:"已对照专业来源",expected_version:"correction-v1"}}));
  await user.click(await screen.findByRole("button",{name:"以已接受纠正知识运行独立复测"}));
  await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("machine_retest",{body:{retest_of:"evaluation_answer1",knowledge_id:"correction1",question:"实际问题",max_tokens:2048,timeout_s:120}}));
  expect(await screen.findByLabelText("独立复测机器回答")).toHaveTextContent("纠正后复测回答");
  expect(screen.getByRole("region",{name:"独立复测结果对照"})).toHaveTextContent("未测评；等待真人比较");
  await user.click(screen.getByRole("button",{name:"撤回已接受纠正（标记为弃用）"}));
  await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("knowledge_review",{id:"correction1",body:{action:"deprecated",reviewer:"实际使用者",note:"已对照专业来源",expected_version:"correction-v2"}}));
 });
 it("withholds an answer when the persistent task readback differs",async()=>{
  bridge.call.mockImplementation(async(op:string)=>op==="machine_answer"?answer:{task_id:"answer1",conditions:JSON.stringify({...answer,answer:{answer:"different"}})});
  render(<MachineAnswerPanel knowledgeId="k1"/>);const user=userEvent.setup();await user.type(screen.getByLabelText("实际问题"),"实际问题");await user.click(screen.getByRole("button",{name:"执行本地机器回答"}));
  expect(await screen.findByText(/持久化读回未确认/)).toBeInTheDocument();expect(screen.queryByLabelText("真实机器回答")).not.toBeInTheDocument();
 });
});
