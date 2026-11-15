import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createHash, webcrypto } from "node:crypto";
import { CanonicalLibrarySpace } from "../spaces/CanonicalLibrarySpace";
import { JobContent } from "../components/JobContent";
import { jobContentCoreFixture, outputReceipt } from "./fixtures/jobContentCoreFixture";

const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
vi.mock("../components/CheckPanel",()=>({CheckPanel:()=>null}));
vi.mock("../components/BackupPanel",()=>({BackupPanel:()=>null}));
vi.mock("../components/DocumentBacklinks",()=>({DocumentBacklinks:()=>null}));
vi.mock("../templates/TemplateWorkspace",()=>({TemplateLauncher:()=>null}));

const rootHtml='<p>MHTML 正文🙂</p><script>SHOULD_NOT_RUN</script>';
const raw='MIME-Version: 1.0\r\nContent-Type: multipart/related; boundary="B"; type="text/html"; start="<root>"\r\n\r\n--B\r\nContent-Type: image/png\r\nContent-ID: <image>\r\n\r\nopaque\r\n--B\r\nContent-Type: text/html; charset=utf-8\r\nContent-ID: <root>\r\nContent-Location: javascript:SHOULD_NOT_RUN\r\nContent-Transfer-Encoding: 8bit\r\n\r\n'+rootHtml+'\r\n--B--\r\n';
const revision=createHash("sha256").update(raw).digest("hex");
const body="MHTML 正文🙂";
function loss(){return {engine:"python-worker-html",engine_version:"0.1.1",params:{source_sha256:revision,mhtml:{schema:"archeaxis.mhtml-projection/v1",format:"mhtml",root_selection:"start-content-id",part_count:2,resource_count:1,resources:[{content_id:"<image>"}],root:{path:["mime-part-2"],content_id:"<root>",content_location:"javascript:SHOULD_NOT_RUN",media_type:"text/html",charset:"utf-8",decoded_bytes:Buffer.byteLength(rootHtml),decoded_sha256:createHash("sha256").update(rootHtml).digest("hex")}},worker_structure:[{kind:"mhtml_block",path:["mime-part-2","block-1"],char_start:0,char_end:Array.from(body).length}]},loss_note:"Only decoded root text; resource references are declarations, no execution or fetching."};}
const structure=[{kind:"line",path:["line-1"],char_start:0,char_end:Array.from(body).length}];
const source={source_id:"mhtml-source",source_revision:revision,sha256:revision,original_name:"saved.mhtml",imported_at:"2026-11-12"};
let previousScroll:typeof HTMLElement.prototype.scrollIntoView;
beforeEach(()=>{bridge.call.mockReset();vi.stubGlobal("crypto",webcrypto);vi.stubGlobal("__TAURI__",undefined);previousScroll=HTMLElement.prototype.scrollIntoView;HTMLElement.prototype.scrollIntoView=vi.fn();});
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllGlobals();HTMLElement.prototype.scrollIntoView=previousScroll;});

function savedTransport(receipt=loss()){
 bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>={})=>{
  if(op==="sources_list")return {sources:[source]};
  if(op==="documents_list")return {documents:[],next_cursor:null,snapshot_count:0};
  if(op==="source_original")return {source_id:source.source_id,name:source.original_name,sha256:revision,media_type:"multipart/related",content_base64:Buffer.from(raw).toString("base64")};
  if(op==="anchors_list")return {anchors:[]};
  if(op==="capabilities_list")return {};
  if(op==="source_jobs")return {source_id:source.source_id,jobs:[{job_id:"saved-mhtml",kind:"html",input_ref:source.source_id,state:"succeeded",attempt:1}],jobs_capped:false};
  if(op==="jobs_get")return {job_id:"saved-mhtml",kind:"html",input_ref:source.source_id,state:"succeeded",attempt:1,request_id:"saved-request"};
  if(op==="job_output")return outputReceipt(p.kind,p.kind==="text"?body:JSON.stringify(p.kind==="loss_report"?receipt:structure));
  if(op==="job_quality")return {job_id:"saved-mhtml",loss_count:2};
  if(op==="source_job_transform")return {source_id:source.source_id,job_id:"saved-mhtml",raw_sha256:revision,transform_id:1,content:body};
  throw new Error(`Unexpected mock operation: ${op}`);
 });
}

