import {afterEach,beforeEach,expect,it,vi} from "vitest";
import {fireEvent,render,screen,waitFor,act} from "@testing-library/react";
import {webcrypto} from "node:crypto";
import {MaterialQuestionPanel} from "../components/MaterialQuestionPanel";
const bridge=vi.hoisted(()=>({call:vi.fn(),configuration:{revision:0} as Record<string,unknown>}));vi.mock("../api/core",()=>({coreCommand:(op:string,p:unknown)=>op==="model_configuration_get"?Promise.resolve(bridge.configuration):bridge.call(op,p)}));
const material={kind:"document" as const,document_id:"doc_a",version:1,content_sha256:"a".repeat(64),block_id:null};
beforeEach(()=>{vi.stubGlobal("crypto",webcrypto);bridge.call.mockReset();bridge.configuration={revision:0};});afterEach(()=>vi.unstubAllGlobals());
it("previews exact Unicode selection and executes only the explicitly confirmed frozen request",async()=>{
 bridge.call.mockImplementation(async(op,p)=>{expect(op).toBe("material_question");return p.body.preview?{schema:"archeaxis.material-question-preview/v1",plan_sha256:"b".repeat(64),plan:{destination:"LOCAL_LOOPBACK_ONLY"}}:{schema:"archeaxis.material-answer/v1",request_id:p.body.request_id,outcome:"succeeded",answer:{answer:"SIMULATED answer"}};});
 render(<MaterialQuestionPanel material={material} text="前缀原文😀后缀"/>);fireEvent.change(screen.getByLabelText("材料问题"),{target:{value:"解释选区"}});
 const area=screen.getByLabelText("材料问答选区") as HTMLTextAreaElement;area.setSelectionRange(2,6);fireEvent.select(area);fireEvent.click(screen.getByText("预览材料提问"));await screen.findByText("确认并提问或读回同一请求");expect(bridge.call).toHaveBeenCalledTimes(1);
 const preview=bridge.call.mock.calls[0][1].body;expect(preview.selection).toEqual({start_utf16:2,end_utf16:6,quote_sha256:Array.from(new Uint8Array(await webcrypto.subtle.digest("SHA-256",new TextEncoder().encode("原文😀")))).map(x=>x.toString(16).padStart(2,"0")).join("")});
 fireEvent.click(screen.getByText("确认并提问或读回同一请求"));await screen.findByText("SIMULATED answer");expect(bridge.call.mock.calls[1][1].body).toEqual({...preview,preview:false,confirmed_plan_sha256:"b".repeat(64)});
});
it("changing objects discards delayed preview and never binds it to the new material",async()=>{
 let resolve!:(value:unknown)=>void;bridge.call.mockImplementation(()=>new Promise(r=>{resolve=r;}));const view=render(<MaterialQuestionPanel material={material} text="first"/>);fireEvent.change(screen.getByLabelText("材料问题"),{target:{value:"question"}});fireEvent.click(screen.getByText("预览材料提问"));await waitFor(()=>expect(bridge.call).toHaveBeenCalledTimes(1));view.rerender(<MaterialQuestionPanel material={{...material,document_id:"doc_b"}} text="second"/>);await act(async()=>resolve({schema:"archeaxis.material-question-preview/v1",plan_sha256:"b".repeat(64)}));expect(screen.queryByText("确认并提问或读回同一请求")).toBeNull();
});
it("maps textarea LF offsets to the original CRLF quote and clears selection on object change",async()=>{
 bridge.call.mockResolvedValue({schema:"archeaxis.material-question-preview/v1",plan_sha256:"b".repeat(64)});
 const view=render(<MaterialQuestionPanel material={material} text={"前\r\n原文😀"}/>);fireEvent.change(screen.getByLabelText("材料问题"),{target:{value:"question"}});
 const area=screen.getByLabelText("材料问答选区") as HTMLTextAreaElement;area.setSelectionRange(2,6);fireEvent.select(area);fireEvent.click(screen.getByText("预览材料提问"));await screen.findByText("确认并提问或读回同一请求");expect(bridge.call.mock.calls[0][1].body.selection).toMatchObject({start_utf16:3,end_utf16:7});
 view.rerender(<MaterialQuestionPanel material={{...material,document_id:"doc_b"}} text="new"/>);expect(screen.getByText("整个已保存材料")).toBeTruthy();
});
it("reads a persisted same-version request without performing inference",async()=>{
 const request={request_id:"old_request",material:{block_id:null,content_sha256:material.content_sha256,document_id:material.document_id,kind:"document",version:1},selection:null,question:"old question",purpose:"learning",model:null,max_tokens:128,timeout_s:5,preview:false,confirmed_plan_sha256:null};
 bridge.call.mockImplementation(async(op,p)=>{expect(op).toBe("material_question_status");return p.body.request_id===null?{schema:"archeaxis.material-question-journal/v1",plans:[{request}]}:{schema:"archeaxis.material-answer/v1",request_id:"old_request",outcome:"succeeded",answer:{answer:"historical answer"}};});
 render(<MaterialQuestionPanel material={material} text="material"/>);fireEvent.click(screen.getByText("恢复最近同版本材料请求"));await screen.findByText("historical answer");expect(bridge.call).toHaveBeenCalledTimes(2);expect(screen.getByLabelText("材料问题")).toHaveProperty("value","old question");
});

