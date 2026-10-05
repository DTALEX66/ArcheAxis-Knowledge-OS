import type { Editor } from "@tiptap/core";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createHash, webcrypto } from "node:crypto";
import { assertCoreDto } from "../api/generated/core-contract";
import { CanonicalLibrarySpace } from "../spaces/CanonicalLibrarySpace";

const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));
const hash = createHash("sha256").update("原文样板").digest("hex");
const source = { source_id: "src_test", source_revision: hash, sha256: hash, original_name: "样板.txt", imported_at: "2026-10-05" };
let doc = { document_id: "doc_test", source_id: source.source_id, source_revision: hash, title: source.original_name, version: 1,
  editor_json: { type: "doc", content: [{ type: "paragraph", attrs: { block_id: "p1" }, content: [{ type: "text", text: "已保存笔记" }] }] }, text_projection: "已保存笔记", content_sha256: hash, blocks: [] };

describe("canonical content sample", () => {
  beforeEach(() => {
    vi.stubGlobal("crypto", webcrypto);
    bridge.call.mockReset();
    doc = { ...doc, version: 1 };
    bridge.call.mockImplementation(async (operation: string, payload: Record<string, unknown>) => {
      switch (operation) {
        case "sources_list": return { sources: [source] };
        case "documents_list": return { documents: [doc] };
        case "source_original": return { source_id: source.source_id, name: source.original_name, media_type: "text/plain", sha256: hash, content_base64: Buffer.from("原文样板").toString("base64") };
        case "anchors_list": return { anchors: [] };
        case "document_get": return doc;
        case "document_version": return { ...doc, version: payload.version };
        case "document_restore": return { ...doc, version: doc.version + 1 };
        case "anchor_create": return { anchor_id: "anchor_test", source_id: source.source_id, source_revision: hash, position: (payload.body as Record<string, unknown>).position, location_status: "bound_revision" };
        case "document_draft": return { ...doc, editor_json: (payload.body as Record<string, unknown>).editor_json, version: doc.version + 1 };
        case "document_export": return {document_id:doc.document_id,version:doc.version,format:payload.format,source_revision:hash,projection_sha256:hash,files:[{path:"document.md",media_type:"text/markdown",content:"已保存笔记"}]};
        case "document_export_save": return {directory:"exports/doc_test/markdown/version-1",version:doc.version,files:["document.md","manifest.json"]};
        default: throw new Error(operation);
      }
    });
  });
  it("does not let a late original creation discard newly edited text",async()=>{
    let complete!:(value:unknown)=>void;
    const previous=bridge.call.getMockImplementation()!;
    bridge.call.mockImplementation((op:string,payload:Record<string,unknown>)=>op==="document_create"?new Promise(resolve=>{complete=resolve;}):previous(op,payload));
    render(<CanonicalLibrarySpace/>);const user=userEvent.setup();
    await user.click(await screen.findByRole("button",{name:"样板.txt · 文档"}));
    const textbox=await screen.findByRole("textbox",{name:"文档草稿"});
    await user.click(screen.getByRole("button",{name:"新建原创笔记"}));
    fireEvent.compositionStart(textbox);act(()=>{(textbox as HTMLElement & {editor:Editor}).editor.commands.setContent({type:"doc",content:[{type:"paragraph",content:[{type:"text",text:"New unsaved text during request"}]}]},{emitUpdate:true});});
    await screen.findByText(/尚未保存 · 当前持久化版本/);
    await act(async()=>{complete({...doc,document_id:"late_original",source_id:null,source_revision:null,title:"late original",editor_json:{type:"doc",content:[{type:"paragraph"}]}});});
    expect(screen.getByRole("textbox",{name:"文档草稿"})).toHaveTextContent("New unsaved text during request");
    expect(screen.getByRole("button",{name:"late original · 文档"})).toBeInTheDocument();
  });
  it("reuses the inspector with the actual saved version and source fingerprint without inventing review", async () => {
    const onInspect = vi.fn(); render(<CanonicalLibrarySpace onInspect={onInspect} />);
    await userEvent.setup().click(await screen.findByRole("button", { name: "样板.txt · 文档" }));
    await waitFor(() => expect(onInspect).toHaveBeenCalledWith(expect.objectContaining({ version: "1", rawSha256: hash })));
    const target = onInspect.mock.calls.at(-1)![0];
    expect(target.detail).toContain(doc.document_id);
    expect(target.lifecycle).toContain("核验与依据分析独立记录");
    expect(target.review).toBeUndefined();
  });
  it.each(["document_get","document_restore"])("preserves edits begun while %s is pending",async(operation)=>{
    let complete!:(value:unknown)=>void;
    const previous=bridge.call.getMockImplementation()!;
    const other={...doc,document_id:"late-read",title:"late reader"};
    bridge.call.mockImplementation((op:string,payload:Record<string,unknown>)=>{
      if(op==="documents_list")return Promise.resolve({documents:[doc,other]});
      if(op===operation&&(op!=="document_get"||payload.document_id==="late-read"))return new Promise(resolve=>{complete=resolve;});
      return previous(op,payload);
    });
    render(<CanonicalLibrarySpace/>);const user=userEvent.setup();
    await user.click(await screen.findByRole("button",{name:"样板.txt · 文档"}));
    const textbox=await screen.findByRole("textbox",{name:"文档草稿"});
    await user.click(screen.getByRole("button",{name:operation==="document_get"?"late reader · 文档":"读取并恢复版本"}));
    fireEvent.compositionStart(textbox);act(()=>{(textbox as HTMLElement & {editor:Editor}).editor.commands.setContent({type:"doc",content:[{type:"paragraph",content:[{type:"text",text:"Preserved while read pending"}]}]},{emitUpdate:true});});
    await screen.findByText(/尚未保存 · 当前持久化版本/);
    await act(async()=>{complete(operation==="document_get"?other:{...doc,version:2});});
    expect(screen.getByRole("textbox",{name:"文档草稿"})).toHaveTextContent("Preserved while read pending");
  });
  it("saves an explicitly selected revision basis without requiring check execution",async()=>{
    const base=bridge.call.getMockImplementation();
    bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>{
      if(op==="document_checks")return {document_id:doc.document_id,version:1,content_sha256:hash,historical:false,default_status:"unverified",checks_capped:false,next_offset:null,checks:[{check_id:"check1",document_id:doc.document_id,version:1,content_sha256:hash,dimension:"recognition_fidelity",provider_mode:"manual",status:"uncertain",actor:"human",execution_verified:false,execution_state:"recorded"}]};
      return base?.(op,payload);
    });
    render(<CanonicalLibrarySpace/>);const user=userEvent.setup();
    await user.click(await screen.findByRole("button",{name:"样板.txt · 文档"}));
    await screen.findByText(/不确定 · 手动记录/);
    await user.type(screen.getByLabelText("下一次修订理由"),"修订说明");await user.click(screen.getByRole("button",{name:"用于下一次修订"}));
    await user.click(screen.getByRole("button",{name:"保存草稿"}));
    await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("document_draft",{document_id:doc.document_id,body:{expected_version:1,editor_json:expect.anything(),revision_basis:{rationale:"修订说明",reference_version:1,check_id:"check1"}}}));
  });
  it("creates and edits an original note without source or review prerequisites", async()=>{
    const originalDoc={...doc,source_id:null,source_revision:null,title:"原创笔记"};
    const base=bridge.call.getMockImplementation();
    bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>{
      if(op==="sources_list")return {sources:[]};
      if(op==="documents_list")return {documents:[]};
      if(op==="document_create")return originalDoc;
      if(op==="document_draft")return {...originalDoc,version:2,editor_json:(payload.body as Record<string,unknown>).editor_json};
      return base?.(op,payload);
    });
    render(<CanonicalLibrarySpace/>);
    await userEvent.setup().click(screen.getByRole("button",{name:"新建原创笔记"}));
    expect(await screen.findByLabelText("版本化草稿编辑器")).toBeInTheDocument();
    expect(screen.queryByRole("button",{name:"引用当前页"})).not.toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button",{name:"保存草稿"}));
    await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("document_draft",expect.anything()));
    expect(bridge.call).toHaveBeenCalledWith("document_create",{body:{title:"原创笔记",editor_json:{type:"doc",content:[{type:"paragraph"}]}}});
    expect(bridge.call.mock.calls.some(([op])=>op==="anchor_create"||op==="machine_answer")).toBe(false);
  });
  it("keeps the readback provenance folded and never upgrades an unverified locator",async()=>{
    const previous=bridge.call.getMockImplementation()!;
    bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>op==="anchors_list"?{anchors:[{anchor_id:"anchor_unverified",source_id:source.source_id,source_revision:hash,position:JSON.stringify({type:"text",start:0,end:12}),location_status:"unverified"}]}:previous(op,payload));
    render(<CanonicalLibrarySpace/>);
    await userEvent.setup().click(await screen.findByRole("button",{name:"样板.txt"}));
    expect(await screen.findByRole("button",{name:"来源引用 · 定位未核实"})).toBeInTheDocument();
    const details=screen.getByText("更多信息：来源链与内容指纹").closest("details");
    expect(details).not.toHaveAttribute("open");
    expect(details).toHaveTextContent(hash);
    expect(details).toHaveTextContent("原件字节与 Core 内容指纹已匹配");
  });
  it("reports oversized import as not imported instead of conversion success",async()=>{
    render(<CanonicalLibrarySpace/>);
    const file=new File([new Uint8Array(5*1024*1024+1)],"large.xlsx");
    await userEvent.setup().upload(screen.getByLabelText("导入原件"),file);
    expect(await screen.findByLabelText("导入回执")).toHaveTextContent("未导入：超过大小上限");
    expect(bridge.call.mock.calls.some(([operation])=>operation==="source_import")).toBe(false);
  });
  it("rejects original source identity mismatch even when returned bytes and SHA match",async()=>{
    const previous=bridge.call.getMockImplementation()!;
    bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>{
      const result=await previous(op,payload);
      return op==="source_original"?{...result,source_id:"another-source"}:result;
    });
    render(<CanonicalLibrarySpace/>);
    await userEvent.setup().click(await screen.findByRole("button",{name:"样板.txt"}));
    expect(await screen.findByRole("alert")).toHaveTextContent("原件版本核对未完成");
    expect(screen.queryByLabelText("原件正文")).not.toBeInTheDocument();
  });
  it("fails closed with a specific stage when WebView has no Web Crypto",async()=>{
    vi.stubGlobal("crypto",{});
    render(<CanonicalLibrarySpace/>);
    await userEvent.setup().click(await screen.findByRole("button",{name:"样板.txt"}));
    expect(await screen.findByRole("alert")).toHaveTextContent("原件字节核验未完成");
    expect(screen.queryByLabelText("原件正文")).not.toBeInTheDocument();
  });
  it("reads the exact real WebDriver source/original/empty-anchor DTO shapes through generated validation",async()=>{
    const realSource={source_id:"src_0c797d79499de2016ce7eceb",source_revision:"b9fe434a61ec006d638253664b058b05eda6ecec1e4a7ec4964da04138785d14",sha256:"b9fe434a61ec006d638253664b058b05eda6ecec1e4a7ec4964da04138785d14",original_name:"WebDriver证据.txt",imported_at:"2026-10-05 10:19:34"};
    const realOriginal={source_id:realSource.source_id,name:realSource.original_name,sha256:realSource.sha256,media_type:"text/plain",content_base64:"5Lit5paHIFdlYkRyaXZlciDljp/mlofor4Hmja4gR29sZGVuIG5hdGl2ZSB3aW5kb3cgNDIuCg=="};
    bridge.call.mockImplementation(async(op:string)=>{
      if(op==="sources_list")return assertCoreDto("SourcesListDto",{sources:[realSource]});
      if(op==="documents_list")return assertCoreDto("DocumentsListDto",{documents:[]});
      if(op==="source_original")return assertCoreDto("OriginalDto",realOriginal);
      if(op==="anchors_list")return assertCoreDto("AnchorsListDto",{anchors:[]});
      if(op==="capabilities_list")return {};
      if(op==="workspace_backups")return {backups:[]};
      throw new Error(op);
    });
    render(<CanonicalLibrarySpace/>);
    await userEvent.setup().click(await screen.findByRole("button",{name:"WebDriver证据.txt"}));
    expect(await screen.findByLabelText("原件正文")).toHaveTextContent("中文 WebDriver 原文证据 Golden native window 42.");
    expect(screen.getByText("此来源尚无引用记录。")).toBeInTheDocument();
  });
  it("exports only to the product-owned directory and reports its real save receipt", async () => {
    render(<CanonicalLibrarySpace />);
    const user=userEvent.setup();
    await user.click(await screen.findByRole("button",{name:"样板.txt"}));
    await user.click(await screen.findByRole("button",{name:"Markdown 导出到产品资料目录"}));
    await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("document_export_save",{document_id:"doc_test",format:"markdown"}));
    expect(await screen.findByText(/已导出到产品资料目录/)).toHaveTextContent("外部应用读取仍需单独验证");
  });
  it("bounds the source navigation DOM while allowing later originals to be reached", async () => {
    const sources=Array.from({length:501},(_,index)=>({...source,source_id:`src_${index}`,original_name:`source-${index}.txt`}));
    bridge.call.mockImplementation(async(operation:string)=>operation==="sources_list"?{sources}:{documents:[]});
    render(<CanonicalLibrarySpace/>);
    await screen.findByRole("button",{name:"source-0.txt"});
    expect(screen.queryByRole("button",{name:"source-30.txt"})).not.toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button",{name:"下一组原件"}));
    expect(screen.getByRole("button",{name:"source-30.txt"})).toBeInTheDocument();
    expect(screen.queryByRole("button",{name:"source-0.txt"})).not.toBeInTheDocument();
  });
  it("reads hashed original, records a canonical reference and restores by optimistic version", async () => {
    render(<CanonicalLibrarySpace />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "样板.txt" }));
    expect(await screen.findByLabelText("原件正文")).toHaveTextContent("原文样板");
    expect(await screen.findByRole("textbox", { name: "文档草稿" })).toHaveTextContent("已保存笔记");
    await user.click(screen.getByRole("button", { name: "引用当前页" }));
    await waitFor(() => expect(bridge.call).toHaveBeenCalledWith("anchor_create", expect.objectContaining({ source_id: "src_test", body: expect.objectContaining({ revision: hash }) })));
    await user.click(screen.getByRole("button", { name: "保存草稿" }));
    await waitFor(() => expect(bridge.call).toHaveBeenCalledWith("document_draft", expect.objectContaining({ document_id: "doc_test", body: expect.objectContaining({ expected_version: 1 }) })));
    await user.click(screen.getByRole("button", { name: "读取并恢复版本" }));
    await waitFor(() => expect(bridge.call).toHaveBeenCalledWith("document_restore", expect.objectContaining({ body: expect.objectContaining({ expected_version: 2, restore_version: 1 }) })));
    expect(await screen.findByText(/恢复为新版本/)).toBeInTheDocument();
  });
  it("rejects altered original bytes instead of displaying false provenance", async () => {
    bridge.call.mockImplementation(async (operation: string) => operation === "sources_list" ? { sources: [source] }
      : operation === "documents_list" ? { documents: [] }
      : operation === "anchors_list" ? { anchors: [] }
      : { source_id:source.source_id,name:source.original_name,sha256: hash, content_base64: btoa("altered"), media_type: "text/plain" });
    render(<CanonicalLibrarySpace />);
    await userEvent.setup().click(await screen.findByRole("button", { name: "样板.txt" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("原件字节核验未完成");
    expect(screen.queryByLabelText("原件正文")).not.toBeInTheDocument();
  });
});
