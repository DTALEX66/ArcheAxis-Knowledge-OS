// AXW-UI-804: Vitest setup — register @testing-library/jest-dom matchers
// (toBeInTheDocument, toHaveAttribute, toHaveFocus, ...) for jsdom tests.
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// jsdom has no layout engine. ProseMirror calls Range geometry for scrolling;
// keep these test-only empty bounds, without claiming native pixel validation.
if (typeof Range !== "undefined" && !Range.prototype.getClientRects) {
  Range.prototype.getClientRects = () => [] as unknown as DOMRectList;
  Range.prototype.getBoundingClientRect = () => new DOMRect();
}

// Vitest runs without globals, so React Testing Library's auto-cleanup is not
// registered; unmount between tests to keep queries unambiguous.
afterEach(() => {
  cleanup();
});
