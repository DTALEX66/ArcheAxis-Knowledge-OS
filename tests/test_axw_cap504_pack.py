"""AXW-CAP-504 Capability Pack builder tests.

Proves: ``scripts/capability_pack.py`` builds a real ``<name>-<version>.pack.zip``
(pack.json with manifests + per-file sha256, files/ payload), that
pack.json hashes match the actual file contents, that ``verify`` refuses
tampered files and lying hashes, that the builder refuses invalid
manifests/missing asset dirs/unsafe paths, and that the built pack is
consumable by ``scripts/capability_download.py`` stage -> verify without
any interface change.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from scripts.capability_download import cmd_stage, cmd_verify
from scripts.capability_pack import (
    PACK_JSON,
    PackBuildError,
    _assert_safe_rel,
    build_pack,
    main,
    verify_pack,
)
from shared.plugin_manifest import MANIFEST_VERSION


def _fake_manifest(plugin_id: str, name: str, version: str = "1.0.0") -> dict:
    return {
        "manifest_version": MANIFEST_VERSION,
        "plugin_id": plugin_id,
        "name": name,
        "version": version,
        "api_contract": "1.x",
        "permissions": ["files.read"],
        "platform": {"os": "windows", "arch": "x86_64"},
        "entry": "entry.py",
        "data_ownership": {"declared": True, "note": "test fixture"},
        "healthcheck": "import:entry",
    }


def _assets(tmp_path: Path) -> Path:
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "note.md").write_text("# hello\n", encoding="utf-8")
    (assets / "blob.bin").write_bytes(b"\x00\x01\x02\xff")
    return assets


def test_build_pack_structure_and_hashes(tmp_path: Path) -> None:
    manifests = [
        _fake_manifest("ax.test.alpha", "Alpha"),
        _fake_manifest("ax.test.beta", "Beta"),
    ]
    pack_path = build_pack(manifests, _assets(tmp_path), tmp_path / "out")

    assert pack_path.name == "ax.test.alpha-1.0.0.pack.zip"
    assert pack_path.is_file()
    with zipfile.ZipFile(pack_path) as zf:
        names = set(zf.namelist())
        assert PACK_JSON in names
        assert {"files/note.md", "files/blob.bin"} <= names

        pack = json.loads(zf.read(PACK_JSON))
        # schema fields are all present
        assert pack["pack_format"] == 1
        assert pack["name"] == "ax.test.alpha"
        assert pack["version"] == "1.0.0"
        assert pack["created_at"]
        assert [entry["plugin_id"] for entry in pack["manifests"]] == [
            "ax.test.alpha",
            "ax.test.beta",
        ]
        by_path = {entry["path"]: entry for entry in pack["files"]}
        assert set(by_path) == {"files/note.md", "files/blob.bin"}
        for rel, entry in by_path.items():
            payload = zf.read(rel)
            assert entry["sha256"] == hashlib.sha256(payload).hexdigest()
            assert entry["size_bytes"] == len(payload)

    # the verifier agrees with the on-disk zip
    assert verify_pack(pack_path) == ["files/blob.bin", "files/note.md"]


def test_build_pack_without_assets(tmp_path: Path) -> None:
    pack_path = build_pack([_fake_manifest("ax.test.solo", "Solo")], None, tmp_path)
    with zipfile.ZipFile(pack_path) as zf:
        pack = json.loads(zf.read(PACK_JSON))
        assert pack["files"] == []
    assert verify_pack(pack_path) == []


def test_verify_refuses_tampered_file_content(tmp_path: Path) -> None:
    pack_path = build_pack([_fake_manifest("ax.test.alpha", "Alpha")], _assets(tmp_path), tmp_path)
    tampered = tmp_path / "tampered.pack.zip"
    with zipfile.ZipFile(pack_path) as src, zipfile.ZipFile(tampered, "w") as dst:
        for name in src.namelist():
            data = src.read(name)
            if name == "files/note.md":
                data = data.replace(b"hello", b"TAMPERED")
            dst.writestr(name, data)
    with pytest.raises(PackBuildError, match="sha256 mismatch"):
        verify_pack(tampered)


def test_verify_refuses_lying_hash_in_pack_json(tmp_path: Path) -> None:
    pack_path = build_pack([_fake_manifest("ax.test.alpha", "Alpha")], _assets(tmp_path), tmp_path)
    tampered = tmp_path / "lied.pack.zip"
    with zipfile.ZipFile(pack_path) as src, zipfile.ZipFile(tampered, "w") as dst:
        for name in src.namelist():
            data = src.read(name)
            if name == PACK_JSON:
                pack = json.loads(data)
                pack["files"][0]["sha256"] = "0" * 64
                data = json.dumps(pack, indent=2, sort_keys=True).encode("utf-8")
            dst.writestr(name, data)
    with pytest.raises(PackBuildError, match="sha256 mismatch"):
        verify_pack(tampered)


def test_verify_refuses_orphan_file_not_listed_in_pack_json(tmp_path: Path) -> None:
    pack_path = build_pack([_fake_manifest("ax.test.alpha", "Alpha")], _assets(tmp_path), tmp_path)
    tampered = tmp_path / "orphan.pack.zip"
    with zipfile.ZipFile(pack_path) as src, zipfile.ZipFile(tampered, "w") as dst:
        for name in src.namelist():
            dst.writestr(name, src.read(name))
        dst.writestr("files/sneaky.txt", "payload")
    with pytest.raises(PackBuildError, match="file list mismatch"):
        verify_pack(tampered)


def test_build_refuses_invalid_manifest(tmp_path: Path) -> None:
    bad = _fake_manifest("ax.test.bad", "Bad")
    bad["permissions"] = ["rm -rf"]
    with pytest.raises(ValueError, match="rm -rf"):
        build_pack([bad], None, tmp_path)


def test_build_refuses_empty_manifest_list(tmp_path: Path) -> None:
    with pytest.raises(PackBuildError, match="at least one"):
        build_pack([], None, tmp_path)


def test_build_refuses_missing_assets_dir(tmp_path: Path) -> None:
    with pytest.raises(PackBuildError, match="assets directory"):
        build_pack([_fake_manifest("ax.test.alpha", "Alpha")], tmp_path / "nope", tmp_path)


def test_unsafe_entry_paths_refused() -> None:
    with pytest.raises(PackBuildError, match="unsafe"):
        _assert_safe_rel("../evil.txt")
    with pytest.raises(PackBuildError, match="unsafe"):
        _assert_safe_rel("files/../../evil.txt")
    with pytest.raises(PackBuildError, match="unsafe"):
        _assert_safe_rel("C:/absolute.txt")
    _assert_safe_rel("files/ok.txt")  # safe paths pass


def test_cli_build_and_verify_roundtrip(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest_path = tmp_path / "plugin-manifest.json"
    manifest_path.write_text(json.dumps(_fake_manifest("ax.test.cli", "CLI")), encoding="utf-8")
    out = tmp_path / "out"

    assert main(["build", "--manifest", str(manifest_path), "--out", str(out)]) == 0
    pack = out / "ax.test.cli-1.0.0.pack.zip"
    assert pack.is_file()

    assert main(["verify", str(pack)]) == 0
    captured = capsys.readouterr()
    assert "verify OK" in captured.out

    # a missing pack is refused with a non-zero exit code
    assert main(["verify", str(tmp_path / "missing.pack.zip")]) == 1


def test_pack_consumable_by_capability_download_stage_verify(tmp_path: Path) -> None:
    """The built .pack.zip is one artifact the download-governance CLI can
    stage (file:// URL) and verify — no interface change to that CLI."""
    pack_path = build_pack([_fake_manifest("ax.test.alpha", "Alpha")], None, tmp_path)
    dest = tmp_path / "staging"

    assert (
        cmd_stage(
            argparse.Namespace(
                url=pack_path.as_uri(),
                dest_dir=str(dest),
                name="ax.test.alpha-1.0.0.pack.zip",
                license="MIT",
                license_url="",
                force=False,
            )
        )
        == 0
    )
    download_manifest = dest / "ax.test.alpha-1.0.0.pack.zip.download-manifest.json"
    assert download_manifest.is_file()
    assert cmd_verify(argparse.Namespace(manifest=str(download_manifest))) == 0
