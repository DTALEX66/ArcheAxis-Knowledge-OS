"""Finite upstream URL mapping in an isolated synthetic package layout.

No HTML, package scripts, network, model, product route or Core task is run.
The module loader and hash checks are test/prototype boundaries, not a sandbox.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import threading
from functools import lru_cache

import pytest

from scripts.release.tauri_portable_candidate import native


ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services/learning-providers/openmaic"
NPM = SERVICE / "vendor/npm"
DONOR = SERVICE / "vendor/scene-content-0.3.28-original/generation"
WORKER = SERVICE / "interactive-url-map-worker.mjs"
NODE = os.environ.get("ARCHEAXIS_TEST_NODE")
NODE_SHA256 = "ba4e6d110e8c1592a1ecd390f6b05f3da124b13871a5be62b341a07a853c6c32"
SCHEMA = "archeaxis.openmaic-interactive-url-map/v1"
ORIGINALS_SHA256 = "5679a80166d41114448ab35a1e2128a56baca7c9611218af590c81f3889d1ce3"
ORIGINALS = {
    "package.json": "5308b268d06dd27e592de00f02d57b046588df0d6e160f4179788388d5a806d1",
    "LICENSE": "ba252563743227138231604c9138dd400faca5a10c3cf206b466e5466c565a19",
    "src/interactive-library-mapper.ts": "fe4637cc0e32cd557dcdc285017008cfe741e7799478a9c9ec102cc97194b1fe",
    "src/interactive-libraries.ts": "1c9f212d7e2010dd3e1f4889efe22825fcb1f52772b056e5a30fc58753f29de1",
}
PACKAGES = {
    "parse5-8.0.1": ("fb5a2c507c9c2d2c59073df562e2131ada5860b3370ebc9508762bc4be1cad30", 33),
    "entities-8.0.0": ("91fd19349c025f903464fe8d0e4ab5464708db4386024dbd9957c273c91a422c", 58),
    "es-module-lexer-2.0.0": ("2c222673e20d94f84a03d8a277df5a91c842053a6e991a44cec6b62e8aa45d71", 8),
    "postcss-8.5.23": ("b0e2faa80c9539b2f9b5d5e8e67b328dbf421130a02cd1695a5da659447ca61f", 55),
    "postcss-value-parser-4.2.0": ("d7b344a5bd2494aea12255918bf24e4dd4a34ba80a06d9bb399ea5469e145607", 9),
    "nanoid-3.3.19": ("3495da1b2b7f1c42952fc5090cd0eb818f207eb70a9f2083837ffedfa6dbdcf4", 25),
    "picocolors-1.1.1": ("04718da4913e9256b832a9227dc9ee4a875e5f7f7b57c44592caadcc612bb057", 7),
    "source-map-js-1.2.1": ("20eaf7236bed35a6bb8a316852680637c369ea7a3c0ec6aabc3fb51eb47c7bbe", 18),
}
requires_node = pytest.mark.skipif(not NODE, reason="explicit, preverified ARCHEAXIS_TEST_NODE is required; PATH is not searched")


def read_bytes(path: Path) -> bytes:
    with open(native(path), "rb") as stream:
        return stream.read()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_sources() -> dict[str, dict]:
    raw = read_bytes(DONOR / "ORIGINALS.json")
    assert digest(raw) == ORIGINALS_SHA256
    original = json.loads(raw)["originals"]
    for name, expected in ORIGINALS.items():
        assert original[name] == expected and digest(read_bytes(DONOR.joinpath(*PurePosixPath(name).parts))) == expected
    packages = {}
    for stem, (expected_sha, count) in PACKAGES.items():
        root = NPM / stem
        raw = read_bytes(root / "SOURCE.json")
        assert digest(raw) == expected_sha
        manifest = json.loads(raw)
        files = manifest["files"]
        assert len(files) == count
        actual = {item.relative_to(root).as_posix() for item in root.rglob("*") if item.is_file()}
        assert actual == set(files) | {"SOURCE.json"}
        for name, identity in files.items():
            rel = PurePosixPath(name)
            assert not rel.is_absolute() and ".." not in rel.parts and "\\" not in name and ":" not in name
            source = root.joinpath(*rel.parts)
            assert source.is_file() and not source.is_symlink()
            data = read_bytes(source)
            assert (len(data), digest(data)) == (identity["bytes"], identity["sha256"])
        packages[stem] = manifest
    assert sum(len(manifest["files"]) for manifest in packages.values()) == 213
    return packages


def write_new(path: Path, data: bytes) -> None:
    os.makedirs(native(path.parent), exist_ok=True)
    with open(native(path), "xb") as stream:
        stream.write(data)
    assert read_bytes(path) == data


def stage_sources(stage: Path) -> None:
    packages = check_sources()
    write_new(stage / WORKER.name, read_bytes(WORKER))
    donor_target = stage / "vendor/scene-content-0.3.28-original/generation"
    for name in (*ORIGINALS, "ORIGINALS.json"):
        write_new(donor_target.joinpath(*PurePosixPath(name).parts), read_bytes(DONOR.joinpath(*PurePosixPath(name).parts)))
    for stem, manifest in packages.items():
        for name in (*manifest["files"], "SOURCE.json"):
            relative = PurePosixPath(name)
            write_new((stage / "vendor/npm" / stem).joinpath(*relative.parts),
                      read_bytes((NPM / stem).joinpath(*relative.parts)))
    # These synthetic decoys would fail if the worker fell back to an ambient
    # same-named package. No decoy is allowed to execute in a successful run.
    write_new(stage / "node_modules/nanoid/package.json",
              b'{"name":"nanoid","version":"5.1.14","exports":{"./non-secure":"./non-secure/index.cjs"}}')
    write_new(stage / "node_modules/nanoid/non-secure/index.cjs", b"throw Error('SYNTHETIC_NANOID_DECOY')\n")
    write_new(stage / "node_modules/entities/package.json",
              b'{"name":"entities","version":"6.0.1","type":"module","exports":{"./decode":"./decode.js","./escape":"./escape.js"}}')
    write_new(stage / "node_modules/entities/decode.js", b"throw Error('SYNTHETIC_ENTITIES_DECOY')\n")
    write_new(stage / "node_modules/entities/escape.js", b"throw Error('SYNTHETIC_ENTITIES_DECOY')\n")


@lru_cache(maxsize=1)
def checked_node() -> Path:
    assert NODE and Path(NODE).is_absolute()
    node = Path(NODE)
    assert node.is_file()
    h = hashlib.sha256()
    with node.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    assert h.hexdigest() == NODE_SHA256
    return node


def call(stage: Path, raw: bytes, *, env_override: dict[str, str] | None = None,
         node_args: tuple[str, ...] = ()) -> tuple[dict, bytes, bytes]:
    node = checked_node()
    env = {key: os.environ[key] for key in ("SystemRoot", "SYSTEMROOT", "WINDIR") if key in os.environ}
    if env_override:
        env.update(env_override)
    process = subprocess.Popen([str(node), *node_args, str(stage / WORKER.name)], cwd=str(stage), env=env,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    streams: dict[str, bytes] = {}
    errors: list[str] = []

    def bounded(pipe, name):
        try:
            data = pipe.read(8193)
            streams[name] = data
            if len(data) > 8192:
                try:
                    process.kill()
                except OSError:
                    pass
        except OSError as error:
            errors.append(type(error).__name__)

    def send():
        try:
            process.stdin.write(raw)
            process.stdin.close()
        except (BrokenPipeError, OSError):
            # An intentional early rejection can close stdin before the writer.
            pass

    readers = [threading.Thread(target=bounded, args=(process.stdout, "stdout"), daemon=True),
               threading.Thread(target=bounded, args=(process.stderr, "stderr"), daemon=True)]
    writer = threading.Thread(target=send, daemon=True)
    for thread in (*readers, writer):
        thread.start()
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
        raise AssertionError("owned synthetic Node process exceeded its deadline")
    finally:
        for thread in (*readers, writer):
            thread.join(timeout=5)
    assert not any(thread.is_alive() for thread in (*readers, writer)), "owned process pipe cleanup unconfirmed"
    assert not errors and process.returncode == 0
    assert len(streams["stdout"]) <= 8192 and len(streams["stderr"]) <= 8192
    return json.loads(streams["stdout"]), streams["stdout"], streams["stderr"]


def request(url: str, request_id: str = "synthetic_1") -> bytes:
    return (json.dumps({"schema": SCHEMA, "request_id": request_id, "url": url}, ensure_ascii=False) + "\n").encode()


def assert_boundaries(result: dict) -> None:
    assert result["schema"] == SCHEMA and result["source"] == "CALLER_SUPPLIED_UNVERIFIED"
    assert (result["provider"], result["provider_version"], result["generation_version"]) == ("openmaic", "1.3.0", "0.3.28")
    assert result["expected_source_sha256"] == ORIGINALS["src/interactive-library-mapper.ts"]
    assert "source_sha256" not in result
    verified = (result["status"] in {"MAPPED", "UNMAPPED"} or
                result.get("error_code") == "UNSAFE_UPSTREAM_PATH")
    assert result["source_verification"] == ("VERIFIED_SELECTED_MEMBERS" if verified else "NOT_ASSERTED")
    assert result["resource_availability"] == "NOT_VERIFIED"
    assert result["network_isolation"] == "NOT_ESTABLISHED"
    assert result["core_authorization"] == "NOT_ESTABLISHED"
    assert result["security_sanitizer"] is False and result["input_script_executed"] is False


def test_fixed_source_members_are_self_contained():
    check_sources()


@requires_node
def test_original_mapper_returns_pinned_paths_and_isolates_unsafe_results(tmp_path):
    stage = tmp_path / "u"
    stage_sources(stage)
    cases = [
        ("https://unpkg.com/katex@0.16.9/dist/katex.min.js", "MAPPED",
         "/vendor/interactive/katex@0.16.38/dist/katex.min.js"),
        ("https://unpkg.com/chart.js@4.0.0/dist/chart.umd.min.js", "MAPPED",
         "/vendor/interactive/chart.js@4.4.8/dist/chart.umd.js"),
        ("/vendor/interactive/chart.js@4.4.8/dist/chart.umd.js", "MAPPED",
         "/vendor/interactive/chart.js@4.4.8/dist/chart.umd.js"),
        ("https://unknown.invalid/chart.js@4", "UNMAPPED", None),
        ("https://SYNTHETIC_USER:SYNTHETIC_PASSWORD@unknown.invalid/a?token=SYNTHETIC_QUERY", "UNMAPPED", None),
        ("https://cdn.jsdelivr.net/npm/chart.js@4?module", "UNMAPPED", None),
        ("/vendor/interactive/../../escape", "REJECTED", None),
        ('/vendor/interactive/three@0.160.0/build/evil".js', "REJECTED", None),
    ]
    for url, status, path in cases:
        result, stdout, stderr = call(stage, request(url))
        assert_boundaries(result)
        assert result["request_id"] == "synthetic_1" and result["input_sha256"] == digest(url.encode())
        assert result["status"] == status and result["path"] == path
        assert b"SYNTHETIC_NANOID_DECOY" not in stdout + stderr
        assert b"SYNTHETIC_ENTITIES_DECOY" not in stdout + stderr
        assert b"SYNTHETIC_USER" not in stdout + stderr and b"SYNTHETIC_PASSWORD" not in stdout + stderr
        assert b"SYNTHETIC_QUERY" not in stdout + stderr
        if status == "MAPPED":
            assert result["upstream_returned"] is True and result["changed"] is (url != path)
            assert result["upstream_result_sha256"] == digest(path.encode())
        elif status == "UNMAPPED":
            assert result["upstream_returned"] is False and result["upstream_result_sha256"] is None
        else:
            assert result["upstream_returned"] is True and result["error_code"] == "UNSAFE_UPSTREAM_PATH"
            # The upstream local-prefix branch returned this exact unsafe input;
            # the wrapper records only its hash and withholds the usable path.
            assert result["upstream_result_sha256"] == digest(url.encode())
            assert url.encode() not in stdout


@requires_node
def test_bad_requests_are_rejected_without_reflecting_unknown_fields(tmp_path):
    stage = tmp_path / "u"
    stage_sources(stage)
    base = '{"schema":"' + SCHEMA + '","request_id":"id","url":"https://example.invalid/x"'
    raw_cases = [
        (base + ',"secret":"SYNTHETIC_PRIVATE_SENTINEL"}').encode(),
        (base + ',"url":"https://duplicate.invalid/x"}').encode(),
        (base + '} {"second":"object"}').encode(),
        b'{"schema":"' + SCHEMA.encode() + b'","request_id":"id","url":"https://example.invalid/\xff"}',
        request("https://example.invalid/" + "a" * 4097),
    ]
    for raw in raw_cases:
        result, stdout, stderr = call(stage, raw)
        assert_boundaries(result)
        assert result["status"] == "REJECTED" and result["error_code"] == "INVALID_REQUEST"
        assert result["path"] is None and "request_id" not in result and "input_sha256" not in result
        assert b"SYNTHETIC_PRIVATE_SENTINEL" not in stdout + stderr
        assert b"duplicate.invalid" not in stdout + stderr
    oversized = request("https://example.invalid/" + "a" * 17000)
    result, _, _ = call(stage, oversized)
    assert_boundaries(result)
    assert result["status"] == "REJECTED" and result["error_code"] == "INPUT_TOO_LARGE"
    assert result["path"] is None and "request_id" not in result and "input_sha256" not in result


@requires_node
def test_environment_overrides_are_rejected(tmp_path):
    stage = tmp_path / "u"
    stage_sources(stage)
    for override in ({"INTERACTIVE_ASSET_BASE_URL": "https://synthetic.invalid/assets"},
                     {"NODE_PATH": "synthetic-ambient-packages"}, {"NODE_OPTIONS": "--no-warnings"}):
        result, stdout, stderr = call(stage, request("https://unpkg.com/chart.js@4"), env_override=override)
        assert_boundaries(result)
        assert result["status"] == "REJECTED" and result["error_code"] == "ENVIRONMENT_OVERRIDE"
        assert result["path"] is None and b"synthetic.invalid" not in stdout + stderr


@requires_node
def test_ambient_node_flags_are_rejected(tmp_path):
    stage = tmp_path / "u"
    stage_sources(stage)
    result, _, _ = call(stage, request("https://unpkg.com/chart.js@4"), node_args=("--conditions=browser",))
    assert_boundaries(result)
    assert result["status"] == "REJECTED" and result["error_code"] == "NODE_IDENTITY_MISMATCH"


@requires_node
def test_missing_or_tampered_member_fails_before_mapping_without_fallback(tmp_path):
    stage = tmp_path / "u"
    stage_sources(stage)
    npm = stage / "vendor/npm"
    targets = {
        "missing_entities8": npm / "entities-8.0.0/dist/decode.js",
        "missing_nanoid3": npm / "nanoid-3.3.19/SOURCE.json",
        "tampered_nanoid3": npm / "nanoid-3.3.19/non-secure/index.cjs",
        "tampered_manifest": npm / "parse5-8.0.1/SOURCE.json",
        "tampered_mapper": stage / "vendor/scene-content-0.3.28-original/generation/src/interactive-library-mapper.ts",
        "tampered_libraries": stage / "vendor/scene-content-0.3.28-original/generation/src/interactive-libraries.ts",
    }
    for case, target in targets.items():
        original = read_bytes(target)
        try:
            if case.startswith("missing_"):
                os.unlink(native(target))
            else:
                with open(native(target), "ab") as stream:
                    stream.write(b"\n/* synthetic tamper */\n")
            result, stdout, stderr = call(stage, request("https://unpkg.com/chart.js@4"))
            assert_boundaries(result)
            expected = ("UPSTREAM_IDENTITY_MISMATCH" if case in {"tampered_mapper", "tampered_libraries"}
                        else "DEPENDENCY_IDENTITY_MISMATCH")
            assert result["status"] == "REJECTED" and result["error_code"] == expected and result["path"] is None
            assert "input_sha256" not in result
            assert b"SYNTHETIC_NANOID_DECOY" not in stdout + stderr
            assert b"SYNTHETIC_ENTITIES_DECOY" not in stdout + stderr
        finally:
            # Restore only this test's own isolated copy before the next case.
            with open(native(target), "wb") as stream:
                stream.write(original)
            assert read_bytes(target) == original
