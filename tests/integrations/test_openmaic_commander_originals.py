"""Offline commander identity and synthetic behavior; not KaTeX integration."""
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

from tests.integrations.test_openmaic_npm_git_ignore import (
    configuration_environments,
    ignored_paths,
    invoke_git,
    require_readable_effective_excludes,
)


ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / "services/learning-providers/openmaic/vendor/npm/commander-8.3.0"
CACHE = (ROOT / ".project-local/cache/npm"
         / "openmaic-owner-4660cd2b97ac2a3862cd238fc28b54195a622c8beabb87c9185d87f626f47a29"
         / "backend-verify-npm-commander-fetch-9aa2c4e0be/commander-8.3.0.tgz")
ARCHIVE_SRI = "sha512-OkTL9umf+He2DZkUq8f8J9of7yL6RJKI24dVITBmNfZBmri9zYZQrKkuXiKhyfPSu8tUhnVBB1iKXevvnlR4Ww=="
ARCHIVE_SHA256 = "1b38e65f9229a84060ca5d041a58e3bc1ea374da6d933f9060ca86a67949c10b"
SOURCE_SHA256 = "bd5a268b5062ffa660dd441121059d453d193c681522ca5e490232399d093fea"
LICENSE_SHA256 = "04512a63dce4d2d506ad612dc0bd7681ccf6e3655f7b6eaef7dfac8323d1ec0b"
NODE_SHA256 = "ba4e6d110e8c1592a1ecd390f6b05f3da124b13871a5be62b341a07a853c6c32"
NODE = os.environ.get("ARCHEAXIS_TEST_NODE")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_originals() -> dict:
    raw = (VENDOR / "SOURCE.json").read_bytes()
    assert digest(raw) == SOURCE_SHA256
    manifest = json.loads(raw)
    assert (manifest["name"], manifest["version"], manifest["license"]) == ("commander", "8.3.0", "MIT")
    assert (manifest["archive_sha256"], manifest["archive_bytes"], manifest["archive_sri"]) == (ARCHIVE_SHA256, 39361, ARCHIVE_SRI)
    assert manifest["origin"] == "https://registry.npmjs.org/" and manifest["scripts_executed"] is False
    assert manifest["fetch_run"] == "backend-verify-npm-commander-fetch-9aa2c4e0be"
    assert manifest["audit_run"] == "backend-verify-npm-katex-audit-b3193af45e"
    files = manifest["files"]
    assert isinstance(files, dict) and len(files) == 13
    assert sum(item["bytes"] for item in files.values()) == 151267
    assert files["LICENSE"]["sha256"] == LICENSE_SHA256
    actual = {path.relative_to(VENDOR).as_posix() for path in VENDOR.rglob("*") if path.is_file()}
    assert actual == set(files) | {"SOURCE.json"}
    for name, identity in files.items():
        relative = PurePosixPath(name)
        assert not relative.is_absolute() and ".." not in relative.parts
        assert re.fullmatch(r"[0-9a-f]{64}", identity["sha256"]) and isinstance(identity["bytes"], int)
        path = VENDOR.joinpath(*relative.parts)
        assert path.is_file() and not path.is_symlink()
        data = path.read_bytes()
        assert (len(data), digest(data)) == (identity["bytes"], identity["sha256"])
    package = json.loads((VENDOR / "package.json").read_bytes())
    assert (package["name"], package["version"], package["license"], package["main"]) == ("commander", "8.3.0", "MIT", "./index.js")
    assert all(not package.get(field) for field in ("dependencies", "optionalDependencies", "peerDependencies"))
    return manifest


def test_originals_are_self_contained():
    check_originals()


def test_optional_audited_archive_matches_every_member():
    if not CACHE.is_file():
        pytest.skip("local-only original absent in a Git clone/CI (Git-ignored .project-local input); "
                    "this skip is NOT evidence of byte identity")
    manifest = check_originals()
    compressed = CACHE.read_bytes()
    assert (len(compressed), digest(compressed)) == (39361, ARCHIVE_SHA256)
    assert "sha512-" + base64.b64encode(hashlib.sha512(compressed).digest()).decode("ascii") == ARCHIVE_SRI
    with tarfile.open(fileobj=io.BytesIO(compressed), mode="r:gz") as archive:
        members = archive.getmembers()
        assert len(members) == 13 and all(member.isfile() and member.name.startswith("package/") for member in members)
        names = [member.name.removeprefix("package/") for member in members]
        assert len(set(names)) == len(names) and set(names) == set(manifest["files"])
        for member, name in zip(members, names, strict=True):
            stream = archive.extractfile(member)
            assert stream is not None
            data = stream.read()
            identity = manifest["files"][name]
            assert (len(data), digest(data)) == (identity["bytes"], identity["sha256"])
            assert VENDOR.joinpath(*PurePosixPath(name).parts).read_bytes() == data


def test_git_ignore_and_clean_are_checked_without_index(tmp_path):
    git = shutil.which("git")
    if not git:
        pytest.skip("Git is unavailable")
    if not (ROOT / ".git").exists():
        pytest.skip("not a Git checkout")
    manifest = check_originals()
    paths = [(VENDOR / name).relative_to(ROOT).as_posix() for name in (*manifest["files"], "SOURCE.json")]
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


@pytest.mark.skipif(not NODE, reason="explicit, preverified ARCHEAXIS_TEST_NODE is required; PATH is not searched")
def test_fixed_node_parses_synthetic_options_with_original_commander():
    check_originals()
    node = Path(NODE)
    assert node.is_absolute() and node.is_file()
    executable_sha = hashlib.sha256()
    with node.open("rb") as executable:
        for chunk in iter(lambda: executable.read(1024 * 1024), b""):
            executable_sha.update(chunk)
    assert executable_sha.hexdigest() == NODE_SHA256
    source = r"""
const {Command} = require(process.argv[1]);
const program = new Command();
program.exitOverride();
program.name('synthetic').option('-n, --number <value>').option('--flag');
program.parse(['--number', '3', '--flag'], {from: 'user'});
const body = JSON.stringify({node: process.versions.node, name: program.name(), options: program.opts()});
if (Buffer.byteLength(body, 'utf8') > 4096) process.exit(2);
process.stdout.write(body);
"""
    # No inherited Node options or package scripts. This is not an OS sandbox.
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
        raise AssertionError("synthetic commander process exceeded its deadline")
    finally:
        for reader in readers:
            reader.join(timeout=5)
    assert not any(reader.is_alive() for reader in readers), "package pipe cleanup unconfirmed"
    assert not errors and len(streams["stdout"]) <= 4096 and len(streams["stderr"]) <= 4096
    assert process.returncode == 0 and not streams["stderr"]
    assert json.loads(streams["stdout"]) == {"node": "24.21.0", "name": "synthetic", "options": {"number": "3", "flag": True}}
