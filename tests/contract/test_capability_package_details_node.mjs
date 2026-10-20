// 内置Node runner；仅自有ignored fixture，不安装依赖、不启动服务。
import { test } from "node:test";
import assert from "node:assert/strict";
import { copyFileSync, mkdirSync, mkdtempSync, readFileSync, renameSync, symlinkSync, unlinkSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import { checkCapabilityPackageDetails } from "../../scripts/contracts/check_capability_package_details.mjs";
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const OUTPUT = join(ROOT, ".project-local", "node-manifest-guard-cases");
const MANIFEST = "config/capability-packages/pdf-extract.manifest.json";
const TARGET = "frontend/src/api/generated/capability-package-details.ts";
const FIXED = [MANIFEST, TARGET,
  "packages/contracts/v2/capability-package.schema.json",
  "packages/contracts/v1/core-document.schema.json",
  "scripts/contracts/validate_capability_package.py",
  "scripts/contracts/generate_capability_package_details.py",
  "scripts/contracts/check_capability_package_details.mjs",
  "config/capability-map.v1.json",
  "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
  "services/python-workers/routes.json", "crates/archeaxis-api/Cargo.toml",
];
function fixture() {
  mkdirSync(OUTPUT, { recursive: true });
  const root = mkdtempSync(join(OUTPUT, "owned-"));
  for (const name of FIXED) {
    mkdirSync(dirname(join(root, name)), { recursive: true });
    copyFileSync(join(ROOT, name), join(root, name));
  }
  return root;
}
function rejected(root) {
  assert.throws(() => checkCapabilityPackageDetails(root), error => error.message === "MANIFEST_PROJECTION_CHECK_FAILED");
}
test("guard succeeds from frontend cwd with no usable Python and empty PATH", () => {
  const root = fixture();
  const child = spawnSync(process.execPath, [join(root, "scripts/contracts/check_capability_package_details.mjs"), "--check"], {
    cwd: join(root, "frontend"), encoding: "utf8",
    env: { ...process.env, PATH: "", ARCHEAXIS_PYTHON: join(root, "NO_PYTHON_EXISTS.exe") },
  });
  assert.equal(child.status, 0); assert.equal(child.stdout, ""); assert.equal(child.stderr, "");
});
test("manifest raw whitespace drift is rejected and exact restoration succeeds", () => {
  const root = fixture(), path = join(root, MANIFEST), original = readFileSync(path);
  writeFileSync(path, Buffer.concat([original, Buffer.from(" ")])); rejected(root);
  writeFileSync(path, original); assert.equal(checkCapabilityPackageDetails(root), true);
});
test("fixed validator generator host and schema drift cannot keep old projection", () => {
  for (const name of ["scripts/contracts/validate_capability_package.py", "scripts/contracts/generate_capability_package_details.py", "scripts/contracts/check_capability_package_details.mjs", "crates/archeaxis-api/Cargo.toml", "packages/contracts/v2/capability-package.schema.json"]) {
    const root = fixture(), path = join(root, name);
    writeFileSync(path, Buffer.concat([readFileSync(path), Buffer.from("\n")])); rejected(root);
  }
});
test("tampered sources cannot grant private path reads or duplicate source identity", () => {
  for (const change of [text => text.replace('"config/capability-map.v1.json"', '"docs/private/SYNTHETIC_SECRET.json"'), text => text.replace('"sources": [', '"sources": [{"path":"docs/private/SYNTHETIC_SECRET.json","sha256":"' + "0".repeat(64) + '"},'), text => text.replace(/("sources": \[\n)(    \{[\s\S]*?\n    \},\n)/, "$1$2$2")]) {
    const root = fixture(), path = join(root, TARGET);
    writeFileSync(path, change(readFileSync(path, "utf8"))); rejected(root);
  }
});
test("generated runtime flags identity manifest payload header and suffix tampering fail", () => {
  for (const change of [text => text.replace('"runtime": "UNKNOWN"', '"runtime": "AVAILABLE"'), text => text.replace('"package_id": "archeaxis.pdf-extract"', '"package_id": "forged"'), text => text.replace("Declaration only.", "Approved runtime."), text => text + "\nthrow new Error('SYNTHETIC_PRIVATE_VALUE');\n"]) {
    const root = fixture(), path = join(root, TARGET);
    writeFileSync(path, change(readFileSync(path, "utf8"))); rejected(root);
  }
});
test("duplicate JSON keys and excessive nesting are rejected without evaluation", () => {
  const root = fixture(), path = join(root, MANIFEST), raw = readFileSync(path, "utf8");
  writeFileSync(path, raw.replace('"schema":', '"schema":"duplicate","schema":')); rejected(root);
  writeFileSync(path, "[".repeat(66) + "0" + "]".repeat(66)); rejected(root);
});
test("public references cannot escape to protected absolute private or traversal paths", () => {
  for (const path of ["E:/SYNTHETIC_PRIVATE_VALUE", "F:/SYNTHETIC_PRIVATE_VALUE", "../outside.schema.json", "packages/contracts/../private/a.schema.json", "docs/private/SYNTHETIC_SECRET.json"]) {
    const root = fixture(), file = join(root, MANIFEST), value = JSON.parse(readFileSync(file, "utf8"));
    value.compatibility.contract_refs[0].path = path;
    writeFileSync(file, JSON.stringify(value)); rejected(root);
  }
});
test("missing and oversized fixed source or target are bounded failures", () => {
  let root = fixture(); unlinkSync(join(root, "services/python-workers/routes.json")); rejected(root);
  root = fixture(); writeFileSync(join(root, "scripts/contracts/validate_capability_package.py"), Buffer.alloc(4194305)); rejected(root);
  root = fixture(); writeFileSync(join(root, TARGET), Buffer.alloc(524289)); rejected(root);
});
test("linked public schema directory is rejected before reading its target", () => {
  const root = fixture(), original = join(root, "packages/contracts/v1"), moved = join(root, "owned-linked-source");
  renameSync(original, moved);
  symlinkSync(moved, original, process.platform === "win32" ? "junction" : "dir");
  rejected(root);
});

test("Git clean checkout preserves declaration identity and frozen archive bytes", () => {
  const root = fixture();
  const frozen = [
    "docs/history/owner-dialogue-20261019/README.md",
    "docs/history/owner-dialogue-20261019/decision-coverage.json",
    "docs/history/oss-absorption-evidence/20261019-companion-policy/task-delta.diff",
  ];
  const names = [".gitattributes", ...frozen];
  for (const name of names) {
    mkdirSync(dirname(join(root, name)), { recursive: true });
    copyFileSync(join(ROOT, name), join(root, name));
  }
  const originals = new Map([MANIFEST, ...frozen].map(name => [name, readFileSync(join(root, name))]));
  function git(args) {
    const env = { ...process.env };
    // 父进程可能带有真实仓库的 Git 定位；fixture 子进程不能继承其 index/worktree/object 路由。
    for (const key of Object.keys(env)) if (key.toUpperCase().startsWith("GIT_")) delete env[key];
    const child = spawnSync("git", ["-c", "core.safecrlf=false", ...args], { cwd: root, encoding: "utf8", env });
    assert.equal(child.status, 0, `isolated Git fixture failed: ${child.stderr}`);
  }
  git(["init", "--quiet"]);
  git(["add", "--", ...FIXED, ...names]);
  const checkout = join(root, "owned-checkout");
  git(["checkout-index", "--all", "--force", "--prefix=" + checkout.replaceAll("\\", "/") + "/"]);
  // Execute the actual guard against clean checkout bytes; no generated payload is evaluated.
  assert.equal(checkCapabilityPackageDetails(checkout), true);
  for (const [name, before] of originals) assert.deepEqual(readFileSync(join(checkout, name)), before, name);
  // Preserve strict raw identity: a later byte change must still fail.
  const path = join(checkout, MANIFEST);
  writeFileSync(path, Buffer.concat([readFileSync(path), Buffer.from(" ")]));
  rejected(checkout);
});
