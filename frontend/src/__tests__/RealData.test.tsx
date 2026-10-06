import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { DataError, DataTable, Loading, Section } from "../components/RealData";
import { userErrorMessage } from "../presentation/labels";

// AXW-UI-804: RealData holds the shared real-data primitives every space
// renders through. These are the components that decide what a reader sees
// while a view is loading, empty, or failed, so the tests pin the visible
// label and - most importantly - that a failure body is the user-facing
// mapping rather than the raw engine string.
describe("RealData", () => {
  it("Loading names what is being loaded", () => {
    render(<Loading label="资料库" />);
    expect(screen.getByText("加载中：资料库…")).toBeInTheDocument();
  });

  it("DataError names the failing view and shows the mapped message, never the raw one", () => {
    render(<DataError label="能力目录" message="AAK-WORKER-003 raw" />);
    expect(screen.getByText("能力目录 加载失败")).toBeInTheDocument();
    // The body is exactly what the shared mapper returns for this input...
    expect(screen.getByText(userErrorMessage("AAK-WORKER-003 raw"))).toBeInTheDocument();
    // ...and the engine identifier that triggered the mapping is not surfaced.
    expect(screen.queryByText("AAK-WORKER-003 raw")).not.toBeInTheDocument();
  });

  it("DataError passes a human-readable message through unchanged", () => {
    const message = "本地核心未完成此操作";
    render(<DataError label="作业" message={message} />);
    expect(userErrorMessage(message)).toBe(message);
    expect(screen.getByText(message)).toBeInTheDocument();
  });

  it("DataTable shows the empty label when there are no rows", () => {
    render(<DataTable columns={[{ key: "name", label: "名称" }]} rows={[]} empty="暂无可显示的数据" />);
    expect(screen.getByText("暂无可显示的数据")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("DataTable renders the declared columns and every row value", () => {
    render(
      <DataTable
        columns={[
          { key: "name", label: "名称" },
          { key: "size", label: "大小" },
        ]}
        rows={[{ name: "原件", size: 42 }]}
        empty="空"
      />,
    );
    expect(screen.getByRole("columnheader", { name: "名称" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "原件" })).toBeInTheDocument();
    // A number is still projected as text, not dropped.
    expect(screen.getByRole("cell", { name: "42" })).toBeInTheDocument();
  });

  it("DataTable marks a missing cell with an em dash instead of an empty cell", () => {
    render(
      <DataTable columns={[{ key: "name", label: "名称" }, { key: "note", label: "说明" }]} rows={[{ name: "原件" }]} empty="空" />,
    );
    expect(screen.getByRole("cell", { name: "—" })).toBeInTheDocument();
  });

  it("Section renders its title as a heading with the children beneath it", () => {
    render(
      <Section title="诊断">
        <span>正文</span>
      </Section>,
    );
    expect(screen.getByRole("heading", { name: "诊断" })).toBeInTheDocument();
    expect(screen.getByText("正文")).toBeInTheDocument();
  });
});
