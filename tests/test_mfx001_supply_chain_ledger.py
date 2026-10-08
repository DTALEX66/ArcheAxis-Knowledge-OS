"""MFX-001 regression tests: supply chain ledger integrity (v2 schema).

Verifies the structured supply chain ledger is valid JSON, every component
has an allowed disposition, and components marked ``REVIEW-BLOCK`` are not
claimed as default capabilities anywhere in the ingestion path.
"""

import json
import pathlib

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_LEDGER = _ROOT / "docs" / "truth" / "SUPPLY_CHAIN_LEDGER.json"
_ALLOWED_DISPOSITIONS: set[str] = {
    "CURRENT", "ADOPT_PRODUCT_BASE", "ADOPT", "EVALUATE", "SIDECAR",
    "REFERENCE", "DEFER", "REVIEW-BLOCK", "REJECT-CORE",
}


def _ledger() -> dict:
    return json.loads(_LEDGER.read_text(encoding="utf-8"))


def test_ledger_exists_and_is_valid_json() -> None:
    assert _LEDGER.is_file(), f"missing {_LEDGER}"
    data = _ledger()
    assert data["schema_version"] == 2
    assert len(data["components"]) > 0


def test_all_dispositions_are_allowed() -> None:
    data = _ledger()
    for comp in data["components"]:
        assert comp["disposition"] in _ALLOWED_DISPOSITIONS, (
            f"{comp['name']} has invalid disposition {comp['disposition']!r}"
        )
        assert comp.get("code_license"), f"{comp['name']} missing code_license"


def test_known_blocked_components_present_and_blocked() -> None:
    """Licence-gated components must be present and marked REVIEW-BLOCK."""
    data = {c["name"].lower(): c["disposition"] for c in _ledger()["components"]}
    for name in ["mineru", "pymupdf", "marker", "funasr", "searxng"]:
        key = next((k for k in data if name in k), None)
        assert key is not None, f"{name} missing from supply chain ledger"
        assert data[key] == "REVIEW-BLOCK", f"{name} must be REVIEW-BLOCK, got {data[key]}"


def test_approved_default_engines_present() -> None:
    """The default engine set must be present with CURRENT or ADOPT disposition."""
    data = {c["name"].lower(): c["disposition"] for c in _ledger()["components"]}
    for name in ["markitdown", "pytesseract", "trafilatura"]:
        key = next((k for k in data if name in k), None)
        assert key is not None, f"{name} missing from ledger"
        assert data[key] in {"CURRENT", "ADOPT"}, (
            f"{name} expected CURRENT/ADOPT, got {data[key]}"
        )
    # PDF.js left the REFERENCE bucket on 2026-10-08, and the bucket was the stale part of the
    # record, not the honest part: `frontend/package.json` declares `pdfjs-dist` 6.4.299 and
    # `frontend/src/components/PdfReader.tsx` imports it, while `frontend/` + `src-tauri/` are the
    # formal host under SUP-022. "Not a dependency" was no longer a true sentence about it, so the
    # ledger now says CURRENT. What actually has to stay guarded is narrower than the old bucket, so
    # it is pinned directly rather than smuggled through a disposition string.
    pdfjs = next(c for c in _ledger()["components"] if "pdf.js" in c["name"].lower())
    assert set(pdfjs["qualification"]) <= {"source"}, (
        f"PDF.js may only claim source presence, got {pdfjs['qualification']}"
    )


def test_blocked_components_not_in_default_engine_chain() -> None:
    """Blocked components must not appear in the default ingestion engine map."""
    from app.ingestion import multi_format

    blocked = {
        c["name"].lower()
        for c in _ledger()["components"]
        if c["disposition"] == "REVIEW-BLOCK"
    }
    assert blocked, "expected at least one REVIEW-BLOCK component in ledger"
    chain_text = json.dumps(multi_format._ENGINES, default=str).lower()
    for name in blocked:
        assert name not in chain_text, (
            f"blocked component {name} leaked into default engine chain"
        )
    # guard: the ledger must still flag the historical blockers
    # (zotero was never REVIEW-BLOCK — it is not in this disposition)
    for name in {"mineru", "funasr / sensevoice", "searxng", "marker"}:
        assert name in blocked, f"{name} expected REVIEW-BLOCK in ledger"


def test_disposition_labels_stay_definitions_and_summary_covers_them() -> None:
    """The label map defines each disposition; the summary counts every one of them.

    A script that overwrote `disposition_labels` with counts passed this file unchanged, so the
    ledger's own test was blind to the damage it had to repair. Both shapes are pinned here: a
    definition is a non-empty string, and a summary key set is exactly the label vocabulary.
    """
    ledger = _ledger()
    labels = ledger["disposition_labels"]
    assert isinstance(labels, dict) and labels, "disposition_labels must be a non-empty mapping"
    for label, definition in labels.items():
        assert isinstance(definition, str) and definition.strip(), (
            f"{label}: a disposition label must carry a definition, not a count"
        )

    summary = ledger["disposition_summary"]
    assert set(summary) == set(labels), (
        f"disposition_summary and the label vocabulary disagree: "
        f"{sorted(set(summary) ^ set(labels))}"
    )
    counts: dict[str, int] = {}
    for component in ledger["components"]:
        counts[component["disposition"]] = counts.get(component["disposition"], 0) + 1
    assert summary == {label: counts.get(label, 0) for label in labels}, (
        "disposition_summary must be the count of the rows that exist, zero included"
    )
