"""Release SBOM must fail closed when a canonical supply-chain root is missing."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import release_sbom


def _write_minimal_sources(root: Path) -> None:
    (root / "frontend").mkdir(parents=True)
    (root / "src-tauri").mkdir(parents=True)
    (root / "shared/models/magika").mkdir(parents=True)
    (root / "uv.lock").write_text(
        '[[package]]\nname = "alpha"\nversion = "1.0.0"\n', encoding="utf-8"
    )
    (root / "frontend/package-lock.json").write_text(
        json.dumps(
            {
                "packages": {
                    "": {},
                    "node_modules/react": {
                        "version": "18.3.1",
                        "license": "MIT",
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    (root / "Cargo.lock").write_text(
        '[[package]]\nname = "archeaxis-core-fixture"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    (root / "src-tauri/Cargo.lock").write_text(
        '[[package]]\nname = "tauri"\nversion = "2.8.4"\n', encoding="utf-8"
    )

    (root / "shared/models/magika/model.onnx").write_bytes(b"onnx")
    (root / "shared/models/magika/LICENSE").write_text("Apache-2.0", encoding="utf-8")


def test_collect_components_covers_canonical_roots_and_vendored_assets(tmp_path: Path):
    _write_minimal_sources(tmp_path)

    components = release_sbom.collect_components(tmp_path)
    purls = {component["purl"] for component in components}

    assert "pkg:pypi/alpha@1.0.0" in purls
    assert "pkg:npm/react@18.3.1" in purls
    assert "pkg:cargo/tauri@2.8.4" in purls
    assert "pkg:cargo/archeaxis-core-fixture@0.1.0" in purls
    assert "pkg:generic/pdfjs@6.2.108" not in purls
    assert "pkg:generic/magika-model@0.6.3" in purls
    for component in components:
        if component["type"] in {"vendored-javascript", "model"}:
            assert component["hashes"][0]["alg"] == "SHA-256"
            assert len(component["hashes"][0]["content"]) == 64


def test_collect_components_fails_when_frontend_lock_is_missing(tmp_path: Path):
    _write_minimal_sources(tmp_path)
    (tmp_path / "frontend/package-lock.json").unlink()

    with pytest.raises(release_sbom.MissingCoverageError, match="frontend/package-lock.json"):
        release_sbom.collect_components(tmp_path)


def test_collect_components_requires_canonical_core_lock(tmp_path: Path):
    _write_minimal_sources(tmp_path)
    (tmp_path / "Cargo.lock").unlink()
    with pytest.raises(release_sbom.MissingCoverageError, match="Cargo.lock"):
        release_sbom.collect_components(tmp_path)


def test_multiple_rust_roots_preserve_version_and_lock_provenance(tmp_path: Path):
    _write_minimal_sources(tmp_path)
    (tmp_path / "Cargo.lock").write_text('[[package]]\nname = "shared"\nversion = "1.0.0"\n', encoding="utf-8")
    (tmp_path / "src-tauri/Cargo.lock").write_text('[[package]]\nname = "shared"\nversion = "1.0.0"\n', encoding="utf-8")
    (tmp_path / "desktop/src-tauri").mkdir(parents=True)
    (tmp_path / "desktop/src-tauri/Cargo.lock").write_text('[[package]]\nname = "shared"\nversion = "2.0.0"\n', encoding="utf-8")
    components = release_sbom.collect_components(tmp_path)
    matching = [x for x in components if x['name'] == 'shared']
    assert len(matching) == 2
    versions = {x['version']: x for x in matching}
    assert set(versions) == {'1.0.0', '2.0.0'}
    assert {p['value'] for p in versions['1.0.0']['properties'] if p['name'] == 'archeaxis:lock-source'} == {'Cargo.lock', 'src-tauri/Cargo.lock'}
    assert {p['value'] for p in versions['2.0.0']['properties'] if p['name'] == 'archeaxis:lock-source'} == {'desktop/src-tauri/Cargo.lock'}
