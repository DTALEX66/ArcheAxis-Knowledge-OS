// Cut from the owner's black/white logo master (2026-10-08); see
// docs/current/AAOS-UI-MASTER-ASSET-AUDIT-20261001.md for the source hash and the per-slot sizes.
import blackBrandMark from "../assets/aaos-brand-mark-black.png";
import whiteBrandMark from "../assets/aaos-brand-mark-white.png";
import cosmicBrandMark from "../assets/aaos-brand-mark-cosmic.png";

export const AAOS_THEMES = [
  { id: "blueprint", label: "新设计／深蓝" },
  { id: "blueprint-light", label: "新设计／浅色" },
  { id: "black", label: "黑色" },
  { id: "white", label: "珍珠白" },
  { id: "cosmic", label: "科技／深空／星环" },
] as const;

export type AaosThemeId = (typeof AAOS_THEMES)[number]["id"];

/** Theme-specific decorative resources share one source with the theme IDs. */
export const AAOS_THEME_REGISTRY = {
  blueprint: { id: "blueprint", brandMark: cosmicBrandMark },
  "blueprint-light": { id: "blueprint-light", brandMark: whiteBrandMark },
  black: { id: "black", brandMark: blackBrandMark },
  white: { id: "white", brandMark: whiteBrandMark },
  cosmic: { id: "cosmic", brandMark: cosmicBrandMark },
} as const satisfies Record<AaosThemeId, { id: AaosThemeId; brandMark: string }>;

/** The CSS box the status bar draws the brand mark in. The cut-out carries this aspect, so a
    re-cut at a different ratio shows up as a failed contract test rather than as a squashed logo. */
export const BRAND_MARK_SLOT = { width: 31, height: 28 } as const;

const PREFERENCE_KEY = "aaos.ui.theme.v1";

export function readThemePreference(storage?: Pick<Storage, "getItem">): AaosThemeId {
  try {
    const stored = (storage ?? globalThis.localStorage)?.getItem(PREFERENCE_KEY);
    if (AAOS_THEMES.some((theme) => theme.id === stored)) return stored as AaosThemeId;
  } catch {
    // Private browsing and embedded WebViews may reject localStorage access.
  }
  return "blueprint";
}

export function writeThemePreference(theme: AaosThemeId, storage?: Pick<Storage, "setItem">): void {
  try {
    (storage ?? globalThis.localStorage)?.setItem(PREFERENCE_KEY, theme);
  } catch {
    // The selected theme remains active for this session when storage is unavailable.
  }
}

export function applyTheme(theme: AaosThemeId, root: HTMLElement = document.documentElement): void {
  root.dataset.aaosTheme = theme;
}
