// @vitest-environment node
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const spaces = join(dirname(fileURLToPath(import.meta.url)), "..", "spaces");

/** Brace-matched body of each `catch` clause, up to a sane length. */
function catchBodies(source: string): string[] {
  const bodies: string[] = [];
  for (let index = source.indexOf("catch"); index !== -1; index = source.indexOf("catch", index + 1)) {
    const open = source.indexOf("{", index);
    if (open === -1) break;
    let depth = 0;
    let end = open;
    for (; end < source.length && end - open < 4000; end += 1) {
      if (source[end] === "{") depth += 1;
      else if (source[end] === "}") {
        depth -= 1;
        if (depth === 0) break;
      }
    }
    bodies.push(source.slice(open + 1, end));
  }
  return bodies;
}

// UI-03 ratchet: a failed read must never be rendered as an empty result.
// Conservative by construction — it only inspects catch bodies that clear a list,
// and JSON.parse fallbacks are exempt because they keep the unparsed raw value.
function fabricatesEmptyResult(file: string): string[] {
  const source = readFileSync(join(spaces, file), "utf8");
  return catchBodies(source)
    .filter((body) => /set[A-Z]\w*\(\s*\[\s*\]\s*\)/.test(body))
    .filter((body) => !/JSON\.parse/.test(body))
    .filter((body) => !/setError|setMessage|setFailureReason|failureMessage|coreFailureReason|Unknown/.test(body))
    .map((body) => body.trim().slice(0, 60));
}

describe("a failed read is never presented as an empty result", () => {
  it("across every product page", () => {
    const offenders = readdirSync(spaces)
      .filter((name) => name.endsWith(".tsx"))
      .flatMap((name) => fabricatesEmptyResult(name).map((body) => `${name}: ${body}`));
    expect(offenders).toEqual([]);
  });

  it("detects the shape it claims to guard, so the gate is not vacuous", () => {
    const sample = `async function load() {
  try { const page = await list(); setRows(page.rows); }
  catch { setRows([]); }
}`;
    const withoutFlag = catchBodies(sample).filter((body) => /set[A-Z]\w*\(\s*\[\s*\]\s*\)/.test(body)
      && !/setError|setMessage|setFailureReason|failureMessage|coreFailureReason|Unknown/.test(body));
    expect(withoutFlag).toHaveLength(1);
  });

  it("keeps the vault backup listing honest after a failed read", () => {
    const vault = readFileSync(join(spaces, "VaultSpace.tsx"), "utf8");
    expect(vault).toContain("setBackupsUnknown(true);");
    expect(vault).toContain("备份列表未能读取；这不代表该文件没有备份。");
  });
});
