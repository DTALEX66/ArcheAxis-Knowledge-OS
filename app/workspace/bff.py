"""Read-only Workspace BFF projections.

The v1 BFF is deliberately narrower than the legacy workspace compatibility API:
no command, persistence, or approval identifiers cross this boundary.
"""
from __future__ import annotations

import base64
import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class BFFUnavailableError(RuntimeError):
    """The projection cannot be read safely from the current local database."""


class BFFNotFoundError(LookupError):
    """The opaque public reference does not identify a supported object."""


@dataclass(frozen=True)
class ActivityPage:
    items: list[dict[str, Any]]
    next_cursor: str | None


def public_ref(kind: str, value: str) -> str:
    """Return a stable opaque reference without exposing persistence identifiers.

    This is an object reference, not an authorization credential. Local loopback
    isolation remains the authorization boundary.
    """
    material = f"archeaxis-workspace-bff-v1\0{kind}\0{value}".encode()
    return f"wr1_{hashlib.sha256(material).hexdigest()[:32]}"


def _cursor_encode(updated_at: str, reference: str) -> str:
    raw = f"{updated_at}\0{reference}".encode()
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _cursor_decode(cursor: str) -> tuple[str, str]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        updated_at, reference = base64.urlsafe_b64decode(padded).decode("utf-8").split("\0", 1)
    except (ValueError, UnicodeDecodeError, base64.binascii.Error) as exc:
        raise ValueError("invalid activity cursor") from exc
    if not updated_at or not reference:
        raise ValueError("invalid activity cursor")
    return updated_at, reference


def _connection(db_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(Path(db_path), timeout=30.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout=30000")
    connection.execute("PRAGMA query_only=ON")
    return connection


def _require_table(connection: sqlite3.Connection, table: str) -> None:
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    if exists is None:
        raise BFFUnavailableError(f"workspace projection table unavailable: {table}")


def _activity_rows(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    _require_table(connection, "workspace_jobs_v1")
    _require_table(connection, "research_packages_v1")
    rows: list[dict[str, Any]] = []
    for row in connection.execute(
        "SELECT job_id, state, updated_at FROM workspace_jobs_v1"
    ).fetchall():
        reference = public_ref("job", str(row["job_id"]))
        rows.append(
            {
                "public_ref": reference,
                "kind": "job",
                "label": "资料导入",
                "state": str(row["state"]),
                "updated_at": str(row["updated_at"]),
            }
        )
    for row in connection.execute(
        "SELECT canonical_url, status, created_at FROM research_packages_v1"
    ).fetchall():
        reference = public_ref("source", str(row["canonical_url"]))
        rows.append(
            {
                "public_ref": reference,
                "kind": "source",
                "label": "研究资料",
                "state": str(row["status"]),
                "updated_at": str(row["created_at"]),
            }
        )
    return sorted(
        rows,
        key=lambda item: (item["updated_at"], item["public_ref"]),
        reverse=True,
    )


def activity(*, db_path: str | Path, limit: int = 20, cursor: str | None = None) -> dict[str, Any]:
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")
    with _connection(db_path) as connection:
        rows = _activity_rows(connection)
    if cursor:
        cursor_time, cursor_ref = _cursor_decode(cursor)
        rows = [
            item
            for item in rows
            if (item["updated_at"], item["public_ref"]) < (cursor_time, cursor_ref)
        ]
    page = rows[:limit]
    next_cursor = None
    if len(rows) > limit:
        tail = page[-1]
        next_cursor = _cursor_encode(tail["updated_at"], tail["public_ref"])
    return {"schema_version": "v1", "items": page, "next_cursor": next_cursor}


def _object_from_row(kind: str, row: sqlite3.Row) -> dict[str, Any]:
    if kind == "job":
        value = str(row["job_id"])
        return {
            "schema_version": "v1",
            "kind": "job",
            "public_ref": public_ref(kind, value),
            "label": "资料导入",
            "state": str(row["state"]),
            "updated_at": str(row["updated_at"]),
        }
    value = str(row["canonical_url"])
    return {
        "schema_version": "v1",
        "kind": "source",
        "public_ref": public_ref(kind, value),
        "label": "研究资料",
        "source": value,
        "state": str(row["status"]),
        "updated_at": str(row["created_at"]),
    }


def object_by_ref(*, db_path: str | Path, reference: str) -> dict[str, Any]:
    if not reference.startswith("wr1_") or len(reference) != 36:
        raise BFFNotFoundError("workspace object was not found")
    with _connection(db_path) as connection:
        _require_table(connection, "workspace_jobs_v1")
        for row in connection.execute(
            "SELECT job_id, state, updated_at FROM workspace_jobs_v1"
        ).fetchall():
            if public_ref("job", str(row["job_id"])) == reference:
                return _object_from_row("job", row)
        _require_table(connection, "research_packages_v1")
        for row in connection.execute(
            "SELECT canonical_url, status, created_at FROM research_packages_v1"
        ).fetchall():
            if public_ref("source", str(row["canonical_url"])) == reference:
                return _object_from_row("source", row)
    raise BFFNotFoundError("workspace object was not found")


def home(*, db_path: str | Path) -> dict[str, Any]:
    from app.workspace.service import workspace_status

    status = workspace_status(db_path=db_path)
    recent = activity(db_path=db_path, limit=5)["items"]
    return {
        "schema_version": "v1",
        "observed_at": status["observed_at"],
        "release": status["release"],
        "components": status["components"],
        "counts": status["counts"],
        "capabilities": status["capabilities"],
        "recent_activity": recent,
    }
