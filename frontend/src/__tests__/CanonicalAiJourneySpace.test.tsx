import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CanonicalAiJourneySpace } from "../spaces/CanonicalAiJourneySpace";
import type { ContextConsumptionDto, ContextGrantDto, DocumentDto } from "../api/generated/core-contract";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
vi.mock("../components/MachineEvaluationPanel",()=>({MachineEvaluationPanel:()=>null}));
vi.mock("../components/MachineAnswerPanel",()=>({MachineAnswerPanel:(props:{knowledgeId:string;contextGrant?:ContextConsumptionDto;retestContextGrant?:ContextConsumptionDto;onTask?:(id:string)=>void;onCandidate?:(id:string)=>void})=><section aria-label="scoped panel"><span>原知识 {props.knowledgeId}</span><span>回答授权 {props.contextGrant?.document_id??"无"}</span><span>复测授权 {props.retestContextGrant?.document_id??"无"}</span><button onClick={()=>props.onCandidate?.("correction1")}>模拟实际候选读回</button><button onClick={()=>props.onTask?.("task1")}>模拟实际任务读回</button><button>读取既有历史</button></section>}));
const hash="a".repeat(64);
function document(id:string,knowledge="k1",changes:Partial<ContextGrantDto>={}):DocumentDto{return {document_id:id,version:2,title:id,content_sha256:hash,source_id:null,source_revision:null,text_projection:"正文",blocks:[],editor_json:{type:"doc",content:[],attrs:{ownerUnknown:{retained:true},archeaxis_context_grant:{schema:"archeaxis.context-grant/v1",purpose:"项目问题",consumer:"local-machine",operations:["answer","retest"],knowledge_id:knowledge,provenance:[],authorization_basis:"真人明确允许",expires_at:null,state:"granted",...changes}}}};}
const snap=(id:string):ContextConsumptionDto=>({document_id:id,version:2,content_sha256:hash,purpose:"项目问题"});
function fixture(docs:DocumentDto[]){bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>={})=>{
 if(op==="machine_contexts_list")return {items:docs.map(d=>({document_id:d.document_id,version:d.version,title:d.title,content_sha256:d.content_sha256})),next_cursor:null};
 if(op==="document_get")return docs.find(d=>d.document_id===payload.document_id);
 throw new Error("Unexpected inference/write "+op);
});}
describe("SIMULATED canonical AI journey scoped grants",()=>{
beforeEach(()=>{bridge.call.mockReset();});
 it("uses an exact onUse snapshot and forwards real callback identities",async()=>{
  fixture([document("grant1")]);const onTask=vi.fn(),onCandidate=vi.fn();render(<CanonicalAiJourneySpace initialConsumption={snap("grant1")} onTask={onTask} onCandidate={onCandidate}/>);
  expect(await screen.findByText("回答授权 grant1")).toBeInTheDocument();const user=userEvent.setup();await user.click(screen.getByRole("button",{name:"模拟实际任务读回"}));await user.click(screen.getByRole("button",{name:"模拟实际候选读回"}));
  expect(onTask).toHaveBeenCalledWith("task1");expect(onCandidate).toHaveBeenCalledWith("correction1");expect(bridge.call.mock.calls.every(([op])=>["machine_contexts_list","document_get"].includes(op))).toBe(true);
 });
 it("keeps original and actual correction authorizations separate",async()=>{
  fixture([document("original"),document("corrected","correction1")]);render(<CanonicalAiJourneySpace/>);const user=userEvent.setup();
  await user.click(await screen.findByRole("button",{name:"选择原知识授权 original"}));expect(await screen.findByText("回答授权 original")).toBeInTheDocument();
  await user.click(screen.getByRole("button",{name:"模拟实际候选读回"}));await user.click(screen.getByRole("button",{name:"选择纠正候选授权 corrected"}));expect(await screen.findByText("复测授权 corrected")).toBeInTheDocument();expect(screen.getByText("回答授权 original")).toBeInTheDocument();
 });
 it("rejects a stale consumption snapshot without guessing another version",async()=>{
  fixture([document("grant1")]);render(<CanonicalAiJourneySpace initialConsumption={{...snap("grant1"),version:1}}/>);
  expect(await screen.findByRole("alert")).toBeInTheDocument();expect(screen.queryByRole("region",{name:"scoped panel"})).not.toBeInTheDocument();
 });
 it("revoked grants leave history readable without new inference authorization",async()=>{
  fixture([document("revoked","k1",{state:"revoked"})]);render(<CanonicalAiJourneySpace initialConsumption={snap("revoked")}/>);
  expect(await screen.findByText("回答授权 无")).toBeInTheDocument();expect(screen.getByRole("button",{name:"读取既有历史"})).toBeEnabled();expect(bridge.call.mock.calls.some(([op])=>op==="machine_answer")).toBe(false);
 });
 it("expired grant is not a fresh consumption permission",async()=>{
  fixture([document("expired","k1",{expires_at:1})]);render(<CanonicalAiJourneySpace initialConsumption={snap("expired")}/>);
  expect(await screen.findByText("回答授权 无")).toBeInTheDocument();expect(screen.getByRole("button",{name:"读取既有历史"})).toBeEnabled();
 });
 it("wrong knowledge grant cannot authorize the correction retest",async()=>{
  fixture([document("original"),document("wrong","other")]);render(<CanonicalAiJourneySpace initialConsumption={snap("original")}/>);await screen.findByText("回答授权 original");const user=userEvent.setup();
  await user.click(screen.getByRole("button",{name:"模拟实际候选读回"}));await user.click(screen.getByRole("button",{name:"选择纠正候选授权 wrong"}));
  await waitFor(()=>expect(screen.getByRole("region",{name:"纠正候选授权快照"})).toHaveTextContent("wrong"));expect(screen.getByText("复测授权 无")).toBeInTheDocument();
 });
 it("preserves current selection when the scoped panel owns an unfinished draft",async()=>{
  fixture([document("first"),document("second","k2")]);render(<CanonicalAiJourneySpace initialConsumption={snap("first")}/>);await screen.findByText("回答授权 first");
  act(()=>window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner:"panel",dirty:true}})));const user=userEvent.setup();await user.click(screen.getByRole("button",{name:"选择原知识授权 second"}));
  expect(screen.getByText("原知识 k1")).toBeInTheDocument();expect(bridge.call.mock.calls.some(([op,p])=>op==="document_get" && p.document_id==="second")).toBe(false);
 });
 it("late original read cannot overwrite the newer picked authorization",async()=>{
  let resolve!:(v:DocumentDto)=>void;fixture([document("first"),document("second","k2")]);const previous=bridge.call.getMockImplementation()!;
  bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>={})=>op==="document_get"&&payload.document_id==="first"?new Promise(done=>{resolve=done;}):previous(op,payload));
  const ui=render(<CanonicalAiJourneySpace initialConsumption={snap("first")}/>);await waitFor(()=>expect(resolve).toBeTypeOf("function"));
  ui.rerender(<CanonicalAiJourneySpace initialConsumption={snap("second")}/>);expect(await screen.findByText("原知识 k2")).toBeInTheDocument();act(()=>resolve(document("first")));await waitFor(()=>expect(screen.getByText("原知识 k2")).toBeInTheDocument());
 });
 it("unknown metadata fails closed and does not strip the saved envelope",async()=>{
  const doc=document("future");(doc.editor_json as {attrs:{archeaxis_context_grant:Record<string,unknown>}}).attrs.archeaxis_context_grant.future=true;
  fixture([doc]);render(<CanonicalAiJourneySpace initialConsumption={snap("future")}/>);expect(await screen.findByRole("alert")).toBeInTheDocument();expect(screen.queryByRole("region",{name:"scoped panel"})).not.toBeInTheDocument();
 });
});
