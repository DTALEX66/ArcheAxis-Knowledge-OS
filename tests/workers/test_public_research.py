"""Bounded anonymous public search; fixtures are synthetic, never live evidence."""
import base64
import gzip
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "services/python-workers/machine/public_research.py"


@pytest.fixture
def worker(monkeypatch):
    # Synthetic fixtures must never inherit the developer's real Windows route.
    monkeypatch.setenv("ARCHEAXIS_PUBLIC_RESEARCH_PROXY", "direct")
    spec = importlib.util.spec_from_file_location("public_research_fixture", WORKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def request(**changes):
    return {"schema": "public-research-worker/v1", "query": "synthetic public words",
            "families": ["encyclopedia", "community", "research"], **changes}


def fake_http(worker, monkeypatch, payloads):
    calls = []
    bodies = [json.dumps(p, ensure_ascii=False).encode() for p in payloads]
    def fetch(url, *, policy, headers):
        calls.append(url)
        assert policy.max_bytes == 131072 and policy.max_redirects == 0
        assert policy.timeout <= 12 and policy.allowed_ports == (443,)
        assert len(policy.allowed_hosts) == 1
        assert "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS" in headers["User-Agent"]
        return SimpleNamespace(body=bodies[len(calls)-1], headers={}, status=200)
    monkeypatch.setattr(worker.http, "fetch", fetch)
    return calls, bodies


def test_duplicate_public_body_is_rejected_without_losing_raw_response(worker, monkeypatch):
    raw = (b'{"items":[{"question_id":42,"title":"Synthetic question",'
           b'"link":"https://academia.stackexchange.com/questions/42/synthetic",'
           b'"body":"<p>SYNTHETIC_FIRST</p>","body":"<p>SYNTHETIC_SECOND</p>"}]}')
    calls = []

    def fetch(url, *, policy, headers):
        calls.append(url)
        return SimpleNamespace(body=raw, headers={}, status=200)

    monkeypatch.setattr(worker.http, "fetch", fetch)
    channel = worker.execute(request(families=["community"]))["channels"][0]
    assert len(calls) == 1
    assert base64.b64decode(channel["raw_response_base64"]) == raw
    assert channel["status"] == "failed", (
        "duplicate body accepted; synthetic observed excerpt="
        + repr(channel["hits"][0]["excerpt"] if channel["hits"] else None)
    )
    assert channel["error_code"] == "invalid_response" and channel["hits"] == []


@pytest.mark.parametrize("revision", [br"\ud800", br"\udc00"], ids=["high-surrogate", "low-surrogate"])
def test_openalex_unpaired_revision_keeps_raw_and_other_channel(worker, monkeypatch, revision):
    wiki_raw = b'{"batchcomplete":true}'
    openalex_raw = (b'{"results":[{"id":"https://openalex.org/W7",'
                    b'"title":"Synthetic paper","updated_date":"' + revision + b'"}]}')
    calls = []

    def fetch(url, *, policy, headers):
        calls.append(url)
        if url.startswith("https://en.wikipedia.org/"):
            return SimpleNamespace(body=wiki_raw, headers={}, status=200)
        if url.startswith("https://api.openalex.org/"):
            return SimpleNamespace(body=openalex_raw, headers={}, status=200)
        pytest.fail("invalid provider data must not trigger a fallback")

    monkeypatch.setattr(worker.http, "fetch", fetch)
    result = worker.execute(request(families=["encyclopedia", "research"], limit=1))
    assert len(calls) == 2 and len(result["channels"]) == 2
    wiki, openalex = result["channels"]
    assert wiki["status"] == "complete" and base64.b64decode(wiki["raw_response_base64"]) == wiki_raw
    assert openalex["status"] == "failed" and openalex["error_code"] == "invalid_response"
    assert openalex["hits"] == [] and base64.b64decode(openalex["raw_response_base64"]) == openalex_raw
    json.dumps(result, ensure_ascii=False).encode("utf-8", errors="strict")


@pytest.mark.parametrize(("revision", "expected"), [
    (b"2026-11-02", "2026-11-02"),
    (br"2026-\ud83d\ude00", "2026-😀"),
], ids=["ascii-date", "paired-surrogates"])
def test_openalex_valid_revision_preserves_unicode_and_raw(worker, monkeypatch, revision, expected):
    raw = (b'{"results":[{"id":"https://openalex.org/W7",'
           b'"title":"Synthetic paper","updated_date":"' + revision + b'"}]}')
    calls = []

    def fetch(url, *, policy, headers):
        calls.append(url)
        assert url.startswith("https://api.openalex.org/")
        return SimpleNamespace(body=raw, headers={}, status=200)

    monkeypatch.setattr(worker.http, "fetch", fetch)
    result = worker.execute(request(families=["research"], limit=1))
    assert len(calls) == 1 and len(result["channels"]) == 1
    channel = result["channels"][0]
    assert channel["status"] == "complete" and channel["error_code"] is None
    assert channel["hits"][0]["upstream_revision"] == expected
    assert base64.b64decode(channel["raw_response_base64"]) == raw
    json.dumps(result, ensure_ascii=False).encode("utf-8", errors="strict")


@pytest.mark.parametrize("compressed", [False, True], ids=["plain", "gzip"])
@pytest.mark.parametrize("raw", [
    b'{"results":[],"results":[]}',
    b'{"results":[],"results":[{}]}',
    br'{"results":[],"res\u0075lts":[]}',
    b'{"results":[],"ignored":{"nested":[{"key":1,"key":1}]}}',
    b'{"results":[],"ignored":{"nested":[{"key":1,"key":2}]}}',
    b'{"results":[],"ignored":[NaN]}',
    b'{"results":[],"ignored":[Infinity]}',
    b'{"results":[],"ignored":[-Infinity]}',
    b'{"results":[],"ignored":{"nested":[1e9999]}}',
    b'{"results":[],"ignored":{"nested":[-1e9999]}}',
    b'{"results":[],"ignored":' + b'[' * 1500 + b'0' + b']' * 1500 + b'}',
], ids=["same-root", "conflicting-root", "escaped-key", "same-nested", "conflicting-nested",
        "nan", "positive-infinity", "negative-infinity", "positive-float-overflow",
        "negative-float-overflow", "excessive-depth"])
def test_ambiguous_or_nonfinite_json_fails_closed_without_fallback(worker, monkeypatch, capsys, raw, compressed):
    received = gzip.compress(raw, mtime=0) if compressed else raw
    response_headers = {"content-encoding": "gzip"} if compressed else {}
    calls = []

    def fetch(url, *, policy, headers):
        calls.append(url)
        return SimpleNamespace(body=received, headers=response_headers, status=200)

    monkeypatch.setattr(worker.http, "fetch", fetch)
    result = worker.execute(request(families=["research"]))
    assert len(calls) == 1 and calls[0].startswith("https://api.openalex.org/")
    assert len(result["channels"]) == 1
    channel = result["channels"][0]
    assert channel["provider"] == "openalex" and channel["status"] == "failed"
    assert channel["error_code"] == "invalid_response" and channel["hits"] == []
    assert base64.b64decode(channel["raw_response_base64"]) == received
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "utf-16", "utf-16-be", "utf-32", "utf-32-be"])
@pytest.mark.parametrize("depth", [64, 65], ids=["at-limit", "over-limit"])
@pytest.mark.parametrize("compressed", [False, True], ids=["plain", "gzip"])
def test_json_nesting_bound_preserves_existing_utf_encodings(
        worker, monkeypatch, encoding, depth, compressed):
    # The outer object counts as one; alternate object/array levels thereafter.
    levels = [("[", "]") if index % 2 == 0 else ('{"node":', "}")
              for index in range(depth - 1)]
    text = ('{"results":[],"ignored":' + "".join(level[0] for level in levels) + "0"
            + "".join(level[1] for level in reversed(levels)) + "}")
    raw = text.encode(encoding)
    received = gzip.compress(raw, mtime=0) if compressed else raw
    response_headers = {"content-encoding": "gzip"} if compressed else {}
    calls = []

    def fetch(url, *, policy, headers):
        calls.append(url)
        return SimpleNamespace(body=received, headers=response_headers, status=200)

    monkeypatch.setattr(worker.http, "fetch", fetch)
    result = worker.execute(request(families=["research"]))
    assert len(calls) == len(result["channels"]) == 1
    channel = result["channels"][0]
    assert channel["status"] == ("complete" if depth == 64 else "failed")
    assert channel["error_code"] == (None if depth == 64 else "invalid_response")
    assert channel["hits"] == [] and base64.b64decode(channel["raw_response_base64"]) == received


