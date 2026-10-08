// @vitest-environment node
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  MIN_NON_WHITESPACE_CHARS_PER_REQUIRED_FILE,
  SCAN_SELF_MATCH_PROBE,
  captureScanError,
  contentFloorViolations,
  emptyArrayAssignmentsInCatch,
  isTsxSource,
  listProductFiles,
  scanProductSources,
  withScanFixture,
  type ContentFloor,
  type ProductScanConfig,
} from "./support/productSourceScan";

const here = dirname(fileURLToPath(import.meta.url));
const spaces = join(here, "..", "spaces");

// UI-03 ratchet, as a static source-pattern guard: no `catch` clause in a product page
// may clear a stateful list without naming the failure. Conservative by construction —
// it only inspects catch bodies that clear a list, and JSON.parse fallbacks are exempt
// because they keep the unparsed raw value. This does not prove data authenticity; a
// green run means the scanned product source contains no such shape.
const scan: ProductScanConfig = {
  root: spaces,
  matches: isTsxSource,
  // `spaces` holds neither test nor generated material, so nothing is excluded here.
  excludePathParts: [],
  // 14 page modules today; below 8 the scan would be naming far fewer pages than it claims.
  minFiles: 8,
  requiredTargets: ["VaultSpace.tsx", "SpaceView.tsx"],
};

// Floor, not proof. Smallest named page today is ~2.6k non-whitespace characters and the
// whole scanned set is ~120k (measured 2026-10-08); an emptied body is 0.
const contentFloor: ContentFloor = {
  requiredFiles: [
    "VaultSpace.tsx", "SpaceView.tsx", "LibrarySpace.tsx", "SettingsSpace.tsx",
    "IntakeSpace.tsx", "LearningSpace.tsx",
  ],
  minCharsPerRequiredFile: MIN_NON_WHITESPACE_CHARS_PER_REQUIRED_FILE,
  minTotalChars: 20_000,
};

const PAGE_NAMES = [
  "VaultSpace.tsx", "SpaceView.tsx", "LibrarySpace.tsx", "SettingsSpace.tsx", "IntakeSpace.tsx",
  "LearningSpace.tsx", "AiAssetsSpace.tsx", "EvidenceSpace.tsx", "ExchangeSpace.tsx", "WorkspaceSpace.tsx",
] as const;

/** A page in the honest shape: the list is cleared, and the failure is named in the same clause. */
const CLEAN_PAGE = "export function Page() {\n  const [rows, setRows] = useState<Row[]>([]);\n"
  + "  // Reads the live Core page and names any failure instead of showing an empty list.\n"
  + "  async function load() { try { setRows((await list()).rows); } catch { setRows([]); setError(\"读取失败\"); } }\n"
  + "  return <div>{rows.length}</div>;\n}\n";

/** The shape the ratchet forbids, used only inside temp fixtures and the shared predicate. */
const PLANTED_OFFENDER = "export function Page() {\n  const [rows, setRows] = useState<Row[]>([]);\n"
  + "  // Reads the live Core page and shows an empty list when the read fails.\n"
  + "  async function load() { try { setRows((await list()).rows); } catch { setRows([]); } }\n"
  + "  return <div>{rows.length}</div>;\n}\n";

const emptiedPages = (): Record<string, string> => Object.fromEntries(PAGE_NAMES.map((name): [string, string] => [name, ""]));
const cleanPages = (overrides: Record<string, string> = {}): Record<string, string> =>
  Object.fromEntries(PAGE_NAMES.map((name): [string, string] => [name, overrides[name] ?? CLEAN_PAGE]));

