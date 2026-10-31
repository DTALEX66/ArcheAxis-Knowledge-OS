"""Read-only formal runtime member/namespace validation shared by builder and assembler.

No cleanup, installation, execution or runtime-journey qualification occurs here.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
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
