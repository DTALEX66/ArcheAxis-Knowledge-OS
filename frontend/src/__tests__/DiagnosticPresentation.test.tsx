import {it, expect} from "vitest";
import {render, screen, within} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {DocumentSnapshot} from "../components/DocumentSnapshot";
import {DiagnosticCenter} from "../components/DiagnosticConsole";
import {FrozenRequestSummary} from "../components/FrozenRequestSummary";
import type {ConversationRequestDto} from "../api/generated/conversation";

it("shows the actual unsaved snapshot text while preserving unsupported structure in diagnostics", async () => {
  const value = {type:"doc",content:[{type:"paragraph",content:[{type:"text",text:"未保存的新正文"},{type:"hardBreak"},{type:"text",text:"第二行"}]},{type:"futureBlock",attrs:{opaque:"retained"},content:[{type:"text",text:"未支持节点内的文本"}]}]};
  const {container} = render(<><DocumentSnapshot value={value} label="共享草稿"/><DiagnosticCenter/></>);
  expect(screen.getByLabelText("共享草稿").textContent).toBe("未保存的新正文\n第二行\n未支持节点内的文本");
  expect(container.textContent).not.toContain('"futureBlock"');
  await userEvent.setup().click(screen.getByRole("button", {name:/共享草稿结构记录/}));
  expect(screen.getByRole("dialog").querySelector("pre")?.textContent).toBe(JSON.stringify(value,null,2));
  expect(value.content[1].attrs).toEqual({opaque:"retained"});
});
const request: ConversationRequestDto = {session_id:"session-private",request_id:"request-private",purpose:"material_learning",material:{kind:"document",document_id:"document-private",version:7,content_sha256:"a".repeat(64),block_id:null},selection:{start_utf16:0,end_utf16:2,quote_sha256:"b".repeat(64)},question:"确认的问题",model:"frozen-model",max_tokens:1024,timeout_s:120,preview:true,confirmed_plan_sha256:null,model_configuration:{schema:"archeaxis.resolved-model/v1",configuration_revision:3,configuration_sha256:"c".repeat(64),purpose:"material",lane:"deep",profile_id:"chosen",workspace_id:"d".repeat(32),restore_epoch:"initial",profile:{endpoint:"http://127.0.0.1:1234/v1",protocol:"openai",model:"frozen-model",credential_ref:null,max_tokens:1024,timeout_s:120}}};
it("keeps the frozen purpose, material, model and destination visible with a stable material identity", () => {
  render(<FrozenRequestSummary request={request} destinationCandidates={["http://127.0.0.1:9999"]}/>);
  const summary = screen.getByRole("region", {name:"待确认请求"});
  expect(summary).toHaveTextContent("确认的问题");
  expect(summary).toHaveTextContent("已保存文档第 7 版，仅所选片段");
  expect(summary).toHaveTextContent("frozen-model（深度）");
  expect(summary).toHaveTextContent("http://127.0.0.1:1234/v1");
  expect(summary).not.toHaveTextContent("9999");
  expect(summary).not.toHaveTextContent("document-private");
  expect(summary).toHaveTextContent("材料标题尚未核对");
  expect(summary).not.toHaveTextContent(/request-private|UTF-16/);
  expect(within(summary).getByText("材料学习")).toBeInTheDocument();
});
it("never presents a legacy candidate destination as the actual selected model or loaded endpoint", () => {
  render(<FrozenRequestSummary request={{...request,model:null,model_configuration:null}} destinationCandidates={["http://127.0.0.1:1234/v1","http://127.0.0.1:4321/v1"]}/>);
  expect(screen.getByText("由本地服务选择，尚未确定")).toBeInTheDocument();
  expect(screen.getByText(/由本地服务从以下地址选择/)).toHaveTextContent("4321");
  expect(screen.queryByText(/已加载/)).toBeNull();
});

