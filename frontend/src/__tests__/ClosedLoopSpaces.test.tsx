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
  listEvidenceAnchors: vi.fn(), listResearchCandidates: vi.fn(), approveResearchCandidate: vi.fn(),
  getMachineKnowledge: vi.fn(), listMachineKnowledgeCandidates: vi.fn(),
  approveMachineKnowledge: vi.fn(), deprecateMachineKnowledge: vi.fn(),
  getSetupStatus: vi.fn(), initializeSetup: vi.fn(), createBackup: vi.fn(), verifyBackup: vi.fn(),
  getHome: vi.fn(), getActivity: vi.fn(), retryDesktopBackend: vi.fn(), resetRuntimeClient: vi.fn(),
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
});
