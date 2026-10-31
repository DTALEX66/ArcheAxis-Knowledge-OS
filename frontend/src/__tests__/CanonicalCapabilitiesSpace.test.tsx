import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { basename, resolve } from "node:path";
import { CanonicalCapabilitiesSpace } from "../spaces/CanonicalCapabilitiesSpace";
import { CAPABILITY_CATALOG } from "../api/generated/capability-catalog";
import { scopedReadiness } from "../test/fixtures/readiness";
import { DiagnosticConsole } from "../components/DiagnosticConsole";
import { resetDiagnostics } from "../presentation/diagnostics";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const repository=basename(process.cwd()) === "frontend" ? resolve(process.cwd(),"..") : process.cwd();
describe("single-source capability exploration",()=>{
 beforeEach(()=>{bridge.call.mockReset();resetDiagnostics();});
 it("keeps internal directory identity and state in diagnostics while future capability limits remain visible",async()=>{
  const entry=CAPABILITY_CATALOG.entries.find(item=>item.atlas.capability_id==="CAP-0080")!;
  render(<><CanonicalCapabilitiesSpace onNavigate={vi.fn()} selectedCapabilityId={entry.atlas.capability_id}/><DiagnosticConsole/></>);
  const details=screen.getByRole("article",{name:"能力详情"});
  expect(details).not.toHaveTextContent(/CAP-0080|binding_long_term|not_implemented|UNKNOWN|Atlas\/implementation|config\/capability-map/);
  expect(details).toHaveTextContent("完整能力尚未接入");expect(screen.getByRole("button",{name:"当前执行入口尚未提供"})).toBeDisabled();
  await userEvent.setup().click(within(details).getByText("实现与来源详情"));
  await userEvent.setup().click(screen.getByRole("button",{name:/能力登记与运行声明/}));
  expect(JSON.parse(screen.getByLabelText("诊断控制台").querySelector("pre")!.textContent!)).toEqual({atlas:entry.atlas,implementation:entry.implementation});
  expect(bridge.call).not.toHaveBeenCalled();
 });
 it("covers exactly the existing Atlas/map and records the current source hashes",()=>{
  for(const source of CAPABILITY_CATALOG.sources){const bytes=readFileSync(resolve(repository,source.path));expect(createHash("sha256").update(bytes).digest("hex")).toBe(source.sha256);}
  const atlas=readFileSync(resolve(repository,"docs/truth/CAPABILITY_ATLAS_V2.yaml"),"utf8");const atlasIds=[...atlas.matchAll(/^  - capability_id: "([^"]+)"/gm)].map(match=>match[1]);
  const mapping=JSON.parse(readFileSync(resolve(repository,"config/capability-map.v1.json"),"utf8"));
  expect(CAPABILITY_CATALOG.entries.map(entry=>entry.atlas.capability_id)).toEqual(atlasIds);
  for(const entry of CAPABILITY_CATALOG.entries)expect(entry.implementation).toEqual(mapping.capabilities.find((item:{capability_id:string})=>item.capability_id===entry.atlas.capability_id));
 });
 it("keeps future formal details available while refusing an unimplemented execution",async()=>{
  bridge.call.mockResolvedValue({capabilities:[]});const navigate=vi.fn();render(<CanonicalCapabilitiesSpace onNavigate={navigate}/>);
  await userEvent.setup().click(screen.getByRole("button",{name:/空间记忆与沉浸学习/}));
  expect(screen.getByRole("article",{name:"能力详情"})).toHaveTextContent("完整能力尚未接入");expect(screen.getByRole("button",{name:"当前执行入口尚未提供"})).toBeDisabled();expect(screen.getByText(/供体映射未建立/)).toBeInTheDocument();expect(navigate).not.toHaveBeenCalled();
  expect(bridge.call).not.toHaveBeenCalled();
 });
 it("separates observed handshake/permissions from implementation declaration and routes only a real UI",async()=>{
  bridge.call.mockImplementation(async(_op:string,p:{body:{scope:string,operations:string[]}})=>{const snapshot=scopedReadiness(p.body);snapshot.operations.forEach(row=>{row.permission="DISABLED";row.reasons=["CAPABILITY_DISABLED"];});return snapshot;});const navigate=vi.fn();render(<><CanonicalCapabilitiesSpace onNavigate={navigate}/><DiagnosticConsole/></>);
  await userEvent.setup().click(screen.getByRole("button",{name:/AI 学习资产与受控调用/}));await screen.findByText(/已读取当前视图/);
  expect(screen.getByText(/连接\/权限/)).toHaveTextContent("已禁用");expect(screen.getByText(/连接\/权限/)).toHaveTextContent("状态未知");
  await userEvent.setup().click(screen.getByRole("button",{name:/能力运行详细信息/}));
  const observed=JSON.parse(screen.getByLabelText("诊断控制台").querySelector("pre")!.textContent!);
  expect(observed).toMatchObject({enabled:false,health:"UNKNOWN",qualification:"UNVERIFIED",reasons:["CAPABILITY_DISABLED"]});
  await userEvent.setup().click(screen.getByRole("button",{name:"打开当前产品入口"}));expect(navigate).toHaveBeenCalledWith("vault");
 });
 it("preserves the formal directory when current health is unavailable",async()=>{
  bridge.call.mockImplementation(async()=>{throw new Error("unavailable");});await act(async()=>{render(<CanonicalCapabilitiesSpace onNavigate={vi.fn()} selectedCapabilityId="CAP-0050"/>);});
  expect(screen.getByRole("status")).toHaveTextContent("显示未知");await userEvent.setup().click(screen.getByRole("tab",{name:"目录与搜索"}));expect(document.querySelectorAll("button[data-entry-id]")).toHaveLength(CAPABILITY_CATALOG.entries.length);
 });
 it("prioritizes purpose, truthful status and next action while retaining implementation evidence behind disclosure",async()=>{
  render(<CanonicalCapabilitiesSpace onNavigate={vi.fn()} selectedCapabilityId="CAP-0080"/>);
  const details=screen.getByRole("article",{name:"能力详情"});
  const summary=within(details).getByText("实现与来源详情"),disclosure=summary.closest("details")!;
  expect(disclosure).not.toHaveAttribute("open");
  expect(within(details).getByText(/^执行前提：/)).not.toBeVisible();
  expect(within(details).getByText(/^所需验收证据：/)).not.toBeVisible();
  expect(within(details).getByText(/供体映射未建立/)).not.toBeVisible();
  const next=within(details).getByText(/^下一步：/);
  expect(next).toBeVisible();
    expect(next).toHaveTextContent(/尚未|暂未|不能使用/);
    expect(next).not.toHaveTextContent(/合同|契约|入口映射|实施包|资格|回执/);
  expect(next.compareDocumentPosition(disclosure)&Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(within(details).getByText("完整能力尚未接入",{exact:false})).toBeVisible();
  expect(within(details).getByRole("button",{name:"当前执行入口尚未提供"})).toBeVisible();
  expect(within(details).getByRole("button",{name:"当前执行入口尚未提供"})).toBeDisabled();
  expect(within(details).getByRole("region",{name:"设计细项与独立证据"})).toBeVisible();
  await userEvent.setup().click(summary);
  expect(disclosure).toHaveAttribute("open");
  expect(within(details).getByText(/^执行前提：/)).toBeVisible();
  expect(within(details).getByText(/^所需验收证据：/)).toBeVisible();
  expect(within(details).getByText(/供体映射未建立/)).toBeVisible();
  expect(bridge.call).not.toHaveBeenCalled();
 });
});
