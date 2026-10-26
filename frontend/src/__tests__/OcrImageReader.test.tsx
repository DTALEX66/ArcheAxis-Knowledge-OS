import {createHash,webcrypto} from "node:crypto";
import {beforeEach,expect,it,vi} from "vitest";
import {act,fireEvent,render,screen,waitFor} from "@testing-library/react";
import {OcrImageReader} from "../components/OcrImageReader";
import {outputReceipt} from "./fixtures/jobContentCoreFixture";
import type {AnchorDto} from "../api/generated/core-contract";

const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const hash=(s:string)=>createHash("sha256").update(s).digest("hex");
const revision=hash("authored image bytes"),text="甲🙂乙\r\n次行",quote="甲🙂乙\r\n";
const structure=JSON.stringify([{kind:"line",path:["line-1"],char_start:0,char_end:5}]);
const loss=JSON.stringify({params:{input_sha256:revision,regions:[{text:"甲🙂乙",char_start:0,char_end:3,bbox:{x:10,y:20,w:60,h:10}}]}});
const position={type:"ocr_line",job_id:"pinned-old-job",attempt:1,kind:"line",path:["line-1"],char_start:0,char_end:5,checksum:hash(quote),result_sha256:hash(structure),loss_sha256:hash(loss)};
const anchor:AnchorDto={anchor_id:"anchor",source_id:"source",source_revision:revision,position:JSON.stringify(position),checksum:hash(quote),location_status:"located"};
const original={source_id:"source",name:"scan.png",media_type:"image/png",sha256:revision,content_base64:Buffer.from("authored image bytes").toString("base64")};
function resolution(a=anchor){return {anchor_id:a.anchor_id,source_id:a.source_id,source_revision:a.source_revision,current_source_revision:a.source_revision,position:a.position,status:"CURRENT",scope:"locator_provenance_only"};}
function view(a=anchor){return <OcrImageReader sourceId="source" revision={revision} name="scan.png" original={original} anchors={[a]}/>;}
function loaded(){const img=screen.getByRole("img");Object.defineProperties(img,{naturalWidth:{value:200,configurable:true},naturalHeight:{value:100,configurable:true}});fireEvent.load(img);}
beforeEach(()=>{
  vi.stubGlobal("crypto",webcrypto);bridge.call.mockReset();
  bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>)=>{
    if(op==="anchor_resolve")return resolution();
    if(op==="jobs_get")return {job_id:"pinned-old-job",input_ref:"source",state:"succeeded",attempt:1,request_id:"original-request"};
    if(op==="job_output")return outputReceipt(p.kind,p.kind==="text"?text:p.kind==="document_structure"?structure:loss);
    throw new Error(`Unexpected ${op}`);
  });
});

it("SYNTHETIC: displays the pinned Unicode quote and original-image region without running OCR or substituting the latest job",async()=>{
  const {container}=render(view());loaded();
  const button=screen.getByRole("button",{name:"查看第 1 条识别引用"});button.focus();fireEvent.click(button);
  expect(await screen.findByLabelText("定位识别原文")).toHaveTextContent("甲🙂乙");
  const rect=container.querySelector("svg rect")!;expect(rect).toHaveAttribute("x","10");expect(rect).toHaveAttribute("width","60");
  await waitFor(()=>expect(screen.getByLabelText("识别位置原图")).toHaveFocus());
  expect(bridge.call).toHaveBeenCalledWith("jobs_get",{job_id:"pinned-old-job"});
  expect(bridge.call.mock.calls.every(([op])=>["anchor_resolve","jobs_get","job_output"].includes(op))).toBe(true);
});

