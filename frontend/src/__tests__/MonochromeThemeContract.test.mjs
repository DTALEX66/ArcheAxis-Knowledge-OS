// @vitest-environment node
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const stylesheet = readFileSync(
  new URL("../design-system/tokens.css", import.meta.url),
  "utf8",
);

describe("monochrome product theme contract", () => {
  it("uses an offline black-and-white dark baseline with accessible motion fallback", () => {
    expect(stylesheet).toContain("Monochrome Design System");
    expect(stylesheet).toContain("color-scheme: dark");
    expect(stylesheet).toContain("--ax-accent: #f5f5f5");
    expect(stylesheet).not.toContain("fonts.googleapis.com");
    expect(stylesheet).not.toContain("99, 102, 241");
    expect(stylesheet).not.toContain("94, 106, 210");
    expect(stylesheet).toContain(".command-backdrop");
    expect(stylesheet).toContain("prefers-reduced-motion: reduce");
  });
});
