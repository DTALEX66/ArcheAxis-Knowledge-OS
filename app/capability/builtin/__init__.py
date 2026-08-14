"""Builtin conversion plugins (AXW-CAP-503).

Each module in this package registers one existing ingestion adapter
(docx/html/media/ocr/pptx/xlsx) as a plugin manifest compatible with
``contracts/plugin/plugin-manifest.schema.json`` and exposes a
``healthcheck()`` probe that verifies the real adapter module is
importable. ``discover()`` validates every manifest fail-closed and
returns ``PluginManifest`` objects ready for
``CapabilityStore.install_builtin()``.
"""

from __future__ import annotations

from typing import Any

from shared.plugin_manifest import PluginManifest, load_manifest_from_mapping, validate

from . import (
    converters_docx,
    converters_html,
    converters_media,
    converters_ocr,
    converters_pptx,
    converters_xlsx,
)

_CONVERTER_MODULES: tuple[Any, ...] = (
    converters_docx,
    converters_html,
    converters_media,
    converters_ocr,
    converters_pptx,
    converters_xlsx,
)


def discover() -> list[PluginManifest]:
    """Return validated manifests for every builtin converter plugin.

    Fail-closed: a broken builtin manifest (invalid permissions, missing
    fields, ...) raises ValueError instead of being silently skipped.
    """
    manifests: list[PluginManifest] = []
    for module in _CONVERTER_MODULES:
        raw = module.MANIFEST
        validate(raw)
        manifests.append(load_manifest_from_mapping(raw))
    return manifests


def healthcheck_all() -> list[dict[str, Any]]:
    """Run every builtin plugin's healthcheck probe."""
    return [module.healthcheck() for module in _CONVERTER_MODULES]
