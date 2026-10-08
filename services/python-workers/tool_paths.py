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
    "antiword": ("ARCHEAXIS_ANTIWORD_CMD",),
    "chromium": ("ARCHEAXIS_CHROMIUM_CMD",),
    "zulu-jre": ("ARCHEAXIS_JAVA_CMD",),
    "apache-tika": ("ARCHEAXIS_TIKA_JAR",),
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


class PlatformUnavailable(RuntimeError):
    """The resource is declared for a platform this host is not.

    A cross-platform contract has to say which platform it is refusing, and name what was
    consulted, instead of returning an empty answer that reads like a missing install.
    """


def _external_root() -> Path | None:
    for name in _ROOT_ENV:
        raw = os.environ.get(name, "").strip()
        if not raw:
            continue
        root = Path(raw)
        if root.is_absolute():
            return root
    # A locally staged artifact can name the explicitly selected shared root.
    # This declaration travels inside workers/, so the desktop resource mapping
    # retains it; no global config or source manifest is modified.
    staged = Path(__file__).resolve().parent / "capability-requirements.yaml"
    if staged.is_file():
        try:
            import yaml
            document = yaml.safe_load(staged.read_text(encoding="utf-8")) or {}
            raw = document.get("artifact_external_root")
        except (OSError, ValueError, ImportError) as error:
            raise ManifestUnreadable("staged external-root declaration is unreadable") from error
        if raw:
            root = Path(raw)
            if root.is_absolute() and not str(root).lower().startswith(("e:", "\\\\")):
                return root
            raise ManifestUnreadable("staged external-root declaration is not an allowed absolute local path")
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
    worker_resource = here.parent / "capability-requirements.yaml"
    if worker_resource.is_file():
        return worker_resource
    beside = here.parent.parent / "config" / "environment" / "capability-requirements.yaml"
    if beside.is_file():
        return beside
    return here.parents[2] / "config" / "environment" / "capability-requirements.yaml"


def _manifest_document(manifest: Path) -> dict:
    """The parsed manifest, or `{}` when there is simply no manifest.

    An absent manifest means nothing is declared. A manifest that is present but cannot be read is
    a different matter and raises: the resolver needs a YAML parser, and without one every declared
    engine would silently look undeclared. That is how a runtime interpreter lacking PyYAML reported
    "tesseract binary not found on PATH" for an installed, declared engine.
    """
    if not manifest.is_file():
        return {}
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
        return yaml.safe_load(text) or {}
    except Exception as error:  # noqa: BLE001 - a parse failure is not a missing tool
        raise ManifestUnreadable(f"{manifest}: cannot be parsed ({error})") from error


def _declared_entries(manifest: Path) -> list[dict]:
    """The declared capability entries."""
    entries: list[dict] = []
    for group in (_manifest_document(manifest).get("capabilities") or {}).values():
        for entry in group or []:
            if isinstance(entry, dict):
                entries.append(entry)
    return entries


SIBLING_ROOTS_KEY = "sibling_roots"


def sibling_roots(root: Path, manifest: Path) -> dict[str, Path]:
    """The declared sibling roots beside the external root, by name.

    Some shared resources live *beside* the external root rather than inside it — the model library
    is the real case. Naming those roots here is what lets a declaration reach them without turning
    the external root into a boundary that `..` walks straight through: a traversal in
    `external_paths` is still refused, and an entry reaches a sibling only through a root this
    manifest names.

    A sibling root must step exactly one level up and then down into one directory, and it must
    exist. `../../etc` and `..` alone are refused, so the set of reachable places stays the declared
    one rather than "anywhere the process can read".
    """
    declared = _manifest_document(manifest).get(SIBLING_ROOTS_KEY) or {}
    if not isinstance(declared, dict):
        raise ManifestUnreadable(f"{manifest}: {SIBLING_ROOTS_KEY} must be a mapping")
    resolved: dict[str, Path] = {}
    for name, relative in declared.items():
        if not isinstance(name, str) or not isinstance(relative, str):
            raise ManifestUnreadable(f"{manifest}: every sibling root must be name: path")
        parts = Path(relative).parts
        if len(parts) != 2 or parts[0] != ".." or Path(relative).is_absolute():
            raise ManifestUnreadable(
                f"{manifest}: sibling root {name} must be exactly '..' plus one directory, not {relative!r}")
        path = (root / Path(relative)).resolve()
        if not path.is_dir():
            raise ManifestUnreadable(f"{manifest}: sibling root {name} is not a directory: {relative}")
        resolved[name] = path
    return resolved


