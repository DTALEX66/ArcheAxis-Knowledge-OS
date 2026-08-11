"""Tests for shared.evidence_connectors (ADS-004/005/006/007).

These tests validate connector structure and error handling.
Live API calls are skipped in CI (no network) and run locally when available.
"""

import pytest

from shared.evidence_connectors import (
    CrossrefClient,
    DataCiteClient,
    EvidenceConnectorError,
    OpenAlexClient,
    WikidataClient,
)

_NEEDS_NETWORK = pytest.mark.skipif("not config.getoption('--run-network', default=False)")


class TestCrossrefClient:
    def test_constructs(self) -> None:
        c = CrossrefClient()
        assert c is not None

    def test_invalid_doi_raises_error(self) -> None:
        c = CrossrefClient()
        with pytest.raises(EvidenceConnectorError):
            c.lookup_doi("not-a-real-doi-9999999999")

    @_NEEDS_NETWORK
    def test_real_doi(self) -> None:
        c = CrossrefClient()
        result = c.lookup_doi("10.1038/nature12373")
        assert "message" in result


class TestDataCiteClient:
    def test_constructs(self) -> None:
        c = DataCiteClient()
        assert c is not None


class TestOpenAlexClient:
    def test_constructs(self) -> None:
        c = OpenAlexClient()
        assert c is not None

    def test_constructs_with_email(self) -> None:
        c = OpenAlexClient(email="test@example.com")
        assert c is not None


class TestWikidataClient:
    def test_constructs(self) -> None:
        c = WikidataClient()
        assert c is not None

    def test_rejects_invalid_qid(self) -> None:
        c = WikidataClient()
        with pytest.raises(EvidenceConnectorError, match="Invalid QID"):
            c.get_entity("not-a-qid")

    @_NEEDS_NETWORK
    def test_real_q42(self) -> None:
        c = WikidataClient()
        result = c.get_entity("Q42")
        assert "entities" in result
        assert "Q42" in result["entities"]
