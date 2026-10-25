import { beforeEach, afterEach, expect, it, vi } from "vitest";
import { useState } from "react";
import { StitchResearchOutlet } from "../components/StitchWorkspaceChrome";
import { webcrypto } from "node:crypto";
import { documentRequestIdentity } from "../presentation/documentRequestIdentity";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CanonicalResearchSpace, parseResearch, type ResearchValue } from "../spaces/CanonicalResearchSpace";
import type { DocumentDto } from "../api/generated/core-contract";
import { DiagnosticConsole } from "../components/DiagnosticConsole";
import { resetDiagnostics } from "../presentation/diagnostics";
import { DocumentBusinessProvider, DocumentBusinessSessions } from "../workspace/documentSessions";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
type J=Record<string,any>;

it("ports the live bound materials without replacing the editor, saving, or retaining closed contents",async()=>{
 const research=(docs.get("doc_a")!.editor_json as J).attrs.archeaxis_research as ResearchValue;
 research.materials=[{id:"material_one",note:"原有材料",reference:{kind:"document",document_id:"doc_b",version:2}}];
 const before=structuredClone(research),located=vi.fn();
 function Harness(){const [host,setHost]=useState<HTMLDivElement|null>(null),[open,setOpen]=useState(true);return <StitchResearchOutlet.Provider value={{host:open?host:null,onLocate:located}}><button onClick={()=>setOpen(!open)}>切换资料窗</button><div aria-label="资料出口" ref={setHost}/><CanonicalResearchSpace/></StitchResearchOutlet.Provider>;}
 const view=render(<Harness/>);await openA();
 const editor=screen.getByRole("region",{name:"研究编辑区"}),question=screen.getByRole("textbox",{name:"研究问题"});
 const sidebar=screen.getByRole("complementary",{name:"相关资料"});
 expect(editor).not.toContainElement(sidebar);expect(sidebar.parentElement).toHaveAttribute("aria-label","资料出口");
 expect(sidebar).toHaveTextContent("版本 2");expect(screen.getAllByRole("complementary",{name:"相关资料"})).toHaveLength(1);
 fireEvent.click(within(sidebar).getByRole("button",{name:"定位相关材料 1"}));
 expect(document.activeElement).toHaveAttribute("data-research-material","material_one");expect(located).toHaveBeenCalledTimes(1);
 selectPane("overview");fireEvent.change(question,{target:{value:"仍在原编辑器中的草稿"}});
 selectPane("evidence");fireEvent.change(screen.getByRole("textbox",{name:"材料说明 1"}),{target:{value:"同步修改说明"}});
 expect(sidebar).toHaveTextContent("同步修改说明");expect(sidebar).toHaveTextContent("草稿有未保存修改");
 selectPane("overview");fireEvent.click(screen.getByRole("button",{name:"切换资料窗"}));expect(screen.queryByRole("complementary",{name:"相关资料"})).not.toBeInTheDocument();
 expect(question).toHaveValue("仍在原编辑器中的草稿");expect(screen.getByRole("region",{name:"研究编辑区"})).toBe(editor);
 fireEvent.click(screen.getByRole("button",{name:"切换资料窗"}));
 expect(screen.getByRole("textbox",{name:"研究问题"})).toBe(question);expect(screen.getByRole("complementary",{name:"相关资料"})).toHaveTextContent("同步修改说明");
 expect((docs.get("doc_a")!.editor_json as J).attrs.archeaxis_research).toEqual(before);expect(requests).toHaveLength(0);
 view.unmount();expect(screen.queryByRole("complementary",{name:"相关资料"})).not.toBeInTheDocument();
});

it("late verified original preserves editing focus and input after the request was started",async()=>{
 const raw=new TextEncoder().encode("verified original");
 const sha=Array.from(new Uint8Array(await webcrypto.subtle.digest("SHA-256",raw))).map(n=>n.toString(16).padStart(2,"0")).join("");
 const research=(docs.get("doc_a")!.editor_json as J).attrs.archeaxis_research as ResearchValue;
 research.materials=[{id:"material_focus",note:"原件",reference:{kind:"source",source_id:"source_actual",sha256:sha}}];
 let resolveOriginal!:(value:unknown)=>void;
 bridge.call.mockImplementation((op:string,p:J)=>op==="source_original"?new Promise(resolve=>{resolveOriginal=resolve;}):original(op,p));
 render(<CanonicalResearchSpace/>);await openA();
 selectPane("evidence");const button=screen.getByRole("button",{name:"读取校验原件"});button.focus();fireEvent.click(button);
 selectPane("overview");const question=screen.getByRole("textbox",{name:"研究问题"});question.focus();editQuestion("读取期间继续编辑");
 await act(async()=>resolveOriginal({source_id:"source_actual",name:"source.txt",media_type:"text/plain",sha256:sha,content_base64:btoa(String.fromCharCode(...raw))}));
 await screen.findByText("verified original");expect(question).toHaveFocus();expect(question).toHaveValue("读取期间继续编辑");expect(requests).toHaveLength(0);
});
const value=(question:string):ResearchValue=>({schema:"archeaxis.research/v1",question,materials:[],hypotheses:[],methods:[],experiments:[],counterevidence:[],conclusions:[],unresolved:[]});
function dto(id:string,question:string,version=1):DocumentDto{return {document_id:id,title:id,version,content_sha256:"a".repeat(64),source_id:null,source_revision:null,text_projection:question,blocks:[{block_id:`block_${id}`,kind:"paragraph",ordinal:0,node_json:{type:"paragraph"},text_projection:"body",codec_status:"known"}],editor_json:{type:"doc",attrs:{ownerUnknown:{raw:"未修改的外层载荷"},archeaxis_research:value(question)},content:[{type:"ownerUnknown",attrs:{block_id:`block_${id}`},payload:{raw:"未知块原文\r\n保留 "}}]}};}
let docs:Map<string,DocumentDto>,requests:J[],original:(op:string,p:J)=>Promise<unknown>,events:boolean[];
beforeEach(()=>{vi.stubGlobal("crypto",webcrypto);docs=new Map([["doc_a",dto("doc_a","A")],["doc_b",dto("doc_b","B")]]);requests=[];events=[];bridge.call.mockReset();original=async(op:string,p:J={})=>{
 if(op==="documents_list")return {documents:[...docs.values()],next_cursor:null,snapshot_count:docs.size};
 if(op==="sources_list")return {sources:[{source_id:"source_actual",source_revision:"b".repeat(64),sha256:"b".repeat(64),original_name:"真实来源.txt",imported_at:"fixture"}]};
 if(op==="document_get")return structuredClone(docs.get(p.document_id));
 if(op==="document_version")return dto(p.document_id,"历史原文",p.version);
 if(op==="search")return {items:[],transforms:[],count:0,transform_count:0,documents:[],document_count:0};
 if(op==="document_create"){requests.push(structuredClone(p));const id=await documentRequestIdentity(p.body.create_request_id);let d=docs.get(id);if(!d){d={...dto(id,""),title:p.body.title,editor_json:structuredClone(p.body.editor_json)};docs.set(d.document_id,d);}return structuredClone(d);}
 if(op==="document_draft"){requests.push(structuredClone(p));const old=docs.get(p.document_id)!;if(old.version!==p.body.expected_version)throw new Error("409");const d={...old,version:old.version+1,editor_json:structuredClone(p.body.editor_json)};docs.set(d.document_id,d);return structuredClone(d);}
 throw new Error(`unimplemented fixture operation ${op}`);
};bridge.call.mockImplementation(original);});
afterEach(()=>{resetDiagnostics();vi.restoreAllMocks();vi.unstubAllGlobals();});

