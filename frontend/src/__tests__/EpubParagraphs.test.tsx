// SIMULATED API/UI fixtures; no real EPUB parsing claim.
import { webcrypto } from "node:crypto";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor, cleanup } from "@testing-library/react";
import { EpubParagraphs, epubProof, type EpubProof } from "../components/EpubParagraphs";
import { utf8Sha256 } from "../components/TranscriptionCues";
import { JobContent } from "../components/JobContent";
const command=vi.hoisted(()=>vi.fn());
vi.mock("../api/core",()=>({coreCommand:command}));
beforeEach(()=>{vi.stubGlobal("crypto",webcrypto);command.mockReset();});
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
const proof:EpubProof={sourceId:"source",revision:"a".repeat(64),jobId:"old-success",attempt:1,resultSha256:"b".repeat(64),locations:[{kind:"epub_chapter_paragraph",path:"book/ch.xhtml",chapter:1,paragraph:1,value:"Known paragraph 37"}]};
describe("EPUB receipt-native reading (SIMULATED)",()=>{
 it("reopens successful persisted EPUB without new job and keeps it after later failure",async()=>{
  const content=JSON.stringify({params:{format:{format:"epub",parsed:true,locations:proof.locations}}});
  const output={content,metadata:{kind:"loss_report",sha256:await utf8Sha256(content),byte_length:new TextEncoder().encode(content).length}};
  const state={job_id:proof.jobId,input_ref:proof.sourceId,state:"succeeded",attempt:1};
  command.mockImplementation(async(op,args)=>{
   if(op==="capabilities_list")return {};
   if(op==="source_jobs")return {source_id:proof.sourceId,jobs:[{...state,kind:"text"}],jobs_capped:false};
   if(op==="jobs_get")return args.job_id===proof.jobId?state:{job_id:args.job_id,input_ref:proof.sourceId,state:"failed",attempt:1,error:{code:"FIXTURE"}};
   if(op==="job_output")return args.kind==="loss_report"?output:{content:args.kind==="text"?"Known paragraph 37":"[]"};
   if(op==="job_quality")return {};
   if(op==="source_job_transform")return {source_id:proof.sourceId,job_id:proof.jobId,transform_id:1,content:"Known paragraph 37"};
   if(op==="job_enqueue")return {job_id:args.body.job_id};
   if(op==="job_execute")return {};
   throw new Error(`unexpected ${op}`);
  });
  render(<JobContent sourceId={proof.sourceId} sourceRevision={proof.revision} name="book.epub"/>);
  await screen.findByText("EPUB 章节段落");
  expect(command.mock.calls.some(call=>call[0]==="job_enqueue")).toBe(false);
  expect(command.mock.calls.filter(call=>call[0]==="source_jobs").every(call=>!('offset' in call[1]))).toBe(true);
  fireEvent.click(screen.getByText("执行真实内容转换"));
  await screen.findByText("转换未完成或产物读取失败。不会把失败或未知状态当作成功。");
  expect(screen.getByText("EPUB 章节段落")).toBeInTheDocument();
  expect(screen.getByText(/成功任务 old-success/)).toBeInTheDocument();
 });
 it("rejects actual mismatched source job and tampered output digest",async()=>{
  const content=JSON.stringify({params:{format:{format:"epub",parsed:true,locations:proof.locations}}});
  const output={content,metadata:{kind:"loss_report",sha256:await utf8Sha256(content),byte_length:new TextEncoder().encode(content).length}};
  const state={job_id:proof.jobId,input_ref:proof.sourceId,state:"succeeded",attempt:1};
  const row={...state,kind:"text"};
  expect((await epubProof(proof.sourceId,proof.revision,proof.jobId,state,output,row)).locations[0].value).toBe("Known paragraph 37");
  await expect(epubProof(proof.sourceId,proof.revision,proof.jobId,state,output,{...row,input_ref:"other"})).rejects.toThrow();
  await expect(epubProof(proof.sourceId,proof.revision,proof.jobId,state,{...output,content:content+" "},row)).rejects.toThrow();
 });
 it("sends immutable old successful identity and rejects wrong-source anchor",async()=>{
  const onAnchor=vi.fn();command.mockResolvedValue({anchor_id:"wrong",source_id:"other",source_revision:proof.revision,position:"{}",location_status:"located"});
  render(<EpubParagraphs proof={proof} onAnchor={onAnchor}/>);
  fireEvent.click(screen.getByText("引用 EPUB 段落"));
  await waitFor(()=>expect(command).toHaveBeenCalled());
  const args=command.mock.calls[0][1];expect(args.source_id).toBe("source");
  expect(JSON.parse(args.body.position)).toMatchObject({job_id:"old-success",attempt:1,chapter:1,paragraph:1,result_sha256:proof.resultSha256});
  expect(args.body.checksum).toBe(await utf8Sha256("Known paragraph 37"));
  await screen.findByText("EPUB 段落引用未确认。");expect(onAnchor).not.toHaveBeenCalled();
 });
 it("jumps to paragraph 31 by receipt identity and refuses another attempt",async()=>{
  const many={...proof,locations:Array.from({length:31},(_,i)=>({...proof.locations[0],paragraph:i+1,value:`Paragraph ${i+1}`}))};
  const seek={type:"epub" as const,job_id:proof.jobId,attempt:1,result_sha256:proof.resultSha256,path:"book/ch.xhtml",chapter:1,paragraph:31};
  const view=render(<EpubParagraphs proof={many} seek={seek}/>);
  await waitFor(()=>expect(screen.getByText("Paragraph 31")).toHaveAttribute("data-epub-focused","true"));
  view.rerender(<EpubParagraphs proof={many} seek={{...seek,attempt:2}}/>);
  await screen.findByText("引用属于另一成功解析回执，未自动迁移定位。");
 });
});

