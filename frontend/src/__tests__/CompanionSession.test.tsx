import {StrictMode} from "react";
import {beforeEach, afterEach, it, expect, vi} from "vitest";
import {render, screen, within, fireEvent, act, waitFor} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {webcrypto} from "node:crypto";
import {ConversationPanel} from "../components/ConversationPanel";
import {CompanionSessionProvider} from "../companion/CompanionSessionProvider";
import {CompanionSession} from "../companion/CompanionSession";
import {CoreWorkingStateSession, type WorkingRead} from "../presentation/coreWorkingState";
import {CoreWorkingStateProvider} from "../presentation/useCoreWorkingState";

const bridge = vi.hoisted(() => ({call: vi.fn(), configuration: null as null | (() => Promise<unknown>)}));
vi.mock("../api/core", () => ({coreCommand: (op: string, p: unknown) => op === "model_configuration_get" ? bridge.configuration?.() ?? Promise.resolve({revision: 0}) : bridge.call(op, p)}));
const summary = {session_id: "session_a", title: "SYNTHETIC session", last_sequence: 0, consumer: "archeaxis"};
const history = {schema: "archeaxis.conversation-session/v1", ...summary, events: [], requests: [], delivery: "BUFFERED", cross_project_consumer: "UNVERIFIED"};
const material = {kind: "document" as const, document_id: "doc_a", version: 1, content_sha256: "a".repeat(64), block_id: null};
function normal(op: string, p: {body: Record<string, unknown>}) {
  if (op === "conversation_history") return p.body.session_id ? {...history, session_id: p.body.session_id} : {schema: "archeaxis.conversation-catalog/v1", sessions: [summary], limit: 16};
  if (op === "conversation_request") return p.body.preview ? {schema: "archeaxis.conversation-preview/v1", plan: {request: p.body}, plan_sha256: "b".repeat(64)} : receipt(p.body);
  if (op === "conversation_status") return receipt(p.body);
  throw Error(op);
}
function receipt(body: Record<string, unknown>) {return {schema: "archeaxis.conversation-receipt/v1", session_id: body.session_id, request_id: body.request_id, state: "completed", answer: {answer: "SYNTHETIC answer"}, delivery: "BUFFERED"};}
function Slots({reader = material, showHome = true}: {reader?: typeof material; showHome?: boolean}) {
  return <>{showHome ? <div data-testid="home"><ConversationPanel slot="home"/></div> : null}<div data-testid="reader"><ConversationPanel slot="reader" material={reader}/></div><div data-testid="sidebar"><ConversationPanel slot="sidebar"/></div></>;
}
const slot = (name: string) => within(screen.getByTestId(name));
async function select() {await slot("home").findByText("SYNTHETIC session · 1"); fireEvent.change(slot("home").getByLabelText("已保存会话"), {target: {value: "session_a"}}); await slot("reader").findByText("当前会话：SYNTHETIC session");}
async function preview() {fireEvent.change(slot("home").getByLabelText("会话问题"), {target: {value: "跨位置草稿"}}); fireEvent.click(slot("reader").getByText("预览会话请求")); await slot("sidebar").findByText("确认执行同一会话请求");}
beforeEach(() => {vi.stubGlobal("crypto", webcrypto); bridge.configuration = null; bridge.call.mockReset(); bridge.call.mockImplementation(async (op, p) => normal(op, p));});
afterEach(() => {vi.unstubAllGlobals(); delete window.__TAURI__;});

