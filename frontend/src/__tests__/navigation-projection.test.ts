import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { CAPABILITY_CATALOG } from "../api/generated/capability-catalog";
import {
  EFFECTIVE_NAVIGATION_ENTRIES,
  resolveCapabilityEntry,
  resolveLegacySpaceAlias,
  resolveNavigationHash,
  validateNavigationProjection,
} from "../presentation/navigation";

describe("effective navigation projection", () => {
  it("projects each formal capability once and resolves stable IDs, historical aliases and deep links", () => {
    expect(validateNavigationProjection()).toEqual([]);
    expect(EFFECTIVE_NAVIGATION_ENTRIES.filter((entry) => entry.capability).map((entry) => entry.entry_id))
      .toEqual(CAPABILITY_CATALOG.entries.map((entry) => entry.atlas.capability_id));
    expect(resolveLegacySpaceAlias("home")).toBe("workspace");
    expect(resolveLegacySpaceAlias("#/library")).toBe("library");
    const first = CAPABILITY_CATALOG.entries[0]!;
    expect(resolveCapabilityEntry(first.atlas.capability_id)?.atlas.capability_id).toBe(first.atlas.capability_id);
    expect(resolveNavigationHash(`#capability/${first.atlas.capability_id}`)?.capabilityId).toBe(first.atlas.capability_id);
    expect(resolveNavigationHash(`#capability=${first.atlas.origin_requirement_ids[0]}`)?.capabilityId).toBe(first.atlas.capability_id);
  });

  it("keeps stable capability identity in search independently of fixed catalog count", () => {
    for (const capability of CAPABILITY_CATALOG.entries) {
      const entry = EFFECTIVE_NAVIGATION_ENTRIES.find((item) => item.entry_id === capability.atlas.capability_id);
      expect(entry).toBeDefined();
      expect(entry?.keywords).toEqual(expect.arrayContaining([...capability.atlas.dependencies, ...capability.atlas.entry_gate]));
    }
  });

  it("keeps the checked-in entry matrix aligned with the live read-only projection", () => {
    const matrix = JSON.parse(readFileSync(resolve(process.cwd(), "docs/current/AAOS-UI-CAPABILITY-ENTRY-MATRIX-20261007.json"), "utf8")) as {
      capability_count: number;
      capabilities: Array<{ entry_id: string; route: string; menu_visible: boolean; command_search_visible: boolean; detail_available: boolean; destination_space: string | null; legacy_aliases: Array<{ alias: string; resolves_to_entry_id: string }> }>;
    };
    expect(matrix.capability_count).toBe(CAPABILITY_CATALOG.entries.length);
    expect(matrix.capabilities.map((item) => item.entry_id)).toEqual(CAPABILITY_CATALOG.entries.map((item) => item.atlas.capability_id));
    for (const row of matrix.capabilities) {
      const entry = EFFECTIVE_NAVIGATION_ENTRIES.find((item) => item.entry_id === row.entry_id);
      expect(entry).toBeDefined();
      expect(row).toMatchObject({ route: `#capability/${row.entry_id}`, menu_visible: true, command_search_visible: true, detail_available: true, destination_space: entry?.destination ?? null });
      for (const alias of row.legacy_aliases) expect(resolveCapabilityEntry(alias.alias)?.atlas.capability_id).toBe(alias.resolves_to_entry_id);
    }
  });
});