it("keeps the research content landmark distinct from its Dockview host and explains the first saved artifact",async()=>{
 render(<div role="region" aria-label="研究空间"><CanonicalResearchSpace/></div>);
 await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("documents_list",{}));
 expect(screen.getAllByRole("region",{name:"研究空间"})).toHaveLength(1);
 expect(screen.getByRole("region",{name:"研究专题内容"})).toBeInTheDocument();
 expect(screen.getByText("第一次做研究：先比较一个具体问题")).toBeInTheDocument();
 expect(screen.getByText("保存在本地研究文档")).toBeInTheDocument(); expect(requests).toHaveLength(0);
});

it("offers an explicit retry of the same pending save without creating a second research request",async()=>{
 let fail=true;
 bridge.call.mockImplementation(async(op:string,p:J)=>{if(op==="document_create"&&fail){requests.push(structuredClone(p));throw new Error("receipt lost");}return original(op,p);});
 render(<CanonicalResearchSpace/>);editQuestion("小白使用中的第一份研究");
 fireEvent.click(screen.getByRole("button",{name:"保存研究草稿"}));
 const retry=await screen.findByRole("button",{name:"重试原保存请求"});
 const first=structuredClone(requests[0]); expect(screen.getByRole("textbox",{name:"研究问题"})).toHaveValue("小白使用中的第一份研究");
 fail=false; fireEvent.click(retry);
 await waitFor(()=>expect(requests).toHaveLength(2)); expect(requests[1]).toEqual(first);
 await waitFor(()=>expect(screen.queryByRole("button",{name:"重试原保存请求"})).not.toBeInTheDocument());
});

it("keeps public search preparation local and saves only an explicit unresolved plan",async()=>{
 render(<CanonicalResearchSpace/>);await openA();
 const panel=screen.getByRole("region",{name:"公开资料检索"});
 expect(within(panel).getByRole("textbox",{name:"公开检索关键词"})).toHaveValue("");
 expect(panel).toHaveTextContent("尚未检索公开资料");
 expect(within(panel).getByRole("button",{name:"检索公开资料"})).toBeDisabled();
 fireEvent.change(within(panel).getByRole("textbox",{name:"公开检索关键词"}),{target:{value:"间隔复习 证据"}});
 fireEvent.click(within(panel).getByRole("button",{name:"把检索计划加入未决草稿"}));
 expect(requests).toHaveLength(0);
 selectPane("notes");expect((screen.getByRole("textbox",{name:"未决 1"}) as HTMLTextAreaElement).value).toContain("间隔复习 证据");
 fireEvent.click(screen.getByRole("button",{name:"保存研究草稿"}));
 await waitFor(()=>expect(requests).toHaveLength(1));
 const saved=requests[0].body.editor_json.attrs.archeaxis_research;
 expect(saved.unresolved[0].references).toEqual([]);
 expect(saved.unresolved[0].text).toContain("未执行外部检索");
 expect(bridge.call.mock.calls.some(([op])=>op==="search"||String(op).includes("external"))).toBe(false);
});

it("keeps the saved quote readable and its complete fixed identity in diagnostics without changing the stored research",async()=>{
 resetDiagnostics();
 const research=(docs.get("doc_a")!.editor_json as J).attrs.archeaxis_research as ResearchValue;
 const reference={kind:"source" as const,source_id:"source_actual",sha256:"b".repeat(64)};
 const citation={schema:"archeaxis.research-citation/v1" as const,anchor_id:"anchor_private",source_sha256:"b".repeat(64),anchor_position_sha256:"c".repeat(64),quote:"原文甲😀\r\n乙仍保留",quote_sha256:"d".repeat(64),read_snapshot_sha256:"b".repeat(64)};
 research.materials=[{id:"material_private",note:"作者说明",reference,citation}];
 const stored=structuredClone(docs.get("doc_a"));
 const view=render(<><CanonicalResearchSpace/><DiagnosticConsole/></>);await openA();
 const region=screen.getByRole("region",{name:"研究编辑区"});
 expect(region.textContent).not.toMatch(/source_actual|anchor_private|b{64}|c{64}/);
 selectPane("evidence");const quote=within(region).getByRole("complementary",{name:"已保存版本的引文快照"});
 expect(quote.querySelector("blockquote")!.textContent).toBe(citation.quote);
 fireEvent.click(within(quote).getByRole("button",{name:"查看诊断详情：研究引文原始记录"}));
 expect(JSON.parse(view.container.querySelector(".diagnostic-console pre")!.textContent!)).toEqual({reference,citation});
 expect(docs.get("doc_a")).toEqual(stored);expect(requests).toHaveLength(0);
});

it("does not borrow a newer document title for an older fixed reference",async()=>{
 const latest=dto("doc_b","B",2);latest.title="只属于新版的标题";docs.set("doc_b",latest);
 const research=(docs.get("doc_a")!.editor_json as J).attrs.archeaxis_research as ResearchValue;
 research.hypotheses=[{id:"h",text:"作者假设",references:[{kind:"document",document_id:"doc_b",version:1,block_id:"block_private"}]}];
 const open=vi.fn();render(<CanonicalResearchSpace onOpenDocument={open}/>);await openA();
 selectPane("notes");const section=screen.getByRole("region",{name:"假设"});
 expect(section).toHaveTextContent("文档名称尚未读取 · 版本 1");
 expect(section.textContent).not.toMatch(/只属于新版的标题|doc_b|block_private/);
 fireEvent.click(within(section).getByRole("button",{name:"打开固定版本"}));
 expect(open).toHaveBeenCalledWith("doc_b",1,"block_private");expect(requests).toHaveLength(0);
});

it("keeps original reference records accessible when another view owns the write lease",async()=>{
 resetDiagnostics();
 const sessions=new DocumentBusinessSessions("workspace","initial");sessions.acquire("doc_a","writer");
 const research=(docs.get("doc_a")!.editor_json as J).attrs.archeaxis_research as ResearchValue;
 research.materials=[{id:"m",note:"只读材料",reference:{kind:"source",source_id:"source_actual",sha256:"b".repeat(64)}}];
 const view=render(<><DocumentBusinessProvider sessions={sessions} viewId="reader"><CanonicalResearchSpace/></DocumentBusinessProvider><DiagnosticConsole/></>);
 await openA();expect(screen.getByRole("button",{name:"保存研究草稿"})).toBeDisabled();
 const button=screen.getByRole("button",{name:"查看诊断详情：只读研究引用记录"});expect(button).toBeEnabled();fireEvent.click(button);
 expect(JSON.parse(view.container.querySelector(".diagnostic-console pre")!.textContent!)).toEqual({base_document:{document_id:"doc_a",version:1},draft:research,draft_dirty:false,save_pending:false});
 expect(sessions.session("doc_a").owner).toBe("writer");expect(requests).toHaveLength(0);
});