it("shares draft, selected session and frozen material across three slots, with one catalog under StrictMode", async () => {
  render(<StrictMode><CompanionSessionProvider><Slots/></CompanionSessionProvider></StrictMode>);
  await select(); await preview();
  expect(slot("sidebar").getByLabelText("会话问题")).toHaveValue("跨位置草稿");
  expect(slot("home").getByText(/已保存文档第 1 版/)).toBeInTheDocument();
  expect(bridge.call.mock.calls.filter(c => c[0] === "conversation_history" && !c[1].body.session_id)).toHaveLength(1);
  const frozen = bridge.call.mock.calls.find(c => c[0] === "conversation_request")![1].body;
  expect(frozen).toMatchObject({material, purpose: "material_learning", question: "跨位置草稿"});
  fireEvent.click(slot("home").getByText("确认执行同一会话请求")); await slot("sidebar").findByRole("img", {name: "小栖：已完成"});
  expect(bridge.call.mock.calls.filter(c => c[0] === "conversation_request")[1][1].body).toEqual({...frozen, preview: false, confirmed_plan_sha256: "b".repeat(64)});
});
it("admits only one execution when two slots confirm synchronously, and removing a view never cancels it", async () => {
  let finish!: (v: unknown) => void; let running: Record<string, unknown> = {};
  bridge.call.mockImplementation((op, p) => op === "conversation_request" && !p.body.preview ? (running = p.body, new Promise(resolve => {finish = resolve;})) : Promise.resolve(normal(op, p)));
  const view = render(<CompanionSessionProvider><Slots/></CompanionSessionProvider>); await select(); await preview();
  act(() => {slot("home").getByText("确认执行同一会话请求").click(); slot("sidebar").getByText("确认执行同一会话请求").click();});
  view.rerender(<CompanionSessionProvider><Slots showHome={false}/></CompanionSessionProvider>);
  expect(slot("sidebar").getByRole("img", {name: "小栖：思考中"})).toBeInTheDocument();
  await act(async () => finish(receipt(running)));
  expect(bridge.call.mock.calls.filter(c => c[0] === "conversation_request" && !c[1].body.preview)).toHaveLength(1);
  expect(bridge.call.mock.calls.some(c => c[0] === "conversation_cancel")).toBe(false);
});
it("retains UNKNOWN and the original ID when all views unmount and return", async () => {
  let running: Record<string, unknown> = {};
  bridge.call.mockImplementation(async (op, p) => {if (op === "conversation_request" && !p.body.preview) {running = p.body; throw Error("SYNTHETIC lost ACK");} return normal(op, p);});
  const service = new CompanionSession();
  const view = render(<CompanionSessionProvider session={service}><Slots/></CompanionSessionProvider>); await select(); await preview();
  fireEvent.click(slot("home").getByText("确认执行同一会话请求")); await slot("sidebar").findByText("请求状态未确认，请查询原请求。");
  view.rerender(<CompanionSessionProvider session={service}>{null}</CompanionSessionProvider>);
  view.rerender(<CompanionSessionProvider session={service}><Slots/></CompanionSessionProvider>);
  expect(slot("home").getByLabelText("会话问题")).toHaveValue("跨位置草稿");
  expect(slot("home").getByText("预览会话请求")).toBeDisabled();
  fireEvent.click(slot("sidebar").getByText("查询未确认请求")); await slot("reader").findByRole("img", {name: "小栖：已完成"});
  expect(bridge.call.mock.calls.find(c => c[0] === "conversation_status")![1].body).toEqual({session_id: "session_a", request_id: running.request_id});
  expect(bridge.call.mock.calls.filter(c => c[0] === "conversation_request")).toHaveLength(2);
  for (const name of ["home", "reader", "sidebar"]) expect(slot(name).getAllByText("SYNTHETIC answer")).toHaveLength(1);
});
it("recovers the original answer and request index, then deduplicates a later history replay", async () => {
  let running: Record<string, unknown> = {}, completed = false, failHistory = false;
  bridge.call.mockImplementation(async (op, p) => {
    if (op === "conversation_request" && !p.body.preview) {running = p.body; throw Error("SYNTHETIC lost ACK");}
    if (op === "conversation_history" && p.body.session_id && completed) {
      if (failHistory) throw Error("SYNTHETIC history offline");
      const terminal = receipt(running);
      return {...history, last_sequence: 2, events: [
        {session_id: "session_a", request_id: running.request_id, sequence: 1, kind: "accepted", data: {question: "跨位置草稿"}, delivery: "BUFFERED"},
        {session_id: "session_a", request_id: running.request_id, sequence: 2, kind: "completed", data: terminal, delivery: "BUFFERED"},
      ], requests: [{request_id: running.request_id, state: "completed", receipt: terminal}]};
    }
    return normal(op, p);
  });
  render(<CompanionSessionProvider><Slots/></CompanionSessionProvider>); await select(); await preview();
  fireEvent.click(slot("home").getByText("确认执行同一会话请求")); await slot("sidebar").findByText("请求状态未确认，请查询原请求。");
  completed = true; failHistory = true;
  fireEvent.click(slot("sidebar").getByText("查询未确认请求"));
  await slot("home").findByText("原请求回执已核对；历史暂未同步，请重读历史。");
  for (const name of ["home", "reader", "sidebar"]) expect(slot(name).getAllByText("SYNTHETIC answer")).toHaveLength(1);
  failHistory = false; fireEvent.click(slot("home").getByText("重读历史"));
  await slot("reader").findByText("查询第 1 次提问 · 已完成");
  for (const name of ["home", "reader", "sidebar"]) expect(slot(name).getAllByText("SYNTHETIC answer")).toHaveLength(1);
  expect(bridge.call.mock.calls.filter(c => c[0] === "conversation_request" && !c[1].body.preview)).toHaveLength(1);
});
it("refreshes terminal status history without replacing already loaded events", async () => {
  let refresh = false;
  const accepted = {session_id: "session_a", request_id: "old_request", sequence: 1, kind: "accepted", data: {question: "已加载的问题"}, delivery: "BUFFERED"};
  bridge.call.mockImplementation(async (op, p) => op === "conversation_history" && p.body.session_id ? {...history, last_sequence: 1, events: refresh ? [] : [accepted], requests: [{request_id: "old_request", state: "EXECUTING", receipt: null}]} : normal(op, p));
  render(<CompanionSessionProvider><Slots/></CompanionSessionProvider>); await select(); refresh = true;
  fireEvent.click(slot("home").getByText("查询未确认请求"));
  await slot("sidebar").findByText("原请求回执与历史已读回；回答仍需你判断。");
  expect(slot("reader").getByText("已加载的问题")).toBeVisible();
  expect(slot("reader").getByText("查询第 1 次提问 · 已完成")).toBeVisible();
  expect(slot("reader").getByText("SYNTHETIC answer")).toBeVisible();
  expect(bridge.call.mock.calls.some(c => c[0] === "conversation_request")).toBe(false);
});
it("fences a delayed status-history refresh after workspace retirement", async () => {
  const service = new CompanionSession(); let finish!: (v: unknown) => void, refresh = false;
  bridge.call.mockImplementation((op, p) => refresh && op === "conversation_history" && p.body.session_id ? new Promise(resolve => {finish = resolve;}) : Promise.resolve(normal(op, p)));
  await service.load("session_a"); refresh = true;
  const reading = service.readRequest("old_request"); await waitFor(() => expect(finish).toBeDefined());
  service.pause(); const current = service.getSnapshot().current;
  await act(async () => {finish({...history, title: "LATE HISTORY"}); await reading;});
  expect(service.getSnapshot().current).toBe(current); expect(service.getSnapshot().paused).toBe(true);
});
it("keeps a completed execution visible when only its subsequent history read fails", async () => {
  let admitted = false;
  bridge.call.mockImplementation(async (op, p) => {
    if (op === "conversation_request" && !p.body.preview) {admitted = true; return receipt(p.body);}
    if (op === "conversation_history" && p.body.session_id && admitted) throw Error("SYNTHETIC history offline");
    return normal(op, p);
  });
  const service = new CompanionSession();
  render(<CompanionSessionProvider session={service}><Slots/></CompanionSessionProvider>); await select(); await preview();
  fireEvent.click(slot("home").getByText("确认执行同一会话请求"));
  await slot("sidebar").findByText("原请求回执已核对；历史暂未同步，请重读历史。");
  expect(slot("reader").getByText("SYNTHETIC answer")).toBeVisible();
  expect(slot("reader").queryByText("请求状态未确认，请查询原请求。")).toBeNull();
  expect(service.getSnapshot().current?.events).toEqual([]);
  expect(service.getSnapshot().confirmedReceipts).toHaveLength(1);
  expect(bridge.call.mock.calls.filter(c => c[0] === "conversation_request" && !c[1].body.preview)).toHaveLength(1);
});
it("never displays another session's status answer or a retired workspace's late receipt", async () => {
  const service = new CompanionSession(); await service.load("session_a");
  bridge.call.mockImplementation(async (op, p) => op === "conversation_status" ? {...receipt(p.body), session_id: "session_other"} : normal(op, p));
  await service.readRequest("old_request");
  expect(service.getSnapshot().result).toBeNull(); expect(service.getSnapshot().confirmedReceipts).toEqual([]);
  let finish!: (v: unknown) => void;
  bridge.call.mockImplementation((op, p) => op === "conversation_status" ? new Promise(resolve => {finish = resolve;}) : Promise.resolve(normal(op, p)));
  const reading = service.readRequest("old_request"); service.pause();
  finish(receipt({session_id: "session_a", request_id: "old_request"})); await reading;
  expect(service.getSnapshot().result).toBeNull(); expect(service.getSnapshot().confirmedReceipts).toEqual([]);
  expect(service.getSnapshot().paused).toBe(true);
});
it("invalidates a delayed preview only when its initiating reader context changes", async () => {
  let finish!: (v: unknown) => void; let body: Record<string, unknown> = {};
  bridge.call.mockImplementation((op, p) => op === "conversation_request" ? (body = p.body, new Promise(resolve => {finish = resolve;})) : Promise.resolve(normal(op, p)));
  const view = render(<CompanionSessionProvider><Slots/></CompanionSessionProvider>); await select();
  fireEvent.change(slot("home").getByLabelText("会话问题"), {target: {value: "材料 A"}}); fireEvent.click(slot("reader").getByText("预览会话请求"));
  await waitFor(() => expect(finish).toBeDefined());
  view.rerender(<CompanionSessionProvider><Slots reader={{...material, document_id: "doc_b"}}/></CompanionSessionProvider>);
  await act(async () => finish({schema: "archeaxis.conversation-preview/v1", plan: {request: body}, plan_sha256: "b".repeat(64)}));
  expect(screen.queryByText("确认执行同一会话请求")).toBeNull();
  expect(slot("home").getByLabelText("会话问题")).toHaveValue("材料 A");
});
it("fences old workspace responses without leaking the old draft into a replacement service", async () => {
  let finish!: (v: unknown) => void; let running: Record<string, unknown> = {};
  bridge.call.mockImplementation((op, p) => op === "conversation_request" && !p.body.preview ? (running = p.body, new Promise(resolve => {finish = resolve;})) : Promise.resolve(normal(op, p)));
  const first = new CompanionSession(), second = new CompanionSession();
  const view = render(<CompanionSessionProvider session={first}><Slots/></CompanionSessionProvider>); await select(); await preview(); fireEvent.click(slot("home").getByText("确认执行同一会话请求"));
  view.rerender(<CompanionSessionProvider session={second}><Slots/></CompanionSessionProvider>);
  const reads = bridge.call.mock.calls.filter(c => c[0] === "conversation_history" && c[1].body.session_id).length;
  await act(async () => finish(receipt(running)));
  expect(bridge.call.mock.calls.filter(c => c[0] === "conversation_history" && c[1].body.session_id)).toHaveLength(reads);
  expect(screen.queryByText("当前会话：SYNTHETIC session")).toBeNull(); expect(second.getSnapshot().question).toBe(""); expect(second.getSnapshot().result).toBeNull();
  expect(bridge.call.mock.calls.filter(c => c[0] === "conversation_request" && !c[1].body.preview)).toHaveLength(1);
});
it("retiring a workspace while model resolution is pending prevents any old preview command", async () => {
  let finish!: (v: unknown) => void; bridge.configuration = () => new Promise(resolve => {finish = resolve;});
  const view = render(<CompanionSessionProvider session={new CompanionSession()}><Slots/></CompanionSessionProvider>); await select();
  fireEvent.change(slot("home").getByLabelText("会话问题"), {target: {value: "旧工作区"}}); fireEvent.click(slot("reader").getByText("预览会话请求")); await waitFor(() => expect(finish).toBeDefined());
  view.rerender(<CompanionSessionProvider session={new CompanionSession()}><Slots/></CompanionSessionProvider>);
  await act(async () => finish({revision: 0}));
  expect(bridge.call.mock.calls.some(c => c[0] === "conversation_request")).toBe(false);
});
it("a blocked working-state status cannot be unlocked by an identity callback captured while ready", async () => {
  const read: WorkingRead = {schema: "archeaxis.ui-working-state/v1", workspace_id: "a".repeat(32), restore_epoch: "initial", state_revision: 0, state: {drafts: {}, opened_documents: [], active_document: null, page_id: null, pending_original: null}, draft_digests: {}, pending_document_id: null, recovery_candidates: null, recovery_requires_confirmation: false};
  let blocked = false;
  const working = new CoreWorkingStateSession({read: async () => {if (blocked) throw Error("SYNTHETIC blocked"); return structuredClone(read);}, write: async () => read, clearSaved: async () => read, recover: async () => read}); await working.load();
  bridge.call.mockImplementation(async (op, p) => op === "ui_state_read" ? read : normal(op, p));
  render(<CoreWorkingStateProvider session={working}><CompanionSessionProvider><Slots/></CompanionSessionProvider></CoreWorkingStateProvider>); await select();
  blocked = true; await act(async () => {await working.load().catch(() => {});});
  fireEvent.click(slot("home").getByText("核对陪伴工作区"));
  expect(slot("sidebar").getByText("新建陪伴会话")).toBeDisabled(); expect(bridge.call.mock.calls.some(c => c[0] === "ui_state_read")).toBe(false);
});
it("accepts a terminal receipt from later history pages after a lost execution acknowledgment", async () => {
  let running: Record<string, unknown> = {}, paged = false;
  bridge.call.mockImplementation(async (op, p) => {
    if (op === "conversation_request" && !p.body.preview) {running = p.body; throw Error("SYNTHETIC lost ACK");}
    if (op === "conversation_history" && p.body.session_id && paged) {
      const complete = p.body.after_sequence === 0 && bridge.call.mock.calls.filter(c => c[0] === "conversation_history" && c[1].body.session_id && c[1].body.limit === 64).length > 2;
      const terminal = receipt(running);
      return {...history, last_sequence: 1, events: complete ? [{session_id: "session_a", request_id: running.request_id, sequence: 1, kind: "completed", data: terminal, delivery: "BUFFERED"}] : [], requests: [{request_id: running.request_id, state: complete ? "completed" : "EXECUTING", receipt: complete ? terminal : null}]};
    }
    return normal(op, p);
  });
  render(<CompanionSessionProvider><Slots/></CompanionSessionProvider>); await select(); await preview(); fireEvent.click(slot("home").getByText("确认执行同一会话请求")); await slot("sidebar").findByText("请求状态未确认，请查询原请求。");
  paged = true; fireEvent.click(slot("home").getByText("重读历史")); await slot("home").findByText("读取后续会话事件"); fireEvent.click(slot("home").getByText("读取后续会话事件"));
  await slot("sidebar").findByRole("img", {name: "小栖：已完成"});
  expect(slot("reader").queryByText("请求状态未确认，请查询原请求。")).toBeNull(); expect(slot("home").getByText("预览会话请求")).not.toBeDisabled();
});
it("an unconfirmed workspace invalidation pauses sending and keeps the admitted ID instead of clearing it", async () => {
  bridge.call.mockImplementation(async (op, p) => {if (op === "conversation_request" && !p.body.preview) throw Error("SYNTHETIC lost ACK"); return normal(op, p);});
  const service = new CompanionSession(); render(<CompanionSessionProvider session={service}><Slots/></CompanionSessionProvider>); await select(); await preview(); fireEvent.click(slot("home").getByText("确认执行同一会话请求")); await slot("sidebar").findByText("请求状态未确认，请查询原请求。");
  const original = service.getSnapshot().outstandingId;
  act(() => {window.dispatchEvent(new CustomEvent("workspace-invalidated", {detail: {confirmed: false}}));});
  expect(service.getSnapshot().outstandingId).toBe(original); expect(slot("sidebar").getByText("新建陪伴会话")).toBeDisabled();
  await act(async () => {await service.create(); await service.execute(); await service.prepare({}, {});});
  expect(bridge.call.mock.calls.filter(c => c[0] === "conversation_request")).toHaveLength(2);
});
it("a previous terminal request cannot suppress invalidation of the next delayed material preview", async () => {
  const service = new CompanionSession();
  const view = render(<CompanionSessionProvider session={service}><Slots/></CompanionSessionProvider>); await select(); await preview(); fireEvent.click(slot("home").getByText("确认执行同一会话请求")); await slot("sidebar").findByRole("img", {name: "小栖：已完成"});
  let finish!: (v: unknown) => void; let body: Record<string, unknown> = {};
  bridge.call.mockImplementation((op, p) => op === "conversation_request" ? (body = p.body, new Promise(resolve => {finish = resolve;})) : Promise.resolve(normal(op, p)));
  fireEvent.click(slot("reader").getByText("预览会话请求")); await waitFor(() => expect(finish).toBeDefined());
  view.rerender(<CompanionSessionProvider session={service}><Slots reader={{...material, version: 2}}/></CompanionSessionProvider>);
  await act(async () => finish({schema: "archeaxis.conversation-preview/v1", plan: {request: body}, plan_sha256: "b".repeat(64)}));
  expect(screen.queryByText("确认执行同一会话请求")).toBeNull();
});
it("does not lose a delayed catalog when a new session is created first", async () => {
  let finish!: (v: unknown) => void;
  bridge.call.mockImplementation((op, p) => op === "conversation_history" && !p.body.session_id ? new Promise(resolve => {finish = resolve;}) : Promise.resolve(op === "conversation_session_create" ? {...history, session_id: p.body.session_id, title: "NEW"} : normal(op, p)));
  const service = new CompanionSession(); render(<CompanionSessionProvider session={service}><Slots/></CompanionSessionProvider>);
  fireEvent.click(slot("home").getByText("新建陪伴会话")); await waitFor(() => expect(service.getSnapshot().current?.title).toBe("NEW"));
  await act(async () => finish({schema: "archeaxis.conversation-catalog/v1", sessions: [summary], limit: 16}));
  expect(service.getSnapshot().sessions.map(s => s.title)).toEqual(["NEW", "SYNTHETIC session"]);
});
it("a recovered terminal receipt overrides a stale EXECUTING history index for the next preview", async () => {
  bridge.call.mockImplementation(async (op, p) => op === "conversation_history" && p.body.session_id ? {...history, requests: [{request_id: "old_request", state: "EXECUTING", receipt: null}]} : normal(op, p));
  render(<CompanionSessionProvider><Slots/></CompanionSessionProvider>); await select();
  fireEvent.click(slot("home").getByText("查询未确认请求")); await slot("sidebar").findByRole("img", {name: "小栖：已完成"});
  await preview(); expect(slot("home").getByText("确认执行同一会话请求")).not.toBeDisabled();
});
it("exposes a single-flight catalog retry after a failed initial read", async () => {
  bridge.call.mockRejectedValueOnce(Error("SYNTHETIC catalog unavailable"));
  render(<CompanionSessionProvider><Slots/></CompanionSessionProvider>);
  await slot("home").findByText("会话目录暂未确认，请重读或创建。");
  let finish!: (v: unknown) => void;
  bridge.call.mockImplementation((op, p) => op === "conversation_history" && !p.body.session_id ? new Promise(resolve => {finish = resolve;}) : Promise.resolve(normal(op, p)));
  act(() => {slot("home").getByText("重读会话目录").click(); slot("sidebar").getByText("重读会话目录").click();});
  await act(async () => finish({schema: "archeaxis.conversation-catalog/v1", sessions: [summary], limit: 16}));
  expect(bridge.call.mock.calls.filter(c => c[0] === "conversation_history")).toHaveLength(2);
  expect(slot("reader").getByText("SYNTHETIC session · 1")).toBeInTheDocument();
});
it("keeps the restore barrier across ordinary state readbacks, then requires a fresh matching identity after finish", async () => {
  const read: WorkingRead = {schema: "archeaxis.ui-working-state/v1", workspace_id: "a".repeat(32), restore_epoch: "initial", state_revision: 0, state: {drafts: {}, opened_documents: [], active_document: null, page_id: null, pending_original: null}, draft_digests: {}, pending_document_id: null, recovery_candidates: null, recovery_requires_confirmation: false};
  const working = new CoreWorkingStateSession({read: async () => structuredClone(read), write: async () => structuredClone(read), clearSaved: async () => structuredClone(read), recover: async () => structuredClone(read)});
  await working.load();
  let identityAllowed = false;
  bridge.call.mockImplementation(async (op, p) => {if (op === "ui_state_read") {if (!identityAllowed) throw Error("SYNTHETIC identity unavailable"); return read;} return normal(op, p);});
  const service = new CompanionSession();
  render(<CoreWorkingStateProvider session={working}><CompanionSessionProvider session={service}><Slots/></CompanionSessionProvider></CoreWorkingStateProvider>); await select();
  fireEvent.change(slot("home").getByLabelText("会话问题"), {target: {value: "恢复前草稿"}});
  act(() => {window.dispatchEvent(new Event("workspace-restore-start"));});
  await act(async () => {await working.load();});
  expect(slot("sidebar").getByText("新建陪伴会话")).toBeDisabled();
  expect(bridge.call.mock.calls.some(c => c[0] === "ui_state_read")).toBe(false);
  act(() => {window.dispatchEvent(new Event("workspace-restore-finish"));});
  await waitFor(() => expect(bridge.call.mock.calls.some(c => c[0] === "ui_state_read")).toBe(true));
  expect(slot("sidebar").getByText("新建陪伴会话")).toBeDisabled();
  identityAllowed = true; fireEvent.click(slot("home").getByText("核对陪伴工作区"));
  await waitFor(() => expect(slot("sidebar").getByText("新建陪伴会话")).not.toBeDisabled());
  expect(slot("reader").getByLabelText("会话问题")).toHaveValue("恢复前草稿");
});

