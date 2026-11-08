"""Start the staged backend runtime from its own root.

This is the formal entry point of a staged runtime. It resolves every component from
the runtime root it lives in - never from a checkout, a project virtualenv, an
editable install or an inherited `PYTHONPATH` - and it never asks the operator to
resolve an interpreter: the scheduler interpreter comes from `worker-profile.json`,
which is what the Core reads.

    runtime/python.exe start-backend.py --data-root <dir> [--port N] [--smoke]

`--smoke` performs the first exchange, reports health, and shuts the Core down.

Every failure names the component that failed. A missing interpreter, required
worker or Core, a bad profile, a port conflict and an early exit are distinguishable.
The optional private DeepTutor practice route may be absent without preventing
ordinary Core startup.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import errno
import os
import re
import secrets
import socket
import stat
import subprocess
import threading
import time
import urllib.error
import urllib.request
from contextlib import suppress
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROFILE_NAME = "worker-profile.json"
PROFILE_SCHEMA = "archeaxis.worker-profile/v1"
CORE_RELATIVE = Path("core") / "archeaxis-api.exe"
LAUNCH_PROTOCOL = "archeaxis.desktop-launch/v2"
READY_MARKER = "127.0.0.1:"
STARTUP_TIMEOUT_SECONDS = 30.0
PRIVATE_NAMES = set([".git", ".codex", ".dsh", ".zcode", ".hermes", ".openhuman", ".claude", ".agents", ".agent", ".cursor", ".continue", ".aider", ".gemini", ".opencode", ".openhands", ".cline", ".roo", ".kilocode", ".windsurf", ".copilot", ".ssh", ".aws", ".azure", ".gnupg", "agent-private", "private-agent-state", "sessions", "memories", "keychain", "credentials", "auth", "browser-data", ".npmrc", ".pypirc", ".netrc"])
OPENMAIC_DIRECTORY = "workers/openmaic"
OPENMAIC_FILES = {
    "scene-build-worker.mjs": {"bytes": 7315, "sha256": "c4a2dad9c96ebd13aa20827410227d2650cda0dac80e3a3927968d1e024779e9"},
    "vendor/generation-0.3.28/scene-builder.ts": {"bytes": 3082, "sha256": "e550ed528f9a017ea0fa1f9cc4a01f7eb22d541d5ada067967d3434393d1bf0a"},
    "vendor/generation-0.3.28/nanoid.mjs": {"bytes": 389, "sha256": "d5d678dfcecc9a4c0f4dae6555c30b4d0ef41a87b00d4d16d744f31ddae6c16e"},
    "vendor/generation-0.3.28/LICENSE": {"bytes": 1065, "sha256": "ba252563743227138231604c9138dd400faca5a10c3cf206b466e5466c565a19"},
    "vendor/generation-0.3.28/UPSTREAM.md": {"bytes": 1134, "sha256": "83962cee94daba3596fba378867756981c87a8bd7839ced586510643c113d579"},
}
OPENMAIC_NODE_MAX_BYTES = 512 * 1024 * 1024
OPENMAIC_MANIFEST_MAX_BYTES = 16 * 1024 * 1024


class LaunchFailure(Exception):  # noqa: N818 - retained public exception contract
    """A named startup failure; the message says which component failed."""


def filesystem_path(path: Path, *, force: bool = False) -> Path:
    """Use the Windows extended form for long local I/O, not launch profiles."""
    if os.name == "nt":
        absolute = os.path.abspath(path)
        if (force or len(absolute) >= 248) and not absolute.startswith("\\\\"):
            return Path("\\\\?\\" + absolute)
    return path


def safe_path(root: Path, value: str) -> Path:
    spelling = value.replace("\\", "/")
    if not value.strip() or spelling.lower().startswith("e:") or spelling.startswith("//") or ".." in spelling.split("/"):
        raise LaunchFailure("unsafe worker profile path")
    path = Path(os.path.abspath(root / value))
    full = str(path).replace("\\", "/").lower()
    if full.startswith(("e:", "//")) or any(part in PRIVATE_NAMES or part.startswith(".env") for part in full.split("/")) or "/.project-local/agents/" in full:
        raise LaunchFailure("protected worker profile path")
    for part in (*reversed(path.parents), path):
        try:
            info = filesystem_path(part).lstat()
        except (FileNotFoundError, NotADirectoryError):
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise LaunchFailure("linked worker profile path")
    return path


def load_profile(root: Path, explicit_path: str | None = None) -> dict:
    path = safe_path(root, explicit_path if explicit_path is not None else PROFILE_NAME)
    io_path = filesystem_path(path)
    if not io_path.is_file():
        raise LaunchFailure(f"worker profile is missing: {path}")
    try:
        if io_path.stat().st_size > 16384:
            raise LaunchFailure("worker profile exceeds limit")

        def unique(pairs):
            document = {}
            for key, value in pairs:
                if key in document:
                    raise LaunchFailure("duplicate worker profile field")
                document[key] = value
            return document

        document = json.loads(io_path.read_text(encoding="utf-8"), object_pairs_hook=unique)
    except (json.JSONDecodeError, UnicodeError, OSError) as error:
        raise LaunchFailure("worker profile is not valid readable JSON") from error
    allowed_fields = (
        {"schema", "python", "script", "staging"},
        {"schema", "python", "script", "staging", "routes"},
    )
    if not isinstance(document, dict) or set(document) not in allowed_fields:
        raise LaunchFailure("unsupported or incomplete worker profile fields")
    if document.get("schema") != PROFILE_SCHEMA:
        raise LaunchFailure(
            f"worker profile schema is not {PROFILE_SCHEMA}: {document.get('schema')!r}")
    resolved = {}
    for key in ("python", "script", "staging"):
        value = document.get(key)
        if not isinstance(value, str) or not value.strip():
            raise LaunchFailure(f"worker profile has no {key}: {path}")
        resolved[key] = safe_path(path.parent, value)
    require_file(resolved["python"], "worker interpreter")
    require_file(resolved["script"], "worker script")
    resolved["routes"] = _load_routes(document, path)
    return resolved


def _load_routes(document: dict, path: Path) -> list[dict]:
    """The profile's optional capability routes, resolved and validated.

    An absent list keeps the previous single-route behaviour. Each entry names one
    capability and the worker script that serves it, relative to the profile, so the
    staged runtime declares what it actually ships rather than the Core assuming a
    layout. A malformed entry is refused by name instead of being silently dropped,
    because a dropped route would surface later as an unexplained failed job.
    """
    routes = document.get("routes")
    if routes is None:
        return []
    if not isinstance(routes, list):
        raise LaunchFailure("worker profile routes must be a list")
    resolved: list[dict] = []
    seen: set[str] = set()
    for index, entry in enumerate(routes):
        if not isinstance(entry, dict) or set(entry) != {"capability", "script"}:
            raise LaunchFailure(f"worker profile route {index} must be capability and script")
        capability = entry.get("capability")
        script = entry.get("script")
        if not isinstance(capability, str) or not capability.strip():
            raise LaunchFailure(f"worker profile route {index} has no capability")
        if not isinstance(script, str) or not script.strip():
            raise LaunchFailure(f"worker profile route {index} has no script")
        capability = capability.strip()
        if capability == "text.extract":
            raise LaunchFailure("worker profile route must not redeclare text.extract")
        if capability in seen:
            raise LaunchFailure(f"duplicate worker profile route capability: {capability}")
        seen.add(capability)
        resolved_script = safe_path(path.parent, script)
        # These two routes are private, optional Core-controlled processes.
        # Their absence must not prevent the Core or ordinary document saving.
        # Unsafe paths still fail above; other routes keep their existing rule.
        if capability in ("deeptutor.practice.import", "deeptutor.question.turn",
                          "deeptutor.teaching.feedback"):
            if not filesystem_path(resolved_script).is_file():
                continue
        require_file(resolved_script, f"worker route script for {capability}")
        resolved.append({"capability": capability, "script": resolved_script})
    return resolved


def require_file(path: Path, what: str) -> Path:
    if not filesystem_path(path).is_file():
        raise LaunchFailure(f"{what} is missing: {path}")
    return path


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def build_environment(root: Path) -> dict:
    """Only runtime locations are exported. The interpreter is not among them.

    `ARCHEAXIS_PYTHON` is deliberately *not* set: the Core resolves the scheduler
    interpreter from the profile, which is the whole point of the profile existing.
    An inherited value is removed so a developer shell cannot mask a broken runtime.
    """
    environment = dict(os.environ)
    environment.pop("ARCHEAXIS_PYTHON", None)
    environment.pop("ARCHAXIS_PYTHON", None)
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    environment["PYTHONNOUSERSITE"] = "1"
    environment["ARCHEAXIS_BACKEND_ROOT"] = str(root)
    environment["ARCHEAXIS_WORKER_PROFILE"] = str(root / PROFILE_NAME)
    environment["ARCHAXIS_WORKER_PROFILE"] = str(root / PROFILE_NAME)
    scheduler = str(root / "workers" / "learning" / "worker_schedule.py")
    environment["ARCHEAXIS_SCHEDULER_WORKER"] = scheduler
    environment["ARCHAXIS_SCHEDULER_WORKER"] = scheduler
    environment["ARCHEAXIS_CORE_BIN"] = str(root / CORE_RELATIVE)
    environment["ARCHAXIS_CORE_BIN"] = str(root / CORE_RELATIVE)
    return environment


def document_check_config(data_root: Path) -> tuple[dict | None, str | None]:
    """One fixed non-secret owner file; invalid config cannot block ordinary save."""
    from urllib.parse import urlsplit

    def reparse(metadata):
        import stat

        return stat.S_ISLNK(metadata.st_mode) or bool(
            getattr(metadata, "st_file_attributes", 0) & 0x400
        )

    def identity(metadata):
        return metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns

    try:
        # Keep the complete containment/identity comparison in one path form;
        # a short root can still contain a config file beyond MAX_PATH.
        root = filesystem_path(data_root, force=True).resolve(strict=True)
        folder = root / "config"
        try:
            parent = folder.stat(follow_symlinks=False)
        except FileNotFoundError:
            return None, None
        if reparse(parent) or not folder.is_dir():
            return None, "invalid_config"
        folder_identity = folder.resolve(strict=True)
        if not folder_identity.is_relative_to(root):
            return None, "invalid_config"
        path = folder / "document-check.json"
        try:
            before = path.stat(follow_symlinks=False)
        except FileNotFoundError:
            return None, None
        if reparse(before) or not path.is_file() or before.st_size > 16 * 1024:
            return None, "invalid_config"
        canonical = path.resolve(strict=True)
        if canonical.parent != folder_identity or not canonical.is_relative_to(root):
            return None, "invalid_config"
        with path.open("rb") as handle:
            import os

            opened = os.fstat(handle.fileno())
            if identity(before) != identity(opened):
                return None, "invalid_config"
            raw = handle.read(16 * 1024 + 1)
            final_opened = os.fstat(handle.fileno())
        after = path.stat(follow_symlinks=False)
        if (
            len(raw) > 16 * 1024
            or reparse(after)
            or identity(opened) != identity(after)
            or identity(opened) != identity(final_opened)
            or path.resolve(strict=True) != canonical
            or folder.resolve(strict=True) != folder_identity
            or reparse(folder.stat(follow_symlinks=False))
        ):
            return None, "invalid_config"
        def unique_config(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate configuration field")
                result[key] = value
            return result

        config = json.loads(raw, object_pairs_hook=unique_config)
        required = {"provider", "model", "credential_ref", "max_tokens", "timeout_seconds", "search_limit"}
        if (
            not isinstance(config, dict)
            or not required <= config.keys()
            or config.keys() - required - {"endpoint"}
        ):
            return None, "invalid_config"
        provider, model = config["provider"], config["model"]
        credential_ref = config["credential_ref"]
        if not isinstance(credential_ref, str) or re.fullmatch(r"aak_cred_[a-f0-9]{32}", credential_ref) is None:
            return None, "invalid_config"
        if (
            not isinstance(provider, str)
            or not provider
            or len(provider.encode("utf-8")) > 64
            or not all(c.isascii() and (c.isalnum() or c == "_") for c in provider)
        ):
            return None, "invalid_config"
        if (
            not isinstance(model, str)
            or len(model.encode("utf-8")) > 256
            or not model.startswith(provider + "/")
            or not model.split("/", 1)[1].strip()
        ):
            return None, "invalid_config"
        for field, low, high in (
            ("max_tokens", 128, 4096),
            ("timeout_seconds", 1, 120),
            ("search_limit", 1, 3),
        ):
            if type(config[field]) is not int or not low <= config[field] <= high:
                return None, "invalid_config"
        endpoint = config.get("endpoint")
        if endpoint is not None:
            if (
                not isinstance(endpoint, str)
                or not endpoint.startswith("https://")
                or len(endpoint.encode("utf-8")) > 2048
                or any(c in endpoint for c in "@?#")
                or any(c.isspace() for c in endpoint)
            ):
                return None, "invalid_config"
            url = urlsplit(endpoint)
            if not url.hostname or url.username is not None or url.password is not None:
                return None, "invalid_config"
            _ = url.port
        return config, None
    except (OSError, ValueError, TypeError):
        return None, "invalid_config"


def openmaic_node_worker(root: Path) -> tuple[dict | None, str | None]:
    """Read only the fixed staged members; a disabled optional provider says why.

    A same-directory manifest binds the declared bytes, not their provenance or
    installation qualification. Core independently checks the worker before use.
    The reason is a fixed label because an unusable path is a different finding
    from bytes that do not match: folding the two together sends an operator to
    the wrong problem, which is what a 269-character staged member did here.
    """
    path_errnos = {errno.ENAMETOOLONG, errno.ENOTDIR, errno.EINVAL}
    def classified(error: OSError, missing: str, unreadable: str) -> str:
        if getattr(error, "errno", None) in path_errnos or getattr(error, "winerror", None) in (123, 206):
            return "path_invalid"
        if isinstance(error, FileNotFoundError):
            return missing
        return unreadable

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate backend manifest field")
            result[key] = value
        return result

    def reject_nonfinite(_value):
        raise ValueError("non-finite backend manifest number")

    def file_identity(value):
        return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_nlink

    def matches(relative, identity, limit):
        """(ok, reason); reason is None only when the member equals its claim."""
        if (not isinstance(identity, dict) or set(identity) != {"bytes", "sha256"}
                or type(identity["bytes"]) is not int or not 0 < identity["bytes"] <= limit
                or not isinstance(identity["sha256"], str)
                or not re.fullmatch(r"[a-f0-9]{64}", identity["sha256"])):
            return False, "member_claim_invalid"
        path = safe_path(root, f"{OPENMAIC_DIRECTORY}/{relative}")
        io_path = filesystem_path(path)
        try:
            info = io_path.stat()
        except OSError as error:
            return False, classified(error, "member_absent", "member_unreadable")
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            return False, "member_unusable"
        if info.st_size != identity["bytes"]:
            return False, "member_identity_mismatch"
        digest = hashlib.sha256()
        try:
            stream = io_path.open("rb")
        except OSError as error:
            return False, classified(error, "member_absent", "member_unreadable")
        with stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                return False, "member_unusable"
            if (before.st_dev, before.st_ino, before.st_size) != (info.st_dev, info.st_ino, info.st_size):
                return False, "member_identity_mismatch"
            remaining = identity["bytes"]
            while remaining:
                chunk = stream.read(min(65536, remaining))
                if not chunk:
                    return False, "member_identity_mismatch"
                remaining -= len(chunk)
                digest.update(chunk)
            if stream.read(1):
                return False, "member_identity_mismatch"
            after = os.fstat(stream.fileno())
            if not stat.S_ISREG(after.st_mode) or after.st_nlink != 1:
                return False, "member_unusable"
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                    after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
                return False, "member_identity_mismatch"
        if digest.hexdigest() != identity["sha256"]:
            return False, "member_identity_mismatch"
        return True, None

    try:
        path = safe_path(root, "backend-runtime-manifest.json")
        io_path = filesystem_path(path)
        try:
            info = io_path.stat()
        except OSError as error:
            return None, classified(error, "absent", "manifest_unreadable")
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or not 0 < info.st_size <= OPENMAIC_MANIFEST_MAX_BYTES):
            return None, "manifest_unusable"
        with io_path.open("rb") as stream:
            before = os.fstat(stream.fileno())
            if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                    or file_identity(before) != file_identity(info)):
                return None, "manifest_unusable"
            raw = stream.read(info.st_size + 1)
            after = os.fstat(stream.fileno())
            current = io_path.stat()
            if (len(raw) != info.st_size or not stat.S_ISREG(after.st_mode) or not stat.S_ISREG(current.st_mode)
                    or file_identity(after) != file_identity(before) or file_identity(current) != file_identity(before)):
                return None, "manifest_unusable"
        if len(raw) > OPENMAIC_MANIFEST_MAX_BYTES:
            return None, "manifest_unusable"
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=reject_nonfinite)
        if not isinstance(document, dict) or document.get("schema") != "archeaxis.backend-runtime/v1":
            return None, "manifest_invalid"
        config, files = document.get("openmaic_scene_build"), document.get("files")
        if (not isinstance(config, dict) or set(config) != {"status", "node_sha256"}
                or config["status"] != "INCLUDED" or not isinstance(config["node_sha256"], str)
                or not re.fullmatch(r"[a-f0-9]{64}", config["node_sha256"]) or not isinstance(files, dict)):
            return None, "manifest_invalid"
        for relative, identity in OPENMAIC_FILES.items():
            if files.get(f"{OPENMAIC_DIRECTORY}/{relative}") != identity:
                return None, "member_claim_invalid"
            ok, reason = matches(relative, identity, 1_000_000)
            if not ok:
                return None, reason
        node = files.get(f"{OPENMAIC_DIRECTORY}/node.exe")
        license_row = files.get(f"{OPENMAIC_DIRECTORY}/NODE-LICENSE")
        if not isinstance(node, dict) or node.get("sha256") != config["node_sha256"]:
            return None, "member_claim_invalid"
        for relative, identity, limit in (("node.exe", node, OPENMAIC_NODE_MAX_BYTES),
                                          ("NODE-LICENSE", license_row, 1_000_000)):
            ok, reason = matches(relative, identity, limit)
            if not ok:
                return None, reason
        return {"executable": str(safe_path(root, f"{OPENMAIC_DIRECTORY}/node.exe")),
                "executable_sha256": config["node_sha256"],
                "script": str(safe_path(root, f"{OPENMAIC_DIRECTORY}/scene-build-worker.mjs"))}, None
    except (ValueError, TypeError, UnicodeError, RecursionError):
        return None, "manifest_invalid"
    except LaunchFailure:
        return None, "manifest_unusable"
    except OSError as error:
        return None, classified(error, "absent", "manifest_unreadable")


def start(data_root: Path, port: int, *, workspace_name: str = "workspace.sqlite") -> tuple[subprocess.Popen, str, dict, dict]:
    """Launch a session, optionally reopening the product host's workspace file."""
    if not workspace_name.strip() or any(character in workspace_name for character in "\\/:") or workspace_name in {".", ".."}:
        raise LaunchFailure("unsafe workspace filename")
    core = require_file(safe_path(ROOT, str(CORE_RELATIVE)), "Core executable")
    profile = load_profile(ROOT)
    require_file(profile["python"], "scheduler interpreter (from worker profile)")
    require_file(profile["script"], "text worker script (from worker profile)")

    data_root = safe_path(ROOT, str(data_root))
    staging = safe_path(data_root, "worker-staging")
    workspace = safe_path(data_root, workspace_name)
    filesystem_path(data_root).mkdir(parents=True, exist_ok=True)
    filesystem_path(staging).mkdir(parents=True, exist_ok=True)

    launch = {
        "launch_token": secrets.token_hex(32),
        "session_id": secrets.token_hex(16),
        "actor": "human",
        "protocol": LAUNCH_PROTOCOL,
        "machine_token": secrets.token_hex(32),
        "text_worker": {
            "python": str(profile["python"]),
            "script": str(profile["script"]),
            "staging": str(staging),
            # Declared capability routes. An empty list would be identical to omitting
            # the field, so it is only emitted when the runtime actually ships routes.
            **({"routes": [
                {"capability": route["capability"], "script": str(route["script"])}
                for route in profile.get("routes", [])
            ]} if profile.get("routes") else {}),
        },
    }
    openmaic, openmaic_reason = openmaic_node_worker(ROOT)
    if openmaic is not None:
        launch["openmaic_node_worker"] = openmaic
    elif openmaic_reason is not None:
        # A disabled optional provider is a named state, not an absent one.
        launch["openmaic_node_worker_error"] = openmaic_reason
    check_config, check_error = document_check_config(data_root)
    if check_config is not None:
        launch["document_check_config"] = check_config
    if check_error is not None:
        launch["document_check_config_error"] = check_error
    launch_directory = ROOT
    if os.name == "nt":
        # CreateProcess cannot use an overlong current directory even when its
        # executable is addressed using extended syntax. Do not inherit an
        # unrelated caller's cwd; use the nearest short runtime ancestor.
        while len(str(launch_directory)) >= 248:
            parent = launch_directory.parent
            if parent == launch_directory:
                raise LaunchFailure("no usable Core working directory")
            launch_directory = parent
    child = subprocess.Popen(
        [str(filesystem_path(core)), str(workspace), str(port)],
        executable=str(filesystem_path(core)),
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", cwd=str(launch_directory),
        env=build_environment(ROOT),
    )
    try:
        assert child.stdin is not None
        child.stdin.write(json.dumps(launch) + "\n")
        child.stdin.flush()
        child.stdin.close()
        base = wait_for_readiness(child, port, STARTUP_TIMEOUT_SECONDS)
        receipt = {"core": str(core), "workspace": str(workspace), "port": port,
                   "text_worker": launch["text_worker"]}
        if openmaic_reason is not None:
            receipt["openmaic_node_worker_error"] = openmaic_reason
        tokens = {"human": launch["launch_token"], "machine": launch["machine_token"]}
        return child, base, receipt, tokens
    except BaseException:
        stop(child)
        raise


