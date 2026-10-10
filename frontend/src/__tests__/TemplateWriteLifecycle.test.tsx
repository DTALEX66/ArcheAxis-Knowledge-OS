import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { DocumentDto } from "../api/generated/core-contract";
import { documentRequestIdentity } from "../presentation/documentRequestIdentity";
import { TemplateWorkspace } from "../templates/TemplateWorkspace";
import { binding, executeTemplateWrite, prepareTemplateCreate, prepareTemplateSave, readTemplateWrite, readableBinding } from "../templates/bindings";

const api=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:api.call}));
const metadata={schema:"archeaxis.template/v1",template_id:"T1",discipline_id:"math",fields:{status:"unevaluated"},references:[],learning_item_key:null};
let docs:DocumentDto[],versions:Map<string,DocumentDto>;
function normalized(id:string,version:number,editor:unknown,title=id):DocumentDto {
  const value=structuredClone(editor) as {type:string;content:Array<{type:string;attrs?:Record<string,unknown>}>};
  value.content.forEach((node,index)=>{node.attrs={...node.attrs,block_id:node.attrs?.block_id??`block_${index}`};});
  return {document_id:id,version,title,source_id:null,source_revision:null,editor_json:value,content_sha256:"a".repeat(64),text_projection:"fixture",blocks:value.content.map((node,index)=>({block_id:String(node.attrs!.block_id),kind:node.type,ordinal:index,node_json:node,text_projection:"fixture",codec_status:"known"}))};
}
function remember(doc:DocumentDto){versions.set(`${doc.document_id}/${doc.version}`,structuredClone(doc));docs=[...docs.filter(d=>d.document_id!==doc.document_id),doc];return structuredClone(doc);}
async function host(operation:string,payload:Record<string,unknown>={}){
  if(operation==="capabilities_list")return {capabilities:[]};
  if(operation==="documents_list")return {documents:docs,next_cursor:null,snapshot_count:docs.length};
  if(operation==="document_version"){const found=versions.get(`${payload.document_id}/${payload.version}`);if(!found)throw new Error("404");return structuredClone(found);}
  if(operation==="document_get"){const found=docs.find(d=>d.document_id===payload.document_id);if(!found)throw new Error("404");return structuredClone(found);}
  const body=payload.body as Record<string,unknown>;
  if(operation==="document_create"){
    const id=await documentRequestIdentity(String(body.create_request_id));const prior=versions.get(`${id}/1`);
    if(prior)return structuredClone(prior);
    return remember(normalized(id,1,body.editor_json,String(body.title)));
  }
  if(operation==="document_draft"){
    const prior=docs.find(d=>d.document_id===payload.document_id)!;
    if(prior.version!==body.expected_version)throw new Error("409");
    return remember(normalized(prior.document_id,prior.version+1,body.editor_json,prior.title));
  }
  throw new Error(operation);
}
beforeEach(()=>{docs=[];versions=new Map();remember(normalized("saved",1,{type:"doc",attrs:{archeaxis_template:metadata,other:{keep:true}},content:[{type:"paragraph",attrs:{block_id:"original"},content:[{type:"text",text:"original正文"}]}]}));api.call.mockReset();api.call.mockImplementation(host);});