it("keeps sidebar management folded, with explicit catalog/history reads and shared drafts", async () => {
  const user = userEvent.setup();
  render(<CompanionSessionProvider><Slots/></CompanionSessionProvider>);
  await slot("home").findByText("SYNTHETIC session · 1");
  const sidebar = slot("sidebar");
  const management = sidebar.getByText("会话与历史管理").closest("details")!;
  expect(management).not.toHaveAttribute("open");
  expect(sidebar.getByRole("button", {name: "重读会话目录"})).not.toBeVisible();
  expect(sidebar.getByRole("button", {name: "新建陪伴会话"})).toBeVisible();
  expect(bridge.call.mock.calls.filter(c => c[0] === "conversation_history")).toHaveLength(1);
  await user.click(sidebar.getByText("会话与历史管理"));
  expect(management).toHaveAttribute("open");
  await user.click(sidebar.getByRole("button", {name: "重读会话目录"}));
  expect(bridge.call.mock.calls.filter(c => c[0] === "conversation_history" && !c[1].body.session_id)).toHaveLength(2);
  await user.selectOptions(sidebar.getByLabelText("已保存会话"), "session_a");
  await slot("reader").findByText("当前会话：SYNTHETIC session");
  expect(sidebar.getByRole("button", {name: "查看会话诊断：会话运行记录"})).toBeVisible();
  const reads = bridge.call.mock.calls.filter(c => c[0] === "conversation_history" && c[1].body.session_id).length;
  await user.click(sidebar.getByRole("button", {name: "重读历史"}));
  expect(bridge.call.mock.calls.filter(c => c[0] === "conversation_history" && c[1].body.session_id)).toHaveLength(reads + 1);
  await user.click(sidebar.getByText("会话与历史管理"));
  expect(management).not.toHaveAttribute("open");
  expect(sidebar.getByRole("button", {name: "重读历史"})).not.toBeVisible();
  await user.type(sidebar.getByLabelText("会话问题"), "管理折叠后继续提问");
  expect(slot("home").getByLabelText("会话问题")).toHaveValue("管理折叠后继续提问");
  expect(slot("reader").getByLabelText("会话问题")).toHaveValue("管理折叠后继续提问");
  expect(sidebar.getByRole("button", {name: "预览会话请求"})).toBeEnabled();
});

