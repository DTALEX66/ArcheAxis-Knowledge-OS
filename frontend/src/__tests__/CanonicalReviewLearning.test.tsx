import {findLearningItemButton,getLearningItemButton} from "../test/learningQueue";
import {useDiagnostics, resetDiagnostics} from "../presentation/diagnostics";
import {renderHook} from "@testing-library/react";
import {CoreWorkingStateProvider} from "../presentation/useCoreWorkingState";
import {CoreWorkingStateSession,type WorkingRead} from "../presentation/coreWorkingState";
import type { Editor } from "@tiptap/core";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CanonicalKnowledgeSpace } from "../spaces/CanonicalKnowledgeSpace";
import { CanonicalLearningSpace } from "../spaces/CanonicalLearningSpace";
import { ApiError } from "../api/client";
import {useState} from "react";
const bridge = vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
beforeEach(resetDiagnostics);
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
  await screen.findByText(/尚未保存 · 当前已保存版本/);
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
  await screen.findByLabelText("文档草稿编辑器");await user.click(screen.getByRole("button",{name:"保存草稿"}));
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
  const qualificationDebug=vi.spyOn(console,"debug").mockImplementation(()=>{}); const diagnostics = renderHook(useDiagnostics);
  await user.click(screen.getByRole("button",{name:/Core 证据与资格回执/}));
  expect(diagnostics.result.current.map(entry => [null, entry.label, entry.payload]).some(([,label,payload])=>label==="Core 证据与资格回执"&&JSON.stringify(payload).includes('"local_execution_pass":false'))).toBe(true);
  expect(screen.queryByText(/local_execution_pass/)).not.toBeInTheDocument();
  expect(qualificationDebug).not.toHaveBeenCalled(); qualificationDebug.mockRestore();
  expect(screen.getByRole("button",{name:"接受当前候选"})).toBeDisabled();
  await user.type(screen.getByLabelText("审核者"),"测试使用者");await user.type(screen.getByLabelText("审核备注"),"保留判断依据");
  await user.click(screen.getByRole("button",{name:"接受当前候选"}));
  await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("knowledge_review",{id:"k1",body:{action:"accepted",reviewer:"测试使用者",note:"保留判断依据",expected_version:"sha-version"}}));
  expect(await screen.findByRole("status")).toHaveTextContent("审核未完成");expect(screen.getByLabelText("审核备注")).toHaveValue("保留判断依据");
 });
 it.each([["candidate","候选"],["accepted","已接受"],["rejected","未获允许"],["future_state","状态未知"]])("presents knowledge %s in Chinese while preserving its identity and review gate",async(status,label)=>{
  bridge.call.mockImplementation(async(op:string)=>{
   if(op==="search")return {items:[{knowledge_id:"k1",head:"固定知识正文",status,active:status==="accepted"}],transforms:[]};
   if(op==="knowledge_get")return {knowledge_id:"k1",body:"固定知识正文",version:"fixed-version",status,title:"固定知识"};
   if(op==="knowledge_qualification")return {};
   if(op==="courses_list")return {courses:[]};
   throw new Error(op);
  });
  const trail=vi.fn();render(<CanonicalKnowledgeSpace showMachine={false} onTrail={trail}/>);const user=userEvent.setup();
  await user.click(screen.getByRole("button",{name:"搜索"}));
  const candidates=screen.getByRole("list",{name:"知识候选列表"});expect(candidates).toHaveTextContent(label);
  await user.click(within(candidates).getByRole("button",{name:"固定知识正文"}));
  expect(await screen.findByRole("article",{name:"候选对照"})).toHaveTextContent(`状态 ${label} · 版本 fixed-version`);
  expect(trail).toHaveBeenLastCalledWith([expect.anything(),expect.objectContaining({id:"knowledge:k1",detail:`k1 · 版本 fixed-version · ${label}`})]);
  expect(screen.getByRole("button",{name:"由当前知识建立学习问题"})).toHaveProperty("disabled",status!=="accepted");
  expect(bridge.call.mock.calls.some(([op])=>["knowledge_review","assessment_create","learning_reference"].includes(op))).toBe(false);
 });
 it.each(["learning_reference","assessment_create"])("does not blame knowledge acceptance when %s is unavailable",async(failedOperation)=>{
  bridge.call.mockImplementation(async(op:string)=>{
   if(op==="search")return {items:[{knowledge_id:"k1",head:"可学习知识",status:"accepted",active:true}],transforms:[]};
   if(op==="knowledge_get")return {knowledge_id:"k1",body:"已保存正文",version:"fixed-version",status:"accepted",title:"可学习知识"};
   if(op==="knowledge_qualification")return {};
   if(op==="courses_list")return {courses:[]};
   if(op===failedOperation)throw new ApiError(503,"Core offline /api/assessment","offline");
   if(op==="learning_reference")return {};
   throw new Error(op);
  });
  const onLearning=vi.fn();render(<CanonicalKnowledgeSpace showMachine={false} onLearning={onLearning}/>);const user=userEvent.setup();
  await user.click(screen.getByRole("button",{name:"搜索"}));await user.click(await screen.findByRole("button",{name:"可学习知识"}));
  await user.click(await screen.findByRole("button",{name:"由当前知识建立学习问题"}));
  expect(await screen.findByRole("status")).toHaveTextContent("学习问题创建未完成");
  expect(screen.getByText(/离线：请在桌面应用中使用此功能/)).toBeInTheDocument();
  expect(screen.queryByText(/Core|仅允许当前有效、已接受的知识/)).not.toBeInTheDocument();
  expect(screen.getByRole("article",{name:"候选对照"})).toHaveTextContent("状态 已接受");
  expect(onLearning).not.toHaveBeenCalled();
  expect(bridge.call.mock.calls.filter(([op])=>op===failedOperation)).toHaveLength(1);
  if(failedOperation==="learning_reference")expect(bridge.call.mock.calls.some(([op])=>op==="assessment_create")).toBe(false);
 });
 it("keeps review errors in diagnostics and the answer editable after an explicit refusal",async()=>{
  const rawError="Core REVIEW_CONTRACT /api/learning refused";
  bridge.call.mockImplementation(async(op:string)=>{
   if(op==="learning_items")return {items:[{item_key:"a1"}]};
   if(op==="learning_state")return {item_key:"a1",learner:{assessment:{assessment_id:"assess",question:"实际问题",content:"核对内容",knowledge_version:"kv"}},machine:{status:"not_recorded"}};
   if(op==="learning_history")return {events:[]};
   if(op==="learning_review")throw new ApiError(422,rawError);
   throw new Error(op);
  });
  render(<CanonicalLearningSpace/>);const diagnostics=renderHook(useDiagnostics);const user=userEvent.setup();
  await user.click(await findLearningItemButton("a1"));await user.type(screen.getByLabelText("本次答案"),"保留我的答案");
  await user.click(screen.getByRole("button",{name:"查看答案与核对内容"}));await user.click(screen.getByLabelText("回答正确"));await user.selectOptions(screen.getByLabelText("学习者自评"),"3");
  await user.click(screen.getByRole("button",{name:"记录复习结果"}));
  const status=await screen.findByRole("status");expect(status).toHaveTextContent("复习提交未完成");expect(status).toHaveTextContent("答案仍保留");
  expect(status).not.toHaveTextContent(/Core|REVIEW_CONTRACT|422|\/api/);expect(screen.getByLabelText("本次答案")).toHaveValue("保留我的答案");expect(screen.getByLabelText("本次答案")).toBeEnabled();
  await user.click(screen.getByRole("button",{name:"状态与诊断：学习操作错误详情"}));
  expect(diagnostics.result.current[0].payload).toEqual({message:rawError,status:422,code:"unavailable"});
  expect(bridge.call.mock.calls.filter(([op])=>op==="learning_review")).toHaveLength(1);
 });
 it("presents a failed review preflight without leaking its error or submitting the answer",async()=>{
  let server:WorkingRead={schema:"archeaxis.ui-working-state/v1",workspace_id:"a".repeat(32),restore_epoch:"initial",state_revision:0,state:{drafts:{},opened_documents:[],active_document:null,page_id:"06",pending_original:null},draft_digests:{},pending_document_id:null,recovery_candidates:null,recovery_requires_confirmation:false};
  const session=new CoreWorkingStateSession({read:async()=>structuredClone(server),write:vi.fn(async request=>{server={...server,state:structuredClone(request.state),state_revision:server.state_revision+1};return structuredClone(server);}),clearSaved:vi.fn(),recover:vi.fn()});await session.load();
  const rawError="Core journal DTO rejected";vi.spyOn(session,"freezeReview").mockRejectedValue(new Error(rawError));
  bridge.call.mockImplementation(async(op:string)=>{
   if(op==="learning_items")return {items:[{item_key:"a1"}]};
   if(op==="learning_state")return {item_key:"a1",learner:{assessment:{assessment_id:"assess",question:"实际问题",content:"核对内容",knowledge_version:"kv"}},machine:{status:"not_recorded"}};
   if(op==="learning_history")return {events:[]};
   throw new Error(op);
  });
  render(<CoreWorkingStateProvider session={session}><CanonicalLearningSpace initialItemKey="a1"/></CoreWorkingStateProvider>);const user=userEvent.setup();const diagnostics=renderHook(useDiagnostics);
  await user.type(await screen.findByLabelText("本次答案"),"预先保留的答案");await user.click(screen.getByRole("button",{name:"查看答案与核对内容"}));await user.click(screen.getByLabelText("回答正确"));await user.selectOptions(screen.getByLabelText("学习者自评"),"3");
  await user.click(screen.getByRole("button",{name:"记录复习结果"}));
  const status=await screen.findByRole("status");expect(status).toHaveTextContent("未发送复习，答案仍可编辑");expect(status).not.toHaveTextContent(/Core|journal|DTO/);
  expect(screen.getByLabelText("本次答案")).toHaveValue("预先保留的答案");expect(screen.getByLabelText("本次答案")).toBeEnabled();
  expect(bridge.call.mock.calls.some(([op])=>op==="learning_review")).toBe(false);expect(session.getSnapshot().state.pending_reviews).toBeUndefined();
  await user.click(screen.getByRole("button",{name:"状态与诊断：学习操作错误详情"}));expect(diagnostics.result.current[0].payload).toEqual({message:rawError});
 });
 it("separates machine state and retries the same review event after unconfirmed response",async()=>{
  bridge.call.mockImplementation(async(op:string)=>{
   if(op==="learning_items") return {items:[{item_key:"a1",next_review:null}]};
   if(op==="learning_state") return {item_key:"a1",learner:{assessment:{assessment_id:"assess",question:"实际问题",content:"绑定修订中的核对内容",knowledge_version:"kv"}},machine:{status:"not_recorded"}};
   if(op==="learning_history") return {events:[]};
   if(op==="learning_review") throw new Error("unconfirmed");
  });
  render(<CanonicalLearningSpace/>);const user=userEvent.setup();await user.click(await findLearningItemButton("a1"));
  const machineDebug=vi.spyOn(console,"debug").mockImplementation(()=>{}); const diagnostics = renderHook(useDiagnostics);
  await user.click(await screen.findByRole("button",{name:/机器能力/}));
  expect(diagnostics.result.current.map(entry => [null, entry.label, entry.payload]).some(([,label,payload])=>label==="机器能力详细记录"&&JSON.stringify(payload).includes("not_recorded"))).toBe(true);
  expect(screen.queryByText(/not_recorded/)).not.toBeInTheDocument();
  expect(machineDebug).not.toHaveBeenCalled(); machineDebug.mockRestore();await user.type(screen.getByLabelText("本次答案"),"本次实际答案");
  expect(screen.getByText("实际问题")).toBeInTheDocument();expect(screen.queryByText("绑定修订中的核对内容")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button",{name:"查看答案与核对内容"}));expect(screen.getByText("绑定修订中的核对内容")).toBeInTheDocument();
  await user.click(screen.getByLabelText("回答不正确"));await user.selectOptions(screen.getByLabelText("学习者自评"),"1");
  await user.click(screen.getByRole("button",{name:"记录复习结果"}));await screen.findByText(/提交未确认/);
  expect(screen.queryByText(/复习提交未完成|复习记录已保存/)).not.toBeInTheDocument();
  await user.click(getLearningItemButton("a1"));
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
  await findLearningItemButton("a2");expect(bridge.call.mock.calls.filter(([op])=>op==="learning_state")).toHaveLength(0);
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
  render(<CanonicalLearningSpace/>);const user=userEvent.setup();await user.click(await findLearningItemButton("a1"));
  await user.type(screen.getByLabelText("本次答案"),"answer");await user.click(screen.getByRole("button",{name:"查看答案与核对内容"}));await user.click(screen.getByLabelText("回答正确"));await user.selectOptions(screen.getByLabelText("学习者自评"),"3");await user.click(screen.getByRole("button",{name:"记录复习结果"}));
  await screen.findByText("已读回新状态");expect(screen.getByLabelText("本次答案")).toHaveValue("");expect(screen.getByLabelText("本次答案")).not.toBeDisabled();expect(screen.getByText(/已读回 1 条复习事件/)).toBeInTheDocument();
 });

});


