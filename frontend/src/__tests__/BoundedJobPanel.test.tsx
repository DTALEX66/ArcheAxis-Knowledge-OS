import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BoundedJobPanel, type BoundedJobCommand } from "../components/BoundedJobPanel";

const source = { source_id: "s1", source_revision: "rev1", sha256: "a".repeat(64), original_name: "synthetic.txt", imported_at: "2026-10-10" };
const job = { job_id: "j1", kind: "text", state: "queued", input_ref: "s1", created_at: "2026-10-10", completed_at: null, attempt: null, error: null };
function row(state = "queued", request: string | null = null, extra = {}) { return { job_id: "j1", input_ref: "s1", state, attempt: request ? 1 : null, request_id: request, error: null, ...extra }; }
let state: ReturnType<typeof row>, execute: (payload: Record<string, unknown>) => Promise<unknown>, status: () => Promise<unknown>, cancellation: (payload: Record<string, unknown>) => Promise<unknown>;
const command = vi.fn<BoundedJobCommand>();
beforeEach(() => {
  command.mockReset();
  job.kind = "text";
  state = row();
  execute = async payload => { state = row("running", String(payload.request_id)); return { job_id: "j1", request_id: payload.request_id, state: "running", replayed: false }; };
  status = async () => state;
  cancellation = async payload => ({ job_id: "j1", request_id: payload.request_id, cancel_requested: true });
  command.mockImplementation(async (op, payload) => {
    switch (op) {
      case "sources_list": return { sources: [source] };
      case "source_jobs": return { source_id: payload.source_id, jobs: [job], jobs_capped: true };
      case "jobs_get": return state;
      case "job_execution_status": return status();
      case "job_execute": return execute(payload);
      case "job_execution_cancel": return cancellation(payload);
      default: throw new Error(`No finite fixture operation ${op}`);
    }
  });
});
async function select() {
  render(<BoundedJobPanel command={command} pollMs={60000} />);
  await screen.findByRole("option", { name: /synthetic.txt/ });
  fireEvent.change(screen.getByLabelText("已保存来源"), { target: { value: "s1" } });
  await screen.findByRole("option", { name: /text · j1/ });
  fireEvent.change(screen.getByLabelText("来源任务"), { target: { value: "j1" } });
  await waitFor(() => expect(screen.getByRole("button", { name: "执行已保存任务" })).toBeEnabled());
}
describe("BoundedJobPanel isolated finite-port behavior", () => {
  it("allows a new bounded attempt only from actual current continuation condition", async () => {
    await select(); fireEvent.click(screen.getByText("执行已保存任务"));
    await screen.findByText("running", { exact: true });
    const priorRequest = state.request_id;
    state = row("failed", priorRequest, { attempts: [{ attempt: 1, request_id: priorRequest, budget: { deadline_ms: 60000 }, steps: { terminal_write: "RECORDED" }, checkpoint: { status: "NOT_OBSERVED" }, continuation: { new_attempt_eligible_state: false, resume_status: "NOT_SUPPORTED" } }] });
    fireEvent.click(screen.getByText("刷新实际状态")); await screen.findByText("failed", { exact: true });
    expect(screen.getByText("新请求重试（不等于检查点恢复）")).toBeDisabled();
    state = row("failed", priorRequest, { attempts: [{ attempt: 1, request_id: priorRequest, budget: { deadline_ms: 60000 }, steps: { terminal_write: "RECORDED" }, checkpoint: { status: "NOT_OBSERVED" }, continuation: { new_attempt_eligible_state: true, resume_status: "NOT_SUPPORTED" } }] });
    fireEvent.click(screen.getByText("刷新实际状态"));
    await waitFor(() => expect(screen.getByText("新请求重试（不等于检查点恢复）")).toBeEnabled());
    fireEvent.click(screen.getByText("新请求重试（不等于检查点恢复）"));
    await waitFor(() => expect(command.mock.calls.filter(([op]) => op === "job_execute")).toHaveLength(2));
    const calls=command.mock.calls.filter(([op]) => op === "job_execute");
    expect(calls[1][1].request_id).not.toBe(calls[0][1].request_id);
    expect(calls[1][1].body).toEqual(calls[0][1].body);
  });
  it("video does not advertise transcribe-only split or word parameters", async () => {
    job.kind="video";
    render(<BoundedJobPanel command={command} pollMs={60000}/>);
    await screen.findByRole("option",{name:/synthetic.txt/});
    fireEvent.change(screen.getByLabelText("已保存来源"),{target:{value:"s1"}});
    await screen.findByRole("option",{name:/video · j1/});
    fireEvent.change(screen.getByLabelText("来源任务"),{target:{value:"j1"}});
    await waitFor(()=>expect(screen.getByText("执行已保存任务")).toBeEnabled());
    expect(screen.getByLabelText(/媒体分段/)).toBeDisabled();
    expect(screen.getByLabelText("词级时间")).toBeDisabled();
    fireEvent.click(screen.getByText("执行已保存任务"));
    await waitFor(()=>expect(command.mock.calls.filter(([op])=>op==="job_execute")).toHaveLength(1));
    expect(command.mock.calls.find(([op])=>op==="job_execute")![1].body).toEqual({deadline_ms:60000,split:false,words:false});
  });
  it("selects persisted source/jobs, reads jobs_get and reports inventory cap", async () => {
    await select(); expect(command).toHaveBeenCalledWith("jobs_get", { job_id: "j1" });
    expect(screen.getByText(/只列最近 50/)).toBeInTheDocument();
    expect(command.mock.calls.some(([op]) => op === "job_execute")).toBe(false);
  });
  it("refuses invalid budget before any execute call", async () => {
    await select(); fireEvent.change(screen.getByLabelText("单次预算（毫秒）"), { target: { value: "300001" } });
    fireEvent.click(screen.getByText("执行已保存任务"));
    expect(await screen.findByText(/预算必须/)).toBeInTheDocument();
    expect(command.mock.calls.some(([op]) => op === "job_execute")).toBe(false);
  });
  it("lost acknowledgement retains exact request and budget on retry", async () => {
    let count = 0;
    execute = async payload => { count++; if (count === 1) throw new Error("lost ack"); state = row("running", String(payload.request_id)); return { job_id: "j1", request_id: payload.request_id, state: "running" }; };
    await select(); fireEvent.change(screen.getByLabelText("单次预算（毫秒）"), { target: { value: "12000" } });
    fireEvent.click(screen.getByText("执行已保存任务"));
    await screen.findByText(/执行未确认/);
    expect(screen.getByLabelText("单次预算（毫秒）")).toBeDisabled();
    fireEvent.click(screen.getByText("同请求重试"));
    await waitFor(() => expect(count).toBe(2));
    const calls = command.mock.calls.filter(([op]) => op === "job_execute");
    expect(calls[0][1]).toEqual(calls[1][1]);
    expect(calls[0][1].body).toEqual({ deadline_ms: 12000, split: false, words: false });
    expect(String(calls[0][1].request_id)).toMatch(/^job_/);
  });
  it("cancel accepted is pending until actual cancelled state; checkpoint stays verbatim", async () => {
    await select(); fireEvent.click(screen.getByText("执行已保存任务"));
    await waitFor(() => expect(screen.getByRole("button", { name: "请求取消" })).toBeEnabled());
    fireEvent.click(screen.getByText("请求取消"));
    await screen.findByText(/取消待确认/);
    expect(screen.queryByText("cancelled", { exact: true })).not.toBeInTheDocument();
    state = row("cancelled", state.request_id, { error: "user cancellation", checkpoint: { opaque: { preserved: "fixture-receipt" }, windows_present: 2 } });
    fireEvent.click(screen.getByText("刷新实际状态"));
    await screen.findByText("cancelled", { exact: true });
    expect(screen.queryByText(/取消待确认/)).not.toBeInTheDocument();
    expect(screen.getByText(/fixture-receipt/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "执行已保存任务" })).toBeDisabled();
  });
  it("failed status refresh preserves previous complete checkpoint receipt", async () => {
    await select(); fireEvent.click(screen.getByText("执行已保存任务"));
    await waitFor(() => expect(screen.getByText("running", { exact: true })).toBeInTheDocument());
    state = row("running", state.request_id, { checkpoint: { external_future_field: "keep-this" } });
    fireEvent.click(screen.getByText("刷新实际状态")); await screen.findByText(/keep-this/);
    status = async () => { throw new Error("offline"); };
    fireEvent.click(screen.getByText("刷新实际状态")); await screen.findByText(/状态读回未确认/);
    expect(screen.getByText(/keep-this/)).toBeInTheDocument();
  });
  it("wrong execute request identity cannot unlock the frozen payload", async () => {
    execute = async () => ({ job_id: "j1", request_id: "wrong", state: "running" });
    await select(); fireEvent.click(screen.getByText("执行已保存任务"));
    await screen.findByText(/执行未确认/);
    expect(screen.getByRole("button", { name: "同请求重试" })).toBeEnabled();
    expect(screen.getByLabelText("来源任务")).toBeDisabled();
  });
  it("newer read wins over delayed earlier status and wrong-request readback is rejected", async () => {
    await select(); fireEvent.click(screen.getByText("执行已保存任务"));
    await screen.findByText("running", { exact: true });
    let resolve!: (value: unknown) => void;
    status = () => new Promise(done => { resolve = done; });
    fireEvent.click(screen.getByText("刷新实际状态"));
    status = async () => row("succeeded", state.request_id);
    fireEvent.click(screen.getByText("刷新实际状态")); await screen.findByText("succeeded", { exact: true });
    await act(async () => { resolve(row("running", state.request_id)); });
    expect(screen.getByText("succeeded", { exact: true })).toBeInTheDocument();
    status = async () => row("failed", "different-request");
    fireEvent.click(screen.getByText("刷新实际状态")); await screen.findByText(/状态读回未确认/);
    expect(screen.getByText("succeeded", { exact: true })).toBeInTheDocument();
  });
  it("multiple panels have distinct dirty owners and unmount only clears their own", async () => {
    const events: Array<{ owner: string; dirty: boolean }> = [];
    const listener = (event: Event) => events.push((event as CustomEvent).detail);
    window.addEventListener("archeaxis-draft-dirty", listener);
    const first = render(<BoundedJobPanel command={command} />), second = render(<BoundedJobPanel command={command} />);
    const owners = new Set(events.map(event => event.owner)); expect(owners.size).toBe(2);
    first.unmount(); second.unmount();
    expect(events.slice(-2).every(event => !event.dirty)).toBe(true);
    window.removeEventListener("archeaxis-draft-dirty", listener);
  });
  it("polls persisted terminal state without treating execute acknowledgement as success", async () => {
    render(<BoundedJobPanel command={command} pollMs={250} />);
    await screen.findByRole("option", { name: /synthetic.txt/ });
    fireEvent.change(screen.getByLabelText("已保存来源"), { target: { value: "s1" } });
    await screen.findByRole("option", { name: /text · j1/ });
    fireEvent.change(screen.getByLabelText("来源任务"), { target: { value: "j1" } });
    await waitFor(() => expect(screen.getByText("执行已保存任务")).toBeEnabled());
    fireEvent.click(screen.getByText("执行已保存任务"));
    await screen.findByText("running", { exact: true });
    state = row("succeeded", state.request_id);
    await screen.findByText("succeeded", { exact: true });
    expect(command.mock.calls.filter(([op]) => op === "job_execution_status").length).toBeGreaterThanOrEqual(2);
  });
  it("cancellation of reopened running job pins request even without a local execution attempt", async () => {
    state = row("running", "saved-request");
    render(<BoundedJobPanel command={command} pollMs={60000} />);
    await screen.findByRole("option", { name: /synthetic.txt/ });
    fireEvent.change(screen.getByLabelText("已保存来源"), { target: { value: "s1" } });
    await screen.findByRole("option", { name: /text · j1/ });
    fireEvent.change(screen.getByLabelText("来源任务"), { target: { value: "j1" } });
    await waitFor(() => expect(screen.getByText("请求取消")).toBeEnabled());
    fireEvent.click(screen.getByText("请求取消")); await screen.findByText(/取消待确认/);
    state = row("cancelled", "unrelated-new-request");
    fireEvent.click(screen.getByText("刷新实际状态")); await screen.findByText(/状态读回未确认/);
    expect(screen.getByText(/取消待确认/)).toBeInTheDocument();
    state = row("cancelled", "saved-request");
    fireEvent.click(screen.getByText("刷新实际状态")); await screen.findByText("cancelled", { exact: true });
    expect(screen.queryByText(/取消待确认/)).not.toBeInTheDocument();
    expect(command).toHaveBeenCalledWith("job_execution_cancel", { job_id: "j1", request_id: "saved-request" });
  });
});
