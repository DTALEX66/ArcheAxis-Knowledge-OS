import { beforeEach,afterEach,it,expect,vi } from "vitest";
import { webcrypto } from "node:crypto";
import { render,screen,fireEvent,waitFor } from "@testing-library/react";
import { CanonicalAiAssetsSpace } from "../spaces/CanonicalAiAssetsSpace";
import { documentRequestIdentity } from "../presentation/documentRequestIdentity";
import type { DocumentDto } from "../api/generated/core-contract";
import type { AiAsset,AssetContextGrant } from "../api/generated/ai-asset-contract";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
type J=Record<string,any>;
const asset=(state:AiAsset["state"]="candidate"):AiAsset=>({schema:"archeaxis.ai-asset/v1",kind:"memory",content:"原始内容",purpose:"",scope:[],provenance:[],expires_at:null,state,members:[],conflicts:[],revises:null,review:null,source_payload:{unknown:[1,null,"保留"]}});
function dto(id:string,value:AiAsset=asset(),version=1):DocumentDto{return {document_id:id,title:id,version,source_id:null,source_revision:null,content_sha256:"a".repeat(64),blocks:[],text_projection:"原文",editor_json:{type:"doc",attrs:{archeaxis_ai_asset:value,unknownOwner:{x:[null,"原值"]}},content:[{type:"future",payload:{bytes:"不丢"}}]}};}
const parse=(v:unknown)=>{const x=v as J;return x?.schema==="archeaxis.ai-asset/v1"&&!('future' in x)?structuredClone(x) as AiAsset:null;};
const props={parseAsset:parse,parseGrant:()=>null as AssetContextGrant|null,packetCommand:vi.fn()};
let docs:Map<string,DocumentDto>,writes:J[],original:(op:string,p?:J)=>Promise<unknown>;
beforeEach(()=>{vi.stubGlobal("crypto",webcrypto);docs=new Map([["asset_saved",dto("asset_saved")]]);writes=[];bridge.call.mockReset();original=async(op,p={})=>{
 if(op==="ai_assets_list")return {items:[...docs.values()].map(d=>({document_id:d.document_id,title:d.title,version:d.version,content_sha256:d.content_sha256})),next_cursor:null};
 if(op==="document_get")return structuredClone(docs.get(p.document_id));
 if(op==="document_version")return dto(p.document_id,asset(),p.version);
 if(op==="document_create"){writes.push(structuredClone(p));const id=await documentRequestIdentity(p.body.create_request_id);if(!docs.has(id))docs.set(id,{...dto(id),title:p.body.title,editor_json:structuredClone(p.body.editor_json)});return structuredClone(docs.get(id));}
 if(op==="document_draft"){writes.push(structuredClone(p));const old=docs.get(p.document_id)!;const next={...old,version:old.version+1,editor_json:structuredClone(p.body.editor_json)};docs.set(p.document_id,next);return structuredClone(next);}
 throw new Error(`unimplemented ${op}`);
};bridge.call.mockImplementation(original);});
afterEach(()=>{vi.unstubAllGlobals();vi.restoreAllMocks();});
async function open(){fireEvent.click(await screen.findByRole("button",{name:"asset_saved · v1"}));await waitFor(()=>expect(screen.getByLabelText("资产内容")).toHaveValue("原始内容"));}
it("saves incomplete inert candidates for all five kinds without knowledge or rubric prerequisite",async()=>{render(<CanonicalAiAssetsSpace {...props}/>);for(const kind of ["memory","knowledge_package","rule","skill","experience"]){fireEvent.change(screen.getByLabelText("资产类型"),{target:{value:kind}});fireEvent.change(screen.getByLabelText("资产内容"),{target:{value:`惰性 ${kind}`}});fireEvent.click(screen.getByRole("button",{name:"保存资产候选"}));await waitFor(()=>expect(writes.at(-1)?.body.editor_json.attrs.archeaxis_ai_asset.kind).toBe(kind));await screen.findByText("资产版本已保存并读回；保存及采用均不授予 AI 资格。");expect(writes.at(-1)?.body.editor_json.attrs.archeaxis_ai_asset.state).toBe("candidate");expect(writes.at(-1)?.body.editor_json.attrs.archeaxis_ai_asset.review).toBeNull();await waitFor(()=>expect(screen.getByRole("button",{name:"保存资产候选"})).toBeEnabled());}expect(props.packetCommand).not.toHaveBeenCalled();});
it("preserves complete envelope and source payload on semantic edits",async()=>{render(<CanonicalAiAssetsSpace {...props}/>);await open();fireEvent.change(screen.getByLabelText("资产用途"),{target:{value:"新用途"}});fireEvent.click(screen.getByRole("button",{name:"保存资产候选"}));await screen.findByText("资产版本已保存并读回；保存及采用均不授予 AI 资格。");const editor=writes[0].body.editor_json;expect(editor.attrs.unknownOwner).toEqual({x:[null,"原值"]});expect(editor.content).toEqual([{type:"future",payload:{bytes:"不丢"}}]);expect(editor.attrs.archeaxis_ai_asset.source_payload).toEqual(asset().source_payload);});
it("lost acknowledgement retries identical identity and retains later draft",async()=>{let first=true;bridge.call.mockImplementation(async(op,p)=>{const result=await original(op,p);if(op==="document_create"&&first){first=false;throw new Error("lost ack");}return result;});render(<CanonicalAiAssetsSpace {...props}/>);fireEvent.change(screen.getByLabelText("资产内容"),{target:{value:"发送版本"}});fireEvent.click(screen.getByRole("button",{name:"保存资产候选"}));await screen.findByRole("alert");fireEvent.change(screen.getByLabelText("资产内容"),{target:{value:"随后草稿"}});fireEvent.click(screen.getByRole("button",{name:"重试冻结资产请求"}));await screen.findByText("发送版本已确认；后续草稿仍保留。");expect(writes).toHaveLength(2);expect(writes[0]).toEqual(writes[1]);expect(screen.getByLabelText("资产内容")).toHaveValue("随后草稿");expect(docs.size).toBe(2);});
it.each(["document_id","title","source_id"])("rejects wrong %s ACK even when metadata/body match",async(field)=>{bridge.call.mockImplementation(async(op,p)=>{const result=await original(op,p) as J;if(op==="document_create")result[field]="unexpected";return result;});render(<CanonicalAiAssetsSpace {...props}/>);fireEvent.click(screen.getByRole("button",{name:"保存资产候选"}));await screen.findByRole("alert");expect(screen.getByRole("button",{name:"核对冻结资产请求"})).toBeInTheDocument();expect(screen.queryByText("资产版本已保存并读回；保存及采用均不授予 AI 资格。")).not.toBeInTheDocument();});
it("unknown metadata stays readonly without strip or overwrite",async()=>{(docs.get("asset_saved")!.editor_json as J).attrs.archeaxis_ai_asset.future={unknown:"raw"};render(<CanonicalAiAssetsSpace {...props}/>);fireEvent.click(await screen.findByRole("button",{name:"asset_saved · v1"}));await screen.findByText("不兼容资产只读");expect(screen.queryByLabelText("资产内容")).not.toBeInTheDocument();expect(writes).toEqual([]);});
it("invalid JSON and incomplete expiry protect switching and preserve original values",async()=>{render(<CanonicalAiAssetsSpace {...props}/>);await open();fireEvent.click(screen.getByRole("button",{name:"编辑惰性 JSON 内容"}));fireEvent.change(screen.getByLabelText("JSON 内容草稿"),{target:{value:'{"incomplete":'}});fireEvent.click(screen.getByRole("button",{name:"新建资产候选"}));expect(screen.getByLabelText("JSON 内容草稿")).toHaveValue('{"incomplete":');fireEvent.click(screen.getByRole("button",{name:"保存资产候选"}));expect(writes).toEqual([]);fireEvent.click(screen.getByRole("button",{name:"取消 JSON 编辑"}));expect(screen.getByLabelText("资产内容")).toHaveValue("原始内容");fireEvent.change(screen.getByLabelText("到期 Unix 秒（空白为无期限）"),{target:{value:"-"}});fireEvent.click(screen.getByRole("button",{name:"提交时效"}));await screen.findByRole("alert");expect(writes).toEqual([]);});
it("withdrawal keeps history readable and rejects new edits/adoption",async()=>{render(<CanonicalAiAssetsSpace {...props}/>);await open();fireEvent.click(screen.getByRole("button",{name:"撤回资产"}));await screen.findByText("资产版本已保存并读回；保存及采用均不授予 AI 资格。");expect(screen.getByLabelText("资产内容")).toBeDisabled();expect(screen.getByRole("button",{name:"明确采用此评审版本"})).toBeDisabled();fireEvent.click(screen.getByRole("button",{name:"读取资产历史"}));await screen.findByText("历史 v1 只读，当前草稿未替换。");expect((docs.get("asset_saved")!.editor_json as J).attrs.archeaxis_ai_asset.state).toBe("withdrawn");});
it("late history response cannot replace or publish across subsequent edits",async()=>{let resolve!:(v:unknown)=>void;bridge.call.mockImplementation((op,p)=>op==="document_version"?new Promise(r=>resolve=r):original(op,p));render(<CanonicalAiAssetsSpace {...props}/>);await open();fireEvent.click(screen.getByRole("button",{name:"读取资产历史"}));fireEvent.change(screen.getByLabelText("资产内容"),{target:{value:"新草稿"}});resolve(dto("asset_saved"));await waitFor(()=>expect(screen.getByLabelText("资产内容")).toHaveValue("新草稿"));expect(screen.queryByText("历史 v1 只读，当前草稿未替换。")).not.toBeInTheDocument();});
it("adoption requires review of exact saved candidate and actual rubric criteria, later edits reset adoption",async()=>{
 const rubric={...dto("rubric"),version:3,editor_json:{type:"doc",attrs:{archeaxis_machine_rubric:{schema:"archeaxis.machine-rubric/v1",request_id:"rubric_req",title:"实际评审",purpose:"资产评审",criteria:[{criterion_id:"fidelity",label:"保真",expectation:"与来源相符"}],sources:[]}},content:[]}};
 bridge.call.mockImplementation(async(op,p)=>{if(op==="documents_list")return {documents:[{document_id:"rubric",title:"实际评审",version:3}],next_cursor:null,snapshot_count:1};if(op==="document_get"&&p.document_id==="rubric")return rubric;return original(op,p);});
 render(<CanonicalAiAssetsSpace {...props}/>);await open();fireEvent.click(screen.getByRole("button",{name:"选择实际评审准则"}));fireEvent.click(screen.getByRole("button",{name:"读取文档对象"}));await screen.findByRole("option",{name:"实际评审 · 列表 v3"});fireEvent.change(screen.getByLabelText("选择文档"),{target:{value:"rubric"}});await screen.findByRole("button",{name:"加入此对象版本"});fireEvent.click(screen.getByRole("button",{name:"加入此对象版本"}));
 fireEvent.change(screen.getByLabelText("评审人"),{target:{value:"本人"}});fireEvent.change(screen.getByLabelText("评审依据"),{target:{value:"逐项核对实际来源"}});fireEvent.change(screen.getByLabelText("判定 保真"),{target:{value:"passed"}});fireEvent.change(screen.getByLabelText("依据 保真"),{target:{value:"实际来源固定版本"}});fireEvent.click(screen.getByRole("button",{name:"确认全部人工评审通过"}));fireEvent.click(screen.getByRole("button",{name:"明确采用此评审版本"}));await screen.findByText("资产版本已保存并读回；保存及采用均不授予 AI 资格。");const v=writes[0].body.editor_json.attrs.archeaxis_ai_asset;expect(v.state).toBe("adopted");expect(v.review.asset).toEqual({document_id:"asset_saved",version:1,content_sha256:"a".repeat(64)});expect(v.review.rubric).toEqual({document_id:"rubric",version:3,content_sha256:"a".repeat(64)});fireEvent.change(screen.getByLabelText("资产内容"),{target:{value:"变更后需重审"}});expect(screen.getByRole("button",{name:"明确采用此评审版本"})).toBeDisabled();fireEvent.click(screen.getByRole("button",{name:"保存资产候选"}));await waitFor(()=>expect(writes).toHaveLength(2));expect(writes[1].body.editor_json.attrs.archeaxis_ai_asset.state).toBe("candidate");expect(writes[1].body.editor_json.attrs.archeaxis_ai_asset.review).toBeNull();
});


