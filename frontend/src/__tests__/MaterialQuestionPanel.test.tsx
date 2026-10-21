import {afterEach,beforeEach,expect,it,vi} from "vitest";
import {fireEvent,render,screen,waitFor,act} from "@testing-library/react";
import {webcrypto} from "node:crypto";
import {MaterialQuestionPanel} from "../components/MaterialQuestionPanel";
const bridge=vi.hoisted(()=>({call:vi.fn(),configuration:{revision:0} as Record<string,unknown>}));vi.mock("../api/core",()=>({coreCommand:(op:string,p:unknown)=>op==="model_configuration_get"?Promise.resolve(bridge.configuration):bridge.call(op,p)}));
const material={kind:"document" as const,document_id:"doc_a",version:1,content_sha256:"a".repeat(64),block_id:null};
it.each(["accepted","refused","wrong-id","missing-ack"])("checks the exact material cancellation acknowledgment: %s",async mode=>{
 let finish!:(value:unknown)=>void;let running:Record<string,unknown>={};
 bridge.call.mockImplementation((op,p)=>{
  if(op==="material_question_cancel")return Promise.resolve({request_id:mode==="wrong-id"?"other":running.request_id,...(mode==="missing-ack"?{}:{cancel_requested:mode!=="refused"})});
  if(p.body.preview)return Promise.resolve({schema:"archeaxis.material-question-preview/v1",plan_sha256:"b".repeat(64)});
  running=p.body;return new Promise(resolve=>{finish=resolve;});
 });
 render(<MaterialQuestionPanel material={material} text="saved"/>);fireEvent.change(screen.getByLabelText("材料问题"),{target:{value:"question"}});fireEvent.click(screen.getByText("预览材料提问"));await screen.findByText("确认提问或查询原请求");
 fireEvent.click(screen.getByText("确认提问或查询原请求"));fireEvent.click(await screen.findByText("取消材料提问"));
 await screen.findByText(mode==="accepted"?"取消已请求，等待实际回执；提供者停止状态未确认。":mode==="refused"?"该请求已不接受取消，请查询原请求终态。":"取消未确认；原请求仍保留，可重试取消或等待实际回执。");
 expect(bridge.call.mock.calls.find(c=>c[0]==="material_question_cancel")![1].body).toEqual({request_id:running.request_id});
 expect(bridge.call.mock.calls.filter(c=>c[0]==="material_question"&&!c[1].body.preview)).toHaveLength(1);
 await act(async()=>finish({schema:"archeaxis.material-answer/v1",request_id:running.request_id,outcome:"failed",answer:null}));
});
it.each(["reject","wrong-id","invalid-outcome"])("keeps recovered request locked when its status returns %s",async mode=>{
 const request={request_id:"saved_request",material,selection:null,question:"saved question",purpose:"learning",model:null,max_tokens:128,timeout_s:5,preview:false,confirmed_plan_sha256:null};let reads=0;
 bridge.call.mockImplementation(async(op,p)=>{
  expect(op).toBe("material_question_status");if(p.body.request_id===null)return {schema:"archeaxis.material-question-journal/v1",plans:[{request}]};
  if(++reads===1){if(mode==="reject")throw Error("SYNTHETIC status unavailable");return {schema:"archeaxis.material-answer/v1",request_id:mode==="wrong-id"?"other_request":request.request_id,outcome:mode==="invalid-outcome"?"invalid":"succeeded",answer:{answer:"unconfirmed answer"}};}
  return {schema:"archeaxis.material-answer/v1",request_id:request.request_id,outcome:"succeeded",answer:{answer:"SYNTHETIC confirmed recovery"}};
 });
 render(<MaterialQuestionPanel material={material} text="saved material"/>);fireEvent.click(screen.getByText("恢复本版材料的上次提问"));await screen.findByText("材料请求历史未确认，当前输入保留。");
 expect(screen.getByLabelText("材料问题")).toHaveValue("saved question");expect(screen.getByLabelText("材料模型通道")).toBeDisabled();expect(screen.getByText("确认提问或查询原请求")).toBeDisabled();expect(screen.queryByText("unconfirmed answer")).toBeNull();
 fireEvent.click(screen.getByText("查询未确认材料请求"));await screen.findByText("SYNTHETIC confirmed recovery");expect(bridge.call.mock.calls.at(-1)?.[1].body).toEqual({request_id:request.request_id});expect(bridge.call.mock.calls.every(c=>c[0]==="material_question_status")).toBe(true);
});
beforeEach(()=>{vi.stubGlobal("crypto",webcrypto);bridge.call.mockReset();bridge.configuration={revision:0};});afterEach(()=>vi.unstubAllGlobals());
it("does not preview or infer an unconfigured DEEP material request",async()=>{
 render(<MaterialQuestionPanel material={material} text="material"/>);fireEvent.change(screen.getByLabelText("材料模型通道"),{target:{value:"deep"}});fireEvent.change(screen.getByLabelText("材料问题"),{target:{value:"question"}});fireEvent.click(screen.getByText("预览材料提问"));await screen.findByText(/DEEP 尚未配置/);expect(bridge.call).not.toHaveBeenCalled();
});
it.each(["lost-response","invalid-receipt"])("retains a submitted %s request and only queries the original ID",async mode=>{
 let id="";
 bridge.call.mockImplementation(async(op,p)=>{
  if(op==="material_question_status")return {schema:"archeaxis.material-answer/v1",request_id:p.body.request_id,outcome:"succeeded",answer:{answer:"SYNTHETIC recovered"}};
  if(p.body.preview)return {schema:"archeaxis.material-question-preview/v1",plan_sha256:"b".repeat(64)};
  id=p.body.request_id;if(mode==="lost-response")throw Error("SYNTHETIC lost acknowledgement");return {schema:"wrong",request_id:id};
 });
 render(<MaterialQuestionPanel material={material} text="material"/>);fireEvent.change(screen.getByLabelText("材料问题"),{target:{value:"question"}});fireEvent.click(screen.getByText("预览材料提问"));await screen.findByText("确认提问或查询原请求");fireEvent.click(screen.getByText("确认提问或查询原请求"));await screen.findByText("材料请求状态未确认，请查询原请求。");
 for(const label of ["材料问题","提问用途","材料模型通道","材料问答选区"])expect(screen.getByLabelText(label)).toBeDisabled();
 expect(screen.getByText("预览材料提问")).toBeDisabled();expect(screen.getByText("确认提问或查询原请求")).toBeDisabled();
 fireEvent.click(screen.getByText("查询未确认材料请求"));await screen.findByText("SYNTHETIC recovered");expect(bridge.call.mock.calls.filter(c=>c[0]==="material_question")).toHaveLength(2);expect(bridge.call.mock.calls.find(c=>c[0]==="material_question_status")![1].body).toEqual({request_id:id});expect(screen.getByLabelText("材料模型通道")).toBeEnabled();
});
it("resolves the selected DEEP material lane once and freezes it across confirmation",async()=>{
 bridge.configuration={revision:3,workspace_id:"a".repeat(32),restore_epoch:"initial"};
 const resolved={workspace_id:"a".repeat(32),restore_epoch:"initial",schema:"archeaxis.resolved-model/v1",configuration_revision:3,purpose:"material",lane:"deep",profile_id:"mtp",profile:{endpoint:"http://127.0.0.1:1234/v1",protocol:"openai",model:"aaos-deep-27b-mtp",credential_ref:null,max_tokens:1024,timeout_s:120}};
 bridge.call.mockImplementation(async(op,p)=>op==="model_configuration_resolve"?resolved:p.body.preview?{schema:"archeaxis.material-question-preview/v1",plan_sha256:"b".repeat(64)}:{schema:"archeaxis.material-answer/v1",request_id:p.body.request_id,outcome:"succeeded",answer:{answer:"SYNTHETIC DEEP"}});
 render(<MaterialQuestionPanel material={material} text="material"/>);fireEvent.change(screen.getByLabelText("材料模型通道"),{target:{value:"deep"}});fireEvent.change(screen.getByLabelText("材料问题"),{target:{value:"question"}});fireEvent.click(screen.getByText("预览材料提问"));await screen.findByText("确认提问或查询原请求");
 expect(bridge.call.mock.calls.find(c=>c[0]==="model_configuration_resolve")![1].body).toEqual({purpose:"material",lane:"deep"});
 const preview=bridge.call.mock.calls.find(c=>c[0]==="material_question")![1].body;
 expect(preview).toMatchObject({model:"aaos-deep-27b-mtp",max_tokens:1024,model_configuration:resolved});
 fireEvent.click(screen.getByText("确认提问或查询原请求"));await screen.findByText("SYNTHETIC DEEP");
 expect(bridge.call.mock.calls.filter(c=>c[0]==="model_configuration_resolve")).toHaveLength(1);
 expect(bridge.call.mock.calls.filter(c=>c[0]==="material_question")[1][1].body).toEqual({...preview,preview:false,confirmed_plan_sha256:"b".repeat(64)});
 fireEvent.change(screen.getByLabelText("材料模型通道"),{target:{value:"fast"}});expect(screen.queryByText("确认提问或查询原请求")).toBeNull();
});
it("previews exact Unicode selection and executes only the explicitly confirmed frozen request",async()=>{
 bridge.call.mockImplementation(async(op,p)=>{expect(op).toBe("material_question");return p.body.preview?{schema:"archeaxis.material-question-preview/v1",plan_sha256:"b".repeat(64),plan:{destination:"LOCAL_LOOPBACK_ONLY"}}:{schema:"archeaxis.material-answer/v1",request_id:p.body.request_id,outcome:"succeeded",answer:{answer:"SIMULATED answer"}};});
 render(<MaterialQuestionPanel material={material} text="前缀原文😀后缀"/>);fireEvent.change(screen.getByLabelText("材料问题"),{target:{value:"解释选区"}});
 const area=screen.getByLabelText("材料问答选区") as HTMLTextAreaElement;area.setSelectionRange(2,6);fireEvent.select(area);fireEvent.click(screen.getByText("预览材料提问"));await screen.findByText("确认提问或查询原请求");expect(bridge.call).toHaveBeenCalledTimes(1);
 const preview=bridge.call.mock.calls[0][1].body;expect(preview.selection).toEqual({start_utf16:2,end_utf16:6,quote_sha256:Array.from(new Uint8Array(await webcrypto.subtle.digest("SHA-256",new TextEncoder().encode("原文😀")))).map(x=>x.toString(16).padStart(2,"0")).join("")});
 fireEvent.click(screen.getByText("确认提问或查询原请求"));await screen.findByText("SIMULATED answer");expect(bridge.call.mock.calls[1][1].body).toEqual({...preview,preview:false,confirmed_plan_sha256:"b".repeat(64)});
});
it("changing objects discards delayed preview and never binds it to the new material",async()=>{
 let resolve!:(value:unknown)=>void;bridge.call.mockImplementation(()=>new Promise(r=>{resolve=r;}));const view=render(<MaterialQuestionPanel material={material} text="first"/>);fireEvent.change(screen.getByLabelText("材料问题"),{target:{value:"question"}});fireEvent.click(screen.getByText("预览材料提问"));await waitFor(()=>expect(bridge.call).toHaveBeenCalledTimes(1));view.rerender(<MaterialQuestionPanel material={{...material,document_id:"doc_b"}} text="second"/>);await act(async()=>resolve({schema:"archeaxis.material-question-preview/v1",plan_sha256:"b".repeat(64)}));expect(screen.queryByText("确认提问或查询原请求")).toBeNull();
});
it("maps textarea LF offsets to the original CRLF quote and clears selection on object change",async()=>{
 bridge.call.mockResolvedValue({schema:"archeaxis.material-question-preview/v1",plan_sha256:"b".repeat(64)});
 const view=render(<MaterialQuestionPanel material={material} text={"前\r\n原文😀"}/>);fireEvent.change(screen.getByLabelText("材料问题"),{target:{value:"question"}});
 const area=screen.getByLabelText("材料问答选区") as HTMLTextAreaElement;area.setSelectionRange(2,6);fireEvent.select(area);fireEvent.click(screen.getByText("预览材料提问"));await screen.findByText("确认提问或查询原请求");expect(bridge.call.mock.calls[0][1].body.selection).toMatchObject({start_utf16:3,end_utf16:7});
 view.rerender(<MaterialQuestionPanel material={{...material,document_id:"doc_b"}} text="new"/>);expect(screen.getByText("整个已保存材料")).toBeTruthy();
});
it("reads a persisted same-version request without performing inference",async()=>{
 const request={request_id:"old_request",material:{block_id:null,content_sha256:material.content_sha256,document_id:material.document_id,kind:"document",version:1},selection:null,question:"old question",purpose:"learning",model:null,max_tokens:128,timeout_s:5,preview:false,confirmed_plan_sha256:null};
 bridge.call.mockImplementation(async(op,p)=>{expect(op).toBe("material_question_status");return p.body.request_id===null?{schema:"archeaxis.material-question-journal/v1",plans:[{request}]}:{schema:"archeaxis.material-answer/v1",request_id:"old_request",outcome:"succeeded",answer:{answer:"historical answer"}};});
 render(<MaterialQuestionPanel material={material} text="material"/>);fireEvent.click(screen.getByText("恢复本版材料的上次提问"));await screen.findByText("historical answer");expect(bridge.call).toHaveBeenCalledTimes(2);expect(screen.getByLabelText("材料问题")).toHaveProperty("value","old question");
});

