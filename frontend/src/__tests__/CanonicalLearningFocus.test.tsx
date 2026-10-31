/**
 * Target: frontend/src/__tests__/CanonicalLearningFocus.test.tsx
 * SYNTHETIC Core fixtures, using the same persisted course/assessment identities
 * as LearningPracticeJourney.test.tsx. Real journey and review components;
 * no component, focus handler or global-event dispatch is mocked.
 * This does not qualify native persistence, installed runtime or Owner acceptance.
 * Read snapshots before the parent's active-prop fix (2026-10-22):
 * LearningPracticeJourney.test.tsx SHA256 a802f66ac67b7697d90af35771a1def292224b0a9a177473eae9705604494974
 * CanonicalLearningJourneySpace.tsx SHA256 e7ea99b9780338c1620bfb6d4af6c4ba40fec7efed0953d063c9ec6792eaca98
 * CanonicalLearningSpace.tsx SHA256 1399d41bf2055d7e6e62793a59b4377ee3cd3b2d87a5e642077869d63e97f56c
 */
import { webcrypto } from "node:crypto";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { CanonicalLearningJourneySpace } from "../spaces/CanonicalLearningJourneySpace";

const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));
const itemKey = "course:course-exact:artifact:lesson-exact";
const knowledgeId = "knowledge-exact";
const assessment = {
  item_key: itemKey, assessment_id: "assessment-exact",
  knowledge_id: knowledgeId, knowledge_version: knowledgeId,
  question: "解释同一来源的证据", content: "同一来源核对正文",
  source_id: "source-exact", anchor_id: "anchor-exact",
};

beforeEach(() => {
  vi.stubGlobal("crypto", webcrypto);
  bridge.call.mockReset();
  bridge.call.mockImplementation(async (operation: string, payload: Record<string, unknown> = {}) => {
    switch (operation) {
      case "course_list": return { items: [], next_cursor: null };
      case "learning_items": return { items: [{ item_key: itemKey, next_review: "2026-10-12T08:00:00Z" }] };
      case "learning_state":
        expect(payload.item_key).toBe(itemKey);
        return {
          item_key: itemKey,
          learner: { assessment, references: [{ knowledge_id: knowledgeId, active: true }] },
          machine: { status: "not_recorded" },
        };
      case "learning_history":
        expect(payload.item_key).toBe(itemKey);
        return { item_key: itemKey, events: [] };
      // No mutation, generation, model request or substituted identity is
      // silently accepted while changing a presentation slot.
      default: throw new Error(`unconfigured synthetic Core operation: ${operation}`);
    }
  });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it("SYNTHETIC UI06 clears global and local focus when switching to course sources, then restores the same unsent draft", async () => {
  const focusEvents: unknown[] = [];
  const observeFocus = (event: Event) => { focusEvents.push((event as CustomEvent).detail); };
  window.addEventListener("archeaxis-learning-focus", observeFocus);
  try {
    render(<CanonicalLearningJourneySpace pageId="06" initialItemKey={itemKey} />);
    const user = userEvent.setup();
    const answer = await screen.findByRole("textbox", { name: "本次答案" });
    const review = screen.getByRole("region", { name: "学习" });
    const navigation = screen.getByRole("navigation", { name: "学习内容导航" });
    const draft = "  保留未提交的答案\n第二行也不改写  ";
    fireEvent.change(answer, { target: { value: draft } });
    await user.click(screen.getByRole("button", { name: "查看答案与核对内容" }));
    await user.click(screen.getByRole("radio", { name: "回答正确" }));
    await user.selectOptions(screen.getByRole("combobox", { name: "学习者自评" }), "3");

    await user.click(screen.getByRole("button", { name: "进入聚焦模式" }));
    expect(screen.getByRole("button", { name: "退出聚焦模式" })).toHaveAttribute("aria-pressed", "true");
    expect(review).toHaveAttribute("data-focus", "true");
    expect(focusEvents).toEqual([true]);

    await user.click(within(navigation).getByRole("button", { name: "课程来源" }));
    expect(screen.getByRole("region", { name: "课程来源选择" })).toBeVisible();
    await waitFor(() => expect(focusEvents).toEqual([true, false]));
    expect(review).toHaveAttribute("data-focus", "false");
    expect(review).not.toBeVisible();
    expect(answer).toBeInTheDocument();
    expect(answer).toHaveValue(draft);

    await user.click(within(navigation).getByRole("button", { name: "学习路径" }));
    expect(screen.getByRole("button", { name: "进入聚焦模式" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.queryByRole("button", { name: "退出聚焦模式" })).toBeNull();
    expect(screen.getByRole("region", { name: "学习" })).toBe(review);
    expect(screen.getByRole("textbox", { name: "本次答案" })).toBe(answer);
    expect(answer).toBeVisible();
    expect(answer).toHaveValue(draft);
    expect(screen.getByRole("radio", { name: "回答正确" })).toBeChecked();
    expect(screen.getByRole("combobox", { name: "学习者自评" })).toHaveValue("3");
    expect(screen.getByRole("button", { name: "已显示核对内容" })).toBeVisible();
    expect(focusEvents).toEqual([true, false]);
    expect(bridge.call.mock.calls.some(([operation]) => [
      "learning_review", "assessment_create", "learning_reference", "course_from_knowledge",
      "knowledge_review", "machine_answer", "teaching_create",
    ].includes(operation))).toBe(false);
  } finally {
    window.removeEventListener("archeaxis-learning-focus", observeFocus);
  }
});