@pytest.mark.parametrize("compressed", [False, True], ids=["plain", "gzip"])
def test_json_nesting_ignores_brackets_in_escaped_strings(worker, monkeypatch, compressed):
    # json.dumps escapes the adjacent backslashes and quotes; braces in this
    # string are data even when their count exceeds the structural limit.
    opaque = "left" + chr(92) + chr(34) + "[" * 200 + chr(92) * 2 + "}" * 200 + chr(34) + "right"
    raw = json.dumps({"results": [], "ignored": opaque}, ensure_ascii=False).encode("utf-8")
    received = gzip.compress(raw, mtime=0) if compressed else raw
    response_headers = {"content-encoding": "gzip"} if compressed else {}
    assert worker._json_response(received, response_headers)["ignored"] == opaque
    monkeypatch.setattr(worker.http, "fetch", lambda *a, **k: SimpleNamespace(
        body=received, headers=response_headers, status=200))
    result = worker.execute(request(families=["research"]))
    assert len(result["channels"]) == 1
    channel = result["channels"][0]
    assert channel["status"] == "complete" and channel["hits"] == []
    assert base64.b64decode(channel["raw_response_base64"]) == received


@pytest.mark.parametrize("compressed", [False, True], ids=["plain", "gzip"])
def test_finite_public_json_numbers_remain_accepted(worker, monkeypatch, compressed):
    raw = (b'{"results":[],"ignored":{"values":'
           b'[0,-1,1.25,-0.125,1.75e3,1e-310,1.7976931348623157e308]}}')
    received = gzip.compress(raw, mtime=0) if compressed else raw
    response_headers = {"content-encoding": "gzip"} if compressed else {}
    parsed = worker._json_response(received, response_headers)
    numbers = parsed["ignored"]["values"]
    assert numbers[:5] == [0, -1, 1.25, -0.125, 1750.0]
    assert numbers[5] > 0 and all(math.isfinite(number) for number in numbers)

    calls = []

    def fetch(url, *, policy, headers):
        calls.append(url)
        return SimpleNamespace(body=received, headers=response_headers, status=200)

    monkeypatch.setattr(worker.http, "fetch", fetch)
    result = worker.execute(request(families=["research"]))
    assert len(calls) == len(result["channels"]) == 1
    channel = result["channels"][0]
    assert channel["status"] == "complete" and channel["hits"] == [] and channel["error_code"] is None
    assert base64.b64decode(channel["raw_response_base64"]) == received