it("SIMULATED recovery restores original CRLF/emoji selection and queries the same frozen request",async()=>{
 const text="前\r\n原文😀后";
 const quote_sha256=Array.from(new Uint8Array(await webcrypto.subtle.digest("SHA-256",new TextEncoder().encode(text.slice(3,7))))).map(x=>x.toString(16).padStart(2,"0")).join("");
 const request={request_id:"selected_request",material,selection:{start_utf16:3,end_utf16:7,quote_sha256},question:"恢复选区",purpose:"理解",model:null,max_tokens:128,timeout_s:5,preview:false,confirmed_plan_sha256:null};
 let statusReads=0;
 bridge.call.mockImplementation(async(op,p)=>op==="material_question_status"?(p.body.request_id===null?{schema:"archeaxis.material-question-journal/v1",plans:[{request}]}:++statusReads===1?{request_id:request.request_id,schema:"archeaxis.material-question-status/v1",execution_state:"UNKNOWN"}:{schema:"archeaxis.material-answer/v1",request_id:request.request_id,outcome:"succeeded",answer:{answer:"recovered selection answer"}}):{schema:"archeaxis.material-answer/v1",request_id:p.body.request_id,outcome:"succeeded",answer:{answer:"recovered selection answer"}});
 render(<MaterialQuestionPanel material={material} text={text}/>);fireEvent.click(screen.getByText("恢复本版材料的上次提问"));
 await screen.findByText(/执行结果尚未确认/);expect(screen.getByText("已选文本：原文😀")).toBeInTheDocument();
 expect(screen.getByText("确认提问或查询原请求")).toBeDisabled();fireEvent.click(screen.getByText("查询未确认材料请求"));await screen.findByText("recovered selection answer");
 expect(bridge.call.mock.calls.some(([op])=>op==="material_question")).toBe(false);expect(bridge.call.mock.calls.at(-1)?.[1].body).toEqual({request_id:request.request_id});
});

