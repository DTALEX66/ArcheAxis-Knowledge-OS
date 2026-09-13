"""Import the R5 HL01 source registry into the append-only source store."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.contracts.source_anchor_v2 import SourceObjectV2
from app.evidence.source_store_v2 import SourceStoreV2
from app.workspace.job_outbox import record_completed_command

RightsStatus = Literal["owned", "licensed", "public-domain", "permission-recorded"]


@dataclass(frozen=True)
class HL01ImportReceipt:
    registry_sha256: str
    imported: int
    duplicates: int
    source_ids: tuple[str, ...]
    command_id: str | None = None
    job_id: str | None = None
    event_id: str | None = None


def verify_registry_receipt(db_path: str | Path, command_id: str) -> dict[str, object]:
    """Read back and validate a persisted HL01 command receipt."""
    with sqlite3.connect(Path(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT r.command_id, r.command_type, r.job_id, r.result_json, "
            "j.state, j.payload_json FROM workspace_command_receipts_v1 AS r "
            "JOIN workspace_jobs_v1 AS j ON j.job_id=r.job_id WHERE r.command_id=?",
            (command_id,),
        ).fetchone()
        if row is None:
            raise KeyError(command_id)
        if str(row["command_type"]) != "hl01.source_registry.import":
            raise ValueError("unexpected HL01 receipt command type")
        payload = json.loads(str(row["payload_json"]))
        actual_count = int(
            connection.execute(
                "SELECT COUNT(*) FROM source_objects_v2 WHERE source_id LIKE 'hl01:%'"
            ).fetchone()[0]
        )
    if int(payload.get("source_count", -1)) != actual_count:
        raise ValueError("HL01 receipt source count does not match Core")
    return {
        "command_id": str(row["command_id"]),
        "job_id": str(row["job_id"]),
        "state": str(row["state"]),
        "source_count": actual_count,
        "registry_sha256": str(payload["registry_sha256"]),
    }


def _resolve_source_path(
    registry_path: Path, source_path: str, *, repository_root: Path | None = None
) -> Path:
    registry_path = registry_path.resolve()
    repo_root = (repository_root or registry_path.parents[2]).resolve()
    candidate = Path(source_path)
    if candidate.is_absolute():
        resolved = candidate.resolve()
        if not resolved.is_relative_to(repo_root):
            raise ValueError(f"source path escapes repository root: {source_path}")
        return resolved
    roots = [repo_root, *registry_path.parents]
    for root in roots:
        resolved = (root / candidate).resolve()
        if resolved.is_relative_to(repo_root) and resolved.is_file():
            return resolved
    raise FileNotFoundError(source_path)


def import_registry_candidates(
    store: SourceStoreV2,
    registry_path: str | Path,
    *,
    created_at: str,
    rights_status: RightsStatus,
    command_id: str | None = None,
    repository_root: str | Path | None = None,
) -> HL01ImportReceipt:
    """Persist one immutable SourceObjectV2 for each registry candidate record.

    The registry remains a candidate catalogue: this function records source
    truth only and never activates a learning or knowledge record. Repeating
    the same registry is idempotent; a changed hash for an existing source ID
    is rejected by the append-only store.
    """
    path = Path(registry_path)
    raw = path.read_bytes()
    registry = json.loads(raw.decode("utf-8"))
    if registry.get("schema") != "archeaxis.hl01-source-registry/v1":
        raise ValueError("unsupported HL01 registry schema")
    categories = registry.get("categories")
    records = registry.get("records")
    if not isinstance(categories, list) or not isinstance(records, list):
        raise ValueError("HL01 registry categories and records are required")
    category_sizes = {str(item["source_path"]): int(item["bytes"]) for item in categories}
    category_counts = {str(item["source_path"]): int(item["record_count"]) for item in categories}
    if len(records) != int(registry.get("total_records", -1)):
        raise ValueError("HL01 registry record count mismatch")
    seen_ids = [str(item.get("core_id")) for item in records]
    if len(set(seen_ids)) != len(seen_ids):
        raise ValueError("HL01 registry contains duplicate Core IDs")
    actual_counts: dict[str, int] = {}
    for item in records:
        source_path = str(item.get("source_path"))
        if source_path not in category_sizes:
            raise ValueError(f"HL01 registry references unknown source: {source_path}")
        actual_counts[source_path] = actual_counts.get(source_path, 0) + 1
    if actual_counts != category_counts:
        raise ValueError("HL01 registry category counts mismatch")
    imported = 0
    duplicates = 0
    source_objects: list[SourceObjectV2] = []
    source_ids: list[str] = []
    for record in records:
        source_id = str(record["core_id"])
        source_path = _resolve_source_path(
            path,
            str(record["source_path"]),
            repository_root=Path(repository_root) if repository_root is not None else None,
        )
        source_bytes = source_path.read_bytes()
        source_sha256 = hashlib.sha256(source_bytes).hexdigest()
        if source_sha256 != str(record["source_sha256"]):
            raise ValueError(f"source hash mismatch: {record['source_path']}")
        if len(source_bytes) != category_sizes[str(record["source_path"])]:
            raise ValueError(f"source size mismatch: {record['source_path']}")
        source = SourceObjectV2(
            source_id=source_id,
            version=1,
            sha256=source_sha256,
            byte_size=len(source_bytes),
            media_type="application/json",
            rights_status=rights_status,
            original_retained=True,
            created_at=created_at,
        )
        source_objects.append(source)
        source_ids.append(source_id)
    # All source bytes and identities are validated before the first write.
    for source in source_objects:
        existed = store.has_source(source.source_id, source.version)
        store.put_source(source)
        if existed:
            duplicates += 1
        else:
            imported += 1
    command_result: dict[str, str] = {}
    if command_id is not None:
        payload = {
            "registry_sha256": hashlib.sha256(raw).hexdigest(),
            "source_count": len(source_ids),
            "source_ids_sha256": hashlib.sha256("\n".join(source_ids).encode("utf-8")).hexdigest(),
            "rights_status": rights_status,
        }
        with sqlite3.connect(store.db_path) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("BEGIN IMMEDIATE")
            command_result = record_completed_command(
                connection,
                command_id=command_id,
                command_type="hl01.source_registry.import",
                aggregate_id="r5-hl01",
                payload=payload,
            )
            connection.commit()
    return HL01ImportReceipt(
        registry_sha256=hashlib.sha256(raw).hexdigest(),
        imported=imported,
        duplicates=duplicates,
        source_ids=tuple(source_ids),
        command_id=command_result.get("command_id"),
        job_id=command_result.get("job_id"),
        event_id=command_result.get("event_id"),
    )
