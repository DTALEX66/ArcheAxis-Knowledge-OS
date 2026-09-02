"""Governed local-document SourceRecord -> ResearchPackage candidate workflow."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from app.adapters.research_package import build_candidate_research_package
from app.contracts.v1 import CONTRACT_VERSION, ClaimV1, EvidenceV1, SourceRecordV1
from shared.research_store import (
    GovernanceFinding,
    ResearchBeforeCommit,
    ResearchPackageGraph,
    SourceProvenanceRecord,
    persist_research_graph,
)
from shared.stable_hash import stable_hash_text

WORKSPACE_DOCUMENT_ROLE = "workspace_document"
WORKSPACE_RAW_ASSET_ROLE = "workspace_raw_asset_document"
WORKSPACE_WEB_ROLE = "workspace_web_document"
WORKSPACE_WEB_SNAPSHOT_ROLE = "workspace_web_snapshot"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _id(prefix: str, *parts: object) -> str:
    payload = json.dumps(parts, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return f"{prefix}_{stable_hash_text(payload, namespace=f'workspace-{prefix}')[:20]}"


def _first_claim(content: str) -> tuple[str, str]:
    for raw_line in content.splitlines():
        raw = raw_line.strip()
        statement = raw.lstrip("#").strip()
        if statement:
            return statement[:500], statement[:120]
    raise ValueError("converted document has no claimable text")


def build_workspace_document_graph(
    *,
    title: str,
    content: str,
    source_format: str,
    extractor_identity: str,
    source_locator: str | None = None,
    raw_asset_sha256: str | None = None,
    created_at: str | None = None,
) -> ResearchPackageGraph:
    """Build one deterministic, review-required package from a local converted document."""

    timestamp = created_at or _now_utc()
    content_bytes = content.encode("utf-8")
    digest = hashlib.sha256(content_bytes).hexdigest()
    content_hash = f"sha256:{digest}"
    if raw_asset_sha256:
        if len(raw_asset_sha256) != 64 or any(char not in "0123456789abcdef" for char in raw_asset_sha256):
            raise ValueError("workspace raw asset identity must be a lowercase SHA-256 digest")
        raw_locator = f"local-asset://sha256/{raw_asset_sha256}"
        if source_locator:
            parsed = urlsplit(source_locator)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise ValueError("workspace web snapshot requires an absolute http(s) canonical URL")
            canonical_url = source_locator
            locator = raw_locator
            payload_role = WORKSPACE_WEB_SNAPSHOT_ROLE
            collector_identity = "workspace-web-snapshot-intake-v1"
        else:
            canonical_url = raw_locator
            locator = raw_locator
            payload_role = WORKSPACE_RAW_ASSET_ROLE
            collector_identity = "workspace-raw-asset-intake-v1"
    elif source_locator:
        canonical_url = source_locator
        locator = source_locator
        payload_role = WORKSPACE_WEB_ROLE
        collector_identity = "workspace-web-intake-v1"
    else:
        canonical_url = f"local-content://sha256/{digest}"
        locator = f"local-content://sha256/{digest}"
        payload_role = WORKSPACE_DOCUMENT_ROLE
        collector_identity = "workspace-local-intake-v1"
    source_group_id = _id("source_group", canonical_url)
    if payload_role == WORKSPACE_WEB_SNAPSHOT_ROLE:
        source_id = _id("source", canonical_url, raw_asset_sha256, content_hash)
        package_id = _id("research_package", canonical_url, raw_asset_sha256, content_hash)
    else:
        source_id = _id("source", locator, content_hash)
        package_id = _id("research_package", locator, content_hash)
    statement, matched_term = _first_claim(content)
    claim_id = _id("claim", package_id, statement, [source_id])
    evidence_id = _id(
        "evidence", package_id, claim_id, source_id, content_hash, "document:first-claim", matched_term
    )
    source = SourceRecordV1(
        schema_version=CONTRACT_VERSION,
        source_id=source_id,
        title=title,
        content=content,
        source_locator=locator,
        tags=["workspace-intake", source_format],
        provenance_status="unverified",
        quarantine_status="candidate",
        created_at=timestamp,
    )
    provenance = SourceProvenanceRecord(
        source_id=source_id,
        canonical_url=canonical_url,
        source_group_id=source_group_id,
        source_locator=locator,
        retrieved_at=timestamp,
        content_hash=content_hash,
        content_type="text/markdown; charset=utf-8",
        media_type="text/markdown",
        byte_length=len(content_bytes),
        collector_identity=collector_identity,
        extractor_identity=extractor_identity,
        payload_role=payload_role,
    )
    claim = ClaimV1(
        schema_version=CONTRACT_VERSION,
        claim_id=claim_id,
        statement=statement,
        source_record_ids=[source_id],
        status="candidate",
        provenance_status="caller_supplied",
        requires_human_review=True,
        created_at=timestamp,
    )
    evidence = EvidenceV1(
        schema_version=CONTRACT_VERSION,
        evidence_id=evidence_id,
        claim_id=claim_id,
        matched_term=matched_term,
        source_locator=locator,
        location="document:first-claim",
        asset_locator=content_hash,
        kind="workspace_document_text",
        context=statement,
        status="matched",
        provenance_status="caller_supplied",
        requires_human_review=True,
    )
    package = build_candidate_research_package(
        package_id=package_id,
        sources=[source],
        claims=[claim],
        evidence=[evidence],
        conflicts=[],
        unknowns=["single-source document requires independent corroboration"],
        risks=["automatically extracted claim requires human review"],
        created_at=timestamp,
        source_group_ids_by_locator={locator: source_group_id},
    )
    finding_detail = "Single-source local document requires independent corroboration."
    finding = GovernanceFinding(
        finding_id=_id("finding", package_id, "unknown", finding_detail, claim_id, [evidence_id]),
        package_id=package_id,
        finding_type="unknown",
        detail=finding_detail,
        severity="medium",
        claim_id=claim_id,
        evidence_ids=[evidence_id],
        created_at=timestamp,
    )
    return ResearchPackageGraph(
        canonical_url=canonical_url,
        intake_id=_id("intake", canonical_url),
        package=package,
        sources=[source],
        source_provenance=[provenance],
        claims=[claim],
        evidence=[evidence],
        findings=[finding],
    )


def validate_workspace_document_graph(graph: ResearchPackageGraph) -> None:
    """Recompute local-document identities and evidence anchors before persistence/readback."""

    if len(graph.sources) != 1 or len(graph.source_provenance) != 1:
        raise ValueError("workspace document graph must contain exactly one source")
    source = graph.sources[0]
    provenance = graph.source_provenance[0]
    if provenance.payload_role not in {
        WORKSPACE_DOCUMENT_ROLE,
        WORKSPACE_RAW_ASSET_ROLE,
        WORKSPACE_WEB_ROLE,
        WORKSPACE_WEB_SNAPSHOT_ROLE,
    }:
        raise ValueError("workspace document graph has an invalid payload role")
    content_bytes = source.content.encode("utf-8")
    digest = hashlib.sha256(content_bytes).hexdigest()
    content_hash = f"sha256:{digest}"
    if provenance.payload_role == WORKSPACE_WEB_ROLE:
        canonical_url = graph.canonical_url
        locator = graph.canonical_url
        if provenance.collector_identity != "workspace-web-intake-v1":
            raise ValueError("workspace web collector identity is invalid")
    elif provenance.payload_role == WORKSPACE_WEB_SNAPSHOT_ROLE:
        canonical_url = graph.canonical_url
        parsed = urlsplit(canonical_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("workspace web snapshot canonical URL is invalid")
        locator = source.source_locator
        raw_prefix = "local-asset://sha256/"
        raw_sha256 = locator.removeprefix(raw_prefix)
        if (
            not locator.startswith(raw_prefix)
            or len(raw_sha256) != 64
            or any(char not in "0123456789abcdef" for char in raw_sha256)
        ):
            raise ValueError("workspace web snapshot raw asset locator is invalid")
        if provenance.collector_identity != "workspace-web-snapshot-intake-v1":
            raise ValueError("workspace web snapshot collector identity is invalid")
    elif provenance.payload_role == WORKSPACE_RAW_ASSET_ROLE:
        canonical_url = graph.canonical_url
        locator = graph.canonical_url
        raw_prefix = "local-asset://sha256/"
        raw_sha256 = locator.removeprefix(raw_prefix)
        if (
            not locator.startswith(raw_prefix)
            or len(raw_sha256) != 64
            or any(char not in "0123456789abcdef" for char in raw_sha256)
        ):
            raise ValueError("workspace raw asset locator is invalid")
        if provenance.collector_identity != "workspace-raw-asset-intake-v1":
            raise ValueError("workspace raw asset collector identity is invalid")
    else:
        canonical_url = f"local-content://sha256/{digest}"
        locator = f"local-content://sha256/{digest}"
        if provenance.collector_identity != "workspace-local-intake-v1":
            raise ValueError("workspace document collector identity is invalid")
    if graph.canonical_url != canonical_url or source.source_locator != locator:
        raise ValueError("workspace document locator does not match content")
    if provenance.canonical_url != canonical_url or provenance.source_locator != locator:
        raise ValueError("workspace document provenance locator does not match content")
    source_group_id = _id("source_group", canonical_url)
    if provenance.payload_role == WORKSPACE_WEB_SNAPSHOT_ROLE:
        source_id = _id("source", canonical_url, raw_sha256, content_hash)
        package_id = _id("research_package", canonical_url, raw_sha256, content_hash)
    else:
        source_id = _id("source", locator, content_hash)
        package_id = _id("research_package", locator, content_hash)
    if provenance.source_group_id != source_group_id or source.source_id != source_id:
        raise ValueError("workspace document source identity does not match content")
    if graph.package.package_id != package_id or graph.intake_id != _id("intake", canonical_url):
        raise ValueError("workspace document package identity does not match content")
    for claim in graph.claims:
        if claim.claim_id != _id("claim", package_id, claim.statement, claim.source_record_ids):
            raise ValueError("workspace document claim identity does not match semantics")
    source_by_id = {source.source_id: source}
    for item in graph.evidence:
        bound = source_by_id[graph.claims[0].source_record_ids[0]]
        expected = _id(
            "evidence",
            package_id,
            item.claim_id,
            bound.source_id,
            content_hash,
            item.location,
            item.matched_term,
        )
        if item.evidence_id != expected:
            raise ValueError("workspace document evidence identity does not match semantics")
        if item.matched_term.casefold() not in source.content.casefold():
            raise ValueError("workspace document evidence is absent from source content")
        if item.matched_term.casefold() not in item.context.casefold():
            raise ValueError("workspace document evidence context is not grounded")
    for finding in graph.findings:
        expected = _id(
            "finding",
            package_id,
            finding.finding_type,
            finding.detail,
            finding.claim_id,
            finding.evidence_ids,
        )
        if finding.finding_id != expected:
            raise ValueError("workspace document finding identity does not match semantics")


def persist_workspace_document(
    *,
    title: str,
    content: str,
    source_format: str,
    extractor_identity: str,
    db_path: str | Path,
    source_locator: str | None = None,
    raw_asset_sha256: str | None = None,
    before_commit: ResearchBeforeCommit | None = None,
) -> ResearchPackageGraph:
    graph = build_workspace_document_graph(
        title=title,
        content=content,
        source_format=source_format,
        extractor_identity=extractor_identity,
        source_locator=source_locator,
        raw_asset_sha256=raw_asset_sha256,
    )
    return persist_research_graph(graph, db_path=db_path, before_commit=before_commit)
