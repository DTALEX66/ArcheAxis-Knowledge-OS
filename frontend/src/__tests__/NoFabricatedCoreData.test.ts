// @vitest-environment node
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  EXCLUDED_SCOPE_PARTS,
  MIN_NON_WHITESPACE_CHARS_PER_REQUIRED_FILE,
  SCAN_SELF_MATCH_PROBE,
  captureScanError,
  contentFloorViolations,
  emptyArrayAssignmentsInCatch,
  fabricatedCoreIdentities,
  isTsSource,
  listProductFiles,
  scanProductSources,
  withScanFixture,
  type ContentFloor,
  type ProductScanConfig,
} from "./support/productSourceScan";

const here = dirname(fileURLToPath(import.meta.url));
const src = join(here, "..");

// UI-03: identities that only Core may produce. A literal string on the right of one of
// these keys in product source is sample data being presented as a real object. This is a
// static source-pattern guard over committed text — it does not prove that the data the
// running app displays came from Core, and a green run is not a data-authenticity result.
const scan: ProductScanConfig = {
  root: src,
  matches: isTsSource,
  recursive: true,
  // Test and generated material is out of scope; the exclusion is what lets the shared
  // scanner module hold the guarded shapes as data, and it is asserted below.
  excludePathParts: EXCLUDED_SCOPE_PARTS,
  // 63 product modules today; under 40 the scan has lost whole directories of subject.
  minFiles: 40,
  requiredTargets: ["spaces", "components", "app/App.tsx", "main.tsx"],
};

// A fixture tree cannot reach 40 modules, so only the count floor is relaxed there.
// Everything else — root, filter, recursion, exclusions, named subjects — stays the same.
const fixtureConfig = (root: string): ProductScanConfig => ({ ...scan, root, minFiles: 3 });

// Floor, not proof. Named subjects run from ~600 to ~16k non-whitespace characters and
// the whole scanned set is ~343k (measured 2026-10-08); an emptied body is 0.
const contentFloor: ContentFloor = {
  requiredFiles: [
    "main.tsx", "app/App.tsx", "spaces/VaultSpace.tsx", "spaces/SpaceView.tsx", "components/Inspector.tsx",
  ],
  minCharsPerRequiredFile: MIN_NON_WHITESPACE_CHARS_PER_REQUIRED_FILE,
  minTotalChars: 50_000,
};

const REAL_SOURCE = "export function Card({ card }: { card: CardDto }) {\n  return <div>{card.knowledge_id}</div>;\n}\n";
const FABRICATED_SOURCE = 'export const sampleCards = [{ knowledge_id: "card_demo", document_id: \'doc_demo\' }];\n';
/** The two hits `fabricatedCoreIdentities` reports for that source, in report order. */
const FABRICATED_HITS = ['knowledge_id: "', "document_id: '"];
const SAMPLE_HITS = ['source_id: "', "document_id: '"];

const fixtureTree = (overrides: Record<string, string> = {}): Record<string, string> => ({
  "main.tsx": REAL_SOURCE,
  "app/App.tsx": REAL_SOURCE,
  "spaces/VaultSpace.tsx": REAL_SOURCE,
  "spaces/SpaceView.tsx": REAL_SOURCE,
  "components/Inspector.tsx": REAL_SOURCE,
  ...overrides,
});

const emptiedTree = (): Record<string, string> => Object.fromEntries(
  ["main.tsx", "app/App.tsx", "spaces/VaultSpace.tsx", "spaces/SpaceView.tsx", "spaces/LibrarySpace.tsx", "components/Inspector.tsx"]
    .map((path): [string, string] => [path, ""]),
);

