import {useState} from "react";
import {createHash,webcrypto} from "node:crypto";
import {beforeEach,it,expect,vi} from "vitest";
import {act,render,screen,fireEvent,waitFor} from "@testing-library/react";
import {SpaceView} from "../spaces/SpaceView";
import {findUiPage} from "../presentation/uiPages";
import {documentRequestIdentity} from "../presentation/documentRequestIdentity";
import {CanonicalMachineReceiptsSpace} from "../spaces/CanonicalMachineReceiptsSpace";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
// Peripheral asset/rubric surfaces have separate regressions; the actual context and machine panels remain mounted.
vi.mock("../spaces/CanonicalAiAssetsSpace",()=>({CanonicalAiAssetsSpace:()=>null}));
vi.mock("../components/MachineEvaluationPanel",()=>({MachineEvaluationPanel:()=>null}));
type J=Record<string,any>;
const docs=new Map<string,J>(),tasks=new Map<string,J>(),writes:J[]=[];
let correctionStatus="candidate";
const hash="a".repeat(64),originalId="knowledge-exact",candidateId="correction-exact";
function knowledge(id:string){return {knowledge_id:id,body:id===originalId?"同一原件的已接受正文":"使用者纠正正文",version:id+"-review-v1",status:id===originalId?"accepted":correctionStatus,source_id:id===originalId?"source-exact":null,anchor_id:id===originalId?"anchor-exact":null};}
function task(answer:J,scope="runtime.answer"){return {task_id:answer.answer_id,conditions:JSON.stringify(answer),scope,knowledge_version:answer.knowledge_id+"@v1",model_version:"SIMULATED-model",outcome:"unmeasured",method_version:null,tool_version:null,failure:null,retest_of:scope==="runtime.retest"?answer.retest_of:null};}
function setup(){bridge.call.mockImplementation(async(op:string,p:J={})=>{
 if(op==="machine_contexts_list")return {items:[...docs.values()].map(d=>({document_id:d.document_id,title:d.title,version:d.version,content_sha256:d.content_sha256})),next_cursor:null};
 if(op==="assessment_get")return {item_key:"assessment-exact",assessment_id:"assessment-id-exact",knowledge_id:originalId,knowledge_version:originalId,question:"原学习问题",content:"同一原件的已接受正文",source_id:"source-exact",anchor_id:"anchor-exact"};
 if(op==="knowledge_get")return knowledge(p.id);
 if(op==="document_get")return structuredClone(docs.get(p.document_id));
 if(op==="document_create"){const id=await documentRequestIdentity(p.body.create_request_id);const d={document_id:id,version:1,title:p.body.title,source_id:null,source_revision:null,content_sha256:hash,text_projection:"",blocks:[],editor_json:structuredClone(p.body.editor_json)};docs.set(id,d);writes.push({op,body:structuredClone(p.body)});return structuredClone(d);}
 if(op==="machine_answer"){writes.push({op,body:structuredClone(p.body)});const b=p.body,id="answer_req_"+createHash("sha256").update(b.client_request_id).digest("hex");const answer={schema:"archeaxis.machine-answer/v1",answer_id:id,client_request_id:b.client_request_id,knowledge_id:b.knowledge_id,question:b.question,answer:{answer:"SIMULATED 错误回答",model:"SIMULATED-model"},authority:"candidate",request:{schema:"archeaxis.machine-answer-request/v1",knowledge_id:b.knowledge_id,question:b.question,max_tokens:b.max_tokens,timeout_s:b.timeout_s,context_sha256:hash,context_grant:b.context_grant}};tasks.set(id,task(answer));return answer;}
 if(op==="machine_task_get")return structuredClone(tasks.get(p.task_id));
 if(op==="machine_tasks_list")return {items:[],next_cursor:null};
 if(op==="sources_list")return {sources:[]};
 if(op==="machine_correction"){writes.push({op,body:structuredClone(p.body)});return {answer_id:p.body.answer_id,failed_task_id:"evaluation_"+p.body.answer_id,correction_candidate_id:candidateId,status:"candidate",authority:"candidate",corrects_knowledge_id:p.body.knowledge_id,question:p.body.question,machine_answer:p.body.machine_answer,corrected_answer:p.body.corrected_answer,error_note:p.body.error_note,reviewer:p.body.reviewer};}
 if(op==="knowledge_review"){writes.push({op,body:structuredClone(p.body),id:p.id});correctionStatus=p.body.action;return {knowledge_id:p.id,version:p.id+"-review-v1"};}
 if(op==="machine_retest"){writes.push({op,body:structuredClone(p.body)});const b=p.body,answer={schema:"archeaxis.machine-retest/v1",answer_id:"retest-exact",retest_task_id:"retest-exact",retest_of:b.retest_of,knowledge_id:b.knowledge_id,question:b.question,answer:{answer:"SIMULATED 复测回答",model:"SIMULATED-model"},authority:"candidate",request:{retest_of:b.retest_of,knowledge_id:b.knowledge_id,question:b.question,max_tokens:b.max_tokens,context_grant:b.context_grant}};tasks.set("retest-exact",task(answer,"runtime.retest"));return answer;}
 throw new Error(`unconfigured ${op}`);
});}
function Journey(){const[page,setPage]=useState("13");return <SpaceView spaceId={findUiPage(page)!.space} uiPageId={page} onOpenPage={setPage} initialLearningItemKey="assessment-exact" onInspect={()=>{}} onNavigate={()=>{throw new Error("legacy navigation forbidden");}}/>;}
beforeEach(()=>{vi.stubGlobal("crypto",webcrypto);docs.clear();tasks.clear();writes.length=0;correctionStatus="candidate";bridge.call.mockReset();setup();});
async function grant(operation:"answer"|"retest",purpose:string){
 fireEvent.click(await screen.findByRole("button",{name:"读取指定知识并建立上下文候选"}));await screen.findByText(/仅建立上下文候选/);
 fireEvent.change(screen.getByLabelText("用途"),{target:{value:purpose}});fireEvent.change(screen.getByLabelText("授权依据"),{target:{value:"SYNTHETIC explicit human authorization"}});fireEvent.click(screen.getByLabelText(operation==="answer"?"允许本地回答":"允许本地复测"));
 expect(writes.filter(w=>w.op==="document_create")).toHaveLength(operation==="answer"?0:1);
 fireEvent.click(screen.getByRole("button",{name:"明确授权并保存"}));await screen.findByText("授权版本已保存并读回，消费时再次校验用途、知识与时效。");fireEvent.click(screen.getByRole("button",{name:"使用已保存上下文进入纠正与评测"}));
}
it("SIMULATED actual mounted 13→14 correction/review→13 independent grant→14 retest→22 exact readback retains one source journey",async()=>{
 render(<Journey/>);await grant("answer","原知识回答用途");
 expect(await screen.findByLabelText("原知识当前正文")).toHaveTextContent("同一原件的已接受正文");
 fireEvent.change(screen.getByLabelText("实际问题"),{target:{value:"原学习问题"}});fireEvent.click(screen.getByRole("button",{name:"执行本地机器回答"}));await screen.findByLabelText("真实机器回答");
 fireEvent.change(screen.getByLabelText("正确答案"),{target:{value:"使用者纠正正文"}});fireEvent.change(screen.getByLabelText("具体错误依据"),{target:{value:"对照同一原件引文"}});fireEvent.change(screen.getByLabelText("纠正提交者"),{target:{value:"SYNTHETIC reviewer"}});fireEvent.click(screen.getByRole("button",{name:"记录使用者纠正候选"}));
 fireEvent.change(await screen.findByLabelText("审核依据"),{target:{value:"SYNTHETIC reviewed same source"}});fireEvent.click(screen.getByRole("button",{name:"接受纠正知识"}));await screen.findByRole("button",{name:"以已接受纠正知识运行独立复测"});
 expect(screen.getByRole("button",{name:"以已接受纠正知识运行独立复测"})).toBeDisabled();
 fireEvent.click(screen.getByRole("button",{name:"为此纠正知识建立独立复测授权"}));await grant("retest","纠正知识独立复测用途");
 await waitFor(()=>expect(screen.getByRole("button",{name:"以已接受纠正知识运行独立复测"})).toBeEnabled());fireEvent.click(screen.getByRole("button",{name:"以已接受纠正知识运行独立复测"}));await screen.findByLabelText("独立复测机器回答");
 const answer=writes.find(w=>w.op==="machine_answer")!.body,retest=writes.find(w=>w.op==="machine_retest")!.body;
 // A real correction is an UNSOURCED observation; lineage is carried by the
 // original persisted answer and failed evaluation, never invented source fields.
 expect(knowledge(candidateId)).toMatchObject({source_id:null,anchor_id:null});const correction=writes.find(w=>w.op==="machine_correction")!.body;expect(correction.knowledge_id).toBe(originalId);expect(correction.answer_id).toBe("answer_req_"+createHash("sha256").update(answer.client_request_id).digest("hex"));expect(correction.question).toBe(answer.question);expect(correction.machine_answer).toBe("SIMULATED 错误回答");
 expect(answer.knowledge_id).toBe(originalId);expect(retest.knowledge_id).toBe(candidateId);expect(retest.question).toBe(answer.question);expect(retest.retest_of).toBe("evaluation_"+"answer_req_"+createHash("sha256").update(answer.client_request_id).digest("hex"));expect(retest.context_grant.document_id).not.toBe(answer.context_grant.document_id);
 fireEvent.click(screen.getByRole("button",{name:"读取此机器旅程的持久化回执"}));expect(await screen.findByLabelText("历史机器回答")).toHaveTextContent("SIMULATED 复测回答");expect(bridge.call).toHaveBeenCalledWith("machine_task_get",{task_id:"retest-exact"});
 fireEvent.click(screen.getByRole("button",{name:"返回同一纠正与复测旅程"}));expect(screen.getByLabelText("独立复测机器回答")).toHaveTextContent("SIMULATED 复测回答");expect(writes.filter(w=>w.op==="machine_answer")).toHaveLength(1);expect(writes.filter(w=>w.op==="machine_retest")).toHaveLength(1);
});
it("SIMULATED binding learning knowledge only reads a candidate and never grants permissions or invokes a model",async()=>{
 render(<Journey/>);fireEvent.click(screen.getByRole("button",{name:"读取指定知识并建立上下文候选"}));await screen.findByText(/仅建立上下文候选/);expect(screen.getByText("固定知识：knowledge-exact")).toBeTruthy();expect(screen.getByRole("button",{name:"明确授权并保存"})).toBeDisabled();expect(writes).toEqual([]);
});
it("SIMULATED wrong current learning knowledge cannot prepare or authorize a context",async()=>{
 const previous=bridge.call.getMockImplementation()!;bridge.call.mockImplementation(async(op:string,p:J={})=>op==="knowledge_get"?{...knowledge(p.id),knowledge_id:"other"}:previous(op,p));
 render(<Journey/>);fireEvent.click(screen.getByRole("button",{name:"读取指定知识并建立上下文候选"}));await screen.findByRole("alert");expect(writes).toEqual([]);expect(screen.getByRole("button",{name:"明确授权并保存"})).toBeDisabled();
});
it("SIMULATED an exact task outside the bounded directory is read directly and mismatched readback is rejected",async()=>{
 const previous=bridge.call.getMockImplementation()!;bridge.call.mockImplementation(async(op:string,p:J={})=>op==="machine_task_get"?{...task({answer_id:"other",knowledge_id:originalId,question:"wrong",answer:{answer:"wrong"}}),task_id:"other"}:previous(op,p));
 render(<CanonicalMachineReceiptsSpace initialTaskId="task-exact-outside-page"/>);await screen.findByRole("alert");expect(screen.queryByLabelText("历史机器回答")).toBeNull();expect(writes).toEqual([]);
});
it("SIMULATED late knowledge preparation does not replace edits made while its readback is pending",async()=>{
 let finish!:(value:unknown)=>void;const previous=bridge.call.getMockImplementation()!;bridge.call.mockImplementation(async(op:string,p:J={})=>op==="assessment_get"?new Promise(resolve=>{finish=resolve;}):previous(op,p));
 render(<Journey/>);fireEvent.click(screen.getByRole("button",{name:"读取指定知识并建立上下文候选"}));await waitFor(()=>expect(finish).toBeDefined());
 // The existing form fences editing while busy; no candidate or grant has yet been written.
 expect(screen.getByLabelText("用途")).toBeDisabled();fireEvent.change(screen.getByLabelText("用途"),{target:{value:"读取期间新增用途"}});expect(writes).toEqual([]);
 await act(async()=>finish({item_key:"assessment-exact",assessment_id:"assessment-id-exact",knowledge_id:originalId,knowledge_version:originalId,question:"原学习问题",content:"同一原件的已接受正文",source_id:"source-exact",anchor_id:"anchor-exact"}));
 await screen.findByText("读取期间的编辑已保留；指定知识未覆盖当前草稿。");expect(screen.getByLabelText("用途")).toHaveValue("读取期间新增用途");expect(writes).toEqual([]);
});
