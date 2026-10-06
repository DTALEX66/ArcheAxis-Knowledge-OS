// @vitest-environment node
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const sheet = [
  new URL("../design-system/tokens.css", import.meta.url),
  new URL("../components/content.css", import.meta.url),
].map((url) => readFileSync(url, "utf8")).join("\n");

function staticClassNames(source: string): string[] {
  const names = new Set<string>();
  for (const match of source.matchAll(/className="([^"{}]+)"/g)) {
    for (const name of match[1].split(/\s+/)) if (name) names.add(name);
  }
  return [...names];
}

// A class name with no rule is invisible styling debt: the element keeps whatever the
// global reset left it with and looks deliberate until someone reads the DOM.
describe("every statically applied class name has a style rule", () => {
  it.each(["CanvasBoard", "ActivityDock", "Inspector", "StatusBar"])(
    "%s",
    (component) => {
      const source = readFileSync(
        new URL(`../components/${component}.tsx`, import.meta.url),
        "utf8",
      );
      const missing = staticClassNames(source).filter((name) => !sheet.includes(`.${name}`));
      expect(missing).toEqual([]);
    },
  );
});