it("SIMULATED recovery rejects a historical selection whose quote does not match this material",async()=>{
 const request={request_id:"bad_selection",material,selection:{start_utf16:0,end_utf16:4,quote_sha256:"f".repeat(64)},question:"bad",purpose:"理解",model:null,max_tokens:128,timeout_s:5};
 bridge.call.mockResolvedValue({schema:"archeaxis.material-question-journal/v1",plans:[{request}]});
 render(<MaterialQuestionPanel material={material} text="other material"/>);fireEvent.click(screen.getByText("恢复本版材料的上次提问"));
 await screen.findByText("材料请求历史未确认，当前输入保留。");expect(screen.queryByText("确认提问或查询原请求")).toBeNull();
 expect(bridge.call).toHaveBeenCalledTimes(1);
});

it("SIMULATED cancel refusal is shown and the same running request can be cancelled again",async()=>{
 let finish!:(value:unknown)=>void;
 bridge.call.mockImplementation((op,p)=>op==="material_question_cancel"?Promise.reject(new Error("HTTP 503")):p.body.preview?Promise.resolve({schema:"archeaxis.material-question-preview/v1",plan_sha256:"b".repeat(64)}):new Promise(r=>{finish=r;}));
 render(<MaterialQuestionPanel material={material} text="saved"/>);fireEvent.change(screen.getByLabelText("材料问题"),{target:{value:"question"}});fireEvent.click(screen.getByText("预览材料提问"));await screen.findByText("确认提问或查询原请求");
 fireEvent.click(screen.getByText("确认提问或查询原请求"));const cancel=await screen.findByText("取消材料提问");fireEvent.click(cancel);
 await screen.findByText("取消未确认；原请求仍保留，可重试取消或等待实际回执。");fireEvent.click(cancel);await waitFor(()=>expect(bridge.call.mock.calls.filter(([op])=>op==="material_question_cancel")).toHaveLength(2));
 const request=bridge.call.mock.calls.find(([op,p])=>op==="material_question"&&!p.body.preview)![1].body;
 await act(async()=>finish({schema:"archeaxis.material-answer/v1",request_id:request.request_id,outcome:"succeeded",answer:{answer:"completed despite cancel failure"}}));await screen.findByText("completed despite cancel failure");
});

