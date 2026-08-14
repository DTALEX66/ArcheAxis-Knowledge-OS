"""Builtin converter plugin registration: media (AXW-CAP-503).

Registers the existing ``app.ingestion.media_adapter`` as a builtin
conversion plugin. The exported ``MANIFEST`` dict is compatible with
``contracts/plugin/plugin-manifest.schema.json``; ``healthcheck()`` probes
the real adapter module (importlib find_spec) without importing it.

``get_activator()`` (AXW-CAP-503 step 2) returns the activator callable
for ``CapabilityStore.install_builtin()``: invoking it wraps the REAL
``app.ingestion.media_adapter.convert_media`` function into a
store-callable ``FileConverter`` (convert(source_path, options) ->
AdapterResult) and registers it with ``app.capability.conversion`` so
``ConversionDispatcher.get_converter()`` can dispatch it. The single
supported option key ``work_dir`` maps 1:1 onto the adapter's own
``work_dir`` keyword argument; any other key is refused fail-closed.
Conversion failures raise ``ConverterError`` (never a fake result).
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable
from typing import Any

from app.capability.conversion import FileConverter, make_file_converter, register_active_converter

ADAPTER_MODULE = "app.ingestion.media_adapter"
ENTRY_POINT = f"{ADAPTER_MODULE}:convert_media"
ADAPTER_FUNCTION = "convert_media"
ALLOWED_OPTIONS: tuple[str, ...] = ("work_dir",)

MANIFEST: dict[str, Any] = {
    "manifest_version": "1.0",
    "plugin_id": "ax.builtin.converter.media",
    "name": "Media Transcriber (builtin)",
    "version": "1.0.0",
    "api_contract": "1.x",
    "permissions": ["files.read", "process"],
    "platform": {"os": "windows", "arch": "x86_64"},
    "entry": ENTRY_POINT,
    "data_ownership": {
        "declared": True,
        "note": "transcribes user-provided audio/video; time-anchored transcript blocks are stored in the workspace vault",
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


def get_activator() -> Callable[[], FileConverter]:
    """Return the activator for ``CapabilityStore.install_builtin()``.

    The returned callable builds the converter service that wraps the
    REAL ``app.ingestion.media_adapter.convert_media`` function and
    registers it with ``app.capability.conversion``. Re-invocation is
    idempotent (re-registration replaces the same plugin_id).
    """

    def activate() -> FileConverter:
        service = make_file_converter(
            plugin_id=MANIFEST["plugin_id"],
            name=MANIFEST["name"],
            adapter_module=ADAPTER_MODULE,
            adapter_function=ADAPTER_FUNCTION,
            allowed_options=ALLOWED_OPTIONS,
        )
        register_active_converter(MANIFEST["plugin_id"], service)
        return service

    return activate
