import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { SettingsSpace } from "../spaces/SettingsSpace";

// AXW-UI-804: SettingsSpace - the workspace setup wizard and the readiness
// board. These tests pin the three states a reader can be in (loading, failed
// read, ready) and that the backup control refuses to run without a name.
const api = vi.hoisted(() => ({
  getSetupStatus: vi.fn(),
  preflightSetup: vi.fn(),
  initializeSetup: vi.fn(),
  createBackup: vi.fn(),
  verifyBackup: vi.fn(),
  retryDesktopBackend: vi.fn(),
  resetRuntimeClient: vi.fn(),
}));
vi.mock("../api/workspace", () => api);

function readyStatus(steps: { id: string; state: string }[], ready = true) {
  return { ready, workspace_root: "D:/ws", steps };
}

beforeEach(() => {
  for (const fn of Object.values(api)) fn.mockReset();
});

describe("SettingsSpace", () => {
  it("shows the loading state until the setup status arrives", () => {
    api.getSetupStatus.mockReturnValue(new Promise(() => {}));
    render(<SettingsSpace />);
    expect(screen.getByText("加载中：设置…")).toBeInTheDocument();
  });

  it("reports a failed status read through the mapped message, not the raw error", async () => {
    api.getSetupStatus.mockRejectedValue(new Error("本地核心未完成此操作"));
    render(<SettingsSpace />);
    expect(await screen.findByText("设置 加载失败")).toBeInTheDocument();
  });

  it("lists each readiness step with its own label and state text once ready", async () => {
    api.getSetupStatus.mockResolvedValue(
      readyStatus([
        { id: "workspace_exists", state: "ready" },
        { id: "legacy_db_migration", state: "pending" },
      ]),
    );
    render(<SettingsSpace />);

    expect(await screen.findByRole("heading", { name: "设置完成" })).toBeInTheDocument();
    expect(screen.getByText("当前就绪状态")).toBeInTheDocument();
    // Two steps, each naming itself and its state in words (never a bare colour).
    expect(screen.getByText("工作区")).toBeInTheDocument();
    expect(screen.getByText("检查通过")).toBeInTheDocument();
    expect(screen.getByText("旧数据迁移")).toBeInTheDocument();
    expect(screen.getByText("等待完成设置")).toBeInTheDocument();
  });

  it("keeps the backup control disabled until a name is entered, then creates and verifies it", async () => {
    api.getSetupStatus.mockResolvedValue(readyStatus([]));
    api.createBackup.mockResolvedValue({});
    api.verifyBackup.mockResolvedValue({ valid: true });
    render(<SettingsSpace />);

    const button = await screen.findByRole("button", { name: "创建并验证备份" });
    expect(button).toBeDisabled();

    fireEvent.change(screen.getByLabelText("备份名称"), { target: { value: "release-check" } });
    expect(button).toBeEnabled();

    fireEvent.click(button);
    await waitFor(() => expect(api.createBackup).toHaveBeenCalledWith("release-check"));
    await waitFor(() => expect(api.verifyBackup).toHaveBeenCalledWith("release-check"));
    expect(await screen.findByText("备份验证通过")).toBeInTheDocument();
  });
});
