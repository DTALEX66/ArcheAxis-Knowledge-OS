import { act, fireEvent, render, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { CanonicalLearningSpace } from "../spaces/CanonicalLearningSpace";
import { CoreWorkingStateSession, type LearningDraft, type WorkingRead, type WorkingTransport } from "../presentation/coreWorkingState";
import { CoreWorkingStateProvider } from "../presentation/useCoreWorkingState";

const call=vi.hoisted(()=>vi.fn());
vi.mock("../api/core",()=>({coreCommand:call}));
const draft=(key:string):LearningDraft=>({item_key:key,assessment_id:`assessment_${key}`,knowledge_version:"v1",answer:`  raw ${key}\n第二行  `,rating:3,checked_correct:true,answer_revealed:true});
beforeEach(()=>{
  call.mockReset();call.mockImplementation(async(op:string,payload:any)=>{
    if(op==="learning_items")return {items:[{item_key:"a"},{item_key:"b"}]};
    if(op==="learning_state")return {item_key:payload.item_key,learner:{assessment:{assessment_id:`assessment_${payload.item_key}`,knowledge_version:"v1",question:`question ${payload.item_key}`,content:`content ${payload.item_key}`}},machine:{status:"not_recorded"}};
    if(op==="learning_history")return {events:[]};
    throw new Error(`Unexpected ${op}`);
  });
});
afterEach(()=>vi.restoreAllMocks());
function fixture(other=false){
  let server:WorkingRead={schema:"archeaxis.ui-working-state/v1",workspace_id:"a".repeat(32),restore_epoch:"initial",state_revision:0,state:{drafts:{},opened_documents:[],active_document:null,page_id:"12",pending_original:null,learning_drafts:{assessment_a:draft("a"),...(other?{assessment_b:draft("b")}: {})}},draft_digests:{},pending_document_id:null,recovery_candidates:null,recovery_requires_confirmation:false};
  const transport:WorkingTransport={read:async()=>structuredClone(server),write:async request=>{server={...server,state:structuredClone(request.state),state_revision:server.state_revision+1};return structuredClone(server);},clearSaved:vi.fn(),recover:vi.fn()};
  return {session:new CoreWorkingStateSession(transport),server:()=>server};
}
async function views(other=false){
  const f=fixture(other);await f.session.load();const owners=new Map<string,boolean>();
  const listener=(event:Event)=>{const {owner,dirty}=(event as CustomEvent).detail;owners.set(owner,dirty);};
  window.addEventListener("archeaxis-draft-dirty",listener);
  const view=render(<CoreWorkingStateProvider session={f.session}><section data-testid="review"><CanonicalLearningSpace initialItemKey="a"/></section><section data-testid="parked"><CanonicalLearningSpace initialItemKey="a"/></section>{other?<section data-testid="other"><CanonicalLearningSpace initialItemKey="b"/></section>:null}</CoreWorkingStateProvider>);
  const review=within(view.getByTestId("review")),parked=within(view.getByTestId("parked"));
  await waitFor(()=>expect(review.getByLabelText("本次答案")).toHaveValue(draft("a").answer));
  await waitFor(()=>expect(parked.getByLabelText("本次答案")).toHaveValue(draft("a").answer));
  return {...f,view,review,parked,owners,stop:()=>window.removeEventListener("archeaxis-draft-dirty",listener)};
}
it("releases every retained same-item controller after another view confirms the exact review",async()=>{
  const original=call.getMockImplementation()!;let resolve!:(value:unknown)=>void;
  call.mockImplementation((op,payload)=>op==="learning_review"?new Promise(done=>{resolve=done;}):original(op,payload));
  const f=await views();try{
    fireEvent.click(f.review.getByRole("button",{name:"记录复习结果"}));
    await waitFor(()=>expect(f.parked.getByLabelText("本次答案")).toBeDisabled());
    await act(async()=>resolve({next_review_days:1}));
    await f.review.findByText(/Core 已确认复习记录/);
    expect(f.server().state.pending_reviews).toBeUndefined();expect(f.server().state.learning_drafts).toBeUndefined();
    await waitFor(()=>expect(f.parked.getByLabelText("本次答案")).toBeEnabled());
    expect(f.parked.getByLabelText("本次答案")).toHaveValue("");
    await waitFor(()=>expect([...f.owners.values()]).toEqual([false,false]));
    fireEvent.change(f.parked.getByLabelText("本次答案"),{target:{value:"a fresh practice"}});
    expect(f.session.getSnapshot().state.learning_drafts?.assessment_a.answer).toBe("a fresh practice");
  }finally{f.stop();}
});
it("keeps unknown ACKs frozen and restores a newer shared raw draft without changing another item's answer",async()=>{
  const original=call.getMockImplementation()!;let attempts=0;
  call.mockImplementation(async(op,payload)=>{if(op==="learning_review"){if(++attempts===1)throw new Error("unknown ACK");return {next_review_days:1};}return original(op,payload);});
  const f=await views(true);try{
    const other=within(f.view.getByTestId("other"));await waitFor(()=>expect(other.getByLabelText("本次答案")).toHaveValue(draft("b").answer));
    fireEvent.click(f.review.getByRole("button",{name:"记录复习结果"}));await f.review.findByText(/复习提交未确认/);
    const frozen=structuredClone(f.session.getSnapshot().state.pending_reviews);
    expect(f.parked.getByLabelText("本次答案")).toBeDisabled();expect(other.getByLabelText("本次答案")).toBeEnabled();
    expect(f.session.getSnapshot().state.pending_reviews).toEqual(frozen);
    // A shared draft may change while a parked controller waits for its request's receipt.
    const newer={...draft("a"),answer:"  later raw answer\n  ",rating:null,checked_correct:null,answer_revealed:false};
    // Publish the newer snapshot only after Core confirms clearance, before the observer reopens.
    const finish=f.session.finishReview.bind(f.session);
    vi.spyOn(f.session,"finishReview").mockImplementation(async(entry,sent)=>{await finish(entry,sent);f.session.rememberLearningDraft(newer);});
    fireEvent.click(f.review.getByRole("button",{name:"记录复习结果"}));await f.review.findByText(/Core 已确认复习记录/);
    await waitFor(()=>expect(f.parked.getByLabelText("本次答案")).toBeEnabled());
    await waitFor(()=>expect(f.parked.getByLabelText("本次答案")).toHaveValue(newer.answer));
    expect(other.getByLabelText("本次答案")).toHaveValue(draft("b").answer);
    expect(f.session.getSnapshot().state.learning_drafts?.assessment_b).toEqual(draft("b"));
    const reviews=call.mock.calls.filter(([op])=>op==="learning_review");expect(reviews[1][1]).toEqual(reviews[0][1]);
    expect([...f.owners.values()].every(Boolean)).toBe(true);
  }finally{f.stop();}
});
it("does not release another item's frozen request when the same-item retained views reconcile",async()=>{
  const original=call.getMockImplementation()!;call.mockImplementation(async(op,payload)=>op==="learning_review"?{next_review_days:1}:original(op,payload));
  const f=await views(true);try{
    const other=within(f.view.getByTestId("other"));await other.findByLabelText("本次答案");
    const pending={item_key:"b",client_event_id:"frozen_b",origin_restore_epoch:"initial",body:{item_key:"b",client_event_id:"frozen_b",assessment_id:"assessment_b",knowledge_version:"v1",answer:draft("b").answer.trim(),rating:3,correct:true}};
    await act(async()=>f.session.freezeReview(pending));
    await waitFor(()=>expect(other.getByLabelText("本次答案")).toBeDisabled());
    fireEvent.click(f.review.getByRole("button",{name:"记录复习结果"}));await f.review.findByText(/Core 已确认复习记录/);
    await waitFor(()=>expect(f.parked.getByLabelText("本次答案")).toBeEnabled());
    expect(other.getByLabelText("本次答案")).toBeDisabled();
    expect(f.session.getSnapshot().state.pending_reviews).toEqual({frozen_b:pending});
    expect(f.session.getSnapshot().state.learning_drafts?.assessment_b).toEqual(draft("b"));
    expect([...f.owners.values()].every(Boolean)).toBe(true);
  }finally{f.stop();}
});
