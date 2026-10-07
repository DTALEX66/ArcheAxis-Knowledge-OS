import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ContainerMemberChain } from "../components/ContainerMemberChain";

const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));

const member = {
  source_id: "src-member", member: "notes/index.md", origin_ref: "src-outer#notes/index.md",
  original_name: "index.md", sha256: "a".repeat(64), readable: true, job_id: "job-member",
};
const members = {
  container_source_id: "src-outer", member_count: 2, readable_count: 1, custody_only_count: 1,
  members: [member, { ...member, source_id: "src-blob", member: "opaque/blob.bin", original_name: "blob.bin", readable: false, job_id: null }],
  note: "此清单是已导入的成员，不是容器的完整目录。",
};
const reading = { source_id: "src-member", job_id: "job-member", transform_id: 7, raw_sha256: "b".repeat(64), content: "半径 6371 km 记于此处" };

describe("container member chain", () => {
  beforeEach(() => bridge.call.mockReset());

  it("names an unrecorded container instead of drawing an empty table", async () => {
    bridge.call.mockImplementation(async (operation: string) => {
      if (operation === "source_members") throw new Error("本地核心找不到 source_members 所需的对象。");
      return {};
    });
    render(<ContainerMemberChain sourceId="src-outer" />);
    await userEvent.click(screen.getByRole("button", { name: "读取成员清单" }));
    expect(await screen.findByRole("status")).toHaveTextContent("没有成员记录");
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  it("promotes only the human-selected span, with the UTF-16 offsets the Core validates", async () => {
    bridge.call.mockImplementation(async (operation: string) => {
      if (operation === "source_members") return members;
      if (operation === "source_job_transform") return reading;
      if (operation === "knowledge_from_transform") return { status: "candidate", requires_human_review: true, anchor_id: "anc_1", knowledge_id: "k_1" };
      return {};
    });
    render(<ContainerMemberChain sourceId="src-outer" />);
    await userEvent.click(screen.getByRole("button", { name: "读取成员清单" }));
    expect(await screen.findByText(/已读取容器成员清单/)).toBeInTheDocument();
    expect(screen.getByText("此清单是已导入的成员，不是容器的完整目录。")).toBeInTheDocument();
    expect(screen.getByText(/无路由可读/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "index.md" }));
    const area = (await screen.findByRole("textbox", { name: /识别结果/ })) as HTMLTextAreaElement;
    expect(area).toHaveValue("半径 6371 km 记于此处");

    area.setSelectionRange(3, 8);
    fireEvent.select(area);
    expect(await screen.findByText(/选中 5 个 UTF-16 代码单位，偏移 3–8/)).toBeInTheDocument();

    await userEvent.type(screen.getByRole("textbox", { name: /陈述/ }), "笔记声明地球半径为 6371 km。");
    await userEvent.click(screen.getByRole("button", { name: "把选中原文升为知识候选" }));

    expect(bridge.call).toHaveBeenCalledWith("knowledge_from_transform", {
      body: {
        knowledge_type: "FACTUAL_CLAIM", body: "笔记声明地球半径为 6371 km。",
        source_id: "src-member", job_id: "job-member", transform_id: 7,
        selection_start_utf16: 3, selection_end_utf16: 8, quote: "6371 ",
      },
    });
    expect(await screen.findByText(/候选 k_1 · 锚点 anc_1 · 状态 candidate · 需真人复核 true/)).toBeInTheDocument();
  });

  it("refuses to present a receipt that is not a human-review candidate as promoted", async () => {
    bridge.call.mockImplementation(async (operation: string) => {
      if (operation === "source_members") return members;
      if (operation === "source_job_transform") return reading;
      if (operation === "knowledge_from_transform") return { status: "accepted", requires_human_review: false };
      return {};
    });
    render(<ContainerMemberChain sourceId="src-outer" />);
    await userEvent.click(screen.getByRole("button", { name: "读取成员清单" }));
    await userEvent.click(screen.getByRole("button", { name: "index.md" }));
    const area = (await screen.findByRole("textbox", { name: /识别结果/ })) as HTMLTextAreaElement;
    area.setSelectionRange(3, 8);
    fireEvent.select(area);
    await userEvent.type(screen.getByRole("textbox", { name: /陈述/ }), "声明");
    await userEvent.click(screen.getByRole("button", { name: "把选中原文升为知识候选" }));
    expect(await screen.findByRole("status")).toHaveTextContent("未登记任何知识");
    expect(screen.queryByText(/候选 k_1/)).not.toBeInTheDocument();
  });
});