it("preserves the explicit character view on resize without losing session state", async () => {
  vi.stubGlobal("innerWidth", 1920); vi.stubGlobal("innerHeight", 1080);
  const user = userEvent.setup();
  render(<CompanionSessionProvider><Slots/></CompanionSessionProvider>);
  await select();
  fireEvent.change(slot("home").getByLabelText("会话问题"), {target: {value: "缩放前草稿"}});
  const sidebar = slot("sidebar");
  expect(sidebar.getByRole("button", {name: "半身"})).toHaveAttribute("aria-pressed", "true");
  expect(slot("reader").getByRole("img", {name: "小栖：待命"}).closest(".xiaoqi-avatar")).toHaveAttribute("data-presentation", "avatar");
  await user.click(sidebar.getByRole("button", {name: "半身"}));
  vi.stubGlobal("innerHeight", 720);
  act(() => window.dispatchEvent(new Event("resize")));
  expect(sidebar.getByRole("button", {name: "半身"})).toHaveAttribute("aria-pressed", "true");
  await user.click(sidebar.getByRole("button", {name: "半身"}));
  expect(sidebar.getByRole("img", {name: "小栖：待命"}).closest(".xiaoqi-avatar")).toHaveAttribute("data-presentation", "portrait");
  expect(sidebar.getByLabelText("会话问题")).toHaveValue("缩放前草稿");
  vi.stubGlobal("innerHeight", 1080); vi.stubGlobal("innerWidth", 1000);
  act(() => window.dispatchEvent(new Event("resize")));
  expect(sidebar.getByRole("button", {name: "半身"})).toHaveAttribute("aria-pressed", "true");
  vi.stubGlobal("innerWidth", 1920);
  act(() => window.dispatchEvent(new Event("resize")));
  expect(sidebar.getByRole("button", {name: "半身"})).toHaveAttribute("aria-pressed", "true");
  expect(sidebar.getByLabelText("会话问题")).toHaveValue("缩放前草稿");
});

