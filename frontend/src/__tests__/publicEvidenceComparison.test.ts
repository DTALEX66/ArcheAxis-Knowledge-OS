import { beforeEach, expect, it, vi } from "vitest";
import { appendEvidenceComparisons, captureEvidenceComparisons, evidenceHash } from "../presentation/publicEvidenceComparison";
import type { PublicResearchReceiptDto } from "../api/generated/core-contract";
import type { ResearchDocument } from "../api/generated/research-contract";

const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const actor={workspace_id:"0123456789abcdef0123456789abcdef",restore_epoch:"initial"};
const raw={kind:"source" as const,source_id:"raw_public",sha256:"a".repeat(64)};
const hit={id:"https://openalex.org/W123",family:"research" as const,provider:"openalex" as const,title:"Public metadata",url:"https://openalex.org/W123",retrieved_at:"2026-10-21T00:00:00Z",content:"metadata" as const,excerpt:"",locator:null,license:null,free_access:"unknown" as const,upstream_revision:null,representation:"metadata" as const,truncated:false};
const receipt:PublicResearchReceiptDto={schema:"archeaxis.public-research-receipt/v1",...actor,request_id:"saved_public",query:"public",families:["research"],limit:1,state:"complete",channels:[{family:"research",provider:"openalex",status:"complete",retrieved_at:hit.retrieved_at,request_url:"https://api.openalex.org/works?search=public",retry_after_seconds:null,error_code:null,hits:[hit],raw_source:raw,raw_representation:"http_entity_body_bytes"}],reason_code:null,provider_stop_state:"unknown",knowledge_admission:"not_executed"};
const choice={family:"research" as const,id:hit.id,stance:"supports" as const};
const empty=():ResearchDocument=>({schema:"archeaxis.research/v1",question:"Human question",materials:[],hypotheses:[],methods:[],experiments:[],counterevidence:[],conclusions:[],unresolved:[]});
let text:string,bytes:Uint8Array,sha:string,selection:any,position:string;
beforeEach(async()=>{
 text="AAOS synthetic derived metadata\r\n原文😀";bytes=new TextEncoder().encode(text);sha=await evidenceHash(bytes);
 selection={schema:"archeaxis.public-research-selection/v1",request_id:receipt.request_id,family:"research",hit_id:hit.id,reference:{kind:"source",source_id:"derived_public",sha256:sha},raw_reference:raw,title:hit.title,representation:"metadata",truncated:false,note:"Synthetic metadata",knowledge_admission:"not_executed"};
 position=JSON.stringify({type:"text",start:0,end:bytes.length,checksum:sha,location_status:"located"});
 bridge.call.mockReset();bridge.call.mockImplementation(async(op:string,p:any)=>{
  if(op==="public_research_materialize"){expect(p.body).toEqual({...actor,request_id:receipt.request_id,family:"research",hit_id:hit.id});return selection;}
  if(op==="source_original")return {source_id:"derived_public",sha256:sha,name:"snapshot.txt",media_type:"text/plain",content_base64:btoa(String.fromCharCode(...bytes))};
  if(op==="anchor_create"){expect(p.body).toEqual({revision:sha,position:JSON.stringify({type:"text",start:0,end:bytes.length}),checksum:sha});return {anchor_id:"fixed_anchor",source_id:"derived_public",source_revision:sha,location_status:"located",position};}
  if(op==="anchor_resolve")return {anchor_id:"fixed_anchor",source_id:"derived_public",source_revision:sha,current_source_revision:sha,status:"CURRENT",scope:"locator_provenance_only",position};
  throw Error(op);
 });
});
it("pins complete CRLF/Unicode snapshot bytes and retains both sources as authored, unresolved evidence",async()=>{
 const guard=vi.fn(async()=>{}),bindings=await captureEvidenceComparisons(receipt,[choice],actor,guard);
 expect(guard).toHaveBeenCalledTimes(5);expect(bindings[0].citation).toMatchObject({quote:text,quote_sha256:sha,source_sha256:sha,read_snapshot_sha256:sha,anchor_position_sha256:await evidenceHash(new TextEncoder().encode(position))});
 const old=empty(),next=appendEvidenceComparisons(old,undefined,bindings);expect(old).toEqual(empty());
 expect(next.research.materials.map(m=>m.reference)).toEqual([selection.reference,raw]);
 expect(next.research.unresolved[0].references).toEqual([selection.reference,raw]);
 expect(next.research.unresolved[0].text).toContain("来源独立性：UNKNOWN");expect(next.research.unresolved[0].text).toContain("metadata");
 expect(next.relations.relations[0]).toMatchObject({kind:"supports",target:selection.reference});
 expect(appendEvidenceComparisons(next.research,next.relations,bindings)).toEqual(next);
 expect(bridge.call.mock.calls.map(c=>c[0])).toEqual(["public_research_materialize","source_original","anchor_create","anchor_resolve"]);
});

