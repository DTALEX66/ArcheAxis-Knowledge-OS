"""New MHTML boundary cases; no browser, network or external archive acceptance."""
import base64
import email.errors
import hashlib
import importlib.util
import quopri
import socket
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


worker = load("services/python-workers/web/worker_html.py", "mhtml_worker")


def part(body, media="text/html; charset=utf-8", cid="root", encoding="8bit", location=None):
    headers = f"Content-Type: {media}\r\nContent-Transfer-Encoding: {encoding}\r\n"
    if cid is not None:
        headers += f"Content-ID: <{cid}>\r\n"
    if location is not None:
        headers += f"Content-Location: {location}\r\n"
    return headers.encode("ascii") + b"\r\n" + body


def archive(parts, start="root", media="text/html", top="multipart/related"):
    headers = f'MIME-Version: 1.0\r\nContent-Type: {top}; boundary="BOUND"'
    if media is not None:
        headers += f'; type="{media}"'
    if start is not None:
        headers += f'; start="<{start}>"'
    return (headers + "\r\n\r\n").encode() + b"".join(
        b"--BOUND\r\n" + value + b"\r\n" for value in parts
    ) + b"--BOUND--\r\n"


def extract(tmp_path, raw):
    source = tmp_path / "saved.mhtml"
    source.write_bytes(raw)
    return worker.extract(str(source)), source


def test_mhtml_explicit_late_root_keeps_original_and_inert_resources(tmp_path, monkeypatch):
    def no_network(*_args, **_kwargs):
        raise AssertionError("MHTML extraction must not open network connections")
    monkeypatch.setattr(socket, "create_connection", no_network)
    html = '<p>根正文🙂</p><script>DO_NOT_RUN</script><img src="file:///private"><a href="https://example.invalid">链接</a>'
    raw = archive([
        part(b"opaque-image", media="image/png", cid="image", location="../../secret.png"),
        part(base64.b64encode(html.encode()), encoding="base64", location="javascript:DO_NOT_RUN"),
        part(b"<p>UNSELECTED_FRAME</p>", cid="frame"),
    ])
    result, source = extract(tmp_path, raw)
    assert source.read_bytes() == raw
    assert "根正文🙂" in result["text"]
    assert "DO_NOT_RUN" not in result["text"] and "UNSELECTED_FRAME" not in result["text"]
    params = result["loss_receipt"]["params"]
    assert params["source_sha256"] == hashlib.sha256(raw).hexdigest()
    assert params["mhtml"]["root"]["path"] == ["mime-part-2"]
    assert params["mhtml"]["root"]["decoded_sha256"] == hashlib.sha256(html.encode()).hexdigest()
    assert params["mhtml"]["root"]["content_location"] == "javascript:DO_NOT_RUN"
    assert params["mhtml"]["resource_count"] == 2
    assert result["format_execution_receipt"]["original"]["format"] == "mhtml"
    assert "never archive byte offsets" in result["loss_receipt"]["loss_note"]
    assert {file.name for file in tmp_path.iterdir()} == {"saved.mhtml"}
    for anchor in result["structure"]:
        assert anchor["kind"] == "mhtml_block" and anchor["path"][0] == "mime-part-2"
        assert result["text"][anchor["char_start"]:anchor["char_end"]].strip()


@pytest.mark.parametrize("charset,encoding", [("utf-8", "base64"), ("gb18030", "quoted-printable"), ("utf-16", "base64")])
def test_mhtml_uses_declared_charset_and_transfer_encoding(tmp_path, charset, encoding):
    encoded = "<p>字符编码🙂</p>".encode(charset)
    payload = base64.b64encode(encoded) if encoding == "base64" else quopri.encodestring(encoded)
    result, _ = extract(tmp_path, archive([part(payload, media=f"text/html; charset={charset}", encoding=encoding)]))
    assert result["text"] == "字符编码🙂"
    assert result["loss_receipt"]["params"]["mhtml"]["root"]["charset"] == charset


def test_mhtml_default_root_is_first_part_not_first_later_html(tmp_path):
    result, _ = extract(tmp_path, archive([part(b"<p>FIRST</p>", encoding="7bit"), part(b"<p>LATER</p>", cid="later")], start=None))
    assert result["text"] == "FIRST"
    assert result["loss_receipt"]["params"]["mhtml"]["root_selection"] == "first-body-part"
    with pytest.raises(ValueError, match="selected root"):
        extract(tmp_path, archive([part(b"image", media="image/png", cid="image"), part(b"<p>LATER</p>")], start=None))


