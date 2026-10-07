import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FolderIngest } from "../components/FolderIngest";
import { ApiError } from "../api/client";

const bridge = vi.hoisted(() => ({ call: vi.fn() }));
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

describe("folder ingest", () => {
  beforeEach(() => {
    bridge.call.mockReset();
    render(<FolderIngest />);
    bridge.call.mockImplementation(async (operation: string, payload: Record<string, unknown>) => {
      if (operation === "source_import") return { source_id: `src-${(payload.body as { name: string }).name}`, sha256: HASH, duplicate: false };
      if (operation === "job_enqueue") return { job_id: (payload.body as { job_id: string }).job_id, state: "queued" };
      return {};
    });
  });

  it("queues by the full hash with the kind in the identity, and uses a stable batch id as provenance", async () => {
    upload([picked("资料/笔记/a.md"), picked("资料/说明.bin", "bytes")]);

    await waitFor(() => expect(bridge.call).toHaveBeenCalledWith("source_import", expect.objectContaining({
      body: expect.objectContaining({ name: "笔记/a.md", origin_kind: "path", origin_name: "a.md" }),
    })));
    // A03: the job id carries the kind and the full digest, not a 12-char truncation.
    expect(bridge.call).toHaveBeenCalledWith("job_enqueue", {
      body: { job_id: `folder-text-${HASH}`, kind: "text", input_ref: "src-笔记/a.md" },
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

  it("executes this batch's queued jobs to a real terminal state (A06)", async () => {
    bridge.call.mockImplementation(async (operation: string, payload: Record<string, unknown>) => {
      if (operation === "source_import") return { source_id: "src-a", sha256: HASH, duplicate: false };
      if (operation === "job_enqueue") return { job_id: (payload.body as { job_id: string }).job_id, state: "queued" };
      if (operation === "job_execute") return { state: "running" };
      if (operation === "jobs_get") return { job_id: payload.job_id, state: "succeeded" };
      return {};
    });
    upload([picked("册/a.md")]);
    const run = await screen.findByRole("button", { name: "执行本批次转换" });
    await userEvent.setup().click(run);
    await waitFor(() => expect(bridge.call).toHaveBeenCalledWith("job_execute", { job_id: `folder-text-${HASH}` }));
    expect(await screen.findByText("succeeded")).toBeInTheDocument();
    expect(screen.getByText(/转换产物已持久化，可从资料页打开/)).toBeInTheDocument();
  });

  it("stops on request and continues on the next batch (A01 stop)", async () => {
    const gate: { release?: (value: unknown) => void } = {};
    bridge.call.mockImplementation((operation: string) => operation === "source_import"
      ? new Promise((resolve) => { gate.release = resolve; })
      : Promise.resolve({ job_id: "x", state: "queued" }));
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
});