describe("static guard: a failed read is not coded as an empty result", () => {
  it("scans the product pages it claims to cover", () => {
    // listProductFiles throws on an empty scope, a shrunken scope, a missing named
    // subject and a missing root — so reaching these assertions already proves the scan ran.
    const files = listProductFiles(scan);
    expect(files.length).toBeGreaterThanOrEqual(scan.minFiles);
    const scannedNames = files.map((file) => file.slice(spaces.length + 1));
    for (const target of scan.requiredTargets) expect(scannedNames).toContain(target);
  });

  it("finds no catch clause that clears a list without naming the failure", () => {
    expect(scanProductSources(scan, emptyArrayAssignmentsInCatch)).toEqual([]);
  });

  it("guards pages that still contain real source, not hollowed-out shells", () => {
    expect(contentFloorViolations(scan, contentFloor)).toEqual([]);
  });

  it("keeps the vault backup listing honest after a failed read", () => {
    const vault = join(spaces, "VaultSpace.tsx");
    expect(listProductFiles(scan)).toContain(vault);
    const source = readFileSync(vault, "utf8");
    expect(source).toContain("setBackupsUnknown(true);");
    expect(source).toContain("备份列表未能读取；这不代表该文件没有备份。");
    // The exemption is earned, not assumed: this page clears lists and is still clean.
    expect(emptyArrayAssignmentsInCatch(source)).toEqual([]);
  });

  it("detects the shape it guards through the same predicate the scan runs", () => {
    // Same function as the positive scan — no re-implemented predicate inside this test.
    expect(emptyArrayAssignmentsInCatch(PLANTED_OFFENDER)).toHaveLength(1);
    expect(emptyArrayAssignmentsInCatch(SCAN_SELF_MATCH_PROBE)).toHaveLength(1);
    expect(emptyArrayAssignmentsInCatch(CLEAN_PAGE)).toEqual([]);
    // The other two honest shapes the ratchet deliberately spares.
    expect(emptyArrayAssignmentsInCatch("try { x(); } catch { setRows(JSON.parse(raw)); }")).toEqual([]);
    expect(emptyArrayAssignmentsInCatch("try { x(); } catch { setRows([]); setFailureReason(\"core 未响应\"); }")).toEqual([]);
  });

  it("flags the planted offender in a file the scan actually reads", () => {
    const violations = withScanFixture(cleanPages({ "ExchangeSpace.tsx": PLANTED_OFFENDER }), (root) => {
      return scanProductSources({ ...scan, root }, emptyArrayAssignmentsInCatch);
    });
    expect(violations).toEqual([{ file: "ExchangeSpace.tsx", detail: expect.stringContaining("setRows([])") }]);
  });

  it("errors instead of passing when the scan root does not exist", () => {
    const missing = join(spaces, "no-such-directory");
    expect(captureScanError(() => listProductFiles({ ...scan, root: missing })).code).toBe("root-missing");
    // The offender scan is the call the gate makes: it must throw, not return [].
    expect(captureScanError(() => scanProductSources({ ...scan, root: missing }, emptyArrayAssignmentsInCatch)).code).toBe("root-missing");
  });

  it("errors instead of passing when the scanned set is empty", () => {
    const error = withScanFixture({}, (root) => captureScanError(() => scanProductSources({ ...scan, root }, emptyArrayAssignmentsInCatch)));
    expect(error.code).toBe("no-files-matched");
    expect(error.matchedFiles).toBe(0);
  });

  it("errors instead of passing when nothing in scope matches the extension filter", () => {
    const error = withScanFixture(
      { "notes.md": "# nothing", "spaces.ts": "export const SPACES = [];", "VaultSpace.jsx": PLANTED_OFFENDER },
      (root) => captureScanError(() => scanProductSources({ ...scan, root }, emptyArrayAssignmentsInCatch)),
    );
    expect(error.code).toBe("no-files-matched");
  });

  it("errors instead of passing when the scope shrinks below its floor", () => {
    const error = withScanFixture(
      { "VaultSpace.tsx": CLEAN_PAGE, "SpaceView.tsx": CLEAN_PAGE, "LibrarySpace.tsx": CLEAN_PAGE },
      (root) => captureScanError(() => scanProductSources({ ...scan, root }, emptyArrayAssignmentsInCatch)),
    );
    expect(error.code).toBe("below-file-floor");
    expect(error.matchedFiles).toBe(3);
  });

  it("errors instead of passing when a required page is absent", () => {
    const files = Object.fromEntries(PAGE_NAMES.filter((name) => name !== "VaultSpace.tsx")
      .map((name): [string, string] => [name, CLEAN_PAGE]));
    const error = withScanFixture(files, (root) => captureScanError(() => scanProductSources({ ...scan, root }, emptyArrayAssignmentsInCatch)));
    expect(error.code).toBe("required-target-missing");
    expect(error.message).toContain("VaultSpace.tsx");
  });

  it("turns red on emptied product bodies, which the pattern scan alone cannot see", () => {
    const violations = withScanFixture(emptiedPages(), (root) => {
      const config = { ...scan, root };
      // Characterisation of the audited blind spot: with the bodies gone, the offender
      // list is still empty. The content guard below is what makes the gate red.
      const pattern = scanProductSources(config, emptyArrayAssignmentsInCatch);
      return { pattern, content: contentFloorViolations(config, contentFloor) };
    });
    expect(violations.pattern).toEqual([]);
    const thinned = violations.content.map((violation) => violation.file);
    expect(thinned).toContain("VaultSpace.tsx");
    expect(thinned).toContain("SpaceView.tsx");
    expect(violations.content.length).toBeGreaterThanOrEqual(contentFloor.requiredFiles.length + 1);
    expect(violations.content.some((violation) => violation.detail.includes("the product source has no content left"))).toBe(true);
  });

  it("turns red on a mirror of every real product page with its body emptied", () => {
    // The audited experiment, reproduced: same file names as the real scan, 0 bytes each.
    const realPages = listProductFiles(scan).map((file) => file.slice(spaces.length + 1));
    const result = withScanFixture(
      Object.fromEntries(realPages.map((name): [string, string] => [name, ""])),
      (root) => {
        const config = { ...scan, root };
        return { pattern: scanProductSources(config, emptyArrayAssignmentsInCatch), content: contentFloorViolations(config, contentFloor) };
      },
    );
    expect(realPages.length).toBeGreaterThanOrEqual(scan.minFiles);
    expect(result.pattern).toEqual([]);
    expect(result.content.length).toBeGreaterThanOrEqual(contentFloor.requiredFiles.length + 1);
    expect(result.content.some((violation) => violation.detail.includes("the product source has no content left"))).toBe(true);
  });

  it("turns red when product bodies are hollowed to comments rather than deleted", () => {
    const result = withScanFixture(
      Object.fromEntries(PAGE_NAMES.map((name): [string, string] => [name, "// migrated"])),
      (root) => {
        const config = { ...scan, root };
        return { files: listProductFiles(config).length, pattern: scanProductSources(config, emptyArrayAssignmentsInCatch), content: contentFloorViolations(config, contentFloor) };
      },
    );
    expect(result.files).toBe(PAGE_NAMES.length);
    expect(result.pattern).toEqual([]);
    expect(result.content.length).toBeGreaterThanOrEqual(contentFloor.requiredFiles.length + 1);
  });

  it("names a required page that is missing from the content guard too", () => {
    const files = Object.fromEntries(PAGE_NAMES.filter((name) => name !== "SettingsSpace.tsx")
      .map((name): [string, string] => [name, CLEAN_PAGE]));
    const violations = withScanFixture(files, (root) => contentFloorViolations({ ...scan, root }, contentFloor));
    expect(violations).toContainEqual({ file: "SettingsSpace.tsx", detail: "named required product file is not in the scanned set" });
    // The fixture keeps 9 synthetic pages, far below the 20k aggregate floor, so that
    // guard trips here as well; the named-file report above is the point of this control.
    expect(violations.some((violation) => violation.detail.includes("the product source has no content left"))).toBe(true);
  });
});
