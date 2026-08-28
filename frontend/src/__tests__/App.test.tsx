import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../app/App";
import { resetRuntimeClient } from "../api/workspace";

// AXW-UI-804: App shell — six-space navigation, default space, landmarks.
// Rail buttons use the English product labels; space headings are Chinese.
describe("App shell", () => {
  afterEach(() => {
    resetRuntimeClient();
    delete window.__TAURI__;
    vi.unstubAllGlobals();
  });

  it("renders the shell landmarks (banner, navigation, main)", () => {
    render(<App />);
    expect(screen.getByRole("banner")).toBeInTheDocument();
    expect(
      screen.getByRole("navigation", { name: "主空间导航" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("main", { name: "当前空间内容" }),
    ).toBeInTheDocument();
    const webMode = screen.getByText(/浏览器开发模式/);
    expect(webMode).toHaveAttribute("data-status", "development");
  });

  it("starts on the workspace space with aria-current on its rail button", () => {
    render(<App />);
    const main = screen.getByRole("main");
    const rail = screen.getByRole("navigation", { name: "主空间导航" });
    expect(
      within(main).getByRole("heading", { name: /工作台总览/ }),
    ).toBeInTheDocument();
    expect(within(rail).getByRole("button", { name: /工作台/ })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("switches to Library on rail click and moves aria-current", async () => {
    const user = userEvent.setup();
    render(<App />);
    const main = screen.getByRole("main");
    const rail = screen.getByRole("navigation", { name: "主空间导航" });
    expect(
      within(main).getByRole("heading", { name: /工作台总览/ }),
    ).toBeInTheDocument();

    await user.click(within(rail).getByRole("button", { name: /资料库/ }));

    expect(
      within(main).getByRole("heading", { name: /原件库/ }),
    ).toBeInTheDocument();
    expect(within(rail).getByRole("button", { name: /资料库/ })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(within(rail).getByRole("button", { name: /工作台/ })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("moves from the Recovery Shell into the workspace when background startup becomes ready", async () => {
    let recoveryCalls = 0;
    window.__TAURI__ = { core: { invoke: vi.fn(async (command: string) => {
      if (command === "recovery_status") {
        recoveryCalls += 1;
        return recoveryCalls === 1
          ? { state: "booting", safe_mode: false, backend_available: false, message: "正在启动", backups: [], external_dev: false }
          : { state: "ready", safe_mode: false, backend_available: true, message: "已就绪", backups: [], external_dev: false };
      }
      if (command === "backend_info") return { port: 4312, token: "memory-only", scopes: ["workspace:write"] };
      throw new Error(`unexpected command ${command}`);
    }) } };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/v1/system/handshake")) return { ok: true, status: 200, json: async () => ({ product_id: "archeaxis-workspace", product_name: "ArcheAxis Knowledge", api_contract: "1.x", backend_version: "0.6.11", source_commit: "abc1234", schema_version: 15, runtime_mode: "desktop", workspace_id: "workspace-1", capabilities: [], migration_state: "ready" }) } as Response;
      if (url.endsWith("/workspace/api/status")) return { ok: true, status: 200, json: async () => ({ schema_version: "v1", observed_at: "2026-08-29T00:00:00Z", release: { version: "0.6.11", status: "candidate", public: false }, components: {}, migrations: {}, counts: {}, capabilities: {} }) } as Response;
      if (url.endsWith("/workspace/api/v1/home")) return { ok: true, status: 200, json: async () => ({ release: { version: "0.6.11", status: "candidate", public: false }, counts: {}, capabilities: {}, components: {}, recent_activity: [] }) } as Response;
      if (url.includes("/workspace/api/v1/activity")) return { ok: true, status: 200, json: async () => ({ items: [], next_cursor: null }) } as Response;
      if (url.endsWith("/workspace/api/delivery")) return { ok: true, status: 200, json: async () => ({ summary: { jobs: 0, outbox: {}, receipts: {} } }) } as Response;
      throw new Error(`unexpected URL ${url}`);
    }));

    render(<App />);
    expect(await screen.findByRole("main", { name: "恢复工作台" })).toBeInTheDocument();
    expect(await screen.findByRole("navigation", { name: "主空间导航" })).toBeInTheDocument();
  });

  it("replaces the six-space workspace with the Recovery Shell after desktop bootstrap fails", async () => {
    window.__TAURI__ = {
      core: {
        invoke: vi.fn(async (command: string) => {
          if (command === "recovery_status") {
            return {
              state: "failed",
              safe_mode: false,
              backend_available: false,
              message: "Core startup is unavailable",
              backups: [],
            };
          }
          return null;
        }),
      },
    };

    render(<App />);

    expect(
      await screen.findByRole("main", { name: "恢复工作台" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("navigation", { name: "主空间导航" }),
    ).not.toBeInTheDocument();
  });

  it("keeps the Recovery Shell when a ready desktop fails the authenticated handshake", async () => {
    const invoke = vi.fn(async (command: string) => {
      if (command === "recovery_status") {
        return {
          state: "ready",
          safe_mode: false,
          backend_available: true,
          message: "Core is ready",
          backups: [],
          external_dev: false,
        };
      }
      if (command === "backend_info") return { port: 4312, token: "memory-only" };
      return null;
    });
    window.__TAURI__ = { core: { invoke } };
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("handshake unavailable")));

    render(<App />);

    expect(await screen.findByRole("main", { name: "恢复工作台" })).toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "主空间导航" })).not.toBeInTheDocument();
    expect(invoke).toHaveBeenNthCalledWith(1, "recovery_status");
    expect(invoke).toHaveBeenNthCalledWith(2, "backend_info");
    expect(invoke).toHaveBeenNthCalledWith(3, "recovery_status");
  });

  it("projects a migrating workspace as a recoverable startup state", async () => {
    window.__TAURI__ = {
      core: {
        invoke: vi.fn(async (command: string) => {
          if (command === "recovery_status") {
            return {
              state: "ready", safe_mode: false, backend_available: true,
              message: "Core is ready", backups: [], external_dev: false,
            };
          }
          if (command === "backend_info") {
            return { port: 4312, token: "memory-only", scopes: ["workspace:write"] };
          }
          return null;
        }),
      },
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        product_id: "archeaxis-workspace", product_name: "ArcheAxis Knowledge", api_contract: "1.x", backend_version: "0.6.0",
        source_commit: "abc1234", schema_version: 15, runtime_mode: "desktop",
        workspace_id: "workspace-001", capabilities: [], migration_state: "migrating",
      }),
    } as Response));

    render(<App />);

    expect(await screen.findByText("本地核心与当前桌面版本不兼容。")).toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "主空间导航" })).not.toBeInTheDocument();
  });

  it("never renders a control-split raw credential from desktop recovery status", async () => {
    const rawDiagnostic = "to\nken = raw-secret-value";
    window.__TAURI__ = {
      core: {
        invoke: vi.fn(async (command: string) => command === "recovery_status" ? {
          state: "failed",
          safe_mode: false,
          backend_available: false,
          message: rawDiagnostic,
          backups: [],
          external_dev: false,
        } : null),
      },
    };

    render(<App />);

    expect(await screen.findByText(/恢复诊断已隐藏/)).toBeInTheDocument();
    expect(screen.queryByText(rawDiagnostic)).not.toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("raw-secret-value");
  });

  it("withholds a long token that begins after the visible display boundary", async () => {
    const safePrefix = "safe ".repeat(46);
    const rawDiagnostic = `${safePrefix}${"A".repeat(40)}==`;
    window.__TAURI__ = {
      core: {
        invoke: vi.fn(async (command: string) => command === "recovery_status" ? {
          state: "failed",
          safe_mode: false,
          backend_available: false,
          message: rawDiagnostic,
          backups: [],
          external_dev: false,
        } : null),
      },
    };

    render(<App />);

    expect(await screen.findByText(/恢复诊断已隐藏/)).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent(safePrefix.slice(0, 50));
    expect(document.body).not.toHaveTextContent("A".repeat(10));
  });
});
