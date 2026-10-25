import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CanonicalCapabilitiesSpace } from "../spaces/CanonicalCapabilitiesSpace";
import { scopedReadiness } from "../test/fixtures/readiness";
import { readScopedReadiness } from "../api/scopedReadiness";
import { UI_CAPABILITY_INTENT } from "../presentation/uiCapabilityIntent";
import { capabilityDetailText } from "../presentation/capabilityCenter";
const bridge = vi.hoisted(() => ({call: vi.fn()}));
vi.mock("../api/core", () => ({coreCommand: bridge.call}));
describe("capability center uses existing identities without inventing runtime availability", () => {
  beforeEach(() => { bridge.call.mockReset(); bridge.call.mockImplementation(async (_: string, p: any) => scopedReadiness(p.body)); });
  it("filters the existing catalog, keeps future details and never installs or probes during browsing", async () => {
    render(<CanonicalCapabilitiesSpace onNavigate={vi.fn()}/>); const user = userEvent.setup();
    expect(document.querySelectorAll("button[data-entry-id]")).toHaveLength(16);
    await user.click(screen.getByRole("button", {name:"内置能力"}));
    expect(document.querySelectorAll("button[data-entry-id]")).toHaveLength(9);
    await user.click(screen.getByRole("button", {name:"扩展能力"}));
    expect(document.querySelectorAll("button[data-entry-id]")).toHaveLength(1);
    expect(screen.getByRole("button", {name:/LER 视觉教学与课件/})).toHaveTextContent("可选适配器");
    await user.click(screen.getByRole("button", {name:"未来规划"}));
    expect(document.querySelectorAll("button[data-entry-id]")).toHaveLength(6);
    await user.type(screen.getByLabelText("查找能力"), "CAP-0080");
    expect(document.querySelectorAll("button[data-entry-id]")).toHaveLength(1);
    await user.click(screen.getByRole("button", {name:/空间记忆与沉浸学习/}));
    await waitFor(()=>expect(screen.getByRole("heading",{name:"空间记忆与沉浸学习"})).toHaveFocus());
    expect(screen.getByRole("button", {name:"当前执行入口尚未提供"})).toBeDisabled();
    expect(bridge.call).not.toHaveBeenCalled();
  });
  it("shows the complete 16-family / 186-item authored blueprint without promoting unknown child evidence", async () => {
    render(<CanonicalCapabilitiesSpace onNavigate={vi.fn()}/>); const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "全部设计细项" }));
    expect(document.querySelectorAll("button[data-entry-id]")).toHaveLength(16);
    const previews = [...document.querySelectorAll(".capability-design-preview")];
    expect(previews).toHaveLength(16);
    expect(previews.flatMap(preview => [...preview.querySelectorAll("li")])).toHaveLength(186);
    for (const [id, items] of Object.entries(UI_CAPABILITY_INTENT)) {
      const card = document.querySelector(`button[data-entry-id="${id}"]`)!.closest("li")!;
      expect([...card.querySelectorAll(".capability-design-preview li")].map(item => item.textContent)).toEqual(items.map(capabilityDetailText));
      expect(card).toHaveTextContent("独立证据未核验");
    }
    expect(bridge.call).not.toHaveBeenCalled();
  });
  it("previews matching child intentions before opening details and lets future browsing include partially implemented families", async () => {
    render(<CanonicalCapabilitiesSpace onNavigate={vi.fn()}/>); const user = userEvent.setup();
    await user.type(screen.getByLabelText("查找能力"), "VR");
    const matching = screen.getByRole("region", { name: "空间记忆与沉浸学习匹配的设计细项" });
    expect(matching).toHaveTextContent("VR"); expect(matching).toHaveTextContent("独立证据未核验");
    await user.clear(screen.getByLabelText("查找能力"));
    await user.click(screen.getByRole("button", { name: "未来规划" }));
    await user.click(screen.getByRole("button", { name: "查看全部设计蓝图" }));
    const cards = within(screen.getByRole("region", { name: "能力列表" })).getAllByRole("button", { name: /条设计细项/ });
    expect(cards).toHaveLength(16); expect(bridge.call).not.toHaveBeenCalled();
  });
  it("labels donor usability as historical and limits role observations to the selected capability", async () => {
    render(<CanonicalCapabilitiesSpace onNavigate={vi.fn()} selectedCapabilityId="CAP-0020"/>);
    await screen.findByText(/已读取当前视图/);
    expect(screen.getAllByText(/历史可用登记/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/当前可用：/)).not.toBeInTheDocument();
    expect(screen.getByText(/仅观察「多格式转换」/)).toBeInTheDocument();
    expect(screen.queryByText(/当前 Core 登记/)).not.toBeInTheDocument();
    expect(screen.getByText(/本次没有观察本地回答路由/)).toBeInTheDocument();
  });
  it("opens an existing course page through the guarded callback and keeps partial model configuration separate", async () => {
    const open=vi.fn(),navigate=vi.fn();const view=render(<CanonicalCapabilitiesSpace onNavigate={navigate} onOpenPage={open} selectedCapabilityId="CAP-0060"/>);
    await userEvent.setup().click(screen.getByRole("button",{name:"打开当前产品入口"}));
    expect(open).toHaveBeenCalledWith("07");expect(navigate).not.toHaveBeenCalled();
    view.rerender(<CanonicalCapabilitiesSpace onNavigate={navigate} onOpenPage={open} selectedCapabilityId="CAP-0150"/>);
    expect(screen.getByRole("button",{name:"当前执行入口尚未提供"})).toBeDisabled();
    await userEvent.setup().click(screen.getByRole("button",{name:"查看现有模型配置"}));
    expect(open).toHaveBeenLastCalledWith("19");
  });
  it.each([["CAP-0060", "07"], ["CAP-0090", "05"], ["CAP-0120", "19"]])("keeps %s next-step guidance consistent with its page entry", async (id, page) => {
    const open=vi.fn();render(<CanonicalCapabilitiesSpace onNavigate={vi.fn()} onOpenPage={open} selectedCapabilityId={id}/>);
    expect(screen.queryByText(/尚未关联可打开的产品动作入口/)).not.toBeInTheDocument();
    expect(screen.getByText(/通过当前 AAOS 产品入口继续/)).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button", {name:"打开当前产品入口"}));
    expect(open).toHaveBeenCalledWith(page);
  });
  it("disables model configuration when the host has no page callback instead of opening the catalog again", async () => {
    const navigate=vi.fn();render(<CanonicalCapabilitiesSpace onNavigate={navigate} selectedCapabilityId="CAP-0150"/>);
    const button=screen.getByRole("button", {name:/^查看现有模型配置/});
    expect(button).toBeDisabled();
    await userEvent.setup().click(button);
    expect(navigate).not.toHaveBeenCalled();
    expect(button).toHaveAttribute("title", "当前无法打开模型设置页面");
  });
  it.each(["resolve", "reject"])("ignores a late old-scope %s and clears old failure while reading a new scope", async mode => {
    let finish!: (v: unknown) => void, fail!: (v: unknown) => void;
    bridge.call.mockImplementationOnce(() => new Promise((resolve, reject) => { finish=resolve; fail=reject; }));
    const view = render(<CanonicalCapabilitiesSpace onNavigate={vi.fn()} selectedCapabilityId="CAP-0050"/>);
    view.rerender(<CanonicalCapabilitiesSpace onNavigate={vi.fn()} selectedCapabilityId="CAP-0020"/>);
    await screen.findByText(/已读取当前视图/);
    await act(async () => { if(mode === "resolve") finish(scopedReadiness({scope:"view:CAP-0050",operations:["machine.answer"]})); else fail(new Error("late failure")); });
    expect(screen.queryByText(/读取失败/)).not.toBeInTheDocument();
    expect(screen.getByText(/仅观察「多格式转换」/)).toBeInTheDocument();
    expect(screen.getAllByText(/连接\/权限/)).toHaveLength(13);
    bridge.call.mockRejectedValueOnce(new Error("current failure"));
    await userEvent.setup().click(screen.getByRole("tab",{name:"目录与搜索"}));
    await userEvent.setup().click(screen.getByRole("button",{name:"刷新当前健康与权限"}));
    await screen.findByText(/读取失败，显示未知/);
    bridge.call.mockImplementationOnce(() => new Promise(()=>{}));
    await userEvent.setup().click(screen.getByRole("button",{name:"刷新当前健康与权限"}));
    expect(screen.queryByText(/读取失败，显示未知/)).not.toBeInTheDocument();
    expect(screen.getByText(/正在读取所选能力/)).toBeInTheDocument();
  });
});

