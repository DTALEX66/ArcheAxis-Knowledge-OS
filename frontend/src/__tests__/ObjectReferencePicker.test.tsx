import { beforeEach,it,expect,vi } from "vitest";
import { render,screen,fireEvent,waitFor } from "@testing-library/react";
import { ObjectReferencePicker } from "../components/ObjectReferencePicker";
import { DiagnosticConsole } from "../components/DiagnosticConsole";
import { resetDiagnostics } from "../presentation/diagnostics";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const doc={document_id:"document_real",version:4,content_sha256:"a".repeat(64),title:"真实文档",source_id:null,source_revision:null,editor_json:{type:"doc",content:[]},text_projection:"块原文",blocks:[{block_id:"block_real",type:"paragraph",path:[0],text_projection:"块原文",node:{type:"paragraph",text:"块原文"}}]};
beforeEach(()=>{bridge.call.mockReset();bridge.call.mockImplementation(async(op:string)=>{if(op==="documents_list")return {documents:[{document_id:doc.document_id,title:doc.title,version:3,source_id:null,source_revision:null,content_sha256:"b".repeat(64)}],next_cursor:null,snapshot_count:1};if(op==="document_get")return doc;throw new Error("unexpected "+op);});});
it("pins actual document get version and block rather than stale list version",async()=>{const pick=vi.fn();render(<ObjectReferencePicker onPick={pick}/>);fireEvent.click(screen.getByRole("button",{name:"浏览已保存文档"}));await screen.findByRole("option",{name:"真实文档 · 第 3 版"});fireEvent.change(screen.getByLabelText("选择文档"),{target:{value:"document_real"}});await screen.findByLabelText("选择文档片段");fireEvent.change(screen.getByLabelText("选择文档片段"),{target:{value:"block_real"}});fireEvent.click(screen.getByRole("button",{name:"加入此固定引用"}));expect(pick).toHaveBeenCalledWith({kind:"document",document_id:"document_real",version:4,block_id:"block_real"});});
it("late read cannot become selectable after picker disabled or session change",async()=>{let resolve!:(v:unknown)=>void;bridge.call.mockImplementation((op:string)=>op==="document_get"?new Promise(r=>resolve=r):Promise.resolve({documents:[doc],next_cursor:null,snapshot_count:1}));const pick=vi.fn(),view=render(<ObjectReferencePicker onPick={pick}/>);fireEvent.click(screen.getByRole("button",{name:"浏览已保存文档"}));await screen.findByRole("option",{name:"真实文档 · 第 4 版"});fireEvent.change(screen.getByLabelText("选择文档"),{target:{value:"document_real"}});view.rerender(<ObjectReferencePicker onPick={pick} disabled/>);resolve(doc);await waitFor(()=>expect(screen.queryByRole("button",{name:"加入此固定引用"})).not.toBeInTheDocument());expect(pick).not.toHaveBeenCalled();});
it("read errors remain explicit with no synthetic object",async()=>{bridge.call.mockRejectedValue(new Error("Core offline"));render(<ObjectReferencePicker onPick={vi.fn()}/>);fireEvent.click(screen.getByRole("button",{name:"浏览已保存文档"}));await screen.findByRole("alert");expect(screen.queryByRole("button",{name:"加入此固定引用"})).not.toBeInTheDocument();});

it("shows source names with a short distinction while retaining the exact full reference in diagnostics and selection",async()=>{
 resetDiagnostics();const source={source_id:"source_exact_identity_12345678",original_name:"原始图片.png",sha256:"c".repeat(64)},pick=vi.fn();
 bridge.call.mockImplementation(async(op:string)=>{if(op==="sources_list")return {sources:[source]};throw new Error("unexpected "+op);});
 render(<><ObjectReferencePicker onPick={pick}/><DiagnosticConsole/></>);fireEvent.click(screen.getByRole("button",{name:"浏览来源原件"}));
 await screen.findByRole("option",{name:"原始图片.png · 12345678"});fireEvent.change(screen.getByLabelText("选择来源原件"),{target:{value:source.source_id}});
 expect(screen.queryByText(source.sha256,{exact:false})).not.toBeInTheDocument();fireEvent.click(screen.getByRole("button",{name:"状态与诊断：所选引用完整身份"}));
 expect(screen.getByRole("region",{name:"诊断控制台"})).toHaveTextContent(source.sha256);expect(screen.getByRole("region",{name:"诊断控制台"})).toHaveTextContent(source.source_id);
 fireEvent.click(screen.getByRole("button",{name:"加入此固定引用"}));expect(pick).toHaveBeenCalledWith({kind:"source",source_id:source.source_id,sha256:source.sha256});
});
