// @vitest-environment node
import { readdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, relative, sep } from "node:path";
import { describe, expect, it } from "vitest";

const src = join(dirname(fileURLToPath(import.meta.url)), "..");
const sheet = [
  readFileSync(join(src, "design-system", "tokens.css"), "utf8"),
  readFileSync(join(src, "components", "content.css"), "utf8"),
].join("\n");

function sources(dir: string, found: string[] = []): string[] {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) sources(full, found);
    else if (/\.(tsx|ts)$/.test(entry.name)) found.push(full);
  }
  return found;
}

/** Class names applied as a static string that no rule in `stylesheet` defines. */
export function missingClasses(source: string, stylesheet: string): string[] {
  const missing = new Set<string>();
  for (const match of source.matchAll(/className="([^"{}]+)"/g)) {
    for (const name of match[1].split(/\s+/)) {
      // The leading dot is escaped: without it the regex wildcard let any rule
      // whose selector merely ENDS in the class name (".supercard" for ".card")
      // count as a definition, so a real gap could hide behind a longer name.
      if (name && !new RegExp("\\." + name + "(?![\\w-])").test(stylesheet)) missing.add(name);
    }
  }
  return [...missing];
}

// A class name with no rule anywhere is invisible debt: the element keeps whatever the
// global reset left it with, so a whole screen renders as one undivided run of text.
describe("every statically applied class name resolves to a rule", () => {
  it("across every component and space, not just the ones already known to be styled", () => {
    const gaps = sources(src)
      .filter((file) => !file.includes(`${sep}__tests__${sep}`) && !file.includes("generated"))
      .flatMap((file) =>
        missingClasses(readFileSync(file, "utf8"), sheet).map(
          (name) => `${relative(src, file).split(sep).join("/")}: .${name}`,
        ),
      );
    expect(gaps).toEqual([]);
  });

  it("matches a whole class name, so a longer selector cannot mask a real gap", () => {
    const applied = `className="card"`;
    // The defect this pins: under an unescaped wildcard a rule for a longer name
    // satisfied the lookup for "card", so an unstyled element read as styled.
    expect(missingClasses(applied, ".supercard { color: red }")).toEqual(["card"]);
    expect(missingClasses(applied, ".card { color: red }")).toEqual([]);
    // A hyphen or word character after the name is a different class, not a match.
    expect(missingClasses(applied, ".card-muted { color: red }")).toEqual(["card"]);
  });
});
