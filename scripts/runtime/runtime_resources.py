"""Read-only formal runtime member/namespace validation shared by builder and assembler.

No cleanup, installation, execution or runtime-journey qualification occurs here.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path, PurePosixPath

if __package__:
    from . import dev
else:
    import dev

RESOURCES = {"runtime", "core", "workers", "shared", "worker-profile.json",
             "start-backend.py", "start-backend.cmd", "backend-runtime-manifest.json",
             "vcruntime140.dll", "vcruntime140_1.dll"}
SHA = re.compile(r"[0-9a-f]{64}\Z")
FIXED_WEBVIEW2_MANIFEST_SHA256 = "d465623969d3ba9ac271deb6fb81865007261e20c93dd723ff65c38144bc89f7"
# Public file shipped by the already qualified locked FastAPI distribution.
# This exception never authorizes a native agent directory or changed bytes.
PUBLIC_UPSTREAM_FILES = {
    "runtime/Lib/site-packages/fastapi/.agents/skills/fastapi/SKILL.md": {
        "bytes": 13665, "sha256": "833e99b101b657690f44e9d6cab5d77b6b31dbf477e1fb64b5b7b8da27095917"},
}


def native(path: Path) -> str:
    text = os.fspath(path)
    return "\\\\?\\" + text if os.name == "nt" and not text.startswith("\\\\?\\") else text


def checked(path: Path) -> Path:
    path = dev.safe_path(path)
    for part in (*reversed(path.parents), path):
        try:
            info = os.lstat(native(part))
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("Linked candidate path rejected")
    return path


def digest(path: Path) -> str:
    with open(native(path), "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError("Invalid relative member path")
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or parsed.as_posix() != value or any(p in {".", ".."} for p in parsed.parts):
        raise ValueError("Unsafe or noncanonical member path")
    if value not in PUBLIC_UPSTREAM_FILES and any(
            p.casefold() in {".git", ".codex", ".hermes", ".ssh", ".agents", ".env"}
            or p.casefold().startswith(".env.") for p in parsed.parts):
        raise ValueError("Private material is not a candidate input")
    return value


def regular(path: Path, *, cargo_host: bool = False) -> Path:
    path = checked(path)
    info = os.lstat(native(path))
    cargo_pair = False
    if cargo_host and info.st_nlink == 2 and path.parent.name == "release":
        alias = checked(path.parent / "deps" / path.name)
        try:
            cargo_pair = os.path.samestat(info, os.lstat(native(alias)))
        except FileNotFoundError:
            pass
    if not stat.S_ISREG(info.st_mode) or (info.st_nlink != 1 and not cargo_pair):
        raise ValueError(f"Expected an independent regular file: {path}")
    return path


def file_metadata(info) -> dict:
    """Public, bounded lstat evidence; no following a redirect or content dump."""
    return {name: getattr(info, name, None) for name in (
        "st_mode", "st_nlink", "st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns",
        "st_file_attributes", "st_reparse_tag")}


def opened_file_matches(stream, planned: dict) -> bool:
    info = os.fstat(stream.fileno())
    # On Windows fstat and path-lstat expose different permission bits/ctime
    # semantics. Compare the actual file ID/type and bytes here; compare full
    # path-lstat metadata with itself before/after the operation as well.
    return stat.S_IFMT(info.st_mode) == stat.S_IFMT(planned["st_mode"]) and all(
        getattr(info, key, None) == planned[key] for key in (
            "st_dev", "st_ino", "st_nlink", "st_size", "st_mtime_ns", "st_file_attributes", "st_reparse_tag"))


def _core_link_paths(path: Path) -> dict:
    """Ask Windows for this file's exact names, never scan a Cargo deps tree."""
    if os.name != "nt":
        raise ValueError("Core hardlink name enumeration is only supported on Windows")
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    first, next_name, close = kernel.FindFirstFileNameW, kernel.FindNextFileNameW, kernel.FindClose
    first.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.LPWSTR]
    first.restype = wintypes.HANDLE
    next_name.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD), wintypes.LPWSTR]
    next_name.restype = wintypes.BOOL
    close.argtypes, close.restype = [wintypes.HANDLE], wintypes.BOOL
    # A bounded maximum Windows path buffer; MORE_DATA fails closed, never retries without a bound.
    buffer = ctypes.create_unicode_buffer(32768)
    length = wintypes.DWORD(len(buffer))
    handle = first(native(path), 0, ctypes.byref(length), buffer)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    names = []
    try:
        names.append(buffer.value)
        while True:
            length.value = len(buffer)
            if not next_name(handle, ctypes.byref(length), buffer):
                error = ctypes.get_last_error()
                if error != 38:  # ERROR_HANDLE_EOF, including after the second name.
                    raise ctypes.WinError(error)
                break
            if len(names) == 2:
                raise ValueError("Core file has more than two hardlink names")
            names.append(buffer.value)
    finally:
        error = sys.exc_info()[1]
        if not close(handle):
            failure = ctypes.WinError(ctypes.get_last_error())
            if error is not None:
                error.add_note("Core hardlink FindClose also failed: " + str(failure))
            else:
                raise failure
    paths = []
    for name in names:
        if (not re.fullmatch(r"[A-Za-z]:\\", path.anchor) or not name.startswith("\\")
                or name.startswith("\\\\") or ":" in name or "/" in name
                or any(part in {".", "..", ""} for part in name[1:].split("\\"))):
            raise ValueError("Unexpected volume-relative Core hardlink name")
        paths.append(Path(path.anchor + name[1:]))
    return {"paths": paths, "raw_names": names, "method": "WIN32_EXACT_FILE_NAMES"}


