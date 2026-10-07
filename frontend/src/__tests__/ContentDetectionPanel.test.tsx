import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ContentDetectionPanel } from "../components/ContentDetectionPanel";

const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));

const judgement = {
  params: {
    worker_structure: {
      capability: "document.detection", state: "detected", label: "xlsx", group: "office",
      model_score: 0.9995, input_sha256: "c".repeat(64),
      model: { name: "magika", revision: "standard_v3_0", model_sha256: "d".repeat(64) },
    },
  },
};

describe("content detection panel", () => {
  beforeEach(() => bridge.call.mockReset());

  it("runs a real detect job and keeps the verdict labelled as a model judgement", async () => {
    bridge.call.mockImplementation(async (operation: string) => {
      if (operation === "job_output") return { content: JSON.stringify(judgement) };
      if (operation === "jobs_get") return { state: "succeeded" };
      return { job_id: "ignored" };
    });
    render(<ContentDetectionPanel sourceId="src-1" name="field_notes" />);
    await userEvent.click(screen.getByRole("button", { name: "按字节判定内容类型（模型判定）" }));

    expect(bridge.call).toHaveBeenCalledWith("job_enqueue", {
      body: { job_id: expect.stringMatching(/^detect_/), kind: "detect", input_ref: "src-1" },
    });
    expect(bridge.call).toHaveBeenCalledWith("job_execute", {
      job_id: expect.stringMatching(/^detect_/), body: { deadline_ms: 300000 },
    });
    expect(await screen.findByRole("status")).toHaveTextContent("模型判定：xlsx · 组 office · 分值 0.9995");
    expect(screen.getByText(/分值不是准确率/)).toBeInTheDocument();
  });

  it("says the type is still unknown when the model route refuses, and shows no verdict", async () => {
    bridge.call.mockImplementation(async (operation: string) => {
      if (operation === "jobs_get") return { state: "failed" };
      return {};
    });
    render(<ContentDetectionPanel sourceId="src-2" name="mystery" />);
    await userEvent.click(screen.getByRole("button", { name: "按字节判定内容类型（模型判定）" }));
    expect(await screen.findByRole("status")).toHaveTextContent("仍按未知处理");
    expect(screen.queryByText(/模型判定：/)).not.toBeInTheDocument();
  });

  it("does not read a missing judgement out of the receipt as a verdict", async () => {
    bridge.call.mockImplementation(async (operation: string) => {
      if (operation === "job_output") return { content: JSON.stringify({ params: {} }) };
      if (operation === "jobs_get") return { state: "succeeded" };
      return {};
    });
    render(<ContentDetectionPanel sourceId="src-3" name="mystery" />);
    await userEvent.click(screen.getByRole("button", { name: "按字节判定内容类型（模型判定）" }));
    expect(await screen.findByRole("status")).toHaveTextContent("判定未完成或被拒绝");
    expect(screen.queryByText(/模型判定：/)).not.toBeInTheDocument();
  });
});
