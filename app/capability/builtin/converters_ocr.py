"""Builtin converter plugin registration: OCR (AXW-CAP-503).

Registers the existing ``app.ingestion.ocr_adapter`` as a builtin
conversion plugin. The exported ``MANIFEST`` dict is compatible with
``contracts/plugin/plugin-manifest.schema.json``; ``healthcheck()`` probes
the real adapter module (importlib find_spec) without importing it.
"""

from __future__ import annotations

import importlib.util
from typing import Any

ADAPTER_MODULE = "app.ingestion.ocr_adapter"
ENTRY_POINT = f"{ADAPTER_MODULE}:convert_ocr"

MANIFEST: dict[str, Any] = {
    "manifest_version": "1.0",
    "plugin_id": "ax.builtin.converter.ocr",
    "name": "OCR Converter (builtin)",
    "version": "1.0.0",
    "api_contract": "1.x",
    "permissions": ["files.read", "process"],
    "platform": {"os": "windows", "arch": "x86_64"},
    "entry": ENTRY_POINT,
    "data_ownership": {
        "declared": True,
        "note": "OCR of user-provided images/PDF pages; extracted text with page anchors is stored in the workspace vault",
    },
    "healthcheck": f"import:{ADAPTER_MODULE}",
}


def healthcheck() -> dict[str, Any]:
    """Probe that the underlying adapter module is importable (never imports it)."""
    plugin_id = MANIFEST["plugin_id"]
    if importlib.util.find_spec(ADAPTER_MODULE) is None:
        return {
            "ok": False,
            "plugin_id": plugin_id,
            "detail": f"adapter module not importable: {ADAPTER_MODULE}",
        }
    return {
        "ok": True,
        "plugin_id": plugin_id,
        "detail": f"adapter module importable: {ADAPTER_MODULE}",
    }
