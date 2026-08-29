import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { VaultSpace } from "../spaces/VaultSpace";
import { ApiError } from "../api/client";
import * as api from "../api/workspace";

vi.mock("../api/workspace", () => ({
  inspectVault: vi.fn(),
  readVaultFile: vi.fn(),
  readVaultCanvas: vi.fn(),
  searchVault: vi.fn(),
  writeVaultFile: vi.fn(),
  writeVaultCanvas: vi.fn(),
  listVaultBackups: vi.fn(),
  restoreVaultBackup: vi.fn(),
}));

const mocked = vi.mocked(api);

const HASH = "c".repeat(64);

afterEach(() => {
  vi.clearAllMocks();
});

describe("VaultSpace", () => {
  it("opens a vault and lists files with kind labels", async () => {
    const user = userEvent.setup();
    mocked.inspectVault.mockResolvedValue({
      schema_version: "v1",
      root_name: "知识库",
      files: [
        { relative_path: "notes.md", kind: "markdown", file_size: 12, source_hash: HASH, mime_type: "text/markdown", frontmatter: {} },
        { relative_path: "board.canvas", kind: "canvas", file_size: 90, source_hash: HASH, mime_type: "application/json", frontmatter: {} },
      ],
      loss_report: {},
    });
    render(<VaultSpace />);

    await user.type(screen.getByRole("textbox", { name: "知识库路径" }), "D:/知识库");
    await user.click(screen.getByRole("button", { name: "打开知识库" }));

    expect(await screen.findByText("已打开知识库：知识库 · 2 个文件")).toBeInTheDocument();
    expect(screen.getByText("Markdown")).toBeInTheDocument();
    expect(screen.getByText("画布")).toBeInTheDocument();
    expect(screen.getByText("notes.md")).toBeInTheDocument();
  });

  it("reads a markdown file into the editor and saves with optimistic lock", async () => {
    const user = userEvent.setup();
    mocked.inspectVault.mockResolvedValue({
      schema_version: "v1",
      root_name: "知识库",
      files: [
        { relative_path: "notes.md", kind: "markdown", file_size: 12, source_hash: HASH, mime_type: "text/markdown", frontmatter: {} },
      ],
      loss_report: {},
    });
    mocked.readVaultFile.mockResolvedValue({
      schema_version: "v1", relative_path: "notes.md", raw_text: "# 标题\n正文", frontmatter: {}, body: "# 标题\n正文", is_canvas: false, source_hash: HASH, loss_report: {},
    });
    mocked.writeVaultFile.mockResolvedValue({
      schema_version: "v1", relative_path: "notes.md", source_hash: "d".repeat(64), expected_hash_checked: true,
    });
    render(<VaultSpace />);

    await user.type(screen.getByRole("textbox", { name: "知识库路径" }), "D:/知识库");
    await user.click(screen.getByRole("button", { name: "打开知识库" }));
    await user.click(await screen.findByText("notes.md"));

    const editor = screen.getByRole("textbox", { name: "编辑 notes.md" });
    expect(editor).toHaveValue("# 标题\n正文");
    await user.clear(editor);
    await user.type(editor, "# 已修改");
    await user.click(screen.getByRole("button", { name: "保存" }));

    await waitFor(() => expect(mocked.writeVaultFile).toHaveBeenCalledWith("D:/知识库", "notes.md", "# 已修改", HASH));
    expect(await screen.findByText("已保存；写回时使用了乐观锁校验。")).toBeInTheDocument();
  });

  it("reports an optimistic-lock conflict and asks to re-read", async () => {
    const user = userEvent.setup();
    mocked.inspectVault.mockResolvedValue({
      schema_version: "v1",
      root_name: "知识库",
      files: [
        { relative_path: "notes.md", kind: "markdown", file_size: 12, source_hash: HASH, mime_type: "text/markdown", frontmatter: {} },
      ],
      loss_report: {},
    });
    mocked.readVaultFile.mockResolvedValue({
      schema_version: "v1", relative_path: "notes.md", raw_text: "原文", frontmatter: {}, body: "原文", is_canvas: false, source_hash: HASH, loss_report: {},
    });
    mocked.writeVaultFile.mockRejectedValue(new ApiError(409, "/workspace/api/vault/write -> 409", "unavailable"));
    render(<VaultSpace />);

    await user.type(screen.getByRole("textbox", { name: "知识库路径" }), "D:/知识库");
    await user.click(screen.getByRole("button", { name: "打开知识库" }));
    await user.click(await screen.findByText("notes.md"));
    await user.click(screen.getByRole("button", { name: "保存" }));

    expect(await screen.findByText(/文件在读取后被其他程序修改；请重新读取后再保存/)).toBeInTheDocument();
  });

  it("searches the vault and opens a matching file", async () => {
    const user = userEvent.setup();
    mocked.inspectVault.mockResolvedValue({
      schema_version: "v1",
      root_name: "知识库",
      files: [
        { relative_path: "a.md", kind: "markdown", file_size: 12, source_hash: HASH, mime_type: "text/markdown", frontmatter: {} },
      ],
      loss_report: {},
    });
    mocked.searchVault.mockResolvedValue({
      schema_version: "v1", query: "target", results: [{ relative_path: "a.md", snippet: "…target 出现…", source_hash: HASH }],
    });
    mocked.readVaultFile.mockResolvedValue({
      schema_version: "v1", relative_path: "a.md", raw_text: "target", frontmatter: {}, body: "target", is_canvas: false, source_hash: HASH, loss_report: {},
    });
    render(<VaultSpace />);

    await user.type(screen.getByRole("textbox", { name: "知识库路径" }), "D:/知识库");
    await user.click(screen.getByRole("button", { name: "打开知识库" }));
    await user.type(screen.getByRole("textbox", { name: "搜索知识库" }), "target");
    await user.click(screen.getByRole("button", { name: "搜索" }));

    expect(await screen.findByText("搜索「target」：1 处匹配")).toBeInTheDocument();
    expect(await screen.findByText(/target 出现/)).toBeInTheDocument();
  });
});
