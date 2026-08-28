import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LibrarySpace } from "../spaces/LibrarySpace";
import { EvidenceSpace } from "../spaces/EvidenceSpace";
import { AiAssetsSpace } from "../spaces/AiAssetsSpace";
import { SettingsSpace } from "../spaces/SettingsSpace";
import { WorkspaceSpace } from "../spaces/WorkspaceSpace";
import { ActivityDock } from "../components/ActivityDock";
import { Inspector } from "../components/Inspector";

const runtime = vi.hoisted(() => ({
  listLibraryAssets: vi.fn(), downloadLibraryAsset: vi.fn(),
  listEvidenceAnchors: vi.fn(), listEvidenceBundles: vi.fn(), getEvidenceBundleInspection: vi.fn(),
  listResearchCandidates: vi.fn(), approveResearchCandidate: vi.fn(),
  getMachineKnowledge: vi.fn(), listMachineKnowledgeCandidates: vi.fn(),
  approveMachineKnowledge: vi.fn(), deprecateMachineKnowledge: vi.fn(),
  getSetupStatus: vi.fn(), preflightSetup: vi.fn(), initializeSetup: vi.fn(), createBackup: vi.fn(), verifyBackup: vi.fn(),
  getHome: vi.fn(), getActivity: vi.fn(), getActivityObject: vi.fn(), getDelivery: vi.fn(),
  dispatchDelivery: vi.fn(), retryFailedDelivery: vi.fn(), retryDesktopBackend: vi.fn(), resetRuntimeClient: vi.fn(),
}));
vi.mock("../api/workspace", () => runtime);

