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
    vi.unstubAllGlobals();
  });

  it("renders the three learning tabs", () => {
    render(<LearningSpace />);
    expect(screen.getByRole("heading", { name: "学习" })).toBeInTheDocument();
    expect(screen.getByText("人类学习库：安排复习、记录理解与检验表达。")).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("FSRS");
    expect(screen.getByRole("button", { name: "复习队列" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "掌握度" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "复述检验" })).toBeInTheDocument();
  });

  it("loads the FSRS review queue from the learner-state API", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/review-queue")) {
        return jsonResponse({ due_count: 1, due: [{ card_id: "due-1", due_local: "2026-08-28T08:00:00Z", due_utc: "2026-08-28T00:00:00Z", fsrs_state: "review", stability_days: 3 }] });
      }
      return jsonResponse({}, false);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<LearningSpace />);
    await waitFor(() => {
      expect(screen.getByText("当前到期 1 张卡片")).toBeInTheDocument();
      expect(screen.getByRole("option", { name: /到期卡片 1/ })).toBeInTheDocument();
    });
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/learning/review-queue"),
    );
  }, 15_000);

  it("withholds learner endpoint details from visible errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({}, false)));
    render(<LearningSpace />);

    expect(await screen.findByText(/本地数据暂时不可用/)).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("/review-queue");
    expect(document.body).not.toHaveTextContent("-> 500");
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
    await user.click(screen.getByRole("button", { name: "复述检验" }));

    await user.type(screen.getByLabelText("概念"), "BKT");
    await user.type(screen.getByLabelText("你的复述"), "BKT 是隐马尔可夫模型，有猜和滑参数。");
    await user.type(screen.getByLabelText("核对依据（已验证的资料要点）"), "BKT 是隐马尔可夫模型，掌握度是后验概率。");
    await user.click(screen.getByRole("button", { name: "评分" }));

    await waitFor(() => {
      expect(screen.getByText(/已达标/)).toBeInTheDocument();
    });
  });

  it("queries dual mastery and renders the three axes", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/review-queue")) {
        return jsonResponse({ due_count: 1, due: [{ card_id: "c1", due_local: "2026-08-28T08:00:00Z", due_utc: "2026-08-28T00:00:00Z", fsrs_state: "review", stability_days: 3 }] });
      }
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
    await user.selectOptions(screen.getByLabelText("学习卡片"), "c1");
    await user.click(screen.getByRole("button", { name: "查询" }));

    await waitFor(() => {
      expect(screen.getByLabelText("人类掌握 M3")).toBeInTheDocument();
      expect(screen.getByLabelText("机器掌握 K6")).toBeInTheDocument();
      expect(screen.getByText(/引导学习/)).toBeInTheDocument();
    });
  });
});

describe("LearningSpace loop views", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("renders quiz and path tabs", () => {
    render(<LearningSpace />);
    expect(screen.getByRole("button", { name: "练习测验" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "学习路径" })).toBeInTheDocument();
  });

  it("generates quiz items and grades MCQ", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/quiz")) {
        return jsonResponse({
          concept: "BKT",
          items: [
            { item_id: "q1", concept: "BKT", kind: "mcq", prompt: "最匹配的术语？",
              answer: "guess", distractors: ["srs", "irt"] },
          ],
        });
      }
      return jsonResponse({}, false);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<LearningSpace />);
    await user.click(screen.getByRole("button", { name: "练习测验" }));
    expect(screen.getByLabelText("概念")).toHaveValue("");
    await user.type(screen.getByLabelText("概念"), "BKT");
    await user.type(screen.getByLabelText("知识参考"), "BKT 是隐马尔可夫模型");
    await user.click(screen.getByRole("button", { name: "生成测验" }));
    expect(await screen.findByText("最匹配的术语？")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "guess" }));
    expect(screen.getByText("正确")).toBeInTheDocument();
  });

  it("builds a learning path from a prerequisite graph", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/learning-path")) {
        expect(init?.method).toBe("POST");
        return jsonResponse({
          goal: "d",
          steps: [
            { concept: "a", kind: "prerequisite_gap", reason: "先修缺口" },
            { concept: "b", kind: "must_learn", reason: "薄弱" },
            { concept: "d", kind: "must_learn", reason: "目标概念" },
          ],
        });
      }
      return jsonResponse({}, false);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<LearningSpace />);
    await user.click(screen.getByRole("button", { name: "学习路径" }));
    expect(screen.getByLabelText("目标概念")).toHaveValue("");
    expect(screen.getByLabelText("先修概念（用逗号分隔）")).toHaveValue("");
    await user.type(screen.getByLabelText("目标概念"), "d");
    await user.type(screen.getByLabelText("先修概念（用逗号分隔）"), "a, b, c");
    await user.click(screen.getByRole("button", { name: "生成路径" }));
    expect(await screen.findByText(/先修缺口/)).toBeInTheDocument();
  });

  it("submits a review outcome", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/review-outcome")) {
        return jsonResponse({
          review_id: "rv1", mistake_id: null, mastered: false,
          review_count: 1, machine_knowledge_created: false,
        });
      }
      return jsonResponse({ due_count: 1, due: [{ card_id: "card-x", due_local: "2026-08-28T08:00:00Z", due_utc: "2026-08-28T00:00:00Z", fsrs_state: "review", stability_days: 3 }] });
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<LearningSpace />);
    await user.selectOptions(await screen.findByLabelText("待复习卡片"), "card-x");
    await user.click(screen.getByRole("button", { name: "提交复习结果" }));
    expect(await screen.findByText(/已提交复习结果/)).toBeInTheDocument();
  });
});
