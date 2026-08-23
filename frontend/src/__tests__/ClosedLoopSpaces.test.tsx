import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LibrarySpace } from "../spaces/LibrarySpace";
import { EvidenceSpace } from "../spaces/EvidenceSpace";
import { AiAssetsSpace } from "../spaces/AiAssetsSpace";
import { SettingsSpace } from "../spaces/SettingsSpace";
import { WorkspaceSpace } from "../spaces/WorkspaceSpace";
import { ActivityDock } from "../components/ActivityDock";

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
  it("projects release, capabilities, counts, and recent activity on Workspace", async () => {
    runtime.getHome.mockResolvedValue({
      release: { version: "0.6.7", state: "released" },
      counts: { jobs: 3, evidence_anchors: 2 },
      capabilities: { source_archive: "available", governed_learning: "available" },
      components: { api: "available", database: "available" },
      recent_activity: [{ public_ref: "wr1_demo", kind: "job", label: "资料导入", state: "completed", updated_at: "2026-08-23T00:00:00Z" }],
    });
    render(<WorkspaceSpace />);
    expect(await screen.findByText("0.6.7")).toBeInTheDocument();
    expect(screen.getByText(/source_archive · available/)).toBeInTheDocument();
    expect(screen.getByText(/资料导入 · completed/)).toBeInTheDocument();
  });

  it("reads an immutable source by content identity", async () => {
    runtime.listLibraryAssets.mockResolvedValue({ items: [{ source_name: "note.md", raw_sha256: "a".repeat(64), size_bytes: 6, retention: "immutable", conversion_state: "retained" }] });
    runtime.downloadLibraryAsset.mockResolvedValue(new Blob(["source"]));
    const user = userEvent.setup();
    render(<LibrarySpace onInspect={vi.fn()} />);
    await user.click(await screen.findByRole("button", { name: "打开原件" }));
    expect(runtime.downloadLibraryAsset).toHaveBeenCalledWith("a".repeat(64));
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
    await user.click(await screen.findByRole("button", { name: "查看 Bundle" }));

    expect(runtime.getEvidenceBundleInspection).toHaveBeenCalledWith("bundle-ui");
    expect(onInspect).toHaveBeenCalledWith(expect.objectContaining({
      title: "证据 Bundle bundle-ui",
      source: "claim-ui",
      conflict: true,
      rights: ["CC-BY-4.0"],
      scopes: ["workspace"],
      review: expect.objectContaining({ decision: "verified" }),
      versionHistory: [expect.objectContaining({ versionId: "version-ui", conflictStatus: "open" })],
    }));
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
      ["人类学习库", "D:\\Data\\learning"], ["AI 资产库", "D:\\Data\\assets"],
    ]) {
      await user.type(screen.getByLabelText(label), path);
    }
    expect(check).toBeEnabled();
  });

  it("shows durable activity states and can retry desktop recovery", async () => {
    runtime.getActivity.mockResolvedValue({ items: [{ public_ref: "wr1_demo", kind: "job", label: "资料导入", state: "completed", updated_at: "2026-08-23T00:00:00Z" }], next_cursor: null });
    runtime.getSetupStatus.mockResolvedValue({ initialized: true });
    const user = userEvent.setup();
    render(<ActivityDock />);
    expect(await screen.findByText(/资料导入 · completed/)).toBeInTheDocument();
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
    await user.click(await screen.findByRole("button", { name: "查看活动详情" }));
    expect(runtime.getActivityObject).toHaveBeenCalledWith("wr1_demo");
    expect(onInspect).toHaveBeenCalledWith(expect.objectContaining({
      title: "资料导入", lifecycle: "failed", source: "https://example.test/raw",
    }));
    await user.click(screen.getByRole("button", { name: "投递下一条" }));
    await user.click(screen.getByRole("button", { name: "重试失败投递" }));
    expect(runtime.dispatchDelivery).toHaveBeenCalledOnce();
    expect(runtime.retryFailedDelivery).toHaveBeenCalledOnce();
    expect(screen.getByText("投递状态：requeued")).toBeInTheDocument();
  });
});
