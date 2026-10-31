import {beforeEach,describe,expect,it,vi} from "vitest";
import {act,render,screen,within} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {BackupPanel} from "../components/BackupPanel";
import {DiagnosticConsole} from "../components/DiagnosticConsole";
import {resetDiagnostics} from "../presentation/diagnostics";
const bridge=vi.hoisted(()=>({call:vi.fn(),preview:vi.fn(),confirm:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
vi.mock("../api/workspaceRestore",()=>({previewWorkspaceRestore:bridge.preview,confirmWorkspaceRestore:bridge.confirm}));
const receipt={backup_id:"a".repeat(32),filename:`${"a".repeat(32)}.sqlite`,sha256:"b".repeat(64),bytes:4096,schema_version:"10",sqlite_version:"3.51.3",source_sha_list:[],verified:true};
describe("whole workspace recovery confirmation",()=>{
 beforeEach(()=>{vi.clearAllMocks();bridge.call.mockResolvedValue({backups:[receipt]});bridge.preview.mockResolvedValue({schema_version:"10",source_count:0});bridge.confirm.mockResolvedValue({});});
 it("explains replacement and authorization loss before confirmation while retaining the exact preview in diagnostics",async()=>{
  resetDiagnostics();const preview={schema_version:"10",source_count:0};bridge.preview.mockResolvedValue(preview);
  const view=render(<><BackupPanel/><DiagnosticConsole/></>);const user=userEvent.setup();
  await user.click(screen.getByRole("button",{name:"刷新备份列表"}));await user.click(screen.getByRole("button",{name:"检查此备份"}));
  const confirmation=screen.getByRole("group",{name:"确认恢复整个工作区"});
  expect(confirmation).toHaveTextContent("会替换整个工作区");expect(confirmation).toHaveTextContent("不是恢复单篇文档的旧版本");
  expect(confirmation).toHaveTextContent("当前资料和原件会先另行保留");expect(confirmation).toHaveTextContent("原 AI 使用授权将失效，需要重新明确授权");
  expect(view.container.textContent).not.toMatch(/Core|CAS|SQLite|SHA-256|schema_version/);expect(bridge.confirm).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button",{name:/备份详细信息/}));
  expect(JSON.parse(view.container.querySelector("pre")!.textContent!)).toEqual({backup:receipt,restore_preview:preview});expect(bridge.confirm).not.toHaveBeenCalled();
 });
 it("previews only selected identity; cancellation never restores",async()=>{render(<BackupPanel/>);const user=userEvent.setup();await user.click(screen.getByRole("button",{name:"刷新备份列表"}));await user.click(await screen.findByRole("button",{name:"检查此备份"}));expect(await screen.findByRole("button",{name:"确认恢复整个工作区"})).toBeInTheDocument();expect(bridge.preview).toHaveBeenCalledWith(receipt.backup_id,receipt.sha256);expect(bridge.confirm).not.toHaveBeenCalled();const started=vi.fn();window.addEventListener("workspace-restore-start",started);await user.click(screen.getByRole("button",{name:"取消恢复"}));expect(started).not.toHaveBeenCalled();window.removeEventListener("workspace-restore-start",started);expect(bridge.confirm).not.toHaveBeenCalled();expect(screen.getByRole("status")).toHaveTextContent("当前工作区未改变");});
 it("lists unavailable preserved backups beside valid backups without offering restore",async()=>{
  const invalid={backup_id:"c".repeat(32),filename:`${"c".repeat(32)}.sqlite`,code:"AAK-BACKUP-INVALID",message:"SIMULATED could not verify"};
  bridge.call.mockResolvedValue({backups:[receipt],unavailable_backups:[invalid]});render(<BackupPanel/>);const user=userEvent.setup();
  await user.click(screen.getByRole("button",{name:"刷新备份列表"}));
  const unavailable=screen.getByRole("region",{name:"无法核验的备份"});
  expect(unavailable).toHaveTextContent("有 1 份备份无法核验，已保留。");expect(within(unavailable).getByText(invalid.filename)).toBeInTheDocument();
  expect(within(unavailable).getByRole("button",{name:"此备份无法恢复"})).toBeDisabled();expect(screen.getByText(receipt.filename)).toBeInTheDocument();
  await user.click(screen.getByRole("button",{name:"检查此备份"}));expect(bridge.preview).toHaveBeenCalledOnce();expect(bridge.preview).toHaveBeenCalledWith(receipt.backup_id,receipt.sha256);
 });
 it("legacy list producers default unavailable backups to empty",async()=>{
  render(<BackupPanel/>);await userEvent.setup().click(screen.getByRole("button",{name:"刷新备份列表"}));
  expect(screen.getByText(receipt.filename)).toBeInTheDocument();expect(screen.queryByRole("region",{name:"无法核验的备份"})).not.toBeInTheDocument();
 });
 it("malformed unavailable metadata leaves the last valid list in place",async()=>{
  render(<BackupPanel/>);const user=userEvent.setup();await user.click(screen.getByRole("button",{name:"刷新备份列表"}));
  bridge.call.mockResolvedValue({backups:[],unavailable_backups:null});await user.click(screen.getByRole("button",{name:"刷新备份列表"}));
  expect(screen.getByText("备份列表读取失败，原列表仍保留。")).toBeInTheDocument();expect(screen.getByText(receipt.filename)).toBeInTheDocument();
 });
 it("a refreshed unavailable identity removes its old successful preview",async()=>{
  render(<BackupPanel/>);const user=userEvent.setup();await user.click(screen.getByRole("button",{name:"刷新备份列表"}));await user.click(screen.getByRole("button",{name:"检查此备份"}));
  expect(screen.getByRole("button",{name:"确认恢复整个工作区"})).toBeInTheDocument();
  bridge.call.mockResolvedValue({backups:[],unavailable_backups:[{backup_id:receipt.backup_id,filename:receipt.filename,code:"AAK-BACKUP-INVALID",message:"SIMULATED changed manifest"}]});
  await user.click(screen.getByRole("button",{name:"刷新备份列表"}));
  expect(screen.queryByRole("button",{name:"确认恢复整个工作区"})).not.toBeInTheDocument();expect(screen.getByRole("button",{name:"此备份无法恢复"})).toBeDisabled();expect(bridge.confirm).not.toHaveBeenCalled();
 });
 it("blocks workspace restore while a document draft is dirty",async()=>{render(<BackupPanel/>);const user=userEvent.setup();await user.click(screen.getByRole("button",{name:"刷新备份列表"}));await user.click(await screen.findByRole("button",{name:"检查此备份"}));await screen.findByRole("button",{name:"确认恢复整个工作区"});act(()=>window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:true})));expect(screen.getByRole("button",{name:"确认恢复整个工作区"})).toBeDisabled();expect(bridge.confirm).not.toHaveBeenCalled();act(()=>window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:false})));expect(screen.getByRole("button",{name:"确认恢复整个工作区"})).toBeEnabled();});
 it("emits start, restored and finish in order only after confirmed successful readback",async()=>{const events:string[]=[];const listener=(event:Event)=>events.push(event.type);for(const name of ["workspace-restore-start","archeaxis-workspace-restored","workspace-restore-finish"])window.addEventListener(name,listener);try{render(<BackupPanel/>);const user=userEvent.setup();await user.click(screen.getByRole("button",{name:"刷新备份列表"}));await user.click(await screen.findByRole("button",{name:"检查此备份"}));expect(events).toEqual([]);await user.click(await screen.findByRole("button",{name:"确认恢复整个工作区"}));await screen.findByText("整个工作区已恢复，并已重新打开确认。");expect(events).toEqual(["workspace-restore-start","archeaxis-workspace-restored","workspace-restore-finish"]);}finally{for(const name of ["workspace-restore-start","archeaxis-workspace-restored","workspace-restore-finish"])window.removeEventListener(name,listener);}});
 it("late mounted dirty protection uses parent snapshot without needing a new dirty event",async()=>{render(<BackupPanel hasUnsavedDrafts/>);const user=userEvent.setup();await user.click(screen.getByRole("button",{name:"刷新备份列表"}));await user.click(await screen.findByRole("button",{name:"检查此备份"}));expect(await screen.findByRole("button",{name:"确认恢复整个工作区"})).toBeDisabled();expect(bridge.confirm).not.toHaveBeenCalled();});
 it("named A remains protected from B save, close and malformed cleanup before workspace restore",async()=>{
  render(<BackupPanel/>);const user=userEvent.setup();
  await user.click(screen.getByRole("button",{name:"刷新备份列表"}));await user.click(await screen.findByRole("button",{name:"检查此备份"}));
  const restore=await screen.findByRole("button",{name:"确认恢复整个工作区"});
  const emit=(detail:unknown)=>act(()=>{window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail}));});
  emit({owner:"A",dirty:true});emit({owner:"B",dirty:true});emit({owner:"B",dirty:false});
  emit({owner:"B",dirty:false});emit({dirty:false});emit(false);
  expect(restore).toBeDisabled();await user.click(restore);expect(bridge.confirm).not.toHaveBeenCalled();
  emit({owner:"A",dirty:false});expect(restore).toBeEnabled();await user.click(restore);
  expect(bridge.confirm).toHaveBeenCalledWith(receipt.backup_id,receipt.sha256);
 });
 it("late-mounted parent snapshot cannot be cleared by another view's saved or close event",async()=>{
  const view=render(<BackupPanel hasUnsavedDrafts/>);const user=userEvent.setup();
  await user.click(screen.getByRole("button",{name:"刷新备份列表"}));await user.click(await screen.findByRole("button",{name:"检查此备份"}));
  const restore=await screen.findByRole("button",{name:"确认恢复整个工作区"});
  act(()=>{window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner:"B",dirty:false}}));});
  expect(restore).toBeDisabled();expect(bridge.confirm).not.toHaveBeenCalled();
  view.rerender(<BackupPanel hasUnsavedDrafts={false}/>);expect(restore).toBeEnabled();
 });
 it("invalidates uncertain confirmed attempts without emitting a success event",async()=>{bridge.confirm.mockRejectedValue(new Error("post-restore readback failed"));const invalidated=vi.fn();const restored=vi.fn();window.addEventListener("workspace-invalidated",invalidated);window.addEventListener("archeaxis-workspace-restored",restored);try{render(<BackupPanel/>);const user=userEvent.setup();await user.click(screen.getByRole("button",{name:"刷新备份列表"}));await user.click(await screen.findByRole("button",{name:"检查此备份"}));await user.click(await screen.findByRole("button",{name:"确认恢复整个工作区"}));await screen.findByText(/恢复结果暂未确认/);expect(invalidated).toHaveBeenCalledTimes(1);expect((invalidated.mock.calls[0][0] as CustomEvent).detail.confirmed).toBe(false);expect(restored).not.toHaveBeenCalled();}finally{window.removeEventListener("workspace-invalidated",invalidated);window.removeEventListener("archeaxis-workspace-restored",restored);}});
 it("refuses failed preflight without offering destructive confirmation",async()=>{bridge.preview.mockRejectedValue(new Error("bad CAS"));render(<BackupPanel/>);const user=userEvent.setup();await user.click(screen.getByRole("button",{name:"刷新备份列表"}));await user.click(await screen.findByRole("button",{name:"检查此备份"}));expect(await screen.findByText(/备份检查失败/)).toBeInTheDocument();expect(screen.queryByRole("button",{name:"确认恢复整个工作区"})).not.toBeInTheDocument();expect(bridge.confirm).not.toHaveBeenCalled();});
 it("confirms only selected backup and reports restart failure honestly",async()=>{bridge.confirm.mockRejectedValue(new Error("restart required"));render(<BackupPanel/>);const user=userEvent.setup();await user.click(screen.getByRole("button",{name:"刷新备份列表"}));await user.click(await screen.findByRole("button",{name:"检查此备份"}));await user.click(await screen.findByRole("button",{name:"确认恢复整个工作区"}));expect(bridge.confirm).toHaveBeenCalledWith(receipt.backup_id,receipt.sha256);expect(await screen.findByText(/恢复结果暂未确认/)).toBeInTheDocument();});
});
