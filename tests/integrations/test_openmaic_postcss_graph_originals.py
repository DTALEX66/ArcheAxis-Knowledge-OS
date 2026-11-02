"""Offline locked PostCSS graph identity and behavior; not product qualification.

The Node probe owns a synthetic temporary package layout. Its resolution hook
is a test fixture, not a production loader or an OS sandbox. No package scripts,
network, OpenMAIC model call, or generated interactive content are executed.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
import threading

import pytest

from scripts.release.tauri_portable_candidate import native
from tests.integrations.test_openmaic_npm_git_ignore import (
    configuration_environments,
    ignored_paths,
    invoke_git,
    require_readable_effective_excludes,
)


ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / "services/learning-providers/openmaic/vendor/npm"
CACHE = (ROOT / ".project-local/cache/npm"
         / "openmaic-owner-4660cd2b97ac2a3862cd238fc28b54195a622c8beabb87c9185d87f626f47a29")
NODE = os.environ.get("ARCHEAXIS_TEST_NODE")
NODE_SHA256 = "ba4e6d110e8c1592a1ecd390f6b05f3da124b13871a5be62b341a07a853c6c32"
AUDIT = "backend-verify-npm-postcss-audit-0e275110cc"
PACKAGES = {
    "postcss-8.5.23": {
        "name": "postcss", "version": "8.5.23", "license": "MIT", "count": 55, "bytes": 216017,
        "fetch": "backend-verify-npm-postcss-fetch-488b9b7503", "archive_bytes": 51391,
        "archive_sha256": "d2cf324ff10baf8c34e1c79309bf2bfe15ee9b6e957f665737b9a9604c0744f1",
        "archive_sri": "sha512-g50586zr4bZmwFiTlflMu8E0bDTb5I5gertgwAKmsdUlTQIhZtunzUlD1WSzwcVWPoAVpsrA6vlfCD7oXvRwgg==",
        "source_sha256": "b0e2faa80c9539b2f9b5d5e8e67b328dbf421130a02cd1695a5da659447ca61f",
        "license_sha256": "5be1f3465bba68a626777f984878814aaf35e7ef8e9fd314d469bcf887050fb8",
    },
    "nanoid-3.3.19": {
        "name": "nanoid", "version": "3.3.19", "license": "MIT", "count": 25, "bytes": 25291,
        "fetch": "backend-verify-npm-postcss-nanoid-07fa400de4", "archive_bytes": 5694,
        "archive_sha256": "4e371b71e3d5081fa0052356d5c1904e7a60e049864c26f0724cfd32dc303849",
        "archive_sri": "sha512-Y2tUNy4ouw6tq5oDSKeQYGOyhkUBhNOcGV/02KC+6kd9eDGqdZd++mjMiIDilrBYvjEnCYvVtsuHCuP+okSfug==",
        "source_sha256": "3495da1b2b7f1c42952fc5090cd0eb818f207eb70a9f2083837ffedfa6dbdcf4",
        "license_sha256": "da4db1480d9beea3483a2eda5c53b22238d0827d57da162b48f122e04d2d9987",
    },
    "picocolors-1.1.1": {
        "name": "picocolors", "version": "1.1.1", "license": "ISC", "count": 7, "bytes": 6373,
        "fetch": "backend-verify-npm-postcss-picocolors-4ffabc42f8", "archive_bytes": 2625,
        "archive_sha256": "d3aedb2807967b7eb37fd11b03b7e3701e725af79c650d0812ff7213f8f882d9",
        "archive_sri": "sha512-xceH2snhtb5M9liqDsmEw56le376mTZkEX/jEb/RxNFyegNul7eNslCXP9FDj/Lcu0X8KEyMceP2ntpaHrDEVA==",
        "source_sha256": "04718da4913e9256b832a9227dc9ee4a875e5f7f7b57c44592caadcc612bb057",
        "license_sha256": "6582629e2979466878f6014313dcc2f3756c9616148682227ce3063dde310750",
    },
    "source-map-js-1.2.1": {
        "name": "source-map-js", "version": "1.2.1", "license": "BSD-3-Clause", "count": 18, "bytes": 139872,
        "fetch": "backend-verify-npm-postcss-sourcemap-af2f507fc0", "archive_bytes": 35340,
        "archive_sha256": "f126a6f9fca487a43219d8cb8c3a955279187a966119d548eb5cd47e999d4853",
        "archive_sri": "sha512-UXWMKhLOwVKb728IUtQPXxfYU+usdybtUrK/8uGE8CQMvrhOpwvzDBwj0QhSL7MQc7vIsISBG8VQ8+IDQxpfQA==",
        "source_sha256": "20eaf7236bed35a6bb8a316852680637c369ea7a3c0ec6aabc3fb51eb47c7bbe",
        "license_sha256": "6cb0631f71c7749763fd3dd1d5bee52dd1070ec17f2edc1710079ad070bd2fbd",
    },
    # The existing generation slice intentionally retains only these four v5 files.
    "nanoid-5.1.14": {
        "name": "nanoid", "version": "5.1.14", "license": "MIT", "count": 4,
        "source_sha256": "48edba08227f52a6b72e802292de3833a1ae82170c90ad836641f5b5b582cc75",
        "license_sha256": "4383cb2c3608397ce7a4159502614ed66890f8999c2a9c056dd3b1024d6721f0",
    },
}
NEW_PACKAGES = tuple(stem for stem in PACKAGES if stem != "nanoid-5.1.14")


def read_bytes(path: Path) -> bytes:
    with open(native(path), "rb") as stream:
        return stream.read()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_package(stem: str) -> dict:
    expected = PACKAGES[stem]
    root = VENDOR / stem
    raw = read_bytes(root / "SOURCE.json")
    assert digest(raw) == expected["source_sha256"]
    manifest = json.loads(raw)
    assert (manifest["name"], manifest["version"], manifest["license"]) == (
        expected["name"], expected["version"], expected["license"])
    assert manifest["origin"] == "https://registry.npmjs.org/" and manifest["scripts_executed"] is False
    if stem in NEW_PACKAGES:
        assert (manifest["archive_sha256"], manifest["archive_bytes"], manifest["archive_sri"]) == (
            expected["archive_sha256"], expected["archive_bytes"], expected["archive_sri"])
        assert (manifest["fetch_run"], manifest["audit_run"]) == (expected["fetch"], AUDIT)
    files = manifest["files"]
    assert isinstance(files, dict) and len(files) == expected["count"]
    if stem in NEW_PACKAGES:
        assert sum(entry["bytes"] for entry in files.values()) == expected["bytes"]
    assert files["LICENSE"]["sha256"] == expected["license_sha256"]
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    assert actual == set(files) | {"SOURCE.json"}
    for name, identity in files.items():
        relative = PurePosixPath(name)
        assert not relative.is_absolute() and ".." not in relative.parts and "\\" not in name
        assert re.fullmatch(r"[0-9a-f]{64}", identity["sha256"]) and isinstance(identity["bytes"], int)
        path = root.joinpath(*relative.parts)
        assert path.is_file() and not path.is_symlink()
        data = read_bytes(path)
        assert (len(data), digest(data)) == (identity["bytes"], identity["sha256"])
    package = json.loads(read_bytes(root / "package.json"))
    assert (package["name"], package["version"], package["license"]) == (
        expected["name"], expected["version"], expected["license"])
    assert all(not package.get(field) for field in
               ("optionalDependencies", "peerDependencies", "bundleDependencies", "bundledDependencies"))
    if stem == "postcss-8.5.23":
        assert package["exports"]["."] == {"import": "./lib/postcss.mjs", "require": "./lib/postcss.js"}
        assert package["dependencies"] == {"nanoid": "^3.3.16", "picocolors": "^1.1.1", "source-map-js": "^1.2.1"}
    elif stem == "nanoid-3.3.19":
        assert package["exports"]["./non-secure"]["require"]["default"] == "./non-secure/index.cjs"
        assert not package.get("dependencies")
    elif stem == "nanoid-5.1.14":
        assert package["exports"]["."]["default"] == "./index.js"
        assert not package.get("dependencies")
    else:
        assert not package.get("dependencies")
    if stem == "source-map-js-1.2.1":
        item = manifest["additional_notices"][0]
        assert item["member"] == "lib/base64-vlq.js"
        assert item["sha256"] == files[item["member"]]["sha256"] == "f3407e528f54ec0787bd0a71eeac0c99fffd98445916fcbe116dc69ca3be928b"
        notice = read_bytes(root / item["member"])
        assert b"Copyright 2011 The Closure Compiler Authors" in notice
        assert b"Copyright 2011 Mozilla Foundation and contributors" in notice
    return manifest


@pytest.mark.parametrize("stem", NEW_PACKAGES)
def test_originals_are_self_contained(stem):
    check_package(stem)


@pytest.mark.parametrize("stem", NEW_PACKAGES)
def test_optional_audited_archive_matches_every_member(stem):
    expected = PACKAGES[stem]
    archive_path = CACHE / expected["fetch"] / f"{stem}.tgz"
    if not os.path.isfile(native(archive_path)):
        pytest.skip("local-only original absent in a Git clone/CI (Git-ignored .project-local input); "
                    "this skip is NOT evidence of byte identity")
    manifest = check_package(stem)
    compressed = read_bytes(archive_path)
    assert (len(compressed), digest(compressed)) == (expected["archive_bytes"], expected["archive_sha256"])
    assert "sha512-" + base64.b64encode(hashlib.sha512(compressed).digest()).decode("ascii") == expected["archive_sri"]
    with tarfile.open(fileobj=io.BytesIO(compressed), mode="r:gz") as archive:
        members = archive.getmembers()
        assert len(members) == expected["count"]
        assert all(member.isfile() and member.name.startswith("package/") for member in members)
        names = [member.name.removeprefix("package/") for member in members]
        assert len(set(names)) == len(names) and set(names) == set(manifest["files"])
        for member, name in zip(members, names, strict=True):
            stream = archive.extractfile(member)
            assert stream is not None
            data = stream.read()
            identity = manifest["files"][name]
            assert (len(data), digest(data)) == (identity["bytes"], identity["sha256"])
            assert read_bytes((VENDOR / stem).joinpath(*PurePosixPath(name).parts)) == data


@pytest.mark.parametrize("stem", NEW_PACKAGES)
def test_git_ignore_and_clean_are_checked_without_index(tmp_path, stem):
    git = shutil.which("git")
    if not git:
        pytest.skip("Git is unavailable")
    if not (ROOT / ".git").exists():
        pytest.skip("not a Git checkout")
    manifest = check_package(stem)
    paths = [(VENDOR / stem / name).relative_to(ROOT).as_posix() for name in (*manifest["files"], "SOURCE.json")]
    assert all("\n" not in path and "\r" not in path and "\0" not in path for path in paths)
    index = tmp_path / "unused-index"
    assert not index.exists()
    for env in configuration_environments(index):
        probe = invoke_git(git, ROOT, env, "rev-parse", "--show-toplevel")
        assert Path(os.fsdecode(probe.stdout.strip())).resolve() == ROOT.resolve()
        require_readable_effective_excludes(git, ROOT, env)
        assert not ignored_paths(git, ROOT, env, paths), "preserved original is Git-ignored"
        records = invoke_git(git, ROOT, env, "check-attr", "--stdin", "-z", "filter",
                             data=b"\0".join(path.encode() for path in paths) + b"\0").stdout.split(b"\0")
        assert records[-1] == b"" and len(records) == 3 * len(paths) + 1
        for number, path in enumerate(paths):
            assert records[3 * number:3 * number + 3] == [path.encode(), b"filter", b"unspecified"]
        filenames = ("\n".join(paths) + "\n").encode()
        raw = invoke_git(git, ROOT, env, "hash-object", "--stdin-paths", "--no-filters", data=filenames).stdout.splitlines()
        clean = invoke_git(git, ROOT, env, "hash-object", "--stdin-paths", data=filenames).stdout.splitlines()
        assert len(raw) == len(clean) == len(paths)
        for path, raw_blob, clean_blob in zip(paths, raw, clean, strict=True):
            assert re.fullmatch(rb"[0-9a-f]{40}|[0-9a-f]{64}", raw_blob)
            assert raw_blob == clean_blob, f"Git clean filter changes {path}"


def stage_package(stem: str, manifest: dict, target: Path) -> None:
    root = VENDOR / stem
    for name in (*manifest["files"], "SOURCE.json"):
        assert not name.startswith("node_modules/")
        source = root.joinpath(*PurePosixPath(name).parts)
        destination = target.joinpath(*PurePosixPath(name).parts)
        data = read_bytes(source)
        if name == "SOURCE.json":
            assert digest(data) == PACKAGES[stem]["source_sha256"]
        else:
            identity = manifest["files"][name]
            assert (len(data), digest(data)) == (identity["bytes"], identity["sha256"])
        os.makedirs(native(destination.parent), exist_ok=True)
        with open(native(destination), "xb") as stream:
            stream.write(data)
        assert read_bytes(destination) == data


NODE_PROBE = r"""
import { registerHooks } from 'node:module';
import { readFileSync, existsSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = process.cwd();
const p = path.join(root, 'node_modules', 'postcss');
const n3 = path.join(p, 'node_modules', 'nanoid');
const n5 = path.join(root, 'node_modules', 'nanoid');
const pico = path.join(p, 'node_modules', 'picocolors');
const smap = path.join(p, 'node_modules', 'source-map-js');
const hash = data => createHash('sha256').update(data).digest('hex');
function fail(code, details = {}) { throw Object.assign(new Error(code), { code, ...details }); }
function manifest(dir, expected, optional = false) {
  const file = path.join(dir, 'SOURCE.json');
  if (optional && !existsSync(file)) return null;
  const raw = readFileSync(file);
  if (hash(raw) !== expected) fail('MANIFEST_MISMATCH');
  return JSON.parse(raw);
}
const mPost = manifest(p, 'b0e2faa80c9539b2f9b5d5e8e67b328dbf421130a02cd1695a5da659447ca61f');
const m3 = manifest(n3, '3495da1b2b7f1c42952fc5090cd0eb818f207eb70a9f2083837ffedfa6dbdcf4', true);
const m5 = manifest(n5, '48edba08227f52a6b72e802292de3833a1ae82170c90ad836641f5b5b582cc75');
const mPico = manifest(pico, '04718da4913e9256b832a9227dc9ee4a875e5f7f7b57c44592caadcc612bb057');
const mSmap = manifest(smap, '20eaf7236bed35a6bb8a316852680637c369ea7a3c0ec6aabc3fb51eb47c7bbe', true);
function within(dir, target) {
  const rel = path.relative(dir, target);
  return rel !== '' && rel !== '..' && !rel.startsWith('..' + path.sep) && !path.isAbsolute(rel);
}
function verified(dir, m, resolved) {
  if (!resolved.url.startsWith('file:')) fail('NON_FILE_RESOLUTION');
  const actual = fileURLToPath(resolved.url);
  if (!within(dir, actual)) fail('OUTSIDE_PACKAGE');
  const member = path.relative(dir, actual).split(path.sep).join('/');
  const identity = m?.files?.[member];
  if (!identity) fail('UNLISTED_MEMBER', { member });
  const bytes = readFileSync(actual);
  if (bytes.length !== identity.bytes || hash(bytes) !== identity.sha256) fail('MEMBER_MISMATCH', { member });
  return member;
}
const edges = {};
registerHooks({
  resolve(specifier, context, nextResolve) {
    const parent = context.parentURL?.startsWith('file:') ? fileURLToPath(context.parentURL) : '';
    const inPackage = within(p, parent) || within(n5, parent);
    const builtins = new Set(['fs', 'node:fs', 'path', 'node:path', 'url', 'node:url', 'node:crypto']);
    if (inPackage && builtins.has(specifier)) return nextResolve(specifier, context);
    let result;
    try { result = nextResolve(specifier, context); }
    catch (error) {
      if (within(p, parent) && specifier === 'source-map-js' && !mSmap) fail('SOURCE_MAP_MISSING');
      if (within(p, parent) && specifier === 'nanoid/non-secure' && !m3) fail('NANOID3_MISSING');
      throw error;
    }
    if (within(n3, parent)) {
      verified(n3, m3, result);
    } else if (within(pico, parent)) {
      verified(pico, mPico, result);
    } else if (within(smap, parent)) {
      verified(smap, mSmap, result);
    } else if (within(n5, parent)) {
      verified(n5, m5, result);
    } else if (within(p, parent)) {
      if (specifier === 'nanoid/non-secure') {
        const actual = result.url.startsWith('file:') ? fileURLToPath(result.url) : '';
        if (within(n5, actual)) fail('NANOID_FALLBACK_TO_5');
        if (!m3) fail('NANOID3_MISSING');
        const member = verified(n3, m3, result);
        if (member !== 'non-secure/index.cjs') fail('WRONG_NANOID3_EXPORT', { member });
        edges.nanoid = { version: '3.3.19', member };
      } else if (specifier === 'picocolors') {
        const member = verified(pico, mPico, result);
        if (member !== 'picocolors.js') fail('WRONG_PICOCOLORS_EXPORT', { member });
        edges.picocolors = { version: '1.1.1', member };
      } else if (specifier === 'source-map-js') {
        if (!mSmap) fail('SOURCE_MAP_MISSING');
        const member = verified(smap, mSmap, result);
        if (member !== 'source-map.js') fail('WRONG_SOURCE_MAP_EXPORT', { member });
        edges.sourceMap = { version: '1.2.1', member };
      } else if (specifier.startsWith('.')) {
        verified(p, mPost, result);
      } else {
        fail('UNEXPECTED_POSTCSS_IMPORT', { specifier });
      }
    } else if (specifier === 'postcss') {
      if (verified(p, mPost, result) !== 'lib/postcss.mjs') fail('WRONG_POSTCSS_ENTRY');
    } else if (specifier === 'nanoid') {
      const member = verified(n5, m5, result);
      if (member !== 'index.js') fail('WRONG_NANOID5_ENTRY', { member });
      edges.rootNanoid = { version: '5.1.14', member };
    }
    return result;
  },
});
function emit(result) {
  const body = JSON.stringify(result);
  if (Buffer.byteLength(body, 'utf8') > 4096) process.exit(2);
  process.stdout.write(body);
}
try {
  // Install the counters before PostCSS captures its fs methods. Only the
  // synthetic source map below is inspected; module loading is still allowed.
  const require = createRequire(import.meta.url);
  const fs = require('node:fs');
  const originalExists = fs.existsSync;
  const originalRead = fs.readFileSync;
  const mapPath = path.join(root, 'fixture.css.map');
  let mapReads = 0;
  fs.existsSync = function(target, ...rest) {
    if (String(target) === mapPath) mapReads++;
    return originalExists.call(this, target, ...rest);
  };
  fs.readFileSync = function(target, ...rest) {
    if (String(target) === mapPath) mapReads++;
    return originalRead.call(this, target, ...rest);
  };
  const postcss = (await import('postcss')).default;
  const rootNanoid = await import('nanoid');
  const map = { version: 3, sources: ['fixture.css'], names: [], mappings: '', sourcesContent: ['SYNTHETIC_MAP'] };
  writeFileSync(mapPath, JSON.stringify(map));
  const css = 'a { color: red }\n/*# sourceMappingURL=fixture.css.map */';
  mapReads = 0;
  const tree = postcss.parse(css, { from: path.join(root, 'fixture.css'), map: false });
  const disabledMapReads = mapReads;
  mapReads = 0;
  postcss.parse(css, { from: path.join(root, 'fixture.css') });
  const defaultMapReads = mapReads;
  let invalidRejected = false;
  try { postcss.parse('a { color: red', { map: false }); }
  catch (error) { invalidRejected = error.name === 'CssSyntaxError'; }
  const id = rootNanoid.nanoid(8);
  emit({ status: 'OBSERVED', node: process.versions.node, edges, css: tree.toString(),
    color: tree.first.first.value, disabledMapReads, defaultMapReads, invalidRejected, nanoid5Length: id.length });
} catch (error) {
  emit({ status: 'REJECTED', code: error.code || 'UNCLASSIFIED', member: error.member ?? null });
}
"""


def invoke_node_probe(node: Path, cwd: Path) -> dict:
    # Fixed executable and cleared Node overrides; no sandbox or descendant claim.
    env = {key: os.environ[key] for key in ("SystemRoot", "SYSTEMROOT", "WINDIR") if key in os.environ}
    process = subprocess.Popen([str(node), "--input-type=module", "-e", NODE_PROBE], cwd=str(cwd),
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    streams, errors = {}, {}

    def read_bounded(pipe, name):
        try:
            data = pipe.read(4097)
            streams[name] = data
            if len(data) > 4096:
                try:
                    process.kill()
                except OSError:
                    pass
        except OSError as error:
            errors[name] = type(error).__name__

    readers = [threading.Thread(target=read_bounded, args=(process.stdout, "stdout"), daemon=True),
               threading.Thread(target=read_bounded, args=(process.stderr, "stderr"), daemon=True)]
    for reader in readers:
        reader.start()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
        raise AssertionError("synthetic PostCSS process exceeded its deadline")
    finally:
        for reader in readers:
            reader.join(timeout=5)
    assert not any(reader.is_alive() for reader in readers), "package pipe cleanup unconfirmed"
    assert not errors and len(streams["stdout"]) <= 4096 and len(streams["stderr"]) <= 4096
    assert process.returncode == 0 and not streams["stderr"]
    return json.loads(streams["stdout"])


@pytest.mark.skipif(not NODE, reason="explicit, preverified ARCHEAXIS_TEST_NODE is required; PATH is not searched")
@pytest.mark.parametrize("case", ("coexist", "missing3", "tampered3", "missing_smap", "tampered_smap", "tampered_postcss"))
def test_fixed_node_resolves_exact_postcss_graph_before_css(tmp_path, case):
    node = Path(NODE)
    assert node.is_absolute() and node.is_file()
    executable_sha = hashlib.sha256()
    with node.open("rb") as executable:
        for chunk in iter(lambda: executable.read(1024 * 1024), b""):
            executable_sha.update(chunk)
    assert executable_sha.hexdigest() == NODE_SHA256
    manifests = {stem: check_package(stem) for stem in PACKAGES}
    stage = tmp_path / "postcss-graph"
    p = stage / "node_modules/postcss"
    n3 = p / "node_modules/nanoid"
    n5 = stage / "node_modules/nanoid"
    smap = p / "node_modules/source-map-js"
    stage_package("postcss-8.5.23", manifests["postcss-8.5.23"], p)
    stage_package("nanoid-5.1.14", manifests["nanoid-5.1.14"], n5)
    stage_package("picocolors-1.1.1", manifests["picocolors-1.1.1"], p / "node_modules/picocolors")
    if case != "missing3":
        stage_package("nanoid-3.3.19", manifests["nanoid-3.3.19"], n3)
    if case != "missing_smap":
        stage_package("source-map-js-1.2.1", manifests["source-map-js-1.2.1"], smap)
    if case == "missing3":
        # The retained v5 slice omits this export. A synthetic trap makes bare
        # resolution succeed, so the hook must reject the wrong version first.
        trap = n5 / "non-secure/index.js"
        os.makedirs(native(trap.parent), exist_ok=True)
        with open(native(trap), "xb") as stream:
            stream.write(b"throw new Error('SYNTHETIC_WRONG_VERSION_EXECUTED')\n")
    if case == "tampered3":
        with open(native(n3 / "non-secure/index.cjs"), "ab") as stream:
            stream.write(b"\n/* synthetic tamper */\n")
    if case == "tampered_smap":
        with open(native(smap / "source-map.js"), "ab") as stream:
            stream.write(b"\n/* synthetic tamper */\n")
    if case == "tampered_postcss":
        with open(native(p / "lib/input.js"), "ab") as stream:
            stream.write(b"\n/* synthetic tamper */\n")
    observed = invoke_node_probe(node, stage)
    if case == "coexist":
        assert observed["status"] == "OBSERVED" and observed["node"] == "24.21.0"
        assert observed["edges"] == {
            "nanoid": {"version": "3.3.19", "member": "non-secure/index.cjs"},
            "picocolors": {"version": "1.1.1", "member": "picocolors.js"},
            "sourceMap": {"version": "1.2.1", "member": "source-map.js"},
            "rootNanoid": {"version": "5.1.14", "member": "index.js"},
        }
        assert observed["css"] == 'a { color: red }\n/*# sourceMappingURL=fixture.css.map */'
        assert observed["color"] == "red" and observed["nanoid5Length"] == 8
        assert observed["disabledMapReads"] == 0 and observed["defaultMapReads"] > 0
        assert observed["invalidRejected"] is True
    elif case == "missing3":
        assert observed["status"] == "REJECTED" and observed["code"] == "NANOID_FALLBACK_TO_5"
        assert "css" not in observed
    elif case == "missing_smap":
        assert observed["status"] == "REJECTED" and observed["code"] == "SOURCE_MAP_MISSING"
        assert "css" not in observed
    else:
        assert observed["status"] == "REJECTED" and observed["code"] == "MEMBER_MISMATCH"
        expected_member = {"tampered3": "non-secure/index.cjs", "tampered_smap": "source-map.js",
                           "tampered_postcss": "lib/input.js"}[case]
        assert observed["member"] == expected_member
        assert "css" not in observed
