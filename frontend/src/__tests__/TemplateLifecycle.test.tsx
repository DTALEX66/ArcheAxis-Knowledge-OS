import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { CanonicalResourcesSpace } from "../spaces/CanonicalResourcesSpace";
import { collection, prepareTemplateCreate, type TemplateBinding } from "../templates/bindings";
import { changeTemplate, readTemplateState, type TemplateState } from "../templates/templateLifecycle";
import { TEMPLATES, type TemplateDefinition } from "../templates/disciplines";
import type { DocumentDto } from "../api/generated/core-contract";
const api=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:api.call}));
function definition(version:number){const fields:Record<string,string>=version===1?{目标:""}:{目标:"",反思:""};return {version,sha256:String(version).repeat(64),snapshot:{schema:"archeaxis.template-definition/v1",template_id:"T3" as const,version,name:"学习与实践",kind:"first-party-data-only" as const,fields,paragraphs:[`SYNTHETIC definition v${version}`]}};}
let state:TemplateState;
beforeEach(()=>{
  state={capability:"template.T3",enabled:true,installed:true,state_epoch:0,definition:definition(1),available_definitions:[definition(1),definition(2)]};
  api.call.mockReset();api.call.mockImplementation(async(operation:string,payload:Record<string,unknown>={})=>{
    if(operation==="capabilities_list")return {capabilities:[structuredClone(state)]};
    if(operation==="capability_template_read")return {capability:structuredClone(state)};
    if(operation==="documents_list")return {documents:[],next_cursor:null,snapshot_count:0};
    if(operation==="capability_template_change"){
      if(payload.expected_epoch!==state.state_epoch)throw new Error("409 stale");
      const action=String(payload.action);
      state={...state,state_epoch:state.state_epoch+1,definition:definition(Number(payload.version)),installed:action==="uninstall"?false:action==="install"?true:state.installed,enabled:action==="disable"||action==="uninstall"?false:action==="enable"||action==="install"?true:state.enabled};
      return {capability:structuredClone(state)};
    }
    throw new Error(`unexpected ${operation}`);
  });
});
describe("SYNTHETIC first-party T3 host lifecycle through finite native commands",()=>{
  it("existing resource center offers actual update, rollback, disable, enable, uninstall and reinstall controls",async()=>{
    render(<CanonicalResourcesSpace/>);
    fireEvent.click(await screen.findByRole("button",{name:"更新到模板 v2"}));
    await waitFor(()=>expect(state.definition.version).toBe(2));
    fireEvent.click(await screen.findByRole("button",{name:"回退到模板 v1"}));
    await waitFor(()=>expect(state.definition.version).toBe(1));
    fireEvent.click(await screen.findByRole("button",{name:"停用学习与实践模板"}));
    fireEvent.click(await screen.findByRole("button",{name:"启用学习与实践模板"}));
    fireEvent.click(await screen.findByRole("button",{name:"卸载学习与实践模板"}));
    fireEvent.click(await screen.findByRole("button",{name:"安装内置模板 v2"}));
    await screen.findByRole("button",{name:"回退到模板 v1"});
    const writes=api.call.mock.calls.filter(([op])=>op==="capability_template_change");
    expect(writes.map(([,body])=>body.expected_epoch)).toEqual([0,1,2,3,4,5]);
    expect(writes.map(([,body])=>body.action)).toEqual(["update","rollback","disable","enable","uninstall","install"]);
  });
  it("new T3 consumer uses backend selected definition and refuses disabled/uninstalled without document writes",async()=>{
    const first=await prepareTemplateCreate("T3","math","owned-v1");
    const binding=(first.editor.attrs!.archeaxis_template as TemplateBinding);
    expect(binding.definition).toEqual({...definition(1),application_epoch:0});
    expect(JSON.stringify(first.editor.content)).toContain("SYNTHETIC definition v1");
    await changeTemplate(state,"update",definition(2));
    const next=await prepareTemplateCreate("T3","math","owned-v2");
    expect((next.editor.attrs!.archeaxis_template as TemplateBinding).fields).toHaveProperty("反思","");
    state.enabled=false;
    await expect(prepareTemplateCreate("T3","math")).rejects.toThrow("停用或卸载");
    state.enabled=true;state.installed=false;
    await expect(prepareTemplateCreate("T3","math")).rejects.toThrow("停用或卸载");
    expect(api.call.mock.calls.some(([op])=>op==="document_create")).toBe(false);
    // T1/T2 do not acquire a new install prerequisite.
    await expect(prepareTemplateCreate("T1","math")).resolves.toBeDefined();
    await expect(prepareTemplateCreate("T2","math")).resolves.toBeDefined();
  });
  it("historical T3 collection survives removal from the current launcher",()=>{
    const templates=TEMPLATES as TemplateDefinition[];const index=templates.findIndex(t=>t.id==="T3"),[removed]=templates.splice(index,1);
    try {
      const document={document_id:"old-t3",editor_json:{type:"doc",attrs:{archeaxis_template:{schema:"archeaxis.template/v1",template_id:"T3",discipline_id:"math",fields:{},references:[],learning_item_key:null}}}} as unknown as DocumentDto;
      expect(collection([document],"math").members).toEqual([document]);
    } finally {templates.splice(index,0,removed);}
  });
  it("invalid readbacks and mismatched epoch are refused without automatic resend",async()=>{
    expect(()=>readTemplateState({...state,state_epoch:-1})).toThrow();
    api.call.mockResolvedValue({capability:{...state,state_epoch:0}});
    await expect(changeTemplate(state,"disable")).rejects.toThrow("未确认");
    expect(api.call).toHaveBeenCalledTimes(1);
  });
});
