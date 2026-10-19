import {beforeEach,afterEach,it,expect,vi} from "vitest";
import {render,screen,waitFor} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {ModelConfigurationPanel} from "../components/ModelConfigurationPanel";
import {MachineAnswerPanel} from "../components/MachineAnswerPanel";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const profile={endpoint:"http://127.0.0.1:1234/v1",protocol:"openai",model:"configured",credential_ref:null,max_tokens:512,timeout_s:20};
const configuration={schema:"archeaxis.model-configuration/v1",workspace_id:"a".repeat(32),restore_epoch:"initial",revision:3,profiles:{local:profile},bindings:[{purpose:"answer",lane:"deep",profile_id:"local"}]};
beforeEach(()=>{bridge.call.mockReset();});
afterEach(()=>vi.unstubAllGlobals());

it("generates a two-model draft from live inventory and saves eight missing lanes through the original CAS",async()=>{
 const initial={...configuration,revision:0,profiles:{},bindings:[]};
 bridge.call.mockImplementation(async(op:string,p:any)=>op==="model_configuration_get"?initial:{...p.body.configuration,revision:1});
 const fetcher=vi.fn().mockResolvedValue({ok:true,json:async()=>({data:[{id:"qwen3.5-4b"},{id:"aaos-deep-27b-mtp"}]})});vi.stubGlobal("fetch",fetcher);
 const user=userEvent.setup();render(<ModelConfigurationPanel/>);await user.click(screen.getByText("读取模型配置"));await user.click(screen.getByText("补齐 LM Studio FAST/DEEP 配置"));await screen.findByText(/已补齐缺失/);
 expect(bridge.call.mock.calls.some(c=>c[0]==="model_configuration_put")).toBe(false);
 expect(fetcher).toHaveBeenCalledTimes(1);expect(fetcher.mock.calls[0][0]).toBe("http://127.0.0.1:1234/v1/models");
 expect(screen.getByLabelText("companion / DEEP")).toHaveValue("lmstudio-deep");expect(screen.getByLabelText("embedding / FAST")).toHaveValue("");
 await user.click(screen.getByText("保存配置与用途绑定"));await screen.findByText(/已保存版本 1/);
 const saved=bridge.call.mock.calls.find(c=>c[0]==="model_configuration_put")![1].body;
 expect(saved.expected_revision).toBe(0);expect(saved.configuration.bindings).toHaveLength(8);expect(Object.keys(saved.configuration.profiles)).toHaveLength(2);
 expect(saved.configuration.profiles["lmstudio-deep"].model).toBe("aaos-deep-27b-mtp");
});

it("keeps edited custom profiles, existing bindings and embedding identity while filling missing lanes",async()=>{
 const initial={...configuration,profiles:{...configuration.profiles,index:{...profile,model:"embedding-model"}},bindings:[...configuration.bindings,{purpose:"embedding",lane:"fast",profile_id:"index"}]};
 bridge.call.mockImplementation(async(op:string,p:any)=>op==="model_configuration_get"?initial:{...p.body.configuration,revision:4});
 vi.stubGlobal("fetch",vi.fn().mockResolvedValue({ok:true,json:async()=>({data:[{id:"qwen3.5-4b"},{id:"aaos-deep-27b-mtp"}]})}));
 const user=userEvent.setup();render(<ModelConfigurationPanel/>);await user.click(screen.getByText("读取模型配置"));await user.clear(screen.getByLabelText("模型名称"));await user.type(screen.getByLabelText("模型名称"),"custom-edited");
 await user.click(screen.getByText("补齐 LM Studio FAST/DEEP 配置"));await screen.findByText(/已补齐缺失/);
 expect(screen.getByLabelText("answer / DEEP")).toHaveValue("local");expect(screen.getByLabelText("embedding / FAST")).toHaveValue("index");
 await user.selectOptions(screen.getByLabelText("选择配置"),"local");expect(screen.getByLabelText("模型名称")).toHaveValue("custom-edited");
 await user.click(screen.getByText("保存配置与用途绑定"));await screen.findByText(/已保存版本 4/);
 const saved=bridge.call.mock.calls.find(c=>c[0]==="model_configuration_put")![1].body.configuration;
 expect(saved.profiles.local.model).toBe("custom-edited");expect(saved.profiles.index).toEqual(initial.profiles.index);expect(saved.bindings).toEqual(expect.arrayContaining(initial.bindings));
});