def core_identity(path: Path, cargo_root: Path) -> dict:
    """Admit only the canonical Windows Core's exact two-name Cargo output pair.

    This is observed source admission, not a qualified Core build receipt. Host's
    existing same-name rule and generic independent-file rules remain separate.
    """
    path, cargo_root = checked(path), checked(cargo_root)
    if path != cargo_root / "release/archeaxis-api.exe":
        raise ValueError("Core hardlink is outside the canonical Cargo release path")
    info = os.lstat(native(path))
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 2:
        raise ValueError("Cargo Core requires exactly two regular hardlink names")
    observed = _core_link_paths(path)
    names, raw_names = observed["paths"], observed["raw_names"]
    if (len(names) != 2 or len(raw_names) != 2 or len(set(names)) != 2 or path not in names
            or len({name.casefold() for name in raw_names}) != 2):
        raise ValueError("Cargo Core hardlink enumeration differs from the declared source")
    # FindFirst/NextFileName make no ordering promise. Preserve original string
    # contents in a stable order so a repeated observation has the same identity.
    raw_names = sorted(raw_names, key=str.casefold)
    pair = checked(next(name for name in names if name != path))
    if (pair.parent != path.parent / "deps"
            or not re.fullmatch(r"archeaxis_api(?:-[0-9a-f]{16})?\.exe", pair.name)):
        raise ValueError("Cargo Core pair must be its direct deps binary")
    other = os.lstat(native(pair))
    if (not stat.S_ISREG(other.st_mode) or other.st_nlink != 2
            or not os.path.samestat(info, other)):
        raise ValueError("Cargo Core pair must have the exact same file identity")
    sha = hashlib.sha256()
    with open(native(path), "rb") as stream:
        if not opened_file_matches(stream, file_metadata(info)):
            raise ValueError("Cargo Core changed while opening its source")
        remaining = info.st_size
        while remaining:
            chunk = stream.read(min(remaining, 1024 * 1024))
            if not chunk:
                raise ValueError("Cargo Core shorter than observed")
            sha.update(chunk)
            remaining -= len(chunk)
        if stream.read(1):
            raise ValueError("Cargo Core grew beyond observed size")
    if (file_metadata(os.lstat(native(path))) != file_metadata(info)
            or file_metadata(os.lstat(native(pair))) != file_metadata(other)):
        raise ValueError("Cargo Core source pair changed while reading")
    return {"bytes": info.st_size, "sha256": sha.hexdigest(), "cargo_core": {
        "source": str(path), "cargo_root": str(cargo_root), "pair": str(pair),
        "source_metadata": file_metadata(info), "pair_metadata": file_metadata(other),
        "link_names": raw_names, "enumeration": observed["method"],
        "qualification": "OBSERVED_CARGO_OUTPUT_NOT_QUALIFIED_BUILD"}}


def inventory(root: Path) -> set[str]:
    checked(root)
    result = set()
    def fail(error):
        raise error
    for directory, dirs, files in os.walk(native(root), onerror=fail, followlinks=False):
        relative = Path(directory).relative_to(Path(native(root)))
        for name in dirs:
            checked(root / relative / name)
        for name in files:
            path = regular(root / relative / name)
            result.add(path.relative_to(root).as_posix())
    return result


def verify_members(root: Path, members: dict) -> None:
    if not isinstance(members, dict) or not members:
        raise ValueError("Missing member manifest")
    folded = set()
    for name, row in members.items():
        relative_path(name)
        if name.casefold() in folded:
            raise ValueError("Case-insensitive duplicate member")
        folded.add(name.casefold())
        if (not isinstance(row, dict) or type(row.get("bytes")) is not int
                or row["bytes"] < 0 or not isinstance(row.get("sha256"), str)
                or not SHA.fullmatch(row["sha256"])):
            raise ValueError("Invalid member identity")
        if name in PUBLIC_UPSTREAM_FILES and row != PUBLIC_UPSTREAM_FILES[name]:
            raise ValueError("Public upstream exception bytes changed")
        path = regular(root / name)
        if os.stat(native(path)).st_size != row["bytes"] or digest(path) != row["sha256"]:
            raise ValueError(f"Member identity mismatch: {name}")


