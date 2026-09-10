#!/usr/bin/env python3
"""Language boundary contract check (R15 / X13).

`docs/LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md` states the boundary as prose and
`scripts/ci/check_vnext_contracts.py` says in its own docstring that "semantic
cross-language consistency" is somebody else's job. This is that job: it checks
the boundary against the real tree instead of trusting the prose.

Ownership checks (who may do what):
  * database ownership - the SQLite driver is declared only by Rust crates, so a
    Python worker or the desktop shell cannot become a second writer;
  * Python workers hold no database handle - no driver import and no rusqlite
    reference under `services/python-workers/`;
  * the desktop shell is a shell - no SQL client package reference or `using`.

Interoperability check (do the three languages agree?):
  * every `archeaxis.worker-*/vN` envelope literal in Rust, Python and the JSON
    schemas carries the same major version;
  * that version equals `PROTOCOL_VERSION` in the sidecar protocol crate;
  * the Python hello advertises the same major and the schema constrains the same
    major, so a handler that only reads one language still cannot drift silently.

Exit code is 1 with the failures named by file whenever the boundary is crossed;
never an empty success. Both checks are structural: passing here means the
boundary is *described consistently*, not that behaviour has been exercised.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

IGNORED_PARTS = {".git", ".project-local", ".hermes", "target", ".venv", "node_modules", "bin", "obj"}

ENVELOPE_RE = re.compile(r"archeaxis\.worker-([a-z][a-z-]*)/v(\d+)")
PROTOCOL_VERSION_RE = re.compile(r"pub const PROTOCOL_VERSION\s*:\s*u32\s*=\s*(\d+)\s*;")
PY_HELLO_MAJOR_RE = re.compile(r"\"protocol\"\s*:\s*\{\s*\"major\"\s*:\s*(\d+)")

SQL_DRIVER_IN_TOML_RE = re.compile(r"^\s*(rusqlite|sqlx|libsqlite3-sys|diesel|sqlite)\s*=", re.MULTILINE)
PY_DRIVER_IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+(sqlite3|psycopg2?|sqlalchemy|duckdb|pymysql)\b", re.MULTILINE)
CS_SQL_MARKERS = ("sqlite", "npgsql", "dapper", "entityframework", "sqlclient", "mysql", "oracle", "npgsql")


def _ignored(root: Path, path: Path) -> bool:
    """Ignore by position *inside* the tree, never by the caller's absolute path.

    A checkout or a test tree can legitimately live under an ignored directory
    name (e.g. a pytest tmp dir under `.project-local/`); matching the absolute
    path would silently skip every file and turn the check into a no-op.
    """
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        parts = path.parts
    return any(part in IGNORED_PARTS for part in parts)


def _walk(root: Path, subdir: str, suffix: str):
    base = root / subdir
    if not base.is_dir():
        return []
    found = []
    for path in base.rglob(f"*{suffix}"):
        if _ignored(root, path):
            continue
        found.append(path)
    return sorted(found)


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def _read_text(path: Path) -> str:
    """Read text with any byte-order mark removed.

    A BOM at the start of a file stops `^` from matching there, which would make
    every line-anchored rule below silently skip that file. Windows editors write
    BOMs often enough that this is a real way for a gate to become a no-op.
    """
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _envelope_versions(root: Path, subdir: str, suffix: str) -> list[tuple[str, str, int]]:
    """(file, envelope name, major version) for every literal in `subdir`."""
    found = []
    for path in _walk(root, subdir, suffix):
        for name, version in ENVELOPE_RE.findall(_read_text(path)):
            found.append((_rel(root, path), name, int(version)))
    return found


def check_database_ownership(root: Path) -> list[str]:
    """The SQLite driver must be declared by Rust crates only."""
    failures = []
    for toml in sorted(root.rglob("Cargo.toml")):
        if _ignored(root, toml):
            continue
        rel = _rel(root, toml)
        if not rel.startswith("crates/"):
            match = SQL_DRIVER_IN_TOML_RE.search(_read_text(toml))
            if match:
                failures.append(
                    f"{rel}: declares the SQL driver '{match.group(1)}' outside crates/; "
                    "the Rust Core is the only database owner"
                )
    return failures


def check_python_workers_are_database_free(root: Path) -> list[str]:
    """A worker gets staged bytes, never a database handle."""
    failures = []
    for path in _walk(root, "services/python-workers", ".py"):
        text = _read_text(path)
        match = PY_DRIVER_IMPORT_RE.search(text)
        if match:
            failures.append(f"{_rel(root, path)}: imports the database driver '{match.group(1)}'; workers are isolated")
        if "rusqlite" in text:
            failures.append(f"{_rel(root, path)}: references rusqlite; workers never hold the database")
    return failures


def check_desktop_shell_has_no_sql_client(root: Path) -> list[str]:
    """The desktop is UI and Supervisor: no direct SQL, no duplicated rules."""
    failures = []
    for path in _walk(root, "apps/ArcheAxis.Desktop", ".csproj"):
        text = _read_text(path)
        # compare lowercase against lowercase: a case-sensitive needle here would
        # make the rule a silent no-op on every real (capitalised) package id
        for package in re.findall(r'Include\s*=\s*"([^"]+)"', text):
            lowered = package.lower()
            if any(marker in lowered for marker in CS_SQL_MARKERS):
                failures.append(f"{_rel(root, path)}: references an SQL client package '{package}'")
    for path in _walk(root, "apps/ArcheAxis.Desktop", ".cs"):
        lowered = _read_text(path).lower()
        for marker in ("using microsoft.data.sqlite", "using system.data.sqlite", "using npgsql"):
            if marker in lowered:
                failures.append(f"{_rel(root, path)}: '{marker}' - the shell must not open SQL directly")
    return failures


def check_protocol_literals_agree(root: Path) -> tuple[list[str], dict]:
    """Rust, Python and the JSON schemas must name the same protocol major."""
    failures: list[str] = []
    rust = _envelope_versions(root, "crates", ".rs")
    python = _envelope_versions(root, "services/python-workers", ".py")
    schemas = _envelope_versions(root, "packages/contracts", ".json")

    source = root / "crates/archeaxis-sidecar-protocol/src/lib.rs"
    version = None
    if source.is_file():
        match = PROTOCOL_VERSION_RE.search(_read_text(source))
        version = int(match.group(1)) if match else None
    if version is None:
        failures.append("crates/archeaxis-sidecar-protocol/src/lib.rs: PROTOCOL_VERSION not found")

    # the contract directory names the version the whole boundary ships as, so the
    # expected number comes from the artefacts rather than a literal in this file
    contracts_root = root / "packages/contracts"
    contract_versions = sorted(
        {int(match.group(1)) for path in contracts_root.glob("v*") if (match := re.fullmatch(r"v(\d+)", path.name))}
    )
    if len(contract_versions) != 1:
        failures.append(
            f"packages/contracts: expected exactly one version directory, found {sorted(p.name for p in contracts_root.glob('v*'))}"
        )
    elif version is not None and contract_versions[0] != version:
        failures.append(
            f"packages/contracts/v{contract_versions[0]} disagrees with PROTOCOL_VERSION={version}"
        )

    observed: dict[str, set[int]] = {}
    for label, entries in (("rust", rust), ("python", python), ("schemas", schemas)):
        versions = {entry[2] for entry in entries}
        observed[label] = versions
        if not entries:
            failures.append(f"{label}: no archeaxis.worker-*/vN envelope literal found")
        if len(versions) > 1:
            detail = ", ".join(f"{file}->{name}/v{ver}" for file, name, ver in entries)
            failures.append(f"{label}: envelope versions disagree inside one language: {detail}")

    everything = {entry[2] for entry in rust + python + schemas}
    if len(everything) > 1:
        detail = ", ".join(f"{file}->{name}/v{ver}" for file, name, ver in rust + python + schemas)
        failures.append(f"cross-language envelope versions disagree: {detail}")
    if version is not None and everything and everything != {version}:
        failures.append(f"PROTOCOL_VERSION={version} but the envelope literals are {sorted(everything)}")

    # the Python hello must advertise the same major it speaks
    transport = root / "services/python-workers/transport/text_ndjson.py"
    py_major = None
    if transport.is_file():
        match = PY_HELLO_MAJOR_RE.search(_read_text(transport))
        py_major = int(match.group(1)) if match else None
        if py_major is None:
            failures.append("services/python-workers/transport/text_ndjson.py: hello does not advertise a protocol major")
        elif version is not None and py_major != version:
            failures.append(
                f"python hello advertises major {py_major} while PROTOCOL_VERSION is {version}"
            )

    # the schema must constrain the same major it names
    protocol_schema = root / "packages/contracts/v1/worker-protocol.schema.json"
    schema_major = None
    if protocol_schema.is_file():
        try:
            payload = json.loads(_read_text(protocol_schema))
            schema_major = payload["$defs"]["hello"]["properties"]["protocol"]["properties"]["major"]["const"]
        except (json.JSONDecodeError, KeyError, TypeError) as error:
            failures.append(f"packages/contracts/v1/worker-protocol.schema.json: cannot read the hello major const: {error}")
        if schema_major is not None and version is not None and int(schema_major) != version:
            failures.append(f"worker-protocol schema constrains major {schema_major} while PROTOCOL_VERSION is {version}")

    names = {entry[1] for entry in rust + python + schemas}
    detail = {
        "protocol_version": version,
        "contracts_version": contract_versions[0] if len(contract_versions) == 1 else None,
        "rust_majors": sorted(observed.get("rust", set())),
        "python_majors": sorted(observed.get("python", set())),
        "schema_majors": sorted(observed.get("schemas", set())),
        "python_hello_major": py_major,
        "schema_hello_major": schema_major,
        "envelope_names": sorted(names),
    }
    return failures, detail


def run(root: Path = ROOT) -> tuple[list[str], dict]:
    failures: list[str] = []
    failures += check_database_ownership(root)
    failures += check_python_workers_are_database_free(root)
    failures += check_desktop_shell_has_no_sql_client(root)
    protocol_failures, detail = check_protocol_literals_agree(root)
    failures += protocol_failures
    detail["root"] = str(root)
    return failures, detail


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    as_json = "--json" in argv
    failures, detail = run(ROOT)
    if as_json:
        print(json.dumps({"passed": not failures, "failures": failures, **detail}, ensure_ascii=False, indent=2))
    elif failures:
        print("language boundary check failed:")
        for item in failures:
            print(f"  - {item}")
    else:
        print(
            "language boundary check passed: "
            f"protocol major {detail['protocol_version']} agreed by rust/python/schemas; "
            "database owner = crates/ only; workers and desktop shell hold no database handle"
        )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
