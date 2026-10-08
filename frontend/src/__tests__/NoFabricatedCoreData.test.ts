// @vitest-environment node
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const src = join(dirname(fileURLToPath(import.meta.url)), "..");

function sources(dir: string, found: string[] = []): string[] {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) sources(full, found);
    else if (/\.tsx?$/.test(entry.name)) found.push(full);
  }
  return found;
}

// UI-03: identities that only Core may produce. A literal string on the right of one of
// these keys in product source is sample data being presented as a real object.
const DOMAIN_KEYS = ["source_id", "document_id", "knowledge_id", "anchor_id", "item_key", "raw_sha256", "content_sha256", "source_revision", "job_id", "card_id", "backup_name", "transform_id"];
const pattern = new RegExp(`(?<![.\\w])(${DOMAIN_KEYS.join("|")})\\s*:\\s*(["'\`])`, "g");

export function fabricatedIdentities(text: string): string[] {
  const found: string[] = [];
  for (const match of text.matchAll(pattern)) {
    const quote = match[2];
    const start = (match.index ?? 0) + match[0].length;
    const end = text.indexOf(quote, start);
    const value = end === -1 ? "" : text.slice(start, end);
    // A template whose value comes from real data (`folder-${digest}`) is not a sample.
    if (value.includes("${")) continue;
    found.push(`${match[1]}: ${quote}`);
  }
  return found;
}

describe("no page presents sample data as a Core object", () => {
  const productFiles = sources(src).filter((file) => !file.includes("__tests__") && !file.includes("generated"));

  it("scans the product source, not just the pages someone remembered", () => {
    expect(productFiles.some((file) => file.includes(join("spaces")))).toBe(true);
    expect(productFiles.some((file) => file.includes(join("components")))).toBe(true);
    expect(productFiles.length).toBeGreaterThan(40);
  });

  it("finds no Core-owned identity written as a literal value", () => {
    const offenders = productFiles
      .flatMap((file) => fabricatedIdentities(readFileSync(file, "utf8")).map((hit) => `${file.slice(src.length + 1)}: ${hit}`));
    expect(offenders).toEqual([]);
  });

  it("detects the shape it claims to guard, so the gate is not vacuous", () => {
    expect(fabricatedIdentities(`const sample = [{ source_id: "src_demo", document_id: 'doc_demo' }];`))
      .toEqual(["source_id: \"", "document_id: '"]);
  });

  it("does not flag the two honest shapes found in the real code", () => {
    // A template derived from an actual digest, and a ternary operand rather than a property.
    expect(fabricatedIdentities("enqueue({ job_id: `folder-${digest.slice(0, 12)}`, kind });")).toEqual([]);
    expect(fabricatedIdentities("{ label: typeof promotion.knowledge_id === \"string\" ? promotion.knowledge_id : \"回执未提供 knowledge_id\" }")).toEqual([]);
  });
});