it("SIMULATED late cancel ACK does not replace a completed request's result",async()=>{
 let finish!:(value:unknown)=>void,ack!:(value:unknown)=>void;
 bridge.call.mockImplementation((op,p)=>op==="material_question_cancel"?new Promise(r=>{ack=r;}):p.body.preview?Promise.resolve({schema:"archeaxis.material-question-preview/v1",plan_sha256:"b".repeat(64)}):new Promise(r=>{finish=r;}));
 render(<MaterialQuestionPanel material={material} text="saved"/>);fireEvent.change(screen.getByLabelText("材料问题"),{target:{value:"question"}});fireEvent.click(screen.getByText("预览材料提问"));await screen.findByText("确认提问或查询原请求");fireEvent.click(screen.getByText("确认提问或查询原请求"));fireEvent.click(await screen.findByText("取消材料提问"));
 const request=bridge.call.mock.calls.find(([op,p])=>op==="material_question"&&!p.body.preview)![1].body;
 await act(async()=>finish({schema:"archeaxis.material-answer/v1",request_id:request.request_id,outcome:"succeeded",answer:{answer:"finished"}}));await screen.findByText("回答已记录，仍是待判断的模型候选。");
 await act(async()=>ack({request_id:request.request_id}));expect(screen.getByText("回答已记录，仍是待判断的模型候选。")).toBeInTheDocument();
});

