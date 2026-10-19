import {beforeEach,afterEach,it,expect,vi} from "vitest";
import {render,screen,fireEvent,waitFor,act} from "@testing-library/react";
import {webcrypto} from "node:crypto";
import {ConversationPanel} from "../components/ConversationPanel";
import {conversation,mergeConversationEvents} from "../api/conversation";
import type {ConversationEventDto} from "../api/generated/conversation";
const bridge=vi.hoisted(()=>({call:vi.fn(),configuration:{revision:0} as Record<string,unknown>}));vi.mock("../api/core",()=>({coreCommand:(op:string,p:unknown)=>op==="model_configuration_get"?Promise.resolve(bridge.configuration):bridge.call(op,p)}));
const summary={session_id:"session_a",title:"SYNTHETIC session",last_sequence:0,consumer:"archeaxis"};
const session={schema:"archeaxis.conversation-session/v1",...summary,events:[],requests:[],delivery:"BUFFERED",cross_project_consumer:"UNVERIFIED"};
const catalog={schema:"archeaxis.conversation-catalog/v1",sessions:[summary],limit:16};
it.each(["reject","empty-history"])("preserves the submitted UNKNOWN request after %s history reload",async mode=>{
 let requestId="",reload=false;
 bridge.call.mockImplementation(async(op,p)=>{
  if(op==="conversation_history"&&p.body.session_id&&reload&&mode==="reject")throw Error("SYNTHETIC history unavailable");
  if(op==="conversation_request"&&!p.body.preview){requestId=p.body.request_id;throw Error("SYNTHETIC lost ACK");}
  if(op==="conversation_status")return {schema:"archeaxis.conversation-receipt/v1",session_id:"session_a",request_id:p.body.request_id,state:"completed",answer:{answer:"SYNTHETIC recovered"},delivery:"BUFFERED"};
  return normal(op,p);
 });
 render(<ConversationPanel/>);await selectSession();fireEvent.change(screen.getByLabelText("会话问题"),{target:{value:"question"}});fireEvent.click(screen.getByText("预览会话请求"));await screen.findByText("确认执行同一会话请求");fireEvent.click(screen.getByText("确认执行同一会话请求"));await screen.findByText("请求状态未确认，请查询原请求。");
 reload=true;fireEvent.click(screen.getByText("重读历史"));await screen.findByText(mode==="reject"?"会话历史未确认。":"历史已读回；未确认的提问请继续查询。");
 expect(screen.getByText("预览会话请求")).toBeDisabled();expect(screen.getByLabelText("会话模型通道")).toBeDisabled();fireEvent.click(screen.getByText("查询未确认请求"));await screen.findByRole("img",{name:"小栖：已完成"});
 expect(bridge.call.mock.calls.find(c=>c[0]==="conversation_status")![1].body).toEqual({session_id:"session_a",request_id:requestId});expect(bridge.call.mock.calls.filter(c=>c[0]==="conversation_request")).toHaveLength(2);
 expect(await screen.findByText("SYNTHETIC recovered")).toBeVisible();
});
beforeEach(()=>{vi.stubGlobal("crypto",webcrypto);bridge.call.mockReset();bridge.configuration={revision:0};});afterEach(()=>vi.unstubAllGlobals());
async function selectSession(){await screen.findByText("SYNTHETIC session · 1");fireEvent.change(screen.getByLabelText("已保存会话"),{target:{value:"session_a"}});await screen.findByText("当前会话：SYNTHETIC session");}
function normal(op:string,p:{body:Record<string,unknown>}){if(op==="conversation_history")return p.body.session_id?session:catalog;if(op==="conversation_request")return p.body.preview?{schema:"archeaxis.conversation-preview/v1",plan:{request:{...p.body,preview:false,confirmed_plan_sha256:null}},plan_sha256:"b".repeat(64),network_performed:false}:{schema:"archeaxis.conversation-receipt/v1",session_id:p.body.session_id,request_id:p.body.request_id,state:"completed",answer:{answer:"SYNTHETIC answer"},delivery:"BUFFERED"};if(op==="conversation_cancel")return {...p.body,cancel_requested:true};throw Error(op);}
it.each(["status","cancel"] as const)("sends only the finite identity for %s even when the caller holds a full request",async operation=>{
 const full={session_id:"session_a",request_id:"request_a",question:"private authored question",material:{document_id:"doc_a"},model:"local-model",preview:false};
 bridge.call.mockResolvedValue(operation==="cancel"?{session_id:full.session_id,request_id:full.request_id,cancel_requested:true}:{schema:"archeaxis.conversation-status/v1",session_id:full.session_id,request_id:full.request_id,delivery:"BUFFERED"});
 await conversation[operation](full);
 expect(bridge.call.mock.calls).toEqual([[`conversation_${operation}`,{body:{session_id:full.session_id,request_id:full.request_id}}]]);
});
it("does not preview or infer an unconfigured DEEP companion request",async()=>{
 bridge.call.mockImplementation(async(op,p)=>normal(op,p));render(<ConversationPanel/>);await selectSession();fireEvent.change(screen.getByLabelText("会话模型通道"),{target:{value:"deep"}});fireEvent.change(screen.getByLabelText("会话问题"),{target:{value:"question"}});fireEvent.click(screen.getByText("预览会话请求"));await screen.findByText(/DEEP 尚未配置/);expect(bridge.call.mock.calls.every(c=>c[0]==="conversation_history")).toBe(true);
});
it.each([false,true])("freezes the selected DEEP lane for companion or material conversation (%s)",async withMaterial=>{
 bridge.configuration={revision:3,workspace_id:"a".repeat(32),restore_epoch:"initial"};
 const material=withMaterial?{kind:"document" as const,document_id:"doc_a",version:1,content_sha256:"a".repeat(64),block_id:null}:undefined;
 const resolved={workspace_id:"a".repeat(32),restore_epoch:"initial",schema:"archeaxis.resolved-model/v1",configuration_revision:3,lane:"deep",profile_id:"mtp",purpose:withMaterial?"material":"companion",profile:{model:"aaos-deep-27b-mtp",max_tokens:1024,timeout_s:120}};
 bridge.call.mockImplementation(async(op,p)=>op==="model_configuration_resolve"?resolved:normal(op,p));
 render(<ConversationPanel material={material}/>);await selectSession();fireEvent.change(screen.getByLabelText("会话模型通道"),{target:{value:"deep"}});fireEvent.change(screen.getByLabelText("会话问题"),{target:{value:"question"}});fireEvent.click(screen.getByText("预览会话请求"));await screen.findByText("确认执行同一会话请求");
 expect(bridge.call.mock.calls.find(c=>c[0]==="model_configuration_resolve")![1].body).toEqual({purpose:withMaterial?"material":"companion",lane:"deep"});
 const preview=bridge.call.mock.calls.find(c=>c[0]==="conversation_request")![1].body;expect(preview).toMatchObject({model:"aaos-deep-27b-mtp",max_tokens:1024,model_configuration:resolved});
 fireEvent.click(screen.getByText("确认执行同一会话请求"));await screen.findByText(/回执与历史已读回/);
 expect(bridge.call.mock.calls.filter(c=>c[0]==="model_configuration_resolve")).toHaveLength(1);
 expect(bridge.call.mock.calls.filter(c=>c[0]==="conversation_request")[1][1].body).toEqual({...preview,preview:false,confirmed_plan_sha256:"b".repeat(64)});
 fireEvent.change(screen.getByLabelText("会话模型通道"),{target:{value:"fast"}});expect(screen.queryByText("确认执行同一会话请求")).toBeNull();
});
it("reads persisted sessions without inference; explicit preview and confirmation freeze one request",async()=>{
 bridge.call.mockImplementation(async(op,p)=>normal(op,p));const view=render(<ConversationPanel/>);await selectSession();expect(bridge.call.mock.calls.every(c=>c[0]==="conversation_history")).toBe(true);
 fireEvent.change(screen.getByLabelText("会话问题"),{target:{value:"question"}});fireEvent.click(screen.getByText("预览会话请求"));await screen.findByText("确认执行同一会话请求");const preview=bridge.call.mock.calls.find(c=>c[0]==="conversation_request")![1].body;expect(preview.purpose).toBe("companion");expect(preview.material).toBeNull();expect(bridge.call.mock.calls.filter(c=>c[0]==="conversation_request")).toHaveLength(1);
 fireEvent.click(screen.getByText("确认执行同一会话请求"));await screen.findByText("回执与历史已读回；回答仍需你判断。");const calls=bridge.call.mock.calls.filter(c=>c[0]==="conversation_request");expect(calls[1][1].body).toEqual({...preview,preview:false,confirmed_plan_sha256:"b".repeat(64)});
 view.rerender(<ConversationPanel/>);fireEvent.click(screen.getByText("重读历史"));await screen.findByText("历史已读回；未确认的提问请继续查询。");expect(bridge.call.mock.calls.filter(c=>c[0]==="conversation_request")).toHaveLength(2);
});
it("a delayed material preview cannot bind to a replacement object",async()=>{
 let resolve!:(v:unknown)=>void;let pendingBody:Record<string,unknown>={};bridge.call.mockImplementation((op,p)=>{if(op==="conversation_request"){pendingBody=p.body;return new Promise(r=>{resolve=r;});}return Promise.resolve(normal(op,p));});
 const material={kind:"document" as const,document_id:"doc_a",version:1,content_sha256:"a".repeat(64),block_id:null};const view=render(<ConversationPanel material={material}/>);await selectSession();fireEvent.change(screen.getByLabelText("会话问题"),{target:{value:"question"}});fireEvent.click(screen.getByText("预览会话请求"));await waitFor(()=>expect(bridge.call.mock.calls.some(c=>c[0]==="conversation_request")).toBe(true));expect(pendingBody.purpose).toBe("material_learning");expect(pendingBody.material).toEqual(material);
 view.rerender(<ConversationPanel material={{...material,document_id:"doc_b"}}/>);await act(async()=>resolve({schema:"archeaxis.conversation-preview/v1",plan:{request:pendingBody},plan_sha256:"b".repeat(64)}));expect(screen.queryByText("确认执行同一会话请求")).toBeNull();
});
it("cancellation sends the exact session/request and leaves completion to the actual receipt",async()=>{
 let resolve!:(v:unknown)=>void;let running:Record<string,unknown>={};bridge.call.mockImplementation((op,p)=>{if(op==="conversation_request"&&!p.body.preview){running=p.body;return new Promise(r=>{resolve=r;});}return Promise.resolve(normal(op,p));});render(<ConversationPanel/>);await selectSession();fireEvent.change(screen.getByLabelText("会话问题"),{target:{value:"question"}});fireEvent.click(screen.getByText("预览会话请求"));await screen.findByText("确认执行同一会话请求");fireEvent.click(screen.getByText("确认执行同一会话请求"));fireEvent.click(await screen.findByText("取消会话请求"));await screen.findByText("已申请取消，仍在等待实际结果。");expect(bridge.call.mock.calls.find(c=>c[0]==="conversation_cancel")![1].body).toEqual({session_id:"session_a",request_id:running.request_id});await act(async()=>resolve({schema:"archeaxis.conversation-receipt/v1",session_id:"session_a",request_id:running.request_id,state:"cancelled",answer:null,delivery:"BUFFERED"}));expect(screen.queryByText("SYNTHETIC answer")).toBeNull();
});
it("rejects cross-session late fragments and conflicting sequence identities while deduplicating replay",()=>{
 const event={session_id:"session_a",request_id:"request_a",sequence:1,kind:"accepted",data:{question:"question",purpose:"companion",plan_sha256:"a".repeat(64)},delivery:"BUFFERED"} as ConversationEventDto;
 expect(mergeConversationEvents([event],[event],"session_a")).toEqual([event]);expect(()=>mergeConversationEvents([],[{...event,session_id:"session_b"}],"session_a")).toThrow("late_cross_session_event");expect(()=>mergeConversationEvents([event],[{...event,request_id:"changed"}],"session_a")).toThrow("conversation_sequence_conflict");
});
it("closing a presentation neither cancels nor repeats the admitted request, and reopening only reads history",async()=>{
 let resolve!:(v:unknown)=>void;let running:Record<string,unknown>={};bridge.call.mockImplementation((op,p)=>{if(op==="conversation_request"&&!p.body.preview){running=p.body;return new Promise(r=>{resolve=r;});}return Promise.resolve(normal(op,p));});const view=render(<ConversationPanel/>);await selectSession();fireEvent.change(screen.getByLabelText("会话问题"),{target:{value:"question"}});fireEvent.click(screen.getByText("预览会话请求"));await screen.findByText("确认执行同一会话请求");fireEvent.click(screen.getByText("确认执行同一会话请求"));await screen.findByText("取消会话请求");view.unmount();await act(async()=>resolve({schema:"archeaxis.conversation-receipt/v1",session_id:"session_a",request_id:running.request_id,state:"completed",answer:{answer:"SYNTHETIC answer"},delivery:"BUFFERED"}));render(<ConversationPanel/>);await selectSession();expect(bridge.call.mock.calls.filter(c=>c[0]==="conversation_request")).toHaveLength(2);expect(bridge.call.mock.calls.some(c=>c[0]==="conversation_cancel")).toBe(false);
});
it("drives Xiaoqi from confirmed request lifecycle and waits for a cancellation terminal",async()=>{
 let finish!:(value:unknown)=>void;let running:Record<string,unknown>={};
 bridge.call.mockImplementation((op,p)=>{
  if(op==="conversation_request"&&!p.body.preview){running=p.body;return new Promise(resolve=>{finish=resolve;});}
  return Promise.resolve(normal(op,p));
 });
 render(<ConversationPanel/>);await selectSession();
 expect(screen.getByRole("img",{name:"小栖：待命"})).toBeVisible();
 fireEvent.change(screen.getByLabelText("会话问题"),{target:{value:"question"}});
 fireEvent.click(screen.getByText("预览会话请求"));await screen.findByText("确认执行同一会话请求");
 expect(screen.getByRole("img",{name:"小栖：等待确认"})).toBeVisible();
 fireEvent.click(screen.getByText("确认执行同一会话请求"));await screen.findByText("取消会话请求");
 expect(screen.getByRole("img",{name:"小栖：思考中"})).toBeVisible();
 fireEvent.click(screen.getByText("取消会话请求"));await screen.findByText("已申请取消，仍在等待实际结果。");
 expect(screen.getByRole("img",{name:"小栖：思考中"})).toBeVisible();
 await act(async()=>finish({schema:"archeaxis.conversation-receipt/v1",session_id:"session_a",request_id:running.request_id,state:"cancelled",answer:null,delivery:"BUFFERED"}));
 expect(screen.getByRole("img",{name:"小栖：已中断"})).toBeVisible();
 expect(bridge.call.mock.calls.filter(call=>call[0]==="conversation_request")).toHaveLength(2);
});
it.each(["status","lost-response"])("keeps a submitted %s request distinct from an unsubmitted preview",async mode=>{
 let running:Record<string,unknown>={};
 bridge.call.mockImplementation(async(op,p)=>{
  if(op==="conversation_request"&&!p.body.preview){
   running=p.body;
   if(mode==="lost-response")throw Error("SYNTHETIC lost acknowledgement");
   return {schema:"archeaxis.conversation-status/v1",session_id:p.body.session_id,request_id:p.body.request_id,execution_state:"UNKNOWN",answer_published:false,delivery:"BUFFERED"};
  }
  if(op==="conversation_status")return {schema:"archeaxis.conversation-receipt/v1",session_id:p.body.session_id,request_id:p.body.request_id,state:"completed",answer:{answer:"SYNTHETIC answer"},delivery:"BUFFERED"};
  return normal(op,p);
 });
 render(<ConversationPanel/>);await selectSession();
 fireEvent.change(screen.getByLabelText("会话问题"),{target:{value:"question"}});
 fireEvent.click(screen.getByText("预览会话请求"));await screen.findByText("确认执行同一会话请求");
 fireEvent.click(screen.getByText("确认执行同一会话请求"));
 await screen.findByText("请求状态未确认，请查询原请求。");
 expect(screen.queryByRole("img",{name:"小栖：等待确认"})).toBeNull();
 expect(screen.getByText("确认执行同一会话请求")).toBeDisabled();
 fireEvent.click(screen.getByText("查询未确认请求"));
 await screen.findByRole("img",{name:"小栖：已完成"});
 expect(bridge.call.mock.calls.find(call=>call[0]==="conversation_status")![1].body).toEqual({session_id:"session_a",request_id:running.request_id});
 expect(bridge.call.mock.calls.filter(call=>call[0]==="conversation_request")).toHaveLength(2);
});

