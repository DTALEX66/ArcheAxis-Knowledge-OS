import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../app/App";

const recovery = vi.hoisted(() => ({
  getRecoveryStatus: vi.fn(),
  getRecoveryLogTail: vi.fn(),
  enterRecoverySafeMode: vi.fn(),
  retryDesktopBackend: vi.fn(),
  restoreRecoveryBackup: vi.fn(),
  exitRecoveryApplication: vi.fn(),
  resetRuntimeClient: vi.fn(),
}));

vi.mock("../api/runtime", async () => ({
  ...(await vi.importActual<typeof import("../api/runtime")>("../api/runtime")),
  ...recovery,
}));

const failedRecovery = {
  state: "failed",
  safe_mode: false,
  backend_available: false,
  message: "Core startup is unavailable",
  backups: ["backup-20260823T010203Z.axbak"],
};

describe("Recovery Shell", () => {
  beforeEach(() => {
    recovery.getRecoveryStatus.mockResolvedValue(failedRecovery);
    recovery.getRecoveryLogTail.mockResolvedValue({ lines: ["Core startup is unavailable"] });
    recovery.enterRecoverySafeMode.mockResolvedValue({ ...failedRecovery, safe_mode: true });
    recovery.retryDesktopBackend.mockResolvedValue(undefined);
    recovery.restoreRecoveryBackup.mockResolvedValue({ status: "restored" });
    recovery.exitRecoveryApplication.mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.clearAllMocks();
    delete window.__TAURI__;
  });

  it("replaces the workspace with a labelled recovery main and explicit controls", async () => {
    render(<App />);

    const shell = await screen.findByRole("main", { name: "Recovery Shell" });
    expect(within(shell).getByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(within(shell).getByRole("button", { name: "Sanitized Logs" })).toBeInTheDocument();
    expect(within(shell).getByRole("button", { name: "Safe Mode" })).toBeInTheDocument();
    expect(within(shell).getByRole("button", { name: "Restore Backup" })).toBeInTheDocument();
    expect(within(shell).getByRole("button", { name: "Exit" })).toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "主空间导航" })).not.toBeInTheDocument();
  });

  it("shows only Tauri-provided sanitized logs and restores only a selected opaque backup", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "Sanitized Logs" }));
    expect(recovery.getRecoveryLogTail).toHaveBeenCalledOnce();
    expect(await screen.findByText("Core startup is unavailable")).toBeInTheDocument();

    const backupChoice = await screen.findByLabelText("Available backups");
    expect(within(backupChoice).getByRole("option", {
      name: "backup-20260823T010203Z.axbak",
    })).toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: /backup/i })).not.toBeInTheDocument();
    await user.selectOptions(backupChoice, "backup-20260823T010203Z.axbak");
    await user.click(screen.getByRole("button", { name: "Restore Backup" }));
    await user.click(await screen.findByRole("button", { name: "Confirm Restore" }));

    expect(recovery.restoreRecoveryBackup).toHaveBeenCalledWith(
      "backup-20260823T010203Z.axbak",
    );
  });

  it("returns to the six-space shell after a successful retry", async () => {
    const user = userEvent.setup();
    recovery.getRecoveryStatus
      .mockResolvedValueOnce(failedRecovery)
      .mockResolvedValueOnce({
        state: "ready",
        safe_mode: false,
        backend_available: true,
        message: "",
        backups: [],
      });
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "Retry" }));

    await waitFor(() => {
      expect(screen.getByRole("navigation", { name: "主空间导航" })).toBeInTheDocument();
    });
    expect(recovery.retryDesktopBackend).toHaveBeenCalledOnce();
  });

  it("keeps recovery operation failures visible in an alert region", async () => {
    const user = userEvent.setup();
    recovery.enterRecoverySafeMode.mockRejectedValue(new Error("safe mode unavailable"));
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "Safe Mode" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/safe mode/i);
  });
});