it("SIMULATED: formal source reader reopens MHTML body and MIME locations as inert text without executing another job",async()=>{
 savedTransport();const fetch=vi.fn();vi.stubGlobal("fetch",fetch);
 const view=render(<CanonicalLibrarySpace purpose="reader" initialSourceTarget={{source_id:source.source_id,source_revision:revision,sha256:revision}}/>);
 fireEvent.click(await screen.findByRole("button",{name:"读取 MHTML 正文与位置"}));
 expect(await screen.findByLabelText("Core 提取正文")).toHaveTextContent(body);
 expect(screen.getByRole("region",{name:"MHTML 正文根部件"})).toHaveTextContent("mime-part-2");
 expect(screen.getByText(/Content-Location 声明（未访问）/)).toHaveTextContent("javascript:SHOULD_NOT_RUN");
 fireEvent.click(screen.getByRole("button",{name:"预览所选引用"}));
 expect(await screen.findByLabelText("所选引用预览")).toHaveTextContent("mime-part-2 / block-1");
 expect(screen.getByLabelText("所选引用预览")).toHaveTextContent(body);
 expect(document.querySelector("iframe,img,a[href^='javascript:'],script[src]")).toBeNull();
 expect(fetch).not.toHaveBeenCalled();
 expect(bridge.call.mock.calls.some(([op])=>["job_enqueue","job_execute","anchor_create"].includes(op))).toBe(false);
 view.unmount();render(<JobContent sourceId={source.source_id} sourceRevision={revision} name="saved.mhtml" readOnly/>);
 expect(await screen.findByLabelText("Core 提取正文")).toHaveTextContent(body);
 expect(bridge.call.mock.calls.some(([op])=>["job_enqueue","job_execute"].includes(op))).toBe(false);
});

it.each(["source-drift","missing-mime-root","invalid-part-path"])("SIMULATED: %s receipt cannot publish MHTML text or position",async fault=>{
 const receipt=loss();
 if(fault==="source-drift")receipt.params.source_sha256="f".repeat(64);
 else if(fault==="missing-mime-root")receipt.params.mhtml.schema="unknown";
 else receipt.params.mhtml.root.path=["../../arbitrary"];
 savedTransport(receipt);
 render(<JobContent sourceId={source.source_id} sourceRevision={revision} name="saved.mht" readOnly/>);
 await screen.findByText("持久化结果读回未完成；不会自动重新执行任务。");
 expect(screen.queryByLabelText("Core 提取正文")).not.toBeInTheDocument();
 expect(screen.queryByRole("region",{name:"MHTML 正文根部件"})).not.toBeInTheDocument();
 expect(bridge.call.mock.calls.some(([op])=>op==="job_execute")).toBe(false);
});

it.each(["saved.mht","saved.MHTML"])("SIMULATED: %s dispatches the existing HTML route and keeps a refused root failure visible",async name=>{
 bridge.call.mockImplementation(jobContentCoreFixture(async(op,p)=>{
  if(op==="capabilities_list")return {};
  if(op==="source_jobs")return {source_id:source.source_id,jobs:[]};
  if(op==="job_enqueue")return {job_id:(p.body as Record<string,unknown>).job_id};
  if(op==="job_execute")return {};
  if(op==="jobs_get")return {state:"failed",error:"MHTML start root is missing or ambiguous"};
  throw new Error(`Unexpected mock operation: ${op}`);
 }));
 render(<JobContent sourceId={source.source_id} sourceRevision={revision} name={name}/>);
 fireEvent.click(await screen.findByRole("button",{name:"执行真实内容转换"}));
 await screen.findByText(/转换未完成或产物读取失败/);
 await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("job_enqueue",{body:{job_id:expect.any(String),kind:"html",input_ref:source.source_id}}));
 expect(screen.queryByLabelText("Core 提取正文")).not.toBeInTheDocument();
 expect(bridge.call.mock.calls.filter(([op])=>op==="job_execute")).toHaveLength(1);
});
