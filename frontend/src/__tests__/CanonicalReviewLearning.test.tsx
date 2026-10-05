import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CanonicalKnowledgeSpace } from "../spaces/CanonicalKnowledgeSpace";
import { CanonicalLearningSpace } from "../spaces/CanonicalLearningSpace";
const bridge = vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
describe("finite knowledge and learning commands",()=>{
 beforeEach(()=>bridge.call.mockReset());
 it("shows evidence before a user's version-checked review and preserves note on conflict",async()=>{
  bridge.call.mockImplementation(async(op:string)=>{
   if(op==="search") return {items:[{knowledge_id:"k1",head:"候选正文",status:"candidate",active:false}],transforms:[]};
   if(op==="knowledge_get") return {knowledge_id:"k1",body:"候选正文",version:"sha-version",status:"candidate",title:"候选"};
   if(op==="knowledge_qualification") return {local_execution_pass:false};
   if(op==="knowledge_review") throw new Error("conflict");
  });
  render(<CanonicalKnowledgeSpace/>);const user=userEvent.setup();
  await user.click(screen.getByRole("button",{name:"搜索"}));await user.click(await screen.findByRole("button",{name:"候选正文"}));
  expect(await screen.findByText(/local_execution_pass/)).toHaveTextContent("false");
  expect(screen.getByRole("button",{name:"接受当前候选"})).toBeDisabled();
  await user.type(screen.getByLabelText("审核者"),"测试使用者");await user.type(screen.getByLabelText("审核备注"),"保留判断依据");
  await user.click(screen.getByRole("button",{name:"接受当前候选"}));
  await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("knowledge_review",{id:"k1",body:{action:"accepted",reviewer:"测试使用者",note:"保留判断依据",expected_version:"sha-version"}}));
  expect(await screen.findByRole("status")).toHaveTextContent("审核未完成");expect(screen.getByLabelText("审核备注")).toHaveValue("保留判断依据");
 });
 it("separates machine state and retries the same review event after unconfirmed response",async()=>{
  bridge.call.mockImplementation(async(op:string)=>{
   if(op==="learning_items") return {items:[{item_key:"a1",next_review:null}]};
   if(op==="learning_state") return {item_key:"a1",learner:{assessment:{assessment_id:"assess",question:"实际问题",knowledge_version:"kv"}},machine:{status:"not_recorded"}};
   if(op==="learning_history") return {events:[]};
   if(op==="learning_review") throw new Error("unconfirmed");
  });
  render(<CanonicalLearningSpace/>);const user=userEvent.setup();await user.click(await screen.findByRole("button",{name:"a1"}));
  expect(await screen.findByText(/not_recorded/)).toBeInTheDocument();await user.type(screen.getByLabelText("本次答案"),"本次实际答案");
  await user.click(screen.getByRole("button",{name:"记录复习结果"}));await screen.findByText(/提交未确认/);
  await user.click(screen.getByRole("button",{name:"记录复习结果"}));
  const writes=bridge.call.mock.calls.filter(([op])=>op==="learning_review");expect(writes).toHaveLength(2);expect(writes[0][1]).toEqual(writes[1][1]);
  expect(writes[0][1].body).toMatchObject({correct:false,rating:1,assessment_id:"assess",knowledge_version:"kv",answer:"本次实际答案"});
 });
});
