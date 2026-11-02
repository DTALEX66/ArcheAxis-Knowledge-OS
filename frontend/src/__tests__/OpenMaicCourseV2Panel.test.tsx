import { webcrypto } from "node:crypto";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
const storage = vi.hoisted(() => ({ prepare: vi.fn(), save: vi.fn(), reopen: vi.fn(), preserve: vi.fn(), call: vi.fn() }));
vi.mock("../presentation/importedCourseStorage", () => ({ prepareCourseImport: storage.prepare,
  saveCourseImport: storage.save, reopenCourseImport: storage.reopen, preserveCourseOriginal: storage.preserve }));
vi.mock("../api/core", () => ({ coreCommand: storage.call }));
import { ImportedCoursePanel } from "../components/ImportedCoursePanel";
import { parseOpenMaicCourseV2 } from "../adapters/openmaicCourseV2";
import { fixture13Bytes } from "../test/fixtures/openmaicV2";

beforeEach(() => { vi.stubGlobal("crypto", webcrypto); Object.values(storage).forEach(fn => fn.mockReset()); });
async function select() {
  const data = fixture13Bytes(), file = new File([data], "manifest.json", { type: "application/json" });
  Object.defineProperty(file, "arrayBuffer", { value: async () => data.slice().buffer });
  await userEvent.setup().upload(screen.getByLabelText("选择课程 manifest.json"), file);
}
describe("limited offline v2 course view", () => {
  it("plays a positioned text slide followed by quiz feedback without a Core write", async () => {
    storage.prepare.mockResolvedValue({ draft: parseOpenMaicCourseV2(fixture13Bytes()), requestId: "preview" });
    render(<ImportedCoursePanel />); await select();
    expect(await screen.findByText("核对原件 & 来源")).toBeVisible();
    expect(screen.getByLabelText("文本幻灯片")).toBeVisible();
    expect(document.querySelector("script, img, iframe")).toBeNull();
    const user = userEvent.setup(); await user.click(screen.getByRole("button", { name: "下一节" }));
    await user.click(screen.getByLabelText("原件"));
    await user.click(screen.getByRole("button", { name: "核对课件参考答案" }));
    expect(screen.getByText(/与课件参考答案一致/)).toHaveTextContent("不代表掌握");
    await user.click(screen.getByRole("button", { name: "上一节" }));
    await user.click(screen.getByRole("button", { name: "下一节" }));
    expect(screen.getByLabelText("原件")).toBeChecked();
    expect(storage.call).not.toHaveBeenCalled();
    expect(screen.getByText(/作答暂不保存，也不记录掌握/)).toBeInTheDocument();
  });
  it("offers explicit original custody for unsupported inputs without creating a candidate", async () => {
    storage.prepare.mockRejectedValue(new Error("unsupported media"));
    storage.preserve.mockResolvedValue({ sourceId: "source1", sha256: "a".repeat(64) });
    render(<ImportedCoursePanel />); await select();
    await userEvent.setup().click(await screen.findByRole("button", { name: "仅保全课程原件" }));
    expect(await screen.findByText(/原件已保全并读回核对/)).toHaveTextContent("未创建课程");
    expect(storage.preserve).toHaveBeenCalledTimes(1);
    expect(storage.save).not.toHaveBeenCalled();
  });
  it("records a version-bound answer and reads it again after remount without replay", async () => {
    const course = { ...parseOpenMaicCourseV2(fixture13Bytes()), schema: "archeaxis.imported-course/v2" };
    const saved = { document: { document_id: "doc_1", version: 1, content_sha256: "a".repeat(64) }, course };
    storage.prepare.mockResolvedValue({ draft: course, requestId: "preview" });
    storage.save.mockResolvedValue(saved); storage.reopen.mockResolvedValue(saved);
    let activity: any, attemptId = "", submission: any;
    storage.call.mockImplementation(async (op: string, payload: any) => {
      if (op === "learning_provider_activity_create") {
        activity = payload.body;
        return { schema: "archeaxis.provider-learning-activity/v1", activity, duplicate: false,
          material_status: "current", question_binding: "client_declared_unverified", provider_identity: "adapter_declared_unverified", independent_mastery: "not_established" };
      }
      if (op === "learning_provider_attempt_start") {
        attemptId = payload.body.attempt_id;
        return { schema: "archeaxis.provider-learning-attempt/v1", activity_id: activity.activity_id, attempt_id: attemptId,
          state: "pending", origin_restore_epoch: "epoch", duplicate: false, material_status: "current" };
      }
      if (op === "learning_provider_attempt_submit") {
        submission = payload.body;
        return { schema: "archeaxis.provider-learning-result/v1", activity_id: activity.activity_id, attempt_id: attemptId, ...submission,
          duplicate: false, material_status: "current", question_binding: "client_declared_unverified", provider_result_verification: "unverified_client_report", independent_mastery: "not_established" };
      }
      if (op === "learning_provider_activity_get") return { schema: "archeaxis.provider-learning-history/v1", activity,
        question_binding: "client_declared_unverified", provider_identity: "adapter_declared_unverified", provider_result_verification: "unverified_client_report",
        independent_mastery: "not_established", material_status: "current", next_cursor: null,
        attempts: [{ attempt_id: attemptId, state: "submitted", origin_restore_epoch: "epoch", client_event_id: submission.client_event_id,
          result: submission, client_cancel_id: null, created_at: "now", completed_at: "now" }] };
      if (op === "documents_list") return { documents: [{ document_id: "doc_1", title: "外部课程" }], next_cursor: null };
      throw new Error(op);
    });
    const first = render(<ImportedCoursePanel />); await select();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "保全原件并保存课程候选" }));
    await user.click(await screen.findByRole("button", { name: "下一节" }));
    await user.click(screen.getByRole("button", { name: "开始记录本次作答" }));
    await screen.findByText(/已开始记录/);
    await user.click(screen.getByLabelText("原件"));
    await user.click(screen.getByRole("button", { name: "保存作答" }));
    expect(await screen.findByText(/本次作答已保存并读回核对/)).toHaveTextContent("未建立独立掌握");
    expect(submission.provider_correct).toBeNull();
    first.unmount(); render(<ImportedCoursePanel />);
    await user.click(screen.getByRole("button", { name: "浏览已保存文档" }));
    await user.click(await screen.findByRole("button", { name: "打开 外部课程" }));
    await user.click(await screen.findByRole("button", { name: "下一节" }));
    await user.click(screen.getByRole("button", { name: "读取已保存作答" }));
    expect(await screen.findByText(/以下记录按尝试编号分页/)).toHaveTextContent("不是供体评分或独立掌握");
    expect(storage.call.mock.calls.filter(([op]) => op === "learning_provider_attempt_submit")).toHaveLength(1);
  });
});
