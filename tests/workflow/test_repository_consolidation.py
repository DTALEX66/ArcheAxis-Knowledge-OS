"""Synthetic archival guard regressions: no product services or real user data."""
import hashlib
import json
from pathlib import Path

import pytest

from scripts.maintenance.authority_routes import (
    CONSOLIDATION, PUBLIC_RECORDS, PUBLIC_RECORD_BATCHES, RECORD_CONTRACTS, RECORD_CONTRACT_ROWS,
    REGISTRY, PreservedRecords,
    check_consolidation, public_path, resolve,
)


def write(root, name, body):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def save(root, manifest):
    write(root, CONSOLIDATION, json.dumps(manifest))


def scenario(root):
    old = "old-plans/旧 plan.md"
    archive = str(Path(CONSOLIDATION).parent / old).replace("\\", "/")
    raw = b"historical bytes\r\n"
    path = root / archive
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    write(root, "docs/current/handoff.md", "current\n")
    write(root, "README.md", "[current](docs/current/handoff.md)\n")
    write(root, "docs/guide.md", "current\n")
    routes = {"aliases": [], "entries": [
        {"path": "README.md", "role": "LIVE_NAVIGATION"},
        {"path": "docs/guide.md", "role": "LIVE_NAVIGATION"},
        {"path": archive, "role": "HISTORICAL_RECORD"}], "rules": []}
    write(root, REGISTRY, json.dumps(routes))
    manifest = {"schema": "archeaxis.repository-consolidation/v1",
                "source_commit": "a" * 40, "whole_directories": ["old-plans"],
                "files": [{"original_path": old, "archive_path": archive,
                           "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                           "replacement": "docs/current/handoff.md",
                           "role": "HISTORICAL_RECORD", "baseline_commit": "a" * 40}]}
    save(root, manifest)
    return manifest, routes


def test_exact_archive_passes_and_old_locator_resolves_without_stub(tmp_path):
    manifest, routes = scenario(tmp_path)
    assert check_consolidation(tmp_path) == []
    item = manifest["files"][0]
    result = resolve(item["original_path"], routes, tmp_path)
    assert result == {"path": item["original_path"], "role": "RETIRED_LOCATOR",
                      "canonical_path": item["archive_path"],
                      "replacement": item["replacement"]}
    assert not (tmp_path / item["original_path"]).exists()


def compressed_scenario(root):
    import zipfile

    manifest, routes = scenario(root)
    item = manifest["files"][0]
    original = root / item["archive_path"]
    raw = original.read_bytes()
    archive_path = str(Path(PUBLIC_RECORDS).parent / "preoct-public-records.zip").replace("\\", "/")
    archive = root / archive_path
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
        output.writestr(item["archive_path"], raw)
    body = archive.read_bytes()
    descriptor = {"schema": "aaos.preoct-public-records/v1",
                  "archive": {"path": archive_path, "bytes": len(body),
                              "sha256": hashlib.sha256(body).hexdigest()},
                  "files": [{"path": item["archive_path"], "bytes": len(raw),
                             "sha256": hashlib.sha256(raw).hexdigest()}]}
    write(root, PUBLIC_RECORDS, json.dumps(descriptor))
    original.unlink()
    return manifest, routes, descriptor


def test_compression_preserves_original_contract_and_resolves_without_text_stub(tmp_path):
    manifest, routes, descriptor = compressed_scenario(tmp_path)
    item = manifest["files"][0]
    assert check_consolidation(tmp_path) == []
    assert PreservedRecords(tmp_path).read(item["archive_path"]) == b"historical bytes\r\n"
    assert not (tmp_path / item["archive_path"]).exists()
    result = resolve(item["original_path"], routes, tmp_path)
    assert result["role"] == "RETIRED_LOCATOR"
    assert result["canonical_path"] == PUBLIC_RECORDS
    assert result["archive_member"] == item["archive_path"]
    assert result["archive_path"] == descriptor["archive"]["path"]
    assert resolve(item["archive_path"], routes, tmp_path)["role"] == "ARCHIVED_PUBLIC_RECORD"


