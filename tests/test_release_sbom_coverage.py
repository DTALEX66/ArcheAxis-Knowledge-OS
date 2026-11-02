"""Release SBOM must fail closed when a canonical supply-chain root is missing."""
from __future__ import annotations

import json
import hashlib
import shutil
from pathlib import Path

import pytest

from scripts import release_sbom

REPO = Path(__file__).resolve().parents[1]


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
    # Copy only the repository's selected source trees into this owned fixture;
    # tests below change the copies, never the source originals.
    provider = root / "services/learning-providers"
    release_sbom._native_path(provider).mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        release_sbom._native_path(REPO / "services/learning-providers/openmaic/vendor"),
        release_sbom._native_path(provider / "openmaic/vendor"),
    )
    release_sbom._native_path(provider / "deeptutor").mkdir(parents=True)
    shutil.copy2(
        release_sbom._native_path(REPO / "services/learning-providers/deeptutor/LICENSE"),
        release_sbom._native_path(provider / "deeptutor/LICENSE"),
    )
    shutil.copytree(
        release_sbom._native_path(REPO / "services/learning-providers/deeptutor/upstream"),
        release_sbom._native_path(provider / "deeptutor/upstream"),
    )


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
    assert {
        "pkg:generic/deeptutor@1.7.1?scope=source-only",
        "pkg:npm/%40openmaic/generation@0.3.28?scope=source-only",
        "pkg:npm/%40openmaic/dsl@0.12.0?scope=source-only",
        "pkg:npm/%40openmaic/geometry@0.1.0?scope=source-only",
        "pkg:npm/jsonrepair@3.13.3?scope=source-only",
        "pkg:npm/nanoid@5.1.14?scope=source-only",
        "pkg:npm/partial-json@0.1.7?scope=source-only",
        "pkg:npm/postcss-value-parser@4.2.0?scope=source-only",
        "pkg:npm/es-module-lexer@2.0.0?scope=source-only",
        "pkg:npm/entities@6.0.1?scope=source-only",
        "pkg:npm/svg-pathdata@8.0.0?scope=source-only",
        "pkg:npm/tinycolor2@1.6.0?scope=source-only",
        "pkg:npm/parse5@8.0.1?scope=source-only",
        "pkg:npm/entities@8.0.0?scope=source-only",
        "pkg:npm/commander@8.3.0?scope=source-only",
        "pkg:npm/postcss@8.5.23?scope=source-only",
        "pkg:npm/nanoid@3.3.19?scope=source-only",
        "pkg:npm/picocolors@1.1.1?scope=source-only",
        "pkg:npm/source-map-js@1.2.1?scope=source-only",
    } <= purls
    for component in components:
        if component["type"] in {"vendored-javascript", "model"}:
            assert component["hashes"][0]["alg"] == "SHA-256"
            assert len(component["hashes"][0]["content"]) == 64


