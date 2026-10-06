// @vitest-environment node
import { readdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, relative, sep } from "node:path";
import { describe, expect, it } from "vitest";

const src = join(dirname(fileURLToPath(import.meta.url)), "..");
function styles(dir: string, found: string[] = []): string[] {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) styles(full, found);
    else if (/\.css$/.test(entry.name)) found.push(readFileSync(full, "utf8"));
  }
  return found;
}
const sheet = styles(src).join("\n");

function sources(dir: string, found: string[] = []): string[] {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) sources(full, found);
    else if (/\.(tsx|ts)$/.test(entry.name)) found.push(full);
  }
  return found;
}

function unstyledClasses(file: string): string[] {
  const source = readFileSync(file, "utf8");
  const missing = new Set<string>();
  for (const match of source.matchAll(/className="([^"{}]+)"/g)) {
    for (const name of match[1].split(/\s+/)) {
      if (name && !new RegExp("\." + name + "(?![-\w])").test(sheet)) missing.add(name);
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
        unstyledClasses(file).map(
          (name) => `${relative(src, file).split(sep).join("/")}: .${name}`,
        ),
      );
    expect(gaps).toEqual([]);
  });
});
