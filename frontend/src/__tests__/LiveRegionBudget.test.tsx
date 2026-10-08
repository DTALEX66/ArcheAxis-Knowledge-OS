// @vitest-environment jsdom
// UI-11y-02 (finding 2): one effective announce path per broadcast event.
//
// What is pinned here, and why it is not a number chosen to satisfy itself:
//   * a broadcast event (a load, an action's success, an action's failure) must reach assistive
//     tech through AT MOST ONE live region, and must still reach it — so every case asserts both
//     the bound and the announced text;
//   * persisted readouts, chunk-load placeholders and static advisories are read again by the
//     screen reader on every re-render of the surface that hosts them, so they carry no live role
//     and stay plain text labelled in context;
//   * the pre-existing rule that a classified `state-reason` is never a live region
//     (CoreFailureStates) is preserved, not re-litigated.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { webcrypto } from "node:crypto";
import { ApiError } from "../api/client";
import * as workspaceApi from "../api/workspace";
import { ExchangeSpace } from "../spaces/ExchangeSpace";
import { CanonicalLibrarySpace } from "../spaces/CanonicalLibrarySpace";
import { CanonicalLearningSpace } from "../spaces/CanonicalLearningSpace";
import { CanonicalCapabilitiesSpace } from "../spaces/CanonicalCapabilitiesSpace";
import { JobContent } from "../components/JobContent";
import { TranscriptionCues, utf8Sha256 } from "../components/TranscriptionCues";
import { ContentDetectionPanel } from "../components/ContentDetectionPanel";

const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));
vi.mock("../api/workspace", () => ({
  exportExchange: vi.fn(),
  verifyExchange: vi.fn(),
  importExchange: vi.fn(),
}));
const exchangeApi = vi.mocked(workspaceApi);

/**
 * Everything an assistive technology treats as a live region: an implicit live role, or an
 * aria-live announcement that has not been explicitly switched off.
 */
function liveRegions(root: ParentNode = document): HTMLElement[] {
  return Array.from(root.querySelectorAll<HTMLElement>(
    '[role="status"], [role="alert"], [role="log"], [role="timer"], [role="marquee"], [aria-live]:not([aria-live="off"])',
  ));
}

/** The regions that could speak `sentence` — the per-event bound, which is the actual invariant. */
function announcersOf(sentence: string, root: ParentNode = document): HTMLElement[] {
  return liveRegions(root).filter((region) => region.textContent?.includes(sentence));
}

function describeRegions(root: ParentNode = document): string[] {
  return liveRegions(root).map((node) => `${node.tagName}[role=${node.getAttribute("role")}]::${(node.textContent ?? "").slice(0, 40)}`);
}

/** A promise the test controls, so a loading state can be observed instead of raced. */
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

const FAILURE_CLASSES: Array<[string, ApiError]> = [
  ["离线", new ApiError(0, "请在本地桌面应用打开此内容。", "offline")],
  ["权限", new ApiError(403, "本地核心拒绝了此操作的身份。", "unauthorized")],
  ["冲突", new ApiError(409, "版本已变化，请保留当前草稿并重新读取。", "unavailable")],
];

const hash = "a".repeat(64);
const source = { source_id: "src_test", source_revision: hash, sha256: hash, original_name: "样板.txt", imported_at: "2026-10-05" };
const document_ = {
  document_id: "doc_test", source_id: source.source_id, source_revision: hash, title: source.original_name, version: 1,
  editor_json: { type: "doc", content: [{ type: "paragraph", attrs: { block_id: "p1" }, content: [{ type: "text", text: "已保存笔记" }] }] },
  text_projection: "已保存笔记", content_sha256: hash, blocks: [],
};