it("makes opaque content visible without changing the retained payload", () => {
  const value = {type:"doc",content:[{type:"ownerFutureBlock",attrs:{payload:{opaque:"keep"}}}]};
  render(<DocumentSnapshot value={value} label="未知内容"/>);
  expect(screen.getByLabelText("未知内容")).toHaveTextContent("此处有暂不能预览的内容，原内容已保留");
  expect(value.content[0].attrs.payload).toEqual({opaque:"keep"});
});
it("distinguishes fixed materials through matching business labels and preserves their complete identities in diagnostics", async () => {
  const user=userEvent.setup();
  const first=request.material!;
  const view=render(<><FrozenRequestSummary request={request} materialPresentation={{identity:first,title:"同名材料"}}/><DiagnosticCenter/></>);
  expect(screen.getByRole("region",{name:"待确认请求"})).toHaveTextContent("《同名材料》，已保存文档第 7 版，仅所选片段");
  await user.click(screen.getByRole("button",{name:/冻结材料身份与选区/}));
  expect(screen.getByRole("dialog").querySelector("pre")?.textContent).toBe(JSON.stringify({material:first,selection:request.selection},null,2));
  await user.click(screen.getByRole("button",{name:"关闭运行诊断"}));
  const other={kind:"document" as const,document_id:"document-other",version:7,content_sha256:"e".repeat(64),block_id:"block-other"};
  view.rerender(<><FrozenRequestSummary request={{...request,material:other}} materialPresentation={{identity:other,title:"同名材料"}}/><DiagnosticCenter/></>);
  expect(screen.getByRole("region",{name:"待确认请求"})).toHaveTextContent("已保存文档第 7 版，指定内容块");
  expect(screen.getByRole("region",{name:"待确认请求"})).not.toHaveTextContent(/document-other|block-other/);
  await user.click(screen.getByRole("button",{name:/冻结材料身份与选区/}));
  expect(screen.getByRole("dialog").querySelector("pre")?.textContent).toBe(JSON.stringify({material:other,selection:request.selection},null,2));
  await user.click(screen.getByRole("button",{name:"关闭运行诊断"}));
  const nextVersion={...other,version:8};
  view.rerender(<><FrozenRequestSummary request={{...request,material:nextVersion}} materialPresentation={{identity:nextVersion,title:"同名材料"}}/><DiagnosticCenter/></>);
  expect(screen.getByRole("region",{name:"待确认请求"})).toHaveTextContent("已保存文档第 8 版，指定内容块");
  const transformed={kind:"transform" as const,source_id:"source-A",job_id:"job-A",raw_sha256:"a".repeat(64),transform_id:31,transform_sha256:"b".repeat(64)};
  view.rerender(<><FrozenRequestSummary request={{...request,material:transformed}} materialPresentation={{identity:transformed,title:"原件提取正文"}}/><DiagnosticCenter/></>);
  expect(screen.getByRole("region",{name:"待确认请求"})).toHaveTextContent("《原件提取正文》，已固定提取结果");
  await user.click(screen.getByRole("button",{name:/冻结材料身份与选区/}));
  expect(screen.getByRole("dialog").querySelector("pre")?.textContent).toBe(JSON.stringify({material:transformed,selection:request.selection},null,2));
});
it.each(["document_id","version","content_sha256","block_id"] as const)("does not substitute a display title from a different frozen %s",key=>{
  const wrong={...request.material!,[key]:key==="version"?99:"different"};
  render(<FrozenRequestSummary request={request} materialPresentation={{identity:wrong,title:"未经匹配的标题"}}/>);
  const summary=screen.getByRole("region",{name:"待确认请求"});
  expect(summary).not.toHaveTextContent("未经匹配的标题");expect(summary).toHaveTextContent("材料标题尚未核对");expect(summary).toHaveTextContent("已保存文档第 7 版");
});
it("keeps exact frozen consent fields visible for a cloud endpoint without claiming local execution",()=>{
  const cloud={...request,question:"仍是冻结问题",model_configuration:{...request.model_configuration!,lane:"fast" as const,profile:{...request.model_configuration!.profile,endpoint:"https://models.example.test/v1",model:"cloud-frozen"}}};
  render(<FrozenRequestSummary request={cloud} materialPresentation={{identity:request.material!,title:"已读材料"}}/>);
  const summary=screen.getByRole("region",{name:"待确认请求"});
  expect(summary).toHaveTextContent("仍是冻结问题");expect(summary).toHaveTextContent("cloud-frozen（快速）");expect(summary).toHaveTextContent("https://models.example.test/v1");expect(summary).toHaveTextContent("最多 1024 token，等待上限 120 秒");expect(summary).not.toHaveTextContent("本地服务");
});


