import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { basename, resolve } from "node:path";
import { CanonicalCapabilitiesSpace } from "../spaces/CanonicalCapabilitiesSpace";
import { CAPABILITY_CATALOG } from "../api/generated/capability-catalog";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const repository=basename(process.cwd()) === "frontend" ? resolve(process.cwd(),"..") : process.cwd();
describe("single-source capability exploration",()=>{
 beforeEach(()=>{bridge.call.mockReset();});
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
  await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith("capabilities_list"));expect(bridge.call).toHaveBeenCalledTimes(1);
 });
 it("separates observed handshake/permissions from implementation declaration and routes only a real UI",async()=>{
  bridge.call.mockResolvedValue({capabilities:[{capability:"machine.answer",health:"handshake_ready",enabled:false}]});const navigate=vi.fn();render(<CanonicalCapabilitiesSpace onNavigate={navigate}/>);
  await screen.findByText(/已读取当前 Core worker 握手/);await userEvent.setup().click(screen.getByRole("button",{name:/CAP-0050/}));
  expect(screen.getByText(/连接\/权限/)).toHaveTextContent("已禁用");expect(screen.getByText(/连接\/权限/)).toHaveTextContent("handshake_ready");
  expect(screen.getByText(/实际引擎身份/)).toBeInTheDocument();await userEvent.setup().click(screen.getByRole("button",{name:"打开当前产品入口"}));expect(navigate).toHaveBeenCalledWith("vault");
 });
 it("preserves the formal directory when current health is unavailable",async()=>{
  bridge.call.mockImplementation(async()=>{throw new Error("unavailable");});await act(async()=>{render(<CanonicalCapabilitiesSpace onNavigate={vi.fn()}/>);});
  expect(screen.getByRole("status")).toHaveTextContent("显示未知");expect(document.querySelectorAll("button[data-entry-id]")).toHaveLength(CAPABILITY_CATALOG.entries.length);
 });
});