def test_three_families_keep_raw_and_distinguish_representations(worker, monkeypatch):
    wiki = {"query": {"pages": [{"pageid": 12, "title": "Synthetic wiki", "index": 1,
            "revisions": [{"revid": 99, "timestamp": "2026-10-01T00:00:00Z",
            "slots": {"main": {"content": "Lead ''wikitext'' <script>untrusted</script>"}}}]}]}}
    se = {"quota_remaining": 20, "items": [{"question_id": 21, "title": "Synthetic &amp; question",
          "link": "https://academia.stackexchange.com/questions/21/synthetic", "body": "<p>Readable &amp; text</p><script>bad()</script>",
          "content_license": "CC BY-SA 4.0", "last_edit_date": 123}]}
    oa = {"results": [{"id": "https://openalex.org/W7", "title": "Synthetic paper",
          "doi": "https://doi.org/10.1/synthetic", "updated_date": "2026-10-01",
          "abstract_inverted_index": {"A": [0], "result": [1]}}]}
    calls, bodies = fake_http(worker, monkeypatch, [wiki, se, oa])
    result = worker.execute(request())
    assert result["schema"] == "public-research-worker/v1"
    assert len(calls) == 3 and "generator=search" in calls[0] and "sort=relevance" in calls[1]
    for channel, raw in zip(result["channels"], bodies):
        assert channel["status"] == "complete"
        assert base64.b64decode(channel["raw_response_base64"]) == raw
        assert channel["retry_after_seconds"] is None and channel["error_code"] is None
    w, s, a = [c["hits"][0] for c in result["channels"]]
    assert w["representation"] == "wikitext" and w["content"] == "excerpt"
    assert w["upstream_revision"] == "99" and "oldid=99" in w["url"]
    assert s["excerpt"] == "Readable & text" and s["representation"] == "html_text"
    assert s["license"] == "CC BY-SA 4.0" and "bad()" not in s["excerpt"]
    assert a["excerpt"] == "A result" and a["representation"] == "abstract"
    assert a["url"] == "https://openalex.org/W7" and a["license"] is None
    assert all(h["truncated"] is False for h in (w, s, a))