async function replayFixture(status:"CURRENT"|"STALE"="CURRENT") {
 const reference={kind:"source" as const,source_id:"source_actual",sha256:"b".repeat(64)};
 const position=JSON.stringify({type:"text",start:0,end:6});
 const digest=async(text:string)=>Array.from(new Uint8Array(await webcrypto.subtle.digest("SHA-256",new TextEncoder().encode(text)))).map(v=>v.toString(16).padStart(2,"0")).join("");
 const citation={schema:"archeaxis.research-citation/v1" as const,anchor_id:"anchor_replay",source_sha256:reference.sha256,anchor_position_sha256:await digest(position),quote:"原文",quote_sha256:await digest("原文"),read_snapshot_sha256:reference.sha256};
 const result={source_id:reference.source_id,anchor_id:citation.anchor_id,status,reason:status==="CURRENT"?"MATCH":"REVISION_CHANGED",source_revision:reference.sha256,current_source_revision:status==="CURRENT"?reference.sha256:"c".repeat(64),position,scope:"locator_provenance_only"};
 (docs.get("doc_a")!.editor_json as J).attrs.archeaxis_research.materials=[{id:"m",note:"作者引文",reference,citation}];
 return {reference,citation,result};
}

it.each(["CURRENT","STALE"] as const)("explains citation location %s in Chinese while preserving the complete resolution",async status=>{
 const fixture=await replayFixture(status);
 bridge.call.mockImplementation((op:string,p:J)=>op==="anchor_resolve"?Promise.resolve(structuredClone(fixture.result)):original(op,p));
 const view=render(<><CanonicalResearchSpace/><DiagnosticConsole/></>);await openA();
 selectPane("evidence");fireEvent.click(screen.getByRole("button",{name:"重新核验引文定位"}));
 await screen.findByText(status==="CURRENT"?"引文定位仍有效；仅核对定位，不表示内容已证实。":"引文定位已过期；历史快照仍保留，可核对当前原件。");
 const quote=screen.getByRole("complementary",{name:"已保存版本的引文快照"});
 expect(quote.textContent).not.toContain(status);
 fireEvent.click(within(quote).getByRole("button",{name:"查看诊断详情：引文定位核验记录"}));
 expect(JSON.parse(view.container.querySelector(".diagnostic-console pre")!.textContent!)).toEqual({...fixture,observed_at:expect.any(String),outcome:"read"});
 expect(requests).toHaveLength(0);
});

it("does not let an old citation replay overwrite a newer research save outcome",async()=>{
 const fixture=await replayFixture();let finish!:(value:unknown)=>void;
 bridge.call.mockImplementation((op:string,p:J)=>op==="anchor_resolve"?new Promise(resolve=>{finish=resolve;}):original(op,p));
 render(<CanonicalResearchSpace/>);await openA();selectPane("evidence");fireEvent.click(screen.getByRole("button",{name:"重新核验引文定位"}));
 editQuestion("核验期间的新研究输入");await save();await act(async()=>{finish(fixture.result);});
 expect(screen.getByRole("status",{name:"研究操作状态"})).toHaveTextContent("研究草稿已保存并读回；未变为核验或采用状态。");
 expect(screen.getByRole("textbox",{name:"研究问题"})).toHaveValue("核验期间的新研究输入");
 selectPane("evidence");expect(screen.queryByRole("button",{name:"查看诊断详情：引文定位核验记录"})).not.toBeInTheDocument();
 expect(requests).toHaveLength(1);
});

it("keeps identically titled local knowledge results distinct without exposing their raw identifiers",async()=>{
 const items=[{knowledge_id:"knowledge_private_1",head:"同名材料",status:"candidate",active:false},{knowledge_id:"knowledge_private_2",head:"同名材料",status:"candidate",active:false}];
 bridge.call.mockImplementation((op:string,p:J)=>op==="search"?Promise.resolve({items,transforms:[],count:2,transform_count:0}):original(op,p));
 const view=render(<><CanonicalResearchSpace/><DiagnosticConsole/></>);await openA();selectPane("evidence");fireEvent.click(screen.getByRole("button",{name:"添加材料或待整理说明"}));
 const dialog=await screen.findByRole("dialog",{name:"选择研究引用"});fireEvent.click(within(dialog).getByRole("button",{name:"检索本地知识"}));
 const second=await within(dialog).findByRole("button",{name:"选择本地知识结果 2 · 同名材料"});
 expect(dialog.textContent).not.toMatch(/knowledge_private_[12]/);
 fireEvent.click(within(dialog).getByRole("button",{name:"查看诊断详情：本地知识结果 2"}));
 expect(JSON.parse(view.container.querySelector(".diagnostic-console pre")!.textContent!)).toEqual(items[1]);
 fireEvent.click(second);fireEvent.click(within(dialog).getByRole("button",{name:"添加所选引用"}));await save();
 expect(requests[0].body.editor_json.attrs.archeaxis_research.materials[0].reference).toEqual({kind:"knowledge",knowledge_id:"knowledge_private_2"});
});

it.each(["empty","failed"])("distinguishes a confirmed empty local search from %s",async mode=>{
 bridge.call.mockImplementation((op:string,p:J)=>op==="search"?(mode==="failed"?Promise.reject(new Error("unavailable")):Promise.resolve({items:[],transforms:[],count:0,transform_count:0})):original(op,p));
 render(<CanonicalResearchSpace/>);await openA();selectPane("evidence");fireEvent.click(screen.getByRole("button",{name:"添加材料或待整理说明"}));
 const dialog=await screen.findByRole("dialog",{name:"选择研究引用"});
 expect(within(dialog).getByText("尚未检索本地知识。")).toBeInTheDocument();
 fireEvent.click(within(dialog).getByRole("button",{name:"检索本地知识"}));
 await within(dialog).findByText(mode==="failed"?"本地检索失败，是否存在结果仍未知；可重新检索。":"本地检索完成：0 项结果。");
 if(mode==="failed")expect(within(dialog).queryByText("本地检索完成：0 项结果。")).not.toBeInTheDocument();
 expect(requests).toHaveLength(0);
});

it("does not present a delayed local search as results for a newly edited query",async()=>{
 const item={knowledge_id:"knowledge_old_query",head:"旧问题的材料",status:"candidate",active:false};let finish!:(value:unknown)=>void;
 bridge.call.mockImplementation((op:string,p:J)=>op==="search"?new Promise(resolve=>{finish=resolve;}):original(op,p));
 render(<CanonicalResearchSpace/>);await openA();selectPane("evidence");fireEvent.click(screen.getByRole("button",{name:"添加材料或待整理说明"}));
 const dialog=await screen.findByRole("dialog",{name:"选择研究引用"}),input=within(dialog).getByLabelText("研究本地知识检索");
 fireEvent.change(input,{target:{value:"旧问题"}});fireEvent.click(within(dialog).getByRole("button",{name:"检索本地知识"}));fireEvent.change(input,{target:{value:"新问题"}});
 await act(async()=>{finish({items:[item],transforms:[],count:1,transform_count:0});});
 expect(within(dialog).getByText("以下是上次关键词“旧问题”的结果；输入已变化，请重新检索。")).toBeInTheDocument();
 expect(within(dialog).getByRole("button",{name:"选择本地知识结果 1 · 旧问题的材料"})).toBeDisabled();
 expect(within(dialog).getByRole("button",{name:"添加所选引用"})).toBeDisabled();expect(requests).toHaveLength(0);
});