afterEach(() => {
  vi.clearAllMocks();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("Exchange page announce budget", () => {
  beforeEach(() => {
    vi.stubGlobal("crypto", webcrypto);
    bridge.call.mockReset();
  });

  it("reports nothing until an action starts, then announces each Exchange outcome through one region", async () => {
    const gate = deferred<{ destination: string; item_count: number; manifest_sha256: string }>();
    exchangeApi.exportExchange.mockReturnValue(gate.promise);
    render(<ExchangeSpace />);

    // No action has been taken: the page holds no live region at all.
    expect(liveRegions()).toHaveLength(0);

    await userEvent.setup().click(screen.getByRole("button", { name: "导出" }));
    // The loading state is announced once — never once per status element.
    expect(liveRegions()).toHaveLength(1);
    expect(liveRegions()[0]).toHaveTextContent("正在导出交换包…");

    gate.resolve({ destination: "D:/data/exchange/course", item_count: 42, manifest_sha256: "e".repeat(64) });
    await screen.findByText("已导出 42 项知识交换包");
    expect(liveRegions()).toHaveLength(1);
    expect(liveRegions()[0]).toHaveTextContent("已导出 42 项知识交换包");
    // The persisted export receipt stays readable but adds no second announcement.
    const receipt = screen.getByRole("heading", { name: "交换" }).parentElement!.querySelector('[aria-label="导出回执"]')!;
    expect(liveRegions().some((region) => region.contains(receipt))).toBe(false);
  });

  it("announces a successful verification once and keeps the persisted verify receipt out of the live region", async () => {
    exchangeApi.verifyExchange.mockResolvedValue({ valid: true, verified_items: 5 });
    render(<ExchangeSpace />);
    await userEvent.setup().click(screen.getByRole("button", { name: "验证" }));

    await screen.findByText("交换包验证通过：清单与全部文件哈希一致。");
    expect(liveRegions()).toHaveLength(1);

    const verifyReceipt = screen.getByText(/^验证结果：/);
    expect(verifyReceipt).toHaveTextContent("通过 · 5 项");
    expect(verifyReceipt.getAttribute("role")).toBeNull();
    expect(liveRegions().some((region) => region.contains(verifyReceipt))).toBe(false);
  });

  it.each(FAILURE_CLASSES)("announces an Exchange %s failure exactly once, class included", async (_label, error) => {
    exchangeApi.verifyExchange.mockRejectedValue(error);
    render(<ExchangeSpace />);
    await userEvent.setup().click(screen.getByRole("button", { name: "验证" }));

    // Before this change a failed Exchange action produced NO announcement at all: the catch wrote
    // only the error card, which carries no live role.
    const announced = await screen.findByText(new RegExp(`^${_label}：`));
    expect(liveRegions()).toHaveLength(1);
    expect(liveRegions()[0]).toContainElement(announced);
  });

  it("does not leave a stale success region behind when the action after it fails", async () => {
    exchangeApi.exportExchange.mockResolvedValue({ destination: "D:/data/exchange/course", item_count: 3, manifest_sha256: "e".repeat(64) });
    render(<ExchangeSpace />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "导出" }));
    await screen.findByText("已导出 3 项知识交换包");
    expect(liveRegions()).toHaveLength(1);

    exchangeApi.verifyExchange.mockRejectedValue(new ApiError(409, "版本已变化，请保留当前草稿并重新读取。", "unavailable"));
    await user.click(screen.getByRole("button", { name: "验证" }));
    await screen.findByText(/^冲突：/);
    // One region total: the earlier success sentence is gone rather than living on beside the failure.
    expect(liveRegions()).toHaveLength(1);
    expect(liveRegions()[0]).not.toHaveTextContent("已导出 3 项知识交换包");
  });

  it("announces a missing workspace name without adding a region for it", async () => {
    render(<ExchangeSpace />);
    await userEvent.setup().click(screen.getByRole("button", { name: "创建工作区" }));
    await screen.findByText("请输入新工作区名称。");
    expect(liveRegions()).toHaveLength(1);
  });
});

