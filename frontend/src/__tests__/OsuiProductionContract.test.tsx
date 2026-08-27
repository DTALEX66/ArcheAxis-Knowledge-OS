import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { App } from "../app/App";
import { SPACES } from "../spaces/spaces";
import { LearningSpace } from "../spaces/LearningSpace";
import userEvent from "@testing-library/user-event";

describe("OSUI v3 production contract", () => {
  it("uses Chinese-first names for every primary product space", () => {
    expect(SPACES.map((space) => space.label)).toEqual([
      "工作台",
      "资料库",
      "证据",
      "学习",
      "机器知识",
      "设置",
    ]);
  });

  it("renders the Archive Desk workbench instead of a generic status dashboard", () => {
    render(<App />);

    expect(document.querySelector(".archive-desk-shell")).toBeInTheDocument();
    expect(document.querySelector(".workbench-hero")).toBeInTheDocument();
    expect(document.querySelector(".evidence-flow")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "原件、主张与证据，留在同一个可审查的工作面。" })).toBeInTheDocument();
  });

  it("makes every Workbench next action operable", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: "查看原件与锚点" }));
    expect(screen.getByRole("heading", { name: "原件库" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "工作台" }));
    await user.click(screen.getByRole("button", { name: "检查证据生命周期" }));
    expect(screen.getByRole("heading", { name: "证据账本" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "工作台" }));
    expect(screen.getByRole("link", { name: "处理任务与回执" })).toHaveAttribute("href", "#activity-dock");
  });

  it("does not expose the former mixed-language primary labels", () => {
    render(<App />);

    for (const leaked of ["Workspace", "Library", "Evidence", "Learning", "AI Assets", "Settings"]) {
      expect(screen.queryByRole("button", { name: leaked })).not.toBeInTheDocument();
    }
    expect(document.body).not.toHaveTextContent("浏览器开发模式（Web development mode）");
  });

  it("keeps visual lesson and spatial memory designs reachable as honest planning surfaces", async () => {
    const user = userEvent.setup();
    render(<LearningSpace />);

    await user.click(screen.getByRole("button", { name: "视觉课件" }));
    expect(screen.getByRole("heading", { name: "视觉课件工作室" })).toBeInTheDocument();
    expect(document.querySelector(".lesson-studio")).toBeInTheDocument();
    expect(screen.getByText("播放未开放")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "空间记忆" }));
    expect(screen.getByRole("heading", { name: "空间记忆" })).toBeInTheDocument();
    expect(document.querySelector(".spatial-blueprint")).toBeInTheDocument();
    expect(screen.getByText("文字等价路线")).toBeInTheDocument();
  });
});
