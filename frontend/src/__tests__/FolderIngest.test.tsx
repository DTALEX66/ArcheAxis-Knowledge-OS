import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
  render(<FolderIngest />);
  const input = screen.getByLabelText("选择文件夹");
  fireEvent.change(input, { target: { files } });
}

describe("folder ingest", () => {
  beforeEach(() => {
    bridge.call.mockReset();
    bridge.call.mockImplementation(async (operation: string, payload: Record<string, unknown>) => {
      if (operation === "source_import") return { source_id: `src-${(payload.body as { name: string }).name}`, sha256: HASH, duplicate: false };
      if (operation === "job_enqueue") return { job_id: (payload.body as { job_id: string }).job_id };
      return {};
    });
  });

  it("names the folder in the provenance and queues by the hash the Core returned", async () => {
    upload([picked("资料/笔记/a.md"), picked("资料/说明.bin", "bytes")]);

    await waitFor(() => expect(bridge.call).toHaveBeenCalledWith("source_import", {
      body: { name: "笔记/a.md", content_base64: btoa("x"), origin_kind: "path", origin_ref: "资料", origin_name: "a.md" },
    }));
    expect(bridge.call).toHaveBeenCalledWith("job_enqueue", {
      body: { job_id: `folder-${HASH.slice(0, 12)}`, kind: "text", input_ref: "src-笔记/a.md" },
    });
    // A .bin has no mapped Core route: the original is kept, and no job is invented for it.
    expect(bridge.call.mock.calls.filter(([operation]) => operation === "job_enqueue")).toHaveLength(1);
    expect(await screen.findByText("原件已保管，无转换通路")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("已入队 1");
    expect(screen.getByRole("status")).toHaveTextContent("仅保管 1");
  });

  it("refuses the whole folder when private state is inside it, importing nothing", async () => {
    upload([picked("项目/正常.md"), picked("项目/.codex/token.json")]);

    expect(await screen.findByRole("status")).toHaveTextContent("整个文件夹被拒绝");
    expect(bridge.call).not.toHaveBeenCalled();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("counts a Core 409 as already queued rather than as a failure", async () => {
    bridge.call.mockImplementation(async (operation: string) => {
      if (operation === "source_import") return { source_id: "src-a", sha256: HASH, duplicate: true };
      if (operation === "job_enqueue") throw new ApiError(409, "版本已变化，请保留当前草稿并重新读取。", "unavailable");
      return {};
    });
    upload([picked("册/a.md")]);

    expect(await screen.findByText("已在队列中")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("已在队列 1");
    expect(screen.getByRole("status")).not.toHaveTextContent("入队被拒 1");
    expect(screen.getByText(/同哈希原件已存在/)).toBeInTheDocument();
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

  it("states the per-run file limit instead of silently dropping the rest", async () => {
    const many = Array.from({ length: 201 }, (_, index) => picked(`册/f${index}.bin`));
    upload(many);

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("共 201 项"));
    expect(bridge.call.mock.calls.filter(([operation]) => operation === "source_import")).toHaveLength(200);
    expect(await screen.findByText("跳过：超过本次上限")).toBeInTheDocument();
  });

  it("stops on request and marks what it did not start", async () => {
    // The first original is held mid-import so the stop click lands while the run is in flight.
    const gate: { release?: (value: unknown) => void } = {};
    bridge.call.mockImplementation((operation: string) => operation === "source_import"
      ? new Promise((resolve) => { gate.release = resolve; })
      : Promise.resolve({ job_id: `folder-${HASH.slice(0, 12)}` }));
    upload([picked("册/a.md"), picked("册/b.md")]);

    await waitFor(() => expect(bridge.call).toHaveBeenCalledTimes(1));
    fireEvent.click(screen.getByRole("button", { name: "停止" }));
    gate.release?.({ source_id: "src-a", sha256: HASH, duplicate: false });

    expect(await screen.findByText("跳过：未开始")).toBeInTheDocument();
    expect(bridge.call.mock.calls.filter(([operation]) => operation === "source_import")).toHaveLength(1);
  });

  it("does not claim an absolute path the browser never handed over", async () => {
    upload([picked("册/a.md")]);
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("清点完成"));
    expect(screen.getByRole("status")).not.toHaveTextContent("D:");
    const note = screen.getByText(/浏览器不把磁盘绝对路径交给产品/);
    expect(note).toBeInTheDocument();
  });
});