def _candidates(name: str, manifest: Path, root: Path | None = None) -> list[Path]:
    # The declaration is read first, always. An absent external root means nothing can resolve, but
    # it must not mean the manifest goes unread: a manifest that exists and cannot be parsed is a
    # fault to report, and returning early on a missing root turned that into "tool not declared".
    entries = _declared_entries(manifest)
    root = _external_root() if root is None else root
    if root is None:
        return []
    found: list[Path] = []
    for entry in entries:
        if entry.get("name") != name:
            continue
        sibling_name = entry.get("sibling_root")
        base: Path | None = root
        if sibling_name is not None:
            if not isinstance(sibling_name, str):
                raise ManifestUnreadable(f"{manifest}: sibling_root on {name} must be a name")
            base = sibling_roots(root, manifest).get(sibling_name)
            if base is None:
                raise ManifestUnreadable(f"{manifest}: {name} names undeclared sibling root {sibling_name!r}")
        for candidate in entry.get("external_paths") or []:
            if not isinstance(candidate, str) or not candidate.strip():
                continue
            relative = Path(candidate)
            # A declaration may only name a location inside the root it resolved against. That is
            # the external root normally, or one declared sibling root for the shared resources
            # that live beside it — never an arbitrary traversal.
            if relative.is_absolute() or ".." in relative.parts:
                continue
            path = base / relative
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

    consulted = [var for var in OVERRIDES.get(name, ())] + roots_consulted(name)
    hint = ""
    entry = entry_by_name(name)
    if entry is not None and not platform_supported(entry):
        hint = (f"; declared for platform {entry.get('platform')}, this host is {host_platform()}"
                " - nothing is guessed for a platform this host does not provide")
    elif entry is not None and entry.get("required_env"):
        missing = sorted(set(entry["required_env"]) - set(required_environment(name)))
        if missing:
            hint = f"; declared process environment not present on this host: {', '.join(missing)}"
    if guess_on_path:
        found = shutil.which(name)
        hint += f"; PATH would offer {found}" if found else "; PATH offers nothing"
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


def entry_by_name(name: str, manifest: Path | None = None) -> dict | None:
    """The declared entry for *name*, exactly as the manifest carries it.

    The other readers (host inventory, the external-resource index, the development
    launcher) need the binding data around a path - which process environment the resource
    requires, which probe certifies it, which platform it was declared for. Reading it from
    the same parsed manifest this module already resolves against is what keeps one
    declaration serving every reader instead of four copies drifting apart.
    """
    for entry in _declared_entries(manifest or _manifest_path()):
        if entry.get("name") == name:
            return entry
    return None


def host_platform() -> str:
    """This host in the manifest's own vocabulary (`windows-x64`, `linux-x64`, ...)."""
    import platform as _platform

    system = _platform.system().lower()
    machine = _platform.machine().lower()
    if system.startswith("win"):
        return "windows-x64" if machine in ("amd64", "x86_64") else f"windows-{machine}"
    if system == "linux":
        return "linux-x64" if machine in ("amd64", "x86_64") else f"linux-{machine}"
    if system == "darwin":
        return "macos-arm64" if machine == "arm64" else "macos-x64"
    return f"{system}-{machine}"


