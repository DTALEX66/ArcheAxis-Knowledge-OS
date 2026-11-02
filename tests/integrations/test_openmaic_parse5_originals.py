"""Offline parse5/dual-entities identity and behavior; not OpenMAIC qualification."""
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
         / "openmaic-owner-4660cd2b97ac2a3862cd238fc28b54195a622c8beabb87c9185d87f626f47a29"
         / "backend-verify-npm-parse5-fetch-8d76a12965")
NODE = os.environ.get("ARCHEAXIS_TEST_NODE")
NODE_SHA256 = "ba4e6d110e8c1592a1ecd390f6b05f3da124b13871a5be62b341a07a853c6c32"
PACKAGES = {
    "parse5-8.0.1": {
        "name": "parse5", "version": "8.0.1", "license": "MIT", "count": 33, "bytes": 337099,
        "archive_bytes": 56234, "archive_sha256": "d94ec8606e3cef24b8ec001ac121df5d7938f015be69615da27b53a082f86832",
        "archive_sri": "sha512-z1e/HMG90obSGeidlli3hj7cbocou0/wa5HacvI3ASx34PecNjNQeaHNo5WIZpWofN9kgkqV1q5YvXe3F0FoPw==",
        "source_sha256": "fb5a2c507c9c2d2c59073df562e2131ada5860b3370ebc9508762bc4be1cad30",
        "license_sha256": "8c535800331e1e4439835555b3f9edc7fe9dee2fab0d8bbbd5a982e8b8343d4d",
    },
    "entities-8.0.0": {
        "name": "entities", "version": "8.0.0", "license": "BSD-2-Clause", "count": 58, "bytes": 236002,
        "archive_bytes": 86968, "archive_sha256": "8e8b16388e19c12fc80f9f75f518a0f83d99428be6765a38f04c264a078cc25b",
        "archive_sri": "sha512-zwfzJecQ/Uej6tusMqwAqU/6KL2XaB2VZ2Jg54Je6ahNBGNH6Ek6g3jjNCF0fG9EWQKGZNddNjU5F1ZQn/sBnA==",
        "source_sha256": "91fd19349c025f903464fe8d0e4ab5464708db4386024dbd9957c273c91a422c",
        "license_sha256": "cb992345949ccd6e8394b2cd6c465f7b897c864f845937dbf64e8997f389e164",
    },
    "entities-6.0.1": {
        "name": "entities", "version": "6.0.1", "license": "BSD-2-Clause", "count": 86, "bytes": 540551,
        "source_sha256": "2931e2cb2561ccdd29a1c14eb11527e983138ecc2dc31021ede7123f95d11bf6",
        "license_sha256": "cb992345949ccd6e8394b2cd6c465f7b897c864f845937dbf64e8997f389e164",
    },
}
NEW_PACKAGES = ("parse5-8.0.1", "entities-8.0.0")


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
    assert (manifest["name"], manifest["version"], manifest["license"]) == (expected["name"], expected["version"], expected["license"])
    if stem in NEW_PACKAGES:
        assert (manifest["archive_sha256"], manifest["archive_bytes"], manifest["archive_sri"]) == (
            expected["archive_sha256"], expected["archive_bytes"], expected["archive_sri"])
        assert manifest["fetch_run"] == "backend-verify-npm-parse5-fetch-8d76a12965"
        assert manifest["audit_run"] == "backend-verify-npm-parse5-audit-8ba9aef43c"
    assert manifest["origin"] == "https://registry.npmjs.org/" and manifest["scripts_executed"] is False
    files = manifest["files"]
    assert isinstance(files, dict) and len(files) == expected["count"]
    assert sum(item["bytes"] for item in files.values()) == expected["bytes"]
    assert files["LICENSE"]["sha256"] == expected["license_sha256"]
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    assert actual == set(files) | {"SOURCE.json"}
    for name, identity in files.items():
        relative = PurePosixPath(name)
        assert not relative.is_absolute() and ".." not in relative.parts
        assert re.fullmatch(r"[0-9a-f]{64}", identity["sha256"]) and isinstance(identity["bytes"], int)
        path = root.joinpath(*relative.parts)
        assert path.is_file() and not path.is_symlink()
        data = read_bytes(path)
        assert (len(data), digest(data)) == (identity["bytes"], identity["sha256"])
    package = json.loads(read_bytes(root / "package.json"))
    assert (package["name"], package["version"], package["license"]) == (expected["name"], expected["version"], expected["license"])
    if stem == "parse5-8.0.1":
        assert package["dependencies"] == {"entities": "^8.0.0"}
        assert package["exports"]["."]["default"] == "./dist/index.js"
    elif stem == "entities-8.0.0":
        assert not package.get("dependencies")
        assert package["exports"]["./decode"]["default"] == "./dist/decode.js"
        assert package["exports"]["./escape"]["default"] == "./dist/escape.js"
    else:
        assert not package.get("dependencies")
        assert package["exports"]["."]["import"]["default"] == "./dist/esm/index.js"
    return manifest