it("binds a fallback hit to its exact Crossref raw response while retaining the failed OpenAlex source",async()=>{
 const fallback=structuredClone(receipt),channel=fallback.channels![0];
 const fallbackRaw={...raw,source_id:"raw_crossref",sha256:"c".repeat(64)};
 const fallbackHit={...hit,id:"https://doi.org/10.1234/synthetic",url:"https://doi.org/10.1234/synthetic",provider:"crossref" as const};
 fallback.state="partial";fallback.channels=[{...channel,status:"limited",error_code:"rate_limited",hits:[]},{...channel,provider:"crossref",request_url:"https://api.crossref.org/works?query.bibliographic=public&rows=3",hits:[fallbackHit],raw_source:fallbackRaw}];
 selection={...selection,hit_id:fallbackHit.id,raw_reference:fallbackRaw};
 const previous=bridge.call.getMockImplementation()!;
 bridge.call.mockImplementation((op:string,p:any)=>{
  if(op==="public_research_materialize"){expect(p.body).toEqual({...actor,request_id:fallback.request_id,family:"research",hit_id:fallbackHit.id});return Promise.resolve(selection);}
  return previous(op,p);
 });
 const bindings=await captureEvidenceComparisons(fallback,[{...choice,id:fallbackHit.id}],actor,async()=>{});
 expect(bindings[0].hit.provider).toBe("crossref");expect(bindings[0].selection.raw_reference).toEqual(fallbackRaw);
 const next=appendEvidenceComparisons(empty(),undefined,bindings);
 expect(next.research.materials.map(row=>row.reference)).toEqual([selection.reference,fallbackRaw]);
 expect(fallback.channels[0]).toMatchObject({provider:"openalex",status:"limited",hits:[]});
});