it("uses the exact material title only for a matching conversation preview while preserving frozen request identity",async()=>{
 bridge.call.mockImplementation(async(op,p)=>normal(op,p));const material={kind:"document" as const,document_id:"doc_a",version:3,content_sha256:"a".repeat(64),block_id:null};
 render(<ConversationPanel material={material} materialTitle="会话材料标题"/>);await selectSession();fireEvent.change(screen.getByLabelText("会话问题"),{target:{value:"冻结材料会话问题"}});fireEvent.click(screen.getByText("预览会话请求"));await screen.findByText("确认执行同一会话请求");
 expect(screen.getByRole("region",{name:"待确认请求"})).toHaveTextContent("《会话材料标题》，已保存文档第 3 版");const frozen=structuredClone(bridge.call.mock.calls.find(([op])=>op==="conversation_request")![1].body);
 fireEvent.click(screen.getByText("确认执行同一会话请求"));await screen.findByText("回执与历史已读回；回答仍需你判断。");const submitted=bridge.call.mock.calls.filter(([op])=>op==="conversation_request")[1][1].body;expect(submitted).toEqual({...frozen,preview:false,confirmed_plan_sha256:"b".repeat(64)});expect(submitted).not.toHaveProperty("materialTitle");
});

it.each(["execute","status","history","history-unavailable"])("keeps failed companion timeout visible after %s without repeating inference",async mode=>{
 let requestId="timeout_request",executed=false;
 const failed=()=>({schema:"archeaxis.conversation-receipt/v1",session_id:"session_a",request_id:requestId,state:"failed",reason_code:"conversation_model_timeout",answer:null,delivery:"BUFFERED"});
 bridge.call.mockImplementation(async(op,p)=>{
  if(op==="conversation_request"&&!p.body.preview){requestId=p.body.request_id;executed=true;if(mode==="status")throw Error("SYNTHETIC lost ACK");return failed();}
  if(op==="conversation_status")return failed();
  if(op==="conversation_history"&&p.body.session_id){
   if(mode==="history-unavailable"&&executed)throw Error("SYNTHETIC unavailable history");
   return mode==="history"||executed?{...session,requests:[{request_id:requestId,state:"failed",receipt:failed()}]}:session;
  }
  return normal(op,p);
 });
 render(<ConversationPanel/>);await selectSession();
 if(mode!=="history"){
  fireEvent.change(screen.getByLabelText("会话问题"),{target:{value:"question"}});fireEvent.click(screen.getByText("预览会话请求"));fireEvent.click(await screen.findByText("确认执行同一会话请求"));
  if(mode==="status")fireEvent.click(await screen.findByText("查询未确认请求"));
 }
 await screen.findByText(mode==="history-unavailable"?"模型调用超时，未生成可用回答；原请求已保留，没有自动重试。历史暂未同步，请重读历史。":"模型调用超时，未生成可用回答；原请求已保留，没有自动重试。");
 expect(screen.queryByText(/回答仍需你判断/)).toBeNull();
 expect(bridge.call.mock.calls.filter(([op,p])=>op==="conversation_request"&&!p.body.preview)).toHaveLength(mode==="history"?0:1);
});