it("preserves list numbering, nested item order, explicit task states and deleted text in the inert snapshot", () => {
  const value = {type:"doc",content:[
    {type:"orderedList",attrs:{start:7},content:[
      {type:"listItem",content:[{type:"paragraph",content:[{type:"text",text:"第七步"}]},{type:"bulletList",content:[{type:"listItem",content:[{type:"paragraph",content:[{type:"text",text:"先检查"}]}]},{type:"listItem",content:[{type:"paragraph",content:[{type:"text",text:"后执行"}]}]}]}]},
      {type:"listItem",content:[{type:"paragraph",content:[{type:"text",text:"旧结论",marks:[{type:"strike"}]},{type:"text",text:"新结论"}]}]}]},
    {type:"taskList",content:[{type:"taskItem",attrs:{checked:true},content:[{type:"paragraph",content:[{type:"text",text:"已核对"}]}]},{type:"taskItem",attrs:{checked:false},content:[{type:"paragraph",content:[{type:"text",text:"待完成"}]}]},{type:"taskItem",content:[{type:"paragraph",content:[{type:"text",text:"状态未声明"}]}]}]}
  ]};
  const before = JSON.stringify(value);
  const {container} = render(<DocumentSnapshot value={value} label="语义快照" showRaw={false}/>);
  expect(screen.getByLabelText("语义快照").textContent).toBe("7. 第七步\n   - 先检查\n   - 后执行\n8. 〔删除线：旧结论〕新结论\n[x] 已核对\n[ ] 待完成\n[?] 状态未声明");
  expect(JSON.stringify(value)).toBe(before);
  expect(container.querySelector("input, a, button, [contenteditable]")).toBeNull();
});

it("keeps untrusted snapshot text inert while showing strike semantics", () => {
  const {container} = render(<DocumentSnapshot value={{type:"doc",content:[{type:"paragraph",content:[{type:"text",text:'<img src="https://example.invalid/pixel" onerror="alert(1)">',marks:[{type:"strike"},{type:"link",attrs:{href:"https://example.invalid"}}]}]}]}} label="安全快照" showRaw={false}/>);
  expect(screen.getByLabelText("安全快照")).toHaveTextContent('〔删除线：<img src="https://example.invalid/pixel" onerror="alert(1)">〕');
  expect(container.querySelector("img, a, script")).toBeNull();
});

it("keeps a recovery preview available when a saved node shape cannot be rendered", () => {
  const value=JSON.parse('{"type":"doc","content":[null,{"type":"taskList","content":[null]},{"type":"paragraph","content":"invalid"},{"type":"paragraph","content":[{"type":"text","text":"仍可预览的草稿","marks":{}}]}]}');
  const before=JSON.stringify(value);
  render(<DocumentSnapshot value={value} label="待恢复草稿" showRaw={false}/>);
  expect(screen.getByLabelText("待恢复草稿")).toHaveTextContent("仍可预览的草稿");
  expect(screen.getByLabelText("待恢复草稿")).toHaveTextContent("暂不能预览的内容，原内容已保留");
  expect(JSON.stringify(value)).toBe(before);
});