describe("readiness rejects malformed, stale or out-of-scope permission observations", () => {
  const query = {scope:"view:CAP-0050",operations:["machine.answer"]};
  it.each(["nan", "infinity", "unsafe", "expired row", "fractional row", "wrong scope", "duplicate", "wrong operation", "invented ready connection", "missing field", "future observed", "invalid enum"])("rejects %s", mode => {
    const snapshot: any = scopedReadiness(query, 1000, 30000);
    if(mode === "nan") snapshot.expires_at_ms=NaN;
    if(mode === "infinity") snapshot.expires_at_ms=Infinity;
    if(mode === "unsafe") snapshot.expires_at_ms=Number.MAX_SAFE_INTEGER+1;
    if(mode === "expired row") snapshot.operations[0].expires_at_ms=999;
    if(mode === "fractional row") snapshot.operations[0].expires_at_ms=1001.5;
    if(mode === "wrong scope") snapshot.scope="other";
    if(mode === "duplicate") snapshot.operations.push({...snapshot.operations[0]});
    if(mode === "wrong operation") snapshot.operations[0].operation="image.ocr";
    if(mode === "invented ready connection") snapshot.operations[0].connection="READY";
    if(mode === "missing field") delete snapshot.operations[0].dependencies;
    if(mode === "future observed") snapshot.observed_at_ms=1002;
    if(mode === "invalid enum") snapshot.operations[0].permission="YES";
    expect(() => readScopedReadiness(snapshot,query.scope,query.operations,1001)).toThrow();
  });
  it("uses the earliest scoped row expiry and keeps permission distinct from connection and qualification", () => {
    const snapshot = scopedReadiness(query,1000);snapshot.operations[0].expires_at_ms=2000;
    const result=readScopedReadiness(snapshot,query.scope,query.operations,1001);
    expect(result.expiresAt).toBe(2000);expect(result.snapshot.operations[0]).toMatchObject({permission:"ENABLED",connection:"UNKNOWN",qualification:"UNVERIFIED"});
  });
});