it("rejects ambiguous or provider-forged hit ownership before materialization",async()=>{
 const duplicated=structuredClone(receipt);duplicated.channels!.push(structuredClone(duplicated.channels![0]));
 await expect(captureEvidenceComparisons(duplicated,[choice],actor,async()=>{})).rejects.toThrow("comparison hit missing");
 const forged=structuredClone(receipt);forged.channels![0].provider="crossref";
 await expect(captureEvidenceComparisons(forged,[choice],actor,async()=>{})).rejects.toThrow("comparison hit missing");
 expect(bridge.call).not.toHaveBeenCalled();
});
it.each(["opposes","conflict","uncertain","unclassified"] as const)("preserves %s as an authored judgment without inventing factual consensus",async stance=>{
 const bindings=await captureEvidenceComparisons(receipt,[{...choice,stance}],actor,async()=>{});
 const next=appendEvidenceComparisons(empty(),undefined,bindings);
 expect(next.relations.relations[0].kind).toBe(stance==="opposes"?"contradicts":"related");
 expect(next.research.unresolved[0].text).toContain("未核验，未知识采用");expect(next.research.conclusions).toEqual([]);
});
it.each(["raw_reference","hit_id","title"])("rejects mismatched materialized %s before reading source bytes",async field=>{
 selection={...selection,[field]:field==="raw_reference"?{...raw,sha256:"f".repeat(64)}:"changed"};
 await expect(captureEvidenceComparisons(receipt,[choice],actor,async()=>{})).rejects.toThrow();
 expect(bridge.call).toHaveBeenCalledTimes(1);
});
it("rejects wrong CAS bytes before creating a locator",async()=>{
 bytes=new TextEncoder().encode("wrong bytes");await expect(captureEvidenceComparisons(receipt,[choice],actor,async()=>{})).rejects.toThrow();
 expect(bridge.call.mock.calls.some(c=>c[0]==="anchor_create")).toBe(false);
});
it("refuses oversize snapshots without silently cutting their contents",async()=>{
 bytes=new Uint8Array(16385).fill(65);sha=await evidenceHash(bytes);selection.reference.sha256=sha;
 await expect(captureEvidenceComparisons(receipt,[choice],actor,async()=>{})).rejects.toThrow();
 expect(bridge.call.mock.calls.some(c=>c[0]==="anchor_create")).toBe(false);
});
it("requires the resolved locator's exact position rather than accepting CURRENT alone",async()=>{
 const original=bridge.call.getMockImplementation()!;bridge.call.mockImplementation((op:string,p:any)=>op==="anchor_resolve"?{anchor_id:"fixed_anchor",source_id:"derived_public",source_revision:sha,current_source_revision:sha,status:"CURRENT",scope:"locator_provenance_only",position:"{}"}:original(op,p));
 await expect(captureEvidenceComparisons(receipt,[choice],actor,async()=>{})).rejects.toThrow();
});
it("never returns a partial draft when a view/scope guard fails after a Core write",async()=>{
 let checks=0;await expect(captureEvidenceComparisons(receipt,[choice],actor,async()=>{if(++checks===4)throw Error("scope changed");})).rejects.toThrow("scope changed");
 expect(bridge.call.mock.calls.map(c=>c[0])).toEqual(["public_research_materialize","source_original","anchor_create"]);
});
it("preserves manual relations and rejects a changed generated identity instead of overwriting it",async()=>{
 const bindings=await captureEvidenceComparisons(receipt,[choice],actor,async()=>{});
 const graph={schema:"archeaxis.relations/v1" as const,relations:[{id:"manual",kind:"related" as const,label:"Human relation",target:raw}]};
 const next=appendEvidenceComparisons(empty(),graph,bindings);expect(next.relations.relations[0]).toEqual(graph.relations[0]);
 next.research.unresolved[0].text="Human correction";
 expect(()=>appendEvidenceComparisons(next.research,next.relations,bindings)).toThrow("identity collision");expect(next.research.unresolved[0].text).toBe("Human correction");
 expect(()=>appendEvidenceComparisons(empty(),{schema:"future/v9",relations:[]},bindings)).toThrow();
});


it("keeps a long public query lossless while every canonical relation label fits the Core UTF-8 bound",async()=>{
 const longQuery="界".repeat(400),bindings=await captureEvidenceComparisons({...receipt,query:longQuery},[choice],actor,async()=>{});
 const next=appendEvidenceComparisons(empty(),undefined,bindings);
 expect(next.research.unresolved[0].text).toContain(longQuery);
 expect(new TextEncoder().encode(next.relations.relations[0].label).length).toBeLessThanOrEqual(1024);
});

it.each(["label","duplicate_id","invalid_id","reference","count","extra_field"])("rejects an invalid existing %s before any partial draft/envelope merge",async field=>{
 const bindings=await captureEvidenceComparisons(receipt,[choice],actor,async()=>{}),research=empty();
 research.unresolved.push({id:"manual_entry",text:"Human annotation",references:[]});
 const manual={id:"manual",kind:"related",label:"Human relation",target:raw};
 const graph:any={schema:"archeaxis.relations/v1",relations:[manual]};
 if(field==="label")graph.relations[0].label="界".repeat(400);
 if(field==="duplicate_id")graph.relations.push(structuredClone(manual));
 if(field==="invalid_id")graph.relations[0].id="not valid";
 if(field==="reference")graph.relations[0].target={kind:"document",document_id:".",version:0,block_id:null};
 if(field==="count")graph.relations=Array.from({length:256},(_,i)=>({...manual,id:`manual_${i}`}));
 if(field==="extra_field")graph.relations[0].unknown="preserve, do not normalize";
 const before=structuredClone({research,graph});
 expect(()=>appendEvidenceComparisons(research,graph,bindings)).toThrow();
 expect({research,graph}).toEqual(before);
});