it("SIMULATED queue and breadcrumb show shared titles while selecting each exact long item key",async()=>{
  bridge.call.mockReset();
  const keys=[`course:${"a".repeat(64)}:artifact:${"b".repeat(64)}`,`course:${"c".repeat(64)}:artifact:${"d".repeat(64)}`];
  bridge.call.mockImplementation(async(operation:string,payload:Record<string,unknown>={})=>{
    if(operation==="learning_items")return {items:keys.map(item_key=>({item_key,display_title:"同名学习主题",next_review:null})),count:2};
    if(operation==="learning_state")return {item_key:payload.item_key,learner:{assessment:{assessment_id:`assessment_${payload.item_key}`,question:"固定问题",content:"固定核对内容",knowledge_version:"fixed-version"}},machine:{status:"not_recorded"}};
    if(operation==="learning_history")return {events:[]};
    throw new Error(operation);
  });
  const onTrail=vi.fn(),selected=vi.fn();render(<CanonicalLearningSpace onTrail={onTrail} onItemSelected={selected}/>);
  await waitFor(()=>expect(screen.getAllByRole("button",{name:"同名学习主题"})).toHaveLength(2));
  for(const key of keys){
    const button=getLearningItemButton(key);expect(button).toHaveTextContent("同名学习主题");
    expect(screen.queryByRole("button",{name:key})).not.toBeInTheDocument();
    fireEvent.click(button);
    await waitFor(()=>expect(onTrail).toHaveBeenLastCalledWith([
      expect.objectContaining({id:"section:review"}),
      expect.objectContaining({id:`item:${key}`,label:"同名学习主题"}),
    ]));
    expect(screen.getByLabelText("学习项目键")).toHaveValue(key);
  }
  expect(selected.mock.calls).toEqual(keys.map(key=>[key]));
  expect(bridge.call.mock.calls.filter(([operation])=>operation==="learning_state").map(([,payload])=>payload)).toEqual(keys.map(item_key=>({item_key})));
  expect(bridge.call.mock.calls.some(([operation])=>["learning_review","assessment_create","learning_reference"].includes(operation))).toBe(false);
});

