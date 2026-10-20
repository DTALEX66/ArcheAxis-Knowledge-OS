import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrandHeader } from "../components/BrandHeader";
import { TopNavBar } from "../components/TopNavBar";
import { ThemeProvider, useAaosTheme } from "../design-system/ThemeProvider";
import { AAOS_THEMES, AAOS_THEME_REGISTRY, type AaosThemeId } from "../design-system/theme";

afterEach(() => { cleanup(); localStorage.clear(); delete document.documentElement.dataset.aaosTheme; });
function Switch({ theme }: { theme: AaosThemeId }) {
  const { setTheme } = useAaosTheme();
  return <button onClick={() => setTheme(theme)}>切换主题</button>;
}
describe("branding in the active product theme", () => {
  it.each(AAOS_THEMES)("uses the existing $id master in both headers after a live switch", async ({ id }) => {
    localStorage.setItem("aaos.ui.theme.v1", id === "white" ? "black" : "white");
    render(<ThemeProvider><TopNavBar breadcrumbs={[{ label: "今日工作台" }]} /><BrandHeader title="工作台" /><Switch theme={id} /></ThemeProvider>);
    await userEvent.setup().click(screen.getByRole("button", { name: "切换主题" }));
    expect(document.documentElement.dataset.aaosTheme).toBe(id);
    const images = screen.getAllByRole("img", { name: "ArcheAxis" });
    expect(images).toHaveLength(2);
    for (const image of images) expect(image).toHaveAttribute("src", AAOS_THEME_REGISTRY[id].brandMark);
  });
});