@pytest.mark.parametrize("fault", ["missing-start", "duplicate-id", "duplicate-location", "duplicate-type", "missing-type", "wrong-type", "non-html", "wrong-envelope", "nested-root"])
def test_mhtml_refuses_ambiguous_missing_or_unsupported_root_without_fallback(tmp_path, fault):
    parts = [part(b"<p>selected</p>"), part(b"<p>tempting fallback</p>", cid="later")]
    options = {}
    if fault == "missing-start": options["start"] = "absent"
    elif fault == "duplicate-id": parts[1] = part(b"<p>duplicate</p>")
    elif fault == "duplicate-location": parts = [part(b"<p>one</p>", location="same"), part(b"<p>two</p>", cid="later", location="same")]
    elif fault == "duplicate-type": parts[0] = b"Content-Type: text/html\r\n" + parts[0]
    elif fault == "missing-type": options["media"] = None
    elif fault == "wrong-type": options["media"] = "image/png"
    elif fault == "non-html": parts[0] = part(b"plain", media="text/plain")
    elif fault == "wrong-envelope": options["top"] = "multipart/mixed"
    elif fault == "nested-root": parts[0] = b'Content-ID: <root>\r\nContent-Type: multipart/alternative; boundary="ALT"\r\n\r\n--ALT\r\nContent-Type: text/html\r\n\r\n<p>nested</p>\r\n--ALT--'
    with pytest.raises((ValueError, email.errors.MessageError)):
        extract(tmp_path, archive(parts, **options))


@pytest.mark.parametrize("media,encoding,payload", [
    ("text/html; charset=utf-8", "base64", b"!!!not-base64!!!"),
    ("text/html; charset=utf-8", "quoted-printable", b"<p>bad=GG</p>"),
    ("text/html; charset=unknown-mhtml-charset", "8bit", b"<p>body</p>"),
    ("text/html; charset=utf-8", "8bit", b"<p>bad\xff</p>"),
    ("text/html", "8bit", "<p>未声明编码</p>".encode()),
])
def test_mhtml_invalid_encoding_never_repairs_or_selects_another_part(tmp_path, media, encoding, payload):
    raw = archive([part(payload, media=media, encoding=encoding), part(b"<p>fallback</p>", cid="other")])
    with pytest.raises((ValueError, LookupError, email.errors.MessageError)):
        extract(tmp_path, raw)


def test_mhtml_bounds_original_bytes_and_part_count(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, "MHTML_MAX_BYTES", 64)
    with pytest.raises(ValueError, match="original exceeds"):
        extract(tmp_path, b"x" * 65)
    monkeypatch.setattr(worker, "MHTML_MAX_BYTES", 16 * 1024 * 1024)
    with pytest.raises(ValueError, match="part/depth budget"):
        extract(tmp_path, archive([part(b"<p>x</p>", cid="root" if i == 0 else f"p{i}") for i in range(129)]))


def test_mhtml_depth_budget_fails_before_selecting_nested_content(tmp_path):
    nested = b"Content-Type: text/html\r\n\r\n<p>deep</p>"
    for index in range(worker.MHTML_MAX_DEPTH + 1):
        boundary = f"d{index}".encode()
        nested = b'Content-Type: multipart/related; type="text/html"; boundary="' + boundary + b'"\r\n\r\n--' + boundary + b"\r\n" + nested + b"\r\n--" + boundary + b"--\r\n"
    with pytest.raises(ValueError, match="part/depth budget"):
        extract(tmp_path, nested)


def test_additive_decoder_does_not_change_plain_html_or_ordinary_eml(tmp_path):
    html = tmp_path / "ordinary.html"
    html.write_text("<p>ordinary HTML</p><script>NOT_BODY</script>", encoding="utf-8")
    result = worker.extract(str(html))
    assert result["text"] == "ordinary HTML" and "mhtml" not in result["loss_receipt"]["params"]
    light = load("services/python-workers/document/worker_light_formats.py", "mhtml_mail_regression")
    body, facts, _ = light.parse(b"From: a@example.invalid\r\nSubject: Ordinary\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nordinary mail", "message/rfc822")
    assert body == "ordinary mail" and facts["format"] == "eml"
    assert facts["headers"]["Subject"] == "Ordinary"
