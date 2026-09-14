"""Read-only environment capability registry resolver.

This resolves the repository's declared capability requirements to observable
command availability. It never installs tools, expands user paths, or runs a
healthcheck command supplied by configuration.
"""

from __future__ import annotations

import argparse
import json
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
                "resolved_path": path,
                "probe": "command_presence_only",
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
