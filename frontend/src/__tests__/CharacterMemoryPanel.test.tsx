import { StrictMode } from "react";
import { beforeEach, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CharacterMemoryPanel } from "../components/CharacterMemoryPanel";
import { memoryProfile, exportMemory } from "../api/characterMemory";
import type { CharacterProfile, CharacterMemoryWrite } from "../api/generated/core-contract";
const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
let stored:CharacterProfile;
function initial():CharacterProfile{return {schema:"archeaxis.character-memory/v1",workspace_id:"a".repeat(32),restore_epoch:"initial",revision:0,enabled:false,preferences:"",learning_goals:"",memories:[]};}
function apply(body:CharacterMemoryWrite){
 if(body.workspace_id!==stored.workspace_id||body.restore_epoch!==stored.restore_epoch||body.expected_revision!==stored.revision)throw new Error("CAS conflict");
 const forgotten:string[]=[];const c=body.command;
 if(c.operation==="profile"){stored.preferences=c.preferences;stored.learning_goals=c.learning_goals;}
 if(c.operation==="enable")stored.enabled=true;
 if(c.operation==="disable")stored.enabled=false;
 if(c.operation==="remember")stored.memories.push(structuredClone(c.memory));
 if(c.operation==="correct"){const i=stored.memories.findIndex(row=>row.id===c.memory.id);if(i<0)throw new Error("missing");stored.memories[i]=structuredClone(c.memory);}
 if(c.operation==="forget"){forgotten.push(c.id);stored.memories=stored.memories.filter(row=>row.id!==c.id);}
 if(c.operation==="forget_all"){forgotten.push(...stored.memories.map(row=>row.id));stored.memories=[];}
 stored.revision++;
 return {schema:"archeaxis.memory-write/v1",profile:structuredClone(stored),live_store_deleted:forgotten.length>0,forgotten_ids:forgotten,historical_chat_modified:false,backups_modified:false,secure_erasure:false};
}
async function normal(op:string,p:Record<string,unknown>={}){
 if(op==="character_memory_get")return structuredClone(stored);
 if(op==="character_memory_apply")return apply(p.body as CharacterMemoryWrite);
 if(op==="character_memory_export")return {schema:"archeaxis.memory-export/v1",profile:structuredClone(stored),contains_personal_memory:true,network_performed:false};
 throw new Error("not a memory port");
}
beforeEach(()=>{stored=initial();bridge.call.mockReset();bridge.call.mockImplementation(normal);});
async function ready(){await screen.findByText(/当前存储 v0/);}
async function remember(user:ReturnType<typeof userEvent.setup>,text="明确认可的偏好",source="人工确认来源"){
 await user.type(screen.getByRole("textbox",{name:"记忆内容"}),text);await user.type(screen.getByRole("textbox",{name:"记忆来源"}),source);await user.click(screen.getByRole("button",{name:"保存并核对这条记忆"}));await screen.findByText(/变更已保存并读回/);
}
it("SIMULATED initial read is disabled and never extracts chat, enables memory or calls a model",async()=>{
 render(<CharacterMemoryPanel/>);await ready();expect(screen.getByText(/记忆已停用/)).toBeInTheDocument();expect(bridge.call.mock.calls.map(call=>call[0])).toEqual(["character_memory_get"]);
});
it("SIMULATED saves profile, remembers, corrects and reopens the same persisted memory identity",async()=>{
 const user=userEvent.setup();const page=render(<CharacterMemoryPanel/>);await ready();await user.type(screen.getByRole("textbox",{name:"角色偏好"}),"逐步解释");await user.type(screen.getByRole("textbox",{name:"学习目标"}),"学习证据核对");await user.click(screen.getByRole("button",{name:"保存并核对档案"}));await screen.findByText(/变更已保存并读回/);expect(stored.revision).toBe(1);await remember(user);const id=stored.memories[0].id;expect(id).toMatch(/^memory_/);await user.click(screen.getByRole("button",{name:"纠正此条"}));await user.clear(screen.getByRole("textbox",{name:"记忆内容"}));await user.type(screen.getByRole("textbox",{name:"记忆内容"}),"纠正后的偏好");await user.click(screen.getByRole("button",{name:"保存并核对纠正"}));await screen.findByText(/当前存储 v3/);expect(stored.memories).toEqual([{id,text:"纠正后的偏好",provenance:"人工确认来源"}]);page.unmount();render(<CharacterMemoryPanel/>);await screen.findByText(/当前存储 v3/);expect(screen.getByRole("textbox",{name:"角色偏好"})).toHaveValue("逐步解释");expect(screen.getByRole("textbox",{name:"学习目标"})).toHaveValue("学习证据核对");expect(within(screen.getByRole("article",{name:`获准记忆 ${id}`})).getByText("纠正后的偏好")).toBeInTheDocument();expect(bridge.call.mock.calls.some(call=>["conversation_request","knowledge_review","document_create"].includes(call[0]))).toBe(false);
});
it("SIMULATED enabling and disabling memory each requires an explicit action and exact readback",async()=>{
 const user=userEvent.setup();render(<CharacterMemoryPanel/>);await ready();await user.click(screen.getByRole("button",{name:"明确启用陪伴记忆"}));await screen.findByText(/记忆已启用/);expect(stored.enabled).toBe(true);await user.click(screen.getByRole("button",{name:"停用陪伴记忆"}));await screen.findByText(/当前存储 v2.*记忆已停用/);expect(stored.enabled).toBe(false);expect(bridge.call.mock.calls.filter(c=>c[0]==="character_memory_apply").map(c=>(c[1].body as CharacterMemoryWrite).command.operation)).toEqual(["enable","disable"]);
});
it("SIMULATED forget cancellation writes nothing; confirmation removes actual store entry and preserves profile",async()=>{
 stored.preferences="保留偏好";stored.memories=[{id:"approved_one",text:"人工记忆",provenance:"本人确认"}];const user=userEvent.setup();render(<CharacterMemoryPanel/>);await ready();await user.click(screen.getByRole("button",{name:"审阅遗忘此条"}));await user.click(screen.getByRole("button",{name:"取消遗忘"}));expect(stored.memories).toHaveLength(1);expect(bridge.call).not.toHaveBeenCalledWith("character_memory_apply",expect.anything());await user.click(screen.getByRole("button",{name:"审阅遗忘此条"}));await user.click(screen.getByRole("button",{name:"确认遗忘"}));await screen.findByText(/遗忘已在当前记忆存储中读回/);expect(stored.memories).toEqual([]);expect(stored.preferences).toBe("保留偏好");expect(screen.queryByRole("article",{name:"获准记忆 approved_one"})).not.toBeInTheDocument();
});
it("SIMULATED forgetting all uses the bounded Core operation and verifies all deleted identities",async()=>{
 stored.memories=[{id:"first",text:"一",provenance:"人工"},{id:"second",text:"二",provenance:"人工"}];const user=userEvent.setup();render(<CharacterMemoryPanel/>);await ready();await user.click(screen.getByRole("button",{name:"审阅遗忘全部记忆"}));expect(bridge.call).not.toHaveBeenCalledWith("character_memory_apply",expect.anything());await user.click(screen.getByRole("button",{name:"确认遗忘"}));await screen.findByText(/遗忘已在当前记忆存储中读回/);expect(stored.memories).toEqual([]);expect((bridge.call.mock.calls.find(call=>call[0]==="character_memory_apply")![1].body as CharacterMemoryWrite).command).toEqual({operation:"forget_all"});
});
it.each(["identity","revision","text","unrelated","deletion"])("SIMULATED mismatched %s in an ACK never shows persisted success",async(field)=>{
 bridge.call.mockImplementation(async(op,p)=>{const value=await normal(op,p);if(op!=="character_memory_apply")return value;const wrong=structuredClone(value) as any;if(field==="identity")wrong.profile.workspace_id="b".repeat(32);if(field==="revision")wrong.profile.revision++;if(field==="text")wrong.profile.preferences="另一个值";if(field==="unrelated")wrong.profile.memories=[{id:"unexpected",text:"未经提交",provenance:"外来"}];if(field==="deletion")wrong.secure_erasure=true;return wrong;});const user=userEvent.setup();render(<CharacterMemoryPanel/>);await ready();await user.type(screen.getByRole("textbox",{name:"角色偏好"}),"保留我的输入");await user.click(screen.getByRole("button",{name:"保存并核对档案"}));await screen.findByText(/操作未确认/);expect(screen.queryByText(/变更已保存并读回/)).not.toBeInTheDocument();expect(screen.getByRole("textbox",{name:"角色偏好"})).toHaveValue("保留我的输入");expect(screen.getByRole("button",{name:"核对未确认变更"})).toBeInTheDocument();
});
it("SIMULATED ACK loss reconciles the exact stored state without repeating the write",async()=>{
 bridge.call.mockImplementation(async(op,p)=>{const value=await normal(op,p);if(op==="character_memory_apply")throw new Error("lost ACK");return value;});const user=userEvent.setup();render(<CharacterMemoryPanel/>);await ready();await user.type(screen.getByRole("textbox",{name:"角色偏好"}),"冻结偏好");await user.click(screen.getByRole("button",{name:"保存并核对档案"}));await screen.findByText(/操作未确认/);await user.click(screen.getByRole("button",{name:"核对未确认变更"}));await screen.findByText(/变更已保存并读回/);expect(bridge.call.mock.calls.filter(c=>c[0]==="character_memory_apply")).toHaveLength(1);expect(stored.preferences).toBe("冻结偏好");
});
it("SIMULATED CAS conflict preserves edits and only explicit adoption uses the freshly read revision",async()=>{
 const user=userEvent.setup();render(<CharacterMemoryPanel/>);await ready();await user.type(screen.getByRole("textbox",{name:"角色偏好"}),"本地编辑");stored.revision=7;stored.preferences="其他视图保存";await user.click(screen.getByRole("button",{name:"保存并核对档案"}));await screen.findByText(/操作未确认/);expect(stored.preferences).toBe("其他视图保存");await user.click(screen.getByRole("button",{name:"核对未确认变更"}));await screen.findByText(/当前存储与原提交不一致/);expect(screen.getByRole("textbox",{name:"角色偏好"})).toHaveValue("本地编辑");await user.click(screen.getByRole("button",{name:"采用当前版本并保留本地编辑"}));expect(bridge.call.mock.calls.filter(c=>c[0]==="character_memory_apply")).toHaveLength(1);await user.click(screen.getByRole("button",{name:"保存并核对档案"}));await screen.findByText(/当前存储 v8/);expect((bridge.call.mock.calls.filter(c=>c[0]==="character_memory_apply")[1][1].body as CharacterMemoryWrite).expected_revision).toBe(7);
});
it("SIMULATED failed reads never create an empty profile or enable writes",async()=>{
 bridge.call.mockRejectedValue(new Error("offline"));render(<CharacterMemoryPanel/>);await screen.findByText(/不自动重发或把失败当作空记忆/);expect(screen.queryByRole("button",{name:"明确启用陪伴记忆"})).not.toBeInTheDocument();expect(bridge.call.mock.calls.every(c=>c[0]==="character_memory_get")).toBe(true);
});
it("SIMULATED UTF8 byte and provenance limits retain input and reject it before writes",async()=>{
 render(<CharacterMemoryPanel/>);await ready();fireEvent.change(screen.getByRole("textbox",{name:"记忆内容"}),{target:{value:"中".repeat(1366)}});fireEvent.change(screen.getByRole("textbox",{name:"记忆来源"}),{target:{value:"来源"}});fireEvent.click(screen.getByRole("button",{name:"保存并核对这条记忆"}));await screen.findByText(/输入超出记忆允许范围/);expect(bridge.call).not.toHaveBeenCalledWith("character_memory_apply",expect.anything());expect(screen.getByRole("textbox",{name:"记忆内容"})).toHaveValue("中".repeat(1366));
});
it("SIMULATED refresh preserves an unsaved profile form",async()=>{
 const user=userEvent.setup();render(<CharacterMemoryPanel/>);await ready();await user.type(screen.getByRole("textbox",{name:"角色偏好"}),"未存文字");stored.preferences="实际存储";stored.revision=3;await user.click(screen.getByRole("button",{name:"读取当前档案与记忆"}));await screen.findByText(/当前存储 v3/);expect(screen.getByRole("textbox",{name:"角色偏好"})).toHaveValue("未存文字");expect(stored.preferences).toBe("实际存储");
});
it("SIMULATED StrictMode replay finishes reads without a stuck busy lock",async()=>{
 render(<StrictMode><CharacterMemoryPanel/></StrictMode>);await ready();await waitFor(()=>expect(screen.getByRole("button",{name:"明确启用陪伴记忆"})).toBeEnabled());expect(bridge.call.mock.calls.every(c=>c[0]==="character_memory_get")).toBe(true);
});
it("SIMULATED unmount during a write does not perform a new readback or repeat the mutation",async()=>{
 let resolve!:(value:unknown)=>void;bridge.call.mockImplementation((op,p)=>op==="character_memory_apply"?new Promise(r=>{resolve=r;}):normal(op,p));const user=userEvent.setup();const page=render(<CharacterMemoryPanel/>);await ready();await user.click(screen.getByRole("button",{name:"明确启用陪伴记忆"}));const body=bridge.call.mock.calls.find(call=>call[0]==="character_memory_apply")![1].body as CharacterMemoryWrite;page.unmount();await act(async()=>resolve(apply(body)));expect(bridge.call.mock.calls.filter(c=>c[0]==="character_memory_get")).toHaveLength(1);expect(bridge.call.mock.calls.filter(c=>c[0]==="character_memory_apply")).toHaveLength(1);
});
it("SIMULATED export returns the actual bounded personal profile with no network or deletion claim",async()=>{
 stored.memories=[{id:"exported",text:"明确获准",provenance:"本人"}];expect(await exportMemory()).toEqual({schema:"archeaxis.memory-export/v1",profile:stored,contains_personal_memory:true,network_performed:false});expect(bridge.call.mock.calls.map(c=>c[0])).toEqual(["character_memory_export"]);
});
it("SIMULATED malformed or duplicate profile memory cannot appear as a valid store",()=>{
 const row={id:"duplicated",text:"正文",provenance:"来源"};expect(()=>memoryProfile({...initial(),memories:[row,row]})).toThrow();expect(()=>memoryProfile({...initial(),memories:[{...row,text:"\0"}]})).toThrow();
});
it("SIMULATED later wrong readback retains an unconfirmed profile mutation",async()=>{
 let reads=0;bridge.call.mockImplementation(async(op,p)=>{const value=await normal(op,p);if(op==="character_memory_get"&&++reads>1)return {...value,revision:stored.revision+1};return value;});const user=userEvent.setup();render(<CharacterMemoryPanel/>);await ready();await user.type(screen.getByRole("textbox",{name:"角色偏好"}),"原提交");await user.click(screen.getByRole("button",{name:"保存并核对档案"}));await screen.findByText(/操作未确认/);expect(screen.queryByText(/变更已保存并读回/)).not.toBeInTheDocument();expect(screen.getByRole("textbox",{name:"角色偏好"})).toHaveValue("原提交");
});
it("SIMULATED changed workspace or restore epoch cannot be adopted for the frozen original write",async()=>{
 const user=userEvent.setup();render(<CharacterMemoryPanel/>);await ready();stored={...stored,workspace_id:"b".repeat(32),restore_epoch:"c".repeat(32)};await user.click(screen.getByRole("button",{name:"明确启用陪伴记忆"}));await screen.findByText(/操作未确认/);await user.click(screen.getByRole("button",{name:"核对未确认变更"}));await screen.findByText(/当前存储与原提交不一致/);await user.click(screen.getByRole("button",{name:"采用当前版本并保留本地编辑"}));await screen.findByText(/工作区或恢复身份已改变/);expect(screen.getByRole("button",{name:"明确启用陪伴记忆"})).toBeDisabled();expect(bridge.call.mock.calls.filter(c=>c[0]==="character_memory_apply")).toHaveLength(1);
});
it("SIMULATED Escape restores the reviewed memory trigger and never forgets",async()=>{
 stored.memories=[{id:"focus_fixture",text:"保留",provenance:"人工"}];const user=userEvent.setup();render(<CharacterMemoryPanel/>);await ready();const trigger=screen.getByRole("button",{name:"审阅遗忘此条"});await user.click(trigger);await screen.findByRole("alertdialog",{name:"确认遗忘获准记忆"});await user.keyboard("{Escape}");await waitFor(()=>expect(trigger).toHaveFocus());expect(bridge.call).not.toHaveBeenCalledWith("character_memory_apply",expect.anything());expect(stored.memories).toHaveLength(1);
});