it("keeps the original UNKNOWN request query reachable while sidebar management stays closed", async () => {
  let admitted: Record<string, unknown> = {};
  bridge.call.mockImplementation(async (op, p) => {
    if (op === "conversation_request" && !p.body.preview) {admitted = p.body; throw Error("SYNTHETIC lost ACK");}
    return normal(op, p);
  });
  const user = userEvent.setup();
  render(<CompanionSessionProvider><Slots/></CompanionSessionProvider>);
  await select(); await preview();
  const sidebar = slot("sidebar");
  await user.click(sidebar.getByRole("button", {name: "确认执行同一会话请求"}));
  await sidebar.findByText("请求状态未确认，请查询原请求。");
  expect(sidebar.getByText("会话与历史管理").closest("details")).not.toHaveAttribute("open");
  expect(sidebar.getByLabelText("会话问题")).toHaveValue("跨位置草稿");
  expect(sidebar.getByRole("button", {name: "预览会话请求"})).toBeDisabled();
  await user.click(sidebar.getByRole("button", {name: "查询未确认请求"}));
  await sidebar.findByRole("img", {name: "小栖：已完成"});
  expect(bridge.call.mock.calls.find(c => c[0] === "conversation_status")![1].body).toEqual({session_id: "session_a", request_id: admitted.request_id});
  expect(bridge.call.mock.calls.filter(c => c[0] === "conversation_request")).toHaveLength(2);
  expect(sidebar.getByText("会话与历史管理").closest("details")).not.toHaveAttribute("open");
});
