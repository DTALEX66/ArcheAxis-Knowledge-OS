"""Tests for shared.public_evidence (H2 public-source enrichment bridge).

Verifies routing logic (doi/qid/claim_text dispatch), hit construction,
and honest error suppression — without hitting live APIs.
"""

from __future__ import annotations

from shared.evidence_connectors import EvidenceConnectorError
from shared.public_evidence import PublicEvidenceHit, query_public_sources


class _FakeCrossref:
    def lookup_doi(self, doi: str) -> dict:
        return {
            "message": {
                "title": ["Fake Paper"],
                "issued": {"date-parts": [[2024]]},
                "author": [{"family": "Doe", "given": "Jane"}],
            }
        }


class _FakeCrossrefEmpty:
    def lookup_doi(self, doi: str) -> dict:
        return {"message": {}}


class _FakeCrossrefError:
    def lookup_doi(self, doi: str) -> dict:
        raise EvidenceConnectorError("network down")


class _FakeDataCite:
    def lookup_doi(self, doi: str) -> dict:
        return {"data": {"attributes": {"titles": [{"title": "DC Paper"}]}}}


class _FakeOpenAlex:
    def search(self, text: str, per_page: int = 3) -> dict:
        return {
            "results": [
                {
                    "id": "W123",
                    "title": "OpenAlex Paper",
                    "publication_year": 2023,
                    "authorships": [{"author": {"display_name": "A. Researcher"}}],
                }
            ]
        }


class _FakeWikidata:
    def get_entity(self, qid: str) -> dict:
        return {
            "entities": {
                qid: {"labels": {"en": {"value": "Fake Entity"}}}
            }
        }


def test_doi_dispatch_queries_crossref(monkeypatch) -> None:
    monkeypatch.setattr("shared.public_evidence.CrossrefClient", _FakeCrossref)
    monkeypatch.setattr("shared.public_evidence.DataCiteClient", _FakeCrossrefError)
    hits = query_public_sources(doi="10.1000/xyz")
    assert len(hits) == 1
    assert hits[0].source == "crossref"
    assert hits[0].title == "Fake Paper"
    assert hits[0].year == 2024
    assert hits[0].authors == ["Jane Doe"]
    assert hits[0].doi == "10.1000/xyz"


def test_datacite_hit_collected(monkeypatch) -> None:
    monkeypatch.setattr("shared.public_evidence.CrossrefClient", _FakeCrossrefError)
    monkeypatch.setattr("shared.public_evidence.DataCiteClient", _FakeDataCite)
    hits = query_public_sources(doi="10.1000/abc")
    assert len(hits) == 1
    assert hits[0].source == "datacite"
    assert hits[0].title == "DC Paper"


def test_empty_message_no_crash(monkeypatch) -> None:
    monkeypatch.setattr("shared.public_evidence.CrossrefClient", _FakeCrossrefEmpty)
    monkeypatch.setattr("shared.public_evidence.DataCiteClient", _FakeCrossrefError)
    # An empty message must not raise; it yields at most one hit with None fields.
    hits = query_public_sources(doi="10.1000/empty")
    assert len(hits) <= 1
    if hits:
        assert hits[0].title is None


def test_openalex_dispatch_on_claim_text(monkeypatch) -> None:
    monkeypatch.setattr("shared.public_evidence.OpenAlexClient", _FakeOpenAlex)
    hits = query_public_sources(claim_text="machine learning")
    assert len(hits) == 1
    assert hits[0].source == "openalex"
    assert hits[0].title == "OpenAlex Paper"
    assert hits[0].year == 2023
    assert hits[0].authors == ["A. Researcher"]


def test_wikidata_dispatch_on_qid(monkeypatch) -> None:
    monkeypatch.setattr("shared.public_evidence.WikidataClient", _FakeWikidata)
    hits = query_public_sources(qid="Q42")
    assert len(hits) == 1
    assert hits[0].source == "wikidata"
    assert hits[0].id == "Q42"


def test_all_connectors_fail_returns_empty(monkeypatch) -> None:
    monkeypatch.setattr("shared.public_evidence.CrossrefClient", _FakeCrossrefError)
    monkeypatch.setattr("shared.public_evidence.DataCiteClient", _FakeCrossrefError)
    hits = query_public_sources(doi="10.1000/fail")
    assert hits == []


def test_hit_to_dict_roundtrip() -> None:
    hit = PublicEvidenceHit(
        source="crossref", id="W1", title="T", year=2022,
        authors=["A"], doi="10.1/x", url="https://example.com",
    )
    d = hit.to_dict()
    assert d["source"] == "crossref"
    assert d["title"] == "T"
    assert d["authors"] == ["A"]