def platform_supported(entry: dict) -> bool:
    """Whether *entry* was declared for a platform this host can serve."""
    declared = str(entry.get("platform") or "any").strip().lower()
    return declared in ("", "any") or declared == host_platform()


def _relative_to_base(declared: str, base: Path) -> Path | None:
    """A declared relative location inside one root, or None when it is not allowed."""
    relative = Path(declared)
    if relative.is_absolute() or ".." in relative.parts:
        return None
    return base / relative


def _entry_base(entry: dict, name: str, root: Path, manifest: Path) -> Path | None:
    """The root an entry's declarations are relative to: the external root, or its sibling root."""
    sibling_name = entry.get("sibling_root")
    if sibling_name is None:
        return root
    if not isinstance(sibling_name, str):
        raise ManifestUnreadable(f"{manifest}: sibling_root on {name} must be a name")
    base = sibling_roots(root, manifest).get(sibling_name)
    if base is None:
        raise ManifestUnreadable(f"{manifest}: {name} names undeclared sibling root {sibling_name!r}")
    return base


def required_environment(name: str, *, only_existing: bool = True,
                         root: Path | str | None = None) -> dict[str, str]:
    """The process environment a declared resource needs, with paths resolved.

    Some resources resolve to a real file and still cannot run: the rustup proxies in
    `toolchains/rust/cargo/bin` are present on this host yet `rustc.exe` dies with
    ``error: Missing manifest in toolchain 'stable-x86_64-pc-windows-msvc'`` unless
    `RUSTUP_HOME` names the toolchain tree beside it (and bare `cargo.exe` then answers a
    *different* toolchain's version from the host default), while tesseract aborts on
    `--list-langs` without `TESSDATA_PREFIX`. The declaration therefore carries the
    environment, and every reader gets the same one instead of each re-deriving it.

    Values are paths relative to the same root the entry's `external_paths` use; absolute
    and `..` declarations are refused here exactly as they are there, so binding data
    cannot widen the boundary. A declared path that does not exist is skipped when
    `only_existing` - discovery must not hand a child a variable pointing at nothing.
    """
    entry = entry_by_name(name)
    if entry is None:
        return {}
    declared = entry.get("required_env") or {}
    if not isinstance(declared, dict):
        raise ManifestUnreadable(f"{name}: required_env must be a mapping of VARIABLE: relative path")
    if root is not None:
        supplied = Path(root)
        root = supplied if supplied.is_absolute() else None
    else:
        root = _external_root()
    if root is None:
        return {}
    try:
        base = _entry_base(entry, name, root, _manifest_path())
    except ManifestUnreadable:
        # The resource reaches a shared library this host does not have, so no environment for it
        # can be handed to a child. `tool_path(name)` still raises by name for a caller that wants
        # the resource itself; a launcher walking the whole declaration must not die on one row.
        return {}
    if base is None:
        return {}
    found: dict[str, str] = {}
    for variable, location in declared.items():
        if not isinstance(variable, str) or not isinstance(location, str) or not location.strip():
            raise ManifestUnreadable(f"{name}: required_env {variable!r} must name a relative path")
        path = _relative_to_base(location, base)
        if path is None:
            raise ManifestUnreadable(
                f"{name}: required_env {variable} must stay inside the declared root, not {location!r}")
        if only_existing and not (path.is_file() or path.is_dir()):
            continue
        found[variable] = str(path)
    return found


def declared_endpoint(name: str) -> dict | None:
    """The declared HTTP lane for a model served by a local runtime, or None.

    A caption or embedding model is not a file: it is an endpoint plus a model id, and the
    only honest statement about it is what the host actually answers. The declaration names
    the lane; `probe` decides whether it is there.
    """
    entry = entry_by_name(name)
    if entry is None:
        return None
    endpoint = entry.get("endpoint")
    return dict(endpoint) if isinstance(endpoint, dict) else None


