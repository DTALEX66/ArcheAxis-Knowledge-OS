import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { coreCommand } from "../api/core";
import { BoundedJobPanel } from "../components/BoundedJobPanel";
import { FormatQualificationPanel, readFormatQualification, type FormatIdentity } from "../components/FormatQualificationPanel";

const identity: FormatIdentity = { sourceId: "source-1", sourceRevision: "a".repeat(64), jobId: "job-1", attempt: 1, jobState: "succeeded" };
function receipt(extra = {}) {
  const operation = (status: string) => ({ qualification_version: 1, status, scope: "DECLARED_SCOPE_ONLY" });
  return { schema: "archeaxis.file-format-qualification/v1", qualification_version: 1, core_version: "0.1.0",
    source_id: identity.sourceId, source_revision: identity.sourceRevision, job_id: identity.jobId, attempt: 1,
    job_state: "succeeded", execution_succeeded: true, qualification_evidence: "COMPLETE",
    operations: { store: operation("RECORDED"), preview: operation("QUALIFIED"), extract: operation("QUALIFIED"), edit: operation("UNVERIFIED"), export: operation("AVAILABLE"), roundtrip: operation("UNVERIFIED") },
    loss: { status: "unknown", reported_count: null, receipt_ref: null }, outputs: [], evidence_scope: "CONTROLLED_TEST_ONLY", ...extra };
}
describe("explicit per-file qualification", () => {
  afterEach(() => { delete window.__TAURI__; });
  it("uses the finite native command and rejects a malformed qualification DTO", async () => {
    const invoke = vi.fn().mockResolvedValue({ status: 200, body: receipt() });
    window.__TAURI__ = { core: { invoke } };
    await expect(coreCommand("source_job_format_qualification", { source_id: identity.sourceId, job_id: identity.jobId })).resolves.toEqual(receipt());
    expect(invoke).toHaveBeenCalledWith("core_command", { request: { operation: "source_job_format_qualification", payload: { source_id: identity.sourceId, job_id: identity.jobId } } });
    invoke.mockResolvedValue({ status: 200, body: receipt({ operations: {} }) });
    await expect(coreCommand("source_job_format_qualification", { source_id: identity.sourceId, job_id: identity.jobId })).rejects.toThrow();
  });
  it("opens qualification from the existing selected source/job without executing or polling it", async () => {
    const command = vi.fn().mockImplementation(async (op: string) => {
      if (op === "sources_list") return { sources: [{ source_id: identity.sourceId, source_revision: identity.sourceRevision, original_name: "controlled.docx" }] };
      if (op === "source_jobs") return { source_id: identity.sourceId, jobs: [{ job_id: identity.jobId, input_ref: identity.sourceId, kind: "office", state: "succeeded" }] };
      if (op === "jobs_get" || op === "job_execution_status") return { job_id: identity.jobId, input_ref: identity.sourceId, state: "succeeded", attempt: 1, request_id: "request-1", error: null };
      if (op === "source_job_format_qualification") return receipt();
      throw new Error(op);
    });
    render(<BoundedJobPanel command={command}/>);
    await screen.findByRole("option", { name: /controlled.docx/ });
    fireEvent.change(screen.getByLabelText("已保存来源"), { target: { value: identity.sourceId } });
    await screen.findByRole("option", { name: /office · job-1/ });
    fireEvent.change(screen.getByLabelText("来源任务"), { target: { value: identity.jobId } });
    fireEvent.click(await screen.findByRole("button", { name: "读取此文件操作回执" }));
    await screen.findAllByText("QUALIFIED");
    expect(command.mock.calls.filter(([op]) => op === "source_job_format_qualification")).toHaveLength(1);
    expect(command.mock.calls.some(([op]) => op === "job_execute")).toBe(false);
  });
  it("reads only on demand, keeps native edit/roundtrip unknown and loss unknown", async () => {
    const command = vi.fn().mockResolvedValue(receipt());
    render(<FormatQualificationPanel command={command} identity={identity} error={null}/>);
    expect(command).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "读取此文件操作回执" }));
    await screen.findAllByText("QUALIFIED");
    expect(command).toHaveBeenCalledTimes(1);
    expect(command).toHaveBeenCalledWith("source_job_format_qualification", { source_id: "source-1", job_id: "job-1" });
    expect(screen.getByText("原生编辑").nextElementSibling).toHaveTextContent("UNVERIFIED");
    expect(screen.getByText("原格式往返").nextElementSibling).toHaveTextContent("UNVERIFIED");
    expect(screen.getByText(/损失登记：未知/)).toBeInTheDocument();
  });
  it.each(["source_id", "source_revision", "job_id", "attempt", "job_state"])("rejects mismatched %s", field => {
    expect(() => readFormatQualification(receipt({ [field]: field === "attempt" ? 2 : "other" }), identity)).toThrow();
  });
  it("rejects absent attempt and incomplete six-operation evidence", () => {
    expect(() => readFormatQualification(receipt({ attempt: undefined }), identity)).toThrow();
    expect(() => readFormatQualification(receipt({ operations: {} }), identity)).toThrow();
  });
  it("does not populate a new source/job from an old response", async () => {
    let resolve!: (value: unknown) => void;
    const command = vi.fn().mockImplementation(() => new Promise(value => { resolve = value; }));
    const view = render(<FormatQualificationPanel command={command} identity={identity} error={null}/>);
    fireEvent.click(screen.getByRole("button"));
    view.rerender(<FormatQualificationPanel command={command} identity={{...identity, jobId: "job-2"}} error={null}/>);
    await act(async () => resolve(receipt()));
    expect(screen.queryByText("QUALIFIED")).not.toBeInTheDocument();
    expect(screen.getAllByText("UNVERIFIED")).toHaveLength(6);
    expect(command).toHaveBeenCalledTimes(1);
  });
  it("failed reads leave all six unknown and preserve task error", async () => {
    const command = vi.fn().mockRejectedValue(new Error("offline"));
    render(<FormatQualificationPanel command={command} identity={{...identity, jobState: "failed"}} error="malformed document"/>);
    fireEvent.click(screen.getByRole("button"));
    await screen.findByRole("alert");
    expect(screen.getAllByText("UNVERIFIED")).toHaveLength(6);
    expect(screen.getByText(/malformed document/)).toBeInTheDocument();
    await waitFor(() => expect(command).toHaveBeenCalledTimes(1));
  });
});
