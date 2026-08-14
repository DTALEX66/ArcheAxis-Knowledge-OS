// AXW-UI-804: Vitest setup — register @testing-library/jest-dom matchers
// (toBeInTheDocument, toHaveAttribute, toHaveFocus, ...) for jsdom tests.
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Vitest runs without globals, so React Testing Library's auto-cleanup is not
// registered; unmount between tests to keep queries unambiguous.
afterEach(() => {
  cleanup();
});
