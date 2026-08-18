import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LearningSpace } from "../spaces/LearningSpace";

function jsonResponse(data: unknown, ok = true) {
  return {
    ok,
    status: ok ? 200 : 500,
    json: async () => data,
  } as Response;
}

describe("LearningSpace", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the three learning tabs", () => {
    render(<LearningSpace />);
    expect(screen.getByRole("heading", { name: "Learning" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "复习队列" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "掌握度" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Teach-Back" })).toBeInTheDocument();
  });

  it("loads the FSRS review queue from the learner-state API", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/review-queue")) {
        return jsonResponse({ due_count: 7, due: [] });
      }
      return jsonResponse({}, false);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<LearningSpace />);
    await waitFor(() => {
      expect(screen.getByText("当前到期 7 张卡片")).toBeInTheDocument();
    });
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/learning/review-queue"),
    );
  });

  it("submits a teach-back and shows rubric scores", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/teach-back")) {
        expect(init?.method).toBe("POST");
        return jsonResponse({
          record_id: "tb-1",
          concept: "BKT",
          evaluation: {
            accuracy: 0.8, coverage: 1.0, paraphrase: 0.5, organization: 0.3,
            overall: 0.76, passes: true,
            missing_terms: [], extra_claims: [],
          },
        });
      }
      return jsonResponse({}, false);
    });
    vi.stubGlobal("fetch", fetchMock);

    const user = userEvent.setup();
    render(<LearningSpace />);
    await user.click(screen.getByRole("button", { name: "Teach-Back" }));

    await user.type(screen.getByLabelText("概念"), "BKT");
    await user.type(screen.getByLabelText("你的复述"), "BKT 是隐马尔可夫模型，有猜和滑参数。");
    await user.type(screen.getByLabelText("参考答案"), "BKT 是隐马尔可夫模型，掌握度是后验概率。");
    await user.click(screen.getByRole("button", { name: "评分" }));

    await waitFor(() => {
      expect(screen.getByText(/达到 M3-解释/)).toBeInTheDocument();
    });
  });

  it("queries dual mastery and renders the three axes", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/mastery/")) {
        return jsonResponse({
          card_id: "c1",
          state: {
            node_id: "c1",
            human: { level: "M3", label: "M3 EXPLAIN" },
            machine: { level: "K6", label: "K6 VERIFIED" },
            evidence: "current",
            action: "teach_human",
            delta: 3,
          },
          signal: {},
        });
      }
      return jsonResponse({}, false);
    });
    vi.stubGlobal("fetch", fetchMock);

    const user = userEvent.setup();
    render(<LearningSpace />);
    await user.click(screen.getByRole("button", { name: "掌握度" }));
    await user.type(screen.getByLabelText("卡片 ID"), "c1");
    await user.click(screen.getByRole("button", { name: "查询" }));

    await waitFor(() => {
      expect(screen.getByLabelText("human M3")).toBeInTheDocument();
      expect(screen.getByLabelText("machine K6")).toBeInTheDocument();
      expect(screen.getByText(/教你/)).toBeInTheDocument();
    });
  });
});