@pytest.mark.parametrize("stem", NEW_PACKAGES)
def test_originals_are_self_contained(stem):
    check_package(stem)


@pytest.mark.parametrize("stem", NEW_PACKAGES)
def test_optional_audited_archive_matches_every_member(stem):
    archive_path = CACHE / f"{stem}.tgz"
    if not archive_path.is_file():
        pytest.skip("ignored verified npm archive is unavailable in this checkout")
    expected = PACKAGES[stem]
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
def test_new_members_git_ignore_and_clean_are_checked_without_index(tmp_path, stem):
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
        for index_number, path in enumerate(paths):
            assert records[3 * index_number:3 * index_number + 3] == [path.encode(), b"filter", b"unspecified"]
        filenames = ("\n".join(paths) + "\n").encode()
        raw = invoke_git(git, ROOT, env, "hash-object", "--stdin-paths", "--no-filters", data=filenames).stdout.splitlines()
        clean = invoke_git(git, ROOT, env, "hash-object", "--stdin-paths", data=filenames).stdout.splitlines()
        assert len(raw) == len(clean) == len(paths)
        for path, raw_blob, clean_blob in zip(paths, raw, clean, strict=True):
            assert re.fullmatch(rb"[0-9a-f]{40}|[0-9a-f]{64}", raw_blob)
            assert raw_blob == clean_blob, f"Git clean filter changes {path}"


