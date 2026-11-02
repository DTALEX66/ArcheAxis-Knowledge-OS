"""Offline package identity and synthetic behavior, not OpenMAIC qualification."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import threading

import pytest


ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / "services/learning-providers/openmaic/vendor/npm/postcss-value-parser-4.2.0"
CACHE = (ROOT / ".project-local/cache/npm"
         / "openmaic-owner-4660cd2b97ac2a3862cd238fc28b54195a622c8beabb87c9185d87f626f47a29"
         / "backend-verify-npm-pvp-fetch-848f060242")
ARCHIVE = CACHE / "postcss-value-parser-4.2.0.tgz"
ARCHIVE_SRI = "sha512-1NNCs6uurfkVbeXG4S8JFT9t19m45ICnif8zWLd5oPSZ50QnwMfK+H3jv408d4jw/7Bttv5axS5IiHoLaVNHeQ=="
ARCHIVE_SHA256 = "3de5372cf95b66a344b258a046b1b298b20ecaf187637f4d59f50017836a90a7"
SOURCE_SHA256 = "d7b344a5bd2494aea12255918bf24e4dd4a34ba80a06d9bb399ea5469e145607"
NODE_SHA256 = "ba4e6d110e8c1592a1ecd390f6b05f3da124b13871a5be62b341a07a853c6c32"
NODE = os.environ.get("ARCHEAXIS_TEST_NODE")
FILES = {
    "LICENSE": (1074, "3687447039151857a6ba378db062172c7f33d4aa70a615c87a43a9c50e990485"),
    "README.md": (7683, "7b183e14c4853ed481ef03b5b4c924a7fbe70635ff2e2decd3cea5329eb9b2d6"),
    "lib/index.d.ts": (4290, "4533b61de4b1594a736704184d03d4d8d5f3b072a6acfcfd41d76da975ac04fd"),
    "lib/index.js": (607, "b72197f798b185efdd013e8d9b9b405e9a940dd9c5e9c53931684474f447af92"),
    "lib/parse.js": (8344, "7f57d3c73010b7a5f11cd5fd1b49fc61043a0a2b430f090b6eb9220b0b27e4f2"),
    "lib/stringify.js": (1185, "bea6103af615bb9d65a2fc6dff1b2ab8a32b5ca33e263b5a2c8d458c4eff19fc"),
    "lib/unit.js": (2283, "728de375616da4672cd8a2d0b1713fd9b61ec5774075b4d1ad3ef1076cbbd740"),
    "lib/walk.js": (425, "f954705a5401ddf0401d500088ed668a0307bd19259f2af104377704899cd09f"),
    "package.json": (1302, "6cf9201a4d0d15253e7e7b78b4ef808b8cb3354c9809214423453b48bd012bc0"),
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_manifest_and_original_members():
    raw = (VENDOR / "SOURCE.json").read_bytes()
    assert digest(raw) == SOURCE_SHA256
    manifest = json.loads(raw)
    assert manifest["name"] == "postcss-value-parser" and manifest["version"] == "4.2.0"
    assert manifest["license"] == "MIT" and manifest["archive_sri"] == ARCHIVE_SRI
    assert (manifest["archive_sha256"], manifest["archive_bytes"]) == (ARCHIVE_SHA256, 7997)
    assert manifest["origin"] == "https://registry.npmjs.org/" and manifest["scripts_executed"] is False
    assert manifest["fetch_run"] == "backend-verify-npm-pvp-fetch-848f060242"
    assert manifest["audit_run"] == "backend-verify-npm-pvp-audit-9982b6fd58"
    assert manifest["files"] == {name: {"bytes": size, "sha256": checksum}
                                 for name, (size, checksum) in FILES.items()}
    actual = {path.relative_to(VENDOR).as_posix() for path in VENDOR.rglob("*") if path.is_file()}
    assert actual == set(FILES) | {"SOURCE.json"}
    for name, (size, checksum) in FILES.items():
        relative = PurePosixPath(name)
        assert not relative.is_absolute() and ".." not in relative.parts
        path = VENDOR.joinpath(*relative.parts)
        assert path.is_file() and not path.is_symlink()
        data = path.read_bytes()
        assert (len(data), digest(data)) == (size, checksum)
    package = json.loads((VENDOR / "package.json").read_bytes())
    assert (package["name"], package["version"], package["license"]) == ("postcss-value-parser", "4.2.0", "MIT")
    assert all(not package.get(field) for field in ("dependencies", "optionalDependencies", "peerDependencies"))


def test_manifest_and_all_original_members_are_self_contained():
    check_manifest_and_original_members()


def test_local_locked_archive_members_match_when_available():
    if not ARCHIVE.is_file():
        pytest.skip("local-only original absent in a Git clone/CI (Git-ignored .project-local input); "
                    "this skip is NOT evidence of byte identity")
    compressed = ARCHIVE.read_bytes()
    assert (len(compressed), digest(compressed)) == (7997, ARCHIVE_SHA256)
    assert "sha512-" + base64.b64encode(hashlib.sha512(compressed).digest()).decode("ascii") == ARCHIVE_SRI
    with tarfile.open(fileobj=io.BytesIO(compressed), mode="r:gz") as archive:
        members = archive.getmembers()
        assert len(members) == len(FILES) and all(member.isfile() and member.name.startswith("package/") for member in members)
        names = [member.name.removeprefix("package/") for member in members]
        assert len(set(names)) == len(names) and set(names) == set(FILES)
        for member, name in zip(members, names, strict=True):
            stream = archive.extractfile(member)
            assert stream is not None
            data = stream.read()
            assert (len(data), digest(data)) == FILES[name]
            assert VENDOR.joinpath(*PurePosixPath(name).parts).read_bytes() == data


@pytest.mark.skipif(not NODE, reason="explicit, preverified ARCHEAXIS_TEST_NODE is required; PATH is not searched")
def test_original_package_parses_and_rewrites_synthetic_css_offline():
    check_manifest_and_original_members()
    node = Path(NODE)
    assert node.is_absolute() and node.is_file()
    executable_sha = hashlib.sha256()
    with node.open("rb") as executable:
        for chunk in iter(lambda: executable.read(1024 * 1024), b""):
            executable_sha.update(chunk)
    assert executable_sha.hexdigest() == NODE_SHA256
    source = r"""