def wait_for_readiness(child: subprocess.Popen, port: int, timeout: float) -> str:
    """Drain both pipes for the child's lifetime; return only a validated URL.

    Port zero accepts the OS-selected loopback port. On failure the owned child
    is terminated and reaped. The caller owns stop(child) after successful use.
    """
    ready = threading.Event()
    readiness = []
    stream_failed = threading.Event()

    def drain(stream, capture=False):
        # Bounded buffer, including a child that never emits a newline. Never echo
        # child output: it may contain the private stdin handshake.
        line = ""
        try:
            while character := stream.read(1):
                if character == "\n":
                    if capture and not readiness and READY_MARKER in line:
                        readiness.append(line)
                        ready.set()
                    line = ""
                elif capture:
                    line = (line + character)[-4096:]
        except (OSError, UnicodeError):
            stream_failed.set()
            ready.set()
        finally:
            with suppress(OSError):
                stream.close()

    readers = [threading.Thread(target=drain, args=(child.stdout, True), daemon=True),
               threading.Thread(target=drain, args=(child.stderr,), daemon=True)]
    child._archeaxis_readers = readers
    for reader in readers:
        reader.start()
    try:
        deadline = time.monotonic() + timeout
        while not ready.wait(min(0.05, max(0, deadline - time.monotonic()))):
            if child.poll() is not None:
                raise LaunchFailure(f"Core exited before becoming ready (exit {child.returncode})")
            if time.monotonic() >= deadline:
                raise LaunchFailure(f"Core did not report readiness within {timeout:g}s")
        # Accept only this launch's loopback endpoint; arbitrary output never enters
        # the public receipt, even when a compromised child echoes its handshake.
        if stream_failed.is_set():
            raise LaunchFailure("Core output stream failed")
        match = re.fullmatch(r"archeaxis-api ready on http://127\.0\.0\.1:([0-9]{1,5})", readiness[0].strip())
        if match is None or not 1 <= int(match[1]) <= 65535 or (port and int(match[1]) != port):
            raise LaunchFailure("Core reported invalid readiness endpoint")
        return f"http://127.0.0.1:{int(match[1])}"
    except BaseException:
        stop(child)
        raise


