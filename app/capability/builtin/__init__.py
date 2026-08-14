"""Builtin conversion plugins (AXW-CAP-503).

Each module in this package registers one existing ingestion adapter
(docx/html/media/ocr/pptx/xlsx) as a plugin manifest compatible with
``contracts/plugin/plugin-manifest.schema.json`` and exposes a
``healthcheck()`` probe that verifies the real adapter module is
importable. ``discover()`` validates every manifest fail-closed and
returns ``PluginManifest`` objects ready for
``CapabilityStore.install_builtin()``.

Activator wiring (AXW-CAP-503 step 2): every module also exposes
``get_activator()`` — the callable for
``CapabilityStore.install_builtin(manifest, activator)`` that wraps the
REAL adapter conversion function into a store-callable ``FileConverter``
registered with ``app.capability.conversion``.
``activate_all_builtins(store)`` installs and activates all six plugins;
it is restart-safe (re-running it on a store that already has the packs
installed still registers the in-process converters, which
``install_builtin`` alone skips on its idempotent path).

Main-chain integration point (documented, not wired): the conversion
main chain lives in ``app.ingestion.multi_format.convert_file`` (used by
``app.workspace.router: POST /api/batch/import``). A caller holding a
:class:`~app.capability.conversion.ConversionDispatcher` should prefer an
active converter for a format and fall back to the engine chain only
when ``get_converter()`` returns None. That wiring is deliberately not
applied to the existing endpoints yet — the engine chain is exercised
by many tests and the store is not currently instantiated there; adding
the plugin path is a separate, reviewed change.
"""

from __future__ import annotations

from typing import Any

from app.capability.conversion import get_active_converter
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


def activate_all_builtins(store: Any) -> list[str]:
    """Install + activate every builtin converter plugin (idempotent).

    Returns the activated plugin_ids in manifest order. On a fresh store
    each ``install_builtin`` invokes the module activator exactly once,
    which registers the real-adapter converter service with
    ``app.capability.conversion``. On a store that already has the packs
    installed (e.g. re-created after a restart) ``install_builtin`` is
    idempotent and skips the activator, so the activator is re-run
    explicitly here — otherwise the in-process converter would never be
    registered and dispatch would fail-closed to None.
    """
    activated: list[str] = []
    for module in _CONVERTER_MODULES:
        plugin_id = module.MANIFEST["plugin_id"]
        store.install_builtin(load_manifest_from_mapping(module.MANIFEST), module.get_activator())
        if get_active_converter(plugin_id) is None:
            # install_builtin idempotent path skips the activator; run it
            # so this process actually has the converter service.
            module.get_activator()()
        activated.append(plugin_id)
    return activated
