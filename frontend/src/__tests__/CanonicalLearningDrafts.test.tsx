import {findLearningItemButton,getLearningItemButton} from "../test/learningQueue";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { CanonicalLearningSpace } from "../spaces/CanonicalLearningSpace";
import { CoreWorkingStateSession, type WorkingRead, type WorkingTransport } from "../presentation/coreWorkingState";
import { CoreWorkingStateProvider } from "../presentation/useCoreWorkingState";

const call = vi.hoisted(() => vi.fn());
vi.mock("../api/core", () => ({ coreCommand: call }));
const assessment = (key:string, version="v1") => ({ assessment_id:`assessment_${key}_${version}`, question:`question ${key}`, content:`content ${key}`, knowledge_version:version });
afterEach(()=>vi.restoreAllMocks());
beforeEach(() => {
  call.mockReset();
  call.mockImplementation(async (op:string, payload:any) => {
    if(op==="learning_items") return {items:[{item_key:"a"},{item_key:"b"}]};
    if(op==="learning_state") return {item_key:payload.item_key,learner:{assessment:assessment(payload.item_key)},machine:{status:"not_recorded"}};
    if(op==="learning_history") return {events:[]};
    throw new Error(`Unexpected ${op}`);
  });
});
function fixture() {
  let server:WorkingRead={schema:"archeaxis.ui-working-state/v1",workspace_id:"a".repeat(32),restore_epoch:"initial",state_revision:0,state:{drafts:{},opened_documents:[],active_document:null,page_id:"06",pending_original:null},draft_digests:{},pending_document_id:null,recovery_candidates:null,recovery_requires_confirmation:false};
  const transport:WorkingTransport={read:async()=>structuredClone(server),write:vi.fn(async request=>{server={...server,state:structuredClone(request.state),state_revision:server.state_revision+1};return structuredClone(server);}),clearSaved:vi.fn(),recover:vi.fn()};
  return {transport,session:new CoreWorkingStateSession(transport),server:()=>server};
}
it("preserves independent unsubmitted answers and checks when switching a -> b -> a",async()=>{
  const f=fixture();await f.session.load();
  render(<CoreWorkingStateProvider session={f.session}><CanonicalLearningSpace/></CoreWorkingStateProvider>);
  const user=userEvent.setup();await user.click(await findLearningItemButton("a"));
  await user.type(await screen.findByLabelText("本次答案"),"  answer A\n第二行  ");
  await user.click(screen.getByRole("button",{name:"查看答案与核对内容"}));
  await user.click(screen.getByLabelText("回答正确"));await user.selectOptions(screen.getByLabelText("学习者自评"),"3");
  await user.click(getLearningItemButton("b"));
  await user.type(await screen.findByLabelText("本次答案"),"answer B");
  await user.click(getLearningItemButton("a"));
  await waitFor(()=>expect(screen.getByLabelText("本次答案")).toHaveValue("  answer A\n第二行  "));
  expect(screen.getByLabelText("回答正确")).toBeChecked();expect(screen.getByLabelText("学习者自评")).toHaveValue("3");
  await user.click(getLearningItemButton("b"));await waitFor(()=>expect(screen.getByLabelText("本次答案")).toHaveValue("answer B"));
  expect(call.mock.calls.some(([op])=>op==="learning_review")).toBe(false);
});
it("reopens an unsubmitted answer from a new Core working-state session without creating a review event",async()=>{
  const f=fixture();await f.session.load();const first=render(<CoreWorkingStateProvider session={f.session}><CanonicalLearningSpace/></CoreWorkingStateProvider>);
  const user=userEvent.setup();await user.click(await findLearningItemButton("a"));await user.type(await screen.findByLabelText("本次答案"),"尚未提交的答案");
  await act(async()=>{await f.session.flush();});first.unmount();
  const reopened=new CoreWorkingStateSession(f.transport);await reopened.load();render(<CoreWorkingStateProvider session={reopened}><CanonicalLearningSpace initialItemKey="a"/></CoreWorkingStateProvider>);
  await waitFor(()=>expect(screen.getByLabelText("本次答案")).toHaveValue("尚未提交的答案"));
  expect(screen.getByLabelText("本次答案")).not.toBeDisabled();expect(f.server().state.pending_reviews).toBeUndefined();
  expect(call.mock.calls.some(([op])=>op==="learning_review")).toBe(false);
});
it("retains an old assessment answer separately when the item's current assessment changes",async()=>{
  const f=fixture();await f.session.load();render(<CoreWorkingStateProvider session={f.session}><CanonicalLearningSpace/></CoreWorkingStateProvider>);
  const user=userEvent.setup();await user.click(await findLearningItemButton("a"));await user.type(await screen.findByLabelText("本次答案"),"original revision answer");
  await user.click(getLearningItemButton("b"));await screen.findByText("question b");
  const original=call.getMockImplementation()!;call.mockImplementation(async(op,payload)=>op==="learning_state"&&payload.item_key==="a"?{item_key:"a",learner:{assessment:assessment("a","v2")},machine:{status:"not_recorded"}}:original(op,payload));
  await user.click(getLearningItemButton("a"));await waitFor(()=>expect(screen.getByLabelText("本次答案")).toHaveValue(""));
  await user.type(screen.getByLabelText("本次答案"),"new revision answer");
  expect(f.session.getSnapshot().state.learning_drafts?.assessment_a_v1.answer).toBe("original revision answer");
  expect(f.session.getSnapshot().state.learning_drafts?.assessment_a_v2.answer).toBe("new revision answer");
  expect(screen.getByLabelText("保留的学习答案 assessment_a_v1")).toHaveValue("original revision answer");
  expect(call.mock.calls.some(([op])=>op==="learning_review")).toBe(false);
});
it("ignores a delayed question readback after another question has been edited",async()=>{
  const f=fixture();await f.session.load();let release!:(value:unknown)=>void;
  const original=call.getMockImplementation()!;call.mockImplementation(async(op,payload)=>op==="learning_state"&&payload.item_key==="a"?new Promise(resolve=>{release=resolve;}):original(op,payload));
  render(<CoreWorkingStateProvider session={f.session}><CanonicalLearningSpace/></CoreWorkingStateProvider>);
  const user=userEvent.setup();await user.click(await findLearningItemButton("a"));await user.click(getLearningItemButton("b"));
  await user.type(await screen.findByLabelText("本次答案"),"belongs to B");
  await act(async()=>release({item_key:"a",learner:{assessment:assessment("a")},machine:{status:"not_recorded"}}));
  expect(screen.getByText("question b")).toBeInTheDocument();expect(screen.getByLabelText("本次答案")).toHaveValue("belongs to B");
  expect(Object.keys(f.session.getSnapshot().state.learning_drafts??{})).toEqual(["assessment_b_v1"]);
});
it("keeps both drafts on an uncertain review and clears only the exactly submitted draft after confirmation",async()=>{
  const f=fixture();await f.session.load();let attempts=0;
  const original=call.getMockImplementation()!;call.mockImplementation(async(op,payload)=>{if(op==="learning_review"){if(++attempts===1)throw new Error("lost receipt");return {next_review_days:1};}return original(op,payload);});
  render(<CoreWorkingStateProvider session={f.session}><CanonicalLearningSpace/></CoreWorkingStateProvider>);
  const user=userEvent.setup();await user.click(await findLearningItemButton("b"));await user.type(await screen.findByLabelText("本次答案"),"answer B");
  await user.click(getLearningItemButton("a"));await user.type(await screen.findByLabelText("本次答案"),"  answer A  ");
  await user.click(screen.getByRole("button",{name:"查看答案与核对内容"}));await user.click(screen.getByLabelText("回答正确"));await user.selectOptions(screen.getByLabelText("学习者自评"),"3");
  await user.click(screen.getByRole("button",{name:"记录复习结果"}));await screen.findByText(/复习提交未确认/);
  const frozen=structuredClone(f.session.getSnapshot().state.pending_reviews);
  fireEvent.change(screen.getByLabelText("本次答案"),{target:{value:"must not replace frozen answer"}});
  expect(f.session.getSnapshot().state.pending_reviews).toEqual(frozen);expect(screen.getByLabelText("本次答案")).toHaveValue("  answer A  ");
  expect(Object.keys(f.session.getSnapshot().state.learning_drafts??{})).toHaveLength(2);
  await user.click(screen.getByRole("button",{name:"记录复习结果"}));await screen.findByText(/复习记录已保存/);
  const reviews=call.mock.calls.filter(([op])=>op==="learning_review");expect(reviews[0][1]).toEqual(reviews[1][1]);
  expect(f.session.getSnapshot().state.pending_reviews).toBeUndefined();expect(Object.keys(f.session.getSnapshot().state.learning_drafts??{})).toEqual(["assessment_b_v1"]);
  expect(f.session.getSnapshot().state.learning_drafts?.assessment_b_v1.answer).toBe("answer B");
});
it("opens the pinned learning draft only after the user preserves a restore candidate",async()=>{
  const f=fixture();const candidate={...f.server().state,learning_drafts:{assessment_a_v1:{item_key:"a",assessment_id:"assessment_a_v1",knowledge_version:"v1",answer:"restored answer",checked_correct:null,rating:null,answer_revealed:false}}};
  Object.assign(f.server(),{restore_epoch:"b".repeat(32),recovery_requires_confirmation:true,recovery_candidates:candidate});
  f.transport.recover=vi.fn(async()=>{Object.assign(f.server(),{state:structuredClone(candidate),state_revision:1,recovery_candidates:null,recovery_requires_confirmation:false});return structuredClone(f.server());});
  await f.session.load();render(<CoreWorkingStateProvider session={f.session}><CanonicalLearningSpace initialItemKey="a"/></CoreWorkingStateProvider>);
  expect(screen.queryByLabelText("本次答案")).not.toBeInTheDocument();
  await act(async()=>f.session.recover("preserve"));
  await waitFor(()=>expect(screen.getByLabelText("本次答案")).toHaveValue("restored answer"));
  expect(call.mock.calls.some(([op])=>op==="learning_review")).toBe(false);
});
it("discards only an explicitly confirmed draft and resets the current answer after Core ACK",async()=>{
  const f=fixture();await f.session.load();render(<CoreWorkingStateProvider session={f.session}><CanonicalLearningSpace/></CoreWorkingStateProvider>);
  const user=userEvent.setup();await user.click(await findLearningItemButton("a"));await user.type(await screen.findByLabelText("本次答案"),"discard only on request");
  await user.click(screen.getByLabelText("保留的学习答案 assessment_a_v1").closest("details")!.querySelector("summary")!);const confirm=vi.spyOn(window,"confirm").mockReturnValue(false);
  await user.click(screen.getByRole("button",{name:"丢弃草稿 a"}));expect(f.session.getSnapshot().state.learning_drafts?.assessment_a_v1.answer).toBe("discard only on request");
  confirm.mockReturnValue(true);await user.click(screen.getByRole("button",{name:"丢弃草稿 a"}));await screen.findByText("已丢弃这份学习草稿。");
  expect(f.session.getSnapshot().state.learning_drafts).toBeUndefined();expect(screen.getByLabelText("本次答案")).toHaveValue("");
  expect(call.mock.calls.some(([op])=>op==="learning_review")).toBe(false);
});
it("refuses an oversized review journal before freezing input and permits freeing another draft",async()=>{
  const f=fixture();const drafts=Object.fromEntries(Array.from({length:15},(_,i)=>{const key=i===0?"a":`item${i}`;const id=i===0?"assessment_a_v1":`assessment_${i}`;return [id,{item_key:key,assessment_id:id,knowledge_version:"v1",answer:"x".repeat(65_536),checked_correct:true,rating:3,answer_revealed:true}];}));
  f.server().state.learning_drafts=drafts;await f.session.load();
  render(<CoreWorkingStateProvider session={f.session}><CanonicalLearningSpace initialItemKey="a"/></CoreWorkingStateProvider>);
  await screen.findByLabelText("本次答案");const user=userEvent.setup();await user.click(screen.getByRole("button",{name:"记录复习结果"}));await screen.findByText(/复习请求保全将超过 1 MiB/);
  expect(screen.getByLabelText("本次答案")).toBeEnabled();expect(f.session.getSnapshot().status).toBe("ready");expect(f.session.getSnapshot().state.pending_reviews).toBeUndefined();expect(f.transport.write).not.toHaveBeenCalled();
  expect(call.mock.calls.some(([op])=>op==="learning_review")).toBe(false);
  vi.spyOn(window,"confirm").mockReturnValue(true);await user.click(screen.getByLabelText("保留的学习答案 assessment_1").closest("details")!.querySelector("summary")!);await user.click(screen.getByRole("button",{name:"丢弃草稿 item1"}));await screen.findByText("已丢弃这份学习草稿。");
  expect(Object.keys(f.session.getSnapshot().state.learning_drafts??{})).toHaveLength(14);expect(f.session.getSnapshot().status).toBe("ready");
});