@pytest.mark.parametrize(("source", "license_path"), [
    ("services/learning-providers/deeptutor/upstream/answers.py",
     "services/learning-providers/deeptutor/LICENSE"),
    ("services/learning-providers/deeptutor/upstream/question_pipeline.en.yaml",
     "services/learning-providers/deeptutor/LICENSE"),
    ("services/learning-providers/deeptutor/upstream/question_pipeline.zh.yaml",
     "services/learning-providers/deeptutor/LICENSE"),
    ("services/learning-providers/deeptutor/upstream/question_language.py",
     "services/learning-providers/deeptutor/LICENSE"),
    ("services/learning-providers/deeptutor/upstream/teaching.py",
     "services/learning-providers/deeptutor/LICENSE"),
    ("services/learning-providers/deeptutor/upstream/learning_models.py",
     "services/learning-providers/deeptutor/LICENSE"),
    ("services/learning-providers/deeptutor/upstream/agentic_labels.py",
     "services/learning-providers/deeptutor/LICENSE"),
    ("services/learning-providers/openmaic/vendor/generation-0.3.28/scene-builder.ts",
     "services/learning-providers/openmaic/vendor/generation-0.3.28/LICENSE"),
    ("services/learning-providers/openmaic/vendor/dsl-0.12.0-actions/src/action.ts",
     "services/learning-providers/openmaic/vendor/dsl-0.12.0-actions/LICENSE"),
    ("services/learning-providers/openmaic/vendor/scene-content-0.3.28-original/generation/src/scene-generator.ts",
     "services/learning-providers/openmaic/vendor/scene-content-0.3.28-original/generation/LICENSE"),
    ("services/learning-providers/openmaic/vendor/scene-content-0.3.28-original/dsl/src/slides.ts",
     "services/learning-providers/openmaic/vendor/scene-content-0.3.28-original/dsl/LICENSE"),
    ("services/learning-providers/openmaic/vendor/scene-content-0.3.28-original/geometry/src/index.ts",
     "services/learning-providers/openmaic/vendor/scene-content-0.3.28-original/geometry/LICENSE"),
    ("services/learning-providers/openmaic/vendor/npm/jsonrepair-3.13.3/lib/esm/index.js",
     "services/learning-providers/openmaic/vendor/npm/jsonrepair-3.13.3/LICENSE.md"),
    ("services/learning-providers/openmaic/vendor/npm/nanoid-5.1.14/index.js",
     "services/learning-providers/openmaic/vendor/npm/nanoid-5.1.14/LICENSE"),
    ("services/learning-providers/openmaic/vendor/npm/partial-json-0.1.7/dist/index.js",
     "services/learning-providers/openmaic/vendor/npm/partial-json-0.1.7/LICENSE"),
    ("services/learning-providers/openmaic/vendor/npm/postcss-value-parser-4.2.0/lib/parse.js",
     "services/learning-providers/openmaic/vendor/npm/postcss-value-parser-4.2.0/LICENSE"),
    ("services/learning-providers/openmaic/vendor/npm/es-module-lexer-2.0.0/dist/lexer.asm.js",
     "services/learning-providers/openmaic/vendor/npm/es-module-lexer-2.0.0/LICENSE"),
    ("services/learning-providers/openmaic/vendor/npm/entities-6.0.1/dist/esm/index.js",
     "services/learning-providers/openmaic/vendor/npm/entities-6.0.1/LICENSE"),
    ("services/learning-providers/openmaic/vendor/npm/svg-pathdata-8.0.0/dist/index.js",
     "services/learning-providers/openmaic/vendor/npm/svg-pathdata-8.0.0/LICENSE"),
    ("services/learning-providers/openmaic/vendor/npm/tinycolor2-1.6.0/esm/tinycolor.js",
     "services/learning-providers/openmaic/vendor/npm/tinycolor2-1.6.0/LICENSE"),
    ("services/learning-providers/openmaic/vendor/npm/parse5-8.0.1/dist/index.js",
     "services/learning-providers/openmaic/vendor/npm/parse5-8.0.1/LICENSE"),
    ("services/learning-providers/openmaic/vendor/npm/entities-8.0.0/dist/index.js",
     "services/learning-providers/openmaic/vendor/npm/entities-8.0.0/LICENSE"),
    ("services/learning-providers/openmaic/vendor/npm/commander-8.3.0/index.js",
     "services/learning-providers/openmaic/vendor/npm/commander-8.3.0/LICENSE"),
    ("services/learning-providers/openmaic/vendor/npm/postcss-8.5.23/lib/postcss.js",
     "services/learning-providers/openmaic/vendor/npm/postcss-8.5.23/LICENSE"),
    ("services/learning-providers/openmaic/vendor/npm/nanoid-3.3.19/non-secure/index.js",
     "services/learning-providers/openmaic/vendor/npm/nanoid-3.3.19/LICENSE"),
    ("services/learning-providers/openmaic/vendor/npm/picocolors-1.1.1/picocolors.js",
     "services/learning-providers/openmaic/vendor/npm/picocolors-1.1.1/LICENSE"),
    ("services/learning-providers/openmaic/vendor/npm/source-map-js-1.2.1/lib/base64-vlq.js",
     "services/learning-providers/openmaic/vendor/npm/source-map-js-1.2.1/LICENSE"),
], ids=["deeptutor", "deeptutor-en", "deeptutor-zh", "deeptutor-language", "deeptutor-teaching", "deeptutor-learning-models", "deeptutor-agentic-labels", "generation", "dsl", "scene-generation", "scene-dsl", "scene-geometry", "jsonrepair", "nanoid", "partial-json", "postcss-value-parser", "es-module-lexer", "entities", "svg-pathdata", "tinycolor2", "parse5", "entities8", "commander", "postcss", "nanoid3", "picocolors", "source-map-js"])
def test_source_only_missing_and_modified_members_fail_closed(tmp_path: Path, source: str, license_path: str):
    _write_minimal_sources(tmp_path)
    for relative in (source, license_path):
        path = release_sbom._native_path(tmp_path / relative)
        original = path.read_bytes()
        path.unlink()
        with pytest.raises(release_sbom.MissingCoverageError):
            release_sbom.collect_components(tmp_path)
        path.write_bytes(original + b"tampered")
        with pytest.raises(release_sbom.MissingCoverageError):
            release_sbom.collect_components(tmp_path)
        path.write_bytes(original)
    release_sbom.collect_components(tmp_path)


