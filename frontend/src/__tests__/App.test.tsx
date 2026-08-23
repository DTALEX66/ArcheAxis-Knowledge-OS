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
    expect(
      within(main).getByRole("heading", { name: /工作区状态/ }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Workspace/ })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("switches to Library on rail click and moves aria-current", async () => {
    const user = userEvent.setup();
    render(<App />);
    const main = screen.getByRole("main");
    expect(
      within(main).getByRole("heading", { name: /工作区状态/ }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Library/ }));

    expect(
      within(main).getByRole("heading", { name: /原件库/ }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Library/ })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("button", { name: /Workspace/ })).not.toHaveAttribute(
      "aria-current",
    );
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
      await screen.findByRole("main", { name: "Recovery Shell" }),
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

    expect(await screen.findByRole("main", { name: "Recovery Shell" })).toBeInTheDocument();
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

    expect(await screen.findByText("Workspace migration is in progress.")).toBeInTheDocument();
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

    expect(await screen.findByText("Recovery diagnostic withheld")).toBeInTheDocument();
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

    expect(await screen.findByText("Recovery diagnostic withheld")).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent(safePrefix.slice(0, 50));
    expect(document.body).not.toHaveTextContent("A".repeat(10));
  });
});
