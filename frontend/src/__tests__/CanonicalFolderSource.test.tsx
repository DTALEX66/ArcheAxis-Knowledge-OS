import {beforeEach,expect,it,vi} from "vitest";
import {act,fireEvent,render,screen,waitFor} from "@testing-library/react";
import {createHash,webcrypto} from "node:crypto";
import {CanonicalLibrarySpace} from "../spaces/CanonicalLibrarySpace";
const fixture=vi.hoisted(()=>({call:vi.fn(),revision:""}));
vi.mock("../api/core",()=>({coreCommand:fixture.call}));
vi.mock("../components/FolderIngest",()=>({FolderIngest:({onOpenSource}:{onOpenSource?:(id:string,job?:string,revision?:string)=>void})=><><button onClick={()=>onOpenSource?.("src_folder","job_folder",fixture.revision)}>真实成员来源入口</button>{["a","b"].map(id=><button key={id} onClick={()=>onOpenSource?.(`src_${id}`,`job_${id}`,fixture.revision)}>成员 {id}</button>)}</>}));
vi.mock("../components/JobContent",()=>({JobContent:({pinnedJobId}:{pinnedJobId?:string})=><p>固定作业 {pinnedJobId}</p>}));
vi.mock("../components/ContainerMemberChain",()=>({ContainerMemberChain:()=>null}));
vi.mock("../components/PdfPageRecognition",()=>({PdfPageRecognition:()=>null}));
vi.mock("../components/OriginalTextCitation",()=>({OriginalTextCitation:()=>null}));
const text="Public folder source";
const hash=createHash("sha256").update(text).digest("hex");
const source={source_id:"src_folder",source_revision:hash,sha256:hash,original_name:"folder.md",imported_at:"now"};
beforeEach(()=>{vi.stubGlobal("crypto",webcrypto);fixture.revision=hash;fixture.call.mockReset();fixture.call.mockImplementation(async(op:string)=>{
 if(op==="sources_list")return {sources:[]};
 if(op==="documents_list")return {documents:[{document_id:"must_not_auto_pick",source_id:"src_folder",source_revision:hash,title:"same source",version:1,content_sha256:hash}],next_cursor:null,snapshot_count:1};
 if(op==="source_get")return source;
 if(op==="source_original")return {source_id:"src_folder",sha256:hash,name:"folder.md",media_type:"text/markdown",content_base64:Buffer.from(text).toString("base64")};
 if(op==="anchors_list")return {anchors:[]};
 throw new Error(op);
});});
it("SYNTHETIC: opens actual member outside capped list with exact source revision and pinned job, without guessing a Document",async()=>{
 render(<CanonicalLibrarySpace/>);await screen.findByText("same source · 文档");fireEvent.click(screen.getByRole("button",{name:"真实成员来源入口"}));
 await waitFor(()=>expect(screen.getByLabelText("原件正文")).toHaveTextContent(text));
 expect(fixture.call).toHaveBeenCalledWith("source_get",{source_id:"src_folder"});
 expect(screen.getByText("固定作业 job_folder")).toBeVisible();
 expect(fixture.call.mock.calls.some(([op])=>op==="document_get"||op==="document_create")).toBe(false);
});
it("SYNTHETIC: refuses same-name source substitution before reading bytes",async()=>{
 fixture.revision="f".repeat(64);render(<CanonicalLibrarySpace/>);await screen.findByText("same source · 文档");fireEvent.click(screen.getByRole("button",{name:"真实成员来源入口"}));
 await screen.findByText(/所选来源身份未读回/);expect(fixture.call.mock.calls.some(([op])=>op==="source_original"||op==="document_get")).toBe(false);
});

function deferred<T>(){let resolve!:(value:T)=>void;const promise=new Promise<T>(done=>{resolve=done;});return {promise,resolve};}
const member=(id:string)=>({...source,source_id:`src_${id}`,original_name:`${id}.md`});
const original=(id:string)=>({source_id:`src_${id}`,sha256:hash,name:`${id}.md`,media_type:"text/markdown",content_base64:Buffer.from(text).toString("base64")});
for(const first of ["a","b"] as const)it(`SYNTHETIC: last selected B owns metadata/original/job when ${first.toUpperCase()} metadata returns first`,async()=>{
 const a=deferred<ReturnType<typeof member>>(),b=deferred<ReturnType<typeof member>>();const normal=fixture.call.getMockImplementation()!;
 fixture.call.mockImplementation((op:string,p:Record<string,unknown>)=>op==="source_get"?(p.source_id==="src_a"?a.promise:b.promise):op==="source_original"?Promise.resolve(original(p.source_id==="src_a"?"a":"b")):normal(op,p));
 render(<CanonicalLibrarySpace/>);await screen.findByText("same source · 文档");
 fireEvent.click(screen.getByRole("button",{name:"成员 a"}));fireEvent.click(screen.getByRole("button",{name:"成员 b"}));
 await act(async()=>{(first==="a"?a:b).resolve(member(first));});
 await act(async()=>{(first==="a"?b:a).resolve(member(first==="a"?"b":"a"));});
 await waitFor(()=>expect(screen.getByText("固定作业 job_b")).toBeVisible());
 expect(screen.getByRole("heading",{name:"b.md"})).toBeVisible();
 expect(screen.queryByText("固定作业 job_a")).toBeNull();
 expect(fixture.call.mock.calls.filter(([op,p])=>op==="source_original"&&p.source_id==="src_a")).toHaveLength(0);
 expect(fixture.call.mock.calls.filter(([op,p])=>op==="source_original"&&p.source_id==="src_b")).toHaveLength(1);
});
it("SYNTHETIC: older original bytes returning after the next selection cannot replace its source or job",async()=>{
 const bytesA=deferred<ReturnType<typeof original>>();const normal=fixture.call.getMockImplementation()!;
 fixture.call.mockImplementation((op:string,p:Record<string,unknown>)=>op==="source_get"?Promise.resolve(member(p.source_id==="src_a"?"a":"b")):op==="source_original"?(p.source_id==="src_a"?bytesA.promise:Promise.resolve(original("b"))):normal(op,p));
 render(<CanonicalLibrarySpace/>);await screen.findByText("same source · 文档");fireEvent.click(screen.getByRole("button",{name:"成员 a"}));
 await waitFor(()=>expect(fixture.call).toHaveBeenCalledWith("source_original",{source_id:"src_a"}));
 fireEvent.click(screen.getByRole("button",{name:"成员 b"}));await screen.findByText("固定作业 job_b");
 await act(async()=>bytesA.resolve(original("a")));
 expect(screen.getByRole("heading",{name:"b.md"})).toBeVisible();expect(screen.queryByText("固定作业 job_a")).toBeNull();
});