@pytest.mark.parametrize("changes", [
    {"query": " "}, {"query": "x\0y"}, {"query": "x"*1001}, {"document": "PRIVATE"},
    {"families": []}, {"families": ["research", "research"]}, {"families": ["unknown"]},
    {"limit": 0}, {"limit": 4}, {"limit": True}, {"schema": "other"},
    {"community_site": "stackoverflow"}, {"community_site": None}, {"community_site": []},
])
def test_invalid_request_never_dispatches(worker, monkeypatch, changes):
    monkeypatch.setattr(worker.http, "fetch", lambda *a, **k: pytest.fail("network must not run"))
    with pytest.raises(ValueError):
        worker.execute(request(**changes))


def test_provider_failure_is_not_successful_empty_and_others_continue(worker, monkeypatch):
    count = 0
    def fetch(*a, **k):
        nonlocal count
        count += 1
        if count == 1:
            raise worker.http.SafeHTTPStatusError(429, {"retry-after": "42", "set-cookie": "SECRET"})
        return SimpleNamespace(body=b'{"items":[],"quota_remaining":0}', headers={}, status=200)
    monkeypatch.setattr(worker.http, "fetch", fetch)
    result = worker.execute(request(families=["encyclopedia", "community"]))
    w, s = result["channels"]
    assert w["status"] == "limited" and w["retry_after_seconds"] == 42
    assert w["raw_response_base64"] is None and w["error_code"] == "http_429"
    assert s["status"] == "limited" and s["error_code"] == "quota_exhausted"
    assert "SECRET" not in json.dumps(result)


def test_empty_result_and_backoff_are_distinct(worker, monkeypatch):
    fake_http(worker, monkeypatch, [{"results": []}, {"items": [], "backoff": 7}])
    result = worker.execute(request(families=["research", "community"]))
    assert result["channels"][0]["status"] == "complete"
    assert result["channels"][0]["hits"] == []
    assert result["channels"][1]["status"] == "limited"
    assert result["channels"][1]["retry_after_seconds"] == 7


@pytest.mark.parametrize("payload", [{"unexpected": []}, {"results": ["bad"]},
    {"results": [{"id": "http://127.0.0.1/private", "title": "unsafe"}]},
    {"results": [{"id": "https://openalex.org/W7", "title": "x", "abstract_inverted_index": {"x": [999999999]}}]}])
def test_malformed_or_unsafe_provider_result_is_failed(worker, monkeypatch, payload):
    fake_http(worker, monkeypatch, [payload])
    channel = worker.execute(request(families=["research"]))["channels"][0]
    assert channel["status"] == "failed" and channel["error_code"] == "invalid_response"
    assert channel["raw_response_base64"] is not None


def test_excerpt_truncation_is_utf8_safe_and_explicit(worker, monkeypatch):
    fake_http(worker, monkeypatch, [{"items": [{"question_id": 1, "title": "x",
        "link": "https://academia.stackexchange.com/questions/1/x", "body": "<p>" + "汉"*7000 + "</p>"}]}])
    hit = worker.execute(request(families=["community"]))["channels"][0]["hits"][0]
    assert hit["truncated"] and hit["content"] == "excerpt"
    assert len(hit["excerpt"].encode()) <= 16384 and "�" not in hit["excerpt"]


def test_no_abstract_is_metadata_not_fabricated_text(worker, monkeypatch):
    fake_http(worker, monkeypatch, [{"results": [{"id": "https://openalex.org/W7", "title": "Only metadata"}]}])
    hit = worker.execute(request(families=["research"]))["channels"][0]["hits"][0]
    assert hit["content"] == "metadata" and hit["excerpt"] == ""
    assert hit["representation"] == "metadata" and hit["locator"] is None
    assert hit["license"] == "CC0"


