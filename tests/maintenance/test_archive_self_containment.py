"""Small synthetic closure fixtures prove local availability and fail closed."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import zipfile

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/maintenance/verify_archive_self_contained.py"
SPEC = importlib.util.spec_from_file_location("archive_self_containment", SCRIPT)
assert SPEC and SPEC.loader
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


def write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def closure(tmp_path):
    payloads = [b"alpha source", b"beta source", b"source receipt"]
    (tmp_path / "a.txt").write_bytes(payloads[0])
    (tmp_path / "receipt.txt").write_bytes(payloads[2])
    with zipfile.ZipFile(tmp_path / "b.zip", "w") as archive:
        archive.writestr("nested/b.txt", payloads[1])
    rows = []
    for number, data in enumerate(payloads):
        rows.append({"record_id": f"object:{number}" if number < 2 else "source:original.txt",
                     "source_id": f"object:{number}",
                     "kind": "aaos_object" if number < 2 else "source_record",
                     "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                     # Provenance is intentionally unavailable and must never be opened.
                     "archive_original": str(tmp_path.parent / "unavailable-provenance" / f"{number}.txt"),
                     "local": ({"type": "zip_member", "path": "b.zip", "member": "nested/b.txt"}
                               if number == 1 else {"type": "file", "path": "a.txt" if number == 0 else "receipt.txt"})})
    document = {"schema": "archeaxis.repository-local-source-closure/v1",
                "expected_counts": {"aaos_objects": 2, "source_records": 1},
                "source_index": "index.jsonl", "source_manifest": "sources.json", "objects": rows}
    write_json(tmp_path / "closure.json", document)
    (tmp_path / "index.jsonl").write_text("\n".join(json.dumps(row) for row in rows[:2]), encoding="utf-8")
    write_json(tmp_path / "sources.json", {"source_records": [
        {"path": "original.txt", "sha256": rows[2]["sha256"], "bytes": rows[2]["bytes"]}]})
    return tmp_path, document


def verify_fixture(closure):
    root, document = closure
    write_json(root / "closure.json", document)
    return VERIFIER.verify(root, "closure.json")


def test_local_files_and_zip_members_succeed_without_external_provenance(closure, monkeypatch):
    root, _ = closure
    original = Path.open
    def local_only(path, *args, **kwargs):
        assert path.is_relative_to(root), f"external provenance opened: {path}"
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", local_only)
    result = verify_fixture(closure)
    assert result == {"status": "LOCAL_SOURCE_CLOSURE_VERIFIED", "aaos_objects": 2,
                      "source_records": 1, "unique_local_locators": 3, "external_reads": 0,
                      "product_acceptance": "NOT_EVALUATED", "git_clone_includes_ignored_originals": False}


@pytest.mark.parametrize("name", ["a.txt", "b.zip", "receipt.txt", "index.jsonl", "sources.json"])
def test_missing_local_material_is_rejected(closure, name):
    root, _ = closure
    (root / name).unlink()
    with pytest.raises(OSError):
        verify_fixture(closure)


@pytest.mark.parametrize("name", ["a.txt", "receipt.txt"])
def test_same_size_file_tampering_is_rejected(closure, name):
    root, _ = closure
    path = root / name
    path.write_bytes(b"X" * path.stat().st_size)
    with pytest.raises(ValueError, match="hash/size mismatch"):
        verify_fixture(closure)


def test_same_size_zip_member_tampering_is_rejected(closure):
    root, document = closure
    with zipfile.ZipFile(root / "b.zip", "w") as archive:
        archive.writestr("nested/b.txt", b"X" * document["objects"][1]["bytes"])
    with pytest.raises(ValueError, match="hash/size mismatch"):
        verify_fixture(closure)


def test_duplicate_zip_member_is_rejected(closure):
    root, _ = closure
    with pytest.warns(UserWarning, match="Duplicate name"):
        with zipfile.ZipFile(root / "b.zip", "a") as archive:
            archive.writestr("nested/b.txt", b"beta source")
    with pytest.raises(ValueError, match="ambiguous"):
        verify_fixture(closure)


def test_missing_zip_member_is_rejected(closure):
    _, document = closure
    document["objects"][1]["local"]["member"] = "absent.txt"
    with pytest.raises(ValueError, match="ambiguous"):
        verify_fixture(closure)


@pytest.mark.parametrize(
    "bad",
    [
        "../outside.txt",
        "/outside.txt",
        pytest.param(
            "C:/outside.txt",
            marks=pytest.mark.skipif(
                sys.platform != "win32",
                reason=(
                    "a drive-qualified path is absolute only on Windows; on POSIX "
                    "'C:' is a legal relative component, so there is nothing unsafe "
                    "to reject and opening it legitimately misses the file"
                ),
            ),
        ),
    ],
)
def test_unsafe_local_file_path_is_rejected_before_open(closure, monkeypatch, bad):
    root, document = closure
    document["objects"][0]["local"]["path"] = bad
    original = Path.open
    def local_only(path, *args, **kwargs):
        assert path.is_relative_to(root), f"unsafe target opened: {path}"
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", local_only)
    with pytest.raises(ValueError):
        verify_fixture(closure)


@pytest.mark.parametrize("bad", ["../outside.txt", "/outside.txt", "C:/outside.txt", "nested\\outside.txt"])
def test_unsafe_member_is_rejected_even_when_present_in_zip(closure, bad):
    root, document = closure
    document["objects"][1]["local"]["member"] = bad
    with zipfile.ZipFile(root / "b.zip", "w") as archive:
        archive.writestr(bad, b"beta source")
    with pytest.raises(ValueError, match="unsafe member"):
        verify_fixture(closure)


@pytest.mark.parametrize("source", ["index", "manifest"])
def test_wrong_source_identity_set_is_rejected(closure, source):
    root, document = closure
    if source == "index":
        row = dict(document["objects"][0], sha256="0" * 64)
        (root / "index.jsonl").write_text(json.dumps(row), encoding="utf-8")
    else:
        write_json(root / "sources.json", {"source_records": []})
    with pytest.raises(ValueError, match="identity set mismatch"):
        verify_fixture(closure)


@pytest.mark.parametrize("row_number", [0, 1, 2])
def test_actual_local_size_mismatch_is_rejected(closure, row_number):
    root, document = closure
    row = document["objects"][row_number]
    row["bytes"] += 1
    # Keep source declarations consistent: failure must come from actual local bytes.
    if row_number < 2:
        (root / "index.jsonl").write_text("\n".join(json.dumps(r) for r in document["objects"][:2]), encoding="utf-8")
    else:
        write_json(root / "sources.json", {"source_records": [
            {"path": "original.txt", "sha256": row["sha256"], "bytes": row["bytes"]}]})
    with pytest.raises(ValueError, match="hash/size mismatch|wrong-sized"):
        verify_fixture(closure)


def test_duplicate_record_identity_is_rejected(closure):
    _, document = closure
    document["objects"][1]["record_id"] = document["objects"][0]["record_id"]
    with pytest.raises(ValueError, match="duplicate record"):
        verify_fixture(closure)


def test_unknown_kind_cannot_fill_a_declared_source_record_count(closure):
    _, document = closure
    document["objects"][2]["kind"] = "unknown"
    with pytest.raises(ValueError, match="kind count mismatch"):
        verify_fixture(closure)


def test_wrong_original_source_id_is_rejected_even_with_matching_hashes(closure):
    root, document = closure
    rows = [dict(row) for row in document["objects"][:2]]
    rows[0]["source_id"] = "another-source-id"
    (root / "index.jsonl").write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    with pytest.raises(ValueError, match="record identity mismatch"):
        verify_fixture(closure)


def test_repeated_locator_cannot_bypass_type_validation_via_hash_cache(closure):
    root, document = closure
    first, repeated = document["objects"][0], document["objects"][2]
    repeated.update(sha256=first["sha256"], bytes=first["bytes"],
                    local={"type": "unsupported", "path": "a.txt"})
    write_json(root / "sources.json", {"source_records": [
        {"path": "original.txt", "sha256": repeated["sha256"], "bytes": repeated["bytes"]}]})
    with pytest.raises(ValueError, match="unsupported local locator"):
        verify_fixture(closure)


def test_cli_reports_failure_for_a_real_missing_local_file(closure, monkeypatch, capsys):
    root, document = closure
    monkeypatch.setattr(VERIFIER, "ROOT", root)
    monkeypatch.setattr("sys.argv", [str(SCRIPT), "--manifest", "closure.json"])
    assert VERIFIER.main() == 0
    capsys.readouterr()
    (root / document["objects"][0]["local"]["path"]).unlink()
    assert VERIFIER.main() == 1
    assert "local source closure failed" in capsys.readouterr().err
