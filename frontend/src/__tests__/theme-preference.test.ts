import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { AAOS_THEMES, applyTheme, readThemePreference, writeThemePreference } from "../design-system/theme";

describe("AAOS theme preferences", () => {
  it("exposes exactly the three owner-approved cool themes", () => {
    expect(AAOS_THEMES.map((theme) => theme.id)).toEqual(["black", "white", "cosmic"]);
  });

  it("persists UI preference only and tolerates unavailable storage", () => {
    const values = new Map<string, string>();
    const storage = { getItem: (key: string) => values.get(key) ?? null, setItem: (key: string, value: string) => values.set(key, value) };
    expect(readThemePreference(storage)).toBe("black");
    writeThemePreference("white", storage);
    expect(readThemePreference(storage)).toBe("white");
    expect(readThemePreference({ getItem: () => "warm-white" })).toBe("black");
    expect(() => readThemePreference({ getItem: () => { throw new Error("disabled"); } })).not.toThrow();
    expect(() => writeThemePreference("cosmic", { setItem: () => { throw new Error("disabled"); } })).not.toThrow();
  });

  it("applies theme to the root without persisting business data", () => {
    const root = document.createElement("html");
    applyTheme("cosmic", root);
    expect(root.dataset.aaosTheme).toBe("cosmic");
  });

  it("keeps cold surfaces and independently identifiable success, warning and danger semantics", () => {
    const css = readFileSync(resolve(process.cwd(), "frontend/src/design-system/themes.css"), "utf8");
    const block = (id: string) => {
      const start = css.indexOf(`:root[data-aaos-theme="${id}"]`);
      const end = css.indexOf("\n}", start);
      expect(start).toBeGreaterThanOrEqual(0);
      expect(end).toBeGreaterThan(start);
      return css.slice(start, end);
    };
    for (const [id, warning] of [["black", "#aebed5"], ["white", "#53657d"], ["cosmic", "#b7c8e5"]]) {
      const theme = block(id);
      expect(theme).toContain(`--aaos-warning: ${warning};`);
      expect(theme).toMatch(/--aaos-success:\s*#[0-9a-f]{6};/i);
      expect(theme).toMatch(/--aaos-danger:\s*#[0-9a-f]{6};/i);
      const statuses = ["success", "warning", "danger"].map((name) => theme.match(new RegExp(`--aaos-${name}:\\s*(#[0-9a-f]{6});`, "i"))?.[1]);
      expect(new Set(statuses).size).toBe(3);
      expect(theme).not.toMatch(/cream|ivory|beige|amber|gold|copper|#fff8e7|#fdf6ec|#f5ecd9|#d8b65f/i);
    }
    const pearl = block("white");
    expect(pearl).toContain("--aaos-background: #f4f6fa;");
    expect(pearl).not.toMatch(/ivory|cream|beige|amber|gold|copper|#fff8e7|#fdf6ec|#f5ecd9|#d8b65f/i);
  });
});
