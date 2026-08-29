import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { IntakeSpace } from "../spaces/IntakeSpace";
import * as api from "../api/workspace";

vi.mock("../api/workspace", () => ({
  intakeUrl: vi.fn(),
  intakeUpload: vi.fn(),
  startBatchImport: vi.fn(),
  getBatchStatus: vi.fn(),
  pauseBatch: vi.fn(),
  resumeBatch: vi.fn(),
  shutdownBatch: vi.fn(),
}));

const mocked = vi.mocked(api);

afterEach(() => {
  vi.clearAllMocks();
  vi.useRealTimers();
});

describe("IntakeSpace", () => {
  it("imports a URL and renders the multi-format receipt", async () => {
    const user = userEvent.setup();
    mocked.intakeUrl.mockResolvedValue({
      source_type: "web",
      requires_human_review: false,
      format: "html",
      engine: "safe-http+newspaper4k",
      content_preview: "article body",
      char_count: 120,
      raw_sha256: "a".repeat(64),
    });
    render(<IntakeSpace />);

    await user.type(screen.getByRole("textbox", { name: "网页地址" }), "https://example.com/article");
    await user.click(screen.getByRole("button", { name: "导入网页" }));

    expect(await screen.findByText("网页导入完成：120 字符")).toBeInTheDocument();
    expect(screen.getByText("HTML 网页")).toBeInTheDocument();
    expect(screen.getByText("safe-http+newspaper4k")).toBeInTheDocument();
    expect(screen.getAllByText("120 字符", { exact: false }).length).toBeGreaterThan(0);
  });

  it("refuses an empty URL with a product message", async () => {
    const user = userEvent.setup();
    render(<IntakeSpace />);

    await user.click(screen.getByRole("button", { name: "导入网页" }));
    expect(screen.getByText("请输入要导入的网页地址")).toBeInTheDocument();
    expect(mocked.intakeUrl).not.toHaveBeenCalled();
  });

  it("surfaces a conversion failure as an error instead of partial truth", async () => {
    const user = userEvent.setup();
    mocked.intakeUrl.mockRejectedValue(new Error("net unreachable"));
    render(<IntakeSpace />);

    await user.type(screen.getByRole("textbox", { name: "网页地址" }), "https://example.com/broken");
    await user.click(screen.getByRole("button", { name: "导入网页" }));

    expect(await screen.findByText(/本地数据暂时不可用/)).toBeInTheDocument();
    expect(screen.queryByText("网页导入完成")).not.toBeInTheDocument();
  });

  it("starts a batch import and renders progress with failures", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime.bind(vi) });
    mocked.startBatchImport.mockResolvedValue({
      schema_version: "v1",
      batch_id: "ui-batch-1",
      state: "running",
      total: 2,
      completed: 0,
      failed: 0,
      skipped: 0,
      created_at: "2026-08-29T00:00:00Z",
      results: {},
    });
    mocked.getBatchStatus.mockResolvedValue({
      schema_version: "v1",
      batch_id: "ui-batch-1",
      state: "finished",
      total: 2,
      completed: 1,
      failed: 1,
      skipped: 0,
      created_at: "2026-08-29T00:00:00Z",
      results: {
        "ok.md": { status: "completed", result_digest: "converted:x" },
        "bad.canvas": { status: "failed", error: "bad.canvas: invalid JSON Canvas" },
      },
    });
    render(<IntakeSpace />);

    await user.type(screen.getByRole("textbox", { name: "目录路径" }), "D:/资料/课程");
    await user.click(screen.getByRole("button", { name: "开始批量导入" }));

    await waitFor(() => expect(mocked.startBatchImport).toHaveBeenCalledTimes(1));
    expect(screen.getByText(/批量导入已启动：共 2 个文件/)).toBeInTheDocument();

    await vi.advanceTimersByTimeAsync(2000);
    expect(await screen.findByText(/批量导入已完成：成功 1 · 失败 1/)).toBeInTheDocument();
    expect(screen.getByText(/bad.canvas：bad.canvas: invalid JSON Canvas/)).toBeInTheDocument();
  });

  it("pauses, resumes and safely stops a running batch", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime.bind(vi) });
    mocked.startBatchImport.mockResolvedValue({
      schema_version: "v1",
      batch_id: "ui-batch-2",
      state: "running",
      total: 3,
      completed: 1,
      failed: 0,
      skipped: 0,
      created_at: "2026-08-29T00:00:00Z",
      results: {},
    });
    mocked.getBatchStatus.mockResolvedValue({
      schema_version: "v1",
      batch_id: "ui-batch-2",
      state: "paused",
      total: 3,
      completed: 1,
      failed: 0,
      skipped: 0,
      created_at: "2026-08-29T00:00:00Z",
      results: {},
    });
    mocked.pauseBatch.mockResolvedValue({
      schema_version: "v1",
      batch_id: "ui-batch-2",
      state: "paused",
      total: 3,
      completed: 1,
      failed: 0,
      skipped: 0,
      created_at: "2026-08-29T00:00:00Z",
      results: {},
    });
    mocked.shutdownBatch.mockResolvedValue({
      schema_version: "v1",
      batch_id: "ui-batch-2",
      state: "shutdown",
      total: 3,
      completed: 1,
      failed: 0,
      skipped: 0,
      created_at: "2026-08-29T00:00:00Z",
      results: {},
    });
    render(<IntakeSpace />);

    await user.type(screen.getByRole("textbox", { name: "目录路径" }), "D:/资料/课程");
    await user.click(screen.getByRole("button", { name: "开始批量导入" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "暂停" })).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "暂停" }));
    expect(mocked.pauseBatch).toHaveBeenCalledWith("ui-batch-2");

    await user.click(screen.getByRole("button", { name: "安全停止" }));
    expect(mocked.shutdownBatch).toHaveBeenCalledWith("ui-batch-2");
  });
});