// Review outcomes are authored observations, never model or professional truth.
function reviewRubric(version=3):DocumentDto{return {...dto("rubric"),version,content_sha256:String(version).repeat(64),editor_json:{type:"doc",attrs:{archeaxis_machine_rubric:{schema:"archeaxis.machine-rubric/v1",request_id:`rubric_${version}`,title:"实际评审",purpose:"资产评审",criteria:[{criterion_id:"fit",label:"适用性",expectation:"限所评审的来源与版本"},{criterion_id:"conflict",label:"冲突",expectation:"记录实际比较依据"}],sources:[]}},content:[]}};}
function installReviewPicker(current=reviewRubric()){
 const state={rubric:current};
 bridge.call.mockImplementation(async(op,p)=>{
  if(op==="documents_list")return {documents:[{document_id:"rubric",title:"实际评审",version:state.rubric.version}],next_cursor:null,snapshot_count:1};
  if(op==="document_get"&&p.document_id==="rubric")return structuredClone(state.rubric);
  return original(op,p);
 });
 return state;
}
async function pickReview(){
 fireEvent.click(screen.getByRole("button",{name:"选择实际评审准则"}));
 fireEvent.click(screen.getByRole("button",{name:"读取文档对象"}));
 const option=await screen.findByRole("option",{name:/实际评审 · 列表 v/});
 fireEvent.change(screen.getByLabelText("选择文档"),{target:{value:(option as HTMLOptionElement).value}});
 fireEvent.click(await screen.findByRole("button",{name:"加入此对象版本"}));
 await screen.findByLabelText("评审人");
}
function fillReview(first:"failed"|"unmeasured"|"passed",second:"failed"|"unmeasured"|"passed"="passed"){
 fireEvent.change(screen.getByLabelText("评审人"),{target:{value:"独立审查者"}});
 fireEvent.change(screen.getByLabelText("评审依据"),{target:{value:"比较所选来源的固定版本"}});
 for(const [label,outcome] of [["适用性",first],["冲突",second]]){
  fireEvent.change(screen.getByLabelText(`判定 ${label}`),{target:{value:outcome}});
  fireEvent.change(screen.getByLabelText(`依据 ${label}`),{target:{value:`${label}：固定版本的独立观察`}});
 }
}
const savedMessage="资产版本已保存并读回；保存及采用均不授予 AI 资格。";
it.each(["failed","unmeasured","passed"] as const)("explicitly persists %s review as a candidate and retains snapshots on reopen",async(outcome)=>{
 installReviewPicker();render(<CanonicalAiAssetsSpace {...props}/>);await open();await pickReview();fillReview(outcome);
 fireEvent.click(screen.getByRole("button",{name:"保存人工评审（保留候选）"}));await screen.findByText(savedMessage);
 const stored=(docs.get("asset_saved")!.editor_json as J).attrs.archeaxis_ai_asset;
 expect(stored.state).toBe("candidate");expect(stored.review.outcome).toBe(outcome);
 expect(stored.review.asset).toEqual({document_id:"asset_saved",version:1,content_sha256:"a".repeat(64)});
 expect(stored.review.rubric).toEqual({document_id:"rubric",version:3,content_sha256:"3".repeat(64)});
 expect(stored.review.reviewer).toBe("独立审查者");expect(stored.review.judgments).toHaveLength(2);
 fireEvent.click(screen.getByRole("button",{name:"新建资产候选"}));
 fireEvent.click(await screen.findByRole("button",{name:"asset_saved · v2"}));
 await screen.findByRole("button",{name:"查看诊断详情：已保存资产评审"});
 expect(screen.getByRole("button",{name:"明确采用此评审版本"}))[outcome==="passed"?"toBeEnabled":"toBeDisabled"]();
 if(outcome==="passed"){
  fireEvent.click(screen.getByRole("button",{name:"明确采用此评审版本"}));
  await waitFor(()=>expect(writes).toHaveLength(2));await screen.findByText(savedMessage);
  expect(writes[1].body.editor_json.attrs.archeaxis_ai_asset.state).toBe("adopted");
  expect(writes[1].body.editor_json.attrs.archeaxis_ai_asset.review).toEqual(stored.review);
 }
});
it("does not silently discard a pending negative review through ordinary candidate saving",async()=>{
 installReviewPicker();render(<CanonicalAiAssetsSpace {...props}/>);await open();await pickReview();fillReview("failed");
 fireEvent.click(screen.getByRole("button",{name:"保存资产候选"}));
 await screen.findByText("人工评审尚未提交，请先保存人工评审或取消未提交评审。");
 expect(writes).toHaveLength(0);expect(screen.getByLabelText("评审人")).toHaveValue("独立审查者");
 expect(screen.getByLabelText("判定 适用性")).toHaveValue("failed");
 fireEvent.click(screen.getByRole("button",{name:"取消未提交评审"}));
 fireEvent.click(screen.getByRole("button",{name:"保存资产候选"}));await screen.findByText(savedMessage);
 expect(writes[0].body.editor_json.attrs.archeaxis_ai_asset.review).toBeNull();
});
it("aggregates failed before unmeasured and retains every per-criterion observation",async()=>{
 installReviewPicker();render(<CanonicalAiAssetsSpace {...props}/>);await open();await pickReview();fillReview("failed","unmeasured");
 fireEvent.click(screen.getByRole("button",{name:"保存人工评审（保留候选）"}));await screen.findByText(savedMessage);
 const review=writes[0].body.editor_json.attrs.archeaxis_ai_asset.review;
 expect(review.outcome).toBe("failed");expect(review.judgments.map((j:J)=>j.outcome)).toEqual(["failed","unmeasured"]);
});
it("replacing rubric snapshot starts an unmeasured review instead of copying old judgments",async()=>{
 const picker=installReviewPicker();render(<CanonicalAiAssetsSpace {...props}/>);await open();await pickReview();fillReview("passed");
 fireEvent.click(screen.getByRole("button",{name:"确认全部人工评审通过"}));
 fireEvent.click(screen.getByRole("button",{name:"取消未提交评审"}));picker.rubric=reviewRubric(4);
 await pickReview();expect(screen.getByLabelText("判定 适用性")).toHaveValue("unmeasured");
 expect(screen.getByRole("button",{name:"明确采用此评审版本"})).toBeDisabled();fillReview("unmeasured");
 fireEvent.click(screen.getByRole("button",{name:"保存人工评审（保留候选）"}));await screen.findByText(savedMessage);
 expect(writes[0].body.editor_json.attrs.archeaxis_ai_asset.review.rubric).toEqual({document_id:"rubric",version:4,content_sha256:"4".repeat(64)});
});
it("semantic asset edits invalidate a persisted passing review before any later adoption",async()=>{
 installReviewPicker();render(<CanonicalAiAssetsSpace {...props}/>);await open();await pickReview();fillReview("passed");
 fireEvent.click(screen.getByRole("button",{name:"保存人工评审（保留候选）"}));await screen.findByText(savedMessage);
 fireEvent.change(screen.getByLabelText("资产内容"),{target:{value:"不同适用版本的内容"}});
 expect(screen.getByRole("button",{name:"明确采用此评审版本"})).toBeDisabled();
 fireEvent.click(screen.getByRole("button",{name:"保存资产候选"}));await waitFor(()=>expect(writes).toHaveLength(2));await screen.findByText(savedMessage);
 expect(writes[1].body.editor_json.attrs.archeaxis_ai_asset.review).toBeNull();
 expect(writes[1].body.editor_json.attrs.archeaxis_ai_asset.state).toBe("candidate");
 expect(screen.getByRole("button",{name:"明确采用此评审版本"})).toBeDisabled();
});
it("retries a frozen negative review exactly after a lost ACK while preserving later asset draft",async()=>{
 installReviewPicker();const pickerBridge=bridge.call.getMockImplementation()!;let first=true;let ack:unknown;
 bridge.call.mockImplementation(async(op,p)=>{
  if(op==="document_draft"){
   if(first){first=false;ack=await original(op,p);throw new Error("lost review ACK");}
   writes.push(structuredClone(p));return structuredClone(ack);
  }
  return pickerBridge(op,p);
 });
 render(<CanonicalAiAssetsSpace {...props}/>);await open();await pickReview();fillReview("failed");
 fireEvent.click(screen.getByRole("button",{name:"保存人工评审（保留候选）"}));await screen.findByRole("alert");
 expect(screen.getByLabelText("评审人")).toHaveValue("独立审查者");
 expect(screen.getByLabelText("判定 适用性")).toBeDisabled();
 fireEvent.change(screen.getByLabelText("资产内容"),{target:{value:"冻结后继续编辑的候选"}});
 fireEvent.click(screen.getByRole("button",{name:"重试冻结资产请求"}));
 await screen.findByText("发送版本已确认；后续草稿仍保留。");
 expect(writes).toHaveLength(2);expect(writes[0]).toEqual(writes[1]);
 expect(writes[0].body.editor_json.attrs.archeaxis_ai_asset.review.outcome).toBe("failed");
 expect(screen.getByLabelText("资产内容")).toHaveValue("冻结后继续编辑的候选");
 expect(screen.getByRole("button",{name:"明确采用此评审版本"})).toBeDisabled();
});

