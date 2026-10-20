import { webcrypto } from "node:crypto";
import { cleanup,fireEvent,render,screen,waitFor } from "@testing-library/react";
import { afterEach,beforeEach,expect,it,vi } from "vitest";
import { PortableDocumentExchange } from "../components/PortableDocumentExchange";
import { coreCommand } from "../api/core";
vi.mock("../api/core",()=>({coreCommand:vi.fn()}));
vi.mock("../presentation/exchangeProof",()=>({downloadBytes:vi.fn(),sameValue:(a:unknown,b:unknown)=>JSON.stringify(a)===JSON.stringify(b)}));
const doc={document_id:"doc1",source_id:null,source_revision:null,title:"合成包",version:1,editor_json:{type:"doc",content:[]},text_projection:"",content_sha256:"a".repeat(64),blocks:[],revision_basis:null};
const bundle={schema:"archeaxis.document-package/v1",document:doc,objects:[],historical_anchors:[]};
function file() {const f=new File([JSON.stringify(bundle)],"synthetic.json",{type:"application/json"});Object.defineProperty(f,"text",{value:async()=>JSON.stringify(bundle)});return f;}
beforeEach(()=>{vi.stubGlobal("crypto",webcrypto);vi.mocked(coreCommand).mockReset();});
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
it("SIMULATED requires file selection and explicit save; unknown failure reuses the frozen request",async()=>{
  let fail=true;vi.mocked(coreCommand).mockImplementation(async(op):Promise<any>=>{if(op==="document_package_import"){if(fail)throw new Error("unknown transport");return {schema:"archeaxis.document-package-import/v1",package_sha256:"b".repeat(64),document:doc,source_mapping:{},historical_anchors:[],anchor_registration:"NOT_EXECUTED",knowledge_admission:"NOT_EXECUTED"};}return doc;});
  render(<PortableDocumentExchange saved={null}/>);
  fireEvent.change(screen.getByLabelText("选择本地文档包"),{target:{files:[file()]}});
  await screen.findByText(/待保存：合成包/);expect(coreCommand).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button",{name:"确认保存为新普通文档"}));
  await screen.findByText("unknown transport");
  const first=vi.mocked(coreCommand).mock.calls[0][1];fail=false;
  fireEvent.click(screen.getByRole("button",{name:"检查结果并重试同一次导入"}));
  await screen.findByText(/已保存为新文档；尚未加入知识库，旧引用位置需要重新核对/);
  expect(vi.mocked(coreCommand).mock.calls[1][1]).toEqual(first);
  expect(vi.mocked(coreCommand).mock.calls.some(([op])=>op==="knowledge_review")).toBe(false);
});
it("SIMULATED reselecting the same package after remount retains its idempotency identity",async()=>{
  vi.mocked(coreCommand).mockRejectedValue(new Error("unknown"));
  const firstRender=render(<PortableDocumentExchange saved={null}/>);
  fireEvent.change(screen.getByLabelText("选择本地文档包"),{target:{files:[file()]}});await screen.findByText(/待保存/);
  fireEvent.click(screen.getByRole("button",{name:"确认保存为新普通文档"}));await screen.findByText("unknown");
  const first=vi.mocked(coreCommand).mock.calls[0][1];firstRender.unmount();
  render(<PortableDocumentExchange saved={null}/>);fireEvent.change(screen.getByLabelText("选择本地文档包"),{target:{files:[file()]}});await screen.findByText(/待保存/);
  fireEvent.click(screen.getByRole("button",{name:"确认保存为新普通文档"}));await waitFor(()=>expect(coreCommand).toHaveBeenCalledTimes(2));
  expect(vi.mocked(coreCommand).mock.calls[1][1]).toEqual(first);
});
