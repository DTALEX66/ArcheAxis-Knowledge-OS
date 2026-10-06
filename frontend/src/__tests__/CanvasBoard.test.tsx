import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { CanvasBoard } from "../components/CanvasBoard";

// AXW-UI-804: CanvasBoard - the canvas editor. These tests pin the projection
// (nodes and only drawable edges), the identity of the edit/delete affordances,
// and that an edge naming a missing node is never drawn.
const doc = {
  nodes: [
    { id: "n1", type: "text", x: 0, y: 0, width: 100, height: 40, text: "起点" },
    { id: "n2", type: "text", x: 200, y: 0, width: 100, height: 40, text: "终点" },
  ],
  edges: [
    { id: "e1", fromNode: "n1", toNode: "n2" },
    { id: "e2", fromNode: "n1", toNode: "missing" },
  ],
};

describe("CanvasBoard", () => {
  it("renders every node text and the node/edge counts", () => {
    render(<CanvasBoard doc={doc} onChange={() => {}} />);
    expect(screen.getByText("起点")).toBeInTheDocument();
    expect(screen.getByText("终点")).toBeInTheDocument();
    expect(screen.getByText(/节点 2 · 连线 2/)).toBeInTheDocument();
  });

  it("draws an edge only when both endpoints exist", () => {
    const { container } = render(<CanvasBoard doc={doc} onChange={() => {}} />);
    // e1 has both endpoints; e2 names a missing node and must not be drawn.
    expect(container.querySelectorAll("line")).toHaveLength(1);
  });

  it("shows the empty message for an empty canvas", () => {
    render(<CanvasBoard doc={{ nodes: [], edges: [] }} onChange={() => {}} />);
    expect(screen.getByText(/空画布/)).toBeInTheDocument();
    expect(screen.getByText(/节点 0 · 连线 0/)).toBeInTheDocument();
  });

  it("removes a node together with every edge that touches it", () => {
    const onChange = vi.fn();
    render(<CanvasBoard doc={doc} onChange={onChange} />);
    fireEvent.click(screen.getByRole("button", { name: "删除 起点" }));
    const next = onChange.mock.calls[0][0];
    expect(next.nodes.map((node: { id: string }) => node.id)).toEqual(["n2"]);
    // both edges touch the removed node, so none survive.
    expect(next.edges).toEqual([]);
  });

  it("commits an edited node text on Enter", () => {
    const onChange = vi.fn();
    render(<CanvasBoard doc={doc} onChange={onChange} />);
    fireEvent.click(screen.getByRole("button", { name: "编辑 起点" }));
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: "改后" } });
    fireEvent.keyDown(textarea, { key: "Enter" });
    const next = onChange.mock.calls[0][0];
    expect(next.nodes.find((node: { id: string }) => node.id === "n1").text).toBe("改后");
  });

  it("adds a text node carrying the prompted text", () => {
    const onChange = vi.fn();
    vi.spyOn(window, "prompt").mockReturnValue("新节点");
    try {
      render(<CanvasBoard doc={{ nodes: [], edges: [] }} onChange={onChange} />);
      fireEvent.click(screen.getByRole("button", { name: "添加文本节点" }));
      const next = onChange.mock.calls[0][0];
      expect(next.nodes).toHaveLength(1);
      expect(next.nodes[0].text).toBe("新节点");
    } finally {
      vi.restoreAllMocks();
    }
  });
});
