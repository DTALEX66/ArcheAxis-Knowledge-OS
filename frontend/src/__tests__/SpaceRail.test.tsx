import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SpaceRail, SPACES } from "../components/SpaceRail";

// AXW-UI-804: SpaceRail navigation accessibility & interaction tests.
describe("SpaceRail", () => {
  it("renders exactly six space buttons with accessible names", () => {
    render(
      <SpaceRail active="workspace" onNavigate={vi.fn()} spaces={SPACES} />,
    );
    const nav = screen.getByRole("navigation", { name: "主空间导航" });
    expect(within(nav).getAllByRole("button")).toHaveLength(6);
    for (const space of SPACES) {
      expect(
        within(nav).getByRole("button", { name: space.label }),
      ).toBeInTheDocument();
    }
  });

  it("calls onNavigate with the space id when a button is clicked", async () => {
    const onNavigate = vi.fn();
    const user = userEvent.setup();
    render(
      <SpaceRail active="workspace" onNavigate={onNavigate} spaces={SPACES} />,
    );

    await user.click(screen.getByRole("button", { name: "资料库" }));
    expect(onNavigate).toHaveBeenCalledWith("library");

    await user.click(screen.getByRole("button", { name: "设置" }));
    expect(onNavigate).toHaveBeenCalledWith("settings");
  });

  it("marks exactly the active space with aria-current=page", () => {
    render(
      <SpaceRail active="evidence" onNavigate={vi.fn()} spaces={SPACES} />,
    );
    expect(screen.getByRole("button", { name: "证据" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    for (const space of SPACES.filter((s) => s.id !== "evidence")) {
      expect(screen.getByRole("button", { name: space.label })).not.toHaveAttribute(
        "aria-current",
      );
    }
  });

  it("keeps every space button keyboard-focusable (Tab order + focus-visible)", async () => {
    const user = userEvent.setup();
    render(
      <SpaceRail active="workspace" onNavigate={vi.fn()} spaces={SPACES} />,
    );
    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(6);

    // Tab through the rail: each button must receive keyboard focus in order
    // and report focus-visible (keyboard-initiated focus).
    for (const button of buttons) {
      await user.tab();
      expect(button).toHaveFocus();
      expect(button.matches(":focus-visible")).toBe(true);
    }
  });

  it("moves and activates space navigation with arrow keys, Home, and End", async () => {
    const onNavigate = vi.fn();
    const user = userEvent.setup();
    render(
      <SpaceRail active="workspace" onNavigate={onNavigate} spaces={SPACES} />,
    );

    const workspace = screen.getByRole("button", { name: "工作台" });
    const library = screen.getByRole("button", { name: "资料库" });
    const settings = screen.getByRole("button", { name: "设置" });
    workspace.focus();

    await user.keyboard("{ArrowDown}");
    expect(library).toHaveFocus();
    expect(onNavigate).toHaveBeenLastCalledWith("library");

    await user.keyboard("{End}");
    expect(settings).toHaveFocus();
    expect(onNavigate).toHaveBeenLastCalledWith("settings");

    await user.keyboard("{Home}");
    expect(workspace).toHaveFocus();
    expect(onNavigate).toHaveBeenLastCalledWith("workspace");
  });
});
