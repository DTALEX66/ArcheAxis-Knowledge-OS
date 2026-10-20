// Node标准库只读漂移检查；不替代Python Schema/semantic验收，不生成、安装或执行能力。
import { createHash } from "node:crypto";
import { closeSync, constants, fstatSync, lstatSync, openSync, readSync } from "node:fs";
import { dirname, isAbsolute, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const FAIL = "MANIFEST_PROJECTION_CHECK_FAILED";
const MANIFEST = "config/capability-packages/pdf-extract.manifest.json";
const TARGET = "frontend/src/api/generated/capability-package-details.ts";
const FIXED = [
  "packages/contracts/v2/capability-package.schema.json",
  "scripts/contracts/validate_capability_package.py",
  "scripts/contracts/generate_capability_package_details.py",
  "scripts/contracts/check_capability_package_details.mjs",
  "config/capability-map.v1.json",
  "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
  "services/python-workers/routes.json",
  "crates/archeaxis-api/Cargo.toml",
];
const HEADER = `// Generated from exact builtin manifest and public validator inputs. Declaration only.
import type { CapabilityManifestIdentity, CapabilityPackageManifest } from './capability-package';
export type CapabilityPackageDetail = {
  identity: CapabilityManifestIdentity; manifest: CapabilityPackageManifest; source_path: string;
  validation: 'VALIDATED_DECLARATION'; host_version: string;
  source_authenticity: 'UNVERIFIED'; qualification: 'UNKNOWN'; runtime: 'UNKNOWN';
};
export type CapabilityPackageDetailProjection = {
  sources: { path: string; sha256: string }[]; entries: CapabilityPackageDetail[];
};
export const CAPABILITY_PACKAGE_DETAILS: CapabilityPackageDetailProjection = `;
const sha = bytes => createHash("sha256").update(bytes).digest("hex");
const requireThat = value => { if (!value) throw new Error(FAIL); };

function safeRoot(root) {
  requireThat(typeof root === "string" && isAbsolute(root) && !/^[EF]:[\\/]|^[/\\]{2}/i.test(root));
  root = resolve(root);
  const ancestors = [];
  for (let part = root; ; part = dirname(part)) {
    ancestors.unshift(part);
    if (dirname(part) === part) break;
  }
  for (const part of ancestors) requireThat(!lstatSync(part).isSymbolicLink());
  return root;
}

function readPublic(root, name, limit = 4194304) {
  requireThat(typeof name === "string" && name.length <= 240 && !/[\\:]/.test(name));
  const parts = name.split("/");
  const denied = /^(private|secrets|credentials|sessions?|memor(?:y|ies)|tokens|cookies|auth|data|node_modules|target|dist)$/i;
  requireThat(parts.every(part => /^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(part) && part !== ".." && !denied.test(part)));
  let path = root;
  for (const part of parts) {
    path = join(path, part);
    requireThat(!lstatSync(path).isSymbolicLink()); // 包括Windows junction；读取前拒绝，不跟随到私有/其他盘。
  }
  const fd = openSync(path, constants.O_RDONLY | (constants.O_NOFOLLOW ?? 0));
  try {
    const info = fstatSync(fd);
    requireThat(info.isFile() && info.size <= limit);
    const bytes = Buffer.alloc(limit + 1);
    let length = 0;
    while (length < bytes.length) {
      const count = readSync(fd, bytes, length, bytes.length - length, null);
      if (count === 0) break;
      length += count;
    }
    requireThat(length <= limit);
    return bytes.subarray(0, length);
  } finally { closeSync(fd); }
}

// 有界JSON解析，额外拒绝重复key/depth；不执行TS/代码，不回显解析器输入。
function parseJSON(bytes) {
  const text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  let at = 0;
  const space = () => { while (/\s/.test(text[at] ?? "") && at < text.length) at++; };
  function string() {
    const start = at++;
    while (at < text.length) {
      const char = text[at++];
      if (char === "\\") { at++; continue; }
      if (char === '"') return JSON.parse(text.slice(start, at));
    }
    throw new Error(FAIL);
  }
  function value(depth) {
    requireThat(depth <= 64); space();
    if (text[at] === '"') return string();
    if (text[at] === "{" || text[at] === "[") {
      const object = text[at++] === "{";
      const close = object ? "}" : "]";
      const keys = new Set();
      space(); if (text[at] === close) { at++; return; }
      while (at < text.length) {
        if (object) {
          space(); requireThat(text[at] === '"');
          const key = string(); requireThat(!keys.has(key)); keys.add(key);
          space(); requireThat(text[at++] === ":");
        }
        value(depth + 1); space();
        const char = text[at++];
        if (char === close) return;
        requireThat(char === ",");
      }
      throw new Error(FAIL);
    }
    const start = at;
    while (at < text.length && !/[,}\]\s]/.test(text[at])) at++;
    requireThat(at > start); JSON.parse(text.slice(start, at));
  }
  value(0); space(); requireThat(at === text.length);
  return JSON.parse(text);
}