describe("Library page announce budget", () => {
  const libraryFixture = () => {
    bridge.call.mockImplementation(async (operation: string, payload: Record<string, unknown>) => {
      switch (operation) {
        case "sources_list": return { sources: [source] };
        case "documents_list": return { documents: [document_] };
        case "source_original": return { source_id: source.source_id, name: source.original_name, media_type: "text/plain", sha256: hash, content_base64: Buffer.from("原文样板").toString("base64") };
        case "anchors_list": return { anchors: [] };
        case "source_jobs": return { source_id: String(payload.source_id), jobs: [] };
        case "capabilities_list": return { capabilities: [] };
        case "document_get": return document_;
        default: throw new Error(String(operation));
      }
    });
  };

  beforeEach(() => {
    vi.stubGlobal("crypto", webcrypto);
    bridge.call.mockReset();
  });

  it("announces the library read as it starts and leaves no live region once it is ready", async () => {
    const gate = deferred<{ sources: typeof source[] }>();
    bridge.call.mockImplementation((operation: string) => {
      if (operation === "sources_list") return gate.promise;
      if (operation === "documents_list") return Promise.resolve({ documents: [] });
      if (operation === "capabilities_list" || operation === "source_jobs" || operation === "anchors_list") return Promise.resolve({ capabilities: [], jobs: [], anchors: [] });
      throw new Error(String(operation));
    });
    render(<CanonicalLibrarySpace />);

    // The page's own outcome region is the single loading announcement.
    expect(liveRegions()).toHaveLength(1);
    expect(liveRegions()[0]).toHaveTextContent("正在读取资料…");

    gate.resolve({ sources: [] });
    await waitFor(() => expect(liveRegions()).toHaveLength(0));
  });

  it("never runs the loading announcement and the ready state at the same time", async () => {
    libraryFixture();
    let peak = 0;
    const { rerender } = render(<CanonicalLibrarySpace />);
    for (let tick = 0; tick < 8; tick += 1) {
      await Promise.resolve();
      rerender(<CanonicalLibrarySpace />);
      peak = Math.max(peak, liveRegions().length);
    }
    await screen.findByRole("button", { name: "样板.txt" });
    expect(peak).toBeLessThanOrEqual(1);
  });

  it.each(FAILURE_CLASSES)("announces a %s library read exactly once and keeps the classified reason plain", async (label, error) => {
    bridge.call.mockRejectedValue(error);
    render(<CanonicalLibrarySpace />);

    await screen.findByText(/资料暂时无法读取，请检查本地核心。/);
    expect(liveRegions()).toHaveLength(1);
    // The classified reason stays readable-but-not-live, exactly as CoreFailureStates pins it:
    // promoting it would make one failed read announce twice.
    const reason = screen.getByText(new RegExp(`^${label}：`));
    expect(reason).toHaveClass("state-reason");
    expect(reason.hasAttribute("role")).toBe(false);
    expect(liveRegions().some((region) => region.contains(reason))).toBe(false);
  });

  it("announces reading a document-with-unverified-original once, not twice", async () => {
    // The libraryFixture deliberately lets the original's digest disagree with the bound source
    // revision, so opening the document lands in the "关联原件未完成核验" branch. That is the real
    // page state which used to speak the same fact twice: the page outcome region announced the
    // unfinished check while a persistent pane statement about the very same check sat in its own
    // live region beside it.
    libraryFixture();
    render(<CanonicalLibrarySpace />);
    await userEvent.setup().click(await screen.findByRole("button", { name: "样板.txt · 文档" }));
    await screen.findByText("文档已读取；关联原件未完成核验，仍可编辑保存文档。");

    // The page outcome speaks exactly once, and the pane's persistent statement about the same fact is
    // readable but carries no live role.
    expect(announcersOf("关联原件未完成核验")).toHaveLength(1);
    const statement = screen.getByText(/原件读取失败、身份不匹配或未绑定到此文档版本/);
    expect(statement.hasAttribute("role")).toBe(false);
    expect(liveRegions().some((region) => region.contains(statement))).toBe(false);
    // This state used to render more live regions than there were events to report.
    expect(liveRegions().length).toBeLessThanOrEqual(2);
  });

  it("keeps one live region per sub-surface that owns a result, and none per placeholder", async () => {
    libraryFixture();
    render(<CanonicalLibrarySpace />);
    await userEvent.setup().click(await screen.findByRole("button", { name: "样板.txt · 文档" }));
    await screen.findByRole("textbox", { name: "文档草稿" });

    // Measured owners of a live region in this state: the Library page's own outcome region, the
    // document editor's save state, and the check panel's own read result. Three sub-surfaces, three
    // events, three regions — and no more. Before this change the same page also made the chunk-load
    // placeholder and the duplicate pane statement live, i.e. five regions for three events.
    expect(liveRegions().length).toBeLessThanOrEqual(3);
    // The direct statement of "not spammed": no sentence is carried by two live regions at once.
    const spoken = describeRegions().map((entry) => entry.split("::")[1] ?? "");
    expect(new Set(spoken).size).toBe(spoken.length);
    for (const region of liveRegions()) {
      expect(region.textContent).not.toMatch(/正在载入文档编辑器|正在载入 PDF 阅读器/);
      expect(region.textContent).not.toMatch(/原件读取失败、身份不匹配或未绑定到此文档版本/);
    }
    // Each owner's own event is still announced exactly once.
    expect(announcersOf("文档已读取")).toHaveLength(1);
  });
});