const parse = require(process.argv[1]);
const input = 'rgba(233, 45, 66, .5)';
const parsed = parse(input);
const fn = parsed.nodes[0];
const roundtrip = parsed.toString();
const args = fn.nodes.filter(node => node.type === 'word').map(node => node.value);
fn.nodes.find(node => node.type === 'word').value = '255';
const body = JSON.stringify({node: process.versions.node, type: fn.type, function: fn.value,
  args, roundtrip, rewritten: parsed.toString(), stringified: parse.stringify(parsed.nodes)});
if (Buffer.byteLength(body, 'utf8') > 4096) process.exit(2);
process.stdout.write(body);
"""
    # No NODE_OPTIONS, NODE_PATH or inherited user settings are passed. This is
    # a bounded test process, not an operating-system network sandbox.
    env = {name: os.environ[name] for name in ("SystemRoot", "SYSTEMROOT", "WINDIR") if name in os.environ}
    process = subprocess.Popen([str(node), "-e", source, str(VENDOR)], stdin=subprocess.DEVNULL,
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
    result = json.loads(streams["stdout"])
    assert result == {"node": "24.21.0", "type": "function", "function": "rgba",
                      "args": ["233", "45", "66", ".5"], "roundtrip": "rgba(233, 45, 66, .5)",
                      "rewritten": "rgba(255, 45, 66, .5)", "stringified": "rgba(255, 45, 66, .5)"}


def test_current_git_clean_filter_preserves_all_original_bytes_without_index(tmp_path):
    git = shutil.which("git")
    if not git:
        pytest.skip("Git is unavailable")
    if not (ROOT / ".git").exists():
        pytest.skip("not a Git checkout")
    check_manifest_and_original_members()
    alternate_index = tmp_path / "no-index"
    assert not alternate_index.exists()
    env = os.environ.copy()
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES"):
        env.pop(name, None)
    env["GIT_INDEX_FILE"] = str(alternate_index)
    env["GIT_OPTIONAL_LOCKS"] = "0"

    def run_git(*args, data=None):
        process = subprocess.run([git, "-C", str(ROOT), *args], input=data, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, env=env, timeout=15, check=False)
        assert process.returncode == 0, process.stderr.decode("utf-8", "replace")
        assert not alternate_index.exists(), "Git unexpectedly wrote the isolated index"
        return process.stdout

    actual_root = Path(os.fsdecode(run_git("rev-parse", "--show-toplevel").strip())).resolve()
    assert actual_root == ROOT.resolve(), "Git checkout root differs"
    paths = [(VENDOR / name).relative_to(ROOT).as_posix() for name in (*FILES, "SOURCE.json")]
    attributes = run_git("check-attr", "-z", "filter", "--", *paths).split(b"\0")
    assert attributes[-1] == b"" and len(attributes) == 3 * len(paths) + 1
    for index, path in enumerate(paths):
        assert attributes[3 * index:3 * index + 3] == [path.encode(), b"filter", b"unspecified"]
        data = (ROOT / path).read_bytes()
        raw_blob = run_git("hash-object", "--no-filters", "--stdin", data=data).strip()
        clean_blob = run_git("hash-object", f"--path={path}", "--stdin", data=data).strip()
        assert raw_blob == clean_blob, f"Git clean filter changes {path}"