describe("SIMULATED template write lifecycle; real Core separately qualified",()=>{
  it("accepts canonical newly assigned block IDs and retries one deterministic create identity",async()=>{
    const attempt=await prepareTemplateCreate("T2","physics","fixed_template");
    const first=await executeTemplateWrite(attempt);const second=await executeTemplateWrite(attempt);
    expect(first).toEqual(second);expect(docs.filter(d=>d.document_id===attempt.id)).toHaveLength(1);
    expect(first.blocks[0].block_id).toBe("block_0");expect(binding(first)?.discipline_id).toBe("physics");
  });
  it.each(["identity","metadata","正文","block"])("rejects a matching ACK/readback with altered %s",async(kind)=>{
    const attempt=await prepareTemplateCreate("T1","math","bad_template");
    const wrong=normalized(attempt.id,1,attempt.editor,attempt.title);
    if(kind==="identity")wrong.document_id="other";
    if(kind==="metadata")(wrong.editor_json as any).attrs.archeaxis_template.fields.status="adopted";
    if(kind==="正文")(wrong.editor_json as any).content[0].content[0].text="replaced";
    if(kind==="block")wrong.blocks[0].block_id="wrong";
    api.call.mockResolvedValue(wrong);await expect(executeTemplateWrite(attempt)).rejects.toThrow(/模板保存读回/);
  });
  it("save frozen snapshot retains unknown envelope, original body and existing block IDs",async()=>{
    const original=docs[0];const attempt=await prepareTemplateSave(original,{...binding(original)!,fields:{status:"draft",单位:"s"}});
    const saved=await executeTemplateWrite(attempt);expect(saved.version).toBe(2);
    expect((saved.editor_json as any).attrs.other).toEqual({keep:true});expect(saved.blocks[0].block_id).toBe("original");
    expect((saved.editor_json as any).content).toEqual((original.editor_json as any).content);
  });
  it("a default empty learning_state is insufficient proof that a learning object exists",async()=>{
    api.call.mockImplementation(async(op,payload)=>op==="learning_items"?{items:[],count:0}:op==="learning_state"?{item_key:"invented"}:host(op,payload));
    await expect(prepareTemplateSave(docs[0],{...binding(docs[0])!,learning_item_key:"invented"})).rejects.toThrow(/实际学习集合/);
    expect(api.call.mock.calls.some(([op])=>op==="document_draft"||op==="learning_state")).toBe(false);
  });
  it("unrecognized template extension metadata is preserved outside the editable template projection",()=>{
    const future=structuredClone(docs[0]);(future.editor_json as any).attrs.archeaxis_template.future={raw:[1,2,3]};
    const before=JSON.stringify(future);expect(readableBinding(future)).toBeNull();expect(()=>binding(future)).toThrow(/原文仍保留/);expect(JSON.stringify(future)).toBe(before);
  });
  it("an actual listed learning object still binds and saves without enhancement qualification",async()=>{
    api.call.mockImplementation(async(op,payload)=>op==="learning_items"?{items:[{item_key:"existing"}],count:1}:op==="learning_state"?{item_key:"existing"}:host(op,payload));
    const saved=await executeTemplateWrite(await prepareTemplateSave(docs[0],{...binding(docs[0])!,learning_item_key:"existing"}));
    expect(binding(saved)?.learning_item_key).toBe("existing");
  });
  it("lost create ACK freezes ID and payload, prevents duplicate create and resolves same request",async()=>{
    let lost=true;api.call.mockImplementation(async(op,payload)=>{const result=await host(op,payload);if(op==="document_create"&&lost){lost=false;throw new Error("lost ACK");}return result;});
    const dirty=vi.fn();render(<TemplateWorkspace onOpen={vi.fn()} onDirtyChange={dirty}/>);
    await screen.findByRole("button",{name:"saved · v1"});fireEvent.click(screen.getByRole("button",{name:"创建学科对象"}));
    await screen.findByText(/模板请求结果尚未确认/);expect(screen.getByRole("button",{name:"创建学科对象"})).toBeDisabled();
    fireEvent.click(screen.getByRole("button",{name:"重试冻结模板请求"}));await screen.findByText(/模板对象与属性已保存并完整读回/);
    const calls=api.call.mock.calls.filter(([op])=>op==="document_create");expect(calls).toHaveLength(2);expect(calls[0][1]).toEqual(calls[1][1]);expect(docs).toHaveLength(2);
    await waitFor(()=>expect(dirty).toHaveBeenLastCalledWith(false));
  });
  it("lost draft ACK reconciles committed version without issuing another write or losing later edits",async()=>{
    let lost=true;api.call.mockImplementation(async(op,payload)=>{const result=await host(op,payload);if(op==="document_draft"&&lost){lost=false;throw new Error("lost ACK");}return result;});
    const dirty=vi.fn();render(<TemplateWorkspace onOpen={vi.fn()} onDirtyChange={dirty}/>);
    fireEvent.click(await screen.findByRole("button",{name:"saved · v1"}));
    fireEvent.change(screen.getByLabelText("status"),{target:{value:"sent"}});fireEvent.click(screen.getByRole("button",{name:"保存模板属性与关系"}));
    await screen.findByText(/模板请求结果尚未确认/);fireEvent.change(screen.getByLabelText("status"),{target:{value:"later"}});
    fireEvent.click(screen.getByRole("button",{name:"核对冻结模板请求"}));await screen.findByText(/后续属性修改仍未保存/);
    expect(screen.getByLabelText("status")).toHaveValue("later");expect(api.call.mock.calls.filter(([op])=>op==="document_draft")).toHaveLength(1);
    expect(binding(docs[0])?.fields.status).toBe("sent");await waitFor(()=>expect(dirty).toHaveBeenLastCalledWith(true));
  });
  it("late ACK after unmount cannot publish dirty or clear another mounted workspace",async()=>{
    let release!:(value:DocumentDto)=>void;let attemptId="";
    api.call.mockImplementation(async(op,payload)=>{if(op==="document_create"){attemptId=await documentRequestIdentity(String(payload.body.create_request_id));return new Promise<DocumentDto>(r=>{release=r;});}return host(op,payload);});
    const dirty=vi.fn();const view=render(<TemplateWorkspace onOpen={vi.fn()} onDirtyChange={dirty}/>);
    await screen.findByRole("button",{name:"saved · v1"});fireEvent.click(screen.getByRole("button",{name:"创建学科对象"}));await waitFor(()=>expect(release).toBeTypeOf("function"));view.unmount();const count=dirty.mock.calls.length;
    const attempt=await prepareTemplateCreate("T1","math");const value=remember(normalized(attemptId,1,attempt.editor,attempt.title));release(value);
    await new Promise(r=>setTimeout(r,0));expect(dirty.mock.calls).toHaveLength(count);
  });
  it("a failed full collection refresh after confirmed save remains a confirmed write",async()=>{
    let written=false;api.call.mockImplementation(async(op,payload)=>{if(op==="documents_list"&&written)throw new Error("read failed");const result=await host(op,payload);if(op==="document_create")written=true;return result;});
    const dirty=vi.fn();render(<TemplateWorkspace onOpen={vi.fn()} onDirtyChange={dirty}/>);await screen.findByRole("button",{name:"saved · v1"});fireEvent.click(screen.getByRole("button",{name:"创建学科对象"}));
    await screen.findByText(/模板写入已确认；集合刷新失败/);expect(screen.queryByRole("button",{name:"重试冻结模板请求"})).toBeNull();await waitFor(()=>expect(dirty).toHaveBeenLastCalledWith(false));
  });
  it("historical fixed request readback does not replace it with a newer document version",async()=>{
    const attempt=await prepareTemplateCreate("T1","math","history_template");const saved=await executeTemplateWrite(attempt);
    await executeTemplateWrite(await prepareTemplateSave(saved,{...binding(saved)!,fields:{status:"changed"}}));
    expect((await readTemplateWrite(attempt)).version).toBe(1);expect(docs.find(d=>d.document_id===attempt.id)?.version).toBe(2);
  });
});
