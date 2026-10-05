import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MachineAnswerPanel } from "../components/MachineAnswerPanel";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const answer={answer_id:"answer1",knowledge_id:"k1",question:"实际问题",answer:{answer:"实际机器回答",model:"local-model"},authority:"candidate"};
describe("real machine candidate boundary",()=>{
 beforeEach(()=>bridge.call.mockReset());
 it("reads a persisted answer and requires explicit human correction fields without accepting",async()=>{
  bridge.call.mockImplementation(async(op:string)=>op==="machine_answer"?answer:op==="machine_task_get"?{task_id:"answer1",conditions:JSON.stringify(answer),model_version:"local-model",outcome:"unmeasured"}:{answer_id:"answer1",correction_candidate_id:"correction1",status:"candidate"});
  render(<MachineAnswerPanel knowledgeId="k1"/>);const user=userEvent.setup();await user.type(screen.getByLabelText("实际问题"),"实际问题");await user.click(screen.getByRole("button",{name:"执行本地机器回答"}));
  expect(await screen.findByLabelText("真实机器回答")).toHaveTextContent("实际机器回答");expect(screen.getByRole("button",{name:"记录使用者纠正候选"})).toBeDisabled();
  await user.type(screen.getByLabelText("正确答案"),"使用者纠正");await user.type(screen.getByLabelText("具体错误"),"具体错误依据");await user.type(screen.getByLabelText("纠正审核者"),"实际使用者");await user.click(screen.getByRole("button",{name:"记录使用者纠正候选"}));
  await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("machine_correction",{body:{answer_id:"answer1",knowledge_id:"k1",question:"实际问题",machine_answer:"实际机器回答",corrected_answer:"使用者纠正",error_note:"具体错误依据",reviewer:"实际使用者"}}));
  expect(bridge.call.mock.calls.some(([op])=>op==="knowledge_review")).toBe(false);
 });
 it("withholds an answer when the persistent task readback differs",async()=>{
  bridge.call.mockImplementation(async(op:string)=>op==="machine_answer"?answer:{task_id:"answer1",conditions:JSON.stringify({...answer,answer:{answer:"different"}})});
  render(<MachineAnswerPanel knowledgeId="k1"/>);const user=userEvent.setup();await user.type(screen.getByLabelText("实际问题"),"实际问题");await user.click(screen.getByRole("button",{name:"执行本地机器回答"}));
  expect(await screen.findByText(/持久化读回未确认/)).toBeInTheDocument();expect(screen.queryByLabelText("真实机器回答")).not.toBeInTheDocument();
 });
});