def endpoint_resources(role: str | None = None) -> list[dict]:
    """Every declared model lane reached over HTTP, in declaration order.

    The caption and machine-answer workers used to carry their own hardcoded list of
    loopback addresses, so what the product talks to was written in two Python modules and
    nowhere in the declaration the index publishes. This is the read that makes the
    declaration the entry point: each row is `{name, endpoint}` for an entry that names an
    `endpoint`, and `role` narrows it to the lanes one capability actually consumes.
    """
    found: list[dict] = []
    for entry in _declared_entries(_manifest_path()):
        endpoint = entry.get("endpoint")
        if not isinstance(endpoint, dict):
            continue
        if role and role not in (entry.get("required_by") or []) + [entry.get("role")]:
            continue
        found.append({"name": entry.get("name"), "entry": entry, "endpoint": dict(endpoint)})
    return found


def declared_names() -> list[str]:
    """Every declared resource name, in manifest order.

    The development launcher walks the whole declaration to build a child environment
    instead of carrying its own list of tools; that is what stopped `dev.py` naming a Rust
    root the manifest and `scripts/ci/cargo_test.bat` did not name.
    """
    return [str(entry.get("name")) for entry in _declared_entries(_manifest_path())
            if entry.get("name")]


def declared_location(name: str, *, root: Path | str | None = None) -> str | None:
    """The declared path for *name* that exists, or None — without raising and without guessing.

    `root` lets a caller that already selected a root (the development launcher may take it from
    the tracked index rather than the environment) resolve through the same rule instead of
    re-implementing it. Absolute and `..` declarations stay refused either way.
    """
    override = Path(root) if root is not None else None
    if override is not None and not override.is_absolute():
        return None
    for path in _candidates(name, _manifest_path(), override):
        return str(path)
    return None


def roots_consulted(name: str) -> list[str]:
    """What was looked at when a resource could not be resolved - for the failure message."""
    consulted = [f"{MANIFEST_ENV} or {DEFAULT_MANIFEST}"]
    root = _external_root()
    consulted.append("external root from " + " / ".join(_ROOT_ENV)
                     + (f" = {root}" if root else " (none in this environment)"))
    entry = entry_by_name(name)
    if entry is not None and entry.get("sibling_root") is not None and root is not None:
        try:
            siblings = sibling_roots(root, _manifest_path())
        except ManifestUnreadable:
            siblings = {}
        consulted.append(f"sibling root {entry['sibling_root']!r} = "
                         + (str(siblings.get(str(entry['sibling_root'])))
                            if siblings.get(str(entry["sibling_root"])) else "does not resolve"))
    for variable in OVERRIDES.get(name, ()):
        raw = os.environ.get(variable, "").strip()
        consulted.append(f"{variable}" + (f" = {raw}" if raw else " (unset)"))
    return consulted



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


def local_runtime_lanes(role: str | None = None) -> list[dict]:
    """The declared local model lanes, normalized for a worker about to call one.

    Deduplicated by `(protocol, base_url)` in declaration order. A worker that names a model
    itself (the text-answer route asks for a text model) uses the address only; a worker that
    must use the identity the declaration names passes `role` and reads `model`.

    This exists because two addresses were written into Python source instead of the
    declaration: a host that serves the models on the OpenAI-compatible lane while Ollama is
    down had no way to say so, and the index said nothing about either lane at all.
    """
    seen: dict[tuple[str, str], dict] = {}
    for resource in endpoint_resources(role):
        endpoint = resource["endpoint"]
        protocol = str(endpoint.get("protocol") or "")
        base = str(endpoint.get("base_url") or "").rstrip("/")
        if protocol not in ("ollama", "openai") or not base:
            continue
        key = (protocol, base)
        record = {"protocol": protocol, "base": base, "model": endpoint.get("model_id"),
                  "resource": resource["name"], "name": resource["name"]}
        existing = seen.get(key)
        if existing is None:
            seen[key] = record
        elif not existing.get("model") and record.get("model"):
            existing["model"] = record["model"]
    return list(seen.values())


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