function publicReference(ref, contractsOnly) {
  requireThat(ref && typeof ref === "object" && Object.keys(ref).sort().join() === "path,sha256");
  requireThat(typeof ref.sha256 === "string" && /^[a-f0-9]{64}$/.test(ref.sha256));
  requireThat(typeof ref.path === "string" && (contractsOnly
    ? /^packages\/contracts\/[A-Za-z0-9/_.-]+\.schema\.json$/.test(ref.path)
    : /^(LICENSE|THIRD_PARTY_NOTICES\.md|docs\/[A-Za-z0-9/_.-]+\.(md|json|yaml)|packages\/contracts\/[A-Za-z0-9/_.-]+\.schema\.json)$/.test(ref.path)));
  return ref.path;
}

/** 只核对已生成的声明字节与固定公共输入；不能由此授予真实性、许可或执行资格。 */
export function checkCapabilityPackageDetails(root) {
  try {
    root = safeRoot(root);
    const raw = readPublic(root, MANIFEST, 262144);
    const manifest = parseJSON(raw);
    requireThat(manifest.schema === "archeaxis.capability-package/v1" && manifest.declaration === "DECLARATION_ONLY");
    requireThat(typeof manifest.package_id === "string" && manifest.package_id.length <= 96);
    requireThat(typeof manifest.version === "string" && /^(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})$/.test(manifest.version));
    const paths = new Set([...FIXED, MANIFEST]);
    requireThat(Array.isArray(manifest.compatibility?.contract_refs) && manifest.compatibility.contract_refs.length <= 16);
    requireThat(Array.isArray(manifest.license?.notice_refs) && manifest.license.notice_refs.length <= 8);
    requireThat(Array.isArray(manifest.inputs) && manifest.inputs.length <= 8 && Array.isArray(manifest.outputs) && manifest.outputs.length <= 8);
    for (const items of [manifest.compatibility.contract_refs, manifest.license.notice_refs, manifest.inputs, manifest.outputs]) {
      requireThat(new Set(items.map(item => JSON.stringify(item))).size === items.length);
    }
    const refs = [...manifest.compatibility.contract_refs, ...manifest.inputs.map(x => x.contract), ...manifest.outputs.map(x => x.contract)];
    for (const ref of refs) {
      paths.add(publicReference(ref, true));
      requireThat(sha(readPublic(root, ref.path)) === ref.sha256);
    }
    for (const ref of manifest.license.notice_refs) {
      paths.add(publicReference(ref, false));
      requireThat(sha(readPublic(root, ref.path)) === ref.sha256);
    }
    const sources = [...paths].sort().map(path => ({ path, sha256: sha(readPublic(root, path)) }));
    const cargo = new TextDecoder("utf-8", { fatal: true }).decode(readPublic(root, "crates/archeaxis-api/Cargo.toml"));
    const packageSection = cargo.split(/^\[package\]\s*$/m)[1]?.split(/^\[/m)[0];
    const versions = [...(packageSection ?? "").matchAll(/^version\s*=\s*"([0-9]+\.[0-9]+\.[0-9]+)"\s*$/gm)];
    requireThat(versions.length === 1);
    const expected = { sources, entries: [{
      identity: { schema: manifest.schema, package_id: manifest.package_id, version: manifest.version, sha256: sha(raw) },
      manifest, source_path: MANIFEST, validation: "VALIDATED_DECLARATION", host_version: versions[0][1],
      source_authenticity: "UNVERIFIED", qualification: "UNKNOWN", runtime: "UNKNOWN",
    }] };
    const target = readPublic(root, TARGET, 524288);
    const output = new TextDecoder("utf-8", { fatal: true }).decode(target);
    requireThat(output.startsWith(HEADER) && output.endsWith(";\n"));
    const projection = parseJSON(Buffer.from(output.slice(HEADER.length, -2)));
    // sources路径永不来自projection；完整目标必须匹配从固定实际来源重建的只读投影。
    requireThat(JSON.stringify(projection) === JSON.stringify(expected));
    requireThat(output === HEADER + JSON.stringify(expected, null, 2) + ";\n");
    return true;
  } catch { throw new Error(FAIL); }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    requireThat(process.argv.length === 2 || (process.argv.length === 3 && process.argv[2] === "--check"));
    checkCapabilityPackageDetails(resolve(dirname(fileURLToPath(import.meta.url)), "../.."));
  } catch { console.error(FAIL); process.exitCode = 1; }
}