describe("six-space real command loops", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("projects release, capabilities, counts, and recent activity on Workspace", async () => {
    runtime.getHome.mockResolvedValue({
      release: { version: "0.6.7", status: "unreleased", public: false },
      counts: {
        research: { candidate: 2 }, jobs: { succeeded: 3 }, outbox: { pending: 1 },
        learning: { approved: 2 }, machine_knowledge: { candidate: 1 },
      },
      capabilities: {
        local_url_file_github_intake: "available",
        image_ocr: "dependency_required",
        asr_transcription: "not_implemented",
      },
      components: {
        api: "available", database: "available", worker: "available",
        outbox_dispatcher: "lease_fenced", server_sent_events: "not_connected",
      },
      recent_activity: [{ public_ref: "wr1_demo", kind: "job", label: "资料导入", state: "completed", updated_at: "2026-08-23T00:00:00Z" }],
    });
    render(<WorkspaceSpace onNavigate={vi.fn()} />);
    expect(await screen.findByText("0.6.7")).toBeInTheDocument();
    expect(screen.getByText("研究候选")).toBeInTheDocument();
    expect(screen.getByText("待投递记录")).toBeInTheDocument();
    expect(screen.getByText("投递处理器")).toBeInTheDocument();
    expect(screen.getByText("租约保护")).toBeInTheDocument();
    expect(screen.getByText("图像文字识别")).toBeInTheDocument();
    expect(screen.getByText("需要依赖")).toBeInTheDocument();
    expect(screen.getByText("语音转写")).toBeInTheDocument();
    expect(screen.getByText("尚未实现")).toBeInTheDocument();
    expect(screen.getAllByText("可用").length).toBeGreaterThan(0);
    expect(screen.getByText("资料导入")).toBeInTheDocument();
    expect(screen.getByText("已完成")).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("受治理状态");
    expect(document.body).not.toHaveTextContent("lease_fenced");
    expect(document.body).not.toHaveTextContent("dependency_required");
  });

  it("withholds initial Workspace endpoint errors", async () => {
    runtime.getHome.mockRejectedValue(new Error("/workspace/api/v1/home -> 500"));

    render(<WorkspaceSpace onNavigate={vi.fn()} />);

    expect(await screen.findByText(/本地数据暂时不可用/)).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("/workspace/api/v1/home");
  });

  it("reads an immutable source by content identity", async () => {
    runtime.listLibraryAssets.mockResolvedValue({ items: [{ source_name: "note.md", raw_sha256: "a".repeat(64), size_bytes: 6, retention: "immutable", conversion_state: "retained" }] });
    runtime.downloadLibraryAsset.mockResolvedValue(new Blob(["source"]));
    const user = userEvent.setup();
    render(<LibrarySpace onInspect={vi.fn()} />);
    await user.click(await screen.findByRole("button", { name: "打开原件" }));
    expect(runtime.downloadLibraryAsset).toHaveBeenCalledWith("a".repeat(64));
  });

  it("opens a retained PDF with its page anchors inside the canonical Library space", async () => {
    const rawSha256 = "c".repeat(64);
    runtime.listLibraryAssets.mockResolvedValue({ items: [{ source_name: "paper.pdf", raw_sha256: rawSha256, size_bytes: 1024, mime_type: "application/pdf", retention: "immutable", conversion_state: "retained" }] });
    runtime.downloadLibraryAsset.mockResolvedValue(new Blob(["pdf"], { type: "application/pdf" }));
    runtime.listEvidenceAnchors.mockResolvedValue({ count: 1, items: [{ anchor_id: "opaque-anchor", raw_sha256: rawSha256, source_revision: `sha256:${rawSha256}`, locator: { page: 2 } }], next_cursor: null });
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:pdf-reader") });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });

    render(<LibrarySpace onInspect={vi.fn()} />);
    await userEvent.setup().click(await screen.findByRole("button", { name: "打开原件" }));

    expect(await screen.findByTitle("PDF 原件阅读器")).toHaveAttribute("src", "blob:pdf-reader");
    expect(screen.getByText("证据锚点 1 · 第 2 页")).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("opaque-anchor");
  });

  it("withholds Library endpoint details from visible errors", async () => {
    runtime.listLibraryAssets.mockResolvedValue({ items: [{ source_name: "note.md", raw_sha256: "a".repeat(64), size_bytes: 6, retention: "immutable", conversion_state: "retained" }] });
    runtime.downloadLibraryAsset.mockRejectedValue(new Error("/workspace/api/library/download -> 500"));
    const user = userEvent.setup();

    render(<LibrarySpace onInspect={vi.fn()} />);
    await user.click(await screen.findByRole("button", { name: "打开原件" }));

    expect(await screen.findByText(/本地数据暂时不可用/)).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("/workspace/api/library");
    expect(document.body).not.toHaveTextContent("-> 500");
  });

  it("withholds initial Library load errors", async () => {
    runtime.listLibraryAssets.mockRejectedValue(new Error("/workspace/api/library -> 500"));

    render(<LibrarySpace onInspect={vi.fn()} />);

    expect(await screen.findByText(/本地数据暂时不可用/)).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("/workspace/api/library");
  });

  it("approves a research candidate and refreshes the queue", async () => {
    runtime.listEvidenceAnchors.mockResolvedValue({ count: 0, items: [] });
    runtime.listEvidenceBundles.mockResolvedValue({ items: [] });
    runtime.listResearchCandidates
      .mockResolvedValueOnce({ items: [{ source: "https://example.test/source", status: "review" }] })
      .mockResolvedValueOnce({ items: [] });
    runtime.approveResearchCandidate.mockResolvedValue({ status: "approved" });
    const user = userEvent.setup();
    render(<EvidenceSpace onInspect={vi.fn()} />);
    await user.click(await screen.findByRole("button", { name: "批准入账" }));
    expect(runtime.approveResearchCandidate).toHaveBeenCalledWith("https://example.test/source");
    await waitFor(() => expect(runtime.listResearchCandidates).toHaveBeenCalledTimes(2));
  });

  it("withholds Evidence endpoint details from direct status messages", async () => {
    runtime.listEvidenceAnchors.mockResolvedValue({ count: 0, items: [] });
    runtime.listResearchCandidates.mockResolvedValue({ items: [] });
    runtime.listEvidenceBundles.mockRejectedValue(new Error("/workspace/api/evidence/bundles -> 500"));

    render(<EvidenceSpace onInspect={vi.fn()} />);

    expect(await screen.findByText(/本地数据暂时不可用/)).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("/workspace/api/evidence");
    expect(document.body).not.toHaveTextContent("-> 500");
  });

  it("hides opaque Evidence source and hash identities", async () => {
    const rawSha256 = "a".repeat(64);
    runtime.listEvidenceAnchors.mockResolvedValue({ count: 1, items: [{ anchor_id: "anchor-private", raw_sha256: rawSha256, source_revision: "revision-private", locator: { page: 2 } }] });
    runtime.listEvidenceBundles.mockResolvedValue({ items: [] });
    runtime.listResearchCandidates.mockResolvedValue({ items: [{ source: "local-content://sha256/private", status: "review" }] });
    const onInspect = vi.fn();

    render(<EvidenceSpace onInspect={onInspect} />);

    expect(await screen.findByText("本地资料 1")).toBeInTheDocument();
    expect(screen.getByText("已记录")).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("local-content://");
    expect(document.body).not.toHaveTextContent(rawSha256.slice(0, 12));
    await userEvent.setup().click(screen.getByRole("button", { name: "查看" }));
    expect(onInspect).toHaveBeenCalledWith(expect.not.objectContaining({ rawSha256 }));
  });

  it("opens governed Bundle inspection with conflict, rights, review and version history", async () => {
    runtime.listEvidenceAnchors.mockResolvedValue({ count: 0, items: [] });
    runtime.listResearchCandidates.mockResolvedValue({ items: [] });
    runtime.listEvidenceBundles.mockResolvedValue({
      items: [{ bundle_id: "bundle-ui", claim_id: "claim-ui", review_decision: "verified", created_at: "2026-08-24T00:00:00Z" }],
    });
    runtime.getEvidenceBundleInspection.mockResolvedValue({
      bundle_id: "bundle-ui",
      claim_id: "claim-ui",
      fingerprint: "fingerprint-ui",
      entries: [],
      review_history: [{ decision: "verified", reviewer_id: "reviewer-ui", reviewed_at: "2026-08-24T00:00:00Z", rationale: "human reviewed" }],
      latest_review: { decision: "verified", reviewer_id: "reviewer-ui", reviewed_at: "2026-08-24T00:00:00Z", rationale: "human reviewed" },
      conflict: true,
      rights: ["CC-BY-4.0"],
      scopes: ["workspace"],
      version_history: [{ version_id: "version-ui", canonical_key: "key-ui", parent_version_id: null, lifecycle_status: "candidate", created_at: "2026-08-24T00:00:00Z", conflict: { id: "conflict-ui", status: "open" } }],
    });
    const onInspect = vi.fn();
    const user = userEvent.setup();

    render(<EvidenceSpace onInspect={onInspect} />);
    await user.click(await screen.findByRole("button", { name: "查看证据束" }));

    expect(runtime.getEvidenceBundleInspection).toHaveBeenCalledWith("bundle-ui");
    expect(onInspect).toHaveBeenCalledWith(expect.objectContaining({
      title: "受治理证据束",
      source: "关联主张",
      conflict: true,
      rights: ["CC-BY-4.0"],
      scopes: ["workspace"],
      review: expect.objectContaining({ decision: "verified" }),
      versionHistory: [expect.objectContaining({ versionId: "version-ui", conflictStatus: "open" })],
    }));
  });

  it("pages Evidence anchors through the server cursor without growing the rendered list", async () => {
    runtime.listEvidenceAnchors
      .mockResolvedValueOnce({
        count: 1,
        items: [{ anchor_id: "anchor-first", raw_sha256: "a".repeat(64), source_revision: "revision-first", locator: { page: 1 } }],
        next_cursor: "cursor-second",
      })
      .mockResolvedValueOnce({
        count: 1,
        items: [{ anchor_id: "anchor-second", raw_sha256: "b".repeat(64), source_revision: "revision-second", locator: { page: 2 } }],
        next_cursor: null,
      })
      .mockResolvedValueOnce({
        count: 1,
        items: [{ anchor_id: "anchor-first", raw_sha256: "a".repeat(64), source_revision: "revision-first", locator: { page: 1 } }],
        next_cursor: "cursor-second",
      });
    runtime.listEvidenceBundles.mockResolvedValue({ items: [] });
    runtime.listResearchCandidates.mockResolvedValue({ items: [] });
    const user = userEvent.setup();
    const onInspect = vi.fn();

    render(<EvidenceSpace onInspect={onInspect} />);
    expect(await screen.findByText("锚点 1")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "查看" }));
    expect(onInspect).toHaveBeenLastCalledWith(expect.objectContaining({ detail: "定位：第 1 页" }));
    expect(document.body).not.toHaveTextContent("aaaaaaaaaaaa");
    await user.click(screen.getByRole("button", { name: "下一页" }));

    expect(runtime.listEvidenceAnchors).toHaveBeenLastCalledWith(50, "cursor-second");
    await screen.findByText("锚点 1");
    await user.click(screen.getByRole("button", { name: "查看" }));
    expect(onInspect).toHaveBeenLastCalledWith(expect.objectContaining({ detail: "定位：第 2 页" }));
    expect(document.body).not.toHaveTextContent("bbbbbbbbbbbb");
    expect(screen.getByRole("button", { name: "下一页" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "上一页" }));
    expect(runtime.listEvidenceAnchors).toHaveBeenLastCalledWith(50, undefined);
    expect(await screen.findByText("锚点 1")).toBeInTheDocument();
  });

  it("approves and deprecates AI assets as independent governed actions", async () => {
    runtime.getMachineKnowledge.mockResolvedValue({ items: [{ title: "Approved", content: "body", lifecycle: "approved" }] });
    runtime.listMachineKnowledgeCandidates.mockResolvedValue({ items: [{ title: "Candidate", content: "draft", lifecycle: "candidate", version: "1.0.0", evidence_source: "mastery_signal", scope: {} }] });
    runtime.approveMachineKnowledge.mockResolvedValue({ status: "approved" });
    runtime.deprecateMachineKnowledge.mockResolvedValue({ status: "deprecated" });
    const user = userEvent.setup();
    render(<AiAssetsSpace onInspect={vi.fn()} />);
    await user.click(await screen.findByRole("button", { name: "批准 Candidate" }));
    await user.click(screen.getByRole("button", { name: "弃用 Approved" }));
    expect(runtime.approveMachineKnowledge).toHaveBeenCalledWith("Candidate");
    expect(runtime.deprecateMachineKnowledge).toHaveBeenCalledWith("Approved");
  });

  it("withholds Machine Knowledge endpoint details from visible errors", async () => {
    runtime.getMachineKnowledge.mockResolvedValue({ items: [{ title: "Approved", content: "body", lifecycle: "approved" }] });
    runtime.listMachineKnowledgeCandidates.mockResolvedValue({ items: [] });
    runtime.deprecateMachineKnowledge.mockRejectedValue(new Error("/workspace/api/knowledge/deprecate -> 500"));
    const user = userEvent.setup();

    render(<AiAssetsSpace onInspect={vi.fn()} />);
    await user.click(await screen.findByRole("button", { name: "弃用 Approved" }));

    expect(await screen.findByText(/本地数据暂时不可用/)).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("/workspace/api/knowledge");
  });

  it("withholds initial Machine Knowledge load errors", async () => {
    runtime.getMachineKnowledge.mockRejectedValue(new Error("/workspace/api/runtime/knowledge -> 500"));
    runtime.listMachineKnowledgeCandidates.mockResolvedValue({ items: [] });

    render(<AiAssetsSpace onInspect={vi.fn()} />);

    expect(await screen.findByText(/本地数据暂时不可用/)).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("/workspace/api/runtime");
  });

  it("does not render a full source hash in the Inspector", () => {
    const rawSha256 = "b".repeat(64);
    render(<Inspector target={{ title: "原件", source: "原件档案", lifecycle: "已保留", rawSha256 }} />);

    expect(screen.getByText("原件指纹")).toBeInTheDocument();
    expect(screen.getByText("已记录")).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent(rawSha256);
  });

  it("withholds initial Settings endpoint errors", async () => {
    runtime.getSetupStatus.mockRejectedValue(new Error("/workspace/api/setup/status -> 500"));

    render(<SettingsSpace />);

    expect(await screen.findByText(/本地数据暂时不可用/)).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("/workspace/api/setup/status");
  });

  it("creates and verifies a named backup", async () => {
    runtime.getSetupStatus.mockResolvedValue({ initialized: true });
    runtime.createBackup.mockResolvedValue({ file_count: 2 });
    runtime.verifyBackup.mockResolvedValue({ valid: true });
    const user = userEvent.setup();
    render(<SettingsSpace />);
    await user.type(await screen.findByLabelText("备份名称"), "release-check");
    await user.click(screen.getByRole("button", { name: "创建并验证备份" }));
    expect(runtime.createBackup).toHaveBeenCalledWith("release-check");
    expect(runtime.verifyBackup).toHaveBeenCalledWith("release-check");
    expect(await screen.findByText(/备份验证通过/)).toBeInTheDocument();
  });

  it("uses product labels for readiness and withholds Settings endpoint errors", async () => {
    runtime.getSetupStatus.mockResolvedValue({ ready: true, steps: [{ id: "paths_writable", state: "ready", message: "workspace data path is writable (D:/private)" }] });
    runtime.createBackup.mockRejectedValue(new Error("/api/v1/setup/backup -> 500"));
    const user = userEvent.setup();

    render(<SettingsSpace />);
    expect(await screen.findByText("存储位置")).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("paths_writable");
    expect(document.body).not.toHaveTextContent("D:/private");
    await user.type(screen.getByLabelText("备份名称"), "review-check");
    await user.click(screen.getByRole("button", { name: "创建并验证备份" }));

    expect(await screen.findByText(/本地数据暂时不可用/)).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("/api/v1/setup");
  });

  it("blocks workspace creation when health preflight is not ready", async () => {
    runtime.getSetupStatus.mockResolvedValue({ ready: false, steps: [] });
    runtime.preflightSetup.mockResolvedValue({
      ready: false,
      mode: "quick",
      domains: { source_archive: "D:\\ArcheAxis\\source_archive" },
      library_health: { source_archive: { free_bytes: 0, readonly: true } },
    });
    const user = userEvent.setup();
    render(<SettingsSpace />);

    await user.click(await screen.findByRole("button", { name: "开始设置" }));
    await user.click(screen.getByRole("button", { name: "继续" }));
    await user.type(screen.getByLabelText("四库根路径"), "D:\\ArcheAxis");
    await user.click(screen.getByRole("button", { name: "检查四库健康" }));

    expect(await screen.findByRole("button", { name: "创建工作区" })).toBeDisabled();
    expect(screen.getByText(/健康检查未通过/)).toBeInTheDocument();
    expect(runtime.initializeSetup).not.toHaveBeenCalled();
  });

  it("checks four-library health before creating a first workspace", async () => {
    runtime.getSetupStatus.mockResolvedValue({
      ready: false,
      workspace_root: "D:\\ArcheAxis\\workspace",
      steps: [{ id: "paths_writable", state: "ready", message: "path writable", action_hint: "" }],
    });
    runtime.preflightSetup.mockResolvedValue({
      ready: true,
      mode: "quick",
      domains: {
        source_archive: "D:\\ArcheAxis\\source_archive",
        evidence_ledger: "D:\\ArcheAxis\\evidence_ledger",
        human_learning_vault: "D:\\ArcheAxis\\human_learning_vault",
        ai_asset_vault: "D:\\ArcheAxis\\ai_asset_vault",
      },
      library_health: {
        source_archive: { free_bytes: 100, readonly: false, filesystem: "NTFS", removable: "fixed" }, evidence_ledger: { free_bytes: 100 },
        human_learning_vault: { free_bytes: 100 }, ai_asset_vault: { free_bytes: 100 },
      },
    });
    runtime.initializeSetup.mockResolvedValue({ initialized: true, workspace_id: "ws-1" });
    const user = userEvent.setup();
    render(<SettingsSpace />);

    await user.click(await screen.findByRole("button", { name: "开始设置" }));
    await user.click(screen.getByRole("button", { name: "继续" }));
    await user.clear(screen.getByLabelText("四库根路径"));
    await user.type(screen.getByLabelText("四库根路径"), "D:\\ArcheAxis");
    await user.click(screen.getByRole("button", { name: "检查四库健康" }));

    expect(runtime.preflightSetup).toHaveBeenCalledWith({ mode: "quick", root: "D:\\ArcheAxis" });
    expect(await screen.findByText("四库健康检查")).toBeInTheDocument();
    expect(screen.getByText(/可写.*NTFS.*fixed/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "创建工作区" }));
    expect(runtime.initializeSetup).toHaveBeenCalledWith({ mode: "quick", root: "D:\\ArcheAxis" });
    expect(await screen.findByText("设置完成")).toBeInTheDocument();
  });

  it("keeps a successful workspace creation successful when status refresh fails", async () => {
    runtime.getSetupStatus
      .mockResolvedValueOnce({ ready: false, workspace_root: "D:\\ArcheAxis\\workspace", steps: [] })
      .mockRejectedValueOnce(new Error("status refresh unavailable"));
    runtime.preflightSetup.mockResolvedValue({
      ready: true,
      mode: "quick",
      domains: {
        source_archive: "D:\\ArcheAxis\\source_archive",
        evidence_ledger: "D:\\ArcheAxis\\evidence_ledger",
        human_learning_vault: "D:\\ArcheAxis\\human_learning_vault",
        ai_asset_vault: "D:\\ArcheAxis\\ai_asset_vault",
      },
      library_health: {
        source_archive: { free_bytes: 100 }, evidence_ledger: { free_bytes: 100 },
        human_learning_vault: { free_bytes: 100 }, ai_asset_vault: { free_bytes: 100 },
      },
    });
    runtime.initializeSetup.mockResolvedValue({ initialized: true, workspace_id: "ws-1" });
    const user = userEvent.setup();
    render(<SettingsSpace />);

    await user.click(await screen.findByRole("button", { name: "开始设置" }));
    await user.click(screen.getByRole("button", { name: "继续" }));
    await user.click(screen.getByRole("button", { name: "检查四库健康" }));
    await user.click(await screen.findByRole("button", { name: "创建工作区" }));

    expect(await screen.findByText("设置完成")).toBeInTheDocument();
    expect(screen.getByText(/工作区已创建.*状态刷新失败/)).toBeInTheDocument();
  });

  it("requires all four advanced library paths before health preflight", async () => {
    runtime.getSetupStatus.mockResolvedValue({ ready: false, workspace_root: "D:\\ArcheAxis\\workspace", steps: [] });
    const user = userEvent.setup();
    render(<SettingsSpace />);

    await user.click(await screen.findByRole("button", { name: "开始设置" }));
    await user.click(screen.getByLabelText(/高级设置/));
    await user.click(screen.getByRole("button", { name: "继续" }));
    const check = screen.getByRole("button", { name: "检查四库健康" });
    expect(check).toBeDisabled();

    for (const [label, path] of [
      ["源文件归档库", "D:\\Data\\source"], ["证据账本库", "D:\\Data\\evidence"],
      ["人类学习库", "D:\\Data\\learning"], ["机器知识库", "D:\\Data\\assets"],
    ]) {
      await user.type(screen.getByLabelText(label), path);
    }
    expect(check).toBeEnabled();
  });

  it("withholds ActivityDock load errors from the global product surface", async () => {
    runtime.getActivity.mockRejectedValue(new Error("/workspace/api/v1/activity -> 500"));
    runtime.getDelivery.mockResolvedValue({ summary: { jobs: 0, outbox: {}, receipts: {} } });

    render(<ActivityDock />);

    expect(await screen.findByText(/本地数据暂时不可用/)).toBeInTheDocument();
    expect(screen.getByText("投递状态：不可用")).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("/workspace/api/v1/activity");
    expect(document.body).not.toHaveTextContent("-> 500");
  });

  it("withholds ActivityDock delivery-operation errors", async () => {
    runtime.getActivity.mockResolvedValue({ items: [], next_cursor: null });
    runtime.getDelivery.mockResolvedValue({ summary: { jobs: 0, outbox: {}, receipts: {} } });
    runtime.dispatchDelivery.mockRejectedValue(new Error("/workspace/api/delivery/dispatch -> 409"));
    const user = userEvent.setup();

    render(<ActivityDock />);
    await screen.findByText("暂无持久化活动");
    await user.click(screen.getByRole("button", { name: "展开活动坞" }));
    await user.click(screen.getByRole("button", { name: "投递下一条" }));

    expect(await screen.findByText(/投递状态：本地数据暂时不可用/)).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("/workspace/api/delivery");
  });

  it("preserves a successful delivery verdict when readback fails", async () => {
    runtime.getActivity
      .mockResolvedValueOnce({ items: [], next_cursor: null })
      .mockRejectedValueOnce(new Error("/workspace/api/v1/activity -> 500"));
    runtime.getDelivery.mockResolvedValue({ summary: { jobs: 0, outbox: {}, receipts: {} } });
    runtime.dispatchDelivery.mockResolvedValue({ status: "requeued" });
    const user = userEvent.setup();

    render(<ActivityDock />);
    await screen.findByText("暂无持久化活动");
    await user.click(screen.getByRole("button", { name: "展开活动坞" }));
    await user.click(screen.getByRole("button", { name: "投递下一条" }));

    expect(await screen.findByText("投递状态：已重新入队；读回暂不可用")).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("/workspace/api/v1/activity");
  });

  it("withholds ActivityDock detail errors", async () => {
    runtime.getActivity.mockResolvedValue({ items: [{ public_ref: "wr1_demo", kind: "job", label: "资料导入", state: "failed", updated_at: "2026-08-23T00:00:00Z" }], next_cursor: null });
    runtime.getDelivery.mockResolvedValue({ summary: { jobs: 1, outbox: {}, receipts: {} } });
    runtime.getActivityObject.mockRejectedValue(new Error("/workspace/api/v1/activity/wr1_demo -> 500"));
    const user = userEvent.setup();

    render(<ActivityDock />);
    await user.click(await screen.findByRole("button", { name: "展开活动坞" }));
    await user.click(await screen.findByRole("button", { name: "查看活动详情" }));

    expect(await screen.findByText(/本地数据暂时不可用/)).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("/workspace/api/v1/activity");
  });

  it("shows durable activity states and can retry desktop recovery", async () => {
    runtime.getActivity.mockResolvedValue({ items: [{ public_ref: "wr1_demo", kind: "job", label: "资料导入", state: "completed", updated_at: "2026-08-23T00:00:00Z" }], next_cursor: null });
    runtime.getSetupStatus.mockResolvedValue({ initialized: true });
    const user = userEvent.setup();
    render(<ActivityDock />);
    await user.click(await screen.findByRole("button", { name: "展开活动坞" }));
    expect(await screen.findByText(/资料导入 · 已完成/)).toBeInTheDocument();
    render(<SettingsSpace />);
    await user.click(await screen.findByRole("button", { name: "重试桌面后端" }));
    expect(runtime.retryDesktopBackend).toHaveBeenCalledOnce();
    expect(runtime.resetRuntimeClient).toHaveBeenCalledOnce();
  });

  it("opens a durable activity detail and runs only real delivery controls", async () => {
    runtime.getActivity.mockResolvedValue({
      items: [{ public_ref: "wr1_demo", kind: "job", label: "资料导入", state: "failed", updated_at: "2026-08-23T00:00:00Z" }],
      next_cursor: null,
    });
    runtime.getDelivery.mockResolvedValue({ summary: { jobs: 1, outbox: { failed: 1 }, receipts: { missing: 1 } } });
    runtime.getActivityObject.mockResolvedValue({
      label: "资料导入", source: "https://example.test/raw", state: "failed", updated_at: "2026-08-23T00:00:00Z",
    });
    runtime.dispatchDelivery.mockResolvedValue({ status: "idle" });
    runtime.retryFailedDelivery.mockResolvedValue({ status: "requeued" });
    const onInspect = vi.fn();
    const user = userEvent.setup();

    render(<ActivityDock onInspect={onInspect} />);
    await user.click(await screen.findByRole("button", { name: "展开活动坞" }));
    await user.click(await screen.findByRole("button", { name: "查看活动详情" }));
    expect(runtime.getActivityObject).toHaveBeenCalledWith("wr1_demo");
    expect(onInspect).toHaveBeenCalledWith(expect.objectContaining({
      title: "资料导入", lifecycle: "失败", source: "https://example.test/raw",
    }));
    await user.click(screen.getByRole("button", { name: "投递下一条" }));
    await user.click(screen.getByRole("button", { name: "重试失败投递" }));
    expect(runtime.dispatchDelivery).toHaveBeenCalledOnce();
    expect(runtime.retryFailedDelivery).toHaveBeenCalledOnce();
    expect(screen.getByText("投递状态：已重新入队")).toBeInTheDocument();
  });
});
