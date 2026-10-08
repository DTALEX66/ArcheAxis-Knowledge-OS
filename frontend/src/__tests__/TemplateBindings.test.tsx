import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { DocumentDto } from "../api/generated/core-contract";
import { DocumentEditor } from "../components/DocumentEditor";
import { TemplateLauncher, TemplateWorkspace } from "../templates/TemplateWorkspace";
import { backlinks, binding, collection, createTemplate, resolveReference, saveBinding } from "../templates/bindings";
import { DISCIPLINES, TEMPLATES } from "../templates/disciplines";

const api=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:api.call}));
const metadata={schema:"archeaxis.template/v1" as const,template_id:"T1",discipline_id:"math",fields:{status:"unevaluated"},references:[],learning_item_key:null};
function doc(id:string):DocumentDto{return {document_id:id,title:id,version:1,source_id:null,source_revision:null,content_sha256:"hash",editor_json:{type:"doc",attrs:{archeaxis_template:metadata},content:[{type:"paragraph",attrs:{block_id:"p1"},content:[{type:"text",text:"Hypothesis, unevaluated"}]}]},text_projection:"Hypothesis, unevaluated",blocks:[{block_id:"p1",kind:"paragraph",ordinal:0,node_json:{},text_projection:"Hypothesis, unevaluated",codec_status:"known"}]};}
let stored:DocumentDto[]=[];
beforeEach(()=>{stored=[doc("target")];api.call.mockReset();api.call.mockImplementation(async(operation:string,payload:Record<string,unknown>={})=>{
  if(operation==="documents_list")return {documents:stored};
  if(operation==="document_get"||operation==="document_version"){const value=stored.find(d=>d.document_id===payload.document_id);if(!value)throw new Error("not found");return structuredClone(value);}
  if(operation==="document_create"){const body=payload.body as Record<string,unknown>;const value={...doc("created"),title:body.title as string,editor_json:body.editor_json};stored.push(value);return structuredClone(value);}
  if(operation==="document_draft"){const body=payload.body as Record<string,unknown>;const index=stored.findIndex(d=>d.document_id===payload.document_id);if(stored[index].version!==body.expected_version)throw new Error("version conflict");stored[index]={...stored[index],editor_json:body.editor_json,version:stored[index].version+1};return structuredClone(stored[index]);}
  throw new Error(operation);
});});
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
    fireEvent.click(screen.getByRole("button",{name:"保存模板属性与关系"}));await screen.findByText(/属性、关系与画布引用已保存/);
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
      if(operation==="documents_list")return {documents:[]};
      throw new Error(operation);
    });
    render(<TemplateWorkspace onOpen={vi.fn()}/>);
    const state=await screen.findByText("尚无已保存的模板对象；选择学科与模板后创建第一个。");
    expect(state.closest("nav")).toHaveAttribute("aria-label","已保存模板");
    expect(state.hasAttribute("role")).toBe(false);
    // The count is the read that happened, and the invalid-metadata advisory is not noise here.
    expect(screen.getByText(/本次读回 0 个文档对象，其中 0 个带可解析模板属性/)).toBeInTheDocument();
    expect(screen.queryByText(/无效模板属性不参与集合汇总/)).toBeNull();
  });
  it("reports a failed template read as a failed read, not as an empty collection",async()=>{
    // "Core answered nothing" does not establish "there are no template objects"; claiming the
    // second from the first is the fabrication this pins out, and listing the unread document is
    // the fabrication in the other direction.
    api.call.mockImplementation(async(operation:string)=>{
      if(operation==="documents_list")return {documents:[{document_id:"doc_x",source_id:null,source_revision:null,title:"未读回的文档",version:1,content_sha256:"h"}]};
      throw new Error("本地核心未能完成 document_get（503）。");
    });
    render(<TemplateWorkspace onOpen={vi.fn()}/>);
    const announced=await screen.findByText("模板对象读取失败，请重试。");
    expect(announced).toHaveAttribute("role","status");
    const state=await screen.findByText(/列表为空只表示读取失败，不表示没有模板对象/);
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
    expect(screen.getByText(/本次读回 2 个文档对象，其中 1 个带可解析模板属性/)).toBeInTheDocument();
    expect(screen.queryByText(/尚无已保存的模板对象/)).toBeNull();
  });
});
