"""One place that names a Windows path so the file API still creates it.

Measured on this volume (2026-10-07): a plain create starts failing at a total length of 252
characters - 251 succeeds - and the refusal arrives as ``ERROR_FILE_NOT_FOUND`` /
``FileNotFoundError``, which reads as "the directory vanished" rather than "the name is too
long". Twelve extra characters of workspace root are enough to move a passing suite into
failing one, so this is ordinary install-path behaviour, not an exotic-path concern.

There is deliberately **no length threshold here.** A threshold measured on the directory
reproduces the bug it is meant to prevent: a raw-asset store root of 194 characters is well
under every plausible limit, and the file the store then creates is
``.{64-character digest}.tmp`` - 261 characters, refused. Only the caller knows how long the
final name will be, and several of these calls (``mkstemp``, ``NamedTemporaryFile``) generate
the name themselves. The Rust core already names its SQLite path verbatim for the same reason
(``launch.rs`` notes that ``\\?\\D:\\...`` names the same local drive path), so an always-on
prefix is the existing product convention rather than a new one.

The prefix is an input/output detail, so the two helpers are deliberately asymmetric:

* `native_path` is called at the moment of the system call, **after** any containment or
  name validation, because the verbatim form bypasses the normalisation those checks rely on;
* `ordinary_path` is called before a path reaches a record, a manifest, a returned payload
  or anything hashed for identity, because a leaked prefix would silently change a stored
  value and, for a workspace identity, would re-identify every existing workspace.

`services/python-workers/transport/text_ndjson.py` uses the same pair at the worker boundary.
This module is the shared home so the `app/` surface stops inventing it per call site.
"""

from __future__ import annotations

import os
from pathlib import Path

VERBATIM_PREFIX = "\\\\?\\"


def native_path(path: Path | str) -> str:
    """The same absolute path in the form the Windows file API opens at any depth."""
    text = str(path)
    if os.name == "nt" and not text.startswith(VERBATIM_PREFIX) and Path(text).is_absolute():
        return VERBATIM_PREFIX + text
    return text


def ordinary_path(path: Path | str) -> Path:
    """Strip the input/output prefix so a path can be stored, returned or hashed."""
    text = str(path)
    if text.startswith(VERBATIM_PREFIX):
        text = text[len(VERBATIM_PREFIX):]
    return Path(text)


def sqlite_readonly_target(path: Path | str) -> tuple[str, bool]:
    """Where SQLite should open `path` read-only, and whether that is a URI.

    A verbatim prefix is meaningless inside a ``file:`` URI, so the two read-only mechanisms
    cannot both be used. A path that needs the prefix is opened by name with SQLite's own
    ``query_only`` guard instead - the caller must run that pragma when this returns ``False``.
    This is the choice `shared.backup` already made for backups; it lives here so the reader
    side stops inventing its own.
    """
    resolved = Path(path).resolve() if isinstance(path, Path) else Path(path)
    native = native_path(resolved)
    if native != str(resolved):
        return native, False
    return f"{Path(str(resolved)).as_uri()}?mode=ro", True
