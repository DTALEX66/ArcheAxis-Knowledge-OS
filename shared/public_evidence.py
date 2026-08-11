"""Public evidence enrichment — bridges evidence connectors into the pipeline.

Wires ADS-004/005/006/007 (Crossref, DataCite, OpenAlex, Wikidata)
into the cross-validation pipeline as structured public-source queries.
"""

from __future__ import annotations

import logging
from typing import Any

from shared.evidence_connectors import (
    CrossrefClient,
    DataCiteClient,
    EvidenceConnectorError,
    OpenAlexClient,
    WikidataClient,
)

_log = logging.getLogger(__name__)

__all__ = ["query_public_sources", "PublicEvidenceHit"]


class PublicEvidenceHit:
    """A single result from a public evidence source."""

    __slots__ = ("source", "id", "title", "year", "authors", "doi", "url")

    def __init__(
        self,
        source: str,
        id: str | None = None,
        title: str | None = None,
        year: int | None = None,
        authors: list[str] | None = None,
        doi: str | None = None,
        url: str | None = None,
    ) -> None:
        self.source = source
        self.id = id
        self.title = title
        self.year = year
        self.authors = authors or []
        self.doi = doi
        self.url = url

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "id": self.id,
            "title": self.title,
            "year": self.year,
            "authors": self.authors,
            "doi": self.doi,
            "url": self.url,
        }


def query_public_sources(
    claim_text: str | None = None,
    doi: str | None = None,
    qid: str | None = None,
    *,
    timeout: int = 15,
) -> list[PublicEvidenceHit]:
    """Query public evidence sources for claim support.

    If doi is provided, queries Crossref + DataCite for that DOI.
    If qid is provided, queries Wikidata for that entity.
    If claim_text is provided, searches OpenAlex.

    Returns list of PublicEvidenceHit; empty list if no sources respond.
    Errors from individual connectors are logged and suppressed.
    """
    hits: list[PublicEvidenceHit] = []

    if doi:
        _query_doi(doi, hits)

    if qid:
        _query_wikidata(qid, hits)

    if claim_text and not doi:
        _query_openalex(claim_text, hits)

    return hits


def _query_doi(doi: str, hits: list[PublicEvidenceHit]) -> None:
    for name, client_factory in [
        ("crossref", CrossrefClient),
        ("datacite", DataCiteClient),
    ]:
        try:
            client = client_factory()
            result = client.lookup_doi(doi)
            msg = result.get("message", result)
            items = msg.get("items", [msg]) if isinstance(msg, dict) else [msg]
            for item in items:
                if isinstance(item, dict):
                    hits.append(
                        PublicEvidenceHit(
                            source=name,
                            doi=doi,
                            title=_first_str(item, "title"),
                            year=_extract_year(item),
                            authors=_extract_authors(item),
                        )
                    )
        except (EvidenceConnectorError, OSError) as e:
            _log.debug("evidence connector %s failed: %s", name, e)


def _query_wikidata(qid: str, hits: list[PublicEvidenceHit]) -> None:
    try:
        client = WikidataClient()
        result = client.get_entity(qid)
        entities = result.get("entities", {})
        for eid, entity in entities.items():
            labels = entity.get("labels", {})
            title = labels.get("en", {}).get("value") if labels else None
            hits.append(
                PublicEvidenceHit(
                    source="wikidata",
                    id=eid,
                    title=str(title) if title else None,
                    url=f"https://www.wikidata.org/wiki/{eid}",
                )
            )
    except (EvidenceConnectorError, OSError) as e:
        _log.debug("wikidata query failed: %s", e)


def _query_openalex(text: str, hits: list[PublicEvidenceHit]) -> None:
    try:
        client = OpenAlexClient()
        result = client.search(text, per_page=3)
        works = result.get("results", [])
        for w in works:
            if isinstance(w, dict):
                hits.append(
                    PublicEvidenceHit(
                        source="openalex",
                        id=w.get("id"),
                        title=w.get("title"),
                        year=w.get("publication_year"),
                        doi=w.get("doi"),
                        url=w.get("id"),
                        authors=_extract_openalex_authors(w),
                    )
                )
    except (EvidenceConnectorError, OSError) as e:
        _log.debug("openalex query failed: %s", e)


def _first_str(data: dict[str, Any], key: str) -> str | None:
    val = data.get(key)
    if isinstance(val, list) and val:
        return str(val[0])
    if val:
        return str(val)
    return None


def _extract_year(data: dict[str, Any]) -> int | None:
    for key in ("publication_year", "published-print", "created"):
        val = data.get(key)
        if isinstance(val, dict):
            val = val.get("date-parts", [[None]])[0][0]
        if isinstance(val, int):
            return val
        if isinstance(val, str):
            try:
                return int(val[:4])
            except ValueError:
                pass
    return None


def _extract_authors(data: dict[str, Any]) -> list[str]:
    authors = data.get("author", [])
    if not isinstance(authors, list):
        return []
    result = []
    for a in authors:
        if isinstance(a, dict):
            family = a.get("family", "")
            given = a.get("given", "")
            name = f"{given} {family}".strip()
            if name:
                result.append(name)
    return result[:5]


def _extract_openalex_authors(w: dict[str, Any]) -> list[str]:
    authorships = w.get("authorships", [])
    result = []
    for a in authorships:
        if isinstance(a, dict):
            author = a.get("author", {})
            if isinstance(author, dict):
                name = author.get("display_name", "")
                if name:
                    result.append(name)
    return result[:5]