it("reconciles a saved passing review after lost ACK, closes transient inputs and permits later adoption",async()=>{
 installReviewPicker();const pickerBridge=bridge.call.getMockImplementation()!;let first=true;
 bridge.call.mockImplementation(async(op,p)=>{const result=await pickerBridge(op,p);if(op==="document_draft"&&first){first=false;throw new Error("lost review ACK");}return result;});
 render(<CanonicalAiAssetsSpace {...props}/>);await open();await pickReview();fillReview("passed");
 fireEvent.click(screen.getByRole("button",{name:"保存人工评审（保留候选）"}));await screen.findByRole("alert");
 const persisted=(docs.get("asset_saved")!.editor_json as J).attrs.archeaxis_ai_asset.review;
 fireEvent.click(screen.getByRole("button",{name:"核对冻结资产请求"}));
 await screen.findByText("冻结请求已确认；后续草稿保留。");
 expect(screen.queryByLabelText("评审人")).not.toBeInTheDocument();
 expect(screen.queryByRole("button",{name:"核对冻结资产请求"})).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole("button",{name:"新建资产候选"}));
 await waitFor(()=>expect(screen.getByLabelText("资产内容")).toHaveValue(""));
 fireEvent.click(await screen.findByRole("button",{name:"asset_saved · v2"}));
 await screen.findByRole("button",{name:"查看诊断详情：已保存资产评审"});
 expect(screen.getByRole("button",{name:"明确采用此评审版本"})).toBeEnabled();
 fireEvent.click(screen.getByRole("button",{name:"明确采用此评审版本"}));
 await screen.findByText(savedMessage);expect(writes).toHaveLength(2);
 expect(writes[1].body.editor_json.attrs.archeaxis_ai_asset.state).toBe("adopted");
 expect(writes[1].body.editor_json.attrs.archeaxis_ai_asset.review).toEqual(persisted);
});
