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
    for name in ["markitdown", "pytesseract", "trafilatura", "pdf.js"]:
        key = next((k for k in data if name in k), None)
        assert key is not None, f"{name} missing from ledger"
        assert data[key] in {"CURRENT", "ADOPT"}, (
            f"{name} expected CURRENT/ADOPT, got {data[key]}"
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