it("closing a view does not cancel its recorded backend execution",async()=>{
 let finish!:(value:unknown)=>void;
 bridge.call.mockImplementation((op,p)=>{expect(op).toBe("material_question");return p.body.preview?Promise.resolve({schema:"archeaxis.material-question-preview/v1",plan_sha256:"b".repeat(64)}):new Promise(r=>{finish=r;});});
 const view=render(<MaterialQuestionPanel material={material} text="saved material"/>);
 fireEvent.change(screen.getByLabelText("材料问题"),{target:{value:"question"}});fireEvent.click(screen.getByText("预览材料提问"));await screen.findByText("确认提问或查询原请求");
 fireEvent.click(screen.getByText("确认提问或查询原请求"));await waitFor(()=>expect(bridge.call).toHaveBeenCalledTimes(2));const request=bridge.call.mock.calls[1][1].body;
 view.unmount();expect(bridge.call).toHaveBeenCalledTimes(2);
 await act(async()=>finish({schema:"archeaxis.material-answer/v1",request_id:request.request_id,outcome:"succeeded",answer:{answer:"late"}}));expect(bridge.call).toHaveBeenCalledTimes(2);
});

it("freezes the configured Material profile once and keeps it for execution retry",async()=>{
 bridge.configuration={revision:1,workspace_id:"a".repeat(32),restore_epoch:"epoch"};
 const resolved={schema:"archeaxis.resolved-model/v1",workspace_id:"a".repeat(32),restore_epoch:"epoch",configuration_revision:1,configuration_sha256:"c".repeat(64),purpose:"material",lane:"fast",profile_id:"local",profile:{endpoint:"http://127.0.0.1:1234/v1",protocol:"openai",model:"fixed-material-model",credential_ref:null,max_tokens:512,timeout_s:9}};
 bridge.call.mockImplementation(async(op,p)=>op==="model_configuration_resolve"?resolved:p.body.preview?{schema:"archeaxis.material-question-preview/v1",plan_sha256:"b".repeat(64)}:{schema:"archeaxis.material-answer/v1",request_id:p.body.request_id,outcome:"succeeded",answer:{answer:"configured"}});
 render(<MaterialQuestionPanel material={material} text="saved material"/>);fireEvent.change(screen.getByLabelText("材料问题"),{target:{value:"question"}});fireEvent.click(screen.getByText("预览材料提问"));await screen.findByText("确认提问或查询原请求");
 expect(bridge.call.mock.calls[0]).toEqual(["model_configuration_resolve",{body:{purpose:"material",lane:"fast"}}]);
 const preview=bridge.call.mock.calls[1][1].body;expect(preview).toMatchObject({model_configuration:resolved,model:"fixed-material-model",max_tokens:512,timeout_s:9});
 fireEvent.click(screen.getByText("确认提问或查询原请求"));await screen.findByText("configured");expect(bridge.call.mock.calls[2][1].body.model_configuration).toEqual(resolved);expect(bridge.call.mock.calls.filter(([op])=>op==="model_configuration_resolve")).toHaveLength(1);
});

