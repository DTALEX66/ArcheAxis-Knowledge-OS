"""SafeHTTP status compatibility and safe retry metadata for public research."""
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from types import SimpleNamespace

import pytest

from shared import safe_http


@pytest.mark.parametrize("value,expected", [("42", 42), ("0", 0), ("-1", None),
    ("999999", None), ("abc", None), ("9"*150, None)])
def test_retry_after_is_bounded_without_retaining_other_headers(value, expected):
    error = safe_http.SafeHTTPStatusError(429, {"retry-after": value, "set-cookie": "SECRET"})
    assert isinstance(error, safe_http.SafeHTTPError)
    assert str(error) == "HTTP status 429" and error.retry_after_seconds == expected
    assert "SECRET" not in repr(error.__dict__)


def test_retry_after_http_date():
    future = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=60))
    error = safe_http.SafeHTTPStatusError(503, {"retry-after": future})
    assert 58 <= error.retry_after_seconds <= 60


def test_fetch_retains_retry_metadata_and_legacy_message(monkeypatch):
    monkeypatch.setattr(safe_http, "_resolve_addresses", lambda *a, **k: ["93.184.216.34"])
    monkeypatch.setattr(safe_http, "_open_once", lambda *a, **k: SimpleNamespace(status=429,
        headers={"retry-after": "9", "set-cookie": "SECRET"}, body=b"private error body"))
    with pytest.raises(safe_http.SafeHTTPStatusError, match="HTTP status 429") as caught:
        safe_http.fetch("https://example.org/")
    assert caught.value.retry_after_seconds == 9 and caught.value.status_code == 429
    assert "SECRET" not in repr(caught.value.__dict__)
