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

vi.mock("../api/workspace", async () => ({
  ...(await vi.importActual<typeof import("../api/workspace")>("../api/workspace")),
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

    const shell = await screen.findByRole("main", { name: "恢复工作台" });
    expect(within(shell).getByRole("button", { name: "重试" })).toBeInTheDocument();
    expect(within(shell).getByRole("button", { name: "安全诊断" })).toBeInTheDocument();
    expect(within(shell).getByRole("button", { name: "安全模式" })).toBeInTheDocument();
    expect(within(shell).getByRole("button", { name: "恢复备份" })).toBeInTheDocument();
    expect(within(shell).getByRole("button", { name: "退出" })).toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "主空间导航" })).not.toBeInTheDocument();
  });

  it("shows only Tauri-provided sanitized logs and restores only a selected opaque backup", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "安全诊断" }));
    expect(recovery.getRecoveryLogTail).toHaveBeenCalledOnce();
    const logRegion = await screen.findByRole("region", { name: "安全诊断日志" });
    expect(within(logRegion).getByText("Core startup is unavailable")).toBeInTheDocument();

    const backupChoice = await screen.findByLabelText("可用备份");
    const backupOption = within(backupChoice).getByRole("option", {
      name: "cognitive_os_20260823T010203_000000Z.sqlite",
    });
    expect(backupOption).toHaveValue("cognitive_os_20260823T010203_000000Z.sqlite");
    expect(backupOption).not.toHaveTextContent(/[\\/:]/);
    expect(screen.queryByRole("textbox", { name: /backup/i })).not.toBeInTheDocument();
    await user.selectOptions(backupChoice, "cognitive_os_20260823T010203_000000Z.sqlite");
    await user.click(screen.getByRole("button", { name: "恢复备份" }));
    await user.click(await screen.findByRole("button", { name: "确认恢复" }));

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

    await user.click(await screen.findByRole("button", { name: "重试" }));

    await waitFor(() => {
      expect(screen.getByRole("navigation", { name: "主空间导航" })).toBeInTheDocument();
    });
    expect(recovery.retryDesktopBackend).toHaveBeenCalledOnce();
  });

  it("keeps recovery operation failures visible in an alert region", async () => {
    const user = userEvent.setup();
    recovery.enterRecoverySafeMode.mockRejectedValue(new Error("safe mode unavailable"));
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "安全模式" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/安全模式/);
    await waitFor(() => expect(alert.parentElement).toHaveFocus());
  });

  it("disables conflicting recovery actions while desktop verification is checking", () => {
    recovery.getRecoveryStatus.mockReturnValue(new Promise(() => undefined));

    render(<App />);

    expect(screen.getByRole("button", { name: "重试" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "安全模式" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "退出" })).toBeDisabled();
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
      message: "安全模式已启用；本地核心保持停止。",
    });
    render(<App />);

    const retry = await screen.findByRole("button", { name: "重试" });
    const safeMode = screen.getByRole("button", { name: "安全模式" });
    act(() => {
      fireEvent.click(retry);
      fireEvent.click(safeMode);
    });
    expect(await screen.findByText(/安全模式已启用/)).toBeInTheDocument();

    expect(screen.queryByRole("navigation", { name: "主空间导航" })).not.toBeInTheDocument();
    expect(screen.getByRole("main", { name: "恢复工作台" })).toBeInTheDocument();
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
        message: "安全模式已启用；本地核心保持停止。",
      });
    recovery.getStatus.mockReturnValue(handshake.promise);

    const firstGeneration = render(<App />);
    await waitFor(() => expect(recovery.getStatus).toHaveBeenCalledOnce());
    firstGeneration.unmount();

    render(<App />);
    expect(await screen.findByText("安全模式已启用；本地核心保持停止。")).toBeInTheDocument();
    await act(async () => handshake.resolve({ status: "available" }));

    expect(screen.queryByRole("navigation", { name: "主空间导航" })).not.toBeInTheDocument();
    expect(screen.getByRole("main", { name: "恢复工作台" })).toBeInTheDocument();
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
        message: "本地核心已停止。",
      });

    render(<App />);
    await act(async () => Promise.resolve());
    expect(screen.getByRole("navigation", { name: "主空间导航" })).toBeInTheDocument();

    await act(async () => vi.advanceTimersByTimeAsync(10_000));

    expect(screen.getByRole("main", { name: "恢复工作台" })).toBeInTheDocument();
    expect(screen.getByText("本地核心已停止。")).toBeInTheDocument();
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

    expect(screen.getByRole("main", { name: "恢复工作台" })).toBeInTheDocument();
    expect(screen.getByText("本地核心与当前桌面版本不兼容。")).toBeInTheDocument();
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

    await user.click(await screen.findByRole("button", { name: "安全诊断" }));

    expect(screen.getByRole("status")).toHaveTextContent("正在加载安全诊断日志");
    await act(async () => logs.resolve({ lines: [] }));
  });

  it("locks restore after a successful receipt even when status refresh fails", async () => {
    const user = userEvent.setup();
    recovery.getRecoveryStatus
      .mockResolvedValueOnce(failedRecovery)
      .mockRejectedValueOnce(new Error("status unavailable"));
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "恢复备份" }));
    await user.click(screen.getByRole("button", { name: "确认恢复" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "备份已恢复，但状态刷新不可用",
    );
    expect(screen.queryByRole("button", { name: "确认恢复" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "恢复备份" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "恢复备份" }));
    expect(recovery.restoreRecoveryBackup).toHaveBeenCalledOnce();
    expect(screen.getByRole("main", { name: "恢复工作台" })).toBeInTheDocument();
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

    expect(await screen.findByText("开发")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "重新加载当前核心" }));
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

    await screen.findByRole("main", { name: "恢复工作台" });
    expect(screen.queryByRole("button", { name: "重新加载当前核心" })).not.toBeInTheDocument();
    expect(screen.queryByText("开发")).not.toBeInTheDocument();
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
    await user.click(await screen.findByRole("button", { name: "安全诊断" }));
    expect(screen.getByText("正在加载安全诊断日志…")).toBeInTheDocument();
    await act(async () => logs.resolve({ lines: ["本地核心已停止。"] }));

    const logSuccess = await screen.findByText("安全诊断日志已加载。");
    expect(screen.queryByText("正在加载安全诊断日志…")).not.toBeInTheDocument();
    await waitFor(() => expect(logSuccess.parentElement).toHaveFocus());

    await user.click(screen.getByRole("button", { name: "恢复备份" }));
    await user.click(screen.getByRole("button", { name: "确认恢复" }));
    const restoreSuccess = await screen.findByText("备份已恢复；准备好后可重试本地核心。");
    expect(screen.queryByRole("button", { name: "确认恢复" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "恢复备份" })).toBeDisabled();
    await waitFor(() => expect(restoreSuccess.parentElement).toHaveFocus());

    const reload = screen.getByRole("button", { name: "重新加载当前核心" });
    expect(reload).toBeEnabled();
    await user.click(reload);
    expect(await screen.findByRole("navigation", { name: "主空间导航" })).toBeInTheDocument();
  });
});