it("shows the actual material title bound to the frozen saved version without changing the confirmed request",async()=>{
 bridge.call.mockImplementation(async(_op,p)=>p.body.preview?{schema:"archeaxis.material-question-preview/v1",plan_sha256:"b".repeat(64)}:{schema:"archeaxis.material-answer/v1",request_id:p.body.request_id,outcome:"failed",answer:null});
 render(<MaterialQuestionPanel material={material} text="original" materialTitle="已读材料标题"/>);fireEvent.change(screen.getByLabelText("材料问题"),{target:{value:"冻结问题"}});fireEvent.click(screen.getByText("预览材料提问"));await screen.findByText("确认提问或查询原请求");
 expect(screen.getByRole("region",{name:"待确认请求"})).toHaveTextContent("《已读材料标题》，已保存文档第 1 版");const frozen=structuredClone(bridge.call.mock.calls[0][1].body);
 fireEvent.click(screen.getByText("确认提问或查询原请求"));await screen.findByText("执行失败或取消，原请求和材料保留。");expect(bridge.call.mock.calls[1][1].body).toEqual({...frozen,preview:false,confirmed_plan_sha256:"b".repeat(64)});expect(bridge.call.mock.calls[1][1].body).not.toHaveProperty("materialTitle");
});

it.each(["execute","status","history"])("reports a failed material timeout after %s without repeating inference",async mode=>{
 const saved={request_id:"timeout_saved",material,selection:null,question:"saved question",purpose:"learning",model:null,max_tokens:128,timeout_s:5,preview:false,confirmed_plan_sha256:null};
 bridge.call.mockImplementation(async(op,p)=>{
  if(op==="material_question_status"&&p.body.request_id===null)return {schema:"archeaxis.material-question-journal/v1",plans:[{request:saved}]};
  if(p.body.preview)return {schema:"archeaxis.material-question-preview/v1",plan_sha256:"b".repeat(64)};
  if(mode==="status"&&op==="material_question")throw Error("SYNTHETIC lost ACK");
  return {schema:"archeaxis.material-answer/v1",request_id:p.body.request_id,outcome:"failed",reason_code:"material_model_timeout",answer:null};
 });
 render(<MaterialQuestionPanel material={material} text="saved material"/>);
 if(mode==="history")fireEvent.click(screen.getByText("恢复本版材料的上次提问"));
 else {
  fireEvent.change(screen.getByLabelText("材料问题"),{target:{value:"question"}});fireEvent.click(screen.getByText("预览材料提问"));fireEvent.click(await screen.findByText("确认提问或查询原请求"));
  if(mode==="status")fireEvent.click(await screen.findByText("查询未确认材料请求"));
 }
 await screen.findByText("模型调用超时，未生成可用回答；原请求已保留，没有自动重试。");
 expect(screen.queryByText("回答已记录，仍是待判断的模型候选。")).toBeNull();
 expect(bridge.call.mock.calls.filter(([op,p])=>op==="material_question"&&!p.body.preview)).toHaveLength(mode==="history"?0:1);
});

