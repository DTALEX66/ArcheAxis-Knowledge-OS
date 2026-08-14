"""Converter dispatch for the Capability Store (AXW-CAP-503, step 2).

This module turns *registered* builtin converter plugins into *usable*
conversion services. It is the plug-in seam for the conversion main
chain:

    app.ingestion.multi_format.convert_file()  (engine chain _ENGINES)
    app.workspace.router: POST /api/batch/import  (convert_directory_resumable)

Integration point (documented, NOT wired into those endpoints yet):
a caller that holds a :class:`ConversionDispatcher` (bound to a
:class:`~app.capability.store.CapabilityStore`) should prefer
``dispatcher.get_converter(plugin_id).convert(source, options)`` for an
installed-and-activated plugin, and fall back to the engine chain only
when it returns ``None``. Wired that way, an active converter is
honoured and an inactive/unknown plugin degrades to the built-in
engines — never to a silent fake conversion.

Activation model
----------------
* ``CapabilityStore.install_builtin(manifest, activator)`` invokes the
  activator exactly once per fresh install and stores it in memory.
* Each builtin converter module's activator builds a
  :class:`FileConverter` that wraps the REAL adapter function from
  ``app.ingestion.<adapter>`` and registers it here via
  :func:`register_active_converter`.
* A converter is *active* only after its activator ran in this
  process. ``get_converter()`` returns ``None`` for anything else
  (fail-closed; no silent fallback).

Fail-closed guarantees
----------------------
* :class:`ConverterError` is raised when an active converter cannot
  convert: adapter reported failure, adapter raised, unknown options,
  or a wrong return type. No fake success is ever produced.
* Unknown ``options`` keys are refused (each plugin declares the exact
  option keys that map 1:1 onto its real adapter's keyword arguments).
"""

from __future__ import annotations

import importlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shared.adapter_contract import AdapterResult


class ConverterError(RuntimeError):
    """Fail-closed error: an active converter could not perform a conversion."""


@dataclass(frozen=True)
class FileConverter:
    """A store-callable conversion service wrapping one real adapter function.

    ``convert(source_path, options=None)`` invokes the real adapter
    (e.g. ``app.ingestion.docx_adapter.convert_docx``) with the
    adapter's own keyword arguments and returns its ``AdapterResult``
    on success. Any failure — adapter ``success=False``, adapter
    exception, unknown options, unexpected return type — raises
    :class:`ConverterError` (fail-closed, never a fake result).

    The instance itself is callable (``service(path)``) as a shorthand
    for ``service.convert(path)``.
    """

    plugin_id: str
    name: str
    convert: Callable[[str | Path, dict[str, Any] | None], AdapterResult]

    def __call__(
        self, source_path: str | Path, options: dict[str, Any] | None = None
    ) -> AdapterResult:
        return self.convert(source_path, options)


# ── Runtime registry of active converters ─────────────────────────────────
# Populated by the builtin activator implementations (side effect of
# CapabilityStore.install_builtin). Process-local by design: activation
# is an in-memory event; a fresh store must re-run activation (see
# app.capability.builtin.activate_all_builtins for the restart-safe path).

_ACTIVE: dict[str, FileConverter] = {}


def register_active_converter(plugin_id: str, service: FileConverter) -> None:
    """Register (or refresh) the active converter for ``plugin_id``.

    Idempotent: re-registering the same plugin_id replaces the entry.
    """
    if not plugin_id or not service:
        raise ConverterError("register_active_converter requires a plugin_id and a service")
    _ACTIVE[plugin_id] = service


def get_active_converter(plugin_id: str) -> FileConverter | None:
    """Return the active converter for ``plugin_id``, or None (fail-closed)."""
    return _ACTIVE.get(plugin_id)


def list_active() -> list[str]:
    """Return plugin_ids of converters activated in this process (sorted)."""
    return sorted(_ACTIVE)


def reset_active_converters() -> None:
    """Clear the in-process active-converter registry.

    Test/admin utility: lets hermetic test suites and runtime reloads
    start from a clean activation state. Activation is re-established by
    re-running the plugin activators (e.g. ``activate_all_builtins``).
    """
    _ACTIVE.clear()


# ── Service factory (used by every builtin activator) ─────────────────────


