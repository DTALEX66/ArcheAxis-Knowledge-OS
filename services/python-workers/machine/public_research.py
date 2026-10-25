"""Anonymous, bounded public queries. No documents, models, credentials or DB writes.

Raw API bytes and explicitly derived representations are returned to the Core writer.
The caller owns process cancellation; execute also checks cancellation between providers.
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
import re
import sys
import zlib
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable
from urllib.parse import urlencode, urlsplit

SCHEMA = "public-research-worker/v1"
MAX_INPUT = 8192
MAX_OUTPUT = 1024 * 1024
MAX_RESPONSE = 128 * 1024
MAX_EXCERPT = 16 * 1024
FAMILIES = {"encyclopedia": "wikipedia", "community": "stackexchange", "research": "openalex"}
USER_AGENT = "ArcheAxis-Knowledge/0.6 (public-research; https://github.com/DTALEX66/ArcheAxis-Knowledge-OS)"


def _http_module():
    here = Path(__file__).resolve()
    candidates = [here.parents[2] / "shared/safe_http.py", here.parents[3] / "shared/safe_http.py"]
    path = next((p for p in candidates if p.is_file()), None)
    if path is None:
        raise RuntimeError("public_http_unavailable")
    spec = importlib.util.spec_from_file_location("public_research_safe_http", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


http = _http_module()


def _proxy_module():
    spec = importlib.util.spec_from_file_location("public_research_proxy_transport",
        Path(__file__).with_name("public_research_proxy.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


proxy_transport = _proxy_module()


class Cancelled(Exception):
    pass


def validate(request: dict) -> tuple[str, list[str], int]:
    if not isinstance(request, dict) or not {"schema", "query", "families"} <= request.keys() \
            or set(request) - {"schema", "query", "families", "limit"} or request["schema"] != SCHEMA:
        raise ValueError("invalid_request")
    query, families, limit = request["query"], request["families"], request.get("limit", 1)
    if not isinstance(query, str) or not query.strip() or len(query) > 1000 \
            or len(query.encode("utf8")) > 4000 or any(ord(c) < 32 or ord(c) == 127 for c in query):
        raise ValueError("invalid_query")
    if not isinstance(families, list) or not 1 <= len(families) <= 3 \
            or any(not isinstance(f, str) or f not in FAMILIES for f in families) \
            or len(set(families)) != len(families) or type(limit) is not int or not 1 <= limit <= 3:
        raise ValueError("invalid_scope")
    return query, families, limit


def _bounded(value: str, limit: int) -> tuple[str, bool]:
    encoded = value.encode("utf8")
    return (encoded[:limit].decode("utf8", errors="ignore"), True) if len(encoded) > limit else (value, False)


def _text(value, *, optional=False):
    if value is None and optional:
        return None
    if not isinstance(value, str) or "\0" in value:
        raise ValueError("invalid_response")
    return value


def _url(value, hosts):
    value = _text(value)
    parsed = urlsplit(value)
    if len(value) > 2048 or parsed.scheme != "https" or parsed.hostname not in hosts \
            or parsed.username or parsed.password or parsed.port not in (None, 443) \
            or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError("invalid_response")
    return value


class _HTMLText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        elif not self.hidden and tag in ("p", "br", "li", "div", "pre", "blockquote"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.hidden:
            self.hidden -= 1
        elif not self.hidden and tag in ("p", "li", "div", "pre", "blockquote"):
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def _html_text(value):
    parser = _HTMLText()
    parser.feed(_text(value))
    return "\n".join(line.strip() for line in "".join(parser.parts).splitlines() if line.strip())


def _hit(family, identity, title, url, when, text, representation, locator, license, revision, *, full=False):
    title = _text(title)
    if not title.strip() or len(title.encode("utf8")) > 4096:
        raise ValueError("invalid_response")
    excerpt, truncated = _bounded(text, MAX_EXCERPT)
    return {"id": identity, "family": family, "provider": FAMILIES[family], "title": title,
            "url": url, "retrieved_at": when,
            "content": "metadata" if not excerpt else "full_text" if full and not truncated else "excerpt",
            "excerpt": excerpt, "locator": locator if excerpt else None, "license": license,
            "free_access": "free", "upstream_revision": revision,
            "representation": representation if excerpt else "metadata", "truncated": truncated}


def _wikipedia(data, when, limit):
    if "error" in data or not isinstance(data.get("query", {}).get("pages"), list):
        # MediaWiki's successful no-match shape is a batchcomplete object, no query.
        if "error" not in data and "batchcomplete" in data and "query" not in data:
            return []
        raise ValueError("invalid_response")
    result = []
    for page in sorted(data["query"]["pages"], key=lambda page: page.get("index", 0))[:limit]:
        revision = page["revisions"][0]
        page_id, revid = page["pageid"], revision["revid"]
        if type(page_id) is not int or type(revid) is not int or page_id <= 0 or revid <= 0:
            raise ValueError("invalid_response")
        text = _text(revision["slots"]["main"]["content"])
        result.append(_hit("encyclopedia", f"wikipedia:en:{page_id}:{revid}", page["title"],
            f"https://en.wikipedia.org/w/index.php?oldid={revid}", when, text, "wikitext",
            f"pageid={page_id};revid={revid};section=0", "CC BY-SA 4.0", str(revid)))
    return result


def _community(data, when, limit):
    if "error_id" in data or not isinstance(data.get("items"), list):
        raise ValueError("invalid_response")
    result = []
    for item in data["items"][:limit]:
        identity = item["question_id"]
        if type(identity) is not int or identity <= 0:
            raise ValueError("invalid_response")
        url = _url(item["link"], {"academia.stackexchange.com"})
        text = _html_text(item["body"]) if "body" in item else ""
        revision = item.get("last_edit_date")
        revision = f"last_edit_date:{revision}" if type(revision) is int and revision >= 0 else None
        license = _text(item.get("content_license"), optional=True)
        if license is not None and license not in {"CC BY-SA 2.5", "CC BY-SA 3.0", "CC BY-SA 4.0"}:
            license = None
        result.append(_hit("community", f"stackexchange:academia:question:{identity}",
            _html_text(item["title"]), url, when, text, "html_text", f"question_id={identity};body",
            license, revision, full=True))
    return result


def _abstract(value):
    if value is None:
        return ""
    if not isinstance(value, dict):
        raise ValueError("invalid_response")
    words = {}
    for word, positions in value.items():
        if not isinstance(word, str) or not isinstance(positions, list) or len(word) > 16384:
            raise ValueError("invalid_response")
        for position in positions:
            if type(position) is not int or not 0 <= position < 32768 or position in words:
                raise ValueError("invalid_response")
            words[position] = word
    if words and (min(words) != 0 or max(words) + 1 != len(words)):
        raise ValueError("invalid_response")
    return " ".join(words[p] for p in range(len(words)))


def _research(data, when, limit):
    if "error" in data or not isinstance(data.get("results"), list):
        raise ValueError("invalid_response")
    result = []
    for item in data["results"][:limit]:
        identity = _url(item["id"], {"openalex.org"})
        if not re.fullmatch(r"https://openalex.org/W[0-9]+", identity):
            raise ValueError("invalid_response")
        text = _abstract(item.get("abstract_inverted_index"))
        revision = _text(item.get("updated_date"), optional=True)
        if revision is not None and len(revision) > 64:
            raise ValueError("invalid_response")
        # OpenAlex metadata licensing does not establish the abstract text's license.
        license = None if text else "CC0"
        result.append(_hit("research", identity, item.get("title") or item.get("display_name"), identity, when,
            text, "abstract", f"{identity}#/abstract_inverted_index", license, revision))
    return result


def _endpoint(family, query, limit):
    if family == "encyclopedia":
        return "https://en.wikipedia.org/w/api.php?" + urlencode({"action": "query", "generator": "search",
            "gsrsearch": query, "gsrlimit": limit, "gsrnamespace": 0, "prop": "revisions",
            "rvprop": "ids|timestamp|content", "rvslots": "main", "rvsection": 0,
            "format": "json", "formatversion": 2})
    if family == "community":
        return "https://api.stackexchange.com/2.3/search/advanced?" + urlencode({"site": "academia",
            "q": query, "pagesize": limit, "sort": "relevance", "filter": "withbody"})
    return "https://api.openalex.org/works?" + urlencode({"search": query, "per_page": limit})


def _json_response(body, headers):
    if headers.get("content-encoding", "").lower() == "gzip" or body.startswith(b"\x1f\x8b"):
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
        body = decoder.decompress(body, MAX_RESPONSE + 1)
        if len(body) > MAX_RESPONSE or not decoder.eof or decoder.unused_data:
            raise ValueError("invalid_response")
    value = json.loads(body)
    if not isinstance(value, dict):
        raise ValueError("invalid_response")
    return value


def execute(request: dict, *, cancelled: Callable[[], bool] = lambda: False) -> dict:
    query, families, limit = validate(request)
    result = {"schema": SCHEMA, "query": query, "families": families, "channels": []}
    parsers = {"encyclopedia": _wikipedia, "community": _community, "research": _research}
    if cancelled():
        raise Cancelled()
    proxy_url, proxy_error = None, None
    try:
        proxy_url = proxy_transport.select_proxy(os.environ.get("ARCHEAXIS_PUBLIC_RESEARCH_PROXY"))
    except proxy_transport.ProxyFailure as exc:
        proxy_error = exc.code
    for family in families:
        if cancelled():
            raise Cancelled()
        when = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        endpoint = _endpoint(family, query, limit)
        channel = {"family": family, "provider": FAMILIES[family], "status": "failed",
            "retrieved_at": when, "retry_after_seconds": None, "error_code": None,
            "request_url": endpoint, "raw_response_base64": None, "hits": []}
        result["channels"].append(channel)
        try:
            if proxy_error:
                raise proxy_transport.ProxyFailure(proxy_error)
            policy = http.SafeHTTPPolicy(timeout=12,
                max_bytes=MAX_RESPONSE, max_redirects=0, allowed_ports=(443,),
                allowed_hosts=(urlsplit(endpoint).hostname,), allowed_content_types=("application/json",))
            headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
            response = (http.fetch(endpoint, policy=policy, headers=headers) if proxy_url is None else
                proxy_transport.fetch(endpoint, policy=policy, headers=headers, proxy_url=proxy_url, http=http))
            if len(response.body) > MAX_RESPONSE:
                raise ValueError("invalid_response")
            when = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            channel["retrieved_at"] = when
            channel["raw_response_base64"] = base64.b64encode(response.body).decode("ascii")
            data = _json_response(response.body, response.headers)
            channel["hits"] = parsers[family](data, when, limit)
            channel["status"] = "complete"
            if family == "community":
                backoff = data.get("backoff")
                if type(backoff) is int and 0 <= backoff <= 86400:
                    channel.update(status="limited", retry_after_seconds=backoff, error_code="provider_backoff")
                if type(data.get("quota_remaining")) is int and data["quota_remaining"] == 0:
                    channel.update(status="limited", error_code="quota_exhausted")
        except http.SafeHTTPStatusError as exc:
            channel.update(status="limited" if exc.status_code == 429 else "failed",
                           retry_after_seconds=exc.retry_after_seconds, error_code=f"http_{exc.status_code}")
        except proxy_transport.ProxyFailure as exc:
            channel.update(status="offline" if exc.code == "proxy_timeout" else "failed", error_code=exc.code)
        except http.SafeHTTPError as exc:
            # Only static transport classifications escape; exception URLs/messages never do.
            message = str(exc)
            offline = message.startswith("DNS resolution") or "timeout" in message.lower()
            channel.update(status="offline" if offline else "failed",
                           error_code="network_unavailable" if offline else "transport_or_policy")
        except (ValueError, TypeError, KeyError, IndexError, AttributeError, zlib.error):
            channel.update(status="failed", error_code="invalid_response", hits=[])
        except OSError:
            channel.update(status="offline", error_code="network_unavailable", hits=[])
        if cancelled():
            raise Cancelled()
    if len(json.dumps(result, ensure_ascii=False).encode("utf8")) > MAX_OUTPUT:
        raise ValueError("output_limit")
    return result


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT + 1)
        if len(raw) > MAX_INPUT:
            raise ValueError("input_limit")
        result = execute(json.loads(raw))
        output = json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode("utf8")
        if len(output) + 1 > MAX_OUTPUT:
            raise ValueError("output_limit")
        sys.stdout.buffer.write(output + b"\n")
        return 0
    except Exception:
        # Invalid requests have no valid response identity; Core reports worker failure.
        sys.stderr.write("public_research_request_failed\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
