import {beforeEach,it,expect,vi} from "vitest";
import {render,screen,fireEvent,waitFor,within} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {CanonicalLearningSpace} from "../spaces/CanonicalLearningSpace";
import {DiagnosticConsole} from "../components/DiagnosticConsole";
import {resetDiagnostics} from "../presentation/diagnostics";
const call=vi.hoisted(()=>vi.fn());
vi.mock("../api/core",()=>({coreCommand:call}));
const key="course:course-0123456789abcdef:artifact:lesson-0123456789abcdef";
const revision="knowledge-0123456789abcdef";
const assessment={assessment_id:"assessment-0123456789abcdef",knowledge_id:revision,knowledge_version:revision,question_version:"question-version-exact",source_id:"source-exact",anchor_id:"anchor-exact",question:"请解释来源证据",content:"尚未揭示的答案"};
beforeEach(()=>{resetDiagnostics();call.mockReset();call.mockImplementation(async(op:string,payload:Record<string,unknown>={})=>{
 if(op==="learning_items")return {items:[{item_key:key,display_title:"来源证据练习",next_review:"2026-10-18T21:15:49.961000+00:00"}]};
 if(op==="learning_state")return {item_key:payload.item_key,learner:{assessment},machine:{status:"not_recorded"}};
 if(op==="learning_history")return {item_key:payload.item_key,events:[]};
 if(op==="learning_review")return {item_key:key,next_review:"2026-10-20T08:00:00Z"};
 throw new Error(`Unexpected ${op}`);
});});
it("SYNTHETIC manual exact-key locating is opt-in and sends the unchanged key after explicit expansion",async()=>{
 render(<CanonicalLearningSpace/>);const user=userEvent.setup();
 const input=screen.getByLabelText("学习项目键");const locator=input.closest("details");
 expect(locator).not.toBeNull();expect(locator).not.toHaveAttribute("open");
 const summary=within(locator!).getByText("按学习项目键定位");await user.click(summary);
 expect(locator).toHaveAttribute("open");
 fireEvent.change(input,{target:{value:key}});fireEvent.submit(input.closest("form")!);
 await screen.findByLabelText("本次答案");
 expect(call).toHaveBeenCalledWith("learning_state",{item_key:key});expect(call).toHaveBeenCalledWith("learning_history",{item_key:key});
 expect(call.mock.calls.some(([op])=>op==="learning_review")).toBe(false);
});
it("SYNTHETIC selected learning object uses its queue title without printing version identity or revealing the answer",async()=>{
 render(<CanonicalLearningSpace initialItemKey={key}/>);await screen.findByLabelText("本次答案");
 expect(screen.getByLabelText("当前学习项目")).toHaveTextContent("来源证据练习");
 expect(screen.queryByText(`知识修订：${revision}`)).not.toBeInTheDocument();
 expect(screen.queryByText("尚未揭示的答案")).not.toBeInTheDocument();
 expect(screen.getByLabelText("学习项目键")).toHaveValue(key);
});
it("SYNTHETIC missing display title is explicitly unverified and never replaced by the opaque key or the hidden answer",async()=>{
 const original=call.getMockImplementation()!;call.mockImplementation((op,payload)=>op==="learning_items"?Promise.resolve({items:[{item_key:key}]}):original(op,payload));
 render(<CanonicalLearningSpace initialItemKey={key}/>);await screen.findByLabelText("本次答案");
 expect(screen.getByLabelText("当前学习项目")).toHaveTextContent("学习项目（标题尚未核对）");
 expect(screen.getByLabelText("当前学习项目")).not.toHaveTextContent(key);
 expect(screen.queryByText("尚未揭示的答案")).not.toBeInTheDocument();
});
it("SYNTHETIC the existing diagnostic channel preserves all exact assessment identity fields without opening the answer",async()=>{
 render(<><CanonicalLearningSpace initialItemKey={key}/><DiagnosticConsole/></>);await screen.findByLabelText("本次答案");
 fireEvent.click(screen.getByRole("button",{name:"查看原始回执（诊断）：学习项目与题目版本"}));
 const payload=JSON.parse(screen.getByLabelText("诊断控制台").querySelector("pre")!.textContent!);
 expect(payload).toEqual({item_key:key,assessment_id:assessment.assessment_id,knowledge_id:revision,knowledge_version:revision,question_version:assessment.question_version,source_id:assessment.source_id,anchor_id:assessment.anchor_id});
 expect(screen.queryByText("尚未揭示的答案")).not.toBeInTheDocument();
});
it("SYNTHETIC presentation changes keep the submitted item and frozen versions exact",async()=>{
 render(<CanonicalLearningSpace initialItemKey={key}/>);fireEvent.change(await screen.findByLabelText("本次答案"),{target:{value:"独立回答"}});
 fireEvent.click(screen.getByRole("button",{name:"查看答案与核对内容"}));fireEvent.click(screen.getByLabelText("回答正确"));fireEvent.change(screen.getByLabelText("学习者自评"),{target:{value:"3"}});fireEvent.click(screen.getByRole("button",{name:"记录复习结果"}));
 await waitFor(()=>expect(call.mock.calls.filter(([op])=>op==="learning_review")).toHaveLength(1));
 expect(call.mock.calls.find(([op])=>op==="learning_review")?.[1]).toMatchObject({body:{item_key:key,assessment_id:assessment.assessment_id,knowledge_version:revision,question_version:assessment.question_version,correct:true,rating:3,answer:"独立回答"}});
 await screen.findByText(/Core 已确认复习记录/);
});
it("SYNTHETIC entering an answer does not put the opaque item and revision back into the collapsed draft summary",async()=>{
 render(<CanonicalLearningSpace initialItemKey={key}/>);fireEvent.change(await screen.findByLabelText("本次答案"),{target:{value:"保留的独立答案"}});
 const drafts=screen.getByLabelText("未提交学习草稿");const summary=drafts.querySelector("summary")!;
 expect(summary).toHaveTextContent("来源证据练习");expect(summary).not.toHaveTextContent(key);expect(summary).not.toHaveTextContent(revision);
 expect(summary.closest("details")).not.toHaveAttribute("open");fireEvent.click(summary);
 expect(drafts).toHaveTextContent(key);expect(drafts).toHaveTextContent(revision);
 expect(screen.getByLabelText(`保留的学习答案 ${assessment.assessment_id}`)).toHaveValue("保留的独立答案");
 expect(screen.getByLabelText("本次答案")).toHaveValue("保留的独立答案");
 expect(call.mock.calls.some(([op])=>op==="learning_review")).toBe(false);
});
