import {useEffect,useRef,useState} from "react";
import {createHash,webcrypto} from "node:crypto";
import {fireEvent,render,screen,waitFor,within} from "@testing-library/react";
import {afterEach,beforeEach,expect,it,vi} from "vitest";
import {SpaceView} from "../spaces/SpaceView";
import {App} from "../app/App";
import type {DocumentDto,IngestBatchDto} from "../api/generated/core-contract";
import type {SourceJourneyTarget} from "../presentation/sourceJourney";

// The page router, exchange, reader, durable-history control and relation panel
// are real. Only Core transport and the unrelated rich text editor are simulated.
const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call,verifyCanonicalCore:vi.fn(async()=>{})}));
vi.mock("../components/DocumentEditor",()=>({DocumentEditor:()=> <p>SIMULATED editor</p>}));
vi.mock("../components/FirstUseGuide",async original=>({...await original<object>(),FirstUseGuide:()=>null,requestFirstUseGuide:vi.fn()}));
const raw="Original [[image.svg]]",a=createHash("sha256").update(raw).digest("hex"),b="b".repeat(64),c="c".repeat(64);
const selection={batch_id:"batch-exact",ordinal:0,workspace_id:"workspace",restore_epoch:"initial",source_id:"src_a",source_revision:a};
const source={source_id:"src_a",source_revision:a,sha256:a,original_name:"notes/note.md",imported_at:"now"};
const doc:DocumentDto={document_id:"doc_a",version:1,source_id:"src_a",source_revision:a,title:"Fixed note",content_sha256:c,text_projection:"saved body",blocks:[],editor_json:{type:"doc",content:[]}};
const batch:IngestBatchDto={schema:"archeaxis.ingest-batch/v1",workspace_id:"workspace",restore_epoch:"initial",batch_id:"batch-exact",folder_label:"Synthetic vault",expected_members:2,registered_members:2,complete:true,created_at:"now",next_ordinal:null,members:[
 {ordinal:0,relative_path:"notes/note.md",byte_length:raw.length,disposition:"pending",source_id:"src_a",source_revision:a,job_id:null,kind:null,job_state:null},
 {ordinal:1,relative_path:"image.svg",byte_length:10,disposition:"pending",source_id:"src_b",source_revision:b,job_id:null,kind:null,job_state:null},
]};
const changed=vi.fn(),guard=vi.fn();
function Journey({start="16",reject=false}:{start?:string;reject?:boolean}) {
 const [page,setPage]=useState(start),[target,setTarget]=useState<SourceJourneyTarget>();
 const owners=useRef(new Set<string>());
 useEffect(()=>{const listen=(event:Event)=>{const value=(event as CustomEvent<boolean|{owner?:string;dirty?:boolean}>).detail;
  const owner=typeof value==="object"?value.owner??"legacy":"legacy",dirty=typeof value==="object"?value.dirty:value;
  if(dirty)owners.current.add(owner);else owners.current.delete(owner);
 };window.addEventListener("archeaxis-draft-dirty",listen);return()=>window.removeEventListener("archeaxis-draft-dirty",listen);},[]);
 const open=(id:string)=>{guard(id);if(reject||owners.current.size)return false;setPage(id);return true;};
 return <><output aria-label="actual page">{page}</output><button onClick={()=>open("16")}>离开阅读</button><SpaceView spaceId="library" uiPageId={page} onInspect={()=>{}} onNavigate={()=>{}} onOpenPage={open} sourceJourney={{target,onChange:value=>{changed(value);setTarget(value);}}}/></>;
}
beforeEach(()=>{
 vi.stubGlobal("crypto",webcrypto);changed.mockReset();guard.mockReset();bridge.call.mockReset();
 bridge.call.mockImplementation(async(op:string)=>{
  if(op==="sources_list")return {sources:[source]};
  if(op==="documents_list")return {documents:[doc],next_cursor:null,snapshot_count:1};
  if(op==="source_original")return {source_id:"src_a",name:source.original_name,sha256:a,media_type:"text/markdown",content_base64:Buffer.from(raw).toString("base64")};
  if(op==="anchors_list")return {anchors:[]};
  if(op==="document_get"||op==="document_version")return structuredClone(doc);
  if(op==="document_backlinks")return {target:{document_id:doc.document_id,version:doc.version,content_sha256:doc.content_sha256},backlinks:[]};
  if(op==="document_graph")return {center:{document_id:doc.document_id,version:doc.version,content_sha256:doc.content_sha256},edges:[]};
  if(op==="ingest_batches_list")return {workspace_id:"workspace",restore_epoch:"initial",batches:[batch],next_cursor:null};
  if(op==="ingest_batch_get")return structuredClone(batch);
  if(op==="checks_list")return {checks:[]};
  throw new Error(`Unexpected synthetic Core operation ${op}`);
 });
});
afterEach(()=>{vi.unstubAllGlobals();vi.restoreAllMocks();window.history.replaceState(null,"","/");});
async function restore() {
 fireEvent.click(screen.getByRole("button",{name:"读取历史批次"}));
 fireEvent.click(await screen.findByRole("button",{name:"查看批次 Synthetic vault"}));
 return screen.findByRole("button",{name:"映射此原件中的链接"});
}
it("SIMULATED actual page16 history hands the exact member to the actual page03 relation panel",async()=>{
 render(<Journey/>);fireEvent.click(await restore());
 expect(screen.getByLabelText("actual page")).toHaveTextContent("03");
 expect(changed).toHaveBeenLastCalledWith({source_id:"src_a",source_revision:a,sha256:a,folder_member:selection});
 const panel=await screen.findByRole("region",{name:"文件夹原件链接接入"});
 expect(screen.getByText("批次链接与附件").closest("details")).toHaveAttribute("open");
 expect(screen.getByText("批次链接与附件").closest("details")).toHaveClass("reader-batch-tools");
 expect(screen.getByText("批次链接与附件").closest("details")).not.toHaveClass("reader-source-tools");
 fireEvent.click(within(panel).getByRole("button",{name:"读取完整批次映射"}));
 await within(panel).findByLabelText("链接目标 image.svg");
 expect(bridge.call).toHaveBeenCalledWith("ingest_batch_get",{batch_id:"batch-exact"});
 expect(bridge.call.mock.calls.some(([op])=>op==="ingest_member_relations_apply"||op==="document_create")).toBe(false);
});
it("SIMULATED a refused page16 navigation cannot seed a later unrelated reader",async()=>{
 const view=render(<Journey reject/>);fireEvent.click(await restore());
 expect(guard).toHaveBeenLastCalledWith("03");expect(changed).not.toHaveBeenCalled();
 expect(screen.getByLabelText("actual page")).toHaveTextContent("16");
 view.unmount();render(<Journey start="03"/>);
 expect(screen.queryByRole("region",{name:"文件夹原件链接接入"})).toBeNull();
});
it("SIMULATED actual page03 resumes historical batches without uploading or converting them again",async()=>{
 render(<Journey start="03"/>);
 fireEvent.click(screen.getByText("批次链接与附件"));
 fireEvent.click(await restore());
 expect(await screen.findByRole("region",{name:"文件夹原件链接接入"})).toBeInTheDocument();
 expect(changed).not.toHaveBeenCalled();
 expect(bridge.call.mock.calls.some(([op])=>["source_import","ingest_member_import","ingest_member_enqueue","job_execute"].includes(op))).toBe(false);
});
it("SIMULATED lost relation ACK retains the actual reader and blocks replacing its member or leaving",async()=>{
 const original=bridge.call.getMockImplementation()!;
 bridge.call.mockImplementation(async(op:string,...args:unknown[])=>{if(op==="ingest_member_relations_apply")throw new Error("SIMULATED ACK lost");return original(op,...args);});
 render(<Journey/>);fireEvent.click(await restore());
 const panel=await screen.findByRole("region",{name:"文件夹原件链接接入"});
 fireEvent.click(within(panel).getByRole("button",{name:/Fixed note · v1 · doc_a/}));
 await screen.findByRole("heading",{name:"Fixed note"});
 fireEvent.click(within(panel).getByRole("button",{name:"读取完整批次映射"}));
 fireEvent.change(await within(panel).findByLabelText("链接目标 image.svg"),{target:{value:"source"}});
 const apply=within(panel).getByRole("button",{name:"确认映射并保存原件关系"});
 await waitFor(()=>expect(apply).toBeEnabled());fireEvent.click(apply);
 await within(panel).findByText(/处理结果待确认/);
 fireEvent.click(screen.getByRole("button",{name:"离开阅读"}));
 expect(screen.getByLabelText("actual page")).toHaveTextContent("03");
 fireEvent.click(await restore());
 expect(screen.getByText(/原关系请求、草稿或写入未确认/)).toBeInTheDocument();
 expect(screen.getByRole("region",{name:"文件夹原件链接接入"})).toBe(panel);
 fireEvent.click(within(panel).getByRole("button",{name:"只读核对原关系请求"}));
 await within(panel).findByText(/缺少本次操作的确认记录，处理结果仍待确认/);
 expect(bridge.call.mock.calls.filter(([op])=>op==="ingest_member_relations_apply")).toHaveLength(1);
 expect(apply).toBeDisabled();
});
it("SIMULATED actual App navigation guard protects an UNKNOWN request from the real page03 relation panel",async()=>{
 window.history.replaceState(null,"","/#page=16");
 const original=bridge.call.getMockImplementation()!;
 bridge.call.mockImplementation(async(op:string,...args:unknown[])=>{if(op==="ingest_member_relations_apply")throw new Error("SIMULATED ACK lost");return original(op,...args);});
 const confirm=vi.spyOn(window,"confirm").mockReturnValue(false);
 render(<App/>);fireEvent.click(await restore());
 await waitFor(()=>expect(window.location.hash).toBe("#page=03"));
 const panel=await screen.findByRole("region",{name:"文件夹原件链接接入"});
 fireEvent.click(within(panel).getByRole("button",{name:/Fixed note · v1 · doc_a/}));
 await screen.findByRole("heading",{name:"Fixed note"});
 fireEvent.click(within(panel).getByRole("button",{name:"读取完整批次映射"}));
 await within(panel).findByLabelText("链接目标 image.svg");
 fireEvent.click(within(panel).getByRole("button",{name:"确认映射并保存原件关系"}));
 await within(panel).findByText(/处理结果待确认/);confirm.mockClear();
 fireEvent.click(within(screen.getByRole("navigation",{name:"工作空间快捷导航"})).getByRole("button",{name:"知识"}));
 expect(confirm).toHaveBeenCalledTimes(1);expect(window.location.hash).toBe("#page=03");
 expect(screen.getByRole("region",{name:"文件夹原件链接接入"})).toBe(panel);
 expect(bridge.call.mock.calls.filter(([op])=>op==="ingest_member_relations_apply")).toHaveLength(1);
});
