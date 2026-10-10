import { beforeEach,describe,expect,it,vi } from "vitest";
import { render,screen,waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CoreWorkingStateSession,type PendingJob,type WorkingRead,type WorkingTransport } from "../presentation/coreWorkingState";
import { CoreWorkingStateProvider } from "../presentation/useCoreWorkingState";
import { JobContent } from "../components/JobContent";
import { FolderIngest } from "../components/FolderIngest";
import { BoundedJobPanel } from "../components/BoundedJobPanel";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const hash="a".repeat(64);
function fixture(surface:PendingJob["surface"]){
 const entry:PendingJob={source_id:"source",source_revision:hash,job_id:"original_job",request_id:"original_request",kind:"text",body:{deadline_ms:surface==="folder"?90000:60000,split:false,words:false},surface,mode:"single",origin_restore_epoch:"initial",relative:surface==="folder"?"owned.txt":null};
 let server:WorkingRead={schema:"archeaxis.ui-working-state/v1",workspace_id:"b".repeat(32),restore_epoch:"initial",state_revision:1,state:{drafts:{},opened_documents:[],active_document:null,page_id:"03",pending_original:null,pending_jobs:{original_request:entry}},draft_digests:{},pending_document_id:null,recovery_candidates:null,recovery_requires_confirmation:false};
 const transport:WorkingTransport={read:async()=>structuredClone(server),write:async req=>{server={...server,state:structuredClone(req.state),state_revision:server.state_revision+1};return structuredClone(server);},clearSaved:async()=>{throw new Error("unused");},clearJob:async()=>{throw new Error("no terminal proof");},recover:async()=>{throw new Error("unused");}};
 return {entry,transport};
}
describe("SIMULATED real components rehydrate exact Core journal without automatic work",()=>{
 beforeEach(()=>{bridge.call.mockReset();bridge.call.mockImplementation(async(op:string)=>{
  if(op==="capabilities_list")return {};
  if(op==="sources_list")return {sources:[{source_id:"source",source_revision:hash,sha256:hash,original_name:"owned.txt",imported_at:"SIMULATED"}]};
  if(op==="source_jobs")return {source_id:"source",jobs:[{job_id:"original_job",input_ref:"source",kind:"text",state:"queued"}],jobs_capped:false};
  if(op==="jobs_get"||op==="job_execution_status")return {job_id:"original_job",input_ref:"source",kind:"text",state:"queued",request_id:null,attempt:null,error:null,attempts:[],attempts_capped:false};
  if(op==="job_enqueue")return {job_id:"original_job",state:"queued"};
  if(op==="job_execute")throw new Error("SIMULATED lost execution ACK");
  throw new Error("unexpected "+op);
 });});
 it.each(["manual","folder","bounded"] as const)("%s remount and new App session recover same job/request/source/kind/budget before explicit retry",async(surface)=>{
  const f=fixture(surface);const user=userEvent.setup();
  const component=()=>surface==="manual"?<JobContent sourceId="source" sourceRevision={hash} name="owned.txt"/>:surface==="folder"?<FolderIngest/>:<BoundedJobPanel command={bridge.call} pollMs={60000}/>;
  async function mount(){const session=new CoreWorkingStateSession(f.transport);await session.load();return render(<CoreWorkingStateProvider session={session}>{component()}</CoreWorkingStateProvider>);}
  let view=await mount();await user.click(screen.getByRole("button",{name:"恢复冻结现场 original_request"}));
  await waitFor(()=>expect(screen.getAllByText(/original_request/).length).toBeGreaterThan(1));
  expect(bridge.call.mock.calls.some(([op])=>["job_execute","job_enqueue","capability_set_enabled"].includes(op))).toBe(false);
  view.unmount();view=await mount();await user.click(screen.getByRole("button",{name:"恢复冻结现场 original_request"}));
  const retry=surface==="manual"?"同请求重试转换":surface==="folder"?"同请求重试":"同请求重试";
  await user.click(await screen.findByRole("button",{name:retry}));
  await waitFor(()=>expect(bridge.call.mock.calls.filter(([op])=>op==="job_execute")).toHaveLength(1));
  const sent=bridge.call.mock.calls.find(([op])=>op==="job_execute")![1];
  expect(sent).toEqual({job_id:f.entry.job_id,request_id:f.entry.request_id,body:f.entry.body});
  expect(bridge.call.mock.calls.some(([op])=>op==="capability_set_enabled")).toBe(false);
  view.unmount();
 });
});
