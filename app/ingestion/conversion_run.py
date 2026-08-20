"""AXW-020B: Import/Conversion/Derived contracts.

A ConversionRun converts one raw asset into a DerivedDocument composed of
DerivedBlocks, recording per-block and aggregate LossReport. IDs are stable
(deterministic from the raw asset hash + source + engine), versions are
explicit, and the run -> document -> block relation is queryable from a local
SQLite store.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _stable_id(prefix: str, *parts: object) -> str:
    payload = json.dumps(parts, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return f"{prefix}_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


@dataclass(frozen=True)
class DerivedBlock:
    block_id: str
    kind: str
    text: str
    anchor: dict[str, Any]
    source_revision: str | None = None


@dataclass(frozen=True)
class DerivedDocument:
    document_id: str
    raw_sha256: str
    engine: str
    version: int
    blocks: list[DerivedBlock] = field(default_factory=list)


@dataclass(frozen=True)
class LossReport:
    block_count: int
    loss_notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ConversionRun:
    run_id: str
    raw_sha256: str
    source_name: str
    engine: str
    version: int
    document: DerivedDocument
    loss_report: LossReport

    @property
    def blocks(self) -> list[DerivedBlock]:
        return self.document.blocks


def create_conversion_run(
    raw_sha256: str,
    source_name: str,
    blocks: list[dict[str, Any]],
    engine: str,
    version: int = 1,
    loss_notes: list[str] | None = None,
) -> ConversionRun:
    """Build a ConversionRun with stable IDs derived from content identity.

    Empty block lists are rejected: a conversion that produced nothing cannot
    be recorded as a valid derived document.
    """
    if not blocks:
        raise ValueError("conversion produced no blocks")
    run_id = _stable_id("run", raw_sha256, source_name, engine, version)
    document_id = _stable_id("derived", raw_sha256, engine, version)
    derived_blocks: list[DerivedBlock] = []
    for i, b in enumerate(blocks):
        kind = b.get("kind") or "text"
        text = b.get("text") or ""
        anchor = b.get("anchor") or {}
        block_id = _stable_id("block", document_id, i, text, anchor)
        derived_blocks.append(
            DerivedBlock(block_id=block_id, kind=kind, text=text, anchor=anchor)
        )
    document = DerivedDocument(
        document_id=document_id,
        raw_sha256=raw_sha256,
        engine=engine,
        version=version,
        blocks=derived_blocks,
    )
    return ConversionRun(
        run_id=run_id,
        raw_sha256=raw_sha256,
        source_name=source_name,
        engine=engine,
        version=version,
        document=document,
        loss_report=LossReport(block_count=len(derived_blocks), loss_notes=list(loss_notes or [])),
    )


_SCHEMA = """
CREATE TABLE IF NOT EXISTS conversion_runs (
    run_id TEXT PRIMARY KEY,
    raw_sha256 TEXT NOT NULL,
    source_name TEXT NOT NULL,
    engine TEXT NOT NULL,
    version INTEGER NOT NULL,
    document_json TEXT NOT NULL,
    loss_report_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS derived_blocks (
    block_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    text TEXT NOT NULL,
    anchor_json TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES conversion_runs(run_id)
);
CREATE INDEX IF NOT EXISTS idx_blocks_run ON derived_blocks(run_id);
"""


def ensure_conversion_run_schema(db: str | Path) -> None:
    """Create the local derived-conversion schema before a caller transaction."""
    with sqlite3.connect(Path(db)) as connection:
        connection.executescript(_SCHEMA)


def _document_payload(run: ConversionRun) -> str:
    return json.dumps(
        {
            "document_id": run.document.document_id,
            "raw_sha256": run.document.raw_sha256,
            "engine": run.document.engine,
            "version": run.document.version,
        },
        sort_keys=True,
    )


def _loss_payload(run: ConversionRun) -> str:
    return json.dumps(
        {
            "block_count": run.loss_report.block_count,
            "loss_notes": run.loss_report.loss_notes,
        },
        sort_keys=True,
    )


def _stored_blocks(connection: sqlite3.Connection, run_id: str) -> list[tuple[object, ...]]:
    return [
        tuple(row)
        for row in connection.execute(
            "SELECT block_id, run_id, document_id, kind, text, anchor_json "
            "FROM derived_blocks WHERE run_id=? ORDER BY block_id",
            (run_id,),
        ).fetchall()
    ]


def _run_blocks(run: ConversionRun) -> list[tuple[object, ...]]:
    return sorted(
        [
            (
                block.block_id,
                run.run_id,
                run.document.document_id,
                block.kind,
                block.text,
                json.dumps(block.anchor, ensure_ascii=True, sort_keys=True),
            )
            for block in run.blocks
        ]
    )


def store_conversion_run_on_connection(
    connection: sqlite3.Connection, run: ConversionRun
) -> None:
    """Persist one immutable run in the caller-owned transaction.

    Replaying an identical deterministic run is a no-op. A stable run id with
    changed semantics is a conflict, never an overwrite.
    """
    existing = connection.execute(
        "SELECT raw_sha256, source_name, engine, version, document_json, loss_report_json "
        "FROM conversion_runs WHERE run_id=?",
        (run.run_id,),
    ).fetchone()
    if existing is not None:
        recorded = (
            str(existing[0]), str(existing[1]), str(existing[2]), int(existing[3]),
            str(existing[4]), str(existing[5]),
        )
        expected = (
            run.raw_sha256, run.source_name, run.engine, run.version,
            _document_payload(run), _loss_payload(run),
        )
        if recorded == expected and _stored_blocks(connection, run.run_id) == _run_blocks(run):
            return
        raise RuntimeError("conversion run id conflicts with an existing immutable receipt")
    connection.execute(
        "INSERT INTO conversion_runs "
        "(run_id, raw_sha256, source_name, engine, version, document_json, loss_report_json, created_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (
            run.run_id,
            run.raw_sha256,
            run.source_name,
            run.engine,
            run.version,
            _document_payload(run),
            _loss_payload(run),
            "now",
        ),
    )
    for block in run.blocks:
        connection.execute(
            "INSERT INTO derived_blocks "
            "(block_id, run_id, document_id, kind, text, anchor_json) VALUES (?,?,?,?,?,?)",
            (
                block.block_id,
                run.run_id,
                run.document.document_id,
                block.kind,
                block.text,
                json.dumps(block.anchor, ensure_ascii=True, sort_keys=True),
            ),
        )


def store_conversion_run(db: str | Path, run: ConversionRun) -> None:
    """Persist a ConversionRun and its blocks into the local SQLite store."""
    ensure_conversion_run_schema(db)
    with sqlite3.connect(Path(db)) as connection:
        store_conversion_run_on_connection(connection, run)
        connection.commit()


def resolve_conversion_run(db: str | Path, run_id: str) -> ConversionRun | None:
    """Load a ConversionRun by id, restoring its document and blocks."""
    with sqlite3.connect(Path(db)) as conn:
        conn.row_factory = sqlite3.Row
        conn.executescript(_SCHEMA)
        row = conn.execute(
            "SELECT * FROM conversion_runs WHERE run_id=?", (run_id,)
        ).fetchone()
        if row is None:
            return None
        doc = json.loads(row["document_json"])
        loss = json.loads(row["loss_report_json"])
        block_rows = conn.execute(
            "SELECT * FROM derived_blocks WHERE run_id=? ORDER BY block_id",
            (run_id,),
        ).fetchall()
        blocks = [
            DerivedBlock(
                block_id=br["block_id"],
                kind=br["kind"],
                text=br["text"],
                anchor=json.loads(br["anchor_json"]),
            )
            for br in block_rows
        ]
        document = DerivedDocument(
            document_id=doc["document_id"],
            raw_sha256=doc["raw_sha256"],
            engine=doc["engine"],
            version=doc["version"],
            blocks=blocks,
        )
        return ConversionRun(
            run_id=row["run_id"],
            raw_sha256=row["raw_sha256"],
            source_name=row["source_name"],
            engine=row["engine"],
            version=row["version"],
            document=document,
            loss_report=LossReport(
                block_count=loss.get("block_count", len(blocks)),
                loss_notes=list(loss.get("loss_notes") or []),
            ),
        )