async function asyncPreview(body:Record<string,unknown>){
 const plan={schema:"archeaxis.material-question-plan/v1",request:{...body,preview:false,confirmed_plan_sha256:null},context:{material:body.material,selection:null,provenance:{source_id:null,source_revision:null},context_sha256:"c".repeat(64),bytes:8,authority:"unverified_material"},destination:"LOCAL_LOOPBACK_ONLY",destination_candidates:["http://127.0.0.1:1234/v1"],selection_policy:"existing_owned_local_worker_probe",network_scope:"fixed_owned_local_worker",workspace_id:"a".repeat(32),restore_epoch:"initial",usage:null,cost:null};
 const plan_sha256=await digest(JSON.stringify(plan));return {schema:"archeaxis.material-question-preview/v1",plan,plan_sha256};
}
async function digest(text:string){return Array.from(new Uint8Array(await webcrypto.subtle.digest("SHA-256",new TextEncoder().encode(text)))).map(x=>x.toString(16).padStart(2,"0")).join("");}
async function asyncAck(body:Record<string,unknown>){return {schema:"archeaxis.material-question-admission/v1",request_id:body.request_id,task_id:"material_answer_"+await digest(String(body.request_id)),plan_sha256:body.confirmed_plan_sha256,workspace_id:"a".repeat(32),restore_epoch:"initial",admission_state:"ACCEPTED",execution_state:"RUNNING",answer_published:false,provider_stop_state:"UNKNOWN"};}
function chooseAsync(){fireEvent.click(screen.getByLabelText("离开此页后继续提问"));fireEvent.change(screen.getByLabelText("材料问题"),{target:{value:"question"}});fireEvent.click(screen.getByText("预览材料提问"));}
it("SYNTHETIC async submission freezes mode, polls running to terminal, and never submits a second inference",async()=>{
 let preview:Awaited<ReturnType<typeof asyncPreview>>;let reads=0;
 bridge.call.mockImplementation(async(op,p)=>{
  if(op==="material_question")return preview=await asyncPreview(p.body);
  if(op==="material_question_submit")return asyncAck(p.body);
  if(op==="material_question_status")return ++reads===1?{request_id:p.body.request_id,plan:preview.plan,execution_state:"RUNNING",answer_published:false,provider_stop_state:"UNKNOWN"}:{schema:"archeaxis.material-answer/v1",request_id:p.body.request_id,outcome:"succeeded",answer:{answer:"SYNTHETIC async result"}};
  throw Error(op);
 });
 render(<MaterialQuestionPanel material={material} text="material"/>);chooseAsync();fireEvent.click(await screen.findByText("确认提问或查询原请求"));
 await screen.findByText("正在处理原材料请求；关闭页面只停止等待，不会自动取消。");await screen.findByText("SYNTHETIC async result");
 const submitted=bridge.call.mock.calls.filter(([op])=>op==="material_question_submit");expect(submitted).toHaveLength(1);expect(submitted[0][1].body).toMatchObject({execution_mode:"async",timeout_s:120,preview:false});expect(reads).toBe(2);
 expect(bridge.call.mock.calls.filter(([op])=>op==="material_question")).toHaveLength(1);
});
it.each(["wrong-id","wrong-plan","terminal-disguise","unknown-field","lost-ack"])("SYNTHETIC async %s retains the request and never retries inference",async mode=>{
 bridge.call.mockImplementation(async(op,p)=>{
  if(op==="material_question")return asyncPreview(p.body);
  if(op==="material_question_submit"){
   if(mode==="lost-ack")throw Error("lost ACK");const ack=await asyncAck(p.body);
   return mode==="wrong-id"?{...ack,request_id:"other"}:mode==="wrong-plan"?{...ack,plan_sha256:"f".repeat(64)}:mode==="terminal-disguise"?{...ack,answer_published:true}:mode==="unknown-field"?{...ack,endpoint:"http://remote.invalid"}:ack;
  }
  if(op==="material_question_status")return {schema:"archeaxis.material-answer/v1",request_id:p.body.request_id,outcome:"failed",reason_code:"material_model_timeout",answer:null};
  throw Error(op);
 });
 render(<MaterialQuestionPanel material={material} text="material"/>);chooseAsync();fireEvent.click(await screen.findByText("确认提问或查询原请求"));await screen.findByText("结果未确认；请查询原请求状态，不另发新请求。");
 expect(bridge.call.mock.calls.some(([op])=>op==="material_question_status")).toBe(false);fireEvent.click(screen.getByText("查询未确认材料请求"));await screen.findByText("模型调用超时，未生成可用回答；原请求已保留，没有自动重试。");
 expect(bridge.call.mock.calls.filter(([op])=>op==="material_question_submit")).toHaveLength(1);
});
it("SYNTHETIC async view exit ignores delayed status and does not cancel the Core-owned request",async()=>{
 let finish!:(v:unknown)=>void;
 bridge.call.mockImplementation(async(op,p)=>op==="material_question"?asyncPreview(p.body):op==="material_question_submit"?asyncAck(p.body):new Promise(r=>{finish=r;}));
 const view=render(<MaterialQuestionPanel material={material} text="material"/>);chooseAsync();fireEvent.click(await screen.findByText("确认提问或查询原请求"));await waitFor(()=>expect(bridge.call.mock.calls.some(([op])=>op==="material_question_status")).toBe(true));
 const request=bridge.call.mock.calls.find(([op])=>op==="material_question_submit")![1].body;view.rerender(<MaterialQuestionPanel material={{...material,document_id:"other"}} text="other"/>);
 await act(async()=>finish({schema:"archeaxis.material-answer/v1",request_id:request.request_id,outcome:"succeeded",answer:{answer:"late old async result"}}));expect(screen.queryByText("late old async result")).toBeNull();expect(bridge.call.mock.calls.some(([op])=>op==="material_question_cancel")).toBe(false);
});
it("SYNTHETIC async UNKNOWN stops polling while keeping explicit status recovery",async()=>{
 let preview:Awaited<ReturnType<typeof asyncPreview>>;
 bridge.call.mockImplementation(async(op,p)=>op==="material_question"?(preview=await asyncPreview(p.body)):op==="material_question_submit"?asyncAck(p.body):{request_id:p.body.request_id,plan:preview.plan,execution_state:"UNKNOWN",answer_published:false,provider_stop_state:"UNKNOWN"});
 render(<MaterialQuestionPanel material={material} text="material"/>);chooseAsync();fireEvent.click(await screen.findByText("确认提问或查询原请求"));await screen.findByText("执行状态未确认，保留原请求；可显式查询，没有自动重试。");
 expect(screen.getByText("查询未确认材料请求")).toBeEnabled();expect(bridge.call.mock.calls.filter(([op])=>op==="material_question_status")).toHaveLength(1);expect(screen.getByLabelText("离开此页后继续提问")).toBeDisabled();
});