it("SIMULATED shell selection echo does not reread the just-opened learning item",async()=>{
 bridge.call.mockReset();
 bridge.call.mockImplementation(async(operation:string,payload:Record<string,unknown>={})=>{
  if(operation==="learning_items")return {items:[{item_key:"echo-key",display_title:"固定学习主题",next_review:null}],count:1};
  if(operation==="learning_state")return {item_key:payload.item_key,learner:{},machine:{status:"not_recorded"}};
  if(operation==="learning_history")return {events:[]};
  throw new Error(operation);
 });
 function ShellEcho(){const [key,setKey]=useState<string>();return <CanonicalLearningSpace initialItemKey={key} onItemSelected={setKey}/>;}
 render(<ShellEcho/>);fireEvent.click(await screen.findByRole("button",{name:"固定学习主题"}));
 await screen.findByRole("heading",{name:"复习题"});await act(async()=>{await Promise.resolve();});
 expect(bridge.call.mock.calls.filter(([op])=>op==="learning_state")).toEqual([["learning_state",{item_key:"echo-key"}]]);
 expect(bridge.call.mock.calls.filter(([op])=>op==="learning_history")).toEqual([["learning_history",{item_key:"echo-key"}]]);
});

it.each([
 ["workspace","b".repeat(32),"initial",false],
 ["restore epoch","a".repeat(32),"b".repeat(32),false],
 ["recovery confirmation","a".repeat(32),"initial",true],
] as const)("SIMULATED selection dedup does not hide a changed %s",async(_label,workspace_id,restore_epoch,recovery)=>{
 bridge.call.mockReset();
 bridge.call.mockImplementation(async(operation:string,payload:Record<string,unknown>={})=>{
  if(operation==="learning_items")return {items:[{item_key:"echo-key",display_title:"固定学习主题",next_review:null}],count:1};
  if(operation==="learning_state")return {item_key:payload.item_key,learner:{},machine:{status:"not_recorded"}};
  if(operation==="learning_history")return {events:[]};
  throw new Error(operation);
 });
 const initial:WorkingRead={schema:"archeaxis.ui-working-state/v1",workspace_id:"a".repeat(32),restore_epoch:"initial",state_revision:0,state:{drafts:{},opened_documents:[],active_document:null,page_id:"06",pending_original:null},draft_digests:{},pending_document_id:null,recovery_candidates:null,recovery_requires_confirmation:false};
 async function sessionFor(read:WorkingRead){const session=new CoreWorkingStateSession({read:async()=>structuredClone(read),write:vi.fn().mockRejectedValue(new Error("unexpected write")),clearSaved:vi.fn(),recover:vi.fn()});await session.load();return session;}
 const first=await sessionFor(initial),next=await sessionFor({...initial,workspace_id,restore_epoch,recovery_requires_confirmation:recovery});
 const view=(session:CoreWorkingStateSession)=><CoreWorkingStateProvider session={session}><CanonicalLearningSpace initialItemKey="echo-key"/></CoreWorkingStateProvider>;
 const {rerender}=render(view(first));await screen.findByRole("heading",{name:"复习题"});
 expect(bridge.call.mock.calls.filter(([op])=>op==="learning_state")).toHaveLength(1);
 rerender(view(next));await act(async()=>{await Promise.resolve();});
 if(recovery){
  expect(bridge.call.mock.calls.filter(([op])=>op==="learning_state")).toHaveLength(1);
  const ready=await sessionFor({...initial,workspace_id,restore_epoch,recovery_requires_confirmation:false});rerender(view(ready));
 }
 await waitFor(()=>expect(bridge.call.mock.calls.filter(([op])=>op==="learning_state")).toHaveLength(2));
 expect(bridge.call.mock.calls.every(([op])=>["learning_items","learning_state","learning_history"].includes(op))).toBe(true);
});
