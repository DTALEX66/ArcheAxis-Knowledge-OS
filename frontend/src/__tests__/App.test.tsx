import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../app/App";

// AXW-UI-804: App shell — six-space navigation, default space, landmarks.
// Rail buttons use the English product labels; space headings are Chinese.
describe("App shell", () => {
  afterEach(() => {
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
});
