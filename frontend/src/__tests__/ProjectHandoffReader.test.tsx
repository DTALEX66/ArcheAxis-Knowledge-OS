import { createHash, webcrypto } from "node:crypto";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { ProjectHandoffReader } from "../components/ProjectHandoffReader";
import { SpaceView } from "../spaces/SpaceView";
import { resetDiagnostics, useDiagnostics } from "../presentation/diagnostics";
const bridge = vi.hoisted(() => ({call:vi.fn(),mounts:0}));
vi.mock("../api/core", () => ({coreCommand:bridge.call}));
vi.mock("../spaces/CanonicalExchangeSpace", () => ({CanonicalExchangeSpace:() => {
  const [value,setValue] = useState(() => {bridge.mounts++;return "原交换草稿";});
  return <label>原交换草稿<input aria-label="原交换草稿" value={value} onChange={e=>setValue(e.target.value)}/></label>;
}}));
const canonical = (v:unknown):unknown => Array.isArray(v) ? v.map(canonical) : v && typeof v === "object" ? Object.fromEntries(Object.entries(v).sort(([a],[b])=>a < b ? -1 : a > b ? 1 : 0).map(([k,x])=>[k,canonical(x)])) : v;
function fixture(id="doc_a", version=2) {
  const now=Date.now();
  const proposal={schema:"archeaxis.project-handoff/v1",protocol:"archeaxis.project-observer/v1",idempotency_key:"2".repeat(32),producer:{namespace:"archeaxis",workspace_id:"a".repeat(32),restore_epoch:"initial"},consumer:{namespace:"work-lab",instance_id:"b".repeat(32)},created_at_ms:now,expires_at_ms:now+30000,authority:"PREPARATION_ONLY",payload:{kind:"context",source:{reference:{document_id:id,version,content_sha256:"c".repeat(64)},selection:{kind:"whole_object"},selection_qualification:"UNVERIFIED"},purpose:"learning",authorization_scope:"REFERENCE_METADATA_ONLY"}};
  const sha=createHash("sha256").update("archeaxis.project-handoff/v1\0"+JSON.stringify(canonical(proposal))).digest("hex");
  const preview={schema:"archeaxis.project-handoff-preview/v1",checked_at_ms:now,expires_at_ms:proposal.expires_at_ms,proposal,proposal_sha256:sha,reference_state:"CURRENT",source_authentication:"UNVERIFIED",authority:"REFERENCE_METADATA_ONLY",navigation:"UNAVAILABLE",grants_execution:false,grants_knowledge_acceptance:false};
  const snapshot={schema:"archeaxis.project-handoff-snapshot/v1",checked_at_ms:now,expires_at_ms:proposal.expires_at_ms,proposal_sha256:sha,producer:proposal.producer,reference:proposal.payload.source.reference,reference_state:"CURRENT",source_authentication:"UNVERIFIED",selection_qualification:"UNVERIFIED",scope:"LOCAL_HUMAN_READ_ONLY",editor_json:{type:"doc",content:[{type:"paragraph",content:[{type:"text",text:`固定正文 ${id} v${version}`},{type:"hardBreak"},{type:"text",text:"第二行"}]}]},grants_execution:false,grants_knowledge_acceptance:false};
  return {proposal,preview,snapshot};
}
let data:ReturnType<typeof fixture>;
beforeEach(()=>{
  vi.stubGlobal("crypto",webcrypto);data=fixture();bridge.mounts=0;bridge.call.mockReset();bridge.call.mockImplementation(async(op:string)=>op==="project_handoff_preview"?data.preview:data.snapshot);
});
afterEach(()=>{vi.useRealTimers();vi.unstubAllGlobals();vi.restoreAllMocks();});
async function openAndPaste(value:unknown=data.proposal) {
  await userEvent.setup().click(screen.getByRole("button",{name:"预览跨项目引用"}));
  fireEvent.change(screen.getByRole("textbox",{name:"上下文提案 JSON"}),{target:{value:JSON.stringify(value)}});
}
async function preview() {fireEvent.click(screen.getByRole("button",{name:"预览引用信息"}));await screen.findByRole("region",{name:"提案只读预览"});}
async function body() {fireEvent.click(screen.getByRole("button",{name:"打开固定版本全文"}));await screen.findByLabelText("固定版本全文");}
it("SIMULATED two explicit actions are required and exact body stays inert with line breaks",async()=>{
  render(<ProjectHandoffReader/>);await openAndPaste();expect(bridge.call).not.toHaveBeenCalled();await preview();
  expect(bridge.call.mock.calls.map(x=>x[0])).toEqual(["project_handoff_preview"]);expect(screen.getByText(/选区尚未核验/)).toBeInTheDocument();expect(screen.queryByLabelText("固定版本全文")).toBeNull();
  await body();expect(screen.getByLabelText("固定版本全文").textContent).toBe("固定正文 doc_a v2\n第二行");expect(document.querySelector('[contenteditable="true"]')).toBeNull();
  expect(bridge.call.mock.calls).toEqual([["project_handoff_preview",{body:data.proposal}],["project_handoff_snapshot",{body:data.proposal}]]);
});
it("SIMULATED stale fixed version is readable without replacing it with current",async()=>{
  data.preview.reference_state="STALE";data.snapshot.reference_state="STALE";
  render(<ProjectHandoffReader/>);await openAndPaste();await preview();expect(screen.getByText(/不替代为新版/)).toBeInTheDocument();await body();expect(screen.getByLabelText("固定版本全文")).toHaveTextContent("v2");
});
it("SIMULATED NOT_FOUND never reads a substitute body",async()=>{
  data.preview.reference_state="NOT_FOUND";render(<ProjectHandoffReader/>);await openAndPaste();await preview();expect(screen.getByRole("button",{name:"打开固定版本全文"})).toBeDisabled();expect(bridge.call).toHaveBeenCalledTimes(1);
});
it.each(["invalid-json","oversize","task","expired"])("SIMULATED rejects %s before native invocation",async kind=>{
  render(<ProjectHandoffReader/>);await openAndPaste(kind==="task"?{...data.proposal,payload:{kind:"task_proposal"}}:kind==="expired"?{...data.proposal,expires_at_ms:Date.now()-1}:data.proposal);
  if(kind==="invalid-json"||kind==="oversize")fireEvent.change(screen.getByRole("textbox"),{target:{value:kind==="invalid-json"?"{":" ".repeat(65537)}});
  // Oversize whitespace would leave the preview button disabled; include a non-whitespace byte.
  if(kind==="oversize")fireEvent.change(screen.getByRole("textbox"),{target:{value:'{"x":"'+"x".repeat(65537)+'"}'}});
  fireEvent.click(screen.getByRole("button",{name:"预览引用信息"}));await screen.findByRole("alert");expect(bridge.call).not.toHaveBeenCalled();
});
it.each(["reference","producer","sha","authority"])("SIMULATED rejects a successful wrong %s snapshot before exposing text",async kind=>{
  if(kind==="reference")data.snapshot.reference={...data.snapshot.reference,document_id:"other"};
  if(kind==="producer")data.snapshot.producer={...data.snapshot.producer,restore_epoch:"e".repeat(32)};
  if(kind==="sha")data.snapshot.proposal_sha256="f".repeat(64);
  if(kind==="authority")data.snapshot.grants_execution=true;
  render(<ProjectHandoffReader/>);await openAndPaste();await preview();fireEvent.click(screen.getByRole("button",{name:"打开固定版本全文"}));await screen.findByRole("alert");expect(screen.queryByLabelText("固定版本全文")).toBeNull();
});
it("SIMULATED duplicate clicks invoke once; changing input cancels the old queued response",async()=>{
  let resolve!:(x:unknown)=>void;bridge.call.mockImplementation(()=>new Promise(r=>resolve=r));render(<ProjectHandoffReader/>);await openAndPaste();const button=screen.getByRole("button",{name:"预览引用信息"});fireEvent.click(button);fireEvent.click(button);expect(bridge.call).toHaveBeenCalledTimes(1);
  const second=fixture("doc_b");fireEvent.change(screen.getByRole("textbox"),{target:{value:JSON.stringify(second.proposal)}});await act(async()=>resolve(data.preview));expect(screen.queryByRole("region",{name:"提案只读预览"})).toBeNull();
  bridge.call.mockResolvedValue(second.preview);await preview();expect(screen.getByRole("region",{name:"提案只读预览"})).toHaveTextContent("第 2 版");expect(bridge.call).toHaveBeenLastCalledWith("project_handoff_preview",{body:second.proposal});
});
it("SIMULATED close discards a pending body and returns focus to the real opener",async()=>{
  render(<ProjectHandoffReader/>);await openAndPaste();await preview();let resolve!:(x:unknown)=>void;bridge.call.mockImplementation(()=>new Promise(r=>resolve=r));fireEvent.click(screen.getByRole("button",{name:"打开固定版本全文"}));fireEvent.click(screen.getByRole("button",{name:"关闭并返回"}));await waitFor(()=>expect(screen.getByRole("button",{name:"预览跨项目引用"})).toHaveFocus());await act(async()=>resolve(data.snapshot));expect(screen.queryByRole("dialog")).toBeNull();await openAndPaste();expect(screen.queryByLabelText("固定版本全文")).toBeNull();
});
it("SIMULATED Escape closes and restores focus without writing",async()=>{
  render(<ProjectHandoffReader/>);await openAndPaste();await userEvent.setup().keyboard("{Escape}");await waitFor(()=>expect(screen.getByRole("button",{name:"预览跨项目引用"})).toHaveFocus());expect(bridge.call).not.toHaveBeenCalled();
});
it.each(["workspace-invalidated","workspace-restore-start"])("SIMULATED %s clears old input and rejects late body",async event=>{
  render(<ProjectHandoffReader/>);await openAndPaste();await preview();let resolve!:(x:unknown)=>void;bridge.call.mockImplementation(()=>new Promise(r=>resolve=r));fireEvent.click(screen.getByRole("button",{name:"打开固定版本全文"}));act(()=>window.dispatchEvent(new CustomEvent(event,{detail:{confirmed:true}})));await act(async()=>resolve(data.snapshot));expect(screen.queryByLabelText("固定版本全文")).toBeNull();expect(screen.getByRole("textbox")).toHaveValue("");expect(screen.getByRole("button",{name:"预览引用信息"})).toBeDisabled();
});
it("SIMULATED snapshot expiry removes already rendered body without another read",async()=>{
  render(<ProjectHandoffReader/>);await openAndPaste();await preview();data.snapshot.expires_at_ms=Date.now()+5000;vi.useFakeTimers();await act(async()=>{fireEvent.click(screen.getByRole("button",{name:"打开固定版本全文"}));});expect(screen.getByLabelText("固定版本全文")).toBeInTheDocument();await act(async()=>{await vi.advanceTimersByTimeAsync(5001);});expect(screen.queryByLabelText("固定版本全文")).toBeNull();expect(screen.getByRole("alert")).toHaveTextContent("到期");expect(bridge.call).toHaveBeenCalledTimes(2);
});
it("SIMULATED a body completed after its deadline is rejected",async()=>{
  render(<ProjectHandoffReader/>);await openAndPaste();await preview();let resolve!:(x:unknown)=>void;bridge.call.mockImplementation(()=>new Promise(r=>resolve=r));fireEvent.click(screen.getByRole("button",{name:"打开固定版本全文"}));vi.spyOn(Date,"now").mockReturnValue(data.proposal.expires_at_ms);await act(async()=>resolve(data.snapshot));expect(screen.queryByLabelText("固定版本全文")).toBeNull();vi.restoreAllMocks();
});
it("SIMULATED parking the owning page closes the portal and cannot expose a late body",async()=>{
  const host=document.createElement("div");document.body.append(host);const rendered=render(<ProjectHandoffReader/>,{container:host});await openAndPaste();await preview();let resolve!:(x:unknown)=>void;bridge.call.mockImplementation(()=>new Promise(r=>resolve=r));fireEvent.click(screen.getByRole("button",{name:"打开固定版本全文"}));act(()=>{host.hidden=true;});await waitFor(()=>expect(screen.queryByRole("dialog")).toBeNull());await act(async()=>resolve(data.snapshot));expect(screen.queryByLabelText("固定版本全文")).toBeNull();rendered.unmount();host.remove();
});
it("SIMULATED real page16 route keeps the Exchange component and local draft mounted across close",async()=>{
  render(<SpaceView spaceId="exchange" uiPageId="16" onInspect={()=>{}} onNavigate={()=>{}}/>);fireEvent.change(screen.getByRole("textbox",{name:"原交换草稿"}),{target:{value:"保留修改"}});await openAndPaste();await preview();await body();fireEvent.click(screen.getByRole("button",{name:"关闭并返回"}));expect(screen.getByRole("textbox",{name:"原交换草稿"})).toHaveValue("保留修改");expect(bridge.mounts).toBe(1);expect(bridge.call.mock.calls.every(([op])=>op==="project_handoff_preview"||op==="project_handoff_snapshot")).toBe(true);
});

