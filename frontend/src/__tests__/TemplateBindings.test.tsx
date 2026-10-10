import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { DocumentDto } from "../api/generated/core-contract";
import { DocumentEditor } from "../components/DocumentEditor";
import { TemplateLauncher, TemplateWorkspace } from "../templates/TemplateWorkspace";
import { backlinks, binding, collection, createTemplate, loadTemplateDocuments, resolveReference, saveBinding } from "../templates/bindings";
import { DISCIPLINES, TEMPLATES } from "../templates/disciplines";
import { documentRequestIdentity } from "../presentation/documentRequestIdentity";

const api=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:api.call}));
const metadata={schema:"archeaxis.template/v1" as const,template_id:"T1",discipline_id:"math",fields:{status:"unevaluated"},references:[],learning_item_key:null};
function doc(id:string):DocumentDto{return {document_id:id,title:id,version:1,source_id:null,source_revision:null,content_sha256:"hash",editor_json:{type:"doc",attrs:{archeaxis_template:metadata},content:[{type:"paragraph",attrs:{block_id:"p1"},content:[{type:"text",text:"Hypothesis, unevaluated"}]}]},text_projection:"Hypothesis, unevaluated",blocks:[{block_id:"p1",kind:"paragraph",ordinal:0,node_json:{},text_projection:"Hypothesis, unevaluated",codec_status:"known"}]};}
let stored:DocumentDto[]=[];
beforeEach(()=>{stored=[doc("target")];api.call.mockReset();api.call.mockImplementation(async(operation:string,payload:Record<string,unknown>={})=>{
  if(operation==="documents_list")return {documents:stored,next_cursor:null,snapshot_count:stored.length};
  if(operation==="document_get"||operation==="document_version"){const value=stored.find(d=>d.document_id===payload.document_id);if(!value)throw new Error("not found");return structuredClone(value);}
  if(operation==="document_create"){const body=payload.body as Record<string,unknown>;const id=await documentRequestIdentity(String(body.create_request_id));const value=normalize({...doc(id),title:body.title as string,editor_json:body.editor_json});stored.push(value);return structuredClone(value);}
  if(operation==="document_draft"){const body=payload.body as Record<string,unknown>;const index=stored.findIndex(d=>d.document_id===payload.document_id);if(stored[index].version!==body.expected_version)throw new Error("version conflict");stored[index]=normalize({...stored[index],editor_json:body.editor_json,version:stored[index].version+1});return structuredClone(stored[index]);}
  throw new Error(operation);
});});
function normalize(value:DocumentDto):DocumentDto {
  const editor=structuredClone(value.editor_json) as {content:Array<{type:string;attrs?:Record<string,unknown>}>};
  editor.content.forEach((node,index)=>{node.attrs={...node.attrs,block_id:node.attrs?.block_id??`generated_${index}`};});
  return {...value,editor_json:editor,content_sha256:"a".repeat(64),blocks:editor.content.map((node,index)=>({block_id:String(node.attrs!.block_id),kind:node.type,ordinal:index,node_json:node,text_projection:"fixture",codec_status:"known"}))};
}
describe("SIMULATED host binding; Core persistence is separately integrated",()=>{
  it("28 discipline packages use exactly three templates and each has a representative activity",()=>{
    expect(DISCIPLINES).toHaveLength(28);expect(new Set(DISCIPLINES.map(d=>d.id)).size).toBe(28);expect(TEMPLATES.map(t=>t.id)).toEqual(["T1","T2","T3"]);
    for(const pack of DISCIPLINES)expect([pack.fields.length,pack.relations.length,pack.sample.length,pack.activity.length,pack.evaluation.length].every(n=>n>0)).toBe(true);
  });
  it("saves only through finite document commands and preserves content plus expected version",async()=>{
    const created=await createTemplate("T2","physics");const next={...binding(created)!,fields:{...binding(created)!.fields,单位:"s"}};
    const saved=await saveBinding(created,next);expect(saved.version).toBe(2);expect(binding(saved)?.fields.单位).toBe("s");
    expect(api.call).toHaveBeenCalledWith("document_draft",expect.objectContaining({body:expect.objectContaining({expected_version:1})}));
    expect((saved.editor_json as {content:unknown[]}).content).toEqual((created.editor_json as {content:unknown[]}).content);
    await expect(createTemplate("missing","math")).rejects.toThrow("未知");
  });
  it("resolves immutable block text and rejects wrong versions or absent blocks before any save",async()=>{
    const reference={document_id:"target",version:1,block_id:"p1",relation:"supports",x:20,y:20};
    expect((await resolveReference(reference)).text).toBe("Hypothesis, unevaluated");
    await expect(resolveReference({...reference,version:2})).rejects.toThrow("版本不匹配");
    await expect(saveBinding(doc("target"),{...metadata,references:[{...reference,block_id:"missing"}]})).rejects.toThrow("引用块未找到");
    expect(api.call.mock.calls.some(([name])=>name==="document_draft")).toBe(false);
  });
  it("builds backlinks, relation totals and collection status from saved canonical snapshots",()=>{
    const source=doc("source");source.editor_json={...(source.editor_json as object),attrs:{archeaxis_template:{...metadata,references:[{document_id:"target",version:1,block_id:"p1",relation:"supports",x:20,y:20}]}}};
    expect(backlinks([source,doc("target")],"target")[0].context).toContain("Hypothesis");
    expect(collection([source,doc("target")],"math").relations).toBe(1);expect(collection([source],"physics").members).toHaveLength(0);
  });
  it("creates, saves a reference, opens its real object and reloads its persisted binding",async()=>{
    const onOpen=vi.fn();const view=render(<TemplateWorkspace onOpen={onOpen}/>);
    await screen.findByRole("button",{name:"target · v1"});fireEvent.click(screen.getByRole("button",{name:"创建学科对象"}));
    await screen.findByRole("button",{name:"数学 · 知识网络 · v1"});
    fireEvent.change(screen.getByLabelText("关系目标"),{target:{value:"target"}});fireEvent.change(screen.getByLabelText("目标块 ID（可空）"),{target:{value:"p1"}});
    fireEvent.click(screen.getByRole("button",{name:"加入版本绑定引用"}));await screen.findByRole("button",{name:/推导自 → target/});
    fireEvent.click(screen.getByRole("button",{name:"保存模板属性与关系"}));await screen.findByText(/模板对象与属性已保存并完整读回/);
    fireEvent.click(screen.getByRole("button",{name:/推导自 → target/}));await screen.findByLabelText("引用原文");fireEvent.click(screen.getByRole("button",{name:"打开引用对象当前正文"}));expect(onOpen).toHaveBeenCalledWith("target");
    view.unmount();render(<TemplateWorkspace onOpen={onOpen}/>);fireEvent.click(await screen.findByRole("button",{name:"数学 · 知识网络 · v2"}));await screen.findByRole("button",{name:/推导自 → target/});
  });
  it("Tiptap round-trip keeps root template metadata while editing ordinary text",async()=>{
    const content=doc("editor").editor_json as Parameters<typeof DocumentEditor>[0]["content"];
    const onSave=vi.fn(async(next:typeof content)=>({content:next,version:2}));
    render(<DocumentEditor content={content} version={1} onSave={onSave}/>);
    fireEvent.click(screen.getByRole("button",{name:"保存草稿"}));
    await waitFor(()=>expect(onSave).toHaveBeenCalled());expect(onSave.mock.calls[0][0].attrs?.archeaxis_template).toEqual(metadata);
  });
  it("invalid saved metadata does not break derived views or alter the original document",()=>{
    const invalid=doc("bad");invalid.editor_json={type:"doc",attrs:{archeaxis_template:{...metadata,references:[null]}}};
    expect(()=>binding(invalid)).toThrow("模板配置无效");
    expect(collection([invalid],"math").members).toHaveLength(0);
    expect(backlinks([invalid],"target")).toEqual([]);
    expect((invalid.editor_json as {attrs:{archeaxis_template:{references:unknown[]}}}).attrs.archeaxis_template.references).toEqual([null]);
  });
  it("declining to discard dirty template properties keeps the launcher open",async()=>{
    const confirm=vi.spyOn(window,"confirm").mockReturnValue(false);
    const view=render(<TemplateLauncher onOpen={vi.fn()}/>);
    const details=view.container.querySelector("details")!;
    details.open=true;fireEvent(details,new Event("toggle"));
    fireEvent.click(await screen.findByRole("button",{name:"target · v1"}));
    fireEvent.change(screen.getByLabelText("status"),{target:{value:"draft"}});
    details.open=false;fireEvent(details,new Event("toggle"));
    expect(confirm).toHaveBeenCalled();expect(details.open).toBe(true);
    expect(screen.getByLabelText("status")).toHaveValue("draft");confirm.mockRestore();
  });
  it("a collapsed launcher renders no workspace and no live region of its own",async()=>{
    // The library page already owns one outcome region, so an always-mounted workspace would put a
    // second status element on the surface before the user asked for anything.
    const view=render(<TemplateLauncher onOpen={vi.fn()}/>);
    expect(view.container.querySelector("section[aria-label='学科模板工作区']")).toBeNull();
    await new Promise(r=>setTimeout(r,0));
    expect(view.container.querySelectorAll('[role="status"],[role="alert"],[aria-live]:not([aria-live="off"])')).toHaveLength(0);
  });
  it("names an empty template collection instead of leaving a blank list",async()=>{
    api.call.mockImplementation(async(operation:string)=>{
      if(operation==="documents_list")return {documents:[],next_cursor:null,snapshot_count:0};
      throw new Error(operation);
    });
    render(<TemplateWorkspace onOpen={vi.fn()}/>);
    const state=await screen.findByText("尚无已保存的模板对象；选择学科与模板后创建第一个。");
    expect(state.closest("nav")).toHaveAttribute("aria-label","已保存模板");
    expect(state.hasAttribute("role")).toBe(false);
    // The count is the read that happened, and the invalid-metadata advisory is not noise here.
    expect(screen.getByText(/本次完整读回 0 个文档对象，其中 0 个带可解析模板属性/)).toBeInTheDocument();
    expect(screen.queryByText(/无效模板属性不参与集合汇总/)).toBeNull();
  });
  it("reports a failed template read as a failed read, not as an empty collection",async()=>{
    // "Core answered nothing" does not establish "there are no template objects"; claiming the
    // second from the first is the fabrication this pins out, and listing the unread document is
    // the fabrication in the other direction.
    api.call.mockImplementation(async(operation:string)=>{
      if(operation==="documents_list")return {documents:[{document_id:"doc_x",source_id:null,source_revision:null,title:"未读回的文档",version:1,content_sha256:"h"}],next_cursor:null,snapshot_count:1};
      throw new Error("本地核心未能完成 document_get（503）。");
    });
    render(<TemplateWorkspace onOpen={vi.fn()}/>);
    const announced=await screen.findByText("模板对象读取失败，请重试。");
    expect(announced).toHaveAttribute("role","status");
    const state=await screen.findByText(/此前对象仅供保留草稿，当前集合是否为空未知/);
    expect(state.hasAttribute("role")).toBe(false);
    expect(screen.queryByText(/尚无已保存的模板对象/)).toBeNull();
    expect(screen.queryByText(/本次读回/)).toBeNull();
    expect(screen.queryByRole("button",{name:"未读回的文档 · v1"})).toBeNull();
  });
  it("only warns about invalid template attributes when some document actually failed to parse",async()=>{
    stored=[doc("target"),(()=>{const bad=doc("broken");bad.editor_json={type:"doc",attrs:{archeaxis_template:{schema:"other/v1"}}};return bad;})()];
    render(<TemplateWorkspace onOpen={vi.fn()}/>);
    await screen.findByRole("button",{name:"target · v1"});
    expect(screen.getByText(/无效模板属性不参与集合汇总/)).toBeInTheDocument();
    expect(screen.getByText(/本次完整读回 2 个文档对象，其中 1 个带可解析模板属性/)).toBeInTheDocument();
    expect(screen.queryByText(/尚无已保存的模板对象/)).toBeNull();
  });
});

