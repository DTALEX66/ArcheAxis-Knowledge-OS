import {beforeEach,describe,expect,it,vi} from "vitest";
import {fireEvent,render,screen,waitFor} from "@testing-library/react";
import {OriginalTextCitation} from "../components/OriginalTextCitation";
import {utf8Sha256} from "../components/TranscriptionCues";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const revision="a".repeat(64),bytes=new TextEncoder().encode("\uFEFF甲\r\n😀乙");
describe("SIMULATED original text citations",()=>{
 beforeEach(()=>{bridge.call.mockReset();});
 it.each(["valid","source","range","checksum","resolve"])("%s preserves selected original byte identity",async mutation=>{
  bridge.call.mockImplementation(async(op:string,p:any)=>{
   if(op==="anchor_create")return {anchor_id:"anchor",source_id:mutation==="source"?"other":"source",source_revision:revision,location_status:"located",position:JSON.stringify({...JSON.parse(p.body.position),start:mutation==="range"?0:8,checksum:mutation==="checksum"?"wrong":p.body.checksum})};
   if(op==="anchor_resolve")return {anchor_id:"anchor",source_id:"source",source_revision:revision,current_source_revision:mutation==="resolve"?"other":revision,status:"CURRENT",scope:"locator_provenance_only"};
   throw new Error("unexpected write");
  });
  const adopted=vi.fn();render(<OriginalTextCitation sourceId="source" revision={revision} bytes={bytes} onAnchor={adopted}/>);
  expect(bridge.call).not.toHaveBeenCalled();expect(screen.getByRole("button",{name:"引用所选原文"})).toBeDisabled();
  const area=screen.getByRole("textbox",{name:"选择原件引用文字"}) as HTMLTextAreaElement;
  area.focus();area.setSelectionRange(3,5);fireEvent.keyUp(area,{key:"Shift"});
  expect(area.value).toBe("\uFEFF甲\n😀乙");expect(area.selectionStart).toBe(3);expect(area.selectionEnd).toBe(5);
  fireEvent.click(screen.getByRole("button",{name:"引用所选原文"}));
  await waitFor(()=>expect(bridge.call.mock.calls.some(([op])=>op==="anchor_create")).toBe(true));
  const submitted=bridge.call.mock.calls.find(([op])=>op==="anchor_create")![1];
  expect(JSON.parse(submitted.body.position)).toEqual({type:"text",start:8,end:12});expect(submitted.body.checksum).toBe(await utf8Sha256("😀"));
  if(mutation==="valid"){expect(await screen.findByRole("status")).toHaveTextContent("已引用并解析");expect(adopted).toHaveBeenCalledOnce();}
  else{expect(await screen.findByRole("status")).toHaveTextContent("未确认");expect(adopted).not.toHaveBeenCalled();}
  expect(bridge.call.mock.calls.every(([op])=>["anchor_create","anchor_resolve"].includes(op))).toBe(true);
 });
});
