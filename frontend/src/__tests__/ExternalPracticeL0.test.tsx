import { createHash } from "node:crypto";
import { act,fireEvent,render,screen,waitFor,within } from "@testing-library/react";
import { beforeEach,describe,expect,it,vi } from "vitest";
import { CanonicalTeachingSpace } from "../spaces/CanonicalTeachingSpace";
import { ApiError } from "../api/client";
import type { RecordView,TeachingRecord } from "../api/generated/teaching-contract";
import { CoreWorkingStateSession,type WorkingRead,type WorkingTransport } from "../presentation/coreWorkingState";
import { CoreWorkingStateProvider } from "../presentation/useCoreWorkingState";
const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
vi.mock("../spaces/CanonicalLearningSpace",()=>({CanonicalLearningSpace:()=>null}));
const clone=<T,>(value:T):T=>JSON.parse(JSON.stringify(value));
const hash=(value:unknown)=>createHash("sha256").update(JSON.stringify(value)).digest("hex");
const kid="knowledge_candidate_v1";
let records:Map<string,TeachingRecord>,written:TeachingRecord[],lostAck:boolean,lookupFault:"missing"|"different"|"withdrawn"|null;
const row=(id:string,kind:TeachingRecord["kind"],parent_id:string|null=null):TeachingRecord=>({schema:"archeaxis.teaching-record/v2",record_id:id,kind,knowledge_id:kid,knowledge_version:kid,course_id:null,parent_id,purpose:`原记录 ${id}`,content:`固定正文 ${id}`,scope:"personal",privacy:"local_only",feedback_class:kind==="feedback"?"expression_fit":null,assessment_id:null,rubric_version:null,assisted:false,producer_kind:"human_authored"});
const view=(record:TeachingRecord):RecordView=>({record:clone(record),content_sha256:hash(record),withdrawn:false,scoring_status:"not_scored"});
async function transport(op:string,p:any={}){
  if(op==="teaching_list")return {items:[...records.values()].map(view),next_cursor:null};
  if(op==="search")return {items:[{knowledge_id:kid,head:"未接纳的实践来源"}]};
  if(op==="knowledge_get")return {knowledge_id:kid,status:"candidate",knowledge_type:"FACTUAL_CLAIM"};
  if(op==="course_list")throw new ApiError(503,"optional course unavailable");
  if(op==="teaching_create"){
    const record=clone(p.body as TeachingRecord);written.push(record);records.set(record.record_id,record);
    if(lostAck){lostAck=false;throw new ApiError(503,"write ACK lost");}return {item:view(record),duplicate:false};
  }
  if(op==="teaching_get"){
    const record=records.get(p.record_id);if(!record||lookupFault==="missing")throw new ApiError(404,"not found");
    if(lookupFault==="different")return view({...record,content:"其他正文"});
    return {...view(record),withdrawn:lookupFault==="withdrawn"};
  }
  throw new Error("Unexpected "+op);
}
beforeEach(()=>{records=new Map();written=[];lostAck=false;lookupFault=null;bridge.call.mockReset().mockImplementation(transport);});
async function chooseCandidate(){fireEvent.click(screen.getByRole("button",{name:"搜索来源知识"}));fireEvent.click(await screen.findByRole("button",{name:"未接纳的实践来源"}));await screen.findByText(/已绑定未接纳的知识候选/);}
function fill(content:string,purpose="本人实践记录"){fireEvent.change(screen.getByLabelText("用途"),{target:{value:purpose}});fireEvent.change(screen.getByLabelText("内容"),{target:{value:content}});}
async function save(){fireEvent.click(screen.getByRole("button",{name:"保存教学记录"}));await screen.findByText("教学记录已保存；仍为不计分的人工作业记录。");}
async function prepare(action:string,basis?:string){
  fireEvent.change(screen.getByLabelText("实践操作"),{target:{value:action}});
  if(basis)fireEvent.change(screen.getByLabelText("实践依据记录"),{target:{value:basis}});
  fireEvent.click(screen.getByRole("button",{name:"准备实践文字草稿"}));await screen.findByText(/已准备实践文字草稿/);
}
function workingFixture(workspaceId="a".repeat(32)){let server:WorkingRead={schema:"archeaxis.ui-working-state/v1",workspace_id:workspaceId,restore_epoch:"initial",state_revision:0,state:{drafts:{},opened_documents:[],active_document:null,page_id:"08",pending_original:null},draft_digests:{},pending_document_id:null,recovery_candidates:null,recovery_requires_confirmation:false};
  const transport:WorkingTransport={read:async()=>clone(server),write:async request=>{server={...server,state:clone(request.state),state_revision:server.state_revision+1};return clone(server);},clearSaved:vi.fn(),recover:vi.fn()};
  return {transport,session:new CoreWorkingStateSession(transport)};
}

