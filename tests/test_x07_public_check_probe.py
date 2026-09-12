"""R06 regression: a public-check result must separate support from refutation,
irrelevant number matches, undecidable cases and fetch failures.

The X07 probe is a script, so it is loaded by path (no sys.path mutation, which
the architecture guard forbids). These tests are offline: the network fetch and
the local model call are exercised only through their failure/classification
behaviour.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

PROBE = Path(__file__).resolve().parents[1] / "scripts" / "probes" / "x07_public_check_probe.py"


def _load():
    spec = importlib.util.spec_from_file_location("x07_probe_under_test", PROBE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


probe = _load()


class TestEvidenceQuote:
    def test_radius_sentence_with_unit_is_support(self) -> None:
        extract = "Earth's mean radius is 6,371 km.\nIt orbits the Sun."
        supported, kind, quote = probe.evidence_quote(extract)
        assert supported is True
        assert kind == "radius"
        assert "6371" in quote.replace(",", "")

    def test_diameter_only_is_refutation_not_support(self) -> None:
        supported, kind, quote = probe.evidence_quote("Earth's diameter is 12,742 km.")
        assert supported is False, "a diameter match must never count as radius support"
        assert kind == "diameter_only"
        assert quote, "the weaker evidence is still quoted, but marked as weaker"

    def test_irrelevant_same_number_is_not_support(self) -> None:
        # The literal 6371 appears, but not as a radius with a unit.
        supported, kind, _quote = probe.evidence_quote("The year 6371 will be discussed later.")
        assert supported is False
        assert kind == "none", "an unrelated numeric hit must not become support"

    def test_number_without_object_is_not_support(self) -> None:
        supported, kind, _quote = probe.evidence_quote("The distance measured 6,371 km today.")
        assert supported is False
        assert kind == "none"

    def test_empty_extract_is_not_support(self) -> None:
        assert probe.evidence_quote("") == (False, "none", "")


class TestVerdictParsing:
    @pytest.mark.parametrize(
        ("text", "label"),
        [
            ("支持。来源与主张一致。", "supported"),
            ("不支持。来源给出的是直径。", "unsupported"),
            ("无法判断。来源未提及半径。", "undeterminable"),
            ("", "unparseable_or_error"),
            ("Error: model unavailable", "unparseable_or_error"),
            ("The source is consistent with the claim (no explicit verdict)", "unparseable_or_error"),
        ],
    )
    def test_only_an_explicit_support_verdict_counts(self, text: str, label: str) -> None:
        supported, got = probe.parse_verdict(text)
        assert got == label
        assert supported is (label == "supported")

    def test_model_refusal_can_never_become_support(self) -> None:
        for text in ("不支持", "不支持这个主张", "无法判断", "unclear", ""):
            supported, _label = probe.parse_verdict(text)
            assert supported is False


class TestFetchFailureIsDistinct:
    def test_unreachable_source_raises_instead_of_returning_empty_evidence(self) -> None:
        # Nothing is silently turned into "no evidence found": an unreachable
        # source must raise so the caller can classify it as a fetch failure
        # instead of an undecided or unsupported verdict.
        with pytest.raises(OSError):
            probe.fetch("http://127.0.0.1:9/definitely-not-listening")
