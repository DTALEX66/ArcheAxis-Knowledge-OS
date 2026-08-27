import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { StatusBar } from "../components/StatusBar";

// AXW-UI-804: StatusBar — product name, active space, text-bearing status badge.
describe("StatusBar", () => {
  it("renders the product name and the current space in a banner landmark", () => {
    render(<StatusBar activeSpace="library" backendState="available" />);
    const banner = screen.getByRole("banner");
    expect(within(banner).getByText("ArcheAxis Knowledge")).toBeInTheDocument();
    expect(screen.getByLabelText("当前空间")).toHaveTextContent("资料库");
  });

  it("renders a status badge with readable text (never color-only)", () => {
    render(<StatusBar activeSpace="workspace" backendState="checking" />);
    const badge = screen.getByText("正在验证本地后端…");
    expect(badge).toBeInTheDocument();
    expect(badge.textContent?.trim()).not.toBe("");
    expect(badge).toHaveAttribute("data-status", "pending");
  });

  it("renders a persistent text DEV marker only for explicit external development", () => {
    const { rerender } = render(
      <StatusBar activeSpace="workspace" backendState="available" externalDev />,
    );
    expect(screen.getByText("开发")).toBeInTheDocument();

    rerender(
      <StatusBar activeSpace="workspace" backendState="available" externalDev={false} />,
    );
    expect(screen.queryByText("开发")).not.toBeInTheDocument();
  });

  it("renders unavailable state without exposing an unreachable recovery control", () => {
    render(<StatusBar activeSpace="workspace" backendState="unavailable" />);

    expect(screen.getByText("后端状态：不可用")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("labels immediate non-desktop rendering as browser development mode", () => {
    render(<StatusBar activeSpace="workspace" backendState="web" />);

    const badge = screen.getByText(/浏览器开发模式/);
    expect(badge).toHaveAttribute("data-status", "development");
    expect(screen.queryByText("后端状态：本地可用")).not.toBeInTheDocument();
  });
});
