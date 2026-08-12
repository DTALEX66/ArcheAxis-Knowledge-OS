"""Public evidence connectors (ADS-004/005/006/007).

Lightweight HTTP wrappers for public knowledge APIs:
- Crossref REST (DOI metadata, no API key required for basic queries)
- DataCite REST (dataset DOI metadata)
- OpenAlex (academic entity graph, needs free API key for higher limits)
- Wikidata (entity/identifier queries, no key)

Each connector is independently usable, rate-limit aware, and returns structured results.
These are ADOPT items from the absorption atlas v2.

Guardrails:
- These APIs provide public metadata, not verified truth.
- Source independence is judged by organizational lineage, not URL count.
- Results must go through the Evidence cross-validation layer before becoming VerifiedKnowledge.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from typing import Any

__all__ = [
    "CrossrefClient",
    "DataCiteClient",
    "OpenAlexClient",
    "WikidataClient",
    "EvidenceConnectorError",
]

_DEFAULT_TIMEOUT = 15  # seconds
_DEFAULT_DELAY = 0.5  # seconds between calls (polite pool)


class EvidenceConnectorError(Exception):
    """Structured connector error with status code and retry hint."""


def _fetch(url: str, timeout: int = _DEFAULT_TIMEOUT) -> dict[str, Any]:
    """HTTP GET with User-Agent and JSON parsing."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ArcheAxis-Knowledge/0.5 (evidence-connector; mailto:opensource@example.com)",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as e:
        raise EvidenceConnectorError(f"HTTP {e.code} {e.reason}") from e
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        raise EvidenceConnectorError(str(e)) from e


class CrossrefClient:
    """Crossref REST API client. Public/polite pool — no key needed for basic queries."""

    BASE = "https://api.crossref.org/works"

    def __init__(self) -> None:
        self._last_call = 0.0

    def _respect_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < _DEFAULT_DELAY:
            time.sleep(_DEFAULT_DELAY - elapsed)

    def lookup_doi(self, doi: str) -> dict[str, Any]:
        """Look up a DOI. Returns Crossref message dict or raises EvidenceConnectorError."""
        self._respect_rate_limit()
        url = f"{self.BASE}/{urllib.parse.quote(doi, safe='')}"
        try:
            self._last_call = time.monotonic()
            return _fetch(url)
        finally:
            # update timestamp on errors too to avoid tight loops
            pass

    def search(self, query: str, rows: int = 5) -> dict[str, Any]:
        """Simple bibliographic search. query="title+author" format."""
        self._respect_rate_limit()
        url = f"{self.BASE}?query={urllib.parse.quote(query)}&rows={min(rows, 10)}"
        self._last_call = time.monotonic()
        return _fetch(url)


class DataCiteClient:
    """DataCite REST API client. Open metadata, no key required."""

    BASE = "https://api.datacite.org/dois"

    def __init__(self) -> None:
        self._last_call = 0.0

    def _respect_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < _DEFAULT_DELAY:
            time.sleep(_DEFAULT_DELAY - elapsed)

    def lookup_doi(self, doi: str) -> dict[str, Any]:
        """Look up a DataCite DOI. Returns DataCite response dict."""
        self._respect_rate_limit()
        url = f"{self.BASE}/{urllib.parse.quote(doi, safe='')}"
        self._last_call = time.monotonic()
        return _fetch(url)


class OpenAlexClient:
    """OpenAlex API client. Freemium — free key gives higher rate limits.

    Without key: ~10 calls/minute. With free key: ~100k/day.
    Obtain key at https://openalex.org/account.
    """

    BASE = "https://api.openalex.org"

    def __init__(self, email: str | None = None, api_key: str | None = None) -> None:
        self._email = email
        self._api_key = api_key
        self._last_call = 0.0

    def _respect_rate_limit(self) -> None:
        delay = 0.1 if self._api_key else 3.0  # 10/s with key, ~10/min without
        elapsed = time.monotonic() - self._last_call
        if elapsed < delay:
            time.sleep(delay - elapsed)

    def lookup_work(self, openalex_id: str) -> dict[str, Any]:
        """Look up a work by OpenAlex ID (e.g., 'W2741809807')."""
        self._respect_rate_limit()
        url = f"{self.BASE}/works/{openalex_id}"
        if self._email:
            url += f"?mailto={urllib.parse.quote(self._email)}"
        self._last_call = time.monotonic()
        return _fetch(url)

    def search(self, query: str, per_page: int = 5) -> dict[str, Any]:
        """Search works by title/abstract/author."""
        self._respect_rate_limit()
        url = f"{self.BASE}/works?search={urllib.parse.quote(query)}&per_page={min(per_page, 10)}"
        if self._email:
            url += f"&mailto={urllib.parse.quote(self._email)}"
        self._last_call = time.monotonic()
        return _fetch(url)


class WikidataClient:
    """Wikidata entity/identifier queries. Narrow queries only — no fuzzy full-text search.

    Uses wbgetentities API. Data is CC0.
    """

    BASE = "https://www.wikidata.org/w/api.php"

    def __init__(self) -> None:
        self._last_call = 0.0

    def _respect_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < _DEFAULT_DELAY:
            time.sleep(_DEFAULT_DELAY - elapsed)

    def get_entity(self, qid: str) -> dict[str, Any]:
        """Fetch a Wikidata entity by QID (e.g., 'Q42' for Douglas Adams)."""
        if not qid.startswith("Q") or not qid[1:].isdigit():
            raise EvidenceConnectorError(f"Invalid QID: {qid}")
        self._respect_rate_limit()
        url = (
            f"{self.BASE}?action=wbgetentities&ids={qid}&format=json&props=labels|descriptions|claims"
        )
        self._last_call = time.monotonic()
        return _fetch(url)
