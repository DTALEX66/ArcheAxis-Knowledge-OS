"""Builtin converter plugin registration: XLSX (AXW-CAP-503).

Registers the existing ``app.ingestion.xlsx_adapter`` as a builtin
conversion plugin. The exported ``MANIFEST`` dict is compatible with
``contracts/plugin/plugin-manifest.schema.json``; ``healthcheck()`` probes
the real adapter module (importlib find_spec) without importing it.

``get_activator()`` (AXW-CAP-503 step 2) returns the activator callable
for ``CapabilityStore.install_builtin()``: invoking it wraps the REAL
``app.ingestion.xlsx_adapter.convert_xlsx`` function into a
store-callable ``FileConverter`` (convert(source_path, options) ->
AdapterResult) and registers it with ``app.capability.conversion`` so
``ConversionDispatcher.get_converter()`` can dispatch it. Conversion
failures raise ``ConverterError`` (fail-closed, never a fake result).
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable
from typing import Any

from app.capability.conversion import FileConverter, make_file_converter, register_active_converter

ADAPTER_MODULE = "app.ingestion.xlsx_adapter"
ENTRY_POINT = f"{ADAPTER_MODULE}:convert_xlsx"
ADAPTER_FUNCTION = "convert_xlsx"

MANIFEST: dict[str, Any] = {
    "manifest_version": "1.0",
    "plugin_id": "ax.builtin.converter.xlsx",
    "name": "XLSX Converter (builtin)",
    "version": "1.0.0",
    "api_contract": "1.x",
    "permissions": ["files.read"],
    "platform": {"os": "windows", "arch": "x86_64"},
    "entry": ENTRY_POINT,
    "data_ownership": {
        "declared": True,
        "note": "converts user-provided .xlsx/.csv files; cell-semantic blocks are stored in the workspace vault",
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
    REAL ``app.ingestion.xlsx_adapter.convert_xlsx`` function and
    registers it with ``app.capability.conversion``. Re-invocation is
    idempotent (re-registration replaces the same plugin_id).
    """

    def activate() -> FileConverter:
        service = make_file_converter(
            plugin_id=MANIFEST["plugin_id"],
            name=MANIFEST["name"],
            adapter_module=ADAPTER_MODULE,
            adapter_function=ADAPTER_FUNCTION,
        )
        register_active_converter(MANIFEST["plugin_id"], service)
        return service

    return activate