def credential(tokens: dict | None, role: str) -> dict:
    """The request header that authenticates *role* against the Core.

    The Core reads exactly one credential header, `x-archeaxis-launch-token`, and
    matches its value against either the launch token or the machine token before
    deriving the actor from whichever matched (`launch.rs::authenticate`).  The
    machine token therefore travels in that same header; there is no separate
    `x-archeaxis-machine-token` header in the protocol, and sending one would be
    ignored.  Selecting the value here means a caller cannot pick the wrong header
    and silently act as the other principal.
    """
    if role not in {"human", "machine"}:
        raise LaunchFailure(f"unknown credential role: {role}")
    if not tokens:
        raise LaunchFailure(f"no credentials were issued for role: {role}")
    value = tokens.get(role)
    if not value:
        raise LaunchFailure(f"missing credential for role: {role}")
    return {"x-archeaxis-launch-token": value}


def call(base: str, method: str, path: str, body: dict | None = None,
         tokens: dict | None = None, *,
         header_tokens: dict | None = None,
         role: str | None = None) -> tuple[int, object]:
    """Every route is authenticated per request by the launch layer.

    The Core matches `x-archeaxis-launch-token` against the token it accepted on
    stdin and answers `AAK-AUTH-001` otherwise, so a caller that forgets it sees a
    bare 401 rather than a startup problem.

    Pass `role` with the credentials returned by `start` to authenticate as that
    principal.  `header_tokens` is the raw header mapping, for callers that build
    their own headers.
    """
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(base + path, data=data, method=method)
    if data is not None:
        request.add_header("content-type", "application/json")
    headers = dict(header_tokens or {})
    if role is not None:
        headers.update(credential(tokens, role))
    for name, value in headers.items():
        request.add_header(name, value)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = response.read().decode("utf-8")
            return response.status, json.loads(payload) if payload else {}
    except urllib.error.HTTPError as error:
        payload = error.read().decode("utf-8")
        try:
            return error.code, json.loads(payload)
        except json.JSONDecodeError:
            return error.code, payload


