import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { usePublicResearch } from "../presentation/publicResearch";
import type { PublicResearchReceiptDto, PublicResearchRequest } from "../api/generated/core-contract";
import { assertUiWorkingState, type UiWorkingStateRead } from "../api/generated/ui-working-state-contract";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const scope={workspace_id:"0123456789abcdef0123456789abcdef",restore_epoch:"initial"};
const restored="1".repeat(32),olderEpoch="2".repeat(32),changedScope="3".repeat(32);
const ui:UiWorkingStateRead={schema:"archeaxis.ui-working-state/v1",...scope,state_revision:0,state:{drafts:{},opened_documents:[],active_document:null,page_id:null},draft_digests:{},recovery_candidates:null,recovery_requires_confirmation:false,pending_document_id:null};
function receipt(request:PublicResearchRequest):PublicResearchReceiptDto{return {schema:"archeaxis.public-research-receipt/v1",...request,state:"complete",channels:[{family:"research",provider:"openalex",status:"complete",retrieved_at:"2026-10-21T00:00:00Z",request_url:"https://api.openalex.org/works?search=public&per-page=1",retry_after_seconds:null,error_code:null,hits:[{id:"https://openalex.org/W123",family:"research",provider:"openalex",title:"Public result",url:"https://openalex.org/W123",retrieved_at:"2026-10-21T00:00:00Z",content:"metadata",excerpt:"",locator:null,license:null,free_access:"unknown",upstream_revision:null,representation:"metadata",truncated:false}],raw_source:{kind:"source",source_id:"raw_public",sha256:"a".repeat(64)},raw_representation:"http_entity_body_bytes"}],reason_code:null,provider_stop_state:"unknown",knowledge_admission:"not_executed"};}
let resolveSearch:(v:unknown)=>void;
beforeEach(()=>{assertUiWorkingState("Read",ui);bridge.call.mockReset();bridge.call.mockImplementation(async(op:string,p:any)=>{if(op==="ui_state_read")return ui;if(op==="public_research_search")return new Promise(resolve=>{resolveSearch=resolve;});if(op==="public_research_read")return receipt({...p.body,query:"public",families:["research"],limit:1});if(op==="public_research_cancel")return {schema:"archeaxis.public-research-cancel/v1",request_id:p.body.request_id,cancel_requested:true,execution_state:"unknown",provider_stop_state:"unknown"};throw Error(op);});});
it("uses formal scoped body with explicit terms and never queries on mount",async()=>{const {result}=renderHook(()=>usePublicResearch("page-a",()=>true));expect(bridge.call).not.toHaveBeenCalled();act(()=>{void result.current.search("public",["research"]);});await waitFor(()=>expect(bridge.call).toHaveBeenCalledTimes(2));const request=bridge.call.mock.calls[1][1].body;expect(request).toEqual({...scope,request_id:expect.any(String),query:"public",families:["research"],limit:1});await act(async()=>resolveSearch(receipt(request)));expect(result.current.receipt?.query).toBe("public");});
it("cancel stops waiting, retains identity and rejects a late result until explicit read",async()=>{const {result}=renderHook(()=>usePublicResearch("page-a",()=>true));act(()=>{void result.current.search("public",["research"]);});await waitFor(()=>expect(bridge.call).toHaveBeenCalledTimes(2));const request=bridge.call.mock.calls[1][1].body;await act(async()=>{await result.current.cancel();});expect(result.current.phase).toBe("cancelled");expect(result.current.target?.request_id).toBe(request.request_id);await act(async()=>resolveSearch(receipt(request)));expect(result.current.receipt).toBeNull();await act(async()=>{await result.current.read();});expect(result.current.receipt?.request_id).toBe(request.request_id);expect(bridge.call.mock.calls.filter(([op])=>op==="public_research_search")).toHaveLength(1);});
it("does not deliver late results into a different page",async()=>{const {result,rerender}=renderHook(({owner})=>usePublicResearch(owner,()=>true),{initialProps:{owner:"a"}});act(()=>{void result.current.search("public",["research"]);});await waitFor(()=>expect(bridge.call).toHaveBeenCalledTimes(2));const request=bridge.call.mock.calls[1][1].body;rerender({owner:"b"});await act(async()=>resolveSearch(receipt(request)));expect(result.current.receipt).toBeNull();});
it("retains an interrupted page's unknown request for explicit read after returning",async()=>{const {result,rerender}=renderHook(({owner})=>usePublicResearch(owner,()=>true),{initialProps:{owner:"a"}});act(()=>{void result.current.search("public",["research"]);});await waitFor(()=>expect(bridge.call).toHaveBeenCalledTimes(2));const request=bridge.call.mock.calls[1][1].body;rerender({owner:"b"});rerender({owner:"a"});await act(async()=>resolveSearch(receipt(request)));expect(result.current.phase).toBe("failed");expect(result.current.target?.request_id).toBe(request.request_id);expect(result.current.receipt).toBeNull();await act(async()=>{await result.current.read();});expect(result.current.receipt?.request_id).toBe(request.request_id);});
it("preserves unknown identity when cancellation fails and ignores the late search",async()=>{const original=bridge.call.getMockImplementation()!;bridge.call.mockImplementation((op:string,p:any)=>op==="public_research_cancel"?Promise.reject(Error("offline")):original(op,p));const {result}=renderHook(()=>usePublicResearch("a",()=>true));act(()=>{void result.current.search("public",["research"]);});await waitFor(()=>expect(bridge.call).toHaveBeenCalledTimes(2));const request=bridge.call.mock.calls[1][1].body;await act(async()=>{await result.current.cancel();});await act(async()=>resolveSearch(receipt(request)));expect(result.current.phase).toBe("cancelled");expect(result.current.target?.request_id).toBe(request.request_id);expect(result.current.message).toContain("取消回执未确认");expect(result.current.receipt).toBeNull();});
it("rejects malformed canonical receipts and preserves unknown request identity",async()=>{const {result}=renderHook(()=>usePublicResearch("a",()=>true));act(()=>{void result.current.search("public",["research"]);});await waitFor(()=>expect(bridge.call).toHaveBeenCalledTimes(2));const request=bridge.call.mock.calls[1][1].body;await act(async()=>resolveSearch({...receipt(request),knowledge_admission:"accepted"}));expect(result.current.phase).toBe("failed");expect(result.current.target?.request_id).toBe(request.request_id);expect(result.current.receipt).toBeNull();});
it("uses fresh actor scope to list, read and materialize frozen historical receipts without searching",async()=>{
 const fresh={...scope,restore_epoch:restored};
 const saved=receipt({...scope,request_id:"saved_public",query:"public",families:["research"],limit:1});
 const older={...saved,request_id:"older_public",restore_epoch:olderEpoch};
 const hit=saved.channels![0].hits[0],accept=vi.fn(()=>true);
 const selected={schema:"archeaxis.public-research-selection/v1",request_id:saved.request_id,family:hit.family,hit_id:hit.id,reference:{kind:"source",source_id:"derived_public",sha256:"b".repeat(64)},raw_reference:saved.channels![0].raw_source,title:hit.title,representation:hit.representation,truncated:false,note:"未核验",knowledge_admission:"not_executed"};
 bridge.call.mockImplementation(async(op:string,p:any)=>{
  if(op==="ui_state_read")return {...ui,...fresh};
  if(op==="public_research_list"){expect(p).toEqual({body:fresh});return {schema:"archeaxis.public-research-journal/v1",receipts:[saved,older],limit:16,scope:"latest_requests_only"};}
  if(op==="public_research_read"){expect(p).toEqual({body:{...fresh,request_id:saved.request_id}});return saved;}
  if(op==="public_research_materialize"){expect(p).toEqual({body:{...fresh,request_id:saved.request_id,family:hit.family,hit_id:hit.id}});return selected;}
  throw Error(op);
 });
 const {result}=renderHook(()=>usePublicResearch("a",accept));
 await act(async()=>{await result.current.list();});expect(result.current.journal).toEqual([saved,older]);expect(result.current.receipt).toBeNull();
 await act(async()=>{await result.current.read(saved);});expect(result.current.receipt).toEqual(saved);expect(result.current.target?.restore_epoch).toBe("initial");
 await act(async()=>{await result.current.materialize(hit);});expect(accept).toHaveBeenCalledWith(selected);expect(result.current.receipt).toEqual(saved);
 expect(bridge.call.mock.calls.filter(([op])=>op==="public_research_search"||op==="public_research_cancel")).toHaveLength(0);
 expect(bridge.call.mock.calls.filter(([op])=>op==="ui_state_read")).toHaveLength(4);
});
it.each(["query","families","limit","restore_epoch","request_id"])("rejects changed frozen historical %s on explicit read",async field=>{
 const saved=receipt({...scope,request_id:"saved_public",query:"public",families:["research"],limit:1});
 const changed={...saved,[field]:field==="families"?["community"]:field==="limit"?2:"different"};
 bridge.call.mockImplementation(async(op:string)=>{if(op==="ui_state_read")return {...ui,restore_epoch:restored};if(op==="public_research_read")return changed;throw Error(op);});
 const {result}=renderHook(()=>usePublicResearch("a",()=>true));await act(async()=>{await result.current.read(saved);});
 expect(result.current.receipt).toBeNull();expect(result.current.message).toContain("回读未确认");
});
it.each(["restore_epoch","workspace_id"])("refuses draft append if actor %s changes while materializing a historical selection",async field=>{
 const fresh={...scope,restore_epoch:restored},saved=receipt({...scope,request_id:"saved_public",query:"public",families:["research"],limit:1});
 const hit=saved.channels![0].hits[0],accept=vi.fn(()=>true);let changed=false;
 bridge.call.mockImplementation(async(op:string,p:any)=>{
  if(op==="ui_state_read")return {...ui,...fresh,...(changed?{[field]:changedScope}:{})};
  if(op==="public_research_read")return saved;
  if(op==="public_research_materialize"){expect(p.body).toEqual({...fresh,request_id:saved.request_id,family:hit.family,hit_id:hit.id});changed=true;return {schema:"archeaxis.public-research-selection/v1",request_id:saved.request_id,family:hit.family,hit_id:hit.id,reference:{kind:"source",source_id:"derived_public",sha256:"b".repeat(64)},raw_reference:saved.channels![0].raw_source,title:hit.title,representation:hit.representation,truncated:false,note:"未核验",knowledge_admission:"not_executed"};}throw Error(op);
 });
 const {result}=renderHook(()=>usePublicResearch("a",accept));await act(async()=>{await result.current.read(saved);});await act(async()=>{await result.current.materialize(hit);});
 expect(accept).not.toHaveBeenCalled();expect(result.current.receipt).toEqual(saved);expect(result.current.message).toContain("未确认");
});
it("does not cancel a request from a previous execution epoch after restore",async()=>{
 const {result}=renderHook(()=>usePublicResearch("a",()=>true));act(()=>{void result.current.search("public",["research"]);});await waitFor(()=>expect(bridge.call).toHaveBeenCalledTimes(2));const request=bridge.call.mock.calls[1][1].body;
 const original=bridge.call.getMockImplementation()!;bridge.call.mockImplementation((op:string,p:any)=>op==="ui_state_read"?Promise.resolve({...ui,restore_epoch:restored}):original(op,p));
 await act(async()=>{await result.current.cancel();});await act(async()=>resolveSearch(receipt(request)));
 expect(bridge.call.mock.calls.filter(([op])=>op==="public_research_cancel")).toHaveLength(0);expect(result.current.target?.request_id).toBe(request.request_id);expect(result.current.phase).toBe("cancelled");expect(result.current.receipt).toBeNull();
});
it.each(["request_id","hit_id","raw_reference"])("rejects materialization with mismatched %s and keeps the receipt",async field=>{const accept=vi.fn(()=>true);const {result}=renderHook(()=>usePublicResearch("a",accept));act(()=>{void result.current.search("public",["research"]);});await waitFor(()=>expect(bridge.call).toHaveBeenCalledTimes(2));const request=bridge.call.mock.calls[1][1].body;const saved=receipt(request);await act(async()=>resolveSearch(saved));const hit=saved.channels![0].hits[0];const selection={schema:"archeaxis.public-research-selection/v1",request_id:request.request_id,family:"research",hit_id:hit.id,reference:{kind:"source",source_id:"derived_public",sha256:"b".repeat(64)},raw_reference:saved.channels![0].raw_source,title:hit.title,representation:hit.representation,truncated:false,note:"仅元数据，未核验",knowledge_admission:"not_executed"};bridge.call.mockImplementation(async(op:string)=>{if(op==="ui_state_read")return ui;if(op==="public_research_materialize")return {...selection,[field]:field==="raw_reference"?{...selection.raw_reference,sha256:"c".repeat(64)}:"wrong"};throw Error(op);});await act(async()=>{await result.current.materialize(hit);});expect(accept).not.toHaveBeenCalled();expect(result.current.receipt).toEqual(saved);expect(result.current.message).toContain("未确认");});
it("accepts only pinned selection identities, retaining results when the draft rejects append",async()=>{const accept=vi.fn(()=>false);const {result}=renderHook(()=>usePublicResearch("a",accept));act(()=>{void result.current.search("public",["research"]);});await waitFor(()=>expect(bridge.call).toHaveBeenCalledTimes(2));const request=bridge.call.mock.calls[1][1].body;const saved=receipt(request);await act(async()=>resolveSearch(saved));const hit=saved.channels![0].hits[0];bridge.call.mockImplementation(async(op:string,p:any)=>{if(op==="ui_state_read")return ui;if(op==="public_research_materialize"){expect(p.body).toEqual({...scope,request_id:request.request_id,family:"research",hit_id:hit.id});return {schema:"archeaxis.public-research-selection/v1",request_id:request.request_id,family:"research",hit_id:hit.id,reference:{kind:"source",source_id:"derived_public",sha256:"b".repeat(64)},raw_reference:saved.channels![0].raw_source,title:hit.title,representation:hit.representation,truncated:false,note:"未核验",knowledge_admission:"not_executed"};}throw Error(op);});await act(async()=>{await result.current.materialize(hit);});expect(accept).toHaveBeenCalledOnce();expect(result.current.receipt).toEqual(saved);expect(result.current.message).toContain("材料草稿未改变");});
it("rejects byte/codepoint overflow before any Core call",async()=>{const {result}=renderHook(()=>usePublicResearch("a",()=>true));await act(async()=>{await result.current.search("字".repeat(1001),["research"]);});expect(bridge.call).not.toHaveBeenCalled();});
it.each(["workspace_id","restore_epoch"])("does not submit a public query with invalid canonical %s",async field=>{
 const invalid={...ui,[field]:"invalid_scope"},accept=vi.fn(()=>true);
 bridge.call.mockImplementation(async(op:string)=>{if(op==="ui_state_read")return invalid;throw Error("must not submit query");});
 const {result}=renderHook(()=>usePublicResearch("a",accept));await act(async()=>{await result.current.search("public",["research"]);});
 expect(bridge.call.mock.calls.map(([op])=>op)).toEqual(["ui_state_read"]);expect(result.current.phase).toBe("failed");expect(result.current.target).toBeNull();expect(accept).not.toHaveBeenCalled();
});
it.each(["workspace_id","restore_epoch"])("does not materialize or append a draft with invalid actor %s",async field=>{
 const saved=receipt({...scope,request_id:"saved_public",query:"public",families:["research"],limit:1}),accept=vi.fn(()=>true);let invalid=false;
 bridge.call.mockImplementation(async(op:string)=>{if(op==="ui_state_read")return invalid?{...ui,[field]:"invalid_scope"}:ui;if(op==="public_research_read")return saved;throw Error("must not materialize");});
 const {result}=renderHook(()=>usePublicResearch("a",accept));await act(async()=>{await result.current.read(saved);});invalid=true;
 await act(async()=>{await result.current.materialize(saved.channels![0].hits[0]);});expect(bridge.call.mock.calls.filter(([op])=>op==="public_research_materialize")).toHaveLength(0);expect(accept).not.toHaveBeenCalled();expect(result.current.receipt).toEqual(saved);
});
it.each(["workspace_id","restore_epoch"])("rejects draft append when final canonical %s becomes invalid",async field=>{
 const saved=receipt({...scope,request_id:"saved_public",query:"public",families:["research"],limit:1}),hit=saved.channels![0].hits[0],accept=vi.fn(()=>true);let invalid=false;
 bridge.call.mockImplementation(async(op:string)=>{
  if(op==="ui_state_read")return invalid?{...ui,[field]:"invalid_scope"}:ui;
  if(op==="public_research_read")return saved;
  if(op==="public_research_materialize"){invalid=true;return {schema:"archeaxis.public-research-selection/v1",request_id:saved.request_id,family:hit.family,hit_id:hit.id,reference:{kind:"source",source_id:"derived_public",sha256:"b".repeat(64)},raw_reference:saved.channels![0].raw_source,title:hit.title,representation:hit.representation,truncated:false,note:"未核验",knowledge_admission:"not_executed"};}throw Error(op);
 });
 const {result}=renderHook(()=>usePublicResearch("a",accept));await act(async()=>{await result.current.read(saved);});await act(async()=>{await result.current.materialize(hit);});
 expect(bridge.call.mock.calls.filter(([op])=>op==="public_research_materialize")).toHaveLength(1);expect(accept).not.toHaveBeenCalled();expect(result.current.receipt).toEqual(saved);expect(result.current.message).toContain("未确认");
});
