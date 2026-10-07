import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { applyTheme, readThemePreference, writeThemePreference, type AaosThemeId } from "./theme";

type ThemeContextValue = { theme: AaosThemeId; setTheme: (theme: AaosThemeId) => void };
const ThemeContext = createContext<ThemeContextValue>({ theme: "black", setTheme: () => {} });

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<AaosThemeId>(() => readThemePreference());
  const setTheme = useCallback((next: AaosThemeId) => {
    setThemeState(next);
    applyTheme(next);
    writeThemePreference(next);
  }, []);
  useEffect(() => applyTheme(theme), [theme]);
  const value = useMemo(() => ({ theme, setTheme }), [setTheme, theme]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useAaosTheme(): ThemeContextValue {
  return useContext(ThemeContext);
}
