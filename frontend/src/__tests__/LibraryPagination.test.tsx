import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CanonicalLibrarySpace } from "../spaces/CanonicalLibrarySpace";
import { coreCommand } from "../api/core";
vi.mock("../api/core", () => ({ coreCommand: vi.fn() }));
vi.mock("../templates/TemplateWorkspace", () => ({ TemplateLauncher: () => null }));
vi.mock("../components/FolderIngest", () => ({ FolderIngest: () => null }));
const doc = (id: string) => ({ document_id: id, source_id: null, source_revision: null, title: id, version: 1, content_sha256: "a".repeat(64) });

describe("canonical document pagination", () => {
  it("retains the first page on failure and retries the same finite cursor", async () => {
    let attempts = 0;
    vi.mocked(coreCommand).mockImplementation(async (operation, payload) => {
      if (operation === "sources_list") return { sources: [] } as never;
      if (operation === "documents_list" && !payload?.cursor) return { documents: [doc("第一页")], next_cursor: "opaque-next", snapshot_count: 2 } as never;
      if (operation === "documents_list") {
        expect(payload).toEqual({ cursor: "opaque-next" });
        if (++attempts === 1) throw new Error("temporarily offline");
        return { documents: [doc("第二页")], next_cursor: null, snapshot_count: 2 } as never;
      }
      throw new Error(operation);
    });
    render(<CanonicalLibrarySpace />);
    const more = await screen.findByRole("button", { name: "加载更多文档" });
    fireEvent.click(more);
    await screen.findByText(/更多文档读取失败/);
    expect(screen.getByRole("button", { name: "第一页 · 文档" })).toBeInTheDocument();
    fireEvent.click(more);
    await screen.findByRole("button", { name: "第二页 · 文档" });
    await waitFor(() => expect(screen.queryByRole("button", { name: "加载更多文档" })).not.toBeInTheDocument());
    expect(attempts).toBe(2);
  });
  it("refuses a repeated cursor without discarding already loaded documents", async () => {
    vi.mocked(coreCommand).mockImplementation(async operation => {
      if (operation === "sources_list") return { sources: [] } as never;
      return { documents: [doc("第一页")], next_cursor: "loop", snapshot_count: 2 } as never;
    });
    render(<CanonicalLibrarySpace />);
    fireEvent.click(await screen.findByRole("button", { name: "加载更多文档" }));
    await screen.findByText(/更多文档读取失败/);
    expect(screen.getAllByRole("button", { name: "第一页 · 文档" })).toHaveLength(1);
  });
});
