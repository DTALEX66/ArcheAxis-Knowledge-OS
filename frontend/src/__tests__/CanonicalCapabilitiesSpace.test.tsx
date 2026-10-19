import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
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
 it("covers exactly the existing Atlas/map and records the current source hashes",()=>{
  for(const source of CAPABILITY_CATALOG.sources){const bytes=readFileSync(resolve(repository,source.path));expect(createHash("sha256").update(bytes).digest("hex")).toBe(source.sha256);}
  const atlas=readFileSync(resolve(repository,"docs/truth/CAPABILITY_ATLAS_V2.yaml"),"utf8");const atlasIds=[...atlas.matchAll(/^  - capability_id: "([^"]+)"/gm)].map(match=>match[1]);
  const mapping=JSON.parse(readFileSync(resolve(repository,"config/capability-map.v1.json"),"utf8"));
  expect(CAPABILITY_CATALOG.entries.map(entry=>entry.atlas.capability_id)).toEqual(atlasIds);
  for(const entry of CAPABILITY_CATALOG.entries)expect(entry.implementation).toEqual(mapping.capabilities.find((item:{capability_id:string})=>item.capability_id===entry.atlas.capability_id));
 });
 it("keeps future formal details available while refusing an unimplemented execution",async()=>{
  bridge.call.mockResolvedValue({capabilities:[]});const navigate=vi.fn();render(<CanonicalCapabilitiesSpace onNavigate={navigate}/>);
  await userEvent.setup().click(screen.getByRole("button",{name:/CAP-0080/}));
  expect(screen.getByRole("article",{name:"能力详情"})).toHaveTextContent("binding_long_term");expect(screen.getByRole("button",{name:"当前执行入口尚未提供"})).toBeDisabled();expect(screen.getByText(/供体映射未建立/)).toBeInTheDocument();expect(navigate).not.toHaveBeenCalled();
  expect(bridge.call).not.toHaveBeenCalled();
 });
 it("separates observed handshake/permissions from implementation declaration and routes only a real UI",async()=>{
  bridge.call.mockImplementation(async(_op:string,p:{body:{scope:string,operations:string[]}})=>{const snapshot=scopedReadiness(p.body);snapshot.operations.forEach(row=>{row.permission="DISABLED";row.reasons=["CAPABILITY_DISABLED"];});return snapshot;});const navigate=vi.fn();render(<><CanonicalCapabilitiesSpace onNavigate={navigate}/><DiagnosticConsole/></>);
  await userEvent.setup().click(screen.getByRole("button",{name:/CAP-0050/}));await screen.findByText(/已读取当前视图/);
  expect(screen.getByText(/连接\/权限/)).toHaveTextContent("已禁用");expect(screen.getByText(/连接\/权限/)).toHaveTextContent("UNKNOWN");
  await userEvent.setup().click(screen.getByRole("button",{name:/能力运行详细信息/}));
  const observed=JSON.parse(screen.getByLabelText("诊断控制台").querySelector("pre")!.textContent!);
  expect(observed).toMatchObject({enabled:false,health:"UNKNOWN",qualification:"UNVERIFIED",reasons:["CAPABILITY_DISABLED"]});
  await userEvent.setup().click(screen.getByRole("button",{name:"打开当前产品入口"}));expect(navigate).toHaveBeenCalledWith("vault");
 });
 it("preserves the formal directory when current health is unavailable",async()=>{
  bridge.call.mockImplementation(async()=>{throw new Error("unavailable");});await act(async()=>{render(<CanonicalCapabilitiesSpace onNavigate={vi.fn()} selectedCapabilityId="CAP-0050"/>);});
  expect(screen.getByRole("status")).toHaveTextContent("显示未知");await userEvent.setup().click(screen.getByRole("tab",{name:"目录与搜索"}));expect(document.querySelectorAll("button[data-entry-id]")).toHaveLength(CAPABILITY_CATALOG.entries.length);
 });
});
