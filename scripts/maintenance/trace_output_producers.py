"""Read-only structural trace of project output-path producers.

The tracer inspects source/config text in an exact Git worktree and emits
*candidates* for review.  It never opens private runtime directories, follows
reparse points, starts processes, or changes configuration.  A candidate is
not proof that a path was written at runtime; the evidence field says which
source file and line exposed the path token.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
from pathlib import Path

PRIVATE_NAMES = frozenset({
    ".git", ".codex", ".zcode", ".hermes", ".dsh", ".openhuman", ".agents",
    ".project-local", ".venv", "venv", "node_modules", "target", "dist", "build",
    "sessions", "memories", "credentials", "auth",
})
TEXT_SUFFIXES = frozenset({
    ".py", ".ps1", ".psm1", ".psd1", ".sh", ".cmd", ".bat", ".yml", ".yaml",
    ".toml", ".json", ".ini", ".cfg", ".conf", ".md", ".cs", ".csproj",
    ".rs", ".ts", ".tsx", ".js", ".jsx", ".xml",
})

# Deliberately broad enough to find a producer, but values are reported as a
# token only and never as the complete source line (which could contain a
# secret or user data).
TOKEN_RE = re.compile(
    r"(?P<token>ARCHEAXIS_[A-Z0-9_]+|(?:CARGO|UV|PIP|NPM|PLAYWRIGHT|NUGET|DOTNET|TEMP|TMP|HOME)[A-Z0-9_]*(?:DIR|ROOT|PATH|HOME|CACHE|TARGET))",
    re.IGNORECASE,
)


def _is_reparse(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return True
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def _validate_root(root: Path) -> Path:
    text = os.fspath(root).replace("\\", "/")
    if text.casefold().startswith(("e:", "//")):
        raise ValueError("protected drive or UNC root is not permitted")
    root = Path(os.path.abspath(root))
    if any(_is_reparse(part) for part in (*reversed(root.parents), root)):
        raise ValueError("root and ancestors must not be links or reparse points")
    if not root.is_dir():
        raise ValueError("root must be a directory")
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    if result.returncode or os.path.normcase(os.path.abspath(result.stdout.strip())) != os.path.normcase(str(root)):
        raise ValueError("root must be the exact Git project root")
    return root


def trace_output_producers(root: Path) -> dict:
    """Return deterministic source candidates without reading private paths."""
    root = _validate_root(Path(root))
    rows: list[dict] = []
    seen: set[tuple[str, str]] = set()
    skipped: list[dict] = []
    for directory, dirs, files in os.walk(root, topdown=True, followlinks=False):
        directory_path = Path(directory)
        dirs[:] = [name for name in dirs if name.casefold() not in PRIVATE_NAMES]
        for name in sorted(files):
            path = directory_path / name
            relative = path.relative_to(root).as_posix()
            if any(part.casefold() in PRIVATE_NAMES for part in Path(relative).parts):
                continue
            if path.suffix.casefold() not in TEXT_SUFFIXES:
                continue
            try:
                if _is_reparse(path):
                    skipped.append({"path": relative, "reason": "reparse_point"})
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                skipped.append({"path": relative, "reason": type(exc).__name__})
                continue
            for line_number, line in enumerate(text.splitlines(), 1):
                for match in TOKEN_RE.finditer(line):
                    token = match.group("token")
                    key = (relative.casefold(), token.casefold())
                    if key in seen:
                        continue
                    seen.add(key)
                    producer = relative
                    if relative.casefold().startswith("scripts/runtime/"):
                        owner = "project runtime routing"
                    elif relative.casefold().startswith("scripts/"):
                        owner = "project script entrypoint"
                    elif relative.casefold().startswith("config/"):
                        owner = "project configuration"
                    else:
                        owner = "project source; runtime owner requires review"
                    rows.append({
                        "canonical_path": token,
                        "producer": producer,
                        "entrypoint": relative,
                        "config_source": relative if relative.casefold().startswith("config/") else "source reference",
                        "owner_evidence": f"{relative}:{line_number} token={token}; owner={owner}",
                        "shared_users": "unverified; inspect callers",
                        "authorization_basis": "project source inspection only",
                        "planned_fix": "route project-owned output through .project-local; review external/shared paths",
                        "result": "candidate_structural_only",
                    })
    rows.sort(key=lambda row: (row["entrypoint"].casefold(), row["owner_evidence"].casefold()))
    return {
        "schema": "archeaxis.output-producer-trace/v1",
        "mode": "read_only_structural_candidates",
        "root": str(root),
        "rows": rows,
        "skipped": sorted(skipped, key=lambda row: row["path"].casefold()),
        "limitations": [
            "Static tokens are candidates, not proof of runtime writes.",
            "Private agent/runtime directories are opaque and were not read.",
            "Process command lines, logs, and external roots require separate explicit authorization.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path,
                        help="optional JSON destination inside <root>/.project-local")
    args = parser.parse_args()
    try:
        report = trace_output_producers(args.root)
        if args.output:
            root = Path(os.path.abspath(args.root))
            output = Path(os.path.abspath(args.output))
            try:
                output.relative_to(root / ".project-local")
            except ValueError as exc:
                raise ValueError("output path must be inside .project-local") from exc
            if any(_is_reparse(part) for part in (*reversed(output.parents), output) if part.exists()):
                raise ValueError("output path must not contain links or reparse points")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=True))
        return 1
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