def make_file_converter(
    *,
    plugin_id: str,
    name: str,
    adapter_module: str,
    adapter_function: str,
    allowed_options: tuple[str, ...] = (),
) -> FileConverter:
    """Build a FileConverter that calls the REAL adapter function.

    Args:
        plugin_id: plugin identifier used in error messages and dispatch.
        name: human-readable converter name.
        adapter_module: dotted module, e.g. ``app.ingestion.docx_adapter``.
        adapter_function: the real function name inside that module, e.g.
            ``convert_docx``. The adapter module is imported lazily on the
            first convert call, so registering the plugin never pulls in
            adapter dependencies.
        allowed_options: option keys passed straight through as keyword
            arguments to the adapter function. Keys must match the real
            adapter signature (e.g. ``("lang",)`` for convert_ocr,
            ``("work_dir",)`` for convert_media). Unknown keys are
            refused fail-closed.
    """

    def _adapter() -> Callable[..., AdapterResult]:
        try:
            module = importlib.import_module(adapter_module)
        except Exception as exc:  # pragma: no cover - environment dependent
            raise ConverterError(
                f"{plugin_id}: adapter module not importable: {adapter_module} ({exc})"
            ) from exc
        fn = getattr(module, adapter_function, None)
        if not callable(fn):
            raise ConverterError(
                f"{plugin_id}: adapter function missing/not callable: {adapter_module}.{adapter_function}"
            )
        return fn

    def convert(source_path: str | Path, options: dict[str, Any] | None = None) -> AdapterResult:
        if options is None:
            opts: dict[str, Any] = {}
        elif isinstance(options, Mapping):
            opts = dict(options)
        else:
            raise ConverterError(
                f"{plugin_id}: options must be a mapping, got {type(options).__name__}"
            )
        unknown = set(opts) - set(allowed_options)
        if unknown:
            raise ConverterError(
                f"{plugin_id}: unsupported conversion option(s) {sorted(unknown)}; "
                f"supported: {sorted(allowed_options)}"
            )
        try:
            result: AdapterResult = _adapter()(str(source_path), **opts)
        except ConverterError:
            raise
        except Exception as exc:  # pragma: no cover - adapter may raise on bad input
            raise ConverterError(
                f"{plugin_id}: adapter {adapter_module}.{adapter_function} raised: {exc}"
            ) from exc
        if not isinstance(result, AdapterResult):
            raise ConverterError(
                f"{plugin_id}: adapter returned unexpected type {type(result).__name__}; "
                "refusing to fabricate a conversion result"
            )
        if not result.success:
            raise ConverterError(
                f"{plugin_id}: conversion failed: {result.error or 'adapter reported no error detail'}"
            )
        return result

    return FileConverter(plugin_id=plugin_id, name=name, convert=convert)


# ── Store-bound dispatch (fail-closed) ────────────────────────────────────


class ConversionDispatcher:
    """Dispatch active builtin converter plugins for one CapabilityStore.

    A plugin is dispatched only when BOTH hold: its record is
    ``installed`` in the store AND its activator ran in this process
    (registered an active converter). Everything else resolves to
    ``None`` — the caller keeps the built-in engine chain as the
    explicit fallback, never a silent fake conversion.
    """

    def __init__(self, store: Any) -> None:
        # Duck-typed: any object exposing list_installed() works, which
        # keeps this module free of a hard dependency on the store.
        self._store = store

    def get_converter(self, plugin_id: str) -> FileConverter | None:
        """Return the active convert callable for ``plugin_id``, or None.

        None means: plugin not installed, or installed but not activated
        in this process. Fail-closed: never silently substitutes another
        converter.
        """
        installed = {record.plugin_id for record in self._store.list_installed()}
        if plugin_id not in installed:
            return None
        return get_active_converter(plugin_id)

    def list_active_converters(self) -> list[str]:
        """Sorted plugin_ids of installed AND activated converters."""
        installed = {record.plugin_id for record in self._store.list_installed()}
        return sorted(plugin_id for plugin_id in list_active() if plugin_id in installed)


def get_converter(store: Any, plugin_id: str) -> FileConverter | None:
    """Module-level shorthand for ``ConversionDispatcher(store).get_converter(...)``."""
    return ConversionDispatcher(store).get_converter(plugin_id)


def list_active_converters(store: Any) -> list[str]:
    """Module-level shorthand for ``ConversionDispatcher(store).list_active_converters()``."""
    return ConversionDispatcher(store).list_active_converters()
