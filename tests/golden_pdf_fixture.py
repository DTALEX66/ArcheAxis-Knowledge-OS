"""Deterministic Golden Journey PDF fixture with text, a table and an image."""
from __future__ import annotations

import hashlib


def build_golden_pdf() -> bytes:
    """Return a valid one-page PDF using only stable PDF 1.4 primitives."""
    content = b"\n".join(
        (
            b"BT /F1 22 Tf 72 720 Td (Golden Journey Evidence) Tj ET",
            b"BT /F1 12 Tf 72 685 Td (Original SHA and anchored conversion) Tj ET",
            b"72 560 300 80 re S",
            b"172 560 m 172 640 l S",
            b"72 600 m 372 600 l S",
            b"BT /F1 11 Tf 82 615 Td (Criterion) Tj ET",
            b"BT /F1 11 Tf 192 615 Td (Verified) Tj ET",
            b"BT /F1 11 Tf 82 575 Td (Page Anchor) Tj ET",
            b"BT /F1 11 Tf 192 575 Td (PASS) Tj ET",
            b"q 24 0 0 24 430 600 cm /Im1 Do Q",
        )
    )
    objects = (
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> /XObject << /Im1 6 0 R >> >> "
        b"/Contents 4 0 R >>",
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /XObject /Subtype /Image /Width 1 /Height 1 /ColorSpace /DeviceGray "
        b"/BitsPerComponent 8 /Length 1 >>\nstream\n\x80\nendstream",
    )
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode("ascii"))
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    output.extend(b"".join(f"{offset:010d} 00000 n \n".encode("ascii") for offset in offsets[1:]))
    output.extend(
        b"trailer\n<< /Size "
        + str(len(objects) + 1).encode("ascii")
        + b" /Root 1 0 R >>\nstartxref\n"
        + str(xref).encode("ascii")
        + b"\n%%EOF\n"
    )
    return bytes(output)


GOLDEN_PDF = build_golden_pdf()
GOLDEN_PDF_SHA256 = "0f0ffc50c79d9d977efb925351ca1d64a063184e4bdd71507b9ac44992f7adcf"


def test_fixture_identity_is_stable() -> None:
    assert hashlib.sha256(GOLDEN_PDF).hexdigest() == GOLDEN_PDF_SHA256