it("SIMULATED real digest verification rejects a well-shaped but wrong preview fingerprint",async()=>{
  data.preview.proposal_sha256="f".repeat(64);render(<ProjectHandoffReader/>);await openAndPaste();fireEvent.click(screen.getByRole("button",{name:"预览引用信息"}));expect(await screen.findByRole("alert")).toHaveTextContent("指纹");expect(screen.queryByRole("button",{name:"打开固定版本全文"})).toBeNull();expect(bridge.call).toHaveBeenCalledTimes(1);
});
it("SIMULATED restore pause refuses newly pasted input until finish without reusing old approval",async()=>{
  render(<ProjectHandoffReader/>);await openAndPaste();await preview();act(()=>window.dispatchEvent(new Event("workspace-restore-start")));fireEvent.change(screen.getByRole("textbox"),{target:{value:JSON.stringify(data.proposal)}});expect(screen.getByRole("button",{name:"预览引用信息"})).toBeDisabled();act(()=>window.dispatchEvent(new Event("workspace-restore-finish")));expect(screen.getByRole("button",{name:"预览引用信息"})).toBeEnabled();expect(screen.queryByRole("button",{name:"打开固定版本全文"})).toBeNull();expect(bridge.call).toHaveBeenCalledTimes(1);
});

it("SIMULATED a future or malformed body projection cannot unmount the reader or underlying Exchange",async()=>{
  vi.spyOn(console,"error").mockImplementation(()=>{});data.snapshot.editor_json={type:"doc",content:"opaque"} as never;
  const original=JSON.stringify(data.snapshot);
  render(<SpaceView spaceId="exchange" uiPageId="16" onInspect={()=>{}} onNavigate={()=>{}}/>);await openAndPaste();await preview();fireEvent.click(screen.getByRole("button",{name:"打开固定版本全文"}));expect(await screen.findByLabelText("固定版本全文")).toHaveTextContent("此处有暂不能预览的内容，原内容已保留");expect(JSON.stringify(data.snapshot)).toBe(original);expect(bridge.call.mock.calls.map(([op])=>op)).toEqual(["project_handoff_preview","project_handoff_snapshot"]);expect(screen.getByRole("button",{name:/跨项目固定正文身份/})).toBeInTheDocument();fireEvent.click(screen.getByRole("button",{name:"关闭并返回"}));expect(screen.getByRole("textbox",{name:"原交换草稿"})).toHaveValue("原交换草稿");expect(bridge.mounts).toBe(1);
});