describe("static guard: no product source writes a Core-owned identity as a literal", () => {
  it("scans the product source, not just the pages someone remembered", () => {
    const files = listProductFiles(scan);
    expect(files.length).toBeGreaterThanOrEqual(scan.minFiles);
    const relativePaths = files.map((file) => file.slice(src.length + 1).split("\\").join("/"));
    // Named subjects are in the scanned set as files, not merely as directory names.
    expect(relativePaths).toContain("app/App.tsx");
    expect(relativePaths).toContain("main.tsx");
    expect(relativePaths.filter((path) => path.startsWith("spaces/")).length).toBeGreaterThan(1);
    expect(relativePaths.filter((path) => path.startsWith("components/")).length).toBeGreaterThan(1);
    // Exclusion must be real, or this gate would be asserting on its own test material.
    expect(relativePaths.some((path) => path.includes("__tests__"))).toBe(false);
    expect(relativePaths.some((path) => path.includes("generated"))).toBe(false);
  });

  it("finds no Core-owned identity written as a literal value", () => {
    expect(scanProductSources(scan, fabricatedCoreIdentities)).toEqual([]);
  });

  it("guards scanned files that still contain real source", () => {
    expect(contentFloorViolations(scan, contentFloor)).toEqual([]);
  });

  it("keeps the scanner's own pattern literals out of scope by exclusion, not by luck", () => {
    const supportPath = join(here, "support", "productSourceScan.ts");
    const supportRelative = "__tests__/support/productSourceScan.ts";
    // 1. The shared module really does carry both guarded shapes in its bytes.
    const supportSource = readFileSync(supportPath, "utf8");
    expect(fabricatedCoreIdentities(supportSource).length).toBeGreaterThan(0);
    expect(emptyArrayAssignmentsInCatch(supportSource).length).toBeGreaterThan(0);
    // 2. The product scan therefore cannot see it — and that is the load-bearing exclusion.
    expect(listProductFiles(scan)).not.toContain(supportPath);
    // 3. Same scan, exclusion removed: the scanner flags its own module. Without the
    //    exclusion this gate would be RED for holding its patterns in one place.
    const unscoped = scanProductSources({ ...scan, excludePathParts: [] }, fabricatedCoreIdentities);
    expect(unscoped.some((violation) => violation.file === supportRelative)).toBe(true);
    // 4. And the probe shape itself is what both predicates match.
    expect(fabricatedCoreIdentities(SCAN_SELF_MATCH_PROBE)).toEqual(SAMPLE_HITS);
    expect(emptyArrayAssignmentsInCatch(SCAN_SELF_MATCH_PROBE)).toHaveLength(1);
  });

  it("detects the shape it guards through the same predicate the scan runs", () => {
    // No re-implemented predicate here: this is the function scanProductSources applied.
    expect(fabricatedCoreIdentities('const sample = [{ source_id: "src_demo", document_id: \'doc_demo\' }];')).toEqual(SAMPLE_HITS);
  });

  it("does not flag the two honest shapes found in the real code", () => {
    // A template derived from an actual digest, and a ternary operand rather than a property.
    expect(fabricatedCoreIdentities("enqueue({ job_id: `folder-${digest.slice(0, 12)}`, kind });")).toEqual([]);
    expect(fabricatedCoreIdentities('{ label: typeof promotion.knowledge_id === "string" ? promotion.knowledge_id : "回执未提供 knowledge_id" }')).toEqual([]);
  });

  it("flags the planted literal in a file the scan actually reads", () => {
    const violations = withScanFixture(fixtureTree({ "spaces/ExchangeSpace.tsx": FABRICATED_SOURCE }), (root) => {
      return scanProductSources(fixtureConfig(root), fabricatedCoreIdentities);
    });
    expect(violations).toEqual([
      { file: "spaces/ExchangeSpace.tsx", detail: FABRICATED_HITS[0] },
      { file: "spaces/ExchangeSpace.tsx", detail: FABRICATED_HITS[1] },
    ]);
  });

  it("errors instead of passing when the scan root does not exist", () => {
    const missing = join(src, "no-such-directory");
    expect(captureScanError(() => listProductFiles({ ...scan, root: missing })).code).toBe("root-missing");
    expect(captureScanError(() => scanProductSources({ ...scan, root: missing }, fabricatedCoreIdentities)).code).toBe("root-missing");
  });

  it("errors instead of passing when the scanned set is empty", () => {
    const error = withScanFixture({}, (root) => captureScanError(() => scanProductSources(fixtureConfig(root), fabricatedCoreIdentities)));
    expect(error.code).toBe("no-files-matched");
    expect(error.matchedFiles).toBe(0);
  });

  it("errors instead of passing when nothing in scope matches the extension filter", () => {
    const error = withScanFixture(
      { "readme.md": "# product", "spaces/data.json": "{}", "components/panel.css": ".a{}", "app/App.jsx": FABRICATED_SOURCE },
      (root) => captureScanError(() => scanProductSources(fixtureConfig(root), fabricatedCoreIdentities)),
    );
    expect(error.code).toBe("no-files-matched");
  });

  it("errors instead of passing when the scope shrinks below its floor", () => {
    // Plant the shrunken-scope condition: a real tree of 5 modules against a floor of 6.
    const error = withScanFixture(fixtureTree(), (root) => {
      return captureScanError(() => scanProductSources({ ...fixtureConfig(root), minFiles: 6 }, fabricatedCoreIdentities));
    });
    expect(error.code).toBe("below-file-floor");
    expect(error.matchedFiles).toBe(5);
  });

  it("errors instead of passing when a required named subject is absent", () => {
    const files = fixtureTree();
    delete files["components/Inspector.tsx"];
    const error = withScanFixture(files, (root) => captureScanError(() => listProductFiles(fixtureConfig(root))));
    expect(error.code).toBe("required-target-missing");
    expect(error.message).toContain("components");
  });

  it("errors instead of passing when a required subject is a file that is not in scope", () => {
    const files = fixtureTree();
    delete files["app/App.tsx"];
    const error = withScanFixture({ ...files, "app/notes.md": "# not source" }, (root) => captureScanError(() => listProductFiles(fixtureConfig(root))));
    expect(error.code).toBe("required-target-missing");
    expect(error.message).toContain("app/App.tsx");
  });

  it("turns red on emptied product bodies, which the pattern scan alone cannot see", () => {
    const result = withScanFixture(emptiedTree(), (root) => {
      const config = fixtureConfig(root);
      // Characterisation of the audited blind spot: file names survive an emptying, so the
      // offender list is still empty and the old guards still passed. The content guard is
      // what fails, and it is the same scanned set.
      return { pattern: scanProductSources(config, fabricatedCoreIdentities), content: contentFloorViolations(config, contentFloor) };
    });
    expect(result.pattern).toEqual([]);
    const flagged = result.content.map((violation) => violation.file);
    for (const required of contentFloor.requiredFiles) expect(flagged).toContain(required);
    expect(result.content.some((violation) => violation.detail.includes("the product source has no content left"))).toBe(true);
  });

  it("turns red on a full mirror of the real product tree with its bodies emptied", () => {
    // The audited experiment, reproduced: the real scanned file names, 0 bytes each.
    const realFiles = listProductFiles(scan);
    const mirror = Object.fromEntries(realFiles
      .map((file) => [file.slice(src.length + 1).split("\\").join("/"), ""] as [string, string]));
    const result = withScanFixture(mirror, (root) => {
      const config = { ...scan, root };
      return {
        // Names survive an emptying, so the scope guards alone still pass. That is the
        // audited blind spot, and the reason the content guard exists next to them.
        scopeStillPasses: (() => {
          try {
            listProductFiles(config);
            return true;
          } catch {
            return false;
          }
        })(),
        pattern: scanProductSources(config, fabricatedCoreIdentities),
        content: contentFloorViolations(config, contentFloor),
      };
    });
    expect(Object.keys(mirror).length).toBe(realFiles.length);
    expect(result.scopeStillPasses).toBe(true);
    expect(result.pattern).toEqual([]);
    expect(result.content.map((violation) => violation.file))
      .toEqual(expect.arrayContaining([...contentFloor.requiredFiles]));
    expect(result.content.some((violation) => violation.detail.includes("has no content left"))).toBe(true);
  });

  it("turns red when product bodies are hollowed to comments rather than deleted", () => {
    const realFiles = listProductFiles(scan);
    const stubs = Object.fromEntries(realFiles
      .map((file) => [file.slice(src.length + 1).split("\\").join("/"), "// migrated"] as [string, string]));
    const result = withScanFixture(stubs, (root) => {
      const config = { ...scan, root };
      return { files: listProductFiles(config).length, pattern: scanProductSources(config, fabricatedCoreIdentities), content: contentFloorViolations(config, contentFloor) };
    });
    expect(result.files).toBe(realFiles.length);
    expect(result.pattern).toEqual([]);
    expect(result.content.length).toBeGreaterThanOrEqual(contentFloor.requiredFiles.length + 1);
  });

  it("names a required file that has gone missing from the content guard", () => {
    const files = fixtureTree();
    delete files["spaces/SpaceView.tsx"];
    const violations = withScanFixture(files, (root) => contentFloorViolations(fixtureConfig(root), contentFloor));
    expect(violations).toContainEqual({ file: "spaces/SpaceView.tsx", detail: "named required product file is not in the scanned set" });
  });
});