it("retains a missing locator response without reporting a valid citation location",async()=>{
 const fixture=await replayFixture(),missing={...fixture.result,status:"MISSING",reason:"ANCHOR_NOT_FOUND",position:null,source_revision:null};
 bridge.call.mockImplementation((op:string,p:J)=>op==="anchor_resolve"?Promise.resolve(missing):original(op,p));
 const view=render(<><CanonicalResearchSpace/><DiagnosticConsole/></>);await openA();selectPane("evidence");fireEvent.click(screen.getByRole("button",{name:"重新核验引文定位"}));
 await screen.findByText("引文当前定位未确认；历史快照仍保留。");expect(screen.queryByText("引文定位仍有效；仅核对定位，不表示内容已证实。")).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole("button",{name:"查看诊断详情：引文定位核验记录"}));
 expect(JSON.parse(view.container.querySelector(".diagnostic-console pre")!.textContent!)).toEqual({reference:fixture.reference,citation:fixture.citation,result:missing,observed_at:expect.any(String),outcome:"failed"});
 expect(requests).toHaveLength(0);
});

it.each(["cancel","escape","add"])("returns the reference picker to its actual keyboard opener after %s",async action=>{
 render(<CanonicalResearchSpace/>);await openA();const user=userEvent.setup();
 selectPane("evidence");const opener=screen.getByRole("button",{name:"添加材料或待整理说明"});opener.focus();await user.keyboard("{Enter}");
 const dialog=await screen.findByRole("dialog",{name:"选择研究引用"});
 if(action==="escape")await user.keyboard("{Escape}");
 else if(action==="cancel")await user.click(within(dialog).getByRole("button",{name:"取消引用选择"}));
 else{await within(dialog).findByRole("option",{name:/真实来源/});await user.selectOptions(within(dialog).getByLabelText("引用原件"),"source_actual");await user.click(within(dialog).getByRole("button",{name:"添加所选引用"}));}
 await waitFor(()=>expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
 expect(opener).toHaveFocus();expect(requests).toHaveLength(0);
 selectPane("overview");expect(screen.getByRole("textbox",{name:"研究问题"})).toHaveValue("A");
});
it.each(["cancel","escape","switch"])("restores keyboard focus and preserves dirty research through switch dialog %s",async action=>{
 render(<CanonicalResearchSpace/>);await openA();editQuestion("未保存研究");const user=userEvent.setup();
 const opener=screen.getByRole("button",{name:"doc_b · 版本 1"});opener.focus();await user.keyboard("{Enter}");
 const dialog=await screen.findByRole("dialog",{name:"保留研究草稿并切换"});
 if(action==="escape")await user.keyboard("{Escape}");
 else await user.click(within(dialog).getByRole("button",{name:action==="cancel"?"取消切换":"保留草稿并切换"}));
 await waitFor(()=>expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
 expect(opener).toHaveFocus();expect(requests).toHaveLength(0);
 await waitFor(()=>expect(screen.getByRole("textbox",{name:"研究问题"})).toHaveValue(action==="switch"?"B":"未保存研究"));
});

it.each([false,true])("captures exact original quote into version metadata; mismatched anchor=%s retains notes",async mismatch=>{
 const raw=new TextEncoder().encode("甲😀\r\n乙");
 const hash=async(bytes:Uint8Array)=>Array.from(new Uint8Array(await webcrypto.subtle.digest("SHA-256",bytes.slice().buffer))).map(v=>v.toString(16).padStart(2,"0")).join("");
 const revision=await hash(raw),quote="甲😀\r\n";let position="";
 const r=(docs.get("doc_a")!.editor_json as J).attrs.archeaxis_research as ResearchValue;
 r.materials=[{id:"material_quote",note:"作者材料说明",reference:{kind:"source",source_id:"source_actual",sha256:revision}}];
 bridge.call.mockImplementation(async(op:string,p:J)=>{
  if(op==="source_original")return {source_id:"source_actual",sha256:revision,name:"quote.txt",media_type:"text/plain",content_base64:btoa(String.fromCharCode(...raw))};
  if(op==="anchor_create"){position=JSON.stringify({...JSON.parse(p.body.position),checksum:p.body.checksum,location_status:"located"});return {anchor_id:"anchor_quote",source_id:mismatch?"other":"source_actual",source_revision:revision,position,location_status:"located"};}
  if(op==="anchor_resolve")return {anchor_id:"anchor_quote",source_id:"source_actual",source_revision:revision,current_source_revision:revision,status:"CURRENT",position,scope:"locator_provenance_only"};
  return original(op,p);
 });
 render(<CanonicalResearchSpace onOpenReference={vi.fn()}/>);await openA();
 selectPane("evidence");fireEvent.click(screen.getByRole("button",{name:"摘录材料 1原文"}));
 const area=await screen.findByRole("textbox",{name:"选择原件引用文字"}) as HTMLTextAreaElement;
 area.focus();area.setSelectionRange(0,4);fireEvent.keyUp(area,{key:"Shift"});
 fireEvent.click(screen.getByRole("button",{name:"引用所选原文"}));
 if(mismatch){await screen.findByText("原件范围引用未确认，请保留原件后重试。");}
 else{await screen.findByText("原件引文快照已放入草稿；保存后随研究版本保留，不代表内容已证实。");}
 await save();const stored=requests[0].body.editor_json.attrs.archeaxis_research.materials[0];
 expect(stored.note).toBe("作者材料说明");
 if(mismatch)expect(stored.citation).toBeUndefined();
 else{expect(stored.citation).toEqual({schema:"archeaxis.research-citation/v1",anchor_id:"anchor_quote",source_sha256:revision,anchor_position_sha256:await hash(new TextEncoder().encode(position)),quote,quote_sha256:await hash(new TextEncoder().encode(quote)),read_snapshot_sha256:revision});expect(screen.getByRole("complementary",{name:"已保存版本的引文快照"})).toHaveTextContent("甲😀");}
 expect(bridge.call.mock.calls.map(c=>c[0])).not.toContain("knowledge_review");
});

function selectPane(pane:"overview"|"evidence"|"notes"|"conclusions"){
 const names={overview:/^概览$/,evidence:/^证据对比 /,notes:/^研究笔记 /,conclusions:/^结论 /};
 const button=within(screen.getByRole("navigation",{name:"研究内容导航"})).getByRole("button",{name:names[pane]});
 if(button.getAttribute("aria-pressed")!=="true")fireEvent.click(button);expect(button).toHaveAttribute("aria-pressed","true");
}
function openResearchTools(){
 const summary=screen.getByText("研究文档与版本",{selector:"summary"});
 if(!summary.parentElement!.hasAttribute("open"))fireEvent.click(summary);
 expect(summary.parentElement).toHaveAttribute("open");
}

async function openA(){openResearchTools();fireEvent.click(await screen.findByRole("button",{name:"doc_a · 版本 1"}));await waitFor(()=>expect(screen.getByRole("textbox",{name:"研究问题"})).toHaveValue("A"));}
function editQuestion(text:string){selectPane("overview");fireEvent.change(screen.getByRole("textbox",{name:"研究问题"}),{target:{value:text}});}
async function save(){fireEvent.click(screen.getByRole("button",{name:"保存研究草稿"}));await screen.findByText("研究草稿已保存并读回；未变为核验或采用状态。");}
it("stores incomplete counterevidence and unresolved research without question, materials, course or adoption prerequisite",async()=>{
 render(<CanonicalResearchSpace/>);selectPane("notes");fireEvent.click(screen.getByRole("button",{name:"添加反证"}));fireEvent.change(screen.getByLabelText("反证 1"),{target:{value:"反例\n尚未查证"}});fireEvent.click(screen.getByRole("button",{name:"添加未决"}));fireEvent.change(screen.getByLabelText("未决 1"),{target:{value:"实验未做"}});await save();const stored=requests[0].body.editor_json.attrs.archeaxis_research;expect(stored.question).toBe("");expect(stored.materials).toEqual([]);expect(stored.counterevidence[0]).toMatchObject({text:"反例\n尚未查证",references:[]});expect(stored.unresolved[0].text).toBe("实验未做");expect(bridge.call.mock.calls.map(c=>c[0])).not.toContain("knowledge_review");selectPane("overview");expect(screen.getByText(/公开检索需明确输入关键词，多步自动研究当前未接通/)).toBeInTheDocument();
});
it("retains Chinese composition and all envelope/body unknown data through research edits and save",async()=>{
 const view=render(<CanonicalResearchSpace/>);await openA();const area=screen.getByRole("textbox",{name:"研究问题"});fireEvent.compositionStart(area);editQuestion("中文输入\n第二行 ");fireEvent.keyDown(area,{key:"Enter",isComposing:true});fireEvent.compositionEnd(area);document.documentElement.dataset.aaosTheme="white";view.rerender(<CanonicalResearchSpace/>);expect(area).toHaveValue("中文输入\n第二行 ");await save();expect(requests[0].body.expected_version).toBe(1);expect(requests[0].body.editor_json.attrs.ownerUnknown).toEqual({raw:"未修改的外层载荷"});expect(requests[0].body.editor_json.content).toEqual((dto("doc_a","A").editor_json as J).content);
});
it("lost create acknowledgement retries exact frozen request while later content remains dirty",async()=>{
 let first=true;bridge.call.mockImplementation(async(op:string,p:J)=>{const result=await original(op,p);if(op==="document_create"&&first){first=false;throw new Error("lost ack");}return result;});render(<CanonicalResearchSpace/>);editQuestion("FIRST");fireEvent.click(screen.getByRole("button",{name:"保存研究草稿"}));await screen.findByRole("alert");editQuestion("LATER");fireEvent.click(screen.getByRole("button",{name:"重试冻结研究保存"}));await screen.findByText("发送时的研究版本已读回；随后编辑仍未保存。");expect(requests).toHaveLength(2);expect(requests[0]).toEqual(requests[1]);expect(requests[0].body.create_request_id).toMatch(/^research_/);expect(docs.size).toBe(3);expect(screen.getByRole("textbox",{name:"研究问题"})).toHaveValue("LATER");await save();expect(requests[2].body.expected_version).toBe(1);expect(requests[2].body.editor_json.attrs.archeaxis_research.question).toBe("LATER");
});
it("late save receipt never replaces text edited after dispatch",async()=>{
 let resolve!:(value:unknown)=>void;bridge.call.mockImplementation(async(op:string,p:J)=>{const result=await original(op,p);if(op==="document_draft")await new Promise(r=>{resolve=r;});return result;});render(<CanonicalResearchSpace/>);await openA();editQuestion("SENT");fireEvent.click(screen.getByRole("button",{name:"保存研究草稿"}));await waitFor(()=>expect(requests).toHaveLength(1));editQuestion("LATER");await act(async()=>{resolve(null);});await screen.findByText("发送时的研究版本已读回；随后编辑仍未保存。");expect(screen.getByRole("textbox",{name:"研究问题"})).toHaveValue("LATER");
});
it("keeps dirty buffers through cancelled and confirmed object switching",async()=>{
 render(<CanonicalResearchSpace/>);await openA();editQuestion("UNSAVED A");fireEvent.click(screen.getByRole("button",{name:"doc_b · 版本 1"}));fireEvent.click(screen.getByRole("button",{name:"取消切换"}));expect(screen.getByRole("textbox",{name:"研究问题"})).toHaveValue("UNSAVED A");fireEvent.click(screen.getByRole("button",{name:"doc_b · 版本 1"}));fireEvent.click(screen.getByRole("button",{name:"保留草稿并切换"}));await waitFor(()=>expect(screen.getByRole("textbox",{name:"研究问题"})).toHaveValue("B"));fireEvent.click(screen.getByRole("button",{name:"doc_a · 版本 1"}));expect(screen.getByRole("textbox",{name:"研究问题"})).toHaveValue("UNSAVED A");
});
it("unknown research envelope remains complete readonly and cannot silently drop unknown fields in a rewrite",async()=>{
 const invalid=dto("doc_bad","original");(invalid.editor_json as J).attrs.archeaxis_research.future={source:"must survive"};docs.set("doc_bad",invalid);render(<CanonicalResearchSpace/>);openResearchTools();fireEvent.click(await screen.findByRole("button",{name:"doc_bad · 版本 1"}));await screen.findByText("不支持的研究属性保持完整原文，只读不转换。");expect(screen.getByRole("button",{name:"保存研究草稿"})).toBeDisabled();expect(requests).toEqual([]);expect((docs.get("doc_bad")!.editor_json as J).attrs.archeaxis_research.future).toEqual({source:"must survive"});
});
it("pending material input guards save, history and switch; cancellation does not clear existing content dirty",async()=>{
 const listener=(event:Event)=>events.push((event as CustomEvent<boolean>).detail);window.addEventListener("archeaxis-draft-dirty",listener);try{render(<CanonicalResearchSpace/>);await openA();editQuestion("CONTENT DIRTY");const saveButton=screen.getByRole("button",{name:"保存研究草稿"}),historyButton=screen.getByRole("button",{name:"读取研究历史"});selectPane("evidence");fireEvent.click(screen.getByRole("button",{name:"添加材料或待整理说明"}));const dialog=await screen.findByRole("dialog",{name:"选择研究引用"});fireEvent.change(within(dialog).getByLabelText("待整理材料说明"),{target:{value:"未选择出处"}});expect(events.at(-1)).toBe(true);fireEvent.click(saveButton);expect(requests).toHaveLength(0);fireEvent.click(historyButton);expect(bridge.call.mock.calls.map(c=>c[0])).not.toContain("document_version");fireEvent.click(within(dialog).getByRole("button",{name:"取消引用选择"}));expect(events.at(-1)).toBe(true);selectPane("overview");expect(screen.getByRole("textbox",{name:"研究问题"})).toHaveValue("CONTENT DIRTY");}finally{window.removeEventListener("archeaxis-draft-dirty",listener);}
});
it("an unbound material note can be preserved as unresolved draft without fabricating a reference",async()=>{
 render(<CanonicalResearchSpace/>);selectPane("evidence");fireEvent.click(screen.getByRole("button",{name:"添加材料或待整理说明"}));const dialog=await screen.findByRole("dialog",{name:"选择研究引用"});fireEvent.change(within(dialog).getByLabelText("待整理材料说明"),{target:{value:"材料只记了题目，出处待补"}});fireEvent.click(within(dialog).getByRole("button",{name:"无来源说明先保留为未决草稿"}));selectPane("notes");expect(screen.getByRole("textbox",{name:"未决 1"})).toHaveValue("材料只记了题目，出处待补");await save();expect(requests[0].body.editor_json.attrs.archeaxis_research.materials).toEqual([]);expect(requests[0].body.editor_json.attrs.archeaxis_research.unresolved[0].references).toEqual([]);
});
it("pins selected actual document version and block and opens it through exact callback",async()=>{
 const d=docs.get("doc_a")!;const r=(d.editor_json as J).attrs.archeaxis_research as ResearchValue;r.materials=[{id:"material_a",note:"绑定版本",reference:{kind:"document",document_id:"doc_b",version:1,block_id:"block_doc_b"}}];const open=vi.fn();render(<CanonicalResearchSpace onOpenDocument={open}/>);await openA();selectPane("evidence");fireEvent.click(screen.getByRole("button",{name:"打开固定版本"}));expect(open).toHaveBeenCalledWith("doc_b",1,"block_doc_b");expect(bridge.call.mock.calls.map(c=>c[0])).not.toContain("knowledge_review");
});
it("conclusion sources and basis remain separate in UI and frozen payload",async()=>{
 render(<CanonicalResearchSpace/>);selectPane("conclusions");fireEvent.click(screen.getByRole("button",{name:"添加结论"}));fireEvent.change(screen.getByLabelText("结论 1"),{target:{value:"仅为作者结论"}});fireEvent.click(screen.getByRole("button",{name:"为结论 1添加来源"}));let dialog=await screen.findByRole("dialog",{name:"选择研究引用"});await waitFor(()=>expect(within(dialog).getByRole("option",{name:/真实来源/})).toBeInTheDocument());fireEvent.change(within(dialog).getByLabelText("引用原件"),{target:{value:"source_actual"}});fireEvent.click(within(dialog).getByRole("button",{name:"添加所选引用"}));fireEvent.click(screen.getByRole("button",{name:"为结论 1添加依据"}));dialog=await screen.findByRole("dialog",{name:"选择研究引用"});fireEvent.change(within(dialog).getByLabelText("引用文档"),{target:{value:"doc_b"}});await within(dialog).findByText(/将绑定 doc_b · 版本 1/);fireEvent.click(within(dialog).getByRole("button",{name:"添加所选引用"}));await save();const c=requests[0].body.editor_json.attrs.archeaxis_research.conclusions[0];expect(c.sources).toEqual([{kind:"source",source_id:"source_actual",sha256:"b".repeat(64)}]);expect(c.basis).toEqual([{kind:"document",document_id:"doc_b",version:1,block_id:null}]);expect(screen.getByRole("region",{name:"结论 1来源"})).toBeInTheDocument();expect(screen.getByRole("region",{name:"结论 1依据"})).toBeInTheDocument();
});
it("409 and list failure remain explicit errors while preserving author content",async()=>{
 bridge.call.mockImplementation(async(op:string,p:J)=>{if(op==="document_draft")throw new Error("409");return original(op,p);});render(<CanonicalResearchSpace/>);await openA();editQuestion("未丢中文");fireEvent.click(screen.getByRole("button",{name:"保存研究草稿"}));await screen.findByRole("alert");expect(screen.getByRole("textbox",{name:"研究问题"})).toHaveValue("未丢中文");expect(screen.getByRole("button",{name:"重试冻结研究保存"})).toBeInTheDocument();
});
it("strict research parser rejects unknown fields and bad refs but accepts empty incomplete sections",()=>{
 const v=value("");expect(parseResearch(v)).toBe(v);expect(parseResearch({...v,verified:true})).toBeNull();expect(parseResearch({...v,materials:[{id:"m",note:"note",reference:{kind:"source",source_id:"s",sha256:"bad"}}]})).toBeNull();expect(parseResearch({...v,hypotheses:[{id:"a",text:"candidate",references:[],score:100}]})).toBeNull();expect(parseResearch({...v,conclusions:[{id:"x",text:"draft",sources:[],basis:[]},{id:"x",text:"duplicate",sources:[],basis:[]}]})).toBeNull();
});

it("lost draft acknowledgement reconciles committed exact version without a second write or losing later edits",async()=>{
 let first=true;bridge.call.mockImplementation(async(op:string,p:J)=>{const result=await original(op,p);if(op==="document_draft"&&first){first=false;throw new Error("lost ack");}return result;});render(<CanonicalResearchSpace/>);await openA();editQuestion("SENT V2");fireEvent.click(screen.getByRole("button",{name:"保存研究草稿"}));await screen.findByRole("alert");editQuestion("LATER V3");fireEvent.click(screen.getByRole("button",{name:"核对最新保存版本"}));await screen.findByText("发送时的研究版本已读回；随后编辑仍未保存。");expect(requests).toHaveLength(1);expect(docs.get("doc_a")!.version).toBe(2);expect(screen.getByRole("textbox",{name:"研究问题"})).toHaveValue("LATER V3");await save();expect(requests[1].body.expected_version).toBe(2);
});
it("unified pinned reference callback receives source and immutable knowledge identities while preserving dirty research",async()=>{
 const r=(docs.get("doc_a")!.editor_json as J).attrs.archeaxis_research as ResearchValue;r.materials=[{id:"m",note:"原件",reference:{kind:"source",source_id:"source_actual",sha256:"b".repeat(64)}}];r.hypotheses=[{id:"h",text:"待验证",references:[{kind:"knowledge",knowledge_id:"knowledge_version_1"}]}];const open=vi.fn();render(<CanonicalResearchSpace onOpenReference={open}/>);await openA();editQuestion("未保存草稿");selectPane("evidence");fireEvent.click(screen.getByRole("button",{name:"读取校验原件"}));selectPane("notes");fireEvent.click(screen.getByRole("button",{name:"打开不变知识版本"}));selectPane("overview");expect(open.mock.calls).toEqual([[{kind:"source",source_id:"source_actual",sha256:"b".repeat(64)}],[{kind:"knowledge",knowledge_id:"knowledge_version_1"}]]);expect(screen.getByRole("textbox",{name:"研究问题"})).toHaveValue("未保存草稿");expect(requests).toHaveLength(0);
});

it("parallel local search cannot release document reference pending or add an earlier source selection",async()=>{
 let completeSearch!:(v:unknown)=>void,completeDocument!:(v:unknown)=>void;bridge.call.mockImplementation((op:string,p:J)=>op==="search"?new Promise(resolve=>{completeSearch=resolve;}):op==="document_get"&&p.document_id==="doc_b"?new Promise(resolve=>{completeDocument=resolve;}):original(op,p));render(<CanonicalResearchSpace/>);await openA();selectPane("evidence");fireEvent.click(screen.getByRole("button",{name:"添加材料或待整理说明"}));const dialog=await screen.findByRole("dialog",{name:"选择研究引用"});await within(dialog).findByRole("option",{name:/真实来源/});fireEvent.change(within(dialog).getByLabelText("引用原件"),{target:{value:"source_actual"}});fireEvent.click(within(dialog).getByRole("button",{name:"检索本地知识"}));fireEvent.change(within(dialog).getByLabelText("引用文档"),{target:{value:"doc_b"}});await act(async()=>{completeSearch({items:[],transforms:[],count:0,transform_count:0});});expect(within(dialog).getByRole("button",{name:"添加所选引用"})).toBeDisabled();expect(within(dialog).queryByText(/将绑定 source_actual/)).not.toBeInTheDocument();await act(async()=>{completeDocument(dto("doc_b","B"));});await within(dialog).findByText(/将绑定 doc_b · 版本 1/);fireEvent.click(within(dialog).getByRole("button",{name:"添加所选引用"}));await save();expect(requests[0].body.editor_json.attrs.archeaxis_research.materials[0].reference).toEqual({kind:"document",document_id:"doc_b",version:1,block_id:null});
});
it("out of order historical reads keep the most recently requested version readonly",async()=>{
 docs.set("doc_a",dto("doc_a","A",2));const replies=new Map<number,(v:unknown)=>void>();bridge.call.mockImplementation((op:string,p:J)=>op==="document_version"?new Promise(resolve=>{replies.set(p.version,resolve);}):original(op,p));render(<CanonicalResearchSpace/>);openResearchTools();fireEvent.click(await screen.findByRole("button",{name:"doc_a · 版本 2"}));await waitFor(()=>expect(screen.getByRole("textbox",{name:"研究问题"})).toHaveValue("A"));fireEvent.click(screen.getByRole("button",{name:"读取研究历史"}));fireEvent.change(screen.getByLabelText("研究历史版本"),{target:{value:"2"}});fireEvent.click(screen.getByRole("button",{name:"读取研究历史"}));await act(async()=>{replies.get(2)!(dto("doc_a","历史二",2));});await screen.findByRole("heading",{name:"doc_a · 版本 2 · 只读"});await act(async()=>{replies.get(1)!(dto("doc_a","历史一",1));});expect(screen.getByRole("heading",{name:"doc_a · 版本 2 · 只读"})).toBeInTheDocument();expect(screen.queryByRole("heading",{name:"doc_a · 版本 1 · 只读"})).not.toBeInTheDocument();expect(screen.getByRole("textbox",{name:"研究问题"})).toHaveValue("A");
});
it("history response arriving after a new edit never changes the draft into a readonly history mode",async()=>{
 let complete!:(v:unknown)=>void;bridge.call.mockImplementation((op:string,p:J)=>op==="document_version"?new Promise(resolve=>{complete=resolve;}):original(op,p));render(<CanonicalResearchSpace/>);await openA();fireEvent.click(screen.getByRole("button",{name:"读取研究历史"}));editQuestion("读取之后的新输入");await act(async()=>{complete(dto("doc_a","迟到历史",1));});expect(screen.queryByRole("complementary",{name:"只读文档"})).not.toBeInTheDocument();expect(screen.getByRole("textbox",{name:"研究问题"})).toHaveValue("读取之后的新输入");expect(screen.getByRole("button",{name:"保存研究草稿"})).toBeEnabled();
});
it("late fallback original failures cannot overwrite a later reference picker state",async()=>{
 const r=(docs.get("doc_a")!.editor_json as J).attrs.archeaxis_research as ResearchValue;r.materials=[{id:"m",note:"原件",reference:{kind:"source",source_id:"source_actual",sha256:"b".repeat(64)}}];let rejectOriginal!:(v:unknown)=>void;bridge.call.mockImplementation((op:string,p:J)=>op==="source_original"?new Promise((_,reject)=>{rejectOriginal=reject;}):original(op,p));render(<CanonicalResearchSpace/>);await openA();selectPane("evidence");fireEvent.click(screen.getByRole("button",{name:"读取校验原件"}));selectPane("evidence");fireEvent.click(screen.getByRole("button",{name:"添加材料或待整理说明"}));await screen.findByRole("dialog",{name:"选择研究引用"});await act(async()=>{rejectOriginal(new Error("late original failure"));});expect(screen.queryByText("原件读取或内容指纹核对失败，未显示未经核对的内容。")).not.toBeInTheDocument();
});

it.each(["document_id","title","source_id"])("rejects wrong create ACK %s even when its v1 research envelope exactly matches the frozen request",async(field)=>{
 bridge.call.mockImplementation(async(op:string,p:J)=>{const result=await original(op,p);if(op!=="document_create")return result;return {...result as J,[field]:field==="document_id"?"wrong_identical_document":field==="title"?"wrong title":"source_actual"};});render(<CanonicalResearchSpace/>);editQuestion("必须绑定发送身份");fireEvent.click(screen.getByRole("button",{name:"保存研究草稿"}));await screen.findByRole("alert");expect(screen.getByRole("button",{name:"重试冻结研究保存"})).toBeInTheDocument();expect(screen.getByRole("textbox",{name:"研究问题"})).toHaveValue("必须绑定发送身份");expect(requests).toHaveLength(1);expect(bridge.call.mock.calls.filter(c=>c[0]==="document_get")).toHaveLength(0);expect(screen.queryByText("研究草稿已保存并读回；未变为核验或采用状态。")).not.toBeInTheDocument();
});

it("an earlier object open cannot change the active research while current document save is awaiting ACK",async()=>{
 let completeOpen!:(v:unknown)=>void,completeSave!:(v:unknown)=>void;bridge.call.mockImplementation(async(op:string,p:J)=>{if(op==="document_get"&&p.document_id==="doc_b")return new Promise(resolve=>{completeOpen=resolve;});const result=await original(op,p);if(op==="document_draft")await new Promise(resolve=>{completeSave=resolve;});return result;});render(<CanonicalResearchSpace/>);await openA();fireEvent.click(screen.getByRole("button",{name:"doc_b · 版本 1"}));fireEvent.click(screen.getByRole("button",{name:"保存研究草稿"}));await waitFor(()=>expect(requests).toHaveLength(1));await act(async()=>{completeOpen(dto("doc_b","B"));});expect(screen.getByRole("textbox",{name:"研究问题"})).toHaveValue("A");await act(async()=>{completeSave(null);});await screen.findByText("研究草稿已保存并读回；未变为核验或采用状态。");expect(screen.getByRole("textbox",{name:"研究问题"})).toHaveValue("A");expect(docs.get("doc_a")!.version).toBe(2);
});

it("history shows the immutable quote even after a newer research edit",async()=>{
 const historic=dto("doc_a","A",1);
 const research=(historic.editor_json as J).attrs.archeaxis_research as ResearchValue;
 research.materials=[{id:"historical_material",note:"旧材料",reference:{kind:"source",source_id:"source_actual",sha256:"b".repeat(64)},citation:{schema:"archeaxis.research-citation/v1",anchor_id:"anchor_history",source_sha256:"b".repeat(64),anchor_position_sha256:"c".repeat(64),quote:"旧版本原文\r\n仍保留",quote_sha256:"d".repeat(64),read_snapshot_sha256:"b".repeat(64)}}];
 docs.set("doc_a",structuredClone(historic));
 bridge.call.mockImplementation((op:string,p:J)=>op==="document_version"?Promise.resolve(structuredClone(historic)):original(op,p));
 const view=render(<><CanonicalResearchSpace/><DiagnosticConsole/></>);await openA();editQuestion("新版研究问题");await save();
 fireEvent.change(screen.getByLabelText("研究历史版本"),{target:{value:"1"}});
 fireEvent.click(screen.getByRole("button",{name:"读取研究历史"}));
 const history=await screen.findByRole("complementary",{name:"只读文档"});
 expect(within(history).getByRole("complementary",{name:"已保存版本的引文快照"})).toHaveTextContent("旧版本原文");
 expect(within(history).queryByText(/anchor_history/)).not.toBeInTheDocument();
 fireEvent.click(within(history).getByRole("button",{name:"查看诊断详情：研究引文原始记录"}));
 expect(JSON.parse(view.container.querySelector(".diagnostic-console pre")!.textContent!)).toEqual({reference:research.materials[0].reference,citation:research.materials[0].citation});
 expect(within(history).getByRole("button",{name:"重新核验引文定位"})).toBeEnabled();
 expect(screen.getByRole("textbox",{name:"研究问题"})).toHaveValue("新版研究问题");
});


it("uses only bound materials in the Stitch sidebar and focuses evidence without changing or saving identities",async()=>{
 const research=(docs.get("doc_a")!.editor_json as J).attrs.archeaxis_research as ResearchValue;
 research.materials=[
  {id:"material_one",note:"作者材料甲",reference:{kind:"document",document_id:"doc_b",version:1}},
  {id:"material_two",note:"作者材料乙",reference:{kind:"document",document_id:"doc_b",version:2}},
 ];
 const before=structuredClone(research);render(<CanonicalResearchSpace/>);await openA();
 const sidebar=screen.getByRole("complementary",{name:"相关资料"});
 expect(within(sidebar).getByRole("heading",{name:"相关资料 (2)"})).toBeInTheDocument();
 expect(sidebar).toHaveTextContent("版本 1");expect(sidebar).toHaveTextContent("版本 2");
 fireEvent.click(within(sidebar).getByRole("button",{name:"定位相关材料 2"}));
 expect(document.activeElement).toHaveAttribute("data-research-material","material_two");
 expect(within(sidebar).getByRole("button",{name:"定位相关材料 2"})).toHaveAttribute("aria-pressed","true");
 expect((docs.get("doc_a")!.editor_json as J).attrs.archeaxis_research).toEqual(before);expect(requests).toHaveLength(0);
 fireEvent.click(within(screen.getByRole("navigation",{name:"研究内容导航"})).getByRole("button",{name:"研究笔记 (0)"}));
 expect(document.activeElement).toHaveAttribute("data-research-pane","notes");
 selectPane("overview");fireEvent.change(screen.getByRole("textbox",{name:"研究问题"}),{target:{value:"未保存的问题"}});
 expect(screen.getByRole("status",{name:"研究草稿状态"})).toHaveTextContent("草稿有未保存修改");
 expect(requests).toHaveLength(0);expect(sidebar).not.toHaveTextContent("94%");
});

it("shows exactly one authoring pane and preserves its DOM and unsaved inputs while navigating",async()=>{
 const view=render(<CanonicalResearchSpace/>);await openA();
 const region=screen.getByRole("region",{name:"研究编辑区"});
 const panes=Array.from(region.querySelectorAll<HTMLElement>("[data-research-pane]")).filter(p=>["overview","evidence","notes","conclusions"].includes(p.dataset.researchPane!));
 expect(panes).toHaveLength(4);
 const onlyVisible=(name:string)=>{expect(panes.filter(p=>!p.hidden).map(p=>p.dataset.researchPane)).toEqual([name]);for(const p of panes)if(p.dataset.researchPane===name)expect(p).toBeVisible();else expect(p).not.toBeVisible();};
 onlyVisible("overview");const question=screen.getByRole("textbox",{name:"研究问题"});editQuestion("切换后仍保留的问题");
 selectPane("notes");onlyVisible("notes");expect(screen.queryByRole("textbox",{name:"研究问题"})).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole("button",{name:"添加假设"}));const note=screen.getByRole("textbox",{name:"假设 1"});fireEvent.change(note,{target:{value:"切换后仍保留的假设"}});
 selectPane("conclusions");onlyVisible("conclusions");fireEvent.click(screen.getByRole("button",{name:"添加结论"}));const conclusion=screen.getByRole("textbox",{name:"结论 1"});fireEvent.change(conclusion,{target:{value:"切换后仍保留的结论"}});
 selectPane("evidence");onlyVisible("evidence");expect(screen.queryByRole("textbox",{name:"假设 1"})).not.toBeInTheDocument();expect(screen.queryByRole("textbox",{name:"结论 1"})).not.toBeInTheDocument();
 for(const pane of panes){expect(view.container.contains(pane)).toBe(true);expect(region.querySelector('[data-research-pane="'+pane.dataset.researchPane+'"]')).toBe(pane);}
 selectPane("overview");onlyVisible("overview");expect(screen.getByRole("textbox",{name:"研究问题"})).toBe(question);expect(question).toHaveValue("切换后仍保留的问题");
 selectPane("notes");onlyVisible("notes");expect(screen.getByRole("textbox",{name:"假设 1"})).toBe(note);expect(note).toHaveValue("切换后仍保留的假设");
 selectPane("conclusions");onlyVisible("conclusions");expect(screen.getByRole("textbox",{name:"结论 1"})).toBe(conclusion);expect(conclusion).toHaveValue("切换后仍保留的结论");
 expect(requests).toHaveLength(0);
});

it("expands only the selected material while keeping other evidence summaries and draft inputs",async()=>{
 const research=(docs.get("doc_a")!.editor_json as J).attrs.archeaxis_research as ResearchValue;
 research.materials=[{id:"m_one",note:"第一项材料摘要",reference:{kind:"document",document_id:"doc_b",version:1}},{id:"m_two",note:"第二项材料摘要",reference:{kind:"document",document_id:"doc_b",version:2}}];
 const stored=structuredClone(research);render(<CanonicalResearchSpace/>);await openA();selectPane("evidence");
 const first=screen.getByRole("textbox",{name:"材料说明 1"});expect(first).toBeVisible();expect(screen.queryByRole("textbox",{name:"材料说明 2"})).not.toBeInTheDocument();
 const secondButton=screen.getByRole("button",{name:"材料 2 · 选择对照"});expect(secondButton).toBeVisible();expect(secondButton.closest("li")).toHaveTextContent("第二项材料摘要");
 fireEvent.change(first,{target:{value:"第一项未保存输入"}});fireEvent.click(secondButton);
 const second=screen.getByRole("textbox",{name:"材料说明 2"});expect(second).toBeVisible();expect(screen.queryByRole("textbox",{name:"材料说明 1"})).not.toBeInTheDocument();expect(first).toBeInTheDocument();expect(first).not.toBeVisible();
 fireEvent.change(second,{target:{value:"第二项未保存输入"}});fireEvent.click(screen.getByRole("button",{name:"材料 1 · 选择对照"}));
 expect(screen.getByRole("textbox",{name:"材料说明 1"})).toBe(first);expect(first).toHaveValue("第一项未保存输入");expect(second).toBeInTheDocument();expect(second).not.toBeVisible();
 fireEvent.click(screen.getByRole("button",{name:"材料 2 · 选择对照"}));expect(screen.getByRole("textbox",{name:"材料说明 2"})).toBe(second);expect(second).toHaveValue("第二项未保存输入");
 expect(research).toEqual(stored);expect(requests).toHaveLength(0);
});
