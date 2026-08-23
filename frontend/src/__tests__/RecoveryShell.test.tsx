import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StrictMode } from "react";
import { App } from "../app/App";

const recovery = vi.hoisted(() => ({
  getRecoveryStatus: vi.fn(),
  getRecoveryLogTail: vi.fn(),
  enterRecoverySafeMode: vi.fn(),
  retryDesktopBackend: vi.fn(),
  restoreRecoveryBackup: vi.fn(),
  exitRecoveryApplication: vi.fn(),
  resetRuntimeClient: vi.fn(),
  getStatus: vi.fn(),
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
  backups: ["cognitive_os_20260823T010203_000000Z.sqlite"],
  external_dev: false,
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

describe("Recovery Shell", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    recovery.getRecoveryStatus.mockResolvedValue(failedRecovery);
    recovery.getRecoveryLogTail.mockResolvedValue({ lines: ["Core startup is unavailable"] });
    recovery.enterRecoverySafeMode.mockResolvedValue({ ...failedRecovery, safe_mode: true });
    recovery.retryDesktopBackend.mockResolvedValue(undefined);
    recovery.restoreRecoveryBackup.mockResolvedValue({ status: "restored" });
    recovery.exitRecoveryApplication.mockResolvedValue(undefined);
    recovery.getStatus.mockResolvedValue({ status: "available" });
    window.__TAURI__ = { core: { invoke: vi.fn() } };
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
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
    const logRegion = await screen.findByRole("region", { name: "Sanitized Logs" });
    expect(within(logRegion).getByText("Core startup is unavailable")).toBeInTheDocument();

    const backupChoice = await screen.findByLabelText("Available backups");
    const backupOption = within(backupChoice).getByRole("option", {
      name: "cognitive_os_20260823T010203_000000Z.sqlite",
    });
    expect(backupOption).toHaveValue("cognitive_os_20260823T010203_000000Z.sqlite");
    expect(backupOption).not.toHaveTextContent(/[\\/:]/);
    expect(screen.queryByRole("textbox", { name: /backup/i })).not.toBeInTheDocument();
    await user.selectOptions(backupChoice, "cognitive_os_20260823T010203_000000Z.sqlite");
    await user.click(screen.getByRole("button", { name: "Restore Backup" }));
    await user.click(await screen.findByRole("button", { name: "Confirm Restore" }));

    expect(recovery.restoreRecoveryBackup).toHaveBeenCalledWith(
      "cognitive_os_20260823T010203_000000Z.sqlite",
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

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/safe mode/i);
    await waitFor(() => expect(alert.parentElement).toHaveFocus());
  });

  it("disables conflicting recovery actions while desktop verification is checking", () => {
    recovery.getRecoveryStatus.mockReturnValue(new Promise(() => undefined));

    render(<App />);

    expect(screen.getByRole("button", { name: "Retry" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Safe Mode" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Exit" })).toBeDisabled();
  });

  it("does not let a stale retry operation overwrite Safe Mode", async () => {
    recovery.getRecoveryStatus
      .mockResolvedValueOnce(failedRecovery)
      .mockResolvedValueOnce({
        state: "ready",
        safe_mode: false,
        backend_available: true,
        message: "Core is ready",
        backups: [],
        external_dev: false,
      });
    recovery.enterRecoverySafeMode.mockResolvedValue({
      ...failedRecovery,
      state: "stopped",
      safe_mode: true,
      message: "Safe Mode is active",
    });
    render(<App />);

    const retry = await screen.findByRole("button", { name: "Retry" });
    const safeMode = screen.getByRole("button", { name: "Safe Mode" });
    act(() => {
      fireEvent.click(retry);
      fireEvent.click(safeMode);
    });
    expect(await screen.findByText(/Safe Mode is active/)).toBeInTheDocument();

    expect(screen.queryByRole("navigation", { name: "主空间导航" })).not.toBeInTheDocument();
    expect(screen.getByRole("main", { name: "Recovery Shell" })).toBeInTheDocument();
  });

  it("ignores a deferred handshake from an unmounted operation generation", async () => {
    const handshake = deferred<{ status: string }>();
    recovery.getRecoveryStatus
      .mockResolvedValueOnce({
        state: "ready",
        safe_mode: false,
        backend_available: true,
        message: "Core is ready",
        backups: [],
        external_dev: false,
      })
      .mockResolvedValueOnce({
        ...failedRecovery,
        state: "stopped",
        safe_mode: true,
        message: "Safe Mode is active",
      });
    recovery.getStatus.mockReturnValue(handshake.promise);

    const firstGeneration = render(<App />);
    await waitFor(() => expect(recovery.getStatus).toHaveBeenCalledOnce());
    firstGeneration.unmount();

    render(<App />);
    expect(await screen.findByText("Safe Mode is active")).toBeInTheDocument();
    await act(async () => handshake.resolve({ status: "available" }));

    expect(screen.queryByRole("navigation", { name: "主空间导航" })).not.toBeInTheDocument();
    expect(screen.getByRole("main", { name: "Recovery Shell" })).toBeInTheDocument();
  });

  it("moves a ready desktop into Recovery Shell when the liveness check observes Core stopped", async () => {
    vi.useFakeTimers();
    recovery.getRecoveryStatus
      .mockResolvedValueOnce({
        state: "ready",
        safe_mode: false,
        backend_available: true,
        message: "Core is ready",
        backups: [],
        external_dev: false,
      })
      .mockResolvedValueOnce({
        ...failedRecovery,
        state: "stopped",
        message: "Core stopped",
      });

    render(<App />);
    await act(async () => Promise.resolve());
    expect(screen.getByRole("navigation", { name: "主空间导航" })).toBeInTheDocument();

    await act(async () => vi.advanceTimersByTimeAsync(10_000));

    expect(screen.getByRole("main", { name: "Recovery Shell" })).toBeInTheDocument();
    expect(screen.getByText("Core stopped")).toBeInTheDocument();
    expect(recovery.getRecoveryStatus).toHaveBeenCalledTimes(2);
    expect(recovery.getStatus).toHaveBeenCalledOnce();
  });

  it("refreshes recovery status after a later authenticated liveness handshake fails", async () => {
    vi.useFakeTimers();
    const readyStatus = {
      state: "ready",
      safe_mode: false,
      backend_available: true,
      message: "Core is ready",
      backups: [],
      external_dev: false,
    } as const;
    recovery.getRecoveryStatus
      .mockResolvedValueOnce(readyStatus)
      .mockResolvedValueOnce(readyStatus)
      .mockResolvedValueOnce({
        ...failedRecovery,
        state: "stopped",
        message: "Core stopped after handshake failure",
      });
    recovery.getStatus
      .mockResolvedValueOnce({ status: "available" })
      .mockRejectedValueOnce(new Error("handshake unavailable"));

    render(<App />);
    await act(async () => Promise.resolve());
    expect(screen.getByRole("navigation", { name: "主空间导航" })).toBeInTheDocument();

    await act(async () => vi.advanceTimersByTimeAsync(10_000));

    expect(screen.getByRole("main", { name: "Recovery Shell" })).toBeInTheDocument();
    expect(screen.getByText("Authenticated Core handshake failed.")).toBeInTheDocument();
    expect(recovery.getRecoveryStatus).toHaveBeenCalledTimes(3);
    expect(recovery.getStatus).toHaveBeenCalledTimes(2);
  });

  it("cleans up one non-overlapping liveness loop on unmount", async () => {
    vi.useFakeTimers();
    const pendingStatus = deferred<typeof failedRecovery>();
    recovery.getRecoveryStatus
      .mockResolvedValueOnce({
        state: "ready",
        safe_mode: false,
        backend_available: true,
        message: "Core is ready",
        backups: [],
        external_dev: false,
      })
      .mockReturnValueOnce(pendingStatus.promise);

    const view = render(<App />);
    await act(async () => Promise.resolve());
    expect(screen.getByRole("navigation", { name: "主空间导航" })).toBeInTheDocument();

    await act(async () => vi.advanceTimersByTimeAsync(10_000));
    await act(async () => vi.advanceTimersByTimeAsync(30_000));
    expect(recovery.getRecoveryStatus).toHaveBeenCalledTimes(2);

    view.unmount();
    await act(async () => pendingStatus.resolve(failedRecovery));
    await act(async () => vi.advanceTimersByTimeAsync(30_000));

    expect(recovery.getRecoveryStatus).toHaveBeenCalledTimes(2);
    expect(recovery.getStatus).toHaveBeenCalledOnce();
  });

  it("names the active operation in the live progress region", async () => {
    const logs = deferred<{ lines: string[] }>();
    recovery.getRecoveryLogTail.mockReturnValue(logs.promise);
    const user = userEvent.setup();
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "Sanitized Logs" }));

    expect(screen.getByRole("status")).toHaveTextContent("Loading sanitized logs");
    await act(async () => logs.resolve({ lines: [] }));
  });

  it("locks restore after a successful receipt even when status refresh fails", async () => {
    const user = userEvent.setup();
    recovery.getRecoveryStatus
      .mockResolvedValueOnce(failedRecovery)
      .mockRejectedValueOnce(new Error("status unavailable"));
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "Restore Backup" }));
    await user.click(screen.getByRole("button", { name: "Confirm Restore" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Restore succeeded; status refresh unavailable",
    );
    expect(screen.queryByRole("button", { name: "Confirm Restore" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Restore Backup" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Restore Backup" }));
    expect(recovery.restoreRecoveryBackup).toHaveBeenCalledOnce();
    expect(screen.getByRole("main", { name: "Recovery Shell" })).toBeInTheDocument();
  });

  it("shows and sequences reload-current-core only for the explicit external DEV profile", async () => {
    const user = userEvent.setup();
    const order: string[] = [];
    recovery.getRecoveryStatus
      .mockImplementationOnce(async () => ({ ...failedRecovery, external_dev: true }))
      .mockImplementationOnce(async () => {
        order.push("status");
        return {
          state: "ready",
          safe_mode: false,
          backend_available: true,
          message: "Core is ready",
          backups: [],
          external_dev: true,
        };
      });
    recovery.enterRecoverySafeMode.mockImplementation(async () => {
      order.push("safe-mode");
      return { ...failedRecovery, state: "stopped", safe_mode: true, external_dev: true };
    });
    recovery.resetRuntimeClient.mockImplementation(() => order.push("reset"));
    recovery.retryDesktopBackend.mockImplementation(async () => {
      order.push("retry");
    });
    recovery.getStatus.mockImplementation(async () => {
      order.push("handshake");
      return { status: "available" };
    });

    render(<App />);

    expect(await screen.findByText("DEV")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Reload Current Core" }));
    await screen.findByRole("navigation", { name: "主空间导航" });

    expect(order).toEqual([
      "safe-mode",
      "reset",
      "retry",
      "reset",
      "status",
      "handshake",
    ]);
  });

  it("does not expose reload-current-core outside the explicit external DEV profile", async () => {
    render(<App />);

    await screen.findByRole("main", { name: "Recovery Shell" });
    expect(screen.queryByRole("button", { name: "Reload Current Core" })).not.toBeInTheDocument();
    expect(screen.queryByText("DEV")).not.toBeInTheDocument();
  });

  it("keeps async recovery actions live through a real StrictMode effect replay", async () => {
    const user = userEvent.setup();
    const logs = deferred<{ lines: string[] }>();
    const devFailure = { ...failedRecovery, external_dev: true };
    let retrying = false;
    recovery.getRecoveryStatus.mockImplementation(async () => retrying ? {
      state: "ready",
      safe_mode: false,
      backend_available: true,
      message: "Core is ready",
      backups: [],
      external_dev: true,
    } : devFailure);
    recovery.getRecoveryLogTail.mockReturnValue(logs.promise);
    recovery.enterRecoverySafeMode.mockResolvedValue({
      ...devFailure,
      state: "stopped",
      safe_mode: true,
    });
    recovery.retryDesktopBackend.mockImplementation(async () => {
      retrying = true;
    });

    render(<StrictMode><App /></StrictMode>);
    await user.click(await screen.findByRole("button", { name: "Sanitized Logs" }));
    expect(screen.getByText("Loading sanitized logs…")).toBeInTheDocument();
    await act(async () => logs.resolve({ lines: ["Core stopped"] }));

    const logSuccess = await screen.findByText("Sanitized logs loaded.");
    expect(screen.queryByText("Loading sanitized logs…")).not.toBeInTheDocument();
    await waitFor(() => expect(logSuccess.parentElement).toHaveFocus());

    await user.click(screen.getByRole("button", { name: "Restore Backup" }));
    await user.click(screen.getByRole("button", { name: "Confirm Restore" }));
    const restoreSuccess = await screen.findByText("Backup restored. Retry Core when ready.");
    expect(screen.queryByRole("button", { name: "Confirm Restore" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Restore Backup" })).toBeDisabled();
    await waitFor(() => expect(restoreSuccess.parentElement).toHaveFocus());

    const reload = screen.getByRole("button", { name: "Reload Current Core" });
    expect(reload).toBeEnabled();
    await user.click(reload);
    expect(await screen.findByRole("navigation", { name: "主空间导航" })).toBeInTheDocument();
  });
});
