export const AAOS_THEMES = [
  { id: "black", label: "黑色" },
  { id: "white", label: "珍珠白" },
  { id: "cosmic", label: "科技／深空／星环" },
] as const;

export type AaosThemeId = (typeof AAOS_THEMES)[number]["id"];
const PREFERENCE_KEY = "aaos.ui.theme.v1";

export function readThemePreference(storage?: Pick<Storage, "getItem">): AaosThemeId {
  try {
    const stored = (storage ?? globalThis.localStorage)?.getItem(PREFERENCE_KEY);
    if (AAOS_THEMES.some((theme) => theme.id === stored)) return stored as AaosThemeId;
  } catch {
    // Private browsing and embedded WebViews may reject localStorage access.
  }
  return "black";
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