it("SYNTHETIC async cancel remains explicit and keeps the provider state unknown until terminal",async()=>{
 let finish!:(v:unknown)=>void;let id="";
 bridge.call.mockImplementation(async(op,p)=>{
  if(op==="material_question")return asyncPreview(p.body);
  if(op==="material_question_submit"){id=p.body.request_id;return asyncAck(p.body);}
  if(op==="material_question_cancel")return {request_id:p.body.request_id,cancel_requested:true,execution_state:"UNKNOWN",provider_stop_state:"UNKNOWN"};
  return new Promise(r=>{finish=r;});
 });
 render(<MaterialQuestionPanel material={material} text="material"/>);chooseAsync();fireEvent.click(await screen.findByText("确认提问或查询原请求"));await waitFor(()=>expect(bridge.call.mock.calls.some(([op])=>op==="material_question_status")).toBe(true));
 fireEvent.click(screen.getByText("取消材料提问"));await screen.findByText("取消已请求，等待实际回执；提供者停止状态未确认。");
 await act(async()=>finish({schema:"archeaxis.material-answer/v1",request_id:id,outcome:"failed",reason_code:"material_question_cancelled",answer:null}));await screen.findByText("执行失败或取消，原请求和材料保留。");
 expect(bridge.call.mock.calls.filter(([op])=>op==="material_question_submit")).toHaveLength(1);expect(bridge.call.mock.calls.find(([op])=>op==="material_question_cancel")![1].body).toEqual({request_id:id});
});