def verify_worker_contract(root: Path, members: dict) -> None:
    profile = json.loads(regular(root / "worker-profile.json").read_text(encoding="utf-8"))
    routes = json.loads(regular(root / "workers/routes.json").read_text(encoding="utf-8"))
    if (profile.get("schema") != "archeaxis.worker-profile/v1"
            or routes.get("schema") != "archeaxis.worker-routes/v1"
            or profile.get("python") not in {"runtime/python.exe", "runtime/python/python.exe"}
            or profile.get("script") != "workers/transport/text_ndjson.py"
            or profile.get("staging") != "data/worker-staging"):
        raise ValueError("Invalid formal worker launch contract")
    required = {profile["python"], profile["script"], "core/archeaxis-api.exe", "workers/routes.json"}
    for name in ("vcruntime140.dll", "vcruntime140_1.dll"):
        copies = [prefix + name for prefix in ("", "core/", "runtime/")]
        required.update(copies)
        if not all(member in members for member in copies):
            raise ValueError("Required app-local VC runtime copy absent")
        identities = [(members[member].get("bytes"), members[member].get("sha256")) for member in copies]
        if any(identity != identities[0] for identity in identities[1:]):
            raise ValueError("App-local VC runtime copies differ from runtime donor")
    mapping = routes.get("routes")
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError("Missing native worker routes")
    expected = {}
    for capability, scripts in mapping.items():
        if not isinstance(capability, str) or not isinstance(scripts, list) or not scripts:
            raise ValueError("Invalid native worker route")
        for script in scripts:
            required.add("workers/" + relative_path(script))
        expected[capability] = "workers/" + scripts[0]
    observed = {}
    for row in profile["routes"]:
        if row["capability"] in observed:
            raise ValueError("Duplicate worker profile route")
        observed[row["capability"]] = relative_path(row["script"])
    if observed != expected or not required.issubset(members):
        raise ValueError("Native/profile routes differ or worker input absent")


def verify_fixed_webview2(root: Path) -> dict:
    """Qualify the desktop dependency separately from backend-only staging."""
    directory = checked(root / "runtime/webview2")
    manifest = regular(directory / "aaos-fixed-runtime-manifest.json")
    if digest(manifest) != FIXED_WEBVIEW2_MANIFEST_SHA256:
        raise ValueError("fixed WebView2 manifest identity mismatch")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("schema") != "archeaxis.official-fixed-runtime-files/v1":
        raise ValueError("unrecognized fixed WebView2 manifest")
    files = {}
    for row in data["files"]:
        name = relative_path(row["path"])
        if name.casefold() in {p.casefold() for p in files}:
            raise ValueError("duplicate fixed WebView2 member")
        files[name] = {"bytes": row["bytes"], "sha256": row["sha256"]}
    if not {"msedgewebview2.exe", "msedge.dll"}.issubset(files):
        raise ValueError("missing fixed WebView2 executable")
    verify_members(directory, files)
    if inventory(directory) != set(files) | {manifest.name}:
        raise ValueError("unmanifested fixed WebView2 resource")
    return {"version": data["version"], "path": "runtime/webview2",
            "manifest_sha256": digest(manifest),
            "executable_sha256": files["msedgewebview2.exe"]["sha256"]}


def verify_runtime_resources(root: Path, configured_resources: set[str]) -> dict:
    """Verify the complete formal resource namespace, without modifying any member."""
    if configured_resources != RESOURCES:
        raise ValueError("Formal resource contract changed; update the adapter explicitly")
    root = checked(root)
    runtime_manifest = regular(root / "backend-runtime-manifest.json")
    backend = json.loads(runtime_manifest.read_text(encoding="utf-8"))
    if backend.get("schema") != "archeaxis.backend-runtime/v1":
        raise ValueError("Unrecognized backend manifest")
    members = backend["files"]
    for name in members:
        relative_path(name)
        if PurePosixPath(name).parts[0] not in RESOURCES:
            raise ValueError("Backend member outside declared runtime resources")
    verify_members(root, members)
    verify_worker_contract(root, members)
    expected = set(members) | {"backend-runtime-manifest.json"}
    observed = set()
    for resource in RESOURCES:
        path = checked(root / resource)
        if path.is_dir():
            observed.update(resource + "/" + name for name in inventory(path))
        else:
            regular(path)
            observed.add(resource)
    if observed != expected:
        raise ValueError("Unmanifested or missing runtime resources")
    return backend
