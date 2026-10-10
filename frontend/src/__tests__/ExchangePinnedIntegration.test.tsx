import { outputReceipt } from "./fixtures/jobContentCoreFixture";
import { webcrypto } from "node:crypto";
import { cleanup,fireEvent,render,screen } from "@testing-library/react";
import { afterEach,beforeEach,describe,expect,it,vi } from "vitest";
import { CanonicalExchangeSpace } from "../spaces/CanonicalExchangeSpace";
const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
vi.mock("../components/FolderIngest",()=>({FolderIngest:({onOpenSource}:{onOpenSource:(s:string,j:string)=>void})=><button onClick={()=>onOpenSource("source-1","success-older-than-50")}>打开实际批量成功结果</button>}));
vi.mock("../spaces/CanonicalTeachingSpace",()=>({CanonicalTeachingSpace:()=>null}));
let sha:string;const raw=new TextEncoder().encode("原始字节，非转换正文");
const status=()=>({job_id:"success-older-than-50",input_ref:"source-1",kind:"text",state:"succeeded",attempt:4,request_id:"frozen-request-4"});
let override:Record<string,unknown>={};
beforeEach(async()=>{vi.stubGlobal("crypto",webcrypto);sha=Buffer.from(await webcrypto.subtle.digest("SHA-256",raw)).toString("hex");override={};bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>={})=>{
 if(op==="sources_list")return {sources:[{source_id:"source-1",source_revision:sha,sha256:sha,original_name:"report.txt",imported_at:"now"}]};
 if(op==="documents_list")return {documents:[],snapshot_count:0,next_cursor:null};
 if(op==="source_original")return {source_id:"source-1",sha256:sha,name:"report.txt",media_type:"text/plain",content_base64:Buffer.from(raw).toString("base64")};
 if(op==="capabilities_list")return {};
 if(op==="job_execution_status")return {...status(),...override};
 if(op==="jobs_get")return status();
 if(op==="job_output")return outputReceipt(p.kind,p.kind==="text"?"已保存转换正文":p.kind==="loss_report"?JSON.stringify({engine:"SIMULATED text",engine_version:"fixture",params:{},loss_note:"SIMULATED"}):"[]");
 if(op==="job_quality")return {job_id:"success-older-than-50",engine:"SIMULATED text",engine_version:"fixture",loss_count:0};
 if(op==="source_job_transform")return {source_id:"source-1",job_id:"success-older-than-50",raw_sha256:sha,transform_id:9,content:"已保存转换正文"};
 throw new Error(`unexpected ${op}`);
 });});
afterEach(()=>{cleanup();vi.clearAllMocks();vi.unstubAllGlobals();});
describe("SIMULATED source→successful pinned job actual React integration",()=>{
 it("reads exact pinned output through actual JobContent, independently of recent50, with separate downloads",async()=>{render(<CanonicalExchangeSpace/>);fireEvent.click(screen.getByRole("button",{name:"打开实际批量成功结果"}));expect(await screen.findByLabelText("Core 提取正文")).toHaveTextContent("已保存转换正文");expect(screen.getByRole("button",{name:"下载核验原字节"})).toBeEnabled();for(const name of ["正文.txt","结构.json","损失.json","引擎回执.json"])expect(screen.getByRole("button",{name:`下载派生${name}`})).toBeEnabled();expect(bridge.call).toHaveBeenCalledWith("job_execution_status",{job_id:"success-older-than-50"});expect(bridge.call).toHaveBeenCalledWith("source_job_transform",{source_id:"source-1",job_id:"success-older-than-50"});expect(screen.queryByRole("button",{name:"执行真实内容转换"})).toBeNull();expect(screen.queryByLabelText("知识候选正文")).toBeNull();expect(bridge.call.mock.calls.some(([op])=>["source_jobs","job_execute","job_enqueue"].includes(op))).toBe(false);});
 it.each([{attempt:3},{input_ref:"other-source"},{request_id:"other-request"}])("wrong pinned identity %j preserves raw original and refuses derived output",async value=>{override=value;render(<CanonicalExchangeSpace/>);fireEvent.click(screen.getByRole("button",{name:"打开实际批量成功结果"}));await screen.findByText(/持久化结果读回未完成/);expect(screen.getByRole("button",{name:"下载核验原字节"})).toBeEnabled();expect(screen.queryByLabelText("Core 提取正文")).toBeNull();expect(screen.queryByRole("button",{name:"下载派生正文.txt"})).toBeNull();});
});
