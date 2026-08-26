"""Release SBOM must fail closed when a canonical supply-chain root is missing."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import release_sbom


def _write_minimal_sources(root: Path) -> None:
    (root / "frontend").mkdir(parents=True)
    (root / "src-tauri").mkdir(parents=True)
    (root / "app/workspace/ui/assets/licenses").mkdir(parents=True)
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
    (root / "src-tauri/Cargo.lock").write_text(
        '[[package]]\nname = "tauri"\nversion = "2.8.4"\n', encoding="utf-8"
    )
    (root / "app/workspace/ui/assets/pdf.mjs").write_text("// pdf", encoding="utf-8")
    (root / "app/workspace/ui/assets/pdf.worker.mjs").write_text("// worker", encoding="utf-8")
    (root / "app/workspace/ui/assets/licenses/pdfjs-6.2.108-LICENSE.txt").write_text(
        "Apache-2.0", encoding="utf-8"
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
    assert "pkg:generic/pdfjs@6.2.108" in purls
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
