"""Offline geometry dependency identity and synthetic calls; not OpenMAIC qualification."""
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


ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / "services/learning-providers/openmaic/vendor/npm"
CACHE = (ROOT / ".project-local/cache/npm"
         / "openmaic-owner-4660cd2b97ac2a3862cd238fc28b54195a622c8beabb87c9185d87f626f47a29"
         / "backend-verify-npm-geometry-fetch-cd02693046")
NODE = os.environ.get("ARCHEAXIS_TEST_NODE")
NODE_SHA256 = "ba4e6d110e8c1592a1ecd390f6b05f3da124b13871a5be62b341a07a853c6c32"
PACKAGES = {
    "entities-6.0.1": {
        "name": "entities", "version": "6.0.1", "license": "BSD-2-Clause", "count": 86, "bytes": 540551,
        "archive_bytes": 112438, "archive_sha256": "a4de957ab0852f6c91eae59a6000ced5a25a04f0b6e1c3062fbad732a6b5479d",
        "archive_sri": "sha512-aN97NXWF6AWBTahfVOIrB/NShkzi5H7F9r1s9mD3cDj4Ko5f2qhhVoYMibXF7GlLveb/D2ioWay8lxI97Ven3g==",
        "source_sha256": "2931e2cb2561ccdd29a1c14eb11527e983138ecc2dc31021ede7123f95d11bf6",
        "license_sha256": "cb992345949ccd6e8394b2cd6c465f7b897c864f845937dbf64e8997f389e164",
        "entry": "dist/esm/index.js",
        "script": "return {decoded: m.decodeHTML('A &amp; B &lt; C &#x41;')};",
        "result": {"decoded": "A & B < C A"},
    },
    "svg-pathdata-8.0.0": {
        "name": "svg-pathdata", "version": "8.0.0", "license": "MIT", "count": 176, "bytes": 686326,
        "archive_bytes": 120757, "archive_sha256": "ac728127b016c23498dde9b2c00a030395c11317b7714a20a48aeb336ecef45e",
        "archive_sri": "sha512-2Zqf5zsrX44Ws9y52EdHYrzGGnzyQG0jgREw+S3nP7zdx7QeH3QJonnGPvjtxPmYzU5mJMJ2YM+q2hUWGENWFg==",
        "source_sha256": "2d619e3e74942771048204c6740274bfb04e5eb544cde3ad11da982aa121481b",
        "license_sha256": "cd05e8e2516f46a2cd79494bbabdea76f874e8d049dbc19a76b367534a4e013e",
        "entry": "dist/index.js",
        # The upstream encoder emits lowercase z for CLOSE_PATH; the parser
        # accepts either case as the same close command. Compare every command
        # and its coordinates on reparse, not just the output spelling.
        "script": "const p = new m.SVGPathData('M 10 10 H 60 V 60 L 10 60 Z'); const path = p.encode(); const roundtrip = new m.SVGPathData(path); const lower = new m.SVGPathData('M 10 10 H 60 V 60 L 10 60 z'); return {path, commands: p.commands.length, close: p.commands[4].type === m.SVGPathData.CLOSE_PATH, roundtrip_equal: JSON.stringify(p.commands) === JSON.stringify(roundtrip.commands), lower_equal: JSON.stringify(p.commands) === JSON.stringify(lower.commands)};",
        "result": {"path": "M10 10H60V60L10 60z", "commands": 5, "close": True,
                   "roundtrip_equal": True, "lower_equal": True},
    },
    "tinycolor2-1.6.0": {
        "name": "tinycolor2", "version": "1.6.0", "license": "MIT", "count": 14, "bytes": 284855,
        "archive_bytes": 62909, "archive_sha256": "1fd8164c4b0e1bad09bf2252705fbcf6789dcce7c121aa52b515dd6438eb635b",
        "archive_sri": "sha512-XPaBkWQJdsf3pLKJV9p4qN/S+fm2Oj8AIPo1BTUhg5oxkvm9+SVEGFdhyOz7tTdUTfvxMiAs4sp6/eZO2Ew+pw==",
        "source_sha256": "523960b84b6cde69b861ec911da3d58fdc75035f1bcf825ca75963402c958bfb",
        "license_sha256": "c6cb470a9ba0a50d57611aeec1f31da609c5aefdbee8eac7f289bcb0e30625fa",
        "entry": "esm/tinycolor.js",
        "script": "const c = m.default('rgba(255, 0, 0, 0.5)'); return {valid: c.isValid(), hex8: c.toHex8String()};",
        "result": {"valid": True, "hex8": "#ff000080"},
    },
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_manifest_and_members(stem: str) -> dict:
    expected = PACKAGES[stem]
    root = VENDOR / stem
    raw = (root / "SOURCE.json").read_bytes()
    assert digest(raw) == expected["source_sha256"]
    manifest = json.loads(raw)
    assert (manifest["name"], manifest["version"], manifest["license"]) == (expected["name"], expected["version"], expected["license"])
    assert (manifest["archive_sha256"], manifest["archive_bytes"], manifest["archive_sri"]) == (
        expected["archive_sha256"], expected["archive_bytes"], expected["archive_sri"])
    assert manifest["origin"] == "https://registry.npmjs.org/" and manifest["scripts_executed"] is False
    assert manifest["fetch_run"] == "backend-verify-npm-geometry-fetch-cd02693046"
    assert manifest["audit_run"] == "backend-verify-npm-geometry-audit-b93b418f87"
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
        data = path.read_bytes()
        assert (len(data), digest(data)) == (identity["bytes"], identity["sha256"])
    package = json.loads((root / "package.json").read_bytes())
    assert (package["name"], package["version"], package["license"]) == (expected["name"], expected["version"], expected["license"])
    assert all(not package.get(field) for field in ("dependencies", "optionalDependencies", "peerDependencies"))
    if stem.startswith("entities-"):
        assert package["exports"]["."]["import"]["default"] == "./" + expected["entry"]
    elif stem.startswith("tinycolor2-"):
        assert package["exports"]["."]["import"] == "./" + expected["entry"]
    else:
        assert package["main"] == expected["entry"]
    return manifest


@pytest.mark.parametrize("stem", PACKAGES)
def test_manifest_and_all_original_members_are_self_contained(stem):
    check_manifest_and_members(stem)


@pytest.mark.parametrize("stem", PACKAGES)
def test_local_locked_archive_members_match_when_available(stem):
    archive_path = CACHE / f"{stem}.tgz"
    if not archive_path.is_file():
        pytest.skip("ignored verified npm archive is unavailable in this checkout")
    expected = PACKAGES[stem]
    manifest = check_manifest_and_members(stem)
    compressed = archive_path.read_bytes()
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
            assert (VENDOR / stem).joinpath(*PurePosixPath(name).parts).read_bytes() == data


@pytest.mark.skipif(not NODE, reason="explicit, preverified ARCHEAXIS_TEST_NODE is required; PATH is not searched")
@pytest.mark.parametrize("stem", PACKAGES)
def test_fixed_node_calls_original_package_on_synthetic_data(stem):
    check_manifest_and_members(stem)
    expected = PACKAGES[stem]
    node = Path(NODE)
    assert node.is_absolute() and node.is_file()
    executable_sha = hashlib.sha256()
    with node.open("rb") as executable:
        for chunk in iter(lambda: executable.read(1024 * 1024), b""):
            executable_sha.update(chunk)
    assert executable_sha.hexdigest() == NODE_SHA256
    source = """const {pathToFileURL} = require('node:url');
(async () => {
  const m = await import(pathToFileURL(process.argv[1]).href);
  const result = (() => { """ + expected["script"] + """ })();
  const body = JSON.stringify({node: process.versions.node, result});
  if (Buffer.byteLength(body, 'utf8') > 4096) process.exit(2);
  process.stdout.write(body);
})().catch(() => { process.exitCode = 1; });"""
    # No inherited Node options or package scripts. This is not an OS sandbox.
    env = {name: os.environ[name] for name in ("SystemRoot", "SYSTEMROOT", "WINDIR") if name in os.environ}
    process = subprocess.Popen([str(node), "-e", source, str(VENDOR / stem / expected["entry"])], stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
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
        raise AssertionError("synthetic package process exceeded its deadline")
    finally:
        for reader in readers:
            reader.join(timeout=5)
    assert not any(reader.is_alive() for reader in readers), "package pipe cleanup unconfirmed"
    assert not errors and len(streams["stdout"]) <= 4096 and len(streams["stderr"]) <= 4096
    assert process.returncode == 0 and not streams["stderr"]
    assert json.loads(streams["stdout"]) == {"node": "24.21.0", "result": expected["result"]}


@pytest.mark.parametrize("stem", PACKAGES)
def test_git_clean_preserves_each_original_without_index(tmp_path, stem):
    git = shutil.which("git")
    if not git:
        pytest.skip("Git is unavailable")
    if not (ROOT / ".git").exists():
        pytest.skip("not a Git checkout")
    manifest = check_manifest_and_members(stem)
    alternate_index = tmp_path / "no-index"
    assert not alternate_index.exists()
    env = os.environ.copy()
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES"):
        env.pop(name, None)
    env["GIT_INDEX_FILE"] = str(alternate_index)
    env["GIT_OPTIONAL_LOCKS"] = "0"

    def run_git(*args, data=None):
        process = subprocess.run([git, "-C", str(ROOT), *args], input=data, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, env=env, timeout=20, check=False)
        assert process.returncode == 0, process.stderr.decode("utf-8", "replace")
        assert not alternate_index.exists(), "Git unexpectedly wrote the isolated index"
        return process.stdout

    actual_root = Path(os.fsdecode(run_git("rev-parse", "--show-toplevel").strip())).resolve()
    assert actual_root == ROOT.resolve(), "Git checkout root differs"
    paths = [(VENDOR / stem / name).relative_to(ROOT).as_posix() for name in (*manifest["files"], "SOURCE.json")]
    assert all("\n" not in path and "\r" not in path and "\0" not in path for path in paths)
    attributes = run_git("check-attr", "--stdin", "-z", "filter",
                         data=b"\0".join(path.encode() for path in paths) + b"\0").split(b"\0")
    assert attributes[-1] == b"" and len(attributes) == 3 * len(paths) + 1
    for index, path in enumerate(paths):
        assert attributes[3 * index:3 * index + 3] == [path.encode(), b"filter", b"unspecified"]
    filename_input = ("\n".join(paths) + "\n").encode()
    raw = run_git("hash-object", "--stdin-paths", "--no-filters", data=filename_input).splitlines()
    clean = run_git("hash-object", "--stdin-paths", data=filename_input).splitlines()
    assert len(raw) == len(clean) == len(paths)
    for path, raw_blob, clean_blob in zip(paths, raw, clean, strict=True):
        assert re.fullmatch(rb"[0-9a-f]{40}|[0-9a-f]{64}", raw_blob)
        assert raw_blob == clean_blob, f"Git clean filter changes {path}"