// SIMULATED context races: assertions do not claim native runtime validation.
it("rejects empty EPUB locations instead of presenting successful readable paragraphs",async()=>{
 const content=JSON.stringify({params:{format:{format:"epub",parsed:true,locations:[]}}});
 const loss={content,metadata:{kind:"loss_report",sha256:await utf8Sha256(content),byte_length:new TextEncoder().encode(content).length}};
 const state={job_id:proof.jobId,input_ref:proof.sourceId,state:"succeeded",attempt:1};
 await expect(epubProof(proof.sourceId,proof.revision,proof.jobId,state,loss,{...state,kind:"text"})).rejects.toThrow();
});
it("reselects persisted route when the same source name changes extension",async()=>{
 command.mockImplementation(async(op,args)=>op==="source_jobs"?{source_id:args.source_id,jobs:[],jobs_capped:false}:{});
 const view=render(<JobContent sourceId={proof.sourceId} sourceRevision={proof.revision} name="book.txt"/>);
 await waitFor(()=>expect(command.mock.calls.filter(call=>call[0]==="source_jobs")).toHaveLength(1));
 view.rerender(<JobContent sourceId={proof.sourceId} sourceRevision={proof.revision} name="book.epub"/>);
 await waitFor(()=>expect(command.mock.calls.filter(call=>call[0]==="source_jobs")).toHaveLength(2));
});
it("does not execute an old queued response after context changes",async()=>{
 let resolveQueue!:(value:unknown)=>void;
 command.mockImplementation(async(op,args)=>{
  if(op==="source_jobs")return {source_id:args.source_id,jobs:[],jobs_capped:false};
  if(op==="job_enqueue")return new Promise(resolve=>{resolveQueue=()=>resolve({job_id:args.body.job_id});});
  if(op==="jobs_get")return {state:"failed"};
  return {};
 });
 const view=render(<JobContent sourceId={proof.sourceId} sourceRevision={proof.revision} name="book.epub"/>);
 await waitFor(()=>expect(command.mock.calls.some(call=>call[0]==="source_jobs")).toBe(true));
 fireEvent.click(screen.getByText("执行真实内容转换"));
 await waitFor(()=>expect(resolveQueue).toBeDefined());
 view.rerender(<JobContent sourceId="new-source" sourceRevision={"c".repeat(64)} name="new.epub"/>);
 await act(async()=>{resolveQueue({});await Promise.resolve();});
 expect(command.mock.calls.some(call=>call[0]==="job_execute")).toBe(false);
 expect(screen.queryByText("转换未完成或产物读取失败。不会把失败或未知状态当作成功。")).toBeNull();
});