@pytest.mark.parametrize("abstract, expected_license", [
    ({"Synthetic": [0], "abstract": [1]}, None),
    (None, "CC0"),
    ({}, "CC0"),
])
def test_openalex_metadata_license_does_not_extend_to_abstract_text(
        worker, monkeypatch, abstract, expected_license):
    payload = {"results": [{"id": "https://openalex.org/W7", "title": "Synthetic paper",
                            "abstract_inverted_index": abstract}]}
    _, raw = fake_http(worker, monkeypatch, [payload])
    channel = worker.execute(request(families=["research"]))["channels"][0]
    assert channel["hits"][0]["license"] == expected_license
    assert base64.b64decode(channel["raw_response_base64"]) == raw[0]


def test_cancel_check_prevents_next_provider(worker, monkeypatch):
    calls, _ = fake_http(worker, monkeypatch, [{"results": []}])
    def cancel():
        return bool(calls)
    with pytest.raises(worker.Cancelled):
        worker.execute(request(families=["research", "community"]), cancelled=cancel)
    assert len(calls) == 1


def test_entrypoint_rejects_unknown_private_field_without_network():
    child = subprocess.run([sys.executable, "-B", str(WORKER.parent / "worker_machine_answer.py"), "--public-research"],
                           input=json.dumps(request(document="PRIVATE_SENTINEL")).encode(), capture_output=True, timeout=5)
    assert child.returncode != 0 and b"PRIVATE_SENTINEL" not in child.stdout + child.stderr
    assert child.stdout == b""


def test_isolated_core_entrypoint_loads_its_fixed_module_without_pythonpath():
    import os
    environment = dict(os.environ)
    environment["ARCHEAXIS_PUBLIC_RESEARCH_PROXY"] = "invalid-route"
    child = subprocess.run(
        [sys.executable, "-I", "-B", str(WORKER.parent / "worker_machine_answer.py"), "--public-research"],
        input=json.dumps(request(limit=1)).encode(), env=environment,
        capture_output=True, timeout=5,
    )
    assert child.returncode == 0, "the fixed Core entrypoint must work under isolated Python"
    receipt = json.loads(child.stdout)
    assert receipt["schema"] == "public-research-worker/v1"
    assert len(receipt["channels"]) == 3
    assert all(channel["error_code"] == "proxy_config_invalid" for channel in receipt["channels"])
    assert child.stderr == b"", "invalid proxy must fail closed without a network request or traceback"


def test_gzip_preserves_actual_response_bytes_and_bounds_inflation(worker, monkeypatch):
    raw = gzip.compress(b'{"results":[]}')
    monkeypatch.setattr(worker.http, "fetch", lambda *a, **k: SimpleNamespace(body=raw, headers={"content-encoding": "gzip"}, status=200))
    channel = worker.execute(request(families=["research"]))["channels"][0]
    assert channel["status"] == "complete" and base64.b64decode(channel["raw_response_base64"]) == raw
    raw = gzip.compress(b" " * (worker.MAX_RESPONSE + 1))
    channel = worker.execute(request(families=["research"]))["channels"][0]
    assert channel["status"] == "failed" and channel["error_code"] == "invalid_response"


def test_transport_exception_does_not_expose_query_or_exception(worker, monkeypatch):
    def fail(*a, **k):
        raise OSError("PRIVATE_EXCEPTION_SENTINEL")
    monkeypatch.setattr(worker.http, "fetch", fail)
    result = worker.execute(request(families=["research"]))
    assert result["channels"][0]["status"] == "offline"
    assert "PRIVATE_EXCEPTION_SENTINEL" not in json.dumps(result)


def test_only_approved_protocol_fields_escape(worker, monkeypatch):
    fake_http(worker, monkeypatch, [{"results": [{"id": "https://openalex.org/W7", "title": "x", "future_untrusted": "raw-only"}]}])
    result = worker.execute(request(families=["research"]))
    assert set(result) == {"schema", "query", "families", "channels"}
    channel = result["channels"][0]
    assert set(channel) == {"family", "provider", "status", "retrieved_at", "request_url", "retry_after_seconds", "error_code", "raw_response_base64", "hits"}
    assert set(channel["hits"][0]) == {"id", "family", "provider", "title", "url", "retrieved_at", "content", "excerpt", "locator", "license", "free_access", "upstream_revision", "representation", "truncated"}
    assert "future_untrusted" not in channel["hits"][0]