describe("Conversion surface announce budget", () => {
  beforeEach(() => {
    vi.stubGlobal("crypto", webcrypto);
    bridge.call.mockReset();
  });

  it("announces one failed conversion through a single region, with the advisories as plain text", async () => {
    bridge.call.mockImplementation(async (operation: string, payload: Record<string, unknown>) => {
      switch (operation) {
        case "capabilities_list": return { capabilities: [] };
        case "source_jobs": return { source_id: String(payload.source_id), jobs: [] };
        case "job_enqueue": return { job_id: (payload.body as Record<string, unknown>).job_id };
        case "job_execute": return {};
        case "jobs_get": return { state: "failed", error_code: "AAK-WORKER-003" };
        default: throw new Error(String(operation));
      }
    });
    // 600s of audio at the declared realtime factor is far above the single-job ceiling, so the ceiling
    // advisory renders — it used to be a second live region on the same surface, next to the split
    // readout that repeats what the round message already said.
    render(<JobContent sourceId="src_asr" name="sample.wav" mediaDurationSeconds={600} />);
    const advisory = await screen.findByText(/已超过单作业上限/);
    expect(advisory.hasAttribute("role")).toBe(false);
    expect(liveRegions()).toHaveLength(0);

    await userEvent.setup().click(screen.getByRole("button", { name: /^切分执行/ }));
    // The round's own sentence is the single announcement; nothing else on the surface goes live.
    expect(liveRegions()).toHaveLength(1);
    await screen.findByText(/分段转写未完成|第 1 次未覆盖整段录音/);
    expect(liveRegions()).toHaveLength(1);
  });

  it("states split progress as text but announces it once, from the round message", async () => {
    render(<TranscriptionCues proof={{
      sourceId: "s", revision: hash, jobId: "successful-job", attempt: 2, resultSha256: "b".repeat(64),
      durationMs: 2000, cues: [{ start_ms: 100, end_ms: 1000, text: "数值37" }],
      pipeline: { windows: { status: "partial", windows_expected: 4, windows_present: 2, windows_missing: [2, 3] } },
    }} />);

    const partial = screen.getByText(/分段尚未全部完成/);
    expect(partial.hasAttribute("role")).toBe(false);
    expect(liveRegions()).toHaveLength(0);
    expect(bridge.call).not.toHaveBeenCalled();
  });

  it("quotes a citation result once, from the panel's own region, without re-announcing partial coverage", async () => {
    const partialSplitProof = {
      sourceId: "s", revision: hash, jobId: "successful-job", attempt: 2, resultSha256: "b".repeat(64),
      durationMs: 2000, cues: [{ start_ms: 100, end_ms: 1000, text: "数值37" }],
      pipeline: { windows: { status: "partial", windows_expected: 4, windows_present: 2, windows_missing: [2, 3] } },
    };
    bridge.call.mockResolvedValue({
      anchor_id: "a", source_id: "s", source_revision: hash, location_status: "located",
      position: JSON.stringify({
        type: "time", job_id: "successful-job", attempt: 2, cue_index: 0, start_ms: 100, end_ms: 1000,
        result_sha256: "b".repeat(64), checksum: await utf8Sha256("数值37"),
      }),
      checksum: await utf8Sha256("数值37"),
    });
    render(<TranscriptionCues proof={partialSplitProof} />);
    expect(liveRegions()).toHaveLength(0);

    await userEvent.setup().click(screen.getByRole("button", { name: "引用时间段" }));
    await screen.findByText(/识别忠实度仍需独立核验/);
    // The cite result is the one announcement; the partial-coverage fact stays on the reading surface
    // as text, because it describes the receipt rather than something that just happened.
    expect(liveRegions()).toHaveLength(1);
    expect(liveRegions()[0]).toHaveTextContent("识别忠实度仍需独立核验");
    expect(screen.getByText(/分段尚未全部完成/).hasAttribute("role")).toBe(false);
  });

  it("keeps the content-detection message and the verdict readout mutually exclusive", async () => {
    bridge.call.mockImplementation(async (operation: string) => {
      if (operation === "job_enqueue") return { job_id: "detect_1" };
      if (operation === "job_execute") return {};
      if (operation === "jobs_get") return { state: "succeeded" };
      if (operation === "job_output") {
        throw new Error("unreadable");
      }
      throw new Error(String(operation));
    });
    render(<ContentDetectionPanel sourceId="src_unknown" name="mystery.bin" />);
    expect(liveRegions()).toHaveLength(0);
    await userEvent.setup().click(screen.getByRole("button", { name: /按字节判定内容类型/ }));
    await screen.findByText(/内容判定未完成或被拒绝/);
    // One region for the refusal, and the verdict readout cannot be live at the same time.
    expect(liveRegions()).toHaveLength(1);
  });
});

