import {afterEach, beforeEach, expect, it, vi} from "vitest";
import {act, render, screen, within} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {coreCommand} from "../api/core";
import {ApiError, createApiClient} from "../api/client";
import {DiagnosticCenter, DiagnosticCenterTrigger, DiagnosticConsole} from "../components/DiagnosticConsole";
import {beginDiagnosticObservation, recordDiagnosticFailure, resetDiagnostics, resumeDiagnostics, suspendDiagnostics} from "../presentation/diagnostics";
import {coreFailureReason, userErrorMessage} from "../presentation/labels";

beforeEach(resetDiagnostics);
afterEach(() => {delete window.__TAURI__; vi.restoreAllMocks(); vi.unstubAllGlobals();});

it("automatically records a real bridge failure without changing the request, retrying, opening a dialog or moving focus", async () => {
  const invoke = vi.fn().mockResolvedValue({status:409, body:{}});
  window.__TAURI__ = {core:{invoke}};
  const payload = {document_id:"private-document", body:{text:"private-unsaved-text"}};
  const user = userEvent.setup();
  render(<><button>继续编辑</button><DiagnosticCenterTrigger/><DiagnosticCenter/></>);
  const editor = screen.getByRole("button", {name:"继续编辑"});
  editor.focus();
  await act(async () => {await expect(coreCommand("document_draft", payload)).rejects.toMatchObject({status:409, code:"unavailable"});});
  expect(invoke).toHaveBeenCalledTimes(1);
  expect(invoke).toHaveBeenCalledWith("core_command", {request:{operation:"document_draft", payload}});
  expect(editor).toHaveFocus();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", {name:"运行诊断"}));
  const dialog = screen.getByRole("dialog", {name:"运行诊断"});
  expect(dialog).toHaveTextContent("保存文档：冲突");
  expect(dialog).not.toHaveTextContent(/private-document|private-unsaved-text/);
  expect(dialog.querySelector("details")?.open).toBe(false);
  expect(dialog.querySelector("summary")?.textContent).not.toMatch(/\d{4}-\d{2}-\d{2}T/);
});

it("records HTTP failures without retaining endpoint, token, body or arbitrary error messages", async () => {
  const fetch = vi.fn().mockResolvedValue({ok:false, status:503});
  vi.stubGlobal("fetch", fetch);
  render(<DiagnosticConsole/>);
  const client = createApiClient("http://private-endpoint.invalid", "private-token", ["workspace:write"]);
  await act(async () => {await expect(client.write("/private/path", {text:"private-body"}, "private-request")).rejects.toMatchObject({status:503});});
  expect(fetch).toHaveBeenCalledTimes(1);
  const console = screen.getByLabelText("诊断控制台");
  expect(console).toHaveTextContent("连接本地服务");
  expect(console).not.toHaveTextContent(/private-endpoint|private-token|private-body|private-request|private\/path/);
});

it.each([401, 403, 404, 429, 500, 422])("keeps a failed command's status and operation in diagnostics while its message is plain Chinese (%s)", async status => {
  const invoke = vi.fn().mockResolvedValue({status, body:{private:"private-response-body"}});
  window.__TAURI__ = {core:{invoke}};
  const error = await coreCommand("document_get", {document_id:"private-document"}).catch(value => value);
  expect(error).toBeInstanceOf(ApiError);
  if (!(error instanceof ApiError)) throw new Error("Expected ApiError");
  expect(error.status).toBe(status);
  expect(error.code).toBe(status === 401 || status === 403 ? "unauthorized" : "unavailable");
  expect(error.message).toMatch(/[\u3400-\u9fff]/);
  expect(error.message).not.toMatch(/本地核心|document_get|HTTP|\d{3}|private/);
  expect(invoke).toHaveBeenCalledTimes(1);
  render(<DiagnosticConsole/>);
  const console = screen.getByLabelText("诊断控制台");
  expect(console).toHaveTextContent("document_get");
  expect(console).toHaveTextContent(String(status));
  expect(console).not.toHaveTextContent(/private-document|private-response-body/);
});

