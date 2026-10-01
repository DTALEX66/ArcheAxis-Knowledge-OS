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
    raw = os.environ.get(MANIFEST_ENV, "").strip()
    return Path(raw) if raw else DEFAULT_MANIFEST


def _declared_entries(manifest: Path) -> list[dict]:
    if not manifest.is_file():
        return []
    try:
        import yaml
    except ImportError:  # pragma: no cover - reported as an unresolved tool
        return []
    try:
        data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    except (OSError, ValueError):
        return []
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
    """`tool_path(name)`, or None when it cannot be resolved.

    For a worker call site that must keep its existing fallback when there is no
    declaration at all, but must still prefer a declared path when there is one.
    """
    try:
        return tool_path(name)
    except Exception:  # noqa: BLE001 - unresolved is not an error at this layer
        return None


def resolve(name: str) -> str | None:
    """Load this module by file path and resolve *name*; None when unresolvable.

    The single call a worker makes. A worker is executed as a standalone script
    (`python -B worker.py --staging-root ...`) with no package import path, so it
    cannot `import tool_paths`; it locates the sibling file instead. Loading here
    rather than in each worker keeps the dependency direction one way.
    """
    import importlib.util

    module_path = Path(__file__).resolve()
    if not module_path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("worker_tool_paths", module_path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.declared_path(name)
    except Exception:  # noqa: BLE001 - a worker keeps its own fallback
        return None