def test_source_only_notices_report_scope_and_real_license_paths(tmp_path: Path):
    _write_minimal_sources(tmp_path)
    components = release_sbom.collect_components(tmp_path)
    source_only = [c for c in components if any(
        p["name"] == "archeaxis:scope" and p["value"] == "SOURCE_ONLY"
        for p in c.get("properties", [])
    )]
    assert {(c["name"], c["version"], c["license"]) for c in source_only} == {
        ("DeepTutor", "1.7.1", "Apache-2.0"), ("@openmaic/generation", "0.3.28", "MIT"),
        ("@openmaic/dsl", "0.12.0", "MIT"), ("@openmaic/geometry", "0.1.0", "MIT"),
        ("jsonrepair", "3.13.3", "ISC"),
        ("nanoid", "5.1.14", "MIT"), ("partial-json", "0.1.7", "MIT"),
        ("postcss-value-parser", "4.2.0", "MIT"),
        ("es-module-lexer", "2.0.0", "MIT"),
        ("entities", "6.0.1", "BSD-2-Clause"),
        ("svg-pathdata", "8.0.0", "MIT"),
        ("tinycolor2", "1.6.0", "MIT"),
        ("parse5", "8.0.1", "MIT"), ("entities", "8.0.0", "BSD-2-Clause"),
        ("commander", "8.3.0", "MIT"),
        ("postcss", "8.5.23", "MIT"), ("nanoid", "3.3.19", "MIT"),
        ("picocolors", "1.1.1", "ISC"), ("source-map-js", "1.2.1", "BSD-3-Clause"),
    }
    for component in source_only:
        assert {"name": "archeaxis:packaging", "value": "NOT_PROVEN"} in component["properties"]
        assert any(p["name"] == "archeaxis:selected-file-sha256" for p in component["properties"])
        assert any(p["name"] == "archeaxis:license-file" for p in component["properties"])
    notice = tmp_path / "notices.txt"
    release_sbom._write_notices(components, release_sbom._licenses_from_components(components), notice)
    text = notice.read_text(encoding="utf-8")
    assert text.count("[SOURCE_ONLY; packaging not proven]") == len(source_only)
    assert "jsonrepair-3.13.3/LICENSE.md" in text
    assert "deeptutor/upstream/THIRD_PARTY_NOTICES.md" in text
    assert "source-map-js-1.2.1/lib/base64-vlq.js" in text
    generation = next(c for c in source_only if c["name"] == "@openmaic/generation")
    review = next(p["value"] for p in generation["properties"] if p["name"] == "archeaxis:license-review")
    assert "learn-your-way/concept_to_html.py" in review and "not been verified" in review
    assert review in text


def test_source_manifest_cannot_read_outside_its_source_root(tmp_path: Path):
    manifest = json.dumps({"originals": {"../outside": "0" * 64}}).encode()
    (tmp_path / "manifest.json").write_bytes(manifest)
    spec = {
        "name": "synthetic", "version": "1", "license": "MIT", "purl": "synthetic",
        "type": "vendored-javascript", "files": {}, "license_files": [],
        "manifests": {"manifest.json": hashlib.sha256(manifest).hexdigest()},
    }
    with pytest.raises(release_sbom.MissingCoverageError, match="invalid source-only"):
        release_sbom._source_only_component(tmp_path, spec)


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