@pytest.mark.parametrize("damage", ["zip", "metadata", "member_hash", "missing_zip", "duplicate_record"])
def test_record_archive_damage_never_becomes_a_missing_path_exception(tmp_path, damage):
    _, _, descriptor = compressed_scenario(tmp_path)
    archive = tmp_path / descriptor["archive"]["path"]
    if damage == "zip":
        archive.write_bytes(archive.read_bytes() + b"changed")
    elif damage == "metadata":
        descriptor["archive"]["bytes"] = True
    elif damage == "member_hash":
        descriptor["files"][0]["sha256"] = "0" * 64
    elif damage == "missing_zip":
        archive.unlink()
    else:
        descriptor["files"].append(descriptor["files"][0].copy())
    write(tmp_path, PUBLIC_RECORDS, json.dumps(descriptor))
    assert check_consolidation(tmp_path), "corrupt archive was accepted"


@pytest.mark.parametrize("extra", ["unlisted.md", "../escape.md"])
def test_unlisted_or_traversing_zip_members_are_rejected_without_extraction(tmp_path, extra):
    import zipfile

    _, _, descriptor = compressed_scenario(tmp_path)
    archive = tmp_path / descriptor["archive"]["path"]
    with zipfile.ZipFile(archive, "a") as output:
        output.writestr(extra, "unexpected")
    raw = archive.read_bytes()
    descriptor["archive"].update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    write(tmp_path, PUBLIC_RECORDS, json.dumps(descriptor))
    assert any("membership mismatch" in issue for issue in check_consolidation(tmp_path))
    assert not (tmp_path / "escape.md").exists()


def test_archive_cannot_mask_changed_physical_original(tmp_path):
    manifest, _, _ = compressed_scenario(tmp_path)
    item = manifest["files"][0]
    (tmp_path / item["archive_path"]).write_bytes(b"changed")
    assert any("identity mismatch" in issue for issue in check_consolidation(tmp_path))


