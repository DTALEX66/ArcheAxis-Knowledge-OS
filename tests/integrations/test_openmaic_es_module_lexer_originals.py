"""Offline identity and synthetic JS lexer behavior, not OpenMAIC qualification."""
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
VENDOR = ROOT / "services/learning-providers/openmaic/vendor/npm/es-module-lexer-2.0.0"
CACHE = (ROOT / ".project-local/cache/npm"
         / "openmaic-owner-4660cd2b97ac2a3862cd238fc28b54195a622c8beabb87c9185d87f626f47a29"
         / "backend-verify-npm-es-fetch-6e9aa3a383")
ARCHIVE = CACHE / "es-module-lexer-2.0.0.tgz"
ARCHIVE_SRI = "sha512-5POEcUuZybH7IdmGsD8wlf0AI55wMecM9rVBTI/qEAy2c1kTOm3DjFYjrBdI2K3BaJjJYfYFeRtM0t9ssnRuxw=="
ARCHIVE_SHA256 = "723f195974be6363e0b5c75824b2ac24a9ded20de98e298f3ec33b8c7f17b43a"
SOURCE_SHA256 = "2c222673e20d94f84a03d8a277df5a91c842053a6e991a44cec6b62e8aa45d71"
NODE_SHA256 = "ba4e6d110e8c1592a1ecd390f6b05f3da124b13871a5be62b341a07a853c6c32"
NODE = os.environ.get("ARCHEAXIS_TEST_NODE")
FILES = {
    "LICENSE": (1095, "fecc38b5e10d889686b3862e7ade17e8b3e5c94b24b7256b05a354d8524b3274"),
    "README.md": (11423, "d85ead05690ae9118b36a911b7122ed0f6d0ed3ce605dd776ff61357b3c2e033"),
    "dist/lexer.asm.js": (21184, "e1fc80f5096702350c2e30ff4095e35fddc98fb07b902bf2e5d9a8e70e6f82af"),
    "dist/lexer.cjs": (14787, "4fce6f80c9919dd063de1dce2e06a85a3948109263115223a8fb7b0deeca953c"),
    "dist/lexer.js": (14668, "4cc7b4f14ce0dbcece5154e4f069217e013b8f04098adde99d230228977c016e"),
    "lexer.js": (26599, "868ab413367cc9d85ed9cbe5aedcdbaeb97b4e968b0c2cd8ba45d408e3f6739f"),
    "package.json": (1464, "98175eed3b65f199b6482325421978a42a7e17fc2e52d04055c83f1e58eb210b"),
    "types/lexer.d.ts": (6103, "eb4f66ca424c996c2defcfb03e901a408bee2d992020104ed587e243a872acc4"),
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_manifest_and_original_members():
    raw = (VENDOR / "SOURCE.json").read_bytes()
    assert digest(raw) == SOURCE_SHA256
    manifest = json.loads(raw)
    assert manifest["name"] == "es-module-lexer" and manifest["version"] == "2.0.0"
    assert manifest["license"] == "MIT" and manifest["archive_sri"] == ARCHIVE_SRI
    assert (manifest["archive_sha256"], manifest["archive_bytes"]) == (ARCHIVE_SHA256, 32377)
    assert manifest["origin"] == "https://registry.npmjs.org/" and manifest["scripts_executed"] is False
    assert manifest["fetch_run"] == "backend-verify-npm-es-fetch-6e9aa3a383"
    assert manifest["audit_run"] == "backend-verify-npm-es-audit-63de9e7bc2"
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
    assert (package["name"], package["version"], package["license"]) == ("es-module-lexer", "2.0.0", "MIT")
    assert all(not package.get(field) for field in ("dependencies", "optionalDependencies", "peerDependencies"))
    assert package["exports"]["./js"]["default"] == "./dist/lexer.asm.js"


def test_manifest_and_all_original_members_are_self_contained():
    check_manifest_and_original_members()


def test_local_locked_archive_members_match_when_available():
    if not ARCHIVE.is_file():
        pytest.skip("ignored verified npm archive is unavailable in this checkout")
    compressed = ARCHIVE.read_bytes()
    assert (len(compressed), digest(compressed)) == (32377, ARCHIVE_SHA256)
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
def test_original_js_export_lexes_synthetic_source_without_executing_it():
    check_manifest_and_original_members()
    node = Path(NODE)
    assert node.is_absolute() and node.is_file()
    executable_sha = hashlib.sha256()
    with node.open("rb") as executable:
        for chunk in iter(lambda: executable.read(1024 * 1024), b""):
            executable_sha.update(chunk)
    assert executable_sha.hexdigest() == NODE_SHA256
    source = r"""
const {pathToFileURL} = require('node:url');
(async () => {
  const lexer = await import(pathToFileURL(process.argv[1]).href);
  const input = "import { x } from './alpha.js';\nexport const y = x;\nconst later = import('./lazy.js');";
  const [imports, exports] = lexer.parse(input);
  const body = JSON.stringify({node: process.versions.node,
    imports: imports.map(item => ({name: item.n, type: item.t})),
    exports: exports.map(item => item.n)});
  if (Buffer.byteLength(body, 'utf8') > 4096) process.exit(2);
  process.stdout.write(body);
})().catch(() => { process.exitCode = 1; });
"""
    # Only the package's fixed ./js target runs; the source string is data.
    # The time and output limits do not establish an OS network sandbox.
    env = {name: os.environ[name] for name in ("SystemRoot", "SYSTEMROOT", "WINDIR") if name in os.environ}
    process = subprocess.Popen([str(node), "-e", source, str(VENDOR / "dist/lexer.asm.js")], stdin=subprocess.DEVNULL,
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
    assert result == {"node": "24.21.0", "imports": [{"name": "./alpha.js", "type": 1},
                                                       {"name": "./lazy.js", "type": 2}],
                      "exports": ["y"]}


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