def stop(child: subprocess.Popen) -> int:
    try:
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=15)
        return child.returncode or 0
    finally:
        for reader in getattr(child, "_archeaxis_readers", []):
            reader.join(timeout=1)
        for stream in (child.stdin, child.stdout, child.stderr):
            if stream is not None and not stream.closed:
                with suppress(OSError):
                    stream.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=ROOT / "data")
    parser.add_argument("--port", type=int, default=0,
                        help="0 (default) lets the OS choose a free port")
    parser.add_argument("--smoke", action="store_true",
                        help="after readiness, call the first exchange and shut down")
    args = parser.parse_args()

    port = args.port or free_port()
    try:
        child, base, receipt, tokens = start(safe_path(ROOT, str(args.data_root)), port)
    except (LaunchFailure, OSError) as error:
        print(json.dumps({"ok": False, "failure": str(error)}, ensure_ascii=False, indent=2))
        return 2

    receipt["base_url"] = base
    if args.smoke:
        try:
            status, version = call(base, "GET", "/api/v1/system/version",
                                   tokens=tokens, role="human")
            receipt["system_version"] = {"status": status, "body": version}
            status, info = call(base, "GET", "/api/v1/workspaces/info",
                                tokens=tokens, role="human")
            receipt["workspaces_info"] = {"status": status, "body": info}
        finally:
            receipt["exit_code"] = stop(child)
        receipt["ok"] = (
            isinstance(receipt.get("system_version"), dict)
            and receipt["system_version"]["status"] == 200
            and isinstance(receipt.get("workspaces_info"), dict)
            and receipt["workspaces_info"]["status"] == 200
        )
        receipt["shutdown"] = "terminated"
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 0 if receipt["ok"] else 1

    receipt["ok"] = True
    try:
        print(json.dumps(receipt, ensure_ascii=False, indent=2), flush=True)
        return child.wait()
    except KeyboardInterrupt:
        return 130
    finally:
        stop(child)


if __name__ == "__main__":
    raise SystemExit(main())
