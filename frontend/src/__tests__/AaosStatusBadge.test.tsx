import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { AaosStatusBadge } from "../components/AaosStatusBadge";

describe("AAOS status semantics", () => {
  it.each([
    ["success", "已完成"],
    ["warning", "等待设置"],
    ["danger", "失败"],
  ] as const)("shows %s with a visible label and a redundant icon", (tone, label) => {
    render(<AaosStatusBadge tone={tone}>{label}</AaosStatusBadge>);
    const status = screen.getByText(label).closest("[data-status-tone]");
    expect(status?.getAttribute("data-status-tone")).toBe(tone);
    expect(status?.querySelector(`svg[data-icon="${tone}"]`)?.getAttribute("aria-hidden")).toBe("true");
    expect(status?.textContent).toContain(label);
  });
});
