import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { webcrypto } from "node:crypto";
import { MachineEvaluationPanel } from "../components/MachineEvaluationPanel";
import { documentRequestIdentity } from "../presentation/documentRequestIdentity";
import { ApiError } from "../api/client";
const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const hash="a".repeat(64),answerHash="b".repeat(64),receiptHash="c".repeat(64);
const rubric={schema:"archeaxis.machine-rubric/v1",request_id:"rubric-source",title:"既有量规",purpose:"逐项核对",criteria:[{criterion_id:"criterion1",label:"依据一致",expectation:"原答案应符合引用依据"}],sources:[]};
const snapshot={task_id:"task1",knowledge_id:"k1",question:"原问题",original_answer:"实际持久化原答案",model_version:"local-model",original_answer_sha256:answerHash,task_receipt_sha256:receiptHash,receipt:{task_id:"task1",scope:"runtime.answer"},evaluation_authority:"human_observation_only",grants_machine_qualification:false,grants_human_mastery:false,grants_professional_truth:false};
async function doc(body:Record<string,unknown>,key="archeaxis_machine_rubric",title=String(body.title??"人工机器评测")) {
 return {document_id:await documentRequestIdentity(String(body.request_id)),version:1,title,content_sha256:hash,source_id:null,source_revision:null,editor_json:{type:"doc",attrs:{[key]:body},content:[]},blocks:[],text_projection:""};
}
async function setupEvaluation() {
 const user=userEvent.setup();await user.type(screen.getByLabelText("机器任务 ID"),"task1");await user.click(screen.getByRole("button",{name:"读取原答案快照"}));
 await screen.findByText("实际持久化原答案");await user.click(screen.getByRole("button",{name:"读取量规列表"}));await user.click(await screen.findByRole("button",{name:"固定量规 既有量规"}));
 await screen.findByLabelText("人工依据 1");await user.type(screen.getByLabelText("评测者署名"),"使用者甲");await user.type(screen.getByLabelText("整体评测依据"),"已对照原答案及固定准则");await user.type(screen.getByLabelText("人工依据 1"),"此项需要继续核实");return user;
}
async function defaultBridge() {
 const source=await doc(rubric);const persisted=new Map<string,Awaited<ReturnType<typeof doc>>>();
 bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>={})=>{
  if(op==="machine_answer_snapshot")return snapshot;
  if(op==="machine_rubrics_list")return {items:[source],next_cursor:null};
  if(op==="machine_evaluations_list")return {items:[],next_cursor:null};
  if(op==="document_version") {if(payload.document_id===source.document_id)return {...source,version:payload.version};const d=persisted.get(String(payload.document_id));if(d && payload.version===d.version)return d;throw new ApiError(404,"missing","unavailable");}
  if(op==="machine_rubric_create") {const d=await doc(payload.body as Record<string,unknown>);persisted.set(d.document_id,d);return d;}
  if(op==="machine_evaluation_create") {const body=payload.body as Record<string,unknown>;const d=await doc({...body,schema:"archeaxis.machine-evaluation/v1",knowledge_id:"k1",original_answer_sha256:answerHash,task_receipt_sha256:receiptHash},"archeaxis_machine_evaluation");persisted.set(d.document_id,d);return d;}
  throw new Error(`unexpected ${op}`);
 });return {source,persisted};
}
describe("SIMULATED finite human machine evaluation UI",()=>{
 beforeEach(()=>{cleanup();bridge.call.mockReset();vi.stubGlobal("crypto",webcrypto);});
 it("binds the actual original answer and pinned rubric; never sends trusted actor from reviewer annotation",async()=>{
  const {source}=await defaultBridge();render(<MachineEvaluationPanel/>);const user=await setupEvaluation();await user.click(screen.getByRole("button",{name:"登记人工评测"}));
  await screen.findByText(/已登记并核对固定版本/);const [,payload]=bridge.call.mock.calls.find(([op])=>op==="machine_evaluation_create")!;
  expect(payload.body).toMatchObject({task_id:"task1",rubric:{document_id:source.document_id,version:1,content_sha256:hash},reviewer:"使用者甲",outcome:"unmeasured",judgments:[{criterion_id:"criterion1",outcome:"unmeasured",basis:"此项需要继续核实"}]});
  expect(payload.body).not.toHaveProperty("actor");expect(payload.body).not.toHaveProperty("original_answer");expect(bridge.call.mock.calls.some(([op])=>["machine_answer","knowledge_review","learning_review"].includes(op))).toBe(false);
 });
 it("retries the exact frozen evaluation request after lost ACK and verifies original snapshot hashes",async()=>{
  const {persisted}=await defaultBridge();const implementation=bridge.call.getMockImplementation()!;let first=true;
  bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>={})=>{const value=await implementation(op,payload);if(op==="machine_evaluation_create"&&first){first=false;throw new Error("response lost after Core saved");}return value;});
  render(<MachineEvaluationPanel/>);const user=await setupEvaluation();await user.click(screen.getByRole("button",{name:"登记人工评测"}));await screen.findByText(/写入未确认/);
  expect(screen.getByLabelText("整体评测依据")).toHaveValue("已对照原答案及固定准则");await user.click(screen.getByRole("button",{name:"同 ID 重试评测"}));await screen.findByText(/已登记并核对固定版本/);
  const attempts=bridge.call.mock.calls.filter(([op])=>op==="machine_evaluation_create");expect(attempts).toHaveLength(2);expect(attempts[0][1]).toEqual(attempts[1][1]);expect(persisted.size).toBe(1);
 });
 it("does not let a new task hint replace unsaved judgments and uses separate dirty owners",async()=>{
  await defaultBridge();const events: {owner:string;dirty:boolean}[]=[];const listener=(e:Event)=>events.push((e as CustomEvent).detail);window.addEventListener("archeaxis-draft-dirty",listener);
  const view=render(<MachineEvaluationPanel taskId="task1"/>);const user=await setupEvaluation();view.rerender(<MachineEvaluationPanel taskId="task2"/>);await user.click(screen.getByRole("button",{name:"使用新任务提示"}));
  expect(screen.getByLabelText("机器任务 ID")).toHaveValue("task1");expect(screen.getByLabelText("人工依据 1")).toHaveValue("此项需要继续核实");expect(screen.getByText(/新任务提示已保留/)).toBeInTheDocument();
  await user.type(screen.getByLabelText("量规标题"),"未保存量规");expect(new Set(events.filter(e=>e.dirty).map(e=>e.owner)).size).toBe(2);view.unmount();expect(events.slice(-2).every(e=>e.dirty===false)).toBe(true);window.removeEventListener("archeaxis-draft-dirty",listener);
 });
 it("retains rubric request identity after lost ACK and can reconcile with GET without another POST",async()=>{
  await defaultBridge();const impl=bridge.call.getMockImplementation()!;bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>={})=>{const result=await impl(op,p);if(op==="machine_rubric_create")throw new Error("ACK lost");return result;});
  render(<MachineEvaluationPanel/>);const user=userEvent.setup();await user.type(screen.getByLabelText("量规标题"),"新量规");await user.type(screen.getByLabelText("量规用途"),"核对依据");await user.type(screen.getByLabelText("准则名称 1"),"引用");await user.type(screen.getByLabelText("准则预期 1"),"引用可核实");await user.click(screen.getByRole("button",{name:"登记新量规"}));await screen.findByText(/写入未确认/);
  await user.click(screen.getByRole("button",{name:"核对冻结量规"}));await screen.findByText(/已登记并核对固定版本/);expect(bridge.call.mock.calls.filter(([op])=>op==="machine_rubric_create")).toHaveLength(1);
 });
 it("does not report success when Core rejects machine identity or readback answer hashes differ",async()=>{
  await defaultBridge();const impl=bridge.call.getMockImplementation()!;bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>={})=>{if(op==="machine_evaluation_create")throw new ApiError(403,"machine principal refused","unauthorized");return impl(op,p);});
  render(<MachineEvaluationPanel/>);const user=await setupEvaluation();await user.click(screen.getByRole("button",{name:"登记人工评测"}));await screen.findByText(/写入未确认/);expect(screen.queryByText(/已登记并核对固定版本/)).not.toBeInTheDocument();expect(screen.getByLabelText("评测者署名")).toHaveValue("使用者甲");
 });
 it("keeps an edited evaluation while reading a pinned historical evaluation document",async()=>{
  const {persisted}=await defaultBridge();const e={request_id:"historical-eval",task_id:"task1",rubric:{document_id:(await doc(rubric)).document_id,version:1,content_sha256:hash},reviewer:"历史署名",basis:"历史依据",judgments:[{criterion_id:"criterion1",outcome:"failed",basis:"历史差异"}],outcome:"failed",schema:"archeaxis.machine-evaluation/v1",knowledge_id:"k1",original_answer_sha256:answerHash,task_receipt_sha256:receiptHash};const d=await doc(e,"archeaxis_machine_evaluation");persisted.set(d.document_id,d);
  const impl=bridge.call.getMockImplementation()!;bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>={})=>op==="machine_evaluations_list"?{items:[d],next_cursor:null}:impl(op,p));
  render(<MachineEvaluationPanel/>);const user=await setupEvaluation();await user.click(screen.getByRole("button",{name:"读取评测历史"}));await user.click(await screen.findByRole("button",{name:"查看评测 人工机器评测"}));await screen.findByText("历史依据");expect(screen.getByLabelText("人工依据 1")).toHaveValue("此项需要继续核实");expect(bridge.call).toHaveBeenCalledWith("document_version",{document_id:d.document_id,version:1});expect(bridge.call.mock.calls.map(c=>c[0])).not.toContain("document_get");
 });
 it("withholds success when the saved evaluation binds another original answer hash",async()=>{
  await defaultBridge();const impl=bridge.call.getMockImplementation()!;bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>={})=>{const result=await impl(op,p);if(op==="machine_evaluation_create"){const broken=structuredClone(result);broken.editor_json.attrs.archeaxis_machine_evaluation.original_answer_sha256="d".repeat(64);return broken;}return result;});
  render(<MachineEvaluationPanel/>);const user=await setupEvaluation();await user.click(screen.getByRole("button",{name:"登记人工评测"}));await screen.findByText(/写入未确认/);expect(screen.queryByText(/已登记并核对固定版本/)).not.toBeInTheDocument();expect(screen.getByLabelText("人工依据 1")).toHaveValue("此项需要继续核实");
 });
});
