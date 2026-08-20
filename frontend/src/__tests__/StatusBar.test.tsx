import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { StatusBar } from "../components/StatusBar";

// AXW-UI-804: StatusBar — product name, active space, text-bearing status badge.
describe("StatusBar", () => {
  it("renders the product name and the current space in a banner landmark", () => {
    render(<StatusBar activeSpace="library" />);
    const banner = screen.getByRole("banner");
    expect(within(banner).getByText("ArcheAxis Knowledge")).toBeInTheDocument();
    expect(screen.getByLabelText("当前空间")).toHaveTextContent("library");
  });

  it("renders a status badge with readable text (never color-only)", () => {
    render(<StatusBar activeSpace="workspace" />);
    const badge = screen.getByText("正在验证本地后端…");
    expect(badge).toBeInTheDocument();
    expect(badge.textContent?.trim()).not.toBe("");
    expect(badge).toHaveAttribute("data-status", "pending");
  });
});
