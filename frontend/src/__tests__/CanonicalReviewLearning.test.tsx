import {CoreWorkingStateProvider} from "../presentation/useCoreWorkingState";
import {CoreWorkingStateSession,type WorkingRead} from "../presentation/coreWorkingState";
import type { Editor } from "@tiptap/core";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CanonicalKnowledgeSpace } from "../spaces/CanonicalKnowledgeSpace";
import { CanonicalLearningSpace } from "../spaces/CanonicalLearningSpace";
const bridge = vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
describe("finite knowledge and learning commands",()=>{
 beforeEach(()=>{bridge.call.mockReset();});
 it("guards both closing and replacing an unsaved search document",async()=>{
  const doc={document_id:"original",title:"原创内容",source_id:null,source_revision:null,version:1,content_sha256:"hash",editor_json:{type:"doc",content:[{type:"paragraph",content:[{type:"text",text:"随手记录"}]}]},text_projection:"随手记录",blocks:[]};
  const second={...doc,document_id:"second",title:"第二文档"};
  bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>{
   if(op==="search")return {items:[],transforms:[],documents:[{...doc,head:"note"},{...second,head:"second"}]};
   if(op==="sources_list")return {sources:[]};if(op==="documents_list")return {documents:[doc,second]};
   if(op==="document_get")return payload.document_id==="second"?second:doc;
   throw new Error(op);
  });
  const confirm=vi.spyOn(window,"confirm").mockReturnValue(false);
  render(<CanonicalKnowledgeSpace/>);const user=userEvent.setup();await user.click(screen.getByRole("button",{name:"搜索"}));
  await user.click(await screen.findByRole("button",{name:"原创内容 · 版本 1"}));
  const textbox=await screen.findByRole("textbox",{name:"文档草稿"});
  fireEvent.compositionStart(textbox);act(()=>{(textbox as HTMLElement & {editor:Editor}).editor.commands.setContent({type:"doc",content:[{type:"paragraph",content:[{type:"text",text:"Unsaved searched document"}]}]},{emitUpdate:true});});
  await screen.findByText(/尚未保存 · 当前持久化版本/);
  await user.click(screen.getByRole("button",{name:"关闭搜索文档"}));
  expect(screen.getByRole("textbox",{name:"文档草稿"})).toHaveTextContent("Unsaved searched document");
  await user.click(screen.getByRole("button",{name:"第二文档 · 版本 1"}));
  expect(screen.getByRole("textbox",{name:"文档草稿"})).toHaveTextContent("Unsaved searched document");
  expect(confirm).toHaveBeenCalledTimes(2);confirm.mockRestore();
 });
 it("searches an original unverified document and opens the existing editor without knowledge acceptance",async()=>{
  const doc={document_id:"original",title:"原创内容",source_id:null,source_revision:null,version:1,content_sha256:"hash",editor_json:{type:"doc",content:[{type:"paragraph",content:[{type:"text",text:"随手记录"}]}]},text_projection:"随手记录",blocks:[]};
  bridge.call.mockImplementation(async(op:string,payload:Record<string,unknown>)=>{
   if(op==="search")return {items:[],transforms:[],documents:[{...doc,head:"随手记录"}],document_count:1};
   if(op==="sources_list")return {sources:[]};if(op==="documents_list")return {documents:[doc]};
   if(op==="document_get")return doc;
   if(op==="document_draft")return {...doc,version:2,editor_json:(payload.body as Record<string,unknown>).editor_json};
   if(op==="document_checks")return {document_id:"original",version:1,content_sha256:"hash",historical:false,default_status:"unverified",checks_capped:false,next_offset:null,checks:[]};
   throw new Error(op);
  });
  render(<CanonicalKnowledgeSpace/>);const user=userEvent.setup();await user.click(screen.getByRole("button",{name:"搜索"}));
  await user.click(await screen.findByRole("button",{name:"原创内容 · 版本 1"}));
  await screen.findByLabelText("版本化草稿编辑器");await user.click(screen.getByRole("button",{name:"保存草稿"}));
  await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("document_draft",expect.anything()));
  expect(screen.queryByRole("button",{name:"接受当前候选"})).not.toBeInTheDocument();
 });
 it("shows evidence before a user's version-checked review and preserves note on conflict",async()=>{
  bridge.call.mockImplementation(async(op:string)=>{
   if(op==="search") return {items:[{knowledge_id:"k1",head:"候选正文",status:"candidate",active:false}],transforms:[]};
   if(op==="knowledge_get") return {knowledge_id:"k1",body:"候选正文",version:"sha-version",status:"candidate",title:"候选"};
   if(op==="knowledge_qualification") return {local_execution_pass:false};
   if(op==="knowledge_review") throw new Error("conflict");
  });
  render(<CanonicalKnowledgeSpace/>);const user=userEvent.setup();
  await user.click(screen.getByRole("button",{name:"搜索"}));await user.click(await screen.findByRole("button",{name:"候选正文"}));
  const qualificationDebug=vi.spyOn(console,"debug").mockImplementation(()=>{});
  await user.click(screen.getByRole("button",{name:/Core 证据与资格回执/}));
  expect(qualificationDebug.mock.calls.some(([,label,payload])=>label==="Core 证据与资格回执"&&JSON.stringify(payload).includes('"local_execution_pass":false'))).toBe(true);
  expect(screen.queryByText(/local_execution_pass/)).not.toBeInTheDocument();
  qualificationDebug.mockRestore();
  expect(screen.getByRole("button",{name:"接受当前候选"})).toBeDisabled();
  await user.type(screen.getByLabelText("审核者"),"测试使用者");await user.type(screen.getByLabelText("审核备注"),"保留判断依据");
  await user.click(screen.getByRole("button",{name:"接受当前候选"}));
  await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("knowledge_review",{id:"k1",body:{action:"accepted",reviewer:"测试使用者",note:"保留判断依据",expected_version:"sha-version"}}));
  expect(await screen.findByRole("status")).toHaveTextContent("审核未完成");expect(screen.getByLabelText("审核备注")).toHaveValue("保留判断依据");
 });
 it("separates machine state and retries the same review event after unconfirmed response",async()=>{
  bridge.call.mockImplementation(async(op:string)=>{
   if(op==="learning_items") return {items:[{item_key:"a1",next_review:null}]};
   if(op==="learning_state") return {item_key:"a1",learner:{assessment:{assessment_id:"assess",question:"实际问题",content:"绑定修订中的核对内容",knowledge_version:"kv"}},machine:{status:"not_recorded"}};
   if(op==="learning_history") return {events:[]};
   if(op==="learning_review") throw new Error("unconfirmed");
  });
  render(<CanonicalLearningSpace/>);const user=userEvent.setup();await user.click(await screen.findByRole("button",{name:"a1"}));
  const machineDebug=vi.spyOn(console,"debug").mockImplementation(()=>{});
  await user.click(await screen.findByRole("button",{name:/机器能力/}));
  expect(machineDebug.mock.calls.some(([,label,payload])=>label==="机器能力记录回执"&&JSON.stringify(payload).includes("not_recorded"))).toBe(true);
  expect(screen.queryByText(/not_recorded/)).not.toBeInTheDocument();
  machineDebug.mockRestore();await user.type(screen.getByLabelText("本次答案"),"本次实际答案");
  expect(screen.getByText("实际问题")).toBeInTheDocument();expect(screen.queryByText("绑定修订中的核对内容")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button",{name:"查看答案与核对内容"}));expect(screen.getByText("绑定修订中的核对内容")).toBeInTheDocument();
  await user.click(screen.getByLabelText("回答不正确"));await user.selectOptions(screen.getByLabelText("学习者自评"),"1");
  await user.click(screen.getByRole("button",{name:"记录复习结果"}));await screen.findByText(/提交未确认/);
  await user.click(screen.getByRole("button",{name:"a1"}));
  expect(screen.getByLabelText("本次答案")).toHaveValue("本次实际答案");
  expect(screen.getByLabelText("本次答案")).toBeDisabled();
  expect(screen.getByLabelText("学习者自评")).toBeDisabled();
  expect(screen.getByLabelText("学习项目键")).toBeDisabled();
  await user.click(screen.getByRole("button",{name:"记录复习结果"}));
  const writes=bridge.call.mock.calls.filter(([op])=>op==="learning_review");expect(writes).toHaveLength(2);expect(writes[0][1]).toEqual(writes[1][1]);
  expect(writes[0][1].body).toMatchObject({correct:false,rating:1,assessment_id:"assess",knowledge_version:"kv",answer:"本次实际答案"});
 });
 it("restores a Core-retained prior-epoch review and retries only its original event payload",async()=>{
  const body={item_key:"a1",client_event_id:"saved_event",answer:"原答案",assessment_id:"assess",knowledge_version:"kv",correct:false,rating:1};
  const entry={item_key:"a1",client_event_id:"saved_event",origin_restore_epoch:"initial",body};
  let server:WorkingRead={schema:"archeaxis.ui-working-state/v1",workspace_id:"a".repeat(32),restore_epoch:"c".repeat(32),state_revision:1,state:{drafts:{},opened_documents:[],active_document:null,page_id:"12",pending_reviews:{saved_event:entry}},draft_digests:{},pending_document_id:null,recovery_candidates:null,recovery_requires_confirmation:false};
  const write=vi.fn(async request=>{server={...server,state:structuredClone(request.state),state_revision:server.state_revision+1};return structuredClone(server);});
  const session=new CoreWorkingStateSession({read:async()=>structuredClone(server),write,clearSaved:vi.fn(),recover:vi.fn()});await session.load();
  bridge.call.mockImplementation(async(op:string)=>{
   if(op==="learning_items")return {items:[{item_key:"a1"}]};
   if(op==="learning_state")return {item_key:"a1",learner:{assessment:{assessment_id:"assess",question:"独立题干",content:"核对内容",knowledge_version:"kv"}},machine:{status:"not_recorded"}};
   if(op==="learning_history")return {events:[]};
   if(op==="learning_review")throw new Error("ACK unknown again");throw new Error("unexpected");
  });
  render(<CoreWorkingStateProvider session={session}><CanonicalLearningSpace/></CoreWorkingStateProvider>);const user=userEvent.setup();
  await waitFor(()=>expect(screen.getByLabelText("本次答案")).toHaveValue("原答案"));expect(screen.getByLabelText("本次答案")).toBeDisabled();
  await user.click(screen.getByRole("button",{name:"记录复习结果"}));
  await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("learning_review",{body}));
  expect(session.getSnapshot().state.pending_reviews?.saved_event).toEqual(entry);
 });

 it("requires explicit selection of multiple durable review requests and preserves their identities",async()=>{
  const make=(key:string)=>({item_key:key,client_event_id:"event_"+key,origin_restore_epoch:"initial",body:{item_key:key,client_event_id:"event_"+key,answer:"answer_"+key,assessment_id:"assessment_"+key,knowledge_version:"kv",correct:false,rating:1}});
  const a=make("a1"),b=make("a2");
  let server:WorkingRead={schema:"archeaxis.ui-working-state/v1",workspace_id:"a".repeat(32),restore_epoch:"initial",state_revision:1,state:{drafts:{},opened_documents:[],active_document:null,page_id:"06",pending_reviews:{event_a1:a,event_a2:b}},draft_digests:{},pending_document_id:null,recovery_candidates:null,recovery_requires_confirmation:false};
  const write=vi.fn(async request=>{server={...server,state:structuredClone(request.state),state_revision:server.state_revision+1};return structuredClone(server);});const session=new CoreWorkingStateSession({read:async()=>structuredClone(server),write,clearSaved:vi.fn(),recover:vi.fn()});await session.load();
  bridge.call.mockImplementation(async(op:string,payload:any)=>{
   if(op==="learning_items")return {items:[{item_key:"a1"},{item_key:"a2"}]};
   if(op==="learning_state")return {item_key:payload.item_key,learner:{assessment:{assessment_id:"assessment_"+payload.item_key,question:"question_"+payload.item_key,content:"content",knowledge_version:"kv"}},machine:{status:"not_recorded"}};
   if(op==="learning_history")return {events:[]};if(op==="learning_review")throw new Error("synthetic ACK unknown");throw new Error("unexpected mutation");
  });
  render(<CoreWorkingStateProvider session={session}><CanonicalLearningSpace/></CoreWorkingStateProvider>);const user=userEvent.setup();
  await screen.findByRole("button",{name:"a2"});expect(bridge.call.mock.calls.filter(([op])=>op==="learning_state")).toHaveLength(0);
  await user.click(screen.getByRole("button",{name:"恢复复习请求 a2"}));await waitFor(()=>expect(screen.getByLabelText("本次答案")).toHaveValue("answer_a2"));expect(screen.getByLabelText("本次答案")).toBeDisabled();
  await user.click(screen.getByRole("button",{name:"恢复复习请求 a1"}));await waitFor(()=>expect(screen.getByLabelText("本次答案")).toHaveValue("answer_a1"));
  expect(session.getSnapshot().state.pending_reviews).toEqual(server.state.pending_reviews);expect(write).not.toHaveBeenCalled();expect(bridge.call.mock.calls.filter(([op])=>op==="learning_review")).toHaveLength(0);
  await user.click(screen.getByRole("button",{name:"记录复习结果"}));await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("learning_review",{body:a.body}));expect(session.getSnapshot().state.pending_reviews?.event_a2).toEqual(b);
 });

 it("reads the updated state after a confirmed review while the submission is still busy",async()=>{
  let reviewed=false;
  bridge.call.mockImplementation(async(op:string)=>{
   if(op==="learning_items")return {items:[{item_key:"a1"}]};
   if(op==="learning_state")return {item_key:"a1",learner:{assessment:{assessment_id:"assessment",question:reviewed?"已读回新状态":"提交前状态",content:"content",knowledge_version:"kv"}},machine:{status:"not_recorded"}};
   if(op==="learning_history")return {events:reviewed?[{event_id:"event"}]:[]};
   if(op==="learning_review"){reviewed=true;return {next_review:"tomorrow"};}throw new Error("unexpected");
  });
  render(<CanonicalLearningSpace/>);const user=userEvent.setup();await user.click(await screen.findByRole("button",{name:"a1"}));
  await user.type(screen.getByLabelText("本次答案"),"answer");await user.click(screen.getByRole("button",{name:"查看答案与核对内容"}));await user.click(screen.getByLabelText("回答正确"));await user.selectOptions(screen.getByLabelText("学习者自评"),"3");await user.click(screen.getByRole("button",{name:"记录复习结果"}));
  await screen.findByText("已读回新状态");expect(screen.getByLabelText("本次答案")).toHaveValue("");expect(screen.getByLabelText("本次答案")).not.toBeDisabled();expect(screen.getByText(/已读回 1 条复习事件/)).toBeInTheDocument();
 });

});
