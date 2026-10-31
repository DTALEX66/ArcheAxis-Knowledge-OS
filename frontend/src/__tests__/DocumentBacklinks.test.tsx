import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DocumentBacklinks } from "../components/DocumentBacklinks";

const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));

const center = { document_id: "doc.center", version: 3, content_sha256: "a".repeat(64) };
const snapshot = (id: string, version: number) => ({ document_id: id, version, content_sha256: "b".repeat(64) });
const node = (document_id: string, version: number, status: "resolved" | "unavailable" = "resolved") => ({ key: `${document_id}@${version}`, reference: { kind: "document", document_id, version }, status, object: status === "resolved" ? { title: document_id } : null });
const edge = (id: string, document_id: string, version: number, direction: "backlink" | "outgoing") => ({ id, from: `${document_id}@${version}`, to: "doc.center@3", direction, relation: { id: `relation_${id}`, kind: "related", label: `说明 ${id}`, target: { kind: "document", document_id: "doc.center", version: 3 } }, source_snapshot: snapshot(document_id, version) });
const nodes = [node(center.document_id, center.version), node("doc.peer", 2), node("doc.out", 2), node("doc.gone", 2, "unavailable")];
const projection = (overrides: Record<string, unknown> = {}) => ({
  schema: "archeaxis.relation-projection/v1", snapshot_sha256: "c".repeat(64), center,
  nodes, edges: [edge("peer", "doc.peer", 2, "backlink"), edge("out", "doc.out", 2, "outgoing"), edge("gone", "doc.gone", 2, "backlink")],
  unsupported_sources: [], scan: { scanned: 3, next_cursor: null, complete: true }, derived_only: true, ...overrides,
});

beforeEach(() => bridge.call.mockReset());
afterEach(() => vi.clearAllMocks());

describe("DocumentBacklinks", () => {
  it("reads the pinned projection only on request and shows incoming references without outgoing ones", async () => {
    const user = userEvent.setup();
    const open = vi.fn();
    bridge.call.mockResolvedValue(projection());
    render(<DocumentBacklinks document={center} onOpenReference={open} />);

    expect(bridge.call).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "读取反向链接" }));

    expect(bridge.call).toHaveBeenCalledWith("document_graph", { document_id: "doc.center", version: 3 });
    expect(await screen.findByText("来源 doc.peer · v2")).toBeInTheDocument();
    expect(screen.queryByText("来源 doc.out · v2")).not.toBeInTheDocument();
    expect(screen.getByText("扫描当前来源版本 3 项；这一范围扫描完成；已显示 2 条反链。")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /打开来源固定版本 doc.peer · v2/ }));
    expect(open).toHaveBeenCalledWith({ kind: "document", document_id: "doc.peer", version: 2 });
    expect(screen.getByText("来源对象不可用或身份不符；未替换为最新对象。")).toBeInTheDocument();
  });

  it("refuses a projection whose center is another version instead of showing it as this page", async () => {
    const user = userEvent.setup();
    bridge.call.mockResolvedValue(projection({ center: { ...center, version: 2 } }));
    render(<DocumentBacklinks document={center} />);

    await user.click(screen.getByRole("button", { name: "读取反向链接" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("反链读取失败；未显示为空或全库结论");
    expect(screen.queryByText("来源 doc.peer · v2")).not.toBeInTheDocument();
    expect(screen.queryByText(/没有反链记录/)).not.toBeInTheDocument();
  });

  it("keeps an unfinished scan open and never turns it into an empty-library claim", async () => {
    const user = userEvent.setup();
    bridge.call
      .mockResolvedValueOnce(projection({ edges: [], scan: { scanned: 1, next_cursor: "cursor-1", complete: false } }))
      .mockResolvedValueOnce(projection({ edges: [edge("peer", "doc.peer", 2, "backlink")], scan: { scanned: 2, next_cursor: null, complete: false } }));
    render(<DocumentBacklinks document={center} />);

    await user.click(screen.getByRole("button", { name: "读取反向链接" }));
    expect(await screen.findByText("扫描当前来源版本 1 项；扫描尚未完成，不能断言全库无反链；已显示 0 条反链。")).toBeInTheDocument();
    expect(screen.getByText("此页没有反链记录；扫描未完成。")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "读取下一页反链" }));
    expect(bridge.call).toHaveBeenLastCalledWith("document_graph", { document_id: "doc.center", version: 3, cursor: "cursor-1" });
    expect(await screen.findByText("来源 doc.peer · v2")).toBeInTheDocument();
    expect(screen.getByText("扫描当前来源版本 2 项；扫描尚未完成，不能断言全库无反链；已显示 1 条反链。")).toBeInTheDocument();
  });
});
