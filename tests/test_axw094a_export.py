"""AXW-094A: open-exchange manifest/export tests.

Verifies:
- mixed-kind export writes files + manifest with hashes and loss notes;
- verification passes on an intact export and re-hashes every file;
- corruption, missing files, partial exports and schema drift fail with
  explicit messages;
- empty exports are refused;
- the live-store bridge collects raw/evidence/learning artifacts.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.exchange.export import (
    ExportError,
    export_knowledge_exchange,
    extract_exchange_items,
    import_knowledge_exchange,
    verify_export,
)


def _mixed_payload() -> dict[str, object]:
    return {
        "raw_assets": {"sha256:aaa": b"raw bytes"},
        "evidence": {
            "ev_1": {"raw_sha256": "sha256:aaa", "locator": {"page": 1}},
        },
        "relations": [{"claim_id": "cl_1", "evidence_id": "ev_1", "kind": "supports"}],
        "learning": {"deck/note.md": b"# note"},
        "ai_assets": {"kmu_1": {"source": "derived", "status": "candidate"}},
    }


def test_export_roundtrip_verifies(tmp_path: Path) -> None:
    dest = tmp_path / "exchange"
    manifest = export_knowledge_exchange(destination=dest, **_mixed_payload())

    assert manifest["schema_version"] == "v1"
    # raw(1) + evidence(1) + relations(1, kind=evidence) + learning(1) + ai_asset(1)
    assert manifest["item_count"] == 5
    kinds = {item["kind"] for item in manifest["items"]}
    assert kinds == {"raw", "evidence", "learning", "ai_asset"}

    result = verify_export(dest)
    assert result["verified_items"] == 5
    # Every file on disk re-hashes to the manifest's digest (verify_export
    # already proved this; double-check the raw item path mapping).
    raw_item = next(i for i in manifest["items"] if i["kind"] == "raw")
    assert raw_item["path"] == "raw/sha256:aaa"
    assert (dest / raw_item["path"]).read_bytes() == b"raw bytes"


def test_verify_detects_corruption(tmp_path: Path) -> None:
    dest = tmp_path / "exchange"
    export_knowledge_exchange(destination=dest, **_mixed_payload())

    corrupted = dest / "learning" / "deck" / "note.md"
    corrupted.write_bytes(b"tampered")
    with pytest.raises(ExportError, match="hash mismatch"):
        verify_export(dest)


def test_verify_detects_missing_file(tmp_path: Path) -> None:
    dest = tmp_path / "exchange"
    export_knowledge_exchange(destination=dest, **_mixed_payload())

    (dest / "evidence" / "ev_1.json").unlink()
    with pytest.raises(ExportError, match="missing file"):
        verify_export(dest)


def test_verify_detects_manifest_tamper(tmp_path: Path) -> None:
    dest = tmp_path / "exchange"
    export_knowledge_exchange(destination=dest, **_mixed_payload())

    # Modify a payload file AND the manifest body so the manifest self-hash
    # no longer matches its own recomputation.
    (dest / "ai_asset" / "kmu_1.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ExportError, match="hash mismatch"):
        verify_export(dest)


def test_verify_detects_partial_export(tmp_path: Path) -> None:
    dest = tmp_path / "exchange"
    dest.mkdir()
    (dest / "raw").mkdir()
    (dest / "raw" / "sha256:aaa").write_bytes(b"raw bytes")  # files but no manifest
    with pytest.raises(ExportError, match="manifest.json missing"):
        verify_export(dest)


def test_verify_rejects_schema_drift(tmp_path: Path) -> None:
    dest = tmp_path / "exchange"
    export_knowledge_exchange(destination=dest, **_mixed_payload())

    manifest_path = dest / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schema_version"] = "v2"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ExportError, match="unsupported schema version"):
        verify_export(dest)


def test_empty_export_refused(tmp_path: Path) -> None:
    with pytest.raises(ExportError, match="nothing to export"):
        export_knowledge_exchange(destination=tmp_path / "empty")


def test_nonempty_destination_refused_without_overwrite(tmp_path: Path) -> None:
    dest = tmp_path / "occupied"
    dest.mkdir()
    (dest / "stale.txt").write_text("x", encoding="utf-8")
    with pytest.raises(ExportError, match="not empty"):
        export_knowledge_exchange(destination=dest, raw_assets={"a": b"b"})


def test_store_bridge_collects_artifacts(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    (raw_root / "originals").mkdir(parents=True)
    # Windows forbids ":" in file names; real store digests are hex, so use
    # a plain hex name here.
    (raw_root / "originals" / "abc123").write_bytes(b"original")

    learning_root = tmp_path / "learning"
    (learning_root / "deck").mkdir(parents=True)
    (learning_root / "deck" / "note.md").write_text("# note", encoding="utf-8")

    ai_asset_root = tmp_path / "ai-assets"
    ai_asset_root.mkdir()
    (ai_asset_root / "rule.json").write_text(
        '{"asset":{"unit_id":"rule"},"evidence_binding":{"source_record_ids":["s1"]}}',
        encoding="utf-8",
    )

    payload = extract_exchange_items(
        raw_root=raw_root,
        learning_root=learning_root,
        ai_asset_root=ai_asset_root,
    )
    assert payload["raw_assets"] == {"abc123": b"original"}
    assert payload["learning"] == {"deck/note.md": b"# note"}
    assert payload["ai_assets"]["rule"]["asset"]["unit_id"] == "rule"

    dest = tmp_path / "exchange"
    manifest = export_knowledge_exchange(destination=dest, **payload)
    assert manifest["item_count"] == 3
    verify_export(dest)


def test_store_bridge_collects_current_raw_asset_store_layout(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw-assets"
    raw_root.mkdir()
    digest = "a" * 64
    (raw_root / digest).write_bytes(b"original")
    (raw_root / "_metadata").mkdir()

    payload = extract_exchange_items(raw_root=raw_root)

    assert payload["raw_assets"] == {digest: b"original"}


def test_verified_exchange_imports_into_fresh_four_library_workspace(tmp_path: Path) -> None:
    source = tmp_path / "exchange"
    raw_digest = "b" * 64
    export_knowledge_exchange(
        destination=source,
        raw_assets={raw_digest: b"original"},
        evidence={"ev_1": {"raw_sha256": raw_digest, "locator": {"page": 1}}},
        learning={"Learning/note.md": b"# Imported learning\n"},
        ai_assets={"rule": {"asset": {"unit_id": "rule"}}},
    )

    result = import_knowledge_exchange(
        source=source,
        workspace_parent=tmp_path / "isolated",
        workspace_name="imported",
    )

    from shared.workspace_manifest import load

    workspace_root = tmp_path / "isolated" / "imported"
    manifest = load(result["workspace_manifest"])
    assert result["status"] == "imported_untrusted"
    assert result["imported_items"] == 4
    assert (Path(manifest.domains["source_archive"].path) / "raw-assets" / raw_digest).read_bytes() == b"original"
    assert (Path(manifest.domains["human_learning_vault"].path) / "Learning" / "note.md").read_bytes() == b"# Imported learning\n"
    assert (Path(manifest.domains["ai_asset_vault"].path) / "rule.json").is_file()
    receipt = json.loads(Path(result["receipt_path"]).read_text(encoding="utf-8"))
    assert receipt["status"] == "imported_untrusted"
    assert all(item["sha256"] for item in receipt["imported_items"])
    assert Path(result["receipt_path"]).is_relative_to(workspace_root)


def test_exchange_import_requires_fresh_workspace_destination(tmp_path: Path) -> None:
    source = tmp_path / "exchange"
    export_knowledge_exchange(destination=source, raw_assets={"c" * 64: b"original"})
    parent = tmp_path / "isolated"
    import_knowledge_exchange(source=source, workspace_parent=parent, workspace_name="imported")

    with pytest.raises(ExportError, match="fresh workspace"):
        import_knowledge_exchange(source=source, workspace_parent=parent, workspace_name="imported")


def test_exchange_import_rejects_unsafe_manifest_before_creating_workspace(tmp_path: Path) -> None:
    source = tmp_path / "exchange"
    export_knowledge_exchange(destination=source, raw_assets={"d" * 64: b"original"})
    manifest_path = source / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["items"][0]["path"] = "../outside"
    body = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    manifest["manifest_sha256"] = hashlib.sha256(
        json.dumps(body, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    parent = tmp_path / "isolated"
    with pytest.raises(ExportError, match="unsafe exchange relative path"):
        import_knowledge_exchange(source=source, workspace_parent=parent, workspace_name="blocked")
    assert not (parent / "blocked").exists()