it("closing a view does not cancel its recorded backend execution",async()=>{
 let finish!:(value:unknown)=>void;
 bridge.call.mockImplementation((op,p)=>{expect(op).toBe("material_question");return p.body.preview?Promise.resolve({schema:"archeaxis.material-question-preview/v1",plan_sha256:"b".repeat(64)}):new Promise(r=>{finish=r;});});
 const view=render(<MaterialQuestionPanel material={material} text="saved material"/>);
 fireEvent.change(screen.getByLabelText("材料问题"),{target:{value:"question"}});fireEvent.click(screen.getByText("预览材料提问"));await screen.findByText("确认并提问或读回同一请求");
 fireEvent.click(screen.getByText("确认并提问或读回同一请求"));await waitFor(()=>expect(bridge.call).toHaveBeenCalledTimes(2));const request=bridge.call.mock.calls[1][1].body;
 view.unmount();expect(bridge.call).toHaveBeenCalledTimes(2);
 await act(async()=>finish({schema:"archeaxis.material-answer/v1",request_id:request.request_id,outcome:"succeeded",answer:{answer:"late"}}));expect(bridge.call).toHaveBeenCalledTimes(2);
});

it("freezes the configured Material profile once and keeps it for execution retry",async()=>{
 bridge.configuration={revision:1};
 const resolved={schema:"archeaxis.resolved-model/v1",workspace_id:"a".repeat(32),restore_epoch:"epoch",configuration_revision:1,configuration_sha256:"c".repeat(64),purpose:"material",lane:"fast",profile_id:"local",profile:{endpoint:"http://127.0.0.1:1234/v1",protocol:"openai",model:"fixed-material-model",credential_ref:null,max_tokens:512,timeout_s:9}};
 bridge.call.mockImplementation(async(op,p)=>op==="model_configuration_resolve"?resolved:p.body.preview?{schema:"archeaxis.material-question-preview/v1",plan_sha256:"b".repeat(64)}:{schema:"archeaxis.material-answer/v1",request_id:p.body.request_id,outcome:"succeeded",answer:{answer:"configured"}});
 render(<MaterialQuestionPanel material={material} text="saved material"/>);fireEvent.change(screen.getByLabelText("材料问题"),{target:{value:"question"}});fireEvent.click(screen.getByText("预览材料提问"));await screen.findByText("确认并提问或读回同一请求");
 expect(bridge.call.mock.calls[0]).toEqual(["model_configuration_resolve",{body:{purpose:"material",lane:"fast"}}]);
 const preview=bridge.call.mock.calls[1][1].body;expect(preview).toMatchObject({model_configuration:resolved,model:"fixed-material-model",max_tokens:512,timeout_s:9});
 fireEvent.click(screen.getByText("确认并提问或读回同一请求"));await screen.findByText("configured");expect(bridge.call.mock.calls[2][1].body.model_configuration).toEqual(resolved);expect(bridge.call.mock.calls.filter(([op])=>op==="model_configuration_resolve")).toHaveLength(1);
});