it("rejects a missing MTP destination without partial draft changes and keeps a CAS-rejected draft",async()=>{
 bridge.call.mockImplementation(async(op:string)=>{if(op==="model_configuration_get")return configuration;throw Error("SYNTHETIC CAS conflict");});
 const fetcher=vi.fn().mockResolvedValueOnce({ok:true,json:async()=>({data:[{id:"qwen3.5-4b"},{id:"qwen3.8-27b"}]})}).mockResolvedValue({ok:true,json:async()=>({data:[{id:"qwen3.5-4b"},{id:"aaos-deep-27b-mtp"}]})});vi.stubGlobal("fetch",fetcher);
 const user=userEvent.setup();render(<ModelConfigurationPanel/>);await user.click(screen.getByText("读取模型配置"));await user.click(screen.getByText("补齐 LM Studio FAST/DEEP 配置"));await screen.findByText(/请先加载相应模型/);
 expect(screen.getByLabelText("material / FAST")).toHaveValue("");expect(screen.getByLabelText("模型名称")).toHaveValue("configured");
 await user.click(screen.getByText("补齐 LM Studio FAST/DEEP 配置"));await screen.findByText(/已补齐缺失/);await user.click(screen.getByText("保存配置与用途绑定"));await screen.findByText(/保存被拒绝/);
 expect(screen.getByLabelText("material / DEEP")).toHaveValue("lmstudio-deep");expect(bridge.call.mock.calls.find(c=>c[0]==="model_configuration_put")![1].body.expected_revision).toBe(3);
});
it("switches to existing names without overwriting them and preserves incomplete edits across profile switches",async()=>{
 const initial={...configuration,profiles:{...configuration.profiles,other:{...profile,model:"other-model"}}};
 bridge.call.mockImplementation(async(op:string,p:any)=>op==="model_configuration_get"?initial:{...p.body.configuration,revision:4});
 const user=userEvent.setup();render(<ModelConfigurationPanel/>);await user.click(screen.getByText("读取模型配置"));
 await user.clear(screen.getByLabelText("本地服务地址"));await user.type(screen.getByLabelText("本地服务地址"),"http://127.0.0.1:4321/v1");await user.clear(screen.getByLabelText("模型名称"));
 await user.selectOptions(screen.getByLabelText("选择配置"),"other");expect(screen.getByLabelText("模型名称")).toHaveValue("other-model");
 await user.selectOptions(screen.getByLabelText("选择配置"),"local");expect(screen.getByLabelText("模型名称")).toHaveValue("");expect(screen.getByLabelText("本地服务地址")).toHaveValue("http://127.0.0.1:4321/v1");
 await user.type(screen.getByLabelText("模型名称"),"edited-local");await user.clear(screen.getByLabelText("配置名称"));await user.type(screen.getByLabelText("配置名称"),"other");
 expect(screen.getByLabelText("模型名称")).toHaveValue("other-model");await user.click(screen.getByText("保存配置与用途绑定"));await screen.findByText(/已保存版本 4/);
 const saved=bridge.call.mock.calls.find(c=>c[0]==="model_configuration_put")![1].body.configuration;
 expect(saved.profiles.other).toEqual(initial.profiles.other);expect(saved.profiles.local.model).toBe("edited-local");
});
it("aborts an outstanding preset directory request when its presentation closes",async()=>{
 let signal:AbortSignal|undefined;
 bridge.call.mockResolvedValue(configuration);vi.stubGlobal("fetch",vi.fn((_url,options)=>{signal=options.signal;return new Promise((_resolve,reject)=>signal!.addEventListener("abort",()=>reject(Error("aborted"))));}));
 const user=userEvent.setup();const view=render(<ModelConfigurationPanel/>);await user.click(screen.getByText("读取模型配置"));await user.click(screen.getByText("补齐 LM Studio FAST/DEEP 配置"));
 expect(signal?.aborted).toBe(false);view.unmount();expect(signal?.aborted).toBe(true);expect(bridge.call.mock.calls.some(c=>c[0]==="model_configuration_put")).toBe(false);
});
it.each(["constructor","toString","__proto__"])("treats new profile name %s as an own draft without prototype lookup",async name=>{
 bridge.call.mockImplementation(async(op:string,p:any)=>op==="model_configuration_get"?configuration:{...p.body.configuration,revision:4});
 const user=userEvent.setup();render(<ModelConfigurationPanel/>);await user.click(screen.getByText("读取模型配置"));await user.clear(screen.getByLabelText("配置名称"));await user.type(screen.getByLabelText("配置名称"),name);
 expect(screen.getByLabelText("模型名称")).toHaveValue("");await user.type(screen.getByLabelText("模型名称"),"new-model");await user.click(screen.getByText("保存配置与用途绑定"));await screen.findByText(/已保存版本 4/);
 const profiles=bridge.call.mock.calls.find(c=>c[0]==="model_configuration_put")![1].body.configuration.profiles;
 expect(Object.hasOwn(profiles,name)).toBe(true);expect(profiles[name].model).toBe("new-model");expect(profiles.local).toEqual(profile);
});
it("blocks a DEEP machine answer before first configuration without invoking inference",async()=>{
 bridge.call.mockResolvedValue({...configuration,revision:0,profiles:{},bindings:[]});const user=userEvent.setup();render(<MachineAnswerPanel knowledgeId="k1"/>);
 await user.selectOptions(screen.getByLabelText("用途执行通道"),"deep");await user.type(screen.getByLabelText("实际问题"),"question");await user.click(screen.getByText("执行本地机器回答"));await screen.findByText(/回答用途配置未绑定/);
 expect(bridge.call.mock.calls.some(c=>c[0]==="machine_answer")).toBe(false);
});
it("SIMULATED edits one profile and writes fenced CAS plus purpose/lane bindings",async()=>{bridge.call.mockImplementation(async(op:string,p:any)=>op==="model_configuration_get"?configuration:{...p.body.configuration,revision:4});render(<ModelConfigurationPanel/>);const user=userEvent.setup();await user.click(screen.getByText("读取模型配置"));await user.clear(await screen.findByLabelText("模型名称"));await user.type(screen.getByLabelText("模型名称"),"updated");await user.selectOptions(screen.getByLabelText("retest / FAST"),"local");await user.click(screen.getByText("保存配置与用途绑定"));await screen.findByText(/已保存版本 4/);const write=bridge.call.mock.calls.find(c=>c[0]==="model_configuration_put")![1].body;expect(write.expected_revision).toBe(3);expect(write.configuration.workspace_id).toBe(configuration.workspace_id);expect(write.configuration.restore_epoch).toBe("initial");expect(write.configuration.profiles.local.model).toBe("updated");expect(write.configuration.bindings).toContainEqual({purpose:"retest",lane:"fast",profile_id:"local"});});
it("SIMULATED resolves DEEP once and freezes effective destination and budgets before answer",async()=>{bridge.call.mockImplementation(async(op:string,p:any)=>{if(op==="model_configuration_get")return configuration;if(op==="model_configuration_resolve")return {schema:"archeaxis.resolved-model/v1",workspace_id:configuration.workspace_id,restore_epoch:"initial",configuration_revision:3,configuration_sha256:"b".repeat(64),purpose:p.body.purpose,lane:p.body.lane,profile_id:"local",profile};throw new Error("SIMULATED lost ack");});render(<MachineAnswerPanel knowledgeId="k1"/>);const user=userEvent.setup();await user.selectOptions(screen.getByLabelText("用途执行通道"),"deep");await user.type(screen.getByLabelText("实际问题"),"question");await user.click(screen.getByText("执行本地机器回答"));await waitFor(()=>expect(bridge.call.mock.calls.some(c=>c[0]==="machine_answer")).toBe(true));const body=bridge.call.mock.calls.find(c=>c[0]==="machine_answer")![1].body;expect(body.model_configuration.lane).toBe("deep");expect(body.model_configuration.profile.endpoint).toBe(profile.endpoint);expect(body.model).toBe("configured");expect(body.max_tokens).toBe(512);expect(body.timeout_s).toBe(20);expect(bridge.call.mock.calls.filter(c=>c[0]==="model_configuration_resolve")).toHaveLength(1);});
it("SIMULATED missing binding blocks inference without ambient fallback",async()=>{bridge.call.mockImplementation(async(op:string)=>{if(op==="model_configuration_get")return configuration;throw new Error("unbound");});render(<MachineAnswerPanel knowledgeId="k1"/>);const user=userEvent.setup();await user.type(screen.getByLabelText("实际问题"),"question");await user.click(screen.getByText("执行本地机器回答"));await screen.findByText(/回答用途配置未绑定/);expect(bridge.call.mock.calls.some(c=>c[0]==="machine_answer")).toBe(false);});