describe("L0 ordinary text practice consumer",()=>{
  it("saves candidate-source text without a course or connection and survives optional course failure",async()=>{
    render(<CanonicalTeachingSpace pageId="08"/>);await chooseCandidate();
    expect(bridge.call.mock.calls.some(([op])=>op==="course_list")).toBe(false);
    fireEvent.click(screen.getByRole("button",{name:"读取可选课程"}));await screen.findByText(/可选课程暂时无法读取/);
    fireEvent.change(screen.getByLabelText("记录类型"),{target:{value:"requirement"}});fill("没有连接外部工具，也没有成果文件。我要练习解释一个步骤。");await save();
    expect(written[0]).toMatchObject({kind:"requirement",parent_id:null,knowledge_id:kid,knowledge_version:kid,course_id:null,assessment_id:null,rubric_version:null});
    expect(bridge.call.mock.calls.some(([op])=>/learning_|machine_|runtime_|job_/.test(op))).toBe(false);
  });
  it("keeps Observation's existing optional-parent path",async()=>{
    render(<CanonicalTeachingSpace pageId="08"/>);await chooseCandidate();fill("还没有计划，只记下本人的尝试和困惑。");await save();expect(written[0]).toMatchObject({kind:"observation",parent_id:null});
  });
  it("prepares a plan from the saved requirement without substituting a delivery",async()=>{
    const requirement=row("requirement_for_plan","requirement");records.set(requirement.record_id,requirement);render(<CanonicalTeachingSpace pageId="08"/>);
    await screen.findByRole("button",{name:"需求 · 原记录 requirement_for_plan"});await prepare("plan",requirement.record_id);
    fireEvent.change(screen.getByLabelText("内容"),{target:{value:"计划：先读原材料，再用纸笔练习；无需连接工具。"}});await save();
    expect(written[0]).toMatchObject({kind:"proposal",parent_id:requirement.record_id,knowledge_version:kid,course_id:null});
  });
  it("appends skip, replacement, start, self-report and feedback to their exact plan lineage",async()=>{
    const requirement=row("requirement_original","requirement"),plan=row("plan_original","proposal",requirement.record_id);records.set(requirement.record_id,requirement);records.set(plan.record_id,plan);
    render(<CanonicalTeachingSpace pageId="09"/>);await screen.findByRole("button",{name:"表达方案 · 原记录 plan_original"});
    const original=clone(plan);let basis=plan.record_id;
    for(const action of ["skip","replace"]){await prepare(action,basis);fireEvent.change(screen.getByLabelText("内容"),{target:{value:action==="skip"?"跳过旧教程：不适合当前目标；改为手工尝试。":"旧教程替换为新教程 https://example.invalid/tutorial；仅保存链接，不打开。"}});await save();const saved=written.at(-1)!;expect(saved).toMatchObject({kind:"revision",parent_id:basis,knowledge_version:kid});basis=saved.record_id;}
    const planVersion=basis;
    for(const action of ["start","complete","note"]){await prepare(action,planVersion);fireEvent.change(screen.getByLabelText("内容"),{target:{value:`本人${action}的文字记录；没有文件，没有外部连接。`}});await save();expect(written.at(-1)).toMatchObject({kind:"observation",parent_id:planVersion,assessment_id:null,rubric_version:null});}
    const observation=written.at(-1)!;await prepare("feedback",observation.record_id);fireEvent.change(screen.getByLabelText("内容"),{target:{value:"人工反馈：仍需说明第二步理由；并未独立评价或确认掌握。"}});await save();expect(written.at(-1)).toMatchObject({kind:"feedback",parent_id:observation.record_id,feedback_class:"expression_fit"});
    const feedback=written.at(-1)!;await prepare("revise",feedback.record_id);fireEvent.change(screen.getByLabelText("内容"),{target:{value:"按原反馈修订计划，下次补第二步理由。"}});await save();expect(written.at(-1)).toMatchObject({kind:"revision",parent_id:feedback.record_id});
    expect(records.get(plan.record_id)).toEqual(original);expect(written.every(record=>record.course_id===null&&record.knowledge_version===kid&&record.kind!=="delivery"&&record.kind!=="teach_back")).toBe(true);
    expect(bridge.call.mock.calls.some(([op])=>/learning_|assessment_|machine_|job_|course_/.test(op))).toBe(false);
  });
  it("does not replace unsaved prose when another practice action is prepared",async()=>{
    render(<CanonicalTeachingSpace pageId="08"/>);fill("尚未保存的原输入");fireEvent.click(screen.getByRole("button",{name:"准备实践文字草稿"}));await screen.findByText(/当前文字尚未保存/);
    expect(screen.getByLabelText("内容")).toHaveValue("尚未保存的原输入");expect(written).toHaveLength(0);
  });
  it("does not turn a planned start into an unbound observation after changing source selection",async()=>{
    const plan=row("plan_start","proposal","requirement");records.set(plan.record_id,plan);render(<CanonicalTeachingSpace pageId="09"/>);await screen.findByRole("button",{name:"表达方案 · 原记录 plan_start"});
    await prepare("start",plan.record_id);fireEvent.change(screen.getByLabelText("内容"),{target:{value:"本人刚开始第一步。"}});await chooseCandidate();
    fireEvent.click(screen.getByRole("button",{name:"保存教学记录"}));await screen.findByText(/操作未确认完成/);expect(written).toHaveLength(0);expect(screen.getByLabelText("内容")).toHaveValue("本人刚开始第一步。");
  });
  it.each(["different","withdrawn"] as const)("does not prepare against a %s fixed parent readback",async fault=>{
    const plan=row("fixed_plan","proposal","requirement");records.set(plan.record_id,plan);render(<CanonicalTeachingSpace pageId="09"/>);await screen.findByRole("button",{name:"表达方案 · 原记录 fixed_plan"});
    lookupFault=fault;fireEvent.change(screen.getByLabelText("实践操作"),{target:{value:"start"}});fireEvent.change(screen.getByLabelText("实践依据记录"),{target:{value:plan.record_id}});fireEvent.click(screen.getByRole("button",{name:"准备实践文字草稿"}));await screen.findByText(/操作未确认完成/);expect(screen.getByLabelText("内容")).toHaveValue("");expect(written).toHaveLength(0);
  });
  it("keeps a factual candidate out of Delivery while preserving ordinary text",async()=>{
    render(<CanonicalTeachingSpace pageId="10"/>);fireEvent.click(screen.getByRole("button",{name:"搜索来源知识"}));fireEvent.click(await screen.findByRole("button",{name:"未接纳的实践来源"}));await screen.findByText(/操作未确认完成/);fill("保留准备正文，不伪造交付");fireEvent.click(screen.getByRole("button",{name:"保存教学记录"}));await screen.findByText(/操作未确认完成/);expect(screen.getByLabelText("内容")).toHaveValue("保留准备正文，不伪造交付");expect(written).toHaveLength(0);
  });
  it("requires actual prose before registering a prepared empty practice outline",async()=>{
    render(<CanonicalTeachingSpace pageId="08"/>);await chooseCandidate();await prepare("requirement");fireEvent.click(screen.getByRole("button",{name:"保存教学记录"}));await screen.findByText(/操作未确认完成/);expect(written).toHaveLength(0);expect((screen.getByLabelText("内容") as HTMLTextAreaElement).value).toContain("想练习什么");
  });
  it("keeps a lost ACK frozen across a missing read and resolves only the original saved record",async()=>{
    render(<CanonicalTeachingSpace pageId="08"/>);await chooseCandidate();fill("这是实际文字实践，无文件。");lostAck=true;fireEvent.click(screen.getByRole("button",{name:"保存教学记录"}));await screen.findByText(/操作未确认完成/);
    const sent=clone(written[0]);expect(screen.getByLabelText("内容")).toBeDisabled();lookupFault="missing";fireEvent.click(screen.getByRole("button",{name:"重试同一记录"}));await waitFor(()=>expect(bridge.call.mock.calls.some(([op])=>op==="teaching_get")).toBe(true));await waitFor(()=>expect(screen.getByRole("button",{name:"重试同一记录"})).toBeEnabled());
    expect(screen.getByLabelText("内容")).toHaveValue(sent.content);lookupFault=null;fireEvent.click(screen.getByRole("button",{name:"重试同一记录"}));await screen.findByText("已读回同一客户端记录，未重复创建。");expect(written).toEqual([sent]);
    const article=screen.getByRole("article",{name:"已保存教学记录"});expect(within(article).getByText(sent.content)).toBeInTheDocument();
  });
  it("preserves a frozen input when same-ID readback has another body",async()=>{
    render(<CanonicalTeachingSpace pageId="08"/>);await chooseCandidate();fill("不能丢失的原实践记录");lostAck=true;fireEvent.click(screen.getByRole("button",{name:"保存教学记录"}));await screen.findByText(/操作未确认完成/);lookupFault="different";fireEvent.click(screen.getByRole("button",{name:"重试同一记录"}));await waitFor(()=>expect(screen.getByRole("button",{name:"重试同一记录"})).toBeEnabled());
    expect(screen.getByLabelText("内容")).toHaveValue("不能丢失的原实践记录");expect(screen.getByLabelText("内容")).toBeDisabled();expect(written).toHaveLength(1);
  });
  it("reopens the pending practice draft in a new working-state session and only reads its exact record",async()=>{
    const f=workingFixture();await f.session.load();const first=render(<CoreWorkingStateProvider session={f.session}><CanonicalTeachingSpace pageId="08"/></CoreWorkingStateProvider>);
    await chooseCandidate();fill("冷重开保留的文字实践");lostAck=true;fireEvent.click(screen.getByRole("button",{name:"保存教学记录"}));await screen.findByText(/操作未确认完成/);await act(async()=>{await f.session.flush();});first.unmount();
    const reopened=new CoreWorkingStateSession(f.transport);await reopened.load();render(<CoreWorkingStateProvider session={reopened}><CanonicalTeachingSpace pageId="08"/></CoreWorkingStateProvider>);
    expect(screen.getByLabelText("内容")).toHaveValue("冷重开保留的文字实践");expect(screen.getByLabelText("内容")).toBeDisabled();fireEvent.click(screen.getByRole("button",{name:"重试同一记录"}));await screen.findByText("已读回同一客户端记录，未重复创建。");expect(written).toHaveLength(1);
  });
  it.each(["unmount","workspace-switch"] as const)("does not dispatch after %s during the pending journal acknowledgement",async mode=>{
    const f=workingFixture();await f.session.load();let release!:()=>void,journalStarted=false;
    const held=new Promise<void>(resolve=>{release=resolve;}),write=f.transport.write;
    f.transport.write=async request=>{const response=await write(request);if(request.state.teaching_drafts?.["08:"]?.pending_record){journalStarted=true;await held;}return response;};
    const mounted=render(<CoreWorkingStateProvider session={f.session}><CanonicalTeachingSpace pageId="08"/></CoreWorkingStateProvider>);
    await chooseCandidate();fill("切换时保留的原实践输入");fireEvent.click(screen.getByRole("button",{name:"保存教学记录"}));await waitFor(()=>expect(journalStarted).toBe(true));
    expect(written).toHaveLength(0);
    if(mode==="unmount")mounted.unmount();else{const other=workingFixture("b".repeat(32));await other.session.load();mounted.rerender(<CoreWorkingStateProvider session={other.session}><CanonicalTeachingSpace pageId="08"/></CoreWorkingStateProvider>);}
    await act(async()=>{release();await f.session.flush();});expect(written).toHaveLength(0);
    expect(f.session.getSnapshot().state.teaching_drafts?.["08:"]?.pending_record?.content).toBe("切换时保留的原实践输入");
    expect(bridge.call.mock.calls.some(([op])=>op==="teaching_create")).toBe(false);
  });
});