it("drops late native and JSON failures after a workspace generation changes", async () => {
  let finish!: (value: unknown) => void;
  window.__TAURI__ = {core:{invoke:vi.fn().mockImplementation(() => new Promise(resolve => {finish = resolve;}))}};
  const native = coreCommand("documents_list");
  resetDiagnostics();
  finish({status:404, body:{}});
  await expect(native).rejects.toMatchObject({status:404});
  let failJson!: (reason: unknown) => void;
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ok:true, json:() => new Promise((_resolve, reject) => {failJson = reject;})}));
  const request = createApiClient("http://example.invalid", "").request("/data");
  await vi.waitFor(() => expect(failJson).toBeTypeOf("function"));
  resetDiagnostics();
  failJson(new SyntaxError("private-json-body"));
  await expect(request).rejects.toThrow("private-json-body");
  render(<DiagnosticConsole/>);
  expect(screen.getByLabelText("诊断控制台")).toHaveTextContent("暂无诊断记录");
});

it("coalesces repeat polling failures and keeps the log isolated while recovery is pending", () => {
  const error = Object.freeze(new ApiError(503, "private-error-text", "backend_starting"));
  const observed = beginDiagnosticObservation();
  recordDiagnosticFailure("sources_list", error, observed);
  recordDiagnosticFailure("sources_list", error, observed);
  suspendDiagnostics();
  recordDiagnosticFailure("sources_list", error, observed);
  resumeDiagnostics();
  recordDiagnosticFailure("sources_list", error, observed);
  render(<DiagnosticConsole/>);
  const console = screen.getByLabelText("诊断控制台");
  expect(console).toHaveTextContent("近30秒内重复2次");
  expect(console).toHaveTextContent("共 1 条记录");
  expect(console).not.toHaveTextContent("private-error-text");
  expect(within(console).getAllByRole("listitem")).toHaveLength(1);
});

it("returns a late HTTP transport failure without placing it in a new workspace log", async () => {
  let rejectFetch!: (reason: unknown) => void;
  const fetch = vi.fn().mockImplementation(() => new Promise((_resolve, reject) => {rejectFetch = reject;}));
  vi.stubGlobal("fetch", fetch);
  const request = createApiClient("http://private-endpoint.invalid", "private-token").request("/private/path");
  resetDiagnostics();
  rejectFetch(new Error("private-transport-message"));
  await expect(request).rejects.toMatchObject({status:0, code:"offline"});
  expect(fetch).toHaveBeenCalledTimes(1);
  render(<DiagnosticConsole/>);
  expect(screen.getByLabelText("诊断控制台")).toHaveTextContent("暂无诊断记录");
});

it("does not log a successful request as a failure", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ok:true, json:async () => ({kept:"original"})}));
  await expect(createApiClient("http://example.invalid", "").request("/data")).resolves.toEqual({kept:"original"});
  render(<DiagnosticConsole/>);
  expect(screen.getByLabelText("诊断控制台")).toHaveTextContent("暂无诊断记录");
});

it("describes verified refusal semantics before a generic status classification", () => {
  expect(coreFailureReason({status:409, jobAdmission:{schema:"archeaxis.job-admission-refusal/v1", admission_state:"NOT_ADMITTED", enabled:false, active_execution:false}})).toContain("本次没有开始");
  expect(coreFailureReason({status:403, execution:{execution_state:"EXECUTED_BUT_WITHHELD", answer_published:false}})).toContain("AI 已处理");
  expect(coreFailureReason({status:403, machineAdmission:{schema:"archeaxis.context-admission-refusal/v1", execution_state:"NOT_EXECUTED", prior_request_execution:"UNVERIFIED"}})).toContain("先前请求的结果仍需查询");
  expect(coreFailureReason({status:503, machineFailure:{reason_code:"MODEL_CALL_TIMEOUT", execution_state:"UNVERIFIED", answer_published:false}})).toContain("当前结果尚未确认");
});

it.each(["读取失败：TypeError at Reader.tsx:42", "错误位置 C:\\private\\file.py:19", "任务 client_request_id 无效", "执行失败：Traceback", "出错：`code()`"])("keeps mixed Chinese technical errors out of ordinary messages: %s", message => {
  expect(userErrorMessage(message)).toBe("本地数据暂时不可用，请稍后重试或打开运行诊断。");
});