def stage_package(stem: str, manifest: dict, target: Path) -> None:
    root = VENDOR / stem
    names = [*manifest["files"], "SOURCE.json"]
    assert all(not name.startswith("node_modules/") for name in names)
    for name in names:
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
import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = process.cwd();
const p5 = path.join(root, 'node_modules', 'parse5');
const e6 = path.join(root, 'node_modules', 'entities');
const e8 = path.join(p5, 'node_modules', 'entities');
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
function fail(code, details = {}) { throw Object.assign(new Error(code), { code, ...details }); }
function manifest(dir, expected) {
  const raw = readFileSync(path.join(dir, 'SOURCE.json'));
  if (hash(raw) !== expected) fail('MANIFEST_MISMATCH');
  return JSON.parse(raw);
}
const m5 = manifest(p5, 'fb5a2c507c9c2d2c59073df562e2131ada5860b3370ebc9508762bc4be1cad30');
const m6 = manifest(e6, '2931e2cb2561ccdd29a1c14eb11527e983138ecc2dc31021ede7123f95d11bf6');
const m8 = existsSync(path.join(e8, 'SOURCE.json'))
  ? manifest(e8, '91fd19349c025f903464fe8d0e4ab5464708db4386024dbd9957c273c91a422c') : null;
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
const entityResolutions = [];
let rootEntities = null;
registerHooks({
  resolve(specifier, context, nextResolve) {
    const parent = context.parentURL?.startsWith('file:') ? fileURLToPath(context.parentURL) : '';
    const result = nextResolve(specifier, context);
    if (within(e8, parent)) {
      verified(e8, m8, result);
    } else if (within(e6, parent)) {
      verified(e6, m6, result);
    } else if (within(p5, parent)) {
      if (specifier === 'entities/decode' || specifier === 'entities/escape') {
        const actual = result.url.startsWith('file:') ? fileURLToPath(result.url) : '';
        if (within(e6, actual)) {
          const member = verified(e6, m6, result);
          fail('ENTITIES_FALLBACK_TO_6', { specifier, member });
        }
        if (!m8) fail('ENTITIES_8_MISSING');
        const member = verified(e8, m8, result);
        const required = specifier === 'entities/decode' ? 'dist/decode.js' : 'dist/escape.js';
        if (member !== required) fail('WRONG_ENTITIES_EXPORT', { specifier, member });
        entityResolutions.push({ specifier, member, version: '8.0.0' });
      } else if (specifier.startsWith('.')) {
        verified(p5, m5, result);
      } else {
        fail('UNEXPECTED_PARSE5_IMPORT', { specifier });
      }
    } else if (specifier === 'parse5') {
      if (verified(p5, m5, result) !== 'dist/index.js') fail('WRONG_PARSE5_ENTRY');
    } else if (specifier === 'entities') {
      const member = verified(e6, m6, result);
      if (member !== 'dist/esm/index.js') fail('WRONG_ROOT_ENTITIES_ENTRY', { member });
      rootEntities = { version: '6.0.1', member };
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
  const parser = await import('parse5');
  const fragment = parser.parseFragment('<p>A &amp; B &#x41;</p>');
  const v6 = await import('entities');
  emit({ status: 'OBSERVED', node: process.versions.node,
    text: fragment.childNodes[0].childNodes[0].value, decoded6: v6.decodeHTML('&amp;'),
    rootEntities, entityResolutions });
} catch (error) {
  emit({ status: 'REJECTED', code: error.code || 'UNCLASSIFIED',
    specifier: error.specifier ?? null, member: error.member ?? null });
}
"""


def invoke_node_probe(node: Path, cwd: Path) -> dict:
    # An explicit executable and an isolated environment avoid NODE_OPTIONS,
    # NODE_PATH and ambient package settings. This is not an OS sandbox.
    env = {name: os.environ[name] for name in ("SystemRoot", "SYSTEMROOT", "WINDIR") if name in os.environ}
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
        raise AssertionError("synthetic parse5 process exceeded its deadline")
    finally:
        for reader in readers:
            reader.join(timeout=5)
    assert not any(reader.is_alive() for reader in readers), "package pipe cleanup unconfirmed"
    assert not errors and len(streams["stdout"]) <= 4096 and len(streams["stderr"]) <= 4096
    assert process.returncode == 0 and not streams["stderr"]
    return json.loads(streams["stdout"])


@pytest.mark.skipif(not NODE, reason="explicit, preverified ARCHEAXIS_TEST_NODE is required; PATH is not searched")
@pytest.mark.parametrize("case", ("coexist", "missing8", "tampered8"))
def test_fixed_node_resolves_exact_entities_version_before_parsing(tmp_path, case):
    node = Path(NODE)
    assert node.is_absolute() and node.is_file()
    executable_sha = hashlib.sha256()
    with node.open("rb") as executable:
        for chunk in iter(lambda: executable.read(1024 * 1024), b""):
            executable_sha.update(chunk)
    assert executable_sha.hexdigest() == NODE_SHA256
    manifests = {stem: check_package(stem) for stem in PACKAGES}
    stage = tmp_path / "dual-entities"
    parse5_dir = stage / "node_modules/parse5"
    entity6_dir = stage / "node_modules/entities"
    entity8_dir = parse5_dir / "node_modules/entities"
    stage_package("parse5-8.0.1", manifests["parse5-8.0.1"], parse5_dir)
    stage_package("entities-6.0.1", manifests["entities-6.0.1"], entity6_dir)
    if case != "missing8":
        stage_package("entities-8.0.0", manifests["entities-8.0.0"], entity8_dir)
    if case == "tampered8":
        # Modify only this test's fresh temporary copy; the retained source is untouched.
        with open(native(entity8_dir / "dist/decode.js"), "ab") as stream:
            stream.write(b"\n/* synthetic tamper */\n")
    observed = invoke_node_probe(node, stage)
    if case == "coexist":
        assert observed["status"] == "OBSERVED" and observed["node"] == "24.21.0"
        assert observed["text"] == "A & B A" and observed["decoded6"] == "&"
        assert observed["rootEntities"] == {"version": "6.0.1", "member": "dist/esm/index.js"}
        assert sorted(observed["entityResolutions"], key=lambda item: item["specifier"]) == [
            {"specifier": "entities/decode", "member": "dist/decode.js", "version": "8.0.0"},
            {"specifier": "entities/escape", "member": "dist/escape.js", "version": "8.0.0"},
        ]
    elif case == "missing8":
        # Bare Node resolution found the real top-level 6.x export, but the
        # hook rejects it before importing that module or parsing the HTML.
        assert observed["status"] == "REJECTED" and observed["code"] == "ENTITIES_FALLBACK_TO_6"
        assert (observed["specifier"], observed["member"]) in {
            ("entities/decode", "dist/esm/decode.js"), ("entities/escape", "dist/esm/escape.js")}
        assert "text" not in observed and "rootEntities" not in observed
    else:
        assert observed["status"] == "REJECTED" and observed["code"] == "MEMBER_MISMATCH"
        assert observed["member"] == "dist/decode.js" and "text" not in observed