def test_selected_forum_site_binds_query_and_hit_identity(worker, monkeypatch):
    calls, _ = fake_http(worker, monkeypatch, [{"items": [{"question_id": 42,
        "title": "Synthetic stats", "link": "https://stats.stackexchange.com/questions/42/x",
        "body": "<p>Public comparison</p>"}]}])
    channel = worker.execute(request(families=["community"], community_site="stats"))["channels"][0]
    assert "site=stats" in calls[0]
    assert channel["hits"][0]["id"] == "stackexchange:stats:question:42"
    fake_http(worker, monkeypatch, [{"items": [{"question_id": 42, "title": "Wrong site",
        "link": "https://academia.stackexchange.com/questions/42/x"}]}])
    channel = worker.execute(request(families=["community"], community_site="stats"))["channels"][0]
    assert channel["status"] == "failed" and channel["error_code"] == "invalid_response"


@pytest.mark.parametrize("status", [429, 500, 503])
def test_openalex_unavailable_preserves_original_and_crossref_metadata_receipts(worker, monkeypatch, status):
    calls = []
    raw = b'{"status":"ok","message":{"items":[{"DOI":"10.1234/synthetic","title":["Synthetic title"]}]}}'
    def fetch(url, *, policy, headers):
        calls.append(url)
        assert policy.max_redirects == 0 and policy.allowed_hosts == (url.split('/')[2],)
        if len(calls) == 1:
            raise worker.http.SafeHTTPStatusError(status, {"retry-after": "42"})
        return SimpleNamespace(body=raw, headers={}, status=200)
    monkeypatch.setattr(worker.http, "fetch", fetch)
    primary, fallback = worker.execute(request(families=["research"], limit=3))["channels"]
    assert primary["provider"] == "openalex" and primary["error_code"] == f"http_{status}"
    assert primary["retry_after_seconds"] == 42 and primary["raw_response_base64"] is None
    assert fallback["provider"] == "crossref" and fallback["status"] == "complete"
    assert calls[1].startswith("https://api.crossref.org/works?query.bibliographic=") and "rows=3" in calls[1]
    assert base64.b64decode(fallback["raw_response_base64"]) == raw
    hit = fallback["hits"][0]
    assert hit["provider"] == "crossref" and hit["id"] == hit["url"] == "https://doi.org/10.1234/synthetic"
    assert hit["content"] == hit["representation"] == "metadata" and hit["excerpt"] == ""
    assert hit["license"] is None and hit["upstream_revision"] is None


def test_crossref_failure_and_cancellation_are_never_hidden(worker, monkeypatch):
    calls = []
    def fetch(url, **kwargs):
        calls.append(url)
        raise worker.http.SafeHTTPStatusError(429 if len(calls) == 1 else 503, {})
    monkeypatch.setattr(worker.http, "fetch", fetch)
    channels = worker.execute(request(families=["research"]))["channels"]
    assert [(c["provider"], c["error_code"]) for c in channels] == [("openalex", "http_429"), ("crossref", "http_503")]
    calls.clear()
    with pytest.raises(worker.Cancelled):
        worker.execute(request(families=["research"]), cancelled=lambda: bool(calls))
    assert len(calls) == 1


@pytest.mark.parametrize("failure", ["invalid_response", "proxy_tls_failed", "proxy_config_invalid", "http_403"])
def test_crossref_does_not_bypass_invalid_response_or_security_refusal(worker, monkeypatch, failure):
    calls = []
    def fetch(url, **kwargs):
        calls.append(url)
        if failure == "invalid_response":
            return SimpleNamespace(body=b'{"unexpected":[]}', headers={}, status=200)
        if failure == "http_403":
            raise worker.http.SafeHTTPStatusError(403, {})
        raise worker.proxy_transport.ProxyFailure(failure)
    monkeypatch.setattr(worker.http, "fetch", fetch)
    channels = worker.execute(request(families=["research"]))["channels"]
    assert len(calls) == len(channels) == 1 and channels[0]["error_code"] == failure
