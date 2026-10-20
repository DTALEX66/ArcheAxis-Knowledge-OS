import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { CanonicalTeachingSpace } from "../spaces/CanonicalTeachingSpace";
import { CoreWorkingStateSession, type TeachingDraft, type WorkingRead, type WorkingTransport } from "../presentation/coreWorkingState";
import { CoreWorkingStateProvider } from "../presentation/useCoreWorkingState";
import { documentRequestIdentity } from "../presentation/documentRequestIdentity";

const call=vi.hoisted(()=>vi.fn());
vi.mock("../api/core",()=>({coreCommand:call}));
vi.mock("../spaces/CanonicalLearningSpace",()=>({CanonicalLearningSpace:()=>null}));
beforeEach(()=>{call.mockReset();call.mockImplementation(async(op:string)=>{
  if(op==="teaching_list")return {items:[],next_cursor:null};
  throw new Error(`Unexpected ${op}`);
});});
function fixture(){
  let server:WorkingRead={schema:"archeaxis.ui-working-state/v1",workspace_id:"a".repeat(32),restore_epoch:"initial",state_revision:0,state:{drafts:{},opened_documents:[],active_document:null,page_id:"11",pending_original:null},draft_digests:{},pending_document_id:null,recovery_candidates:null,recovery_requires_confirmation:false};
  const transport:WorkingTransport={read:async()=>structuredClone(server),write:vi.fn(async request=>{server={...server,state:structuredClone(request.state),state_revision:server.state_revision+1};return structuredClone(server);}),clearSaved:vi.fn(),recover:vi.fn()};
  return {transport,session:new CoreWorkingStateSession(transport),server:()=>server};
}
function component(session:CoreWorkingStateSession,pageId="11",initialItemKey?:string){return <CoreWorkingStateProvider session={session}><CanonicalTeachingSpace pageId={pageId} initialItemKey={initialItemKey}/></CoreWorkingStateProvider>;}
it("reopens unsubmitted teach-back and feedback independently after a new Core session",async()=>{
  const f=fixture();await f.session.load();const first=render(component(f.session));
  fireEvent.change(screen.getByLabelText("用途"),{target:{value:"未提交复述"}});fireEvent.change(screen.getByLabelText("内容"),{target:{value:"  我的理解\n第二行  "}});
  await act(async()=>{await f.session.flush();});first.rerender(component(f.session,"12"));
  await waitFor(()=>expect(screen.getByLabelText("内容")).toHaveValue(""));fireEvent.change(screen.getByLabelText("内容"),{target:{value:"未提交反馈总结"}});
  fireEvent.change(screen.getByLabelText("反馈分类"),{target:{value:"expression_fit"}});await act(async()=>{await f.session.flush();});first.unmount();
  const reopened=new CoreWorkingStateSession(f.transport);await reopened.load();const next=render(component(reopened));
  await waitFor(()=>expect(screen.getByLabelText("内容")).toHaveValue("  我的理解\n第二行  "));expect(screen.getByLabelText("用途")).toHaveValue("未提交复述");
  next.rerender(component(reopened,"12"));await waitFor(()=>expect(screen.getByLabelText("内容")).toHaveValue("未提交反馈总结"));expect(screen.getByLabelText("反馈分类")).toHaveValue("expression_fit");
  expect(call.mock.calls.some(([op])=>["teaching_create","document_create","learning_review"].includes(op))).toBe(false);
});
function draft(page:"08"|"11"|"12"="11",context:string|null=null):TeachingDraft{return {page_id:page,context_item_key:context,form:{kind:page==="08"?"requirement":page==="11"?"teach_back":"feedback",purpose:"未提交用途",content:"  原始正文\n总结  ",scope:"personal",privacy:"local_only",assisted:false,feedback_class:page==="12"?"mastery":null,rubric_version:"",producer_kind:"human_authored"},knowledge_id:null,course_id:null,item_key:null,assessment_id:null,parent:null,preparation:null,saved_preparation:"",pending_record:null};}
function preparationEntry():TeachingDraft {
  const entry=draft("12");entry.form.content="frozen body";
  entry.preparation_attempt={operation:"document_create",payload:{body:{create_request_id:"fixed_preparation",title:entry.form.purpose,editor_json:{type:"doc",content:[{type:"paragraph",attrs:{block_id:"fixed"},content:[{type:"text",text:entry.form.content}]}]}}},snapshot:JSON.stringify({purpose:entry.form.purpose,content:entry.form.content}),persistedPurpose:entry.form.purpose,expectedTitle:entry.form.purpose};return entry;
}
it("clears a frozen preparation through unknown ACK readback while preserving typing made during clearance",async()=>{
  const f=fixture(),entry=preparationEntry();f.server().state.teaching_drafts={"12:":entry};await f.session.load();
  const write=f.transport.write;f.transport.write=async request=>{await write(request);f.session.rememberTeachingDraft("12:",{...entry,form:{...entry.form,content:"later typing"}});throw new Error("clear ACK lost");};
  await expect(f.session.finishTeachingPreparation("12:",entry.preparation_attempt!,{document_id:"doc_fixed",version:1,title:entry.form.purpose},entry.preparation_attempt!.snapshot)).rejects.toThrow("clear ACK lost");
  expect(f.session.getSnapshot().state.teaching_drafts?.["12:"].preparation_attempt).toEqual(entry.preparation_attempt);
  await f.session.load();const retained=f.session.getSnapshot().state.teaching_drafts?.["12:"];expect(retained?.form.content).toBe("later typing");expect(retained?.preparation_attempt).toBeUndefined();expect(retained?.preparation?.document_id).toBe("doc_fixed");
  expect(f.session.getSnapshot().status).toBe("unsaved");f.transport.write=write;await f.session.flush();expect(f.server().state.teaching_drafts?.["12:"].form.content).toBe("later typing");
});
it("reconciles a cold-reopened draft whose Document save completed before the ACK was lost without appending again",async()=>{
  const f=fixture(),entry=preparationEntry(),create=entry.preparation_attempt!;if(create.operation!=="document_create")throw new Error("fixture");
  entry.preparation={document_id:"doc_existing",version:4,title:entry.form.purpose};entry.preparation_attempt={...create,operation:"document_draft",payload:{document_id:"doc_existing",body:{expected_version:4,editor_json:create.payload.body.editor_json}}};f.server().state.teaching_drafts={"12:":entry};await f.session.load();
  const editor_json=create.payload.body.editor_json,nodes=editor_json.content;
  const doc={document_id:"doc_existing",version:5,title:entry.form.purpose,source_id:null,source_revision:null,revision_basis:null,content_sha256:"b".repeat(64),editor_json,text_projection:entry.form.content,blocks:nodes.map((node,ordinal)=>({block_id:node.attrs.block_id,kind:"paragraph",ordinal,node_json:node,codec_status:"known",text_projection:entry.form.content}))};
  call.mockImplementation(async(op:string)=>{if(op==="teaching_list")return {items:[],next_cursor:null};if(op==="document_get")return doc;throw new Error(`Unexpected ${op}`);});
  render(component(f.session,"12"));fireEvent.click(screen.getByRole("button",{name:"保存准备正文草稿"}));await screen.findByText(/准备正文已保存并读回/);
  expect(call.mock.calls.some(([op])=>op==="document_draft"||op==="document_create")).toBe(false);expect(f.server().state.teaching_drafts?.["12:"].preparation?.version).toBe(5);expect(f.server().state.teaching_drafts?.["12:"].preparation_attempt).toBeUndefined();
});
function freeze(entry:TeachingDraft){
  entry.knowledge_id="knowledge_v1";
  entry.pending_record={schema:"archeaxis.teaching-record/v2",record_id:"teaching_stable",kind:entry.form.kind,knowledge_id:"knowledge_v1",knowledge_version:"knowledge_v1",course_id:null,parent_id:null,purpose:entry.form.purpose,scope:entry.form.scope,privacy:entry.form.privacy,content:entry.form.content,feedback_class:null,assessment_id:null,rubric_version:null,assisted:false,producer_kind:"human_authored"};
  return entry;
}
function view(record:NonNullable<TeachingDraft["pending_record"]>){return {record:structuredClone(record),content_sha256:"a".repeat(64),withdrawn:false,scoring_status:"not_scored"};}
it("keeps locally invalid rubric text editable when no teaching request was dispatched",async()=>{
  const f=fixture(),entry=draft("08");entry.knowledge_id="knowledge_v1";f.server().state.teaching_drafts={"08:":entry};await f.session.load();render(component(f.session,"08"));
  fireEvent.change(screen.getByLabelText("评测准则版本"),{target:{value:"v 1"}});fireEvent.click(screen.getByRole("button",{name:"登记版本化记录"}));await screen.findByText(/操作未确认完成/);
  expect(screen.getByLabelText("内容")).toBeEnabled();expect(screen.getByLabelText("评测准则版本")).toHaveValue("v 1");expect(call.mock.calls.some(([op])=>op==="teaching_create")).toBe(false);expect(f.session.getSnapshot().state.teaching_drafts?.["08:"].pending_record).toBeNull();
});
it("explicitly releases a definitely refused teaching identity into the unchanged editable draft",async()=>{
  const f=fixture(),entry=freeze(draft("08"));f.server().state.teaching_drafts={"08:":entry};await f.session.load();
  call.mockImplementation(async(op:string)=>{if(op==="teaching_list")return {items:[],next_cursor:null};if(op==="teaching_create")throw new Error("parent withdrawn before insert");throw new Error(`Unexpected ${op}`);});
  render(component(f.session,"08"));fireEvent.click(screen.getByRole("button",{name:"重试同一记录"}));await screen.findByText(/操作未确认完成/);expect(screen.getByLabelText("内容")).toBeDisabled();
  fireEvent.click(screen.getByRole("button",{name:"检查结果并恢复编辑"}));await screen.findByText(/已解除冻结/);expect(screen.getByLabelText("内容")).toBeEnabled();expect(screen.getByLabelText("内容")).toHaveValue(entry.form.content);
  expect(f.transport.write).toHaveBeenCalledWith(expect.objectContaining({release_teaching:{draft_key:"08:",record_id:entry.pending_record!.record_id}}));expect(f.server().state.teaching_drafts?.["08:"].pending_record).toBeNull();
});
it.each([false,true])("retains the frozen record across an unknown release ACK until exact readback, admitted=%s",async admitted=>{
  const f=fixture(),entry=freeze(draft("08"));f.server().state.teaching_drafts={"08:":entry};await f.session.load();
  const write=f.transport.write;f.transport.write=async request=>{if(admitted)await write(request);throw new Error("unknown release ACK");};
  await expect(f.session.releaseTeachingDraft("08:",entry)).rejects.toThrow("unknown release ACK");expect(f.session.getSnapshot().state.teaching_drafts?.["08:"]).toEqual(entry);
  await f.session.load();expect(f.session.getSnapshot().state.teaching_drafts?.["08:"].pending_record).toEqual(admitted?null:entry.pending_record);expect(f.session.getSnapshot().state.teaching_drafts?.["08:"].form).toEqual(entry.form);
});
it("isolates the same teaching page by the original learning item without copying another object's text",async()=>{
  const f=fixture();await f.session.load();const first=render(component(f.session,"11","course:a"));
  fireEvent.change(screen.getByLabelText("内容"),{target:{value:"belongs to A"}});first.rerender(component(f.session,"11","course:b"));expect(screen.getByLabelText("内容")).toHaveValue("");
  fireEvent.change(screen.getByLabelText("内容"),{target:{value:"belongs to B"}});first.rerender(component(f.session,"11","course:a"));expect(screen.getByLabelText("内容")).toHaveValue("belongs to A");
  expect(Object.keys(f.session.getSnapshot().state.teaching_drafts??{})).toEqual(["11:course:a","11:course:b"]);
});
it("retries a cold-reopened frozen teaching identity and clears only its exact draft after matching ACK and get",async()=>{
  const f=fixture(),entry=freeze(draft("08")),other=draft("12");f.server().state.teaching_drafts={"08:":entry,"12:":other};await f.session.load();
  let attempts=0;call.mockImplementation(async(op:string,payload:any)=>{
    if(op==="teaching_list")return {items:[],next_cursor:null};
    if(op==="teaching_create"){if(++attempts===1)throw new Error("lost receipt after write");return {item:view(payload.body),duplicate:true};}
    if(op==="teaching_get")return view(entry.pending_record!);throw new Error(`Unexpected ${op}`);
  });
  const first=render(component(f.session,"08"));expect(screen.getByLabelText("内容")).toBeDisabled();fireEvent.click(screen.getByRole("button",{name:"重试同一记录"}));await screen.findByText(/操作未确认完成/);first.unmount();
  const reopened=new CoreWorkingStateSession(f.transport);await reopened.load();render(component(reopened,"08"));fireEvent.click(screen.getByRole("button",{name:"重试同一记录"}));await screen.findByText("已读回同一客户端记录，未重复创建。");
  const sent=call.mock.calls.filter(([op])=>op==="teaching_create");expect(sent).toHaveLength(2);expect(sent[0][1]).toEqual(sent[1][1]);expect(sent[0][1].body).toEqual(entry.pending_record);
  expect(reopened.getSnapshot().state.teaching_drafts).toEqual({"12:":other});expect(f.server().state.teaching_drafts).toEqual({"12:":other});
});
it.each(["ack","readback"])("retains a frozen draft when %s has the same ID but changed body",async target=>{
  const f=fixture(),entry=freeze(draft("08"));f.server().state.teaching_drafts={"08:":entry};await f.session.load();
  call.mockImplementation(async(op:string,payload:any)=>{
    if(op==="teaching_list")return {items:[],next_cursor:null};
    const wrong={...entry.pending_record!,content:"wrong persisted text"};
    if(op==="teaching_create")return {item:view(target==="ack"?wrong:payload.body),duplicate:false};if(op==="teaching_get")return view(wrong);throw new Error(`Unexpected ${op}`);
  });
  render(component(f.session,"08"));fireEvent.click(screen.getByRole("button",{name:"重试同一记录"}));await screen.findByText(/操作未确认完成/);
  expect(f.session.getSnapshot().state.teaching_drafts?.["08:"]).toEqual(entry);expect(f.server().state.teaching_drafts?.["08:"]).toEqual(entry);expect(screen.getByLabelText("内容")).toHaveValue(entry.form.content);
});
it("retains a draft on an unknown clearance ACK and removes it only after exact Core readback",async()=>{
  const f=fixture(),entry=draft();f.server().state.teaching_drafts={"11:":entry};await f.session.load();
  const write=f.transport.write;f.transport.write=async request=>{await write(request);throw new Error("clearance ACK lost");};
  await expect(f.session.finishTeachingDraft("11:",entry)).rejects.toThrow("clearance ACK lost");expect(f.session.getSnapshot().state.teaching_drafts?.["11:"]).toEqual(entry);
  await f.session.load();expect(f.session.getSnapshot().state.teaching_drafts).toBeUndefined();expect(f.session.getSnapshot().status).toBe("ready");
});
it("does not clear a newer draft and refuses to replay retained text into a changed workspace epoch",async()=>{
  const f=fixture(),entry=draft();f.server().state.teaching_drafts={"11:":entry};await f.session.load();
  const newer={...entry,form:{...entry.form,content:"newer input"}};f.session.rememberTeachingDraft("11:",newer);
  expect(await f.session.finishTeachingDraft("11:",entry)).toBe(false);expect(f.session.getSnapshot().state.teaching_drafts?.["11:"]).toEqual(newer);
  f.server().restore_epoch="b".repeat(32);await f.session.load();render(component(f.session));expect(screen.queryByLabelText("内容")).not.toBeInTheDocument();expect(screen.getByLabelText("保留的教学正文 11:")).toHaveValue("newer input");
  expect(call.mock.calls.some(([op])=>op==="teaching_create")).toBe(false);expect(f.session.getSnapshot().status).toBe("blocked");
});
it("does not apply a recovery candidate until explicit preservation",async()=>{
  const f=fixture(),entry=draft("12");Object.assign(f.server(),{restore_epoch:"b".repeat(32),recovery_requires_confirmation:true,recovery_candidates:{...f.server().state,teaching_drafts:{"12:":entry}}});
  f.transport.recover=async()=>{Object.assign(f.server(),{state:f.server().recovery_candidates,state_revision:1,recovery_candidates:null,recovery_requires_confirmation:false});return structuredClone(f.server());};
  await f.session.load();render(component(f.session,"12"));expect(screen.queryByLabelText("内容")).not.toBeInTheDocument();await act(async()=>f.session.recover("preserve"));expect(screen.getByLabelText("内容")).toHaveValue(entry.form.content);
});
it.each([false,true])("clears only ordinary body input after exact Document readback, retains unsaved teaching metadata: %s",async metadata=>{
  const f=fixture();await f.session.load();let saved:any;
  call.mockImplementation(async(op:string,payload:any)=>{
    if(op==="teaching_list")return {items:[],next_cursor:null};
    if(op==="document_create"){
      const body=payload.body,editor_json=structuredClone(body.editor_json),blocks=editor_json.content.map((node:any,ordinal:number)=>({block_id:node.attrs.block_id,kind:"paragraph",ordinal,node_json:node,text_projection:node.content?.map((child:any)=>child.text).join("")??"",codec_status:"known"}));
      saved={document_id:await documentRequestIdentity(body.create_request_id),version:1,title:body.title,source_id:null,source_revision:null,revision_basis:null,editor_json,blocks,text_projection:blocks.map((b:any)=>b.text_projection).filter(Boolean).join("\n"),content_sha256:"b".repeat(64)};return saved;
    }
    if(op==="document_get")return saved;throw new Error(`Unexpected ${op}`);
  });
  const first=render(component(f.session,"12"));fireEvent.change(screen.getByLabelText("用途"),{target:{value:"普通正文"}});fireEvent.change(screen.getByLabelText("内容"),{target:{value:"未提交反馈总结\n第二行"}});
  if(metadata)fireEvent.change(screen.getByLabelText("反馈分类"),{target:{value:"mastery"}});
  fireEvent.click(screen.getByRole("button",{name:"保存准备正文草稿"}));await screen.findByText(/准备正文已保存并读回/);
  expect(saved.text_projection).toBe("未提交反馈总结\n第二行");expect(call.mock.calls.some(([op])=>op==="teaching_create")).toBe(false);
  if(metadata){await act(async()=>{await f.session.flush();});first.unmount();const reopened=new CoreWorkingStateSession(f.transport);await reopened.load();render(component(reopened,"12"));expect(screen.getByLabelText("反馈分类")).toHaveValue("mastery");expect(screen.getByLabelText("内容")).toHaveValue("未提交反馈总结\n第二行");expect(reopened.getSnapshot().state.teaching_drafts?.["12:"].preparation?.version).toBe(1);}
  else expect(f.session.getSnapshot().state.teaching_drafts).toBeUndefined();
});
it("reuses an already persisted preparation create after lost ACK and cold session reopen instead of duplicating documents",async()=>{
  const f=fixture();await f.session.load();const documents=new Map<string,any>();let lost=true;
  call.mockImplementation(async(op:string,payload:any)=>{
    if(op==="teaching_list")return {items:[],next_cursor:null};
    if(op==="document_create"){
      const body=payload.body,id=await documentRequestIdentity(body.create_request_id),editor_json=structuredClone(body.editor_json),blocks=editor_json.content.map((node:any,ordinal:number)=>({block_id:node.attrs.block_id,kind:"paragraph",ordinal,node_json:node,text_projection:node.content?.map((child:any)=>child.text).join("")??"",codec_status:"known"}));
      if(!documents.has(id))documents.set(id,{document_id:id,version:1,title:body.title,source_id:null,source_revision:null,revision_basis:null,editor_json,blocks,text_projection:blocks.map((b:any)=>b.text_projection).filter(Boolean).join("\n"),content_sha256:"c".repeat(64)});
      if(lost){lost=false;throw new Error("lost ACK after Core persistence");}return documents.get(id);
    }
    if(op==="document_get")return documents.get(payload.document_id);throw new Error(`Unexpected ${op}`);
  });
  const first=render(component(f.session,"12"));fireEvent.change(screen.getByLabelText("用途"),{target:{value:"准备总结"}});fireEvent.change(screen.getByLabelText("内容"),{target:{value:"只应生成一份文档"}});
  fireEvent.click(screen.getByRole("button",{name:"保存准备正文草稿"}));await screen.findByText(/操作未确认完成/);expect(documents.size).toBe(1);first.unmount();
  const reopened=new CoreWorkingStateSession(f.transport);await reopened.load();render(component(reopened,"12"));fireEvent.click(screen.getByRole("button",{name:"保存准备正文草稿"}));await screen.findByText(/准备正文已保存并读回/);
  const creates=call.mock.calls.filter(([op])=>op==="document_create");expect(creates).toHaveLength(2);expect(creates[1][1]).toEqual(creates[0][1]);expect(documents.size).toBe(1);
});
