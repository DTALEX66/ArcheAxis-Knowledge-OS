"""Resolve a worker's external tool and model paths from the declared registry.

R6 A02 requires a *tool resolver*, a *model resolver*, *external capability registry*
and **exact paths**, and it forbids PATH guessing. `services/python-workers` never
received one, so the workers guessed instead:

* `vision/worker_ocr.py` called `shutil.which("tesseract")` and derived the binary
  from `TESSDATA_PREFIX`;
* `media/worker_video.py` called `shutil.which("ffmpeg")`;
* `media/worker_transcribe.py` derived a model directory from the checkout's parent.

On a machine where all three are installed and already declared in
`config/environment/capability-requirements.yaml`, every one of them reported "not
found" - not because an engine was missing, but because nothing read the declaration.

This module resolves a declared entry to a concrete, existing path. It is
deliberately small and dependency-light because the workers are launched as
standalone scripts with no package import path.

Resolution order, highest first:

1. an explicit per-tool environment override (`TESSERACT_CMD`, `FFMPEG_CMD`,
   `ARCHEAXIS_ASR_MODEL_DIR`, ...);
2. the declared `external_paths` in the capability manifest, resolved relative to
   the declared external root.

A declared path may not be absolute and may not escape the external root. When
nothing resolves, the failure names the tool and says what was consulted; it never
substitutes a different binary found on `PATH`, because a silent substitution is
how a wrong engine gets used without anyone noticing.

`guess_on_path=True` exists only so a caller can *report* what PATH would have
offered; it is not the resolution path and is never the default.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

MANIFEST_ENV = "ARCHEAXIS_CAPABILITY_MANIFEST"
_ROOT_ENV = ("ARCHEAXIS_EXTERNAL_ROOT", "OS_EXTERNAL_CONFIG")

# The manifest lives in the checkout; this file is at services/python-workers/.
DEFAULT_MANIFEST = (Path(__file__).resolve().parents[2]
                    / "config" / "environment" / "capability-requirements.yaml")

# Explicit per-tool overrides, so an operator can point at a specific install
# without editing the declaration.
OVERRIDES = {
    "tesseract": ("TESSERACT_CMD", "ARCHEAXIS_TESSERACT_CMD"),
    "ffmpeg": ("FFMPEG_CMD", "ARCHEAXIS_FFMPEG_CMD"),
    "faster-whisper-large-v3-turbo": ("ARCHEAXIS_ASR_MODEL_DIR",),
    "faster-whisper-base": ("ARCHEAXIS_ASR_MODEL_DIR",),
}


class ToolNotFound(RuntimeError):
    """A declared tool or model could not be resolved to an existing path."""


class ManifestUnreadable(RuntimeError):
    """The declared capability manifest exists but could not be read or parsed.

    Distinct from `ToolNotFound` on purpose. The manifest is how a declared engine is
    found, so failing to read it is a different fault from a tool that is genuinely not
    declared - and reporting the first as the second is how a missing parser or an
    unreadable file turns into "engine not installed" and sends someone looking in the
    wrong place.
    """


def _external_root() -> Path | None:
    for name in _ROOT_ENV:
        raw = os.environ.get(name, "").strip()
        if not raw:
            continue
        root = Path(raw)
        if root.is_absolute():
            return root
    return None


def _manifest_path() -> Path:
    """The declared capability manifest, in the tree this module is running from.

    `default` is where the file sits relative to this module in the source tree
    (`<repo>/services/python-workers/` -> `<repo>/config/environment/`). A staged runtime
    ships it beside the workers instead (`<root>/config/environment/`), so that is tried
    first; without it a staged OCR job reported "tesseract binary not found on PATH" even
    though the engine is installed and declared.
    """
    raw = os.environ.get(MANIFEST_ENV, "").strip()
    if raw:
        return Path(raw)
    here = Path(__file__).resolve()
    beside = here.parent.parent / "config" / "environment" / "capability-requirements.yaml"
    if beside.is_file():
        return beside
    return here.parents[2] / "config" / "environment" / "capability-requirements.yaml"


def _declared_entries(manifest: Path) -> list[dict]:
    """The declared capability entries.

    An absent manifest means nothing is declared. A manifest that is present but cannot
    be read is a different matter and raises: the resolver needs a YAML parser, and
    without one every declared engine would silently look undeclared. That is how a
    runtime interpreter lacking PyYAML reported "tesseract binary not found on PATH" for
    an installed, declared engine.
    """
    if not manifest.is_file():
        return []
    try:
        import yaml
    except ImportError as error:
        raise ManifestUnreadable(
            f"{manifest}: no YAML parser available ({error}); install PyYAML so declared "
            "capabilities can be read"
        ) from error
    try:
        text = manifest.read_text(encoding="utf-8")
    except OSError as error:
        raise ManifestUnreadable(f"{manifest}: cannot be read ({error})") from error
    try:
        data = yaml.safe_load(text) or {}
    except Exception as error:  # noqa: BLE001 - a parse failure is not a missing tool
        raise ManifestUnreadable(f"{manifest}: cannot be parsed ({error})") from error
    entries: list[dict] = []
    for group in (data.get("capabilities") or {}).values():
        for entry in group or []:
            if isinstance(entry, dict):
                entries.append(entry)
    return entries


def _candidates(name: str, manifest: Path) -> list[Path]:
    root = _external_root()
    found: list[Path] = []
    for entry in _declared_entries(manifest):
        if entry.get("name") != name:
            continue
        for candidate in entry.get("external_paths") or []:
            if not isinstance(candidate, str) or not candidate.strip():
                continue
            relative = Path(candidate)
            # A declaration may only name a location inside the declared root.
            if relative.is_absolute() or ".." in relative.parts:
                continue
            if root is None:
                continue
            path = root / relative
            if path.is_file() or path.is_dir():
                found.append(path)
    return found


def tool_path(name: str, *, guess_on_path: bool = False) -> str:
    """The existing path for a declared tool or model, or a named failure.

    Never invents a location and never silently substitutes another binary.
    """
    if not name or not name.strip():
        raise ToolNotFound("a tool name is required")

    for variable in OVERRIDES.get(name, ()):
        raw = os.environ.get(variable, "").strip()
        if raw:
            path = Path(raw)
            if path.is_file() or path.is_dir():
                return str(path)
            raise ToolNotFound(
                f"{name}: {variable} names a path that does not exist: {raw}")

    manifest = _manifest_path()
    for path in _candidates(name, manifest):
        return str(path)

    consulted = [var for var in OVERRIDES.get(name, ())] + [
        f"{MANIFEST_ENV} or {DEFAULT_MANIFEST}",
        f"external root from {' / '.join(_ROOT_ENV)}",
    ]
    hint = ""
    if guess_on_path:
        found = shutil.which(name)
        hint = f"; PATH would offer {found}" if found else "; PATH offers nothing"
    raise ToolNotFound(
        f"{name}: no declared path resolved (consulted: {', '.join(consulted)}){hint}")


def declared_path(name: str) -> str | None:
    """`tool_path(name)`, or None when there is simply no declaration.

    Only `ToolNotFound` becomes None, so a worker keeps its own fallback when nothing is
    declared. `ManifestUnreadable` propagates: a declaration that cannot be read is a
    fault to report, not a tool that is absent.
    """
    try:
        return tool_path(name)
    except ToolNotFound:
        return None


def transport_path(worker_file: str) -> Path:
    """The NDJSON transport a standalone worker must load, from the worker's own file.

    Two layouts place the shared transport next to a worker's own category directory,
    and both are in live use:

    * the source tree:  `<repo>/services/python-workers/document/worker_x.py`
      with the transport at `<repo>/services/python-workers/transport/text_ndjson.py`;
    * a staged runtime: `<root>/workers/document/worker_x.py`
      with the transport at `<root>/workers/transport/text_ndjson.py`
      (that is the layout `stage_backend_runtime.py` produces and the one the Core's
      own `TEXT_WORKER_RELATIVE` names).

    The workers derived the first from a fixed `parents[3]` and then appended
    `services/python-workers/transport/...`, so a staged run died with
    `FileNotFoundError` before the worker could serve anything. Deriving from the
    worker's own file makes the source case exact, and the sibling case covers the
    staged tree, so neither layout needs a depth constant kept in sync.

    Returns the staged-shell sibling when neither candidate exists, so a caller still
    gets a named path to report rather than a silent wrong one.
    """
    here = Path(worker_file).resolve()
    source_form = here.parent.parent.parent / "services" / "python-workers" / "transport" / "text_ndjson.py"
    sibling_form = here.parent.parent / "transport" / "text_ndjson.py"
    if sibling_form.is_file():
        return sibling_form
    if source_form.is_file():
        return source_form
    return sibling_form


def resolve(name: str) -> str | None:
    """Load this module by file path and resolve *name*; None when unresolvable."""
    module = _load_self()
    return None if module is None else module.declared_path(name)


def declared(name: str, worker_file: str) -> str | None:
    """The declared path for *name*, loading this module from the worker's own tree.

    The single call a worker makes. A worker runs as a standalone script with no package
    import path, so it locates the sibling `tool_paths.py` instead. Only a missing
    declaration returns None: a manifest that exists but cannot be read propagates, since
    a worker that quietly treated "cannot read the declaration" as "not declared" would
    report a missing engine for an installed one.
    """
    module_path = Path(worker_file).resolve().parent.parent / "tool_paths.py"
    if not module_path.is_file():
        return None
    import importlib.util

    spec = importlib.util.spec_from_file_location("worker_tool_paths", module_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.declared_path(name)


def _load_self():
    """This module, loaded by file path (see `resolve`)."""
    import importlib.util

    module_path = Path(__file__).resolve()
    spec = importlib.util.spec_from_file_location("worker_tool_paths", module_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
