"""R6 A01 release freeze contract tests."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_release_workflow_is_tag_only_and_exact_sha_gated() -> None:
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    assert re.search(r"on:\s*\n\s*push:\s*\n\s*tags:\s*\[\"v\*\"\]", workflow)
    assert "if: ${{ false }} # R6 release freeze" in workflow
    assert "Require tag target to equal main" in workflow
    assert "Require successful exact-SHA CI" in workflow
    assert "Download and verify exact-SHA Avalonia Green candidate" in workflow


def test_development_manifest_is_not_a_public_release() -> None:
    manifest = json.loads((ROOT / "app/release-manifest.json").read_text(encoding="utf-8"))
    assert manifest["release"] == {
        "status": "unreleased",
        "channel": "development",
        "public": False,
    }


def test_r6_freeze_document_names_owner_gate_and_no_release() -> None:
    document = (ROOT / "docs/current/R6-VERSION-RELEASE-FREEZE.md").read_text(encoding="utf-8")
    assert "Local Green Development Line" in document
    assert "Release re-opening requires a later explicit Owner decision" in document
    assert "No R6 task may create a tag" in document
