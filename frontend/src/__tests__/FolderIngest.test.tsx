import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FolderIngest } from "../components/FolderIngest";
import { ApiError, type JobAdmissionRefusal } from "../api/client";

const bridge = vi.hoisted(() => ({ call: vi.fn(), open: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));

const HASH = "3f78698a3d7a32944baa70b1b8677e2c9a3d0b9c1e2f3a4b5c6d7e8f90a1b2c3";

/** A file as a directory picker reports it: its path inside the picked folder, and readable bytes. */
function picked(path: string, text = "x") {
  const name = path.split("/").pop() ?? path;
  const file = new File([text], name);
  Object.defineProperty(file, "webkitRelativePath", { value: path });
  Object.defineProperty(file, "arrayBuffer", { value: async () => new TextEncoder().encode(text).buffer });
  return file;
}

function upload(files: File[]) {
  const input = screen.getByLabelText("选择文件夹");
  fireEvent.change(input, { target: { files } });
}

type Status = ReturnType<typeof status>;
const statuses = new Map<string, Status>(), requests = new Map<string, string>();
let enqueueState = "queued", executionState = "succeeded";
let view: ReturnType<typeof render>;
function sourceFor(name: string) { return `src_${name.replace(/[^a-zA-Z0-9_-]/g,"_")}`; }
function hashFor(name: string) { return name.endsWith("b.md") ? "b".repeat(64) : HASH; }
function status(job_id: string, input_ref: string, state: string, request_id: string | null = null, attempt: number | null = request_id ? 1 : null) {
  return { job_id, input_ref, state, request_id, attempt, error: state === "failed" ? "SIMULATED worker failure" : null,
    attempts: request_id ? [{ attempt, request_id, state, budget:{deadline_ms:90000,split:false,words:false}, continuation:{new_attempt_eligible_state:["failed","cancelled"].includes(state),resume_status:"NOT_SUPPORTED"} }] : [] };
}
function deferred<T>() { let resolve!: (value:T)=>void; const promise = new Promise<T>(yes=>{resolve=yes;}); return {promise,resolve}; }
async function fixture(operation: string, payload: Record<string,unknown>): Promise<unknown> {
  const body = payload.body as Record<string,unknown>;
  if (operation === "source_import") { const name=String(body.name); return {source_id:sourceFor(name),sha256:hashFor(name),duplicate:false}; }
  if (operation === "job_enqueue") { const job=String(body.job_id); statuses.set(job,status(job,String(body.input_ref),enqueueState,enqueueState==="queued"?null:"historical_request")); return {job_id:job,state:enqueueState}; }
  if (operation === "job_execution_status") { const stored=statuses.get(String(payload.job_id)); if(!stored)throw new Error("SIMULATED missing job"); return structuredClone(stored); }
  if (operation === "job_execute") {
    expect(body).toEqual({deadline_ms:90000,split:false,words:false}); expect(String(payload.request_id)).toMatch(/^folder_run_[a-zA-Z0-9_-]+$/);
    const job=String(payload.job_id), request=String(payload.request_id), wire=JSON.stringify(payload), old=statuses.get(job)!;
    if (requests.has(request)) { if(requests.get(request)!==wire)throw new ApiError(409,"different frozen payload","unavailable"); return {job_id:job,request_id:request,state:old.state,replayed:true}; }
    requests.set(request,wire);statuses.set(job,status(job,old.input_ref,executionState,request,(old.attempt??0)+1));
    return {job_id:job,request_id:request,state:"running",replayed:false};
  }
  if (operation === "job_execution_cancel") { const old=statuses.get(String(payload.job_id))!; if(payload.request_id!==old.request_id)throw new ApiError(409,"wrong cancellation request","unavailable"); statuses.set(old.job_id,status(old.job_id,old.input_ref,"cancelled",old.request_id,old.attempt)); return {job_id:old.job_id,request_id:old.request_id,cancel_requested:true}; }
  throw new Error(`Unexpected finite operation ${operation}`);
}

describe("folder ingest", () => {
  beforeEach(() => {
    bridge.call.mockReset(); bridge.open.mockReset(); statuses.clear(); requests.clear(); enqueueState="queued"; executionState="succeeded";
    bridge.call.mockImplementation(fixture);
    view = render(<FolderIngest onOpenSource={bridge.open} />);
  });

  it("queues by the full hash with the kind in the identity, and uses a stable batch id as provenance", async () => {
    upload([picked("资料/笔记/a.md"), picked("资料/说明.bin", "bytes")]);

    await waitFor(() => expect(bridge.call).toHaveBeenCalledWith("source_import", expect.objectContaining({
      body: expect.objectContaining({ name: "笔记/a.md", origin_kind: "path", origin_name: "a.md" }),
    })));
    // A03: the job id carries the kind and the full digest, not a 12-char truncation.
    expect(bridge.call).toHaveBeenCalledWith("job_enqueue", {
      body: { job_id: `folder-text-${HASH}`, kind: "text", input_ref: sourceFor("笔记/a.md") },
    });
    // A10: provenance references a stable batch id, not the folder basename, and it is shared by the batch.
    const imports = bridge.call.mock.calls.filter(([operation]) => operation === "source_import");
    const refs = imports.map(([, p]) => (p as { body: { origin_ref: string } }).body.origin_ref);
    expect(refs.every((ref) => typeof ref === "string" && ref.length > 0)).toBe(true);
    expect(new Set(refs).size).toBe(1);
    expect(refs[0]).not.toBe("资料");
    // A .bin has no mapped Core route: the original is kept, and no job is invented for it.
    expect(imports).toHaveLength(2);
    expect(bridge.call.mock.calls.filter(([operation]) => operation === "job_enqueue")).toHaveLength(1);
    expect(await screen.findByText("原件已保管，无转换通路")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("已入队 1");
    expect(screen.getByRole("status")).toHaveTextContent("仅保管 1");
  });

  it("refuses the whole submission on private state, including the root name and any case (A02)", async () => {
    upload([picked("项目/正常.md"), picked("项目/.codex/token.json")]);
    expect(await screen.findByRole("status")).toHaveTextContent("整个文件夹被拒绝");
    expect(bridge.call).not.toHaveBeenCalled();

    // Case-insensitive: `.CODEX` is the same private state on Windows.
    upload([picked("folder/OK/.CODEX/x.md")]);
    expect(await screen.findByRole("status")).toHaveTextContent("整个文件夹被拒绝");
    expect(bridge.call).not.toHaveBeenCalled();

    // The picked folder's own name being private is caught, because the visible path includes it.
    upload([picked(".codex/secret.md")]);
    expect(await screen.findByRole("status")).toHaveTextContent("整个文件夹被拒绝");
    expect(bridge.call).not.toHaveBeenCalled();
  });

  it("shows the real receipt state instead of writing every success as already-queued (A03)", async () => {
    bridge.call.mockImplementation(async (operation: string, payload: Record<string, unknown>) => {
      if (operation === "source_import") return { source_id: "src-a", sha256: HASH, duplicate: false };
      if (operation === "job_enqueue") return { job_id: (payload.body as { job_id: string }).job_id, state: "succeeded" };
      return {};
    });
    upload([picked("册/a.md")]);
    expect(await screen.findByText("已成功")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("已成功 1");
    expect(screen.getByRole("status")).not.toHaveTextContent("已入队 1");
    // A result that already succeeded is not offered for batch execution.
    expect(screen.queryByRole("button", { name: "执行本批次转换" })).not.toBeInTheDocument();
  });

  it("treats a real 409 as a conflict, not as already-queued (A03)", async () => {
    bridge.call.mockImplementation(async (operation: string) => {
      if (operation === "source_import") return { source_id: "src-a", sha256: HASH, duplicate: true };
      if (operation === "job_enqueue") throw new ApiError(409, "identity conflict", "unavailable");
      return {};
    });
    upload([picked("册/a.md")]);
    expect(await screen.findByText("作业身份冲突")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("冲突 1");
    expect(screen.getByRole("status")).not.toHaveTextContent("已在队列");
  });

  it("skips hidden and dependency paths without asking the Core", async () => {
    upload([picked("册/.env"), picked("册/node_modules/pkg/index.md"), picked("册/keep.md")]);
    expect(await screen.findByText("跳过：隐藏路径")).toBeInTheDocument();
    expect(screen.getByText("跳过：排除目录")).toBeInTheDocument();
    const imported = bridge.call.mock.calls.filter(([operation]) => operation === "source_import");
    expect(imported).toHaveLength(1);
    expect((imported[0][1] as { body: { name: string } }).body.name).toBe("keep.md");
  });

  it("refuses an original above the Core's import limit before reading it", async () => {
    const heavy = picked("册/big.pdf");
    Object.defineProperty(heavy, "size", { value: 64 * 1024 * 1024 + 1 });
    upload([heavy]);
    expect(await screen.findByText("未导入：超过大小上限")).toBeInTheDocument();
    expect(bridge.call).not.toHaveBeenCalled();
  });

  it("advances a 201-file folder across batches so none is left behind (A01)", async () => {
    const many = Array.from({ length: 201 }, (_, index) => picked(`册/f${index}.bin`));
    upload(many);

    await waitFor(() => expect(bridge.call.mock.calls.filter(([operation]) => operation === "source_import")).toHaveLength(200));
    expect(screen.getByRole("status")).toHaveTextContent("剩余 1 项待下一批");
    expect(screen.queryByText("跳过：超过本次上限")).not.toBeInTheDocument();

    await userEvent.setup().click(screen.getByRole("button", { name: /下一批（剩余 1）/ }));
    await waitFor(() => expect(bridge.call.mock.calls.filter(([operation]) => operation === "source_import")).toHaveLength(201));
    expect(screen.getByRole("status")).toHaveTextContent("全部处理完毕");
    expect(screen.queryByRole("button", { name: /下一批/ })).not.toBeInTheDocument();
  });

  it("retains uncertain enqueue identity and reconciles without another import or execute",async()=>{
    bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>)=>{
      if(op==="job_enqueue"){await fixture(op,p);throw new Error("SIMULATED lost enqueue ACK");}
      return fixture(op,p);
    });
    upload([picked("册/a.md")]);await screen.findByText("结果 UNKNOWN，待核对");
    fireEvent.click(screen.getByRole("button",{name:"读取转换状态"}));
    await screen.findByText("已入队",{exact:true});
    expect(bridge.call.mock.calls.filter(([op])=>op==="source_import")).toHaveLength(1);
    expect(bridge.call.mock.calls.filter(([op])=>op==="job_enqueue")).toHaveLength(1);
    expect(bridge.call.mock.calls.some(([op])=>op==="job_execute")).toBe(false);
  });
  it("does not claim an uncertain import was refused",async()=>{
    bridge.call.mockImplementation(async()=>{throw new Error("SIMULATED lost import ACK");});
    upload([picked("册/a.md")]);await screen.findByText("原件导入未确认",{exact:true});
    expect(screen.getByLabelText("批次真实统计")).toHaveTextContent("原件导入未确认 1 · 跳过 0");
    expect(screen.queryByText("未导入",{exact:true})).toBeNull();
    expect(bridge.call.mock.calls.some(([op])=>["job_enqueue","job_execute"].includes(op))).toBe(false);
  });
  it("executes this batch's queued jobs to a real terminal state (A06)", async () => {
    upload([picked("册/a.md")]);
    const run = await screen.findByRole("button", { name: "执行本批次转换" });
    await userEvent.setup().click(run);
    await waitFor(() => expect(bridge.call).toHaveBeenCalledWith("job_execute", { job_id: `folder-text-${HASH}`, request_id:expect.stringMatching(/^folder_run_/), body:{deadline_ms:90000,split:false,words:false} }));
    expect(await screen.findByText("已成功", { exact: true })).toBeInTheDocument();
    expect(screen.getByText(/转换终态 succeeded；原件保留/)).toBeInTheDocument();
  });

  it("stops on request and continues on the next batch (A01 stop)", async () => {
    const gate: { release?: (value: unknown) => void } = {};
    bridge.call.mockImplementation((operation: string, payload: Record<string,unknown>) => operation === "source_import"
      ? new Promise((resolve) => { gate.release = resolve; })
      : fixture(operation,payload));
    upload([picked("册/a.md"), picked("册/b.md")]);
    await waitFor(() => expect(bridge.call).toHaveBeenCalledTimes(1));
    fireEvent.click(screen.getByRole("button", { name: "停止" }));
    gate.release?.({ source_id: "src-a", sha256: HASH, duplicate: false });
    // a.md completes; b.md was not started and remains for the next batch.
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("剩余 1 项待下一批"));
    expect(bridge.call.mock.calls.filter(([operation]) => operation === "source_import")).toHaveLength(1);
  });

  it("does not claim an absolute path the browser never handed over", async () => {
    upload([picked("册/a.md")]);
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("批次处理"));
    const note = screen.getByText(/浏览器不把磁盘绝对路径交给产品/);
    expect(note).toBeInTheDocument();
    expect(note).not.toHaveTextContent("D:");
  });

  it("updates a failed row by stable key after async retry and never reimports or reenqueues", async () => {
    enqueueState="failed"; upload([picked("册/a.md")]);
    await screen.findByRole("button",{name:"重试失败项（新请求）"});
    const before=bridge.call.mock.calls.filter(([op])=>["source_import","job_enqueue"].includes(op)).length;
    await userEvent.setup().click(screen.getByRole("button",{name:"重试失败项（新请求）"}));
    await screen.findByText("已成功",{exact:true});
    expect(bridge.call.mock.calls.filter(([op])=>["source_import","job_enqueue"].includes(op))).toHaveLength(before);
    const call=bridge.call.mock.calls.find(([op])=>op==="job_execute")!;
    expect(call[1].request_id).not.toBe("historical_request");
    expect(screen.getByLabelText("批次真实统计")).toHaveTextContent("已成功 1");
  });
  it("retries only the failed sibling and retains a successful source without any new import", async () => {
    bridge.call.mockImplementation(async (op:string,p:Record<string,unknown>)=>{
      if(op==="job_enqueue") { const body=p.body as {job_id:string;input_ref:string}; const state=body.input_ref===sourceFor("b.md")?"failed":"succeeded"; statuses.set(body.job_id,status(body.job_id,body.input_ref,state,"historical_request"));return {job_id:body.job_id,state}; }
      return fixture(op,p);
    });
    upload([picked("册/a.md","first"),picked("册/b.md","second")]);
    await screen.findByRole("button",{name:"重试失败项（新请求）"});
    const successRow=screen.getByText("a.md",{exact:true}).closest("tr")!;
    expect(within(successRow).getByText("已成功",{exact:true})).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button",{name:"重试失败项（新请求）"}));
    await waitFor(()=>expect(screen.getAllByText("已成功",{exact:true})).toHaveLength(2));
    const executed=bridge.call.mock.calls.filter(([op])=>op==="job_execute");expect(executed).toHaveLength(1);expect(executed[0][1].job_id).toBe(`folder-text-${"b".repeat(64)}`);
    expect(bridge.call.mock.calls.filter(([op])=>op==="source_import")).toHaveLength(2);
    expect(bridge.call.mock.calls.filter(([op])=>op==="job_enqueue")).toHaveLength(2);
  });
  it("claims single flight synchronously for two retry clicks",async()=>{
    enqueueState="failed";upload([picked("册/a.md")]);const button=await screen.findByRole("button",{name:"重试失败项（新请求）"});
    const ack=deferred<unknown>();bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>)=>op==="job_execute"?ack.promise:fixture(op,p));
    fireEvent.click(button);fireEvent.click(button);
    await waitFor(()=>expect(bridge.call.mock.calls.filter(([op])=>op==="job_execute")).toHaveLength(1));
    const p=bridge.call.mock.calls.find(([op])=>op==="job_execute")![1];await act(async()=>{ack.resolve(await fixture("job_execute",p));});await screen.findByText("已成功",{exact:true});
  });
  it("lost ACK keeps one frozen request and same retry does not create another attempt",async()=>{
    let lost=true;bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>)=>{const result=await fixture(op,p);if(op==="job_execute"&&lost){lost=false;throw new Error("SIMULATED lost ACK after durable claim");}return result;});
    upload([picked("册/a.md")]);fireEvent.click(await screen.findByRole("button",{name:"执行本批次转换"}));
    await screen.findByRole("button",{name:"同请求重试"});const first=bridge.call.mock.calls.find(([op])=>op==="job_execute")![1];
    expect(screen.getByLabelText("选择文件夹")).toBeDisabled();fireEvent.click(screen.getByRole("button",{name:"同请求重试"}));await screen.findByText("已成功",{exact:true});
    const calls=bridge.call.mock.calls.filter(([op])=>op==="job_execute");expect(calls).toHaveLength(2);expect(calls[1][1]).toEqual(first);expect(statuses.get(String(first.job_id))?.attempt).toBe(1);
    expect(bridge.call.mock.calls.filter(([op])=>op==="source_import")).toHaveLength(1);
  });
  it("UNKNOWN can reconcile the same durable terminal without sending inference or execution again",async()=>{
    bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>)=>{const result=await fixture(op,p);if(op==="job_execute")throw new Error("lost ACK");return result;});
    upload([picked("册/a.md")]);fireEvent.click(await screen.findByRole("button",{name:"执行本批次转换"}));
    fireEvent.click(await screen.findByRole("button",{name:"核对冻结请求状态"}));await screen.findByText("已成功",{exact:true});
    expect(bridge.call.mock.calls.filter(([op])=>op==="job_execute")).toHaveLength(1);
  });
  it("wrong execute ACK keeps UNKNOWN rather than accepting a sibling receipt",async()=>{
    bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>)=>{const value=await fixture(op,p);return op==="job_execute"?{...(value as object),job_id:"wrong_job"}:value;});
    upload([picked("册/a.md")]);fireEvent.click(await screen.findByRole("button",{name:"执行本批次转换"}));await screen.findByRole("button",{name:"同请求重试"});expect(screen.queryByText("已成功",{exact:true})).not.toBeInTheDocument();
    expect(screen.getByText(/执行回执身份不匹配/)).toBeInTheDocument();
  });
  it("wrong request/source/budget readback cannot settle a frozen write",async()=>{
    bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>)=>{const value=await fixture(op,p);return op==="job_execution_status"&&requests.size?{...(value as object),input_ref:"wrong_source"}:value;});
    upload([picked("册/a.md")]);fireEvent.click(await screen.findByRole("button",{name:"执行本批次转换"}));await screen.findByRole("button",{name:"同请求重试"});expect(screen.getByText(/状态回执身份不匹配/)).toBeInTheDocument();expect(screen.queryByText("已成功",{exact:true})).not.toBeInTheDocument();
  });
  it("a rejected job or missing current eligibility never exposes a fresh execute",async()=>{
    enqueueState="rejected";upload([picked("册/a.md")]);await screen.findByText("已拒绝",{exact:true});expect(screen.queryByRole("button",{name:"重试失败项（新请求）"})).not.toBeInTheDocument();expect(screen.queryByRole("button",{name:"执行本批次转换"})).not.toBeInTheDocument();expect(bridge.call.mock.calls.filter(([op])=>op==="job_execute")).toHaveLength(0);
  });
  it("definite Core permission refusal freezes identity and offers readback rather than blind execution",async()=>{
    bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>)=>{if(op==="job_execute")throw new ApiError(403,"route denied","unavailable");return fixture(op,p);});
    upload([picked("册/a.md")]);fireEvent.click(await screen.findByRole("button",{name:"执行本批次转换"}));await screen.findByRole("button",{name:"核对冻结请求状态"});expect(screen.queryByRole("button",{name:"同请求重试"})).not.toBeInTheDocument();expect(screen.getByLabelText("选择文件夹")).toBeDisabled();
  });
  it("a typed disabled non-admission resumes the exact frozen request when enabled",async()=>{
    let disabled=true;
    bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>)=>{
      if(op==="job_execute"&&disabled){const row=statuses.get(String(p.job_id))!;const receipt={schema:"archeaxis.job-admission-refusal/v1",code:"AAK-CAP-001",job_id:p.job_id,request_id:p.request_id,input_ref:row.input_ref,kind:"text",capability:"text.extract",budget:p.body,admission_state:"NOT_ADMITTED",request_consumed:false,active_execution:false,enabled:false,same_request_retry_allowed:true} as JobAdmissionRefusal;throw new ApiError(409,"disabled","unavailable",undefined,receipt);}
      return fixture(op,p);
    });
    upload([picked("册/a.md")]);fireEvent.click(await screen.findByRole("button",{name:"执行本批次转换"}));
    const retry=await screen.findByRole("button",{name:"同请求重试"});const first=bridge.call.mock.calls.find(([op])=>op==="job_execute")![1];expect(requests.size).toBe(0);
    disabled=false;fireEvent.click(retry);await screen.findByText("已成功",{exact:true});
    const calls=bridge.call.mock.calls.filter(([op])=>op==="job_execute");expect(calls).toHaveLength(2);expect(calls[1][1]).toEqual(first);expect(statuses.get(String(first.job_id))?.attempt).toBe(1);
  });
  it("requests current Core cancellation with the exact execution identity; 202 is not terminal",async()=>{
    executionState="running";const ack=deferred<unknown>();bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>)=>op==="job_execution_cancel"?ack.promise:fixture(op,p));
    upload([picked("册/a.md")]);fireEvent.click(await screen.findByRole("button",{name:"执行本批次转换"}));await screen.findByText("作业运行中",{exact:true});fireEvent.click(screen.getByRole("button",{name:"请求取消当前转换"}));
    await waitFor(()=>expect(bridge.call.mock.calls.filter(([op])=>op==="job_execution_cancel")).toHaveLength(1));const execute=bridge.call.mock.calls.find(([op])=>op==="job_execute")![1];const cancel=bridge.call.mock.calls.find(([op])=>op==="job_execution_cancel")![1];expect(cancel).toEqual({job_id:execute.job_id,request_id:execute.request_id});
    await act(async()=>{ack.resolve({job_id:execute.job_id,request_id:execute.request_id,cancel_requested:true});});
    expect(screen.getAllByText(/取消待确认/).length).toBeGreaterThan(0);expect(screen.queryByText("已取消",{exact:true})).not.toBeInTheDocument();
    const old=statuses.get(String(execute.job_id))!;statuses.set(old.job_id,status(old.job_id,old.input_ref,"cancelled",old.request_id,old.attempt));await screen.findByText("已取消",{exact:true});expect(screen.getByLabelText("批次真实统计")).toHaveTextContent("已取消 1");
    executionState="succeeded";await waitFor(()=>expect(screen.getByRole("button",{name:"重试失败项（新请求）"})).toBeEnabled());fireEvent.click(screen.getByRole("button",{name:"重试失败项（新请求）"}));await screen.findByText("已成功",{exact:true});const calls=bridge.call.mock.calls.filter(([op])=>op==="job_execute");expect(calls).toHaveLength(2);expect(calls[1][1].request_id).not.toBe(execute.request_id);expect(bridge.call.mock.calls.filter(([op])=>op==="source_import")).toHaveLength(1);
  });
  it("cancel versus success race respects persisted success, not the cancellation ACK",async()=>{
    executionState="running";bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>)=>{if(op==="job_execution_cancel"){const old=statuses.get(String(p.job_id))!;statuses.set(old.job_id,status(old.job_id,old.input_ref,"succeeded",old.request_id,old.attempt));return {job_id:p.job_id,request_id:p.request_id,cancel_requested:true};}return fixture(op,p);});
    upload([picked("册/a.md")]);fireEvent.click(await screen.findByRole("button",{name:"执行本批次转换"}));await screen.findByText("作业运行中",{exact:true});fireEvent.click(screen.getByRole("button",{name:"请求取消当前转换"}));await screen.findByText("已成功",{exact:true});expect(screen.queryByText("已取消",{exact:true})).not.toBeInTheDocument();
  });
  it("stopping later conversions leaves the current job to settle and does not start its sibling",async()=>{
    const ack=deferred<unknown>();bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>)=>op==="job_execute"?ack.promise:fixture(op,p));upload([picked("册/a.md"),picked("册/b.md")]);
    await waitFor(()=>expect(screen.getByLabelText("批次真实统计")).toHaveTextContent("已入队 2"));fireEvent.click(screen.getByRole("button",{name:"执行本批次转换"}));await waitFor(()=>expect(bridge.call.mock.calls.filter(([op])=>op==="job_execute")).toHaveLength(1));fireEvent.click(screen.getByRole("button",{name:"停止"}));
    const p=bridge.call.mock.calls.find(([op])=>op==="job_execute")![1];await act(async()=>{ack.resolve(await fixture("job_execute",p));});await screen.findByText("已成功",{exact:true});expect(bridge.call.mock.calls.filter(([op])=>op==="job_execute")).toHaveLength(1);expect(screen.getByLabelText("批次真实统计")).toHaveTextContent("已入队 1");
  });
  it("successful locate passes real source and saved job, original-only locate carries no invented job",async()=>{
    enqueueState="succeeded";upload([picked("册/a.md"),picked("册/original.bin")]);await waitFor(()=>expect(screen.getByRole("status")).toHaveTextContent("全部处理完毕"));fireEvent.click(await screen.findByRole("button",{name:"打开成功产物与来源"}));expect(bridge.open).toHaveBeenCalledWith(sourceFor("a.md"),`folder-text-${HASH}`);fireEvent.click(screen.getByRole("button",{name:"打开保留原件"}));expect(bridge.open).toHaveBeenCalledWith(sourceFor("original.bin"),undefined);expect(bridge.call.mock.calls.filter(([op])=>op==="job_execute")).toHaveLength(0);
  });
  it("unmounted late ACK cannot change a newly mounted batch or start further conversion",async()=>{
    const ack=deferred<unknown>();bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>)=>op==="job_execute"?ack.promise:fixture(op,p));upload([picked("册/a.md")]);fireEvent.click(await screen.findByRole("button",{name:"执行本批次转换"}));await waitFor(()=>expect(bridge.call.mock.calls.filter(([op])=>op==="job_execute")).toHaveLength(1));const p=bridge.call.mock.calls.find(([op])=>op==="job_execute")![1];view.unmount();view=render(<FolderIngest onOpenSource={bridge.open}/>);await act(async()=>{ack.resolve(await fixture("job_execute",p));});expect(screen.queryByText("已成功",{exact:true})).not.toBeInTheDocument();expect(screen.queryByLabelText("批次真实统计")).not.toBeInTheDocument();
  });
});
