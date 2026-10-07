import { AAOS_THEMES } from "../design-system/theme";
import { useAaosTheme } from "../design-system/ThemeProvider";

export function ThemePicker() {
  const { theme, setTheme } = useAaosTheme();

  return <label className="theme-picker">
    <span className="sr-only">界面主题</span>
    <select aria-label="界面主题" value={theme} onChange={(event) => {
      setTheme(event.currentTarget.value as typeof theme);
    }}>
      {AAOS_THEMES.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
    </select>
  </label>;
}
