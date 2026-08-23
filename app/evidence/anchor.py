"""AXW-020C: EvidenceAnchor and IndexRevision.

An EvidenceAnchor locates content within a source version — by page, block,
character/region, or source revision. An IndexRevision records a rebuildable
derived index (FTS/vector) that must never be presented as the source of
truth; its rebuild count and source revision distinguish derived index from the
original.
"""
from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _stable_id(prefix: str, *parts: object) -> str:
    payload = json.dumps(parts, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return f"{prefix}_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


@dataclass(frozen=True)
class EvidenceAnchor:
    anchor_id: str
    raw_sha256: str
    source_revision: str
    locator: dict[str, Any]


@dataclass(frozen=True)
class IndexRevision:
    revision_id: str
    raw_sha256: str
    index_name: str
    source_revision: str
    rebuild_count: int


def build_evidence_anchor(
    raw_sha256: str, source_revision: str, locator: dict[str, Any]
) -> EvidenceAnchor:
    """Build a stable EvidenceAnchor from a raw source hash, a source revision
    and a locator (page/block/char-region). Empty locator or revision is
    rejected: an anchor must always pin content to a specific source version.
    """
    if not raw_sha256:
        raise ValueError("evidence anchor requires a raw source hash")
    if not source_revision:
        raise ValueError("evidence anchor requires a source revision")
    if not locator:
        raise ValueError("evidence anchor requires a non-empty locator")
    anchor_id = _stable_id("ev", raw_sha256, source_revision, locator)
    return EvidenceAnchor(
        anchor_id=anchor_id,
        raw_sha256=raw_sha256,
        source_revision=source_revision,
        locator=locator,
    )


_ANCHOR_SCHEMA = """
CREATE TABLE IF NOT EXISTS evidence_anchors (
    anchor_id TEXT PRIMARY KEY,
    raw_sha256 TEXT NOT NULL,
    source_revision TEXT NOT NULL,
    locator_json TEXT NOT NULL
);
"""
_INDEX_SCHEMA = """
CREATE TABLE IF NOT EXISTS index_revisions (
    revision_id TEXT PRIMARY KEY,
    raw_sha256 TEXT NOT NULL,
    index_name TEXT NOT NULL,
    source_revision TEXT NOT NULL,
    rebuild_count INTEGER NOT NULL
);
"""

_ANCHOR_CURSOR_PREFIX = "evidence-anchor-v1:"


def ensure_evidence_anchor_schema(db: str | Path) -> None:
    """Create the evidence-anchor schema before a caller-owned transaction."""
    with sqlite3.connect(Path(db)) as connection:
        connection.executescript(_ANCHOR_SCHEMA)


def _anchor_payload(anchor: EvidenceAnchor) -> tuple[str, str, str]:
    return (
        anchor.raw_sha256,
        anchor.source_revision,
        json.dumps(anchor.locator, ensure_ascii=True, sort_keys=True),
    )


def store_evidence_anchor_on_connection(
    connection: sqlite3.Connection, anchor: EvidenceAnchor
) -> None:
    """Persist an immutable anchor in a caller-owned transaction.

    A deterministic replay is a no-op; a conflicting anchor id is rejected so
    callers cannot silently replace a historical evidence locator.
    """
    existing = connection.execute(
        "SELECT raw_sha256, source_revision, locator_json FROM evidence_anchors WHERE anchor_id=?",
        (anchor.anchor_id,),
    ).fetchone()
    expected = _anchor_payload(anchor)
    if existing is not None:
        if tuple(str(value) for value in existing) == expected:
            return
        raise RuntimeError("evidence anchor id conflicts with an immutable receipt")
    connection.execute(
        "INSERT INTO evidence_anchors "
        "(anchor_id, raw_sha256, source_revision, locator_json) VALUES (?,?,?,?)",
        (anchor.anchor_id, *expected),
    )


def store_evidence_anchor(db: str | Path, anchor: EvidenceAnchor) -> None:
    ensure_evidence_anchor_schema(db)
    with sqlite3.connect(Path(db)) as connection:
        store_evidence_anchor_on_connection(connection, anchor)
        connection.commit()


def resolve_evidence_anchor(db: str | Path, anchor_id: str) -> EvidenceAnchor | None:
    with sqlite3.connect(Path(db)) as conn:
        conn.row_factory = sqlite3.Row
        conn.executescript(_ANCHOR_SCHEMA)
        row = conn.execute(
            "SELECT * FROM evidence_anchors WHERE anchor_id=?", (anchor_id,)
        ).fetchone()
    if row is None:
        return None
    return EvidenceAnchor(
        anchor_id=row["anchor_id"],
        raw_sha256=row["raw_sha256"],
        source_revision=row["source_revision"],
        locator=json.loads(row["locator_json"]),
    )


def list_evidence_anchors(db: str | Path) -> list[EvidenceAnchor]:
    """Return every stored evidence anchor (insertion order)."""
    with sqlite3.connect(Path(db)) as conn:
        conn.row_factory = sqlite3.Row
        conn.executescript(_ANCHOR_SCHEMA)
        rows = conn.execute(
            "SELECT * FROM evidence_anchors ORDER BY rowid"
        ).fetchall()
    return [
        EvidenceAnchor(
            anchor_id=row["anchor_id"],
            raw_sha256=row["raw_sha256"],
            source_revision=row["source_revision"],
            locator=json.loads(row["locator_json"]),
        )
        for row in rows
    ]


def _encode_anchor_cursor(rowid: int) -> str:
    payload = f"{_ANCHOR_CURSOR_PREFIX}{rowid}".encode("ascii")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_anchor_cursor(cursor: str) -> int:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = base64.urlsafe_b64decode(padded.encode("ascii")).decode("ascii")
        prefix, rowid_text = payload.rsplit(":", 1)
        rowid = int(rowid_text)
    except (UnicodeEncodeError, UnicodeDecodeError, ValueError, base64.binascii.Error) as exc:
        raise ValueError("invalid evidence anchor cursor") from exc
    if f"{prefix}:" != _ANCHOR_CURSOR_PREFIX or rowid < 1:
        raise ValueError("invalid evidence anchor cursor")
    return rowid


def list_evidence_anchor_page(
    db: str | Path, *, limit: int = 50, cursor: str | None = None
) -> tuple[list[EvidenceAnchor], str | None]:
    """Read a bounded insertion-ordered anchor page with an opaque cursor."""
    if not 1 <= limit <= 100:
        raise ValueError("evidence anchor page limit must be between 1 and 100")
    after_rowid = _decode_anchor_cursor(cursor) if cursor else 0
    with sqlite3.connect(Path(db)) as conn:
        conn.row_factory = sqlite3.Row
        conn.executescript(_ANCHOR_SCHEMA)
        rows = conn.execute(
            "SELECT rowid, anchor_id, raw_sha256, source_revision, locator_json "
            "FROM evidence_anchors WHERE rowid>? ORDER BY rowid LIMIT ?",
            (after_rowid, limit + 1),
        ).fetchall()
    page_rows = rows[:limit]
    next_cursor = _encode_anchor_cursor(int(page_rows[-1]["rowid"])) if len(rows) > limit else None
    return (
        [
            EvidenceAnchor(
                anchor_id=row["anchor_id"],
                raw_sha256=row["raw_sha256"],
                source_revision=row["source_revision"],
                locator=json.loads(row["locator_json"]),
            )
            for row in page_rows
        ],
        next_cursor,
    )


def mark_index_revision(
    db: str | Path,
    raw_sha256: str,
    index_name: str,
    source_revision: str,
) -> IndexRevision:
    """Record a rebuildable derived index revision. The index points at the raw
    source hash so it can never be mistaken for the source of truth itself."""
    if not raw_sha256:
        raise ValueError("index revision requires a raw source hash")
    if not index_name:
        raise ValueError("index revision requires an index name")
    revision_id = _stable_id("idx", raw_sha256, index_name)
    revision = IndexRevision(
        revision_id=revision_id,
        raw_sha256=raw_sha256,
        index_name=index_name,
        source_revision=source_revision,
        rebuild_count=1,
    )
    with sqlite3.connect(Path(db)) as conn:
        conn.executescript(_INDEX_SCHEMA)
        conn.execute(
            "INSERT OR REPLACE INTO index_revisions "
            "(revision_id, raw_sha256, index_name, source_revision, rebuild_count) VALUES (?,?,?,?,?)",
            (
                revision.revision_id,
                revision.raw_sha256,
                revision.index_name,
                revision.source_revision,
                revision.rebuild_count,
            ),
        )
        conn.commit()
    return revision


def rebuild_index_revision(
    db: str | Path, revision_id: str, new_source_revision: str
) -> IndexRevision | None:
    """Rebuild an existing derived index against a (possibly newer) source
    revision, incrementing the rebuild count. Returns None if unknown."""
    with sqlite3.connect(Path(db)) as conn:
        conn.row_factory = sqlite3.Row
        conn.executescript(_INDEX_SCHEMA)
        row = conn.execute(
            "SELECT * FROM index_revisions WHERE revision_id=?", (revision_id,)
        ).fetchone()
        if row is None:
            return None
        new_count = row["rebuild_count"] + 1
        conn.execute(
            "UPDATE index_revisions SET source_revision=?, rebuild_count=? WHERE revision_id=?",
            (new_source_revision, new_count, revision_id),
        )
        conn.commit()
        return IndexRevision(
            revision_id=row["revision_id"],
            raw_sha256=row["raw_sha256"],
            index_name=row["index_name"],
            source_revision=new_source_revision,
            rebuild_count=new_count,
        )
