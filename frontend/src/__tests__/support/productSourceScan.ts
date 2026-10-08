/**
 * productSourceScan — the one scanning + offender-detection implementation behind the
 * two static source-pattern truth gates:
 *   - `FailedReadIsNotEmptyResult.test.ts` (UI-03 ratchet: a failed read must not be
 *     coded as an empty result)
 *   - `NoFabricatedCoreData.test.ts` (no product source writes a Core-owned identity as
 *     a literal value)
 *
 * WHAT THESE GATES PROVE, STATED NARROWLY: they read committed source text and report
 * whether a forbidden *pattern* appears in the files the scan actually saw. A green run
 * does NOT prove data authenticity, does not prove the UI renders real Core data, and is
 * not a runtime observation. It is a static guard, and it only has force because a scan
 * that sees nothing is an error rather than a pass.
 *
 * Why this module lives under `__tests__/support`: both scans exclude any path segment
 * containing `__tests__`, so the guarded pattern shapes can live here as data without the
 * scanner flagging its own literals. `SCAN_SELF_MATCH_PROBE` below is the control that
 * proves that exclusion is load-bearing rather than luck — see
 * `NoFabricatedCoreData.test.ts`.
 */
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, relative, sep } from "node:path";
import { tmpdir } from "node:os";

/** A scan is only meaningful over a scope it can name. Each config states its own floor. */
export type ProductScanConfig = {
  /** Absolute path of the directory the scan walks. Must exist and be a directory. */
  readonly root: string;
  /** Which basenames count as product source. */
  readonly matches: (name: string) => boolean;
  /** Hard minimum of matched files. Below it the scope shrank without anyone noticing. */
  readonly minFiles: number;
  /**
   * Named subjects of the gate, relative to `root`, in either form:
   * a file that must itself be in the scanned set, or a directory that must contribute
   * at least one scanned file. Absence is a scan failure, not an empty offender list.
   */
  readonly requiredTargets: readonly string[];
  /** Walk subdirectories. Default false. */
  readonly recursive?: boolean;
  /** Path substrings that mark a file as out of scope (test or generated material). */
  readonly excludePathParts?: readonly string[];
};

/** One offender: which scanned file, and what was found in it. */
export type ProductScanViolation = { readonly file: string; readonly detail: string };

/** The four ways a scan can be vacuous, plus the content tripwire codes. */
export type ProductScanVacuumCode =
  | "root-missing"
  | "no-files-matched"
  | "below-file-floor"
  | "required-target-missing";

/**
 * Thrown instead of returning an empty offender list. A vacuous scan that reports
 * "no offenders" is the defect this module exists to remove: with zero files in scope,
 * `expect(offenders).toEqual([])` passes while proving nothing.
 */
export class ProductSourceScanError extends Error {
  readonly code: ProductScanVacuumCode;
  readonly scanRoot: string;
  readonly matchedFiles: number;

  constructor(code: ProductScanVacuumCode, scanRoot: string, matchedFiles: number, message: string) {
    super(`${code}: ${message}`);
    this.name = "ProductSourceScanError";
    this.code = code;
    this.scanRoot = scanRoot;
    this.matchedFiles = matchedFiles;
  }
}

/** Realm-proof guard: vitest module registries can hand back a distinct class identity. */
export function isProductSourceScanError(error: unknown): error is ProductSourceScanError {
  return (
    typeof error === "object"
    && error !== null
    && (error as { name?: unknown }).name === "ProductSourceScanError"
    && typeof (error as { code?: unknown }).code === "string"
  );
}

/** Run a scan that is expected to reject its scope, and return the rejection. */
export function captureScanError(run: () => unknown): ProductSourceScanError {
  try {
    run();
  } catch (error) {
    if (isProductSourceScanError(error)) return error;
    throw error;
  }
  throw new Error("expected a ProductSourceScanError from a vacuous scan, but the scan returned normally");
}

