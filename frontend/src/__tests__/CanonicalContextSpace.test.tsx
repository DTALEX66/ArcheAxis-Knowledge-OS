import { beforeEach, afterEach, expect, it, vi } from "vitest";
import { webcrypto } from "node:crypto";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { CanonicalContextSpace } from "../spaces/CanonicalContextSpace";
import { documentRequestIdentity } from "../presentation/documentRequestIdentity";
import type { DocumentDto, ContextGrantDto } from "../api/generated/core-contract";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
type J=Record<string,any>;
const grant=(state:ContextGrantDto["state"]="candidate"):ContextGrantDto=>({schema:"archeaxis.context-grant/v1",purpose:"学习资料",consumer:"local-machine",operations:["answer"],knowledge_id:"knowledge_original",provenance:[{kind:"knowledge",knowledge_id:"knowledge_original"}],authorization_basis:"本人决定",expires_at:null,state});
function dto(id:string,value=grant(),version=1):DocumentDto{return {document_id:id,title:id,version,content_sha256:"a".repeat(64),source_id:null,source_revision:null,text_projection:"原文",blocks:[],editor_json:{type:"doc",attrs:{archeaxis_context_grant:value,ownerUnknown:{raw:"原始载荷"}},content:[{type:"future",payload:"保留原文"}]}};}
let docs:Map<string,DocumentDto>,writes:J[],original:(op:string,p?:J)=>Promise<unknown>;
beforeEach(()=>{vi.stubGlobal("crypto",webcrypto);docs=new Map([["context_saved",dto("context_saved")]]);writes=[];bridge.call.mockReset();original=async(op,p={})=>{
 if(op==="machine_contexts_list")return {items:[...docs.values()].map(d=>({document_id:d.document_id,title:d.title,version:d.version,content_sha256:d.content_sha256})),next_cursor:null};
 if(op==="document_get")return structuredClone(docs.get(p.document_id));
 if(op==="document_create"){writes.push(structuredClone(p));const id=await documentRequestIdentity(p.body.create_request_id);if(!docs.has(id))docs.set(id,{...dto(id),title:p.body.title,editor_json:structuredClone(p.body.editor_json)});return structuredClone(docs.get(id));}
 if(op==="document_draft"){writes.push(structuredClone(p));const old=docs.get(p.document_id)!;const next={...old,version:old.version+1,editor_json:structuredClone(p.body.editor_json)};docs.set(p.document_id,next);return structuredClone(next);}
 throw new Error(`unimplemented ${op}`);
};bridge.call.mockImplementation(original);});
afterEach(()=>{vi.unstubAllGlobals();vi.restoreAllMocks();});
async function open(){fireEvent.click(await screen.findByRole("button",{name:"context_saved · v1"}));await waitFor(()=>expect(screen.getByLabelText("用途")).toHaveValue("学习资料"));}
it("preserves unknown envelope while explicit grant/readback supplies exact consumption, then revokes without erasing source",async()=>{
 const use=vi.fn();render(<CanonicalContextSpace onUse={use}/>);await open();fireEvent.click(screen.getByRole("button",{name:"明确授权并保存"}));await screen.findByText("授权版本已保存并读回，消费时再次校验用途、知识与时效。");expect(writes[0].body.editor_json.attrs.ownerUnknown).toEqual({raw:"原始载荷"});expect(writes[0].body.editor_json.content).toEqual([{type:"future",payload:"保留原文"}]);fireEvent.click(screen.getByRole("button",{name:"使用已保存上下文进入纠正与评测"}));expect(use.mock.calls[0][0]).toEqual({document_id:"context_saved",version:2,content_sha256:"a".repeat(64),purpose:"学习资料"});fireEvent.click(screen.getByRole("button",{name:"撤回上下文授权"}));await screen.findByText("撤回版本已保存并读回，旧授权不能再次消费。");expect(screen.getByRole("button",{name:"使用已保存上下文进入纠正与评测"})).toBeDisabled();expect((docs.get("context_saved")!.editor_json as J).attrs.archeaxis_context_grant.state).toBe("revoked");
});
it("lost acknowledgement freezes create identity and does not erase a later draft",async()=>{
 let first=true;bridge.call.mockImplementation(async(op,p)=>{const result=await original(op,p);if(op==="document_create"&&first){first=false;throw new Error("lost ack");}return result;});render(<CanonicalContextSpace/>);fireEvent.change(screen.getByLabelText("用途"),{target:{value:"发送版本"}});fireEvent.click(screen.getByRole("button",{name:"保存上下文草稿"}));await screen.findByRole("alert");fireEvent.change(screen.getByLabelText("用途"),{target:{value:"随后编辑"}});fireEvent.click(screen.getByRole("button",{name:"重试冻结的上下文保存"}));await screen.findByText("发送版本已保存；随后编辑仍保留。");expect(writes).toHaveLength(2);expect(writes[0]).toEqual(writes[1]);expect(screen.getByLabelText("用途")).toHaveValue("随后编辑");expect(docs.size).toBe(2);
});
it("readback with matching grant but altered owner data cannot qualify a save or consumption",async()=>{
 bridge.call.mockImplementation(async(op,p)=>{const result=await original(op,p) as DocumentDto;if(op==="document_get"&&result?.version===2)(result.editor_json as J).attrs.ownerUnknown={raw:"CHANGED"};return result;});render(<CanonicalContextSpace/>);await open();fireEvent.click(screen.getByRole("button",{name:"明确授权并保存"}));await screen.findByRole("alert");expect(screen.getByRole("button",{name:"使用已保存上下文进入纠正与评测"})).toBeDisabled();expect(screen.getByRole("button",{name:"核对冻结请求"})).toBeInTheDocument();
});
it("list error is explicit rather than an empty saved context claim",async()=>{
 bridge.call.mockRejectedValue(new Error("offline"));render(<CanonicalContextSpace/>);await screen.findByRole("alert");expect(screen.queryByText("尚无已保存的上下文，可先创建候选。")).not.toBeInTheDocument();expect(writes).toEqual([]);
});