it("SIMULATED a change after CURRENT preview is clearly disclosed by the STALE snapshot",async()=>{
  data.preview.reference_state="CURRENT";data.snapshot.reference_state="STALE";
  render(<ProjectHandoffReader/>);await openAndPaste();await preview();await body();
  expect(screen.getByRole("region",{name:"本机固定版本只读正文"})).toHaveTextContent("读取时当前保存版本已变化");
  expect(screen.getByRole("region",{name:"提案只读预览"})).toHaveTextContent("预览时");
});

it("SIMULATED explicit diagnostics preserve identity only and cannot retain body after close or invalidation",async()=>{
  resetDiagnostics();
  function Probe(){return <output data-testid="diagnostic-probe">{JSON.stringify(useDiagnostics())}</output>;}
  render(<><ProjectHandoffReader/><Probe/></>);await openAndPaste();await preview();await body();
  expect(screen.queryByRole("button",{name:/固定版本全文结构记录/})).toBeNull();
  fireEvent.click(screen.getByRole("button",{name:/跨项目固定正文身份/}));
  const output=screen.getByTestId("diagnostic-probe");
  expect(output.textContent).toContain("LOCAL_HUMAN_READ_ONLY");
  expect(output.textContent).not.toContain("editor_json");expect(output.textContent).not.toContain("固定正文 doc_a");
  fireEvent.click(screen.getByRole("button",{name:"关闭并返回"}));
  act(()=>window.dispatchEvent(new Event("workspace-invalidated")));
  expect(output.textContent).not.toContain("固定正文 doc_a");resetDiagnostics();
});


it("SIMULATED page16 fixed body retains list start and deleted decision meaning through the shared snapshot projection", async()=>{
  data.snapshot.editor_json={type:"doc",content:[{type:"orderedList",attrs:{start:4},content:[{type:"listItem",content:[{type:"paragraph",content:[{type:"text",text:"允许覆盖",marks:[{type:"strike"}]},{type:"text",text:"保留原件"}]}]},{type:"listItem",content:[{type:"paragraph",content:[{type:"text",text:"检查回执"}]}]}]}]} as never;
  render(<SpaceView spaceId="exchange" uiPageId="16" onInspect={()=>{}} onNavigate={()=>{}}/>);await openAndPaste();await preview();await body();
  expect(screen.getByLabelText("固定版本全文").textContent).toBe("4. 〔删除线：允许覆盖〕保留原件\n5. 检查回执");
  expect(document.querySelector('[contenteditable="true"], .document-snapshot-text a')).toBeNull();
  expect(bridge.call.mock.calls.map(([op])=>op)).toEqual(["project_handoff_preview","project_handoff_snapshot"]);
});