def test_compression_does_not_replace_original_manifest_hash_requirement(tmp_path):
    manifest, _, descriptor = compressed_scenario(tmp_path)
    # Even consistent new ZIP/index bytes cannot rewrite the immutable contract.
    import zipfile

    row = descriptor["files"][0]
    archive = tmp_path / descriptor["archive"]["path"]
    payload = b"different record\r\n"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr(row["path"], payload)
    raw = archive.read_bytes()
    row.update(bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
    descriptor["archive"].update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    write(tmp_path, PUBLIC_RECORDS, json.dumps(descriptor))
    assert manifest["files"][0]["sha256"] != row["sha256"]
    assert any("consolidated archive identity mismatch" in issue
               for issue in check_consolidation(tmp_path))


def second_batch(root, members):
    import zipfile

    descriptor_name = PUBLIC_RECORD_BATCHES[1]
    archive_path = str(Path(descriptor_name).parent / "preoct-public-records.zip").replace("\\", "/")
    archive = root / archive_path
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
        for name, payload in members.items():
            output.writestr(name, payload)
    source_contracts = []
    for source, rows_key, path_key in RECORD_CONTRACTS:
        path = root / source
        if not path.is_file():
            name, payload = next(iter(members.items()))
            record = {path_key: name, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
            write(root, source, json.dumps({rows_key: [record] * (1 + max(RECORD_CONTRACT_ROWS[source]))}))
        else:
            # Build full synthetic frozen row slots before binding their original bytes.
            contract = json.loads(path.read_text(encoding="utf-8"))
            while len(contract[rows_key]) <= max(RECORD_CONTRACT_ROWS[source]):
                contract[rows_key].append(contract[rows_key][0].copy())
            write(root, source, json.dumps(contract))
        raw = path.read_bytes()
        source_contracts.append({"path": source, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    raw = archive.read_bytes()
    descriptor = {"schema": "aaos.preoct-public-records/v1",
                  "archive": {"path": archive_path, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()},
                  "source_contracts": source_contracts,
                  "files": [{"path": name, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
                            for name, payload in members.items()]}
    write(root, descriptor_name, json.dumps(descriptor))
    return descriptor


def test_two_registered_batches_keep_distinct_locations_and_earlier_bytes(tmp_path):
    first, routes, _ = compressed_scenario(tmp_path)
    before = (tmp_path / PUBLIC_RECORDS).read_bytes()
    name = "docs/history/donors/older-record.md"
    descriptor = second_batch(tmp_path, {name: b"second\r\n"})
    records = PreservedRecords(tmp_path)
    assert records.read(first["files"][0]["archive_path"]) == b"historical bytes\r\n"
    assert records.read(name) == b"second\r\n"
    result = resolve(name, routes, tmp_path)
    assert result["canonical_path"] == PUBLIC_RECORD_BATCHES[1]
    assert result["archive_path"] == descriptor["archive"]["path"]
    assert result["archive_member"] == name
    assert (tmp_path / PUBLIC_RECORDS).read_bytes() == before
    assert check_consolidation(tmp_path) == []


def test_duplicate_source_between_batches_is_rejected_even_when_identical(tmp_path):
    first, _, _ = compressed_scenario(tmp_path)
    second_batch(tmp_path, {first["files"][0]["archive_path"]: b"historical bytes\r\n"})
    assert any("duplicate preserved record" in issue for issue in check_consolidation(tmp_path))


@pytest.mark.parametrize("damage", ["zip", "owner", "missing_contract", "duplicate_contract", "contract_hash"])
def test_second_batch_damage_cannot_be_hidden_by_good_first_batch(tmp_path, damage):
    compressed_scenario(tmp_path)
    descriptor = second_batch(tmp_path, {"docs/history/older.md": b"second"})
    if damage == "zip":
        archive = tmp_path / descriptor["archive"]["path"]
        archive.write_bytes(archive.read_bytes() + b"changed")
    elif damage == "owner":
        descriptor["archive"]["path"] = str(Path(PUBLIC_RECORDS).parent / "preoct-public-records.zip").replace("\\", "/")
    elif damage == "missing_contract":
        descriptor["source_contracts"].pop()
    elif damage == "duplicate_contract":
        descriptor["source_contracts"].append(descriptor["source_contracts"][0].copy())
    else:
        descriptor["source_contracts"][0]["sha256"] = "0" * 64
    write(tmp_path, PUBLIC_RECORD_BATCHES[1], json.dumps(descriptor))
    assert check_consolidation(tmp_path)


@pytest.mark.parametrize("name", PUBLIC_RECORD_BATCHES)
def test_one_batch_cannot_archive_another_batch_metadata(tmp_path, name):
    compressed_scenario(tmp_path)
    second_batch(tmp_path, {name: b"do not substitute descriptors"})
    assert any("invalid public record source" in issue for issue in check_consolidation(tmp_path))


@pytest.mark.parametrize("source,rows_key,path_key", RECORD_CONTRACTS)
@pytest.mark.parametrize("damage", ["consistent_new_zip", "changed_physical", "directory_physical"])
def test_second_batch_retains_each_original_consumer_hash(tmp_path, source, rows_key, path_key, damage):
    import zipfile

    compressed_scenario(tmp_path)
    name, payload = "docs/history/donor/record.md", b"original donor\r\n"
    write(tmp_path, source, json.dumps({rows_key: [{path_key: name, "bytes": len(payload),
                                                 "sha256": hashlib.sha256(payload).hexdigest()}]}))
    descriptor = second_batch(tmp_path, {name: payload})
    assert check_consolidation(tmp_path) == []
    if damage == "consistent_new_zip":
        payload = b"changed donor bytes"
        archive = tmp_path / descriptor["archive"]["path"]
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr(name, payload)
        raw = archive.read_bytes()
        descriptor["archive"].update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        descriptor["files"][0].update(bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
        write(tmp_path, PUBLIC_RECORD_BATCHES[1], json.dumps(descriptor))
    else:
        original = tmp_path / name
        original.parent.mkdir(parents=True, exist_ok=True)
        if damage == "directory_physical":
            original.mkdir()
        else:
            original.write_bytes(b"changed donor bytes")
    assert check_consolidation(tmp_path), "new batch cannot supersede original consumer identity"


def test_deleted_member_cannot_disappear_from_old_consumer_check_scope(tmp_path):
    import zipfile

    compressed_scenario(tmp_path)
    descriptor = second_batch(tmp_path, {"docs/history/donor/record.md": b"original donor"})
    archive = tmp_path / descriptor["archive"]["path"]
    with zipfile.ZipFile(archive, "w"):
        pass
    raw = archive.read_bytes()
    descriptor["archive"].update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    descriptor["files"] = []
    write(tmp_path, PUBLIC_RECORD_BATCHES[1], json.dumps(descriptor))
    assert any("missing preserved public record" in issue for issue in check_consolidation(tmp_path))


@pytest.mark.parametrize("mutation", ["archive", "size", "hash", "replacement", "original", "baseline", "duplicate"])
def test_identity_or_migration_damage_is_detected(tmp_path, mutation):
    manifest, _ = scenario(tmp_path)
    item = manifest["files"][0]
    expected = {
        "archive": "identity mismatch", "size": "identity mismatch",
        "hash": "identity mismatch", "replacement": "missing consolidation replacement",
        "original": "retired original still exists", "baseline": "invalid baseline_commit",
        "duplicate": "duplicate consolidation identity",
    }[mutation]
    if mutation == "archive":
        (tmp_path / item["archive_path"]).write_bytes(b"changed\n")
    elif mutation == "size":
        item["bytes"] += 1
    elif mutation == "hash":
        item["sha256"] = "0" * 64
    elif mutation == "replacement":
        (tmp_path / item["replacement"]).unlink()
    elif mutation == "original":
        write(tmp_path, item["original_path"], "stub\n")
    elif mutation == "baseline":
        item["baseline_commit"] = "unknown"
    elif mutation == "duplicate":
        manifest["files"].append(item.copy())
    save(tmp_path, manifest)
    assert any(expected in issue for issue in check_consolidation(tmp_path))


def test_unlisted_nested_public_residual_is_detected(tmp_path):
    scenario(tmp_path)
    write(tmp_path, "old-plans/subdir/unlisted.md", "residual\n")
    assert any("public residual: old-plans/subdir/unlisted.md" in issue
               for issue in check_consolidation(tmp_path))


def test_private_residual_is_not_read_or_descended(tmp_path, monkeypatch):
    scenario(tmp_path)
    private = tmp_path / "old-plans/.hilo"
    private.mkdir(parents=True)
    original = Path.iterdir

    def guarded(path):
        assert path != private, "private state must not be traversed"
        return original(path)

    monkeypatch.setattr(Path, "iterdir", guarded)
    assert check_consolidation(tmp_path) == []


def test_linked_residual_fails_without_traversal(tmp_path, monkeypatch):
    scenario(tmp_path)
    write(tmp_path, "old-plans/linked-target/never-read.md", "sentinel\n")
    original_iterdir = Path.iterdir
    original_lstat = Path.lstat
    linked = tmp_path / "old-plans/linked-target"

    def guarded_iterdir(path):
        assert path != linked, "linked directory must not be traversed"
        return original_iterdir(path)

    class Reparse:
        st_mode = 0
        st_file_attributes = 0x400

    def reparse_lstat(path):
        return Reparse() if path == linked else original_lstat(path)

    monkeypatch.setattr(Path, "iterdir", guarded_iterdir)
    monkeypatch.setattr(Path, "lstat", reparse_lstat)
    assert any("uninspectable retired directory child" in issue
               for issue in check_consolidation(tmp_path))


def test_relative_encoded_live_link_to_retired_file_fails(tmp_path):
    scenario(tmp_path)
    write(tmp_path, "docs/guide.md", "[old](../old-plans/./%E6%97%A7%20plan.md#section)\n")
    assert any("live link targets retired original" in issue for issue in check_consolidation(tmp_path))


def test_frozen_archive_old_literal_and_link_do_not_become_live_checks(tmp_path):
    manifest, _ = scenario(tmp_path)
    item = manifest["files"][0]
    raw = b"old-plans/old.md [old](../../old-plans/old.md)\r\n"
    (tmp_path / item["archive_path"]).write_bytes(raw)
    item.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    save(tmp_path, manifest)
    assert check_consolidation(tmp_path) == []


@pytest.mark.parametrize("unsafe", ["../escape.md", ".hilo/storage.json", ".project-local/private.md"])
def test_manifest_cannot_request_private_or_outside_read(tmp_path, unsafe):
    manifest, _ = scenario(tmp_path)
    manifest["files"][0]["archive_path"] = unsafe
    save(tmp_path, manifest)
    assert check_consolidation(tmp_path)


def test_missing_manifest_is_a_failure(tmp_path):
    assert check_consolidation(tmp_path)