it.each(["resolution","artifact","checksum","attempt"])("SYNTHETIC: refuses changed %s and draws no area",async kind=>{
  const previous=bridge.call.getMockImplementation()!;
  let chosen=anchor;
  if(kind==="checksum")chosen={...anchor,checksum:hash("other"),position:JSON.stringify({...position,checksum:hash("other")})};
  bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>)=>{
    const value=await previous(op,p);
    if(op==="anchor_resolve")return {...resolution(chosen),...(kind==="resolution"?{status:"STALE"}:{})};
    if(kind==="artifact"&&op==="job_output"&&p.kind==="text")return {...value,content:"tampered"};
    if(kind==="attempt"&&op==="jobs_get")return {...value,attempt:2};
    return value;
  });
  const {container}=render(view(chosen));loaded();fireEvent.click(screen.getByRole("button",{name:"查看第 1 条识别引用"}));
  expect(await screen.findByRole("alert")).toHaveTextContent("未自动迁移引用");
  expect(container.querySelector("svg")).toBeNull();expect(screen.queryByLabelText("定位识别原文")).toBeNull();
  if(kind==="resolution")expect(bridge.call.mock.calls).toHaveLength(1);
});

it("SYNTHETIC: refuses boxes outside the decoded original",async()=>{
  const {container}=render(view());const img=screen.getByRole("img");Object.defineProperties(img,{naturalWidth:{value:20},naturalHeight:{value:10}});fireEvent.load(img);
  fireEvent.click(screen.getByRole("button",{name:"查看第 1 条识别引用"}));
  expect(await screen.findByRole("alert")).toHaveTextContent("超出当前原图");expect(container.querySelector("svg")).toBeNull();
});

it("SYNTHETIC: a locator invalidated during output reads cannot display the old result",async()=>{
  const previous=bridge.call.getMockImplementation()!;let resolutions=0;
  bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>)=>op==="anchor_resolve"&&++resolutions>1?{...resolution(),status:"UNVERIFIED"}:previous(op,p));
  const {container}=render(view());loaded();fireEvent.click(screen.getByRole("button",{name:"查看第 1 条识别引用"}));
  expect(await screen.findByRole("alert")).toHaveTextContent("读取期间引用定位发生变化");expect(container.querySelector("svg")).toBeNull();
});

it("SYNTHETIC: a late lookup cannot replace a newly selected original",async()=>{
  let done!:(value:unknown)=>void;bridge.call.mockImplementation(()=>new Promise(resolve=>{done=resolve;}));
  const host=render(view());loaded();fireEvent.click(screen.getByRole("button",{name:"查看第 1 条识别引用"}));
  host.rerender(<OcrImageReader sourceId="other" revision={revision} name="other.png" original={{...original,source_id:"other"}} anchors={[]}/>);
  await act(async()=>done(resolution()));
  await waitFor(()=>expect(screen.getByRole("img",{name:"原件 other.png"})).toBeVisible());
  expect(screen.queryByLabelText("定位识别原文")).toBeNull();expect(bridge.call.mock.calls).toHaveLength(1);
});

it("SYNTHETIC: completing a reference read does not steal focus from another input",async()=>{
  const previous=bridge.call.getMockImplementation()!;let done!:(value:unknown)=>void,first=true;
  bridge.call.mockImplementation((op:string,p:Record<string,unknown>)=>{
    if(op==="anchor_resolve"&&first){first=false;return new Promise(resolve=>{done=resolve;});}
    return previous(op,p);
  });
  render(<>{view()}<input aria-label="独立草稿"/></>);loaded();
  const button=screen.getByRole("button",{name:"查看第 1 条识别引用"});button.focus();fireEvent.click(button);
  const other=screen.getByLabelText("独立草稿");other.focus();
  await act(async()=>done(resolution()));
  await screen.findByLabelText("定位识别原文");expect(other).toHaveFocus();
});

it("SYNTHETIC: an existing reference jump reads its exact anchor without creating a new one",async()=>{
  render(<OcrImageReader sourceId="source" revision={revision} name="scan.png" original={original} anchors={[anchor]} seek={{sourceId:"source",revision,anchorId:anchor.anchor_id,position:anchor.position,sequence:1}}/>);loaded();
  expect(await screen.findByLabelText("定位识别原文")).toHaveTextContent("甲🙂乙");
  expect(bridge.call.mock.calls.every(([op])=>["anchor_resolve","jobs_get","job_output"].includes(op))).toBe(true);
});