/** Paths that are test material or machine-generated, never product source. */
export const EXCLUDED_SCOPE_PARTS: readonly string[] = ["__tests__", "generated"];

export const isTsxSource = (name: string): boolean => name.endsWith(".tsx");
export const isTsSource = (name: string): boolean => /\.tsx?$/.test(name);

const toPosix = (path: string): string => path.split(sep).join("/");
const relativePosix = (root: string, file: string): string => toPosix(relative(root, file));

/**
 * The scanned file list, or a thrown `ProductSourceScanError`. Every consumer of the
 * offender predicates goes through this, so no test can silently scan nothing.
 */
export function listProductFiles(config: ProductScanConfig): string[] {
  if (!existsSync(config.root) || !statSync(config.root).isDirectory()) {
    throw new ProductSourceScanError(
      "root-missing", config.root, 0,
      `scan root "${config.root}" does not exist as a directory — the gate has no subject at all`,
    );
  }

  const excluded = config.excludePathParts ?? EXCLUDED_SCOPE_PARTS;
  const found: string[] = [];
  const walk = (dir: string): void => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const full = join(dir, entry.name);
      if (entry.isDirectory()) {
        if (config.recursive) walk(full);
      } else if (config.matches(entry.name) && !excluded.some((part) => toPosix(full).includes(part))) {
        found.push(full);
      }
    }
  };
  walk(config.root);
  found.sort();

  if (found.length === 0) {
    throw new ProductSourceScanError(
      "no-files-matched", config.root, 0,
      `scan of "${config.root}" matched 0 files; an empty scan list can never produce an offender, so it must not pass`,
    );
  }
  if (found.length < config.minFiles) {
    throw new ProductSourceScanError(
      "below-file-floor", config.root, found.length,
      `matched ${found.length} files, floor is ${config.minFiles}; the scope shrank under this gate`,
    );
  }

  const scanned = new Set(found.map((file) => relativePosix(config.root, file)));
  for (const target of config.requiredTargets) {
    const normalized = toPosix(target);
    const isScannedFile = scanned.has(normalized);
    const contributesFiles = [...scanned].some((file) => file.startsWith(`${normalized}/`));
    if (!isScannedFile && !contributesFiles) {
      throw new ProductSourceScanError(
        "required-target-missing", config.root, found.length,
        `required target "${target}" contributed no scanned file; the named subject of this gate is gone`,
      );
    }
  }

  return found;
}

/**
 * Apply one predicate to every file in scope. `inspect` must be the same function the
 * reverse tests call on planted samples — that is the only way a control proves the scan
 * runs rather than just proving a regex.
 */
export function scanProductSources(config: ProductScanConfig, inspect: (source: string) => string[]): ProductScanViolation[] {
  return listProductFiles(config)
    .flatMap((file) => inspect(readFileSync(file, "utf8")).map((detail) => ({ file: relativePosix(config.root, file), detail })));
}

/** Non-whitespace characters: whitespace-only padding cannot satisfy a content floor. */
export function compactLength(text: string): number {
  return text.replace(/\s+/g, "").length;
}

/**
 * Floor, not proof: the smallest named required module in this repository is ~600
 * non-whitespace characters (`main.tsx`, measured 2026-10-08), while an emptied or
 * comment-stubbed body is 0-50. 200 therefore trips on "the source was hollowed out" and
 * has real headroom above that. It says nothing about whether the code is correct.
 */
export const MIN_NON_WHITESPACE_CHARS_PER_REQUIRED_FILE = 200;

export type ContentFloor = {
  /** Named product files that must exist in the scanned set and carry real source. */
  readonly requiredFiles: readonly string[];
  readonly minCharsPerRequiredFile: number;
  /** Aggregate floor over the whole scanned set — this is what an emptied tree trips. */
  readonly minTotalChars: number;
};

/**
 * The content guard: a scanned set of correctly named but empty files is reported here.
 * Pattern scans are blind to that by design, so this assertion is what turns the gate red
 * when product bodies are hollowed out.
 */