describe("complete template document membership",()=>{
  it("filters a long list without changing complete collection or cross-page backlinks",async()=>{
    stored=Array.from({length:101},(_,i)=>doc(`d${i}`));
    stored[100].editor_json={...(stored[100].editor_json as object),attrs:{archeaxis_template:{...metadata,references:[{document_id:"d0",version:1,block_id:"p1",relation:"supports",x:20,y:20}]}}};
    render(<TemplateWorkspace onOpen={vi.fn()}/>);
    await screen.findByRole("button",{name:"d100 · v1"});
    fireEvent.change(screen.getByLabelText("查找已保存模板"),{target:{value:"d0"}});
    expect(screen.queryByRole("button",{name:"d100 · v1"})).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button",{name:"d0 · v1"}));
    expect(screen.getByRole("heading",{name:"d0"})).toHaveFocus();
    expect(screen.getByText(/当前学科集合 101 个对象，1 条关系/)).toBeInTheDocument();
    expect(screen.getByRole("button",{name:"d100"})).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("查找已保存模板"),{target:{value:"missing-title"}});
    expect(screen.getByText(/没有匹配的模板标题/)).toBeInTheDocument();
    expect(screen.getByText(/本次完整读回 101 个/)).toBeInTheDocument();
  });
  it("withdraws complete counts and backlinks when a later refresh fails",async()=>{
    render(<TemplateWorkspace onOpen={vi.fn()}/>);
    fireEvent.click(await screen.findByRole("button",{name:"target · v1"}));
    expect(screen.getByText(/本次完整读回 1 个/)).toBeInTheDocument();
    const original=api.call.getMockImplementation()!;
    api.call.mockImplementation(async(op:string,payload:Record<string,unknown>={})=>{
      if(op==="documents_list")throw new Error("later page unavailable");
      return original(op,payload);
    });
    fireEvent.click(screen.getByRole("button",{name:"创建学科对象"}));
    await screen.findByText("集合刷新未完成，当前反向引用未知。");
    expect(screen.queryByText(/本次完整读回/)).not.toBeInTheDocument();
    expect(screen.queryByText(/当前学科集合 1 个/)).not.toBeInTheDocument();
  });
  it.each([101,501])("reads all %i objects and includes the final cross-page relationship",async count=>{
    stored=Array.from({length:count},(_,i)=>doc(`d${i}`));
    const last=stored[count-1];last.editor_json={...(last.editor_json as object),attrs:{archeaxis_template:{...metadata,references:[{document_id:"d0",version:1,block_id:"p1",relation:"supports",x:20,y:20}]}}};
    const original=api.call.getMockImplementation()!;
    api.call.mockImplementation(async(op:string,payload:Record<string,unknown>={})=>{
      if(op==="documents_list"){const offset=payload.cursor?500:0;return {documents:stored.slice(offset,offset+500),snapshot_count:count,next_cursor:count>500&&!offset?"page2":null};}
      return original(op,payload);
    });
    const result=await loadTemplateDocuments();expect(result.documents).toHaveLength(count);expect(result.bounded).toBe(false);
    expect(backlinks(result.documents,"d0")[0].document.document_id).toBe(`d${count-1}`);
    expect(collection(result.documents,"math").members).toHaveLength(count);expect(collection(result.documents,"math").relations).toBe(1);
    expect(api.call.mock.calls.filter(([op])=>op==="document_version")).toHaveLength(count);
  });
  it.each(["legacy","later_failure","duplicate","count_mismatch","version_mismatch"])("refuses incomplete %s reads",async failure=>{
    api.call.mockImplementation(async(op:string,payload:Record<string,unknown>={})=>{
      if(op==="documents_list"){
        if(failure==="legacy")return {documents:[doc("d")]};
        if(payload.cursor&&failure==="later_failure")throw new Error("offline");
        if(failure==="count_mismatch")return {documents:[doc("d")],snapshot_count:2,next_cursor:null};
        return {documents:[doc("d")],snapshot_count:failure==="version_mismatch"?1:2,next_cursor:failure==="version_mismatch"?null:"page2"};
      }
      return {...doc("d"),version:2};
    });
    await expect(loadTemplateDocuments()).rejects.toThrow();
  });
});