// UI-11y-02 (finding 1): the reading surface carries a human-readable summary; the untouched
// payload travels only through the existing RawReceiptButton -> DiagnosticConsole channel.
describe("raw payloads stay off the reading surface", () => {
  beforeEach(() => {
    vi.stubGlobal("crypto", webcrypto);
    bridge.call.mockReset();
  });

  it("summarises the review history and publishes the untouched readback to the diagnostic console", async () => {
    const history = { events: [{ event_id: "e1", rating: 3 }] };
    bridge.call.mockImplementation(async (operation: string) => {
      if (operation === "learning_items") return { items: [{ item_key: "a1", next_review: null }] };
      if (operation === "learning_state") return {
        item_key: "a1",
        learner: { assessment: { assessment_id: "assess", question: "实际问题", content: "绑定修订中的核对内容", knowledge_version: "kv" } },
        machine: { status: "not_recorded" },
      };
      if (operation === "learning_history") return history;
      throw new Error(String(operation));
    });
    const { container } = render(<CanonicalLearningSpace />);
    await userEvent.setup().click(await screen.findByRole("button", { name: "a1" }));

    const recordRegion = await screen.findByText("历史与回执");
    expect(recordRegion.parentElement?.querySelector("pre")).toBeNull();
    expect(recordRegion.parentElement?.parentElement).toHaveTextContent("已读回 1 条复习事件记录。");

    const debug = vi.spyOn(console, "debug").mockImplementation(() => {});
    await userEvent.setup().click(screen.getByRole("button", { name: /复习历史与 Core 提交回执/ }));
    expect(debug.mock.calls.some(([, label, payload]) => label === "复习历史与 Core 提交回执" && JSON.stringify(payload) === JSON.stringify(history))).toBe(true);
    debug.mockRestore();
    // Nothing resembling the payload's JSON reached the rendered page.
    expect(container.textContent).not.toMatch(/"event_id"/);
    expect(container.querySelectorAll("pre")).toHaveLength(0);
  });

  it("publishes the Core handshake readback instead of printing it under the summary", async () => {
    const observation = { capability: "machine.answer", health: "handshake_ready", enabled: false };
    bridge.call.mockResolvedValue({ capabilities: [observation] });
    const { container } = render(<CanonicalCapabilitiesSpace onNavigate={vi.fn()} />);
    await screen.findByText(/已读取当前 Core worker 握手/);
    await userEvent.setup().click(screen.getByRole("button", { name: /CAP-0050/ }));

    // The human-readable summary is still on the reading surface...
    expect(screen.getByText(/连接\/权限/)).toHaveTextContent("已禁用");
    expect(screen.getByText(/连接\/权限/)).toHaveTextContent("handshake_ready");
    // ...and the raw dump that used to sit under it is gone.
    const details = screen.getByRole("article", { name: "能力详情" });
    expect(details.querySelectorAll("pre")).toHaveLength(0);
    expect(details.querySelectorAll("details")).toHaveLength(0);

    const debug = vi.spyOn(console, "debug").mockImplementation(() => {});
    await userEvent.setup().click(screen.getByRole("button", { name: /Core 握手原始读回 · machine\.answer/ }));
    expect(debug.mock.calls.some(([, label, payload]) => label === "Core 握手原始读回 · machine.answer" && JSON.stringify(payload) === JSON.stringify(observation))).toBe(true);
    debug.mockRestore();
    expect(container.textContent).not.toMatch(/"health"\s*:/);
  });
});