export function contentFloorViolations(config: ProductScanConfig, floor: ContentFloor): ProductScanViolation[] {
  const measured = listProductFiles(config)
    .map((file) => ({ file: relativePosix(config.root, file), chars: compactLength(readFileSync(file, "utf8")) }));
  const byPath = new Map(measured.map((entry) => [entry.file, entry]));
  const violations: ProductScanViolation[] = [];

  for (const required of floor.requiredFiles) {
    const entry = byPath.get(toPosix(required));
    if (!entry) {
      violations.push({ file: toPosix(required), detail: "named required product file is not in the scanned set" });
      continue;
    }
    if (entry.chars < floor.minCharsPerRequiredFile) {
      violations.push({ file: entry.file, detail: `only ${entry.chars} non-whitespace characters, floor ${floor.minCharsPerRequiredFile}: emptied or stubbed source body` });
    }
  }

  const total = measured.reduce((sum, entry) => sum + entry.chars, 0);
  if (total < floor.minTotalChars) {
    violations.push({ file: toPosix(config.root), detail: `scanned set carries ${total} non-whitespace characters across ${measured.length} files, floor ${floor.minTotalChars}: the product source has no content left` });
  }
  return violations;
}

/**
 * Predicate for the UI-03 ratchet: a `catch` clause that clears a stateful list without
 * naming the failure anywhere in the same clause. JSON.parse fallbacks are exempt because
 * they keep the unparsed raw value.
 */
export function emptyArrayAssignmentsInCatch(source: string): string[] {
  return catchClauseBodies(source)
    .filter((body) => /set[A-Z]\w*\(\s*\[\s*\]\s*\)/.test(body))
    .filter((body) => !/JSON\.parse/.test(body))
    .filter((body) => !/setError|setMessage|setFailureReason|failureMessage|coreFailureReason|Unknown/.test(body))
    .map((body) => body.trim().slice(0, 60));
}

/** Brace-matched body of each `catch` clause, up to a sane length. */
export function catchClauseBodies(source: string): string[] {
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

/** Identities that only Core may produce. */
export const CORE_OWNED_IDENTITY_KEYS: readonly string[] = [
  "source_id", "document_id", "knowledge_id", "anchor_id", "item_key", "raw_sha256",
  "content_sha256", "source_revision", "job_id", "card_id", "backup_name", "transform_id",
];

const identityPattern = new RegExp(`(?<![.\\w])(${CORE_OWNED_IDENTITY_KEYS.join("|")})\\s*:\\s*(["'\`])`, "g");

/** Predicate for the no-fabricated-Core-data gate: a Core-owned key given a literal value. */
export function fabricatedCoreIdentities(text: string): string[] {
  const found: string[] = [];
  for (const match of text.matchAll(identityPattern)) {
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

/**
 * Both guarded shapes, as literal source text. A scan that did not exclude `__tests__`
 * would flag this very file on it — which is exactly why the exclusion is asserted, not
 * assumed (see `NoFabricatedCoreData.test.ts`). Written as one template literal so the
 * quotes stay unescaped and the predicates really do match these bytes.
 */
export const SCAN_SELF_MATCH_PROBE = `const sample = [{ source_id: "src_demo", document_id: 'doc_demo' }];
async function load() {
  try { const page = await list(); setRows(page.rows); }
  catch { setRows([]); }
}`;

/** Files a fixture needs: one per line of a relative posix path. */
export function withScanFixture<T>(files: Record<string, string>, run: (root: string) => T): T {
  const root = mkdtempSync(join(tmpdir(), "aak-product-scan-"));
  try {
    for (const [path, content] of Object.entries(files)) {
      const target = join(root, ...path.split("/"));
      mkdirSync(dirname(target), { recursive: true });
      writeFileSync(target, content, "utf8");
    }
    return run(root);
  } finally {
    // Only ever a directory this call created inside os.tmpdir(); never a repo path.
    rmSync(root, { recursive: true, force: true });
  }
}
