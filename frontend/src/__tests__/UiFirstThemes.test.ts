import { describe, expect, it } from "vitest";
import { AAOS_THEMES, readThemePreference } from "../design-system/theme";

describe("UI-first theme selection", () => {
  it("defaults new profiles to the new design while preserving every existing preference", () => {
    expect(readThemePreference({ getItem: () => null })).toBe("blueprint");
    for (const id of ["black", "white", "cosmic", "blueprint", "blueprint-light"]) {
      expect(AAOS_THEMES.some(theme => theme.id === id)).toBe(true);
      expect(readThemePreference({ getItem: () => id })).toBe(id);
    }
    expect(readThemePreference({ getItem: () => { throw new Error("unavailable"); } })).toBe("blueprint");
  });
});
