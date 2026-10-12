import { beforeEach, afterEach, expect, it, vi } from "vitest";
import { render,screen,waitFor,fireEvent,act } from "@testing-library/react";
import { webcrypto } from "node:crypto";
import { PinnedReferencePanel } from "../components/PinnedReferencePanel";
const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
beforeEach(()=>{bridge.call.mockReset();vi.stubGlobal("crypto",webcrypto);});
afterEach(()=>{vi.unstubAllGlobals();});
const doc={document_id:"doc_original",version:1,title:"原文 v1",source_id:"source_original",source_revision:"a".repeat(64),content_sha256:"b".repeat(64),text_projection:"原版本全文",editor_json:{type:"doc",content:[]},blocks:[{block_id:"evidence",text_projection:"固定依据块"}]};
it("refuses a fixed-version read whose SHA differs from the global search observation",async()=>{
 bridge.call.mockResolvedValue(doc);render(<PinnedReferencePanel reference={{kind:"document",document_id:"doc_original",version:1}} expectedDocumentSha={"c".repeat(64)} onClose={()=>{}}/>);
 expect(await screen.findByRole("alert")).toHaveTextContent("指纹与搜索观察不一致");
 expect(screen.queryByText("原版本全文")).not.toBeInTheDocument();
 expect(bridge.call.mock.calls.every(call=>call[0]==="document_version")).toBe(true);
});
it("reads exact historical block and forwards source identity without changing version",async()=>{
 bridge.call.mockResolvedValue(doc);const jump=vi.fn();render(<PinnedReferencePanel reference={{kind:"document",document_id:"doc_original",version:1,block_id:"evidence"}} onClose={()=>{}} onOpenReference={jump}/>);
 await screen.findByText("固定依据块");expect(bridge.call).toHaveBeenCalledWith("document_version",{document_id:"doc_original",version:1});expect(screen.queryByText("原版本全文")).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole("button",{name:"读取此版本的来源原件"}));expect(jump).toHaveBeenCalledWith({kind:"source",source_id:"source_original",sha256:"a".repeat(64)});
});
it("wrong version and missing block remain errors without fallback to current",async()=>{
 bridge.call.mockResolvedValue({...doc,version:2});const rendered=render(<PinnedReferencePanel reference={{kind:"document",document_id:"doc_original",version:1}} onClose={()=>{}}/>);await screen.findByRole("alert");expect(bridge.call.mock.calls.every(c=>c[0]==="document_version")).toBe(true);
 bridge.call.mockResolvedValue(doc);rendered.rerender(<PinnedReferencePanel reference={{kind:"document",document_id:"doc_original",version:1,block_id:"absent"}} onClose={()=>{}}/>);expect(await screen.findByRole("alert")).toHaveTextContent("没有引用的块");expect(screen.queryByText("原版本全文")).not.toBeInTheDocument();
});
it("verifies actual original bytes and renders HTML only as inert text",async()=>{
 const text="<script>unsafe()</script>";const bytes=new TextEncoder().encode(text);const hash=Array.from(new Uint8Array(await webcrypto.subtle.digest("SHA-256",bytes))).map(x=>x.toString(16).padStart(2,"0")).join("");
 bridge.call.mockResolvedValue({source_id:"source_html",sha256:hash,name:"source.html",media_type:"text/html",content_base64:btoa(text)});
 render(<PinnedReferencePanel reference={{kind:"source",source_id:"source_html",sha256:hash}} onClose={()=>{}}/>);expect(await screen.findByText(text)).toBeInTheDocument();expect(document.querySelector("script")).toBeNull();
});
it("tampered source bytes are not displayed",async()=>{
 bridge.call.mockResolvedValue({source_id:"source_bad",sha256:"a".repeat(64),name:"source.txt",media_type:"text/plain",content_base64:btoa("tampered")});
 render(<PinnedReferencePanel reference={{kind:"source",source_id:"source_bad",sha256:"a".repeat(64)}} onClose={()=>{}}/>);expect(await screen.findByRole("alert")).toHaveTextContent("字节校验失败");expect(screen.queryByText("tampered")).not.toBeInTheDocument();
});
it("late reads cannot replace a newly selected pinned object",async()=>{
 let resolve:(value:unknown)=>void=()=>{};bridge.call.mockImplementation((_:string,p:{document_id?:string;knowledge_id?:string})=>p.document_id?new Promise(r=>{resolve=r}):Promise.resolve({knowledge_id:"knowledge_now",body:"当前知识",version:"v1",status:"candidate",source_id:null,anchor_id:null}));
 const rendered=render(<PinnedReferencePanel reference={{kind:"document",document_id:"doc_original",version:1}} onClose={()=>{}}/>);rendered.rerender(<PinnedReferencePanel reference={{kind:"knowledge",knowledge_id:"knowledge_now"}} onClose={()=>{}}/>);await screen.findByText("当前知识");await act(async()=>{resolve(doc);});await waitFor(()=>expect(screen.queryByText("原文 v1 · v1")).not.toBeInTheDocument());
});
