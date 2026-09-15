"""Read-only environment capability registry resolver.

This resolves the repository's declared capability requirements to observable
command availability. It never installs tools, expands user paths, or runs a
healthcheck command supplied by configuration.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - the project preflight reports this
    yaml = None


def _command_name(command: str | None) -> str | None:
    if not command:
        return None
    match = re.match(r"\s*([\w.-]+)", command)
    return match.group(1) if match else None


def _probe_version(executable: str | None, path: str | None) -> tuple[str | None, str]:
    if not path:
        return None, "missing"
    try:
        result = subprocess.run([path, "--version"], capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=5, check=False)
    except (OSError, subprocess.SubprocessError):
        return None, "probe_failed"
    if result.returncode != 0:
        return None, "probe_failed"
    line = (result.stdout or result.stderr).splitlines()
    return (line[0].strip()[:200] if line and line[0].strip() else None), "probed"


def _external_path(entry: dict) -> str | None:
    """Resolve a declared shared-tool path without guessing or installing.

    The root is supplied explicitly by the caller so a missing PATH entry does
    not hide an already-installed shared tool.  Relative candidates are kept
    relative to that root and absolute candidates are ignored for safety.
    """
    root_value = os.environ.get("ARCHEAXIS_EXTERNAL_ROOT", "").strip() or os.environ.get("OS_EXTERNAL_CONFIG", "").strip()
    if not root_value:
        return None
    root = Path(root_value).expanduser()
    if not root.is_absolute():
        return None
    for candidate in entry.get("external_paths", []) or []:
        if not isinstance(candidate, str) or not candidate.strip():
            continue
        relative = Path(candidate)
        if relative.is_absolute() or ".." in relative.parts:
            continue
        path = (root / relative).resolve()
        if (path.is_file() or path.is_dir()) and path.is_relative_to(root.resolve()):
            return str(path)
    return None


def _display_path(path: str | None, *, external: bool) -> str | None:
    """Return a sanitized path label for reports, never a private absolute path."""
    if not path:
        return None
    return f"external:{Path(path).name}" if external else f"path:{Path(path).name}"


def resolve(manifest: Path) -> dict:
    if yaml is None:
        raise RuntimeError("PyYAML is required to resolve the environment registry")
    data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    capabilities = data.get("capabilities", {})
    resolved: list[dict] = []
    for category, entries in capabilities.items():
        for entry in entries or []:
            command = entry.get("healthcheck_command")
            executable = _command_name(command)
            path = shutil.which(executable) if executable else None
            external = False
            if not path:
                path = _external_path(entry)
                external = bool(path)
            version, probe_status = _probe_version(executable, path)
            resolved.append({
                "id": f"{category}/{entry.get('name', '')}",
                "category": category,
                "name": entry.get("name"),
                "version_range": entry.get("version_range"),
                "required_by": entry.get("required_by", []),
                "local_only": bool(entry.get("local_only", False)),
                "source_url": entry.get("source_url"),
                "healthcheck_command": command,
                "executable": executable,
                "available": bool(path),
                "resolved_path": _display_path(path, external=external),
                "version_observed": version,
                "probe": probe_status,
            })
    return {
        "schema": "archeaxis.environment-registry/v1",
        "manifest": str(manifest),
        "manifest_schema_version": data.get("schema_version"),
        "capabilities": resolved,
        "summary": {
            "total": len(resolved),
            "available": sum(bool(item["available"]) for item in resolved),
            "missing": sum(not item["available"] for item in resolved),
        },
        "install_performed": False,
        "private_state_opened": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(resolve(args.manifest.resolve()), ensure_ascii=False, indent=2))
    except (OSError, RuntimeError, ValueError) as error:
        print(json.dumps({"schema": "archeaxis.environment-registry/v1", "error": str(error)}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
