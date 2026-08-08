"""SQLite persistence for governed Phase 4 research package graphs."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable, Sequence
from contextlib import closing
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from app.contracts.v1 import ClaimV1, EvidenceV1, ResearchPackageV1, SourceRecordV1
from shared import research_migration


class ResearchPersistenceError(RuntimeError):
    """Raised when persisted research rows are missing or malformed."""


class SourceProvenanceRecord(BaseModel):
    source_id: str
    canonical_url: str
    source_group_id: str
    source_locator: str
    retrieved_at: str
    content_hash: str
    content_type: str
    media_type: str
    byte_length: int = Field(ge=0)
    collector_identity: str
    extractor_identity: str
    payload_role: str


class GovernanceFinding(BaseModel):
    finding_id: str
    package_id: str
    finding_type: Literal["corroboration", "conflict", "unknown", "risk"]
    detail: str
    severity: Literal["info", "low", "medium", "high"]
    claim_id: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    created_at: str


class ResearchPackageGraph(BaseModel):
    canonical_url: str
    intake_id: str
    package: ResearchPackageV1
    sources: list[SourceRecordV1]
    source_provenance: list[SourceProvenanceRecord]
    claims: list[ClaimV1]
    evidence: list[EvidenceV1]
    findings: list[GovernanceFinding]


ResearchBeforeCommit = Callable[[sqlite3.Connection, ResearchPackageGraph], None]


def _database_path(db_path: str | Path | None) -> Path:
    if db_path is not None:
        return Path(db_path)
    from shared import storage

    return Path(storage.DB_PATH)


def _connect(database: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(database), timeout=30.0)
    connection.execute("PRAGMA busy_timeout=30000")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def _json_dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _json_load(row_id: str, column: str, value: object) -> object:
    if not isinstance(value, str):
        raise ResearchPersistenceError(f"{row_id}: {column} is not persisted JSON text")
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ResearchPersistenceError(f"{row_id}: malformed {column}") from exc


def _json_list(row_id: str, column: str, value: object) -> list[object]:
    decoded = _json_load(row_id, column, value)
    if not isinstance(decoded, list):
        raise ResearchPersistenceError(f"{row_id}: {column} must decode to a list")
    return decoded


def _json_str_list(row_id: str, column: str, value: object) -> list[str]:
    decoded = _json_list(row_id, column, value)
    if not all(isinstance(item, str) for item in decoded):
        raise ResearchPersistenceError(f"{row_id}: {column} must contain only strings")
    return list(decoded)


def _insert_idempotent(
    connection: sqlite3.Connection,
    table: str,
    row: dict[str, object],
    *,
    primary_key: tuple[str, ...] = ("id",),
) -> None:
    columns = list(row)
    placeholders = ", ".join("?" for _ in columns)
    quoted_columns = ", ".join(f'"{column}"' for column in columns)
    cursor = connection.execute(
        f'INSERT OR IGNORE INTO "{table}" ({quoted_columns}) VALUES ({placeholders})',
        [row[column] for column in columns],
    )
    if cursor.rowcount == 1:
        return
    where = " AND ".join(f'"{column}"=?' for column in primary_key)
    existing = connection.execute(
        f'SELECT {quoted_columns} FROM "{table}" WHERE {where}',
        [row[column] for column in primary_key],
    ).fetchone()
    if existing is None:
        raise ResearchPersistenceError(f"{table}: idempotency conflict on a unique key")
    timestamp_columns = {"created_at", "retrieved_at"}
    mismatches = [
        column
        for column in columns
        if column not in timestamp_columns and existing[column] != row[column]
    ]
    if mismatches:
        raise ResearchPersistenceError(
            f"{table}: idempotency conflict for {', '.join(primary_key)}; "
            f"different columns: {', '.join(mismatches)}"
        )


def _source_row(
    source: SourceRecordV1,
    provenance: SourceProvenanceRecord,
) -> dict[str, object]:
    return {
        "id": source.source_id,
        "schema_version": source.schema_version,
        "title": source.title,
        "content": source.content,
        "source_locator": source.source_locator,
        "tags_json": _json_dump(source.tags),
        "provenance_status": source.provenance_status,
        "quarantine_status": source.quarantine_status,
        "created_at": source.created_at,
        "canonical_url": provenance.canonical_url,
        "source_group_id": provenance.source_group_id,
        "retrieved_at": provenance.retrieved_at,
        "content_hash": provenance.content_hash,
        "content_type": provenance.content_type,
        "media_type": provenance.media_type,
        "byte_length": provenance.byte_length,
        "collector_identity": provenance.collector_identity,
        "extractor_identity": provenance.extractor_identity,
        "payload_role": provenance.payload_role,
    }


def _claim_row(claim: ClaimV1, claim_kind: str) -> dict[str, object]:
    return {
        "id": claim.claim_id,
        "schema_version": claim.schema_version,
        "statement": claim.statement,
        "source_record_ids_json": _json_dump(claim.source_record_ids),
        "status": claim.status,
        "provenance_status": claim.provenance_status,
        "requires_human_review": 1 if claim.requires_human_review else 0,
        "created_at": claim.created_at,
        "claim_kind": claim_kind,
    }


def _evidence_row(
    evidence: EvidenceV1,
    source_hash_by_locator: dict[str, str],
) -> dict[str, object]:
    return {
        "id": evidence.evidence_id,
        "schema_version": evidence.schema_version,
        "claim_id": evidence.claim_id,
        "matched_term": evidence.matched_term,
        "source_locator": evidence.source_locator,
        "source_content_hash": source_hash_by_locator[evidence.source_locator],
        "location": evidence.location,
        "asset_locator": evidence.asset_locator,
        "kind": evidence.kind,
        "context": evidence.context,
        "status": evidence.status,
        "provenance_status": evidence.provenance_status,
        "requires_human_review": 1 if evidence.requires_human_review else 0,
    }


def _package_row(graph: ResearchPackageGraph) -> dict[str, object]:
    package = graph.package
    source_group_ids = sorted({record.source_group_id for record in graph.source_provenance})
    return {
        "id": package.package_id,
        "schema_version": package.schema_version,
        "canonical_url": graph.canonical_url,
        "intake_id": graph.intake_id,
        "source_record_ids_json": _json_dump(package.source_record_ids),
        "claim_ids_json": _json_dump(package.claim_ids),
        "evidence_ids_json": _json_dump(package.evidence_ids),
        "source_group_ids_json": _json_dump(source_group_ids),
        "independent_source_count": package.independent_source_count,
        "conflicts_json": _json_dump(package.conflicts),
        "unknowns_json": _json_dump(package.unknowns),
        "risks_json": _json_dump(package.risks),
        "verification_status": package.verification_status,
        "status": package.status,
        "provenance_status": package.provenance_status,
        "requires_human_review": 1 if package.requires_human_review else 0,
        "created_at": package.created_at,
    }


def _finding_row(finding: GovernanceFinding) -> dict[str, object]:
    return {
        "id": finding.finding_id,
        "package_id": finding.package_id,
        "finding_type": finding.finding_type,
        "detail": finding.detail,
        "severity": finding.severity,
        "claim_id": finding.claim_id,
        "evidence_ids_json": _json_dump(finding.evidence_ids),
        "created_at": finding.created_at,
    }


def _intake_row(graph: ResearchPackageGraph) -> dict[str, object]:
    is_workspace_document = {
        record.payload_role for record in graph.source_provenance
    } == {"workspace_document"}
    return {
        "id": graph.intake_id,
        "title": (
            f"Document research candidate: {graph.sources[0].title}"
            if is_workspace_document
            else f"Research package candidate: {graph.canonical_url}"
        ),
        "why": (
            "Local workspace document intake candidate."
            if is_workspace_document
            else "Phase 4 GitHub repository research package candidate."
        ),
        "what_to_absorb_json": _json_dump(graph.package.claim_ids),
        "what_not_to_absorb_json": _json_dump(
            ["verified truth promotion without independent review"]
        ),
        "source_ids_json": _json_dump(graph.package.source_record_ids),
        "risk_level": "medium",
        "target_repo": "Inspiration-Research",
        "created_at": graph.package.created_at,
    }


def _before_claim_write(
    _connection: sqlite3.Connection,
    _graph: ResearchPackageGraph,
) -> None:
    """Test hook for proving graph writes roll back as one transaction."""


def _validate_candidate_graph(graph: ResearchPackageGraph) -> None:
    from app.adapters.research_package import validate_research_bindings
    from app.adapters.taskpack import ContractMappingError

    package = graph.package
    if (
        package.status != "candidate"
        or package.provenance_status != "caller_supplied"
        or not package.requires_human_review
        or package.verification_status != "caller_supplied_candidate"
    ):
        raise ResearchPersistenceError("Phase 4 persistence is candidate-only")
    if any(
        source.quarantine_status != "candidate" or source.provenance_status != "unverified"
        for source in graph.sources
    ):
        raise ResearchPersistenceError("Phase 4 source persistence is candidate-only")
    if any(
        claim.status not in {"candidate", "conflicted", "unknown"}
        or claim.provenance_status != "caller_supplied"
        or not claim.requires_human_review
        for claim in graph.claims
    ):
        raise ResearchPersistenceError("Phase 4 claim persistence is candidate-only")
    if any(
        item.provenance_status != "caller_supplied" or not item.requires_human_review
        for item in graph.evidence
    ):
        raise ResearchPersistenceError("Phase 4 evidence persistence is candidate-only")
    try:
        validate_research_bindings(graph.sources, graph.claims, graph.evidence)
    except ContractMappingError as exc:
        raise ResearchPersistenceError(f"malformed research graph bindings: {exc}") from exc

    source_ids = [source.source_id for source in graph.sources]
    claim_ids = [claim.claim_id for claim in graph.claims]
    evidence_ids = [item.evidence_id for item in graph.evidence]
    if package.source_record_ids != source_ids:
        raise ResearchPersistenceError("package source IDs do not match graph sources")
    if package.claim_ids != claim_ids:
        raise ResearchPersistenceError("package claim IDs do not match graph claims")
    if package.evidence_ids != evidence_ids:
        raise ResearchPersistenceError("package evidence IDs do not match graph evidence")

    provenance_by_id = {record.source_id: record for record in graph.source_provenance}
    if len(provenance_by_id) != len(graph.source_provenance) or set(provenance_by_id) != set(
        source_ids
    ):
        raise ResearchPersistenceError("source provenance must match source records")
    source_by_id = {source.source_id: source for source in graph.sources}
    group_by_locator: dict[str, str] = {}
    hash_by_locator: dict[str, str] = {}
    for source_id, record in provenance_by_id.items():
        source = source_by_id[source_id]
        if record.source_locator != source.source_locator:
            raise ResearchPersistenceError("source provenance locator mismatch")
        if record.canonical_url != graph.canonical_url:
            raise ResearchPersistenceError("source provenance canonical URL mismatch")
        content_bytes = source.content.encode("utf-8")
        expected_hash = "sha256:" + hashlib.sha256(content_bytes).hexdigest()
        if record.content_hash != expected_hash:
            raise ResearchPersistenceError("source provenance content hash mismatch")
        if record.byte_length != len(content_bytes):
            raise ResearchPersistenceError("source provenance byte length mismatch")
        if record.source_locator in group_by_locator:
            raise ResearchPersistenceError("duplicate source provenance locator")
        group_by_locator[record.source_locator] = record.source_group_id
        hash_by_locator[record.source_locator] = record.content_hash
    for item in graph.evidence:
        expected_hash = hash_by_locator.get(item.source_locator)
        if expected_hash is None or item.asset_locator != expected_hash:
            raise ResearchPersistenceError(f"evidence asset locator mismatch: {item.evidence_id}")
    matched_groups = {
        group_by_locator[item.source_locator] for item in graph.evidence if item.status == "matched"
    }
    if package.independent_source_count != len(matched_groups):
        raise ResearchPersistenceError("package independent source count mismatch")

    known_claims = set(claim_ids)
    known_evidence = set(evidence_ids)
    finding_ids: set[str] = set()
    for finding in graph.findings:
        if finding.finding_id in finding_ids:
            raise ResearchPersistenceError("duplicate governance finding IDs")
        finding_ids.add(finding.finding_id)
        if finding.package_id != package.package_id:
            raise ResearchPersistenceError("governance finding references another package")
        if finding.claim_id and finding.claim_id not in known_claims:
            raise ResearchPersistenceError("governance finding references missing claim")
        if not set(finding.evidence_ids) <= known_evidence:
            raise ResearchPersistenceError("governance finding references missing evidence")

    try:
        payload_roles = {record.payload_role for record in graph.source_provenance}
        if payload_roles in ({"workspace_document"}, {"workspace_web_document"}):
            from app.research.document import validate_workspace_document_graph

            validate_workspace_document_graph(graph)
        else:
            from app.research.github import validate_github_graph_identity

            validate_github_graph_identity(graph)
    except ValueError as exc:
        raise ResearchPersistenceError(f"malformed research graph bindings: {exc}") from exc


def persist_research_graph(
    graph: ResearchPackageGraph,
    *,
    db_path: str | Path | None = None,
    before_commit: ResearchBeforeCommit | None = None,
) -> ResearchPackageGraph:
    """Persist a complete research graph transactionally and return the stored graph."""

    _validate_candidate_graph(graph)
    database = _database_path(db_path)
    research_migration.require_applied(db_path=database)
    provenance_by_id = {record.source_id: record for record in graph.source_provenance}
    if set(provenance_by_id) != {source.source_id for source in graph.sources}:
        raise ResearchPersistenceError("source provenance must match source records")
    source_hash_by_locator = {
        record.source_locator: record.content_hash for record in graph.source_provenance
    }
    claim_kinds = _claim_kinds(graph.claims)

    with closing(_connect(database)) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            _insert_idempotent(connection, "ir_intake_cards", _intake_row(graph))
            for source in graph.sources:
                _insert_idempotent(
                    connection,
                    "research_sources_v1",
                    _source_row(source, provenance_by_id[source.source_id]),
                )
            _before_claim_write(connection, graph)
            for claim in graph.claims:
                _insert_idempotent(
                    connection,
                    "research_claims_v1",
                    _claim_row(claim, claim_kinds[claim.claim_id]),
                )
            for item in graph.evidence:
                _insert_idempotent(
                    connection,
                    "research_evidence_v1",
                    _evidence_row(item, source_hash_by_locator),
                )
            _insert_idempotent(connection, "research_packages_v1", _package_row(graph))
            for finding in graph.findings:
                _insert_idempotent(
                    connection,
                    "research_governance_findings_v1",
                    _finding_row(finding),
                )
            _insert_idempotent(
                connection,
                "research_package_intake_links_v1",
                {
                    "package_id": graph.package.package_id,
                    "intake_id": graph.intake_id,
                    "relation_type": "phase4_candidate",
                    "created_at": graph.package.created_at,
                },
                primary_key=("package_id", "intake_id"),
            )
            if before_commit is not None:
                before_commit(connection, graph)
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    # The caller is still inside the live runtime after committing the intake
    # transaction. SQLite may retain WAL/SHM sidecars, so use the query-only
    # live-WAL reader here; immutable checkpoint-only reads remain reserved for
    # offline/external consumers.
    return load_research_package(graph.package.package_id, db_path=database, live_wal=True)


def _claim_kinds(claims: Sequence[ClaimV1]) -> dict[str, str]:
    result: dict[str, str] = {}
    for claim in claims:
        if "license" in claim.statement.lower():
            kind = "license"
        elif "primary language" in claim.statement.lower():
            kind = "language"
        elif "readme title" in claim.statement.lower():
            kind = "readme_title"
        elif "metadata describes" in claim.statement.lower():
            kind = "description"
        else:
            kind = "repository_metadata"
        result[claim.claim_id] = kind
    return result


def _source_from_row(row: sqlite3.Row) -> tuple[SourceRecordV1, SourceProvenanceRecord]:
    row_id = str(row["id"])
    content = str(row["content"])
    content_bytes = content.encode("utf-8")
    expected_hash = "sha256:" + hashlib.sha256(content_bytes).hexdigest()
    if expected_hash != str(row["content_hash"]):
        raise ResearchPersistenceError(f"source content hash mismatch: {row_id}")
    if len(content_bytes) != int(row["byte_length"]):
        raise ResearchPersistenceError(f"source byte length mismatch: {row_id}")
    try:
        source = SourceRecordV1(
            schema_version=str(row["schema_version"]),
            source_id=row_id,
            title=str(row["title"]),
            content=content,
            source_locator=str(row["source_locator"]),
            tags=_json_str_list(row_id, "tags_json", row["tags_json"]),
            provenance_status=str(row["provenance_status"]),
            quarantine_status=str(row["quarantine_status"]),
            created_at=str(row["created_at"]),
        )
        provenance = SourceProvenanceRecord(
            source_id=row_id,
            canonical_url=str(row["canonical_url"]),
            source_group_id=str(row["source_group_id"]),
            source_locator=str(row["source_locator"]),
            retrieved_at=str(row["retrieved_at"]),
            content_hash=str(row["content_hash"]),
            content_type=str(row["content_type"]),
            media_type=str(row["media_type"]),
            byte_length=int(row["byte_length"]),
            collector_identity=str(row["collector_identity"]),
            extractor_identity=str(row["extractor_identity"]),
            payload_role=str(row["payload_role"]),
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise ResearchPersistenceError(f"{row_id}: malformed source row") from exc
    return source, provenance


def _claim_from_row(row: sqlite3.Row) -> ClaimV1:
    row_id = str(row["id"])
    try:
        return ClaimV1(
            schema_version=str(row["schema_version"]),
            claim_id=row_id,
            statement=str(row["statement"]),
            source_record_ids=_json_str_list(
                row_id,
                "source_record_ids_json",
                row["source_record_ids_json"],
            ),
            status=str(row["status"]),
            provenance_status=str(row["provenance_status"]),
            requires_human_review=bool(int(row["requires_human_review"])),
            created_at=str(row["created_at"]),
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise ResearchPersistenceError(f"{row_id}: malformed claim row") from exc


def _evidence_from_row(row: sqlite3.Row) -> EvidenceV1:
    row_id = str(row["id"])
    try:
        return EvidenceV1(
            schema_version=str(row["schema_version"]),
            evidence_id=row_id,
            claim_id=str(row["claim_id"]),
            matched_term=str(row["matched_term"]),
            source_locator=str(row["source_locator"]),
            location=str(row["location"]),
            asset_locator=str(row["asset_locator"]),
            kind=str(row["kind"]),
            context=str(row["context"]),
            status=str(row["status"]),
            provenance_status=str(row["provenance_status"]),
            requires_human_review=bool(int(row["requires_human_review"])),
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise ResearchPersistenceError(f"{row_id}: malformed evidence row") from exc


def _package_from_row(row: sqlite3.Row) -> ResearchPackageV1:
    row_id = str(row["id"])
    try:
        return ResearchPackageV1(
            schema_version=str(row["schema_version"]),
            package_id=row_id,
            source_record_ids=_json_str_list(
                row_id,
                "source_record_ids_json",
                row["source_record_ids_json"],
            ),
            claim_ids=_json_str_list(row_id, "claim_ids_json", row["claim_ids_json"]),
            evidence_ids=_json_str_list(
                row_id,
                "evidence_ids_json",
                row["evidence_ids_json"],
            ),
            independent_source_count=int(row["independent_source_count"]),
            conflicts=_json_str_list(row_id, "conflicts_json", row["conflicts_json"]),
            unknowns=_json_str_list(row_id, "unknowns_json", row["unknowns_json"]),
            risks=_json_str_list(row_id, "risks_json", row["risks_json"]),
            verification_status=str(row["verification_status"]),
            status=str(row["status"]),
            provenance_status=str(row["provenance_status"]),
            requires_human_review=bool(int(row["requires_human_review"])),
            created_at=str(row["created_at"]),
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise ResearchPersistenceError(f"{row_id}: malformed package row") from exc


def _finding_from_row(row: sqlite3.Row) -> GovernanceFinding:
    row_id = str(row["id"])
    try:
        return GovernanceFinding(
            finding_id=row_id,
            package_id=str(row["package_id"]),
            finding_type=str(row["finding_type"]),
            detail=str(row["detail"]),
            severity=str(row["severity"]),
            claim_id=str(row["claim_id"]),
            evidence_ids=_json_str_list(
                row_id,
                "evidence_ids_json",
                row["evidence_ids_json"],
            ),
            created_at=str(row["created_at"]),
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise ResearchPersistenceError(f"{row_id}: malformed finding row") from exc


def _ordered_rows(
    connection: sqlite3.Connection,
    table: str,
    ids: Sequence[str],
) -> list[sqlite3.Row]:
    if not ids:
        return []
    placeholders = ", ".join("?" for _ in ids)
    rows = connection.execute(
        f'SELECT * FROM "{table}" WHERE id IN ({placeholders})',
        list(ids),
    ).fetchall()
    by_id = {str(row["id"]): row for row in rows}
    missing = [item for item in ids if item not in by_id]
    if missing:
        raise ResearchPersistenceError(
            f"package references missing {table} rows: {', '.join(missing)}"
        )
    return [by_id[item] for item in ids]


def load_research_package(
    package_id: str,
    *,
    db_path: str | Path | None = None,
    live_wal: bool = False,
) -> ResearchPackageGraph:
    """Load and strictly validate a persisted research package graph."""

    database = _database_path(db_path)
    if not database.is_file():
        raise RuntimeError("phase4 research schema migration is pending")
    connector = research_migration._connect_consumer_readonly if live_wal else research_migration._connect_readonly
    with closing(connector(database)) as connection:
        research_migration._require_applied_connection(connection, database)
        package_row = connection.execute(
            "SELECT * FROM research_packages_v1 WHERE id=?",
            (package_id,),
        ).fetchone()
        if package_row is None:
            raise ResearchPersistenceError(f"research package not found: {package_id}")
        package = _package_from_row(package_row)
        source_pairs = [
            _source_from_row(row)
            for row in _ordered_rows(
                connection,
                "research_sources_v1",
                package.source_record_ids,
            )
        ]
        sources = [source for source, _provenance in source_pairs]
        provenance = [item for _source, item in source_pairs]
        claims = [
            _claim_from_row(row)
            for row in _ordered_rows(connection, "research_claims_v1", package.claim_ids)
        ]
        source_hash_by_locator: dict[str, str] = {}
        for item in provenance:
            previous = source_hash_by_locator.setdefault(item.source_locator, item.content_hash)
            if previous != item.content_hash:
                raise ResearchPersistenceError(
                    f"ambiguous source locator hash: {item.source_locator}"
                )
        evidence_rows = _ordered_rows(
            connection,
            "research_evidence_v1",
            package.evidence_ids,
        )
        for row in evidence_rows:
            expected_hash = source_hash_by_locator.get(str(row["source_locator"]))
            if expected_hash is None or expected_hash != str(row["source_content_hash"]):
                raise ResearchPersistenceError(f"evidence source hash mismatch: {row['id']}")
        evidence = [_evidence_from_row(row) for row in evidence_rows]
        finding_rows = connection.execute(
            "SELECT * FROM research_governance_findings_v1 "
            "WHERE package_id=? ORDER BY finding_type, id",
            (package.package_id,),
        ).fetchall()
        findings = [_finding_from_row(row) for row in finding_rows]
        known_claims = {claim.claim_id for claim in claims}
        known_evidence = {item.evidence_id for item in evidence}
        for finding in findings:
            if finding.package_id != package.package_id:
                raise ResearchPersistenceError(
                    f"governance finding references another package: {finding.finding_id}"
                )
            if finding.claim_id and finding.claim_id not in known_claims:
                raise ResearchPersistenceError(
                    f"governance finding references missing claim: {finding.finding_id}"
                )
            if not set(finding.evidence_ids) <= known_evidence:
                raise ResearchPersistenceError(
                    f"governance finding references missing evidence: {finding.finding_id}"
                )
        canonical_url = str(package_row["canonical_url"])
        if any(item.canonical_url != canonical_url for item in provenance):
            raise ResearchPersistenceError("source provenance canonical URL mismatch")
        persisted_groups = _json_str_list(
            package.package_id,
            "source_group_ids_json",
            package_row["source_group_ids_json"],
        )
        actual_groups = sorted({item.source_group_id for item in provenance})
        if persisted_groups != actual_groups:
            raise ResearchPersistenceError("package source group summary mismatch")
        intake_row = connection.execute(
            "SELECT * FROM ir_intake_cards WHERE id=?",
            (str(package_row["intake_id"]),),
        ).fetchone()
        link_exists = connection.execute(
            "SELECT 1 FROM research_package_intake_links_v1 "
            "WHERE package_id=? AND intake_id=? AND relation_type='phase4_candidate'",
            (package.package_id, str(package_row["intake_id"])),
        ).fetchone()
        if intake_row is None or link_exists is None:
            raise ResearchPersistenceError("research package intake binding is missing")
        expected_intake = _intake_row(
            ResearchPackageGraph(
                canonical_url=canonical_url,
                intake_id=str(package_row["intake_id"]),
                package=package,
                sources=sources,
                source_provenance=provenance,
                claims=claims,
                evidence=evidence,
                findings=findings,
            )
        )
        for column, expected in expected_intake.items():
            if str(intake_row[column]) != str(expected):
                raise ResearchPersistenceError(
                    f"research package intake content mismatch: {column}"
                )

        from app.adapters.research_package import validate_research_bindings
        from app.adapters.taskpack import ContractMappingError

        try:
            validate_research_bindings(sources, claims, evidence)
        except ContractMappingError as exc:
            raise ResearchPersistenceError(f"malformed research graph bindings: {exc}") from exc

    graph = ResearchPackageGraph(
        canonical_url=canonical_url,
        intake_id=str(package_row["intake_id"]),
        package=package,
        sources=sources,
        source_provenance=provenance,
        claims=claims,
        evidence=evidence,
        findings=findings,
    )
    _validate_candidate_graph(graph)
    return graph
