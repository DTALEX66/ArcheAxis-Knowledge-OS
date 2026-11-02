import { openMaicFixture } from "./openmaic";

/** Synthetic manifest shaped like the OpenMAIC 1.3.0 classroom export and DSL slide. */
export function openMaic13Fixture() {
  const legacy = openMaicFixture();
  return { ...legacy, appVersion: "1.3.0", scenes: [
    { type: "slide", title: "来源与证据", order: 0, actions: [], whiteboards: [],
      content: { type: "slide", schemaVersion: 1, canvas: {
        id: "slide1", viewportSize: 1000, viewportRatio: 0.5625,
        theme: { backgroundColor: "#ffffff", themeColors: ["#5b9bd5"], fontColor: "#333333",
          fontName: "Microsoft YaHei", shadow: { h: 0, v: 0, blur: 10, color: "#000000" } },
        background: { type: "solid", color: "#ffffff" },
        elements: [{ type: "text", id: "text1", left: 100, top: 80, width: 800, height: 60, rotate: 0,
          content: "<p>核对原件 &amp; 来源</p>", defaultFontName: "Microsoft YaHei", defaultColor: "#222222" }],
      } } },
    { ...legacy.scenes[0], order: 1 },
  ] };
}
export const fixture13Bytes = () => new TextEncoder().encode(JSON.stringify(openMaic13Fixture()));
