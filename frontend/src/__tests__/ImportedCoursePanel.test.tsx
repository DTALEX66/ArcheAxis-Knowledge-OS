import { webcrypto } from "node:crypto";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
const storage = vi.hoisted(() => ({ prepare: vi.fn(), save: vi.fn(), reopen: vi.fn(), call: vi.fn() }));
vi.mock("../presentation/importedCourseStorage", () => ({ prepareCourseImport: storage.prepare, saveCourseImport: storage.save, reopenCourseImport: storage.reopen }));
vi.mock("../api/core", () => ({ coreCommand: storage.call }));
import { ImportedCoursePanel } from "../components/ImportedCoursePanel";
import { parseOpenMaicCourse } from "../adapters/openmaicCourse";
import { fixtureBytes } from "../test/fixtures/openmaic";

const draft = () => parseOpenMaicCourse(fixtureBytes());
const saved = () => ({ document: { document_id: "doc1", version: 1 }, course: { ...draft(), status: "candidate", grounding: "external_unverified", human_review_required: true } });
beforeEach(() => {
  vi.stubGlobal("crypto", webcrypto); Object.values(storage).forEach(fn => fn.mockReset());
  storage.prepare.mockResolvedValue({ draft: draft(), requestId: "frozen1" });
  storage.save.mockResolvedValue(saved()); storage.reopen.mockResolvedValue(saved());
});
async function select() {
  const file = new File([fixtureBytes()], "manifest.json", { type: "application/json" });
  Object.defineProperty(file, "arrayBuffer", { value: async () => fixtureBytes().slice().buffer });
  await userEvent.setup().upload(screen.getByLabelText("选择课程 manifest.json"), file);
  await screen.findByRole("button", { name: "保全原件并保存课程候选" });
}
describe("optional external course import and reference practice", () => {
  it("only writes after explicit preview confirmation, uses literal text, and does not record mastery", async () => {
    render(<ImportedCoursePanel />); await select();
    expect(storage.save).not.toHaveBeenCalled();
    expect(screen.getByText(/选择来源 <script>/)).toBeInTheDocument();
    expect(document.querySelector("script")).toBeNull();
    await userEvent.setup().click(screen.getByRole("button", { name: "保全原件并保存课程候选" }));
    expect(await screen.findByText(/候选已保存并读回核对/)).toBeInTheDocument();
    expect(storage.save).toHaveBeenCalledTimes(1);
    await userEvent.setup().click(screen.getByLabelText("原件"));
    await userEvent.setup().click(screen.getByRole("button", { name: "核对课件参考答案" }));
    expect(screen.getByText(/与课件参考答案一致/)).toHaveTextContent("不代表掌握");
    expect(storage.call).not.toHaveBeenCalled();
  });
  it("invalid files show parser reason and never offer a write", async () => {
    storage.prepare.mockRejectedValue(new Error("$.scenes[0].type：不支持 slide"));
    render(<ImportedCoursePanel />);
    const file = new File(["{}"], "manifest.json", { type: "application/json" });
    Object.defineProperty(file, "arrayBuffer", { value: async () => new TextEncoder().encode("{}").buffer });
    await userEvent.setup().upload(screen.getByLabelText("选择课程 manifest.json"), file);
    expect(await screen.findByRole("alert")).toHaveTextContent("不支持 slide");
    expect(screen.queryByRole("button", { name: "保全原件并保存课程候选" })).not.toBeInTheDocument();
    expect(storage.save).not.toHaveBeenCalled();
  });
  it("unknown save results stay unresolved and retry uses the frozen selection, not a new request", async () => {
    storage.save.mockRejectedValueOnce(new Error("原件已保全；课程保存结果待核对。"));
    render(<ImportedCoursePanel />); await select();
    const user = userEvent.setup(); await user.click(screen.getByRole("button", { name: "保全原件并保存课程候选" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("待核对");
    expect(screen.queryByText(/候选已保存并读回核对/)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "同请求重试保存" }));
    await screen.findByText(/候选已保存并读回核对/);
    expect(storage.save.mock.calls[0][0]).toBe(storage.save.mock.calls[1][0]);
    expect(storage.prepare).toHaveBeenCalledTimes(1);
  });
  it("lists only on request, reads selected documents, and never presents a failed list as empty", async () => {
    render(<ImportedCoursePanel />); expect(storage.call).not.toHaveBeenCalled();
    storage.call.mockRejectedValueOnce(new Error("offline"));
    await userEvent.setup().click(screen.getByRole("button", { name: "浏览已保存文档" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("列表读取失败");
    expect(screen.queryByText("没有已保存文档。", { exact: true })).not.toBeInTheDocument();
    storage.call.mockResolvedValue({ documents: [{ document_id: "doc1", title: "外部课程候选 · 证据与来源" }], next_cursor: null });
    await userEvent.setup().click(screen.getByRole("button", { name: "浏览已保存文档" }));
    await userEvent.setup().click(await screen.findByRole("button", { name: "打开 外部课程候选 · 证据与来源" }));
    await waitFor(() => expect(storage.reopen).toHaveBeenCalledWith("doc1"));
    expect(await screen.findByText(/已从保存的原件与文档重新核对/)).toBeInTheDocument();
  });
  it("keeps a submitted save single-flight through repeated clicks", async () => {
    let complete!: (value: unknown) => void;
    storage.save.mockReturnValueOnce(new Promise(resolve => { complete = resolve; }));
    render(<ImportedCoursePanel />); await select();
    const button = screen.getByRole("button", { name: "保全原件并保存课程候选" });
    fireEvent.click(button); fireEvent.click(button);
    expect(storage.save).toHaveBeenCalledTimes(1);
    expect(screen.queryByText(/候选已保存并读回核对/)).not.toBeInTheDocument();
    complete(saved()); await screen.findByText(/候选已保存并读回核对/);
  });
  it("does not publish a late unmounted reply into a reopened panel; reselect retains the frozen request", async () => {
    let complete!: (value: unknown) => void;
    storage.save.mockReturnValueOnce(new Promise(resolve => { complete = resolve; }));
    const first = render(<ImportedCoursePanel />); await select();
    await userEvent.setup().click(screen.getByRole("button", { name: "保全原件并保存课程候选" }));
    const frozen = storage.save.mock.calls[0][0]; first.unmount();
    render(<ImportedCoursePanel />); complete(saved());
    await waitFor(() => expect(screen.queryByText(/候选已保存并读回核对/)).not.toBeInTheDocument());
    await select(); await userEvent.setup().click(screen.getByRole("button", { name: "保全原件并保存课程候选" }));
    await screen.findByText(/候选已保存并读回核对/);
    expect(storage.save.mock.calls[1][0].requestId).toBe(frozen.requestId);
  });
});
