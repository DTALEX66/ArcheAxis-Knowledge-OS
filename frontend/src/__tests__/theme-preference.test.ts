import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { basename, resolve } from "node:path";
import { AAOS_THEMES, AAOS_THEME_REGISTRY, BRAND_MARK_SLOT, applyTheme, readThemePreference, writeThemePreference } from "../design-system/theme";

const frontend = basename(process.cwd()) === "frontend" ? process.cwd() : resolve(process.cwd(), "frontend");

describe("AAOS theme preferences", () => {
  it("exposes exactly the three owner-approved cool themes", () => {
    expect(AAOS_THEMES.map((theme) => theme.id)).toEqual(["black", "white", "cosmic"]);
  });

  it("maps one real AAOS brand mark to each theme through the shared registry", () => {
    expect(Object.keys(AAOS_THEME_REGISTRY)).toEqual(AAOS_THEMES.map(({ id }) => id));
    for (const theme of AAOS_THEMES) {
      const mark = AAOS_THEME_REGISTRY[theme.id].brandMark;
      expect(mark).toMatch(/aaos-brand-mark-(black|white|cosmic)\.png$/);
      const bytes = readFileSync(resolve(frontend, "src/assets", basename(mark)));
      expect(bytes.subarray(1, 4).toString("latin1")).toBe("PNG");
      // IHDR carries the canvas size, so the artwork itself is checked against the box the status
      // bar draws it in: a re-cut at another ratio would squash the logo and no DOM assertion sees
      // that, because the element keeps whatever width it was given.
      const [width, height] = [bytes.readUInt32BE(16), bytes.readUInt32BE(20)];
      expect(Math.abs(width / height - BRAND_MARK_SLOT.width / BRAND_MARK_SLOT.height)).toBeLessThan(0.01);
      expect(height).toBeGreaterThanOrEqual(BRAND_MARK_SLOT.height * 4);
    }
    expect(new Set(Object.values(AAOS_THEME_REGISTRY).map(({ brandMark }) => brandMark)).size).toBe(3);
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
    const css = readFileSync(resolve(frontend, "src/design-system/themes.css"), "utf8");
    const block = (id: string) => {
      const start = css.indexOf(`:root[data-aaos-theme="${id}"]`);
      const end = css.indexOf("\n}", start);
      expect(start).toBeGreaterThanOrEqual(0);
      expect(end).toBeGreaterThan(start);
      return css.slice(start, end);
    };
    for (const [id, warning] of [["black", "#70c6ff"], ["white", "#14577f"], ["cosmic", "#75d8f4"]]) {
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
    expect(css).toContain(':root[data-aaos-theme="white"] .badge-warning { color: var(--aaos-warning); background: var(--ax-warning-soft); }');
    expect(pearl).not.toMatch(/ivory|cream|beige|amber|gold|copper|#fff8e7|#fdf6ec|#f5ecd9|#d8b65f/i);
  });
});
