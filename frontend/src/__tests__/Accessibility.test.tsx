/**
 * Accessibility test for core components
 */
import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { runAccessibilityAudit } from "../test/accessibility";
import { FileUpload } from "../components/FileUpload";
import { CanvasBoard } from "../components/CanvasBoard";

describe("Accessibility", () => {
  it("FileUpload has no critical accessibility issues", () => {
    const { container } = render(<FileUpload />);
    const audit = runAccessibilityAudit(container);

    expect(audit.errors).toEqual([]);
  });

  it("CanvasBoard controls have labels and natural tab order", () => {
    const { container } = render(
      <CanvasBoard doc={{ nodes: [], edges: [] }} onChange={() => {}} />
    );
    const audit = runAccessibilityAudit(container);

    expect(audit.errors).toEqual([]);
    expect(audit.warnings.filter(w => w.issue.includes("tabindex"))).toHaveLength(0);
  });

  it("Buttons have accessible labels", () => {
    const { container } = render(<FileUpload />);
    const buttons = container.querySelectorAll("button");

    buttons.forEach((button) => {
      const hasLabel =
        button.getAttribute("aria-label") ||
        button.textContent?.trim() ||
        button.getAttribute("title");

      expect(hasLabel).toBeTruthy();
    });
  });

  it("Interactive elements are keyboard accessible", () => {
    const { container } = render(<FileUpload />);
    const interactive = container.querySelectorAll("button, a, input");

    interactive.forEach((el) => {
      const tabIndex = el.getAttribute("tabindex");
      // Should not have positive tabindex
      if (tabIndex) {
        expect(parseInt(tabIndex)).toBeLessThanOrEqual(0);
      }
    });
  });
});
