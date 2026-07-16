"""GitHub repository Source -> ResearchPackageV1 workflow."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from app.adapters.research_package import build_candidate_research_package
from app.contracts.v1 import CONTRACT_VERSION, ClaimV1, EvidenceV1, SourceRecordV1
from shared.research_store import (
    GovernanceFinding,
    ResearchPackageGraph,
    SourceProvenanceRecord,
    persist_research_graph,
)
from shared.safe_http import SafeHTTPError, SafeHTTPPolicy, SafeHTTPResponse, fetch
from shared.stable_hash import stable_hash_text

_OWNER_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,37}[a-z0-9])?$")
_REPO_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,99}$")
_LICENSE_PATTERNS = (
    ("Apache-2.0", re.compile(r"\bapache(?:\s+license)?\s+2(?:\.0)?\b", re.I)),
    ("GPL-3.0", re.compile(r"\b(?:gpl|gnu general public license)\s*(?:v?3|3\.0)\b", re.I)),
    ("MIT", re.compile(r"\bmit\s+license\b|\blicense:\s*mit\b", re.I)),
    ("BSD-3-Clause", re.compile(r"\bbsd\s+3(?:-|\s+)clause\b", re.I)),
)


@dataclass(frozen=True)
class CanonicalGitHubRepository:
    owner: str
    repo: str
    canonical_url: str
    api_metadata_url: str
    api_readme_url: str
    source_group_id: str


@dataclass(frozen=True)
class QuarantinedPayload:
    locator: str
    payload_role: str
    retrieved_at: str
    content_hash: str
    content_type: str
    media_type: str
    byte_length: int
    body: bytes
    collector_identity: str
    extractor_identity: str
    source_group_id: str

    @classmethod
    def from_response(
        cls,
        response: SafeHTTPResponse,
        *,
        payload_role: str,
        retrieved_at: str,
        collector_identity: str,
        extractor_identity: str,
        source_group_id: str,
    ) -> QuarantinedPayload:
        content_type = response.headers.get("content-type", "")
        media_type = content_type.split(";", 1)[0].strip().lower()
        digest = hashlib.sha256(response.body).hexdigest()
        return cls(
            locator=response.url,
            payload_role=payload_role,
            retrieved_at=retrieved_at,
            content_hash=f"sha256:{digest}",
            content_type=content_type,
            media_type=media_type,
            byte_length=len(response.body),
            body=response.body,
            collector_identity=collector_identity,
            extractor_identity=extractor_identity,
            source_group_id=source_group_id,
        )


@dataclass(frozen=True)
class CollectedGitHubRepository:
    repository: CanonicalGitHubRepository
    metadata: QuarantinedPayload
    readme: QuarantinedPayload


GitHubFetcher = Callable[
    [str],
    SafeHTTPResponse,
]


def _default_fetcher(
    url: str,
    *,
    policy: SafeHTTPPolicy,
    headers: Mapping[str, str],
) -> SafeHTTPResponse:
    return fetch(url, policy=policy, headers=headers)


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _json_id(prefix: str, *parts: object) -> str:
    payload = json.dumps(parts, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    digest = stable_hash_text(payload, namespace=f"phase4-{prefix}")[:20]
    return f"{prefix}_{digest}"


def normalize_github_repository_url(url: str) -> CanonicalGitHubRepository:
    """Accept only canonical public HTTPS GitHub repository URLs."""

    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname is None
        or parsed.hostname.rstrip(".").lower() != "github.com"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port not in {None, 443}
    ):
        raise ValueError("repository_url must be a canonical https://github.com/owner/repo URL")
    if "%" in parsed.path or parsed.path.endswith(".git"):
        raise ValueError("repository_url must not use escaped path components or .git suffix")
    segments = [segment for segment in parsed.path.split("/") if segment]
    if len(segments) != 2 or any(segment in {".", ".."} for segment in segments):
        raise ValueError("repository_url must contain exactly owner and repo path segments")
    owner, repo = (segment.lower() for segment in segments)
    if not _OWNER_RE.fullmatch(owner) or not _REPO_RE.fullmatch(repo):
        raise ValueError("repository_url contains an invalid owner or repo name")
    canonical_url = f"https://github.com/{owner}/{repo}"
    source_group_id = _json_id("source_group", canonical_url)
    return CanonicalGitHubRepository(
        owner=owner,
        repo=repo,
        canonical_url=canonical_url,
        api_metadata_url=f"https://api.github.com/repos/{owner}/{repo}",
        api_readme_url=f"https://api.github.com/repos/{owner}/{repo}/readme",
        source_group_id=source_group_id,
    )


def _validate_fetch_response(
    response: SafeHTTPResponse,
    *,
    expected_url: str,
    policy: SafeHTTPPolicy,
) -> SafeHTTPResponse:
    if response.url != expected_url:
        raise SafeHTTPError("Safe HTTP response final URL does not match requested endpoint")
    if not 200 <= response.status < 300:
        raise SafeHTTPError(f"Safe HTTP response status is not successful: {response.status}")
    content_type = response.headers.get("content-type", "")
    media_type = content_type.split(";", 1)[0].strip().lower()
    allowed = {item.lower() for item in policy.allowed_content_types}
    if media_type not in allowed:
        raise SafeHTTPError(f"Content-Type not allowed: {media_type or 'missing'}")
    if len(response.body) > policy.max_bytes:
        raise SafeHTTPError(f"response exceeds {policy.max_bytes} bytes")
    return response


def collect_github_repository(
    repository_url: str,
    *,
    fetcher: Callable[..., SafeHTTPResponse] | None = None,
    clock: Callable[[], str] = _now_utc,
) -> CollectedGitHubRepository:
    """Collect GitHub metadata and README through bounded Safe HTTP policies."""

    repository = normalize_github_repository_url(repository_url)
    active_fetcher = fetcher or _default_fetcher
    metadata_policy = SafeHTTPPolicy(
        timeout=8.0,
        max_bytes=250_000,
        max_redirects=0,
        allowed_ports=(443,),
        allowed_content_types=("application/json",),
        allowed_hosts=("api.github.com",),
    )
    readme_policy = SafeHTTPPolicy(
        timeout=8.0,
        max_bytes=1_000_000,
        max_redirects=0,
        allowed_ports=(443,),
        allowed_content_types=(
            "application/octet-stream",
            "application/vnd.github.raw",
            "application/vnd.github.raw+json",
            "text/markdown",
            "text/plain",
        ),
        allowed_hosts=("api.github.com",),
    )
    metadata_response = _validate_fetch_response(
        active_fetcher(
            repository.api_metadata_url,
            policy=metadata_policy,
            headers={"Accept": "application/vnd.github+json"},
        ),
        expected_url=repository.api_metadata_url,
        policy=metadata_policy,
    )
    readme_response = _validate_fetch_response(
        active_fetcher(
            repository.api_readme_url,
            policy=readme_policy,
            headers={"Accept": "application/vnd.github.raw"},
        ),
        expected_url=repository.api_readme_url,
        policy=readme_policy,
    )
    metadata_retrieved_at = clock()
    readme_retrieved_at = clock()
    return CollectedGitHubRepository(
        repository=repository,
        metadata=QuarantinedPayload.from_response(
            metadata_response,
            payload_role="github_repository_metadata",
            retrieved_at=metadata_retrieved_at,
            collector_identity="github-api-v1",
            extractor_identity="github-metadata-json-v1",
            source_group_id=repository.source_group_id,
        ),
        readme=QuarantinedPayload.from_response(
            readme_response,
            payload_role="github_readme",
            retrieved_at=readme_retrieved_at,
            collector_identity="github-api-v1",
            extractor_identity="github-readme-raw-v1",
            source_group_id=repository.source_group_id,
        ),
    )


def _metadata_json(payload: QuarantinedPayload) -> dict[str, Any]:
    try:
        decoded = json.loads(payload.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("GitHub metadata payload is not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise ValueError("GitHub metadata payload must be a JSON object")
    return decoded


def _validate_metadata_repository(
    metadata: Mapping[str, Any],
    repository: CanonicalGitHubRepository,
) -> None:
    expected_name = f"{repository.owner}/{repository.repo}"
    full_name = metadata.get("full_name")
    html_url = metadata.get("html_url")
    if not isinstance(full_name, str) or full_name.casefold() != expected_name.casefold():
        raise ValueError("GitHub metadata does not match requested repository")
    if not isinstance(html_url, str):
        raise ValueError("GitHub metadata does not match requested repository")
    try:
        metadata_repository = normalize_github_repository_url(html_url)
    except ValueError as exc:
        raise ValueError("GitHub metadata does not match requested repository") from exc
    if metadata_repository.canonical_url != repository.canonical_url:
        raise ValueError("GitHub metadata does not match requested repository")


def _readme_text(payload: QuarantinedPayload) -> str:
    try:
        return payload.body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("GitHub README payload must be valid UTF-8") from exc


def _source_from_payload(
    *,
    repository: CanonicalGitHubRepository,
    payload: QuarantinedPayload,
    title: str,
    content: str,
    tags: list[str],
) -> tuple[SourceRecordV1, SourceProvenanceRecord]:
    source_id = _json_id(
        "source",
        repository.canonical_url,
        payload.payload_role,
        payload.content_hash,
    )
    source = SourceRecordV1(
        schema_version=CONTRACT_VERSION,
        source_id=source_id,
        title=title,
        content=content,
        source_locator=payload.locator,
        tags=tags,
        provenance_status="unverified",
        quarantine_status="candidate",
        created_at=payload.retrieved_at,
    )
    provenance = SourceProvenanceRecord(
        source_id=source_id,
        canonical_url=repository.canonical_url,
        source_group_id=payload.source_group_id,
        source_locator=payload.locator,
        retrieved_at=payload.retrieved_at,
        content_hash=payload.content_hash,
        content_type=payload.content_type,
        media_type=payload.media_type,
        byte_length=payload.byte_length,
        collector_identity=payload.collector_identity,
        extractor_identity=payload.extractor_identity,
        payload_role=payload.payload_role,
    )
    return source, provenance


def _context_around(text: str, term: str) -> str:
    position = text.lower().find(term.lower())
    if position < 0:
        return text[:220].strip() or term
    return text[max(0, position - 80) : position + len(term) + 120].strip()


def _metadata_context(field: str, term: str) -> str:
    return f"{field}: {term}"


def _license_from_metadata(metadata: dict[str, Any]) -> str | None:
    raw_license = metadata.get("license")
    if not isinstance(raw_license, dict):
        return None
    spdx = str(raw_license.get("spdx_id") or "").strip()
    if spdx and spdx.upper() != "NOASSERTION":
        return spdx
    name = str(raw_license.get("name") or "").strip()
    return name or None


def _license_from_readme(readme: str) -> tuple[str, str] | None:
    for spdx, pattern in _LICENSE_PATTERNS:
        match = pattern.search(readme)
        if match:
            return spdx, match.group(0)
    return None


def _first_heading(readme: str) -> str | None:
    for line in readme.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if heading:
                return heading
    return None


def _evidence(
    *,
    package_seed: str,
    claim_id: str,
    matched_term: str,
    source: SourceRecordV1,
    provenance: SourceProvenanceRecord,
    location: str,
    kind: str,
    context: str,
) -> EvidenceV1:
    return EvidenceV1(
        schema_version=CONTRACT_VERSION,
        evidence_id=_json_id(
            "evidence",
            package_seed,
            claim_id,
            source.source_id,
            provenance.content_hash,
            location,
            matched_term,
        ),
        claim_id=claim_id,
        matched_term=matched_term,
        source_locator=source.source_locator,
        location=location,
        asset_locator=provenance.content_hash,
        kind=kind,
        context=context,
        status="matched",
        provenance_status="caller_supplied",
        requires_human_review=True,
    )


def _claim(
    *,
    package_seed: str,
    statement: str,
    source_ids: list[str],
    status: str = "candidate",
    created_at: str,
) -> ClaimV1:
    return ClaimV1(
        schema_version=CONTRACT_VERSION,
        claim_id=_json_id("claim", package_seed, statement, source_ids),
        statement=statement,
        source_record_ids=source_ids,
        status=status,
        provenance_status="caller_supplied",
        requires_human_review=True,
        created_at=created_at,
    )


def _finding(
    *,
    package_id: str,
    finding_type: str,
    detail: str,
    severity: str,
    created_at: str,
    claim_id: str = "",
    evidence_ids: list[str] | None = None,
) -> GovernanceFinding:
    evidence_ids = evidence_ids or []
    return GovernanceFinding(
        finding_id=_json_id(
            "finding",
            package_id,
            finding_type,
            detail,
            claim_id,
            evidence_ids,
        ),
        package_id=package_id,
        finding_type=finding_type,
        detail=detail,
        severity=severity,
        claim_id=claim_id,
        evidence_ids=evidence_ids,
        created_at=created_at,
    )


def build_github_research_graph(collected: CollectedGitHubRepository) -> ResearchPackageGraph:
    """Parse quarantined GitHub payloads into a governed candidate graph."""

    repository = collected.repository
    metadata = _metadata_json(collected.metadata)
    _validate_metadata_repository(metadata, repository)
    readme = _readme_text(collected.readme)
    metadata_text = collected.metadata.body.decode("utf-8")
    metadata_source, metadata_provenance = _source_from_payload(
        repository=repository,
        payload=collected.metadata,
        title=f"GitHub repository metadata for {repository.owner}/{repository.repo}",
        content=metadata_text,
        tags=["github", "metadata", "repository"],
    )
    readme_source, readme_provenance = _source_from_payload(
        repository=repository,
        payload=collected.readme,
        title=f"GitHub README for {repository.owner}/{repository.repo}",
        content=readme,
        tags=["github", "readme", "repository"],
    )
    sources = [metadata_source, readme_source]
    provenance = [metadata_provenance, readme_provenance]
    package_seed = _json_id(
        "research_package",
        repository.canonical_url,
        collected.metadata.content_hash,
        collected.readme.content_hash,
    )
    created_at = min(collected.metadata.retrieved_at, collected.readme.retrieved_at)
    claims: list[ClaimV1] = []
    evidence: list[EvidenceV1] = []
    finding_specs: list[dict[str, object]] = []
    conflicts: list[str] = []
    unknowns: list[str] = [
        "Human review is required before promoting GitHub repository claims to verified knowledge."
    ]
    risks: list[str] = [
        "Single source group from one GitHub repository is insufficient for verified status.",
        "External GitHub payloads remain quarantined candidate material.",
    ]

    full_name = str(metadata.get("full_name") or f"{repository.owner}/{repository.repo}")
    description = str(metadata.get("description") or "").strip()
    if description:
        source_ids = [metadata_source.source_id]
        description_in_readme = description.lower() in readme.lower()
        if description_in_readme:
            source_ids.append(readme_source.source_id)
        claim = _claim(
            package_seed=package_seed,
            statement=f"GitHub metadata describes {full_name} as: {description}",
            source_ids=source_ids,
            created_at=created_at,
        )
        claims.append(claim)
        metadata_ev = _evidence(
            package_seed=package_seed,
            claim_id=claim.claim_id,
            matched_term=description,
            source=metadata_source,
            provenance=metadata_provenance,
            location="metadata:description",
            kind="github_api_metadata",
            context=_metadata_context("description", description),
        )
        evidence.append(metadata_ev)
        evidence_ids = [metadata_ev.evidence_id]
        if description_in_readme:
            readme_ev = _evidence(
                package_seed=package_seed,
                claim_id=claim.claim_id,
                matched_term=description,
                source=readme_source,
                provenance=readme_provenance,
                location="readme:description",
                kind="github_readme",
                context=_context_around(readme, description),
            )
            evidence.append(readme_ev)
            evidence_ids.append(readme_ev.evidence_id)
            finding_specs.append(
                {
                    "finding_type": "corroboration",
                    "detail": "README repeats the GitHub metadata description.",
                    "severity": "info",
                    "claim_id": claim.claim_id,
                    "evidence_ids": evidence_ids,
                }
            )
    else:
        unknowns.append("GitHub metadata does not provide a repository description.")

    language = str(metadata.get("language") or "").strip()
    if language:
        claim = _claim(
            package_seed=package_seed,
            statement=f"GitHub metadata lists {language} as the primary language for {full_name}.",
            source_ids=[metadata_source.source_id],
            created_at=created_at,
        )
        claims.append(claim)
        evidence.append(
            _evidence(
                package_seed=package_seed,
                claim_id=claim.claim_id,
                matched_term=language,
                source=metadata_source,
                provenance=metadata_provenance,
                location="metadata:language",
                kind="github_api_metadata",
                context=_metadata_context("language", language),
            )
        )
    else:
        unknowns.append("GitHub metadata does not report a primary language.")

    metadata_license = _license_from_metadata(metadata)
    readme_license = _license_from_readme(readme)
    if metadata_license:
        source_ids = [metadata_source.source_id]
        license_status = "candidate"
        if readme_license is not None:
            source_ids.append(readme_source.source_id)
            if readme_license[0].lower() != metadata_license.lower():
                license_status = "conflicted"
                conflicts.append(
                    "License conflict: GitHub metadata declares "
                    f"{metadata_license} but README mentions {readme_license[0]}."
                )
            else:
                finding_specs.append(
                    {
                        "finding_type": "corroboration",
                        "detail": "README license language matches GitHub metadata license.",
                        "severity": "info",
                        "claim_id": "",
                        "evidence_ids": [],
                    }
                )
        claim = _claim(
            package_seed=package_seed,
            statement=f"GitHub metadata declares the {metadata_license} license for {full_name}.",
            source_ids=source_ids,
            status=license_status,
            created_at=created_at,
        )
        claims.append(claim)
        metadata_ev = _evidence(
            package_seed=package_seed,
            claim_id=claim.claim_id,
            matched_term=metadata_license,
            source=metadata_source,
            provenance=metadata_provenance,
            location="metadata:license",
            kind="github_api_metadata",
            context=_metadata_context("license", metadata_license),
        )
        evidence.append(metadata_ev)
        license_evidence_ids = [metadata_ev.evidence_id]
        if readme_license is not None:
            readme_ev = _evidence(
                package_seed=package_seed,
                claim_id=claim.claim_id,
                matched_term=readme_license[1],
                source=readme_source,
                provenance=readme_provenance,
                location="readme:license",
                kind="github_readme",
                context=_context_around(readme, readme_license[1]),
            )
            evidence.append(readme_ev)
            license_evidence_ids.append(readme_ev.evidence_id)
            if license_status == "conflicted":
                finding_specs.append(
                    {
                        "finding_type": "conflict",
                        "detail": conflicts[-1],
                        "severity": "medium",
                        "claim_id": claim.claim_id,
                        "evidence_ids": license_evidence_ids,
                    }
                )
        for spec in finding_specs:
            if spec["finding_type"] == "corroboration" and not spec["claim_id"]:
                spec["claim_id"] = claim.claim_id
                spec["evidence_ids"] = license_evidence_ids
    else:
        unknowns.append("GitHub metadata does not declare a license.")

    heading = _first_heading(readme)
    if heading:
        claim = _claim(
            package_seed=package_seed,
            statement=f"The README title for {full_name} is {heading}.",
            source_ids=[readme_source.source_id],
            created_at=created_at,
        )
        claims.append(claim)
        evidence.append(
            _evidence(
                package_seed=package_seed,
                claim_id=claim.claim_id,
                matched_term=heading,
                source=readme_source,
                provenance=readme_provenance,
                location="readme:heading:1",
                kind="github_readme",
                context=_context_around(readme, heading),
            )
        )
    else:
        unknowns.append("README does not expose a Markdown title.")

    if not claims:
        claim = _claim(
            package_seed=package_seed,
            statement=f"GitHub API returned repository metadata for {full_name}.",
            source_ids=[metadata_source.source_id],
            created_at=created_at,
        )
        claims.append(claim)
        evidence.append(
            _evidence(
                package_seed=package_seed,
                claim_id=claim.claim_id,
                matched_term=full_name,
                source=metadata_source,
                provenance=metadata_provenance,
                location="metadata:full_name",
                kind="github_api_metadata",
                context=_metadata_context("full_name", full_name),
            )
        )

    if bool(metadata.get("archived")):
        risks.append("Repository is archived according to GitHub metadata.")

    package = build_candidate_research_package(
        package_id=package_seed,
        sources=sources,
        claims=claims,
        evidence=evidence,
        conflicts=conflicts,
        unknowns=unknowns,
        risks=risks,
        created_at=created_at,
        source_group_ids_by_locator={
            item.source_locator: item.source_group_id for item in provenance
        },
    )
    findings: list[GovernanceFinding] = []
    for detail in conflicts:
        if not any(spec.get("detail") == detail for spec in finding_specs):
            finding_specs.append(
                {
                    "finding_type": "conflict",
                    "detail": detail,
                    "severity": "medium",
                    "claim_id": "",
                    "evidence_ids": [],
                }
            )
    for detail in unknowns:
        finding_specs.append(
            {
                "finding_type": "unknown",
                "detail": detail,
                "severity": "low",
                "claim_id": "",
                "evidence_ids": [],
            }
        )
    for detail in risks:
        finding_specs.append(
            {
                "finding_type": "risk",
                "detail": detail,
                "severity": "medium" if "single source" in detail.lower() else "low",
                "claim_id": "",
                "evidence_ids": [],
            }
        )
    for spec in finding_specs:
        findings.append(
            _finding(
                package_id=package.package_id,
                finding_type=str(spec["finding_type"]),
                detail=str(spec["detail"]),
                severity=str(spec["severity"]),
                created_at=created_at,
                claim_id=str(spec["claim_id"]),
                evidence_ids=list(spec["evidence_ids"]),
            )
        )
    intake_id = _json_id("intake", repository.canonical_url)
    return ResearchPackageGraph(
        canonical_url=repository.canonical_url,
        intake_id=intake_id,
        package=package,
        sources=sources,
        source_provenance=provenance,
        claims=claims,
        evidence=evidence,
        findings=findings,
    )


def validate_github_graph_identity(graph: ResearchPackageGraph) -> None:
    """Recompute stable GitHub graph identities and raw-source evidence anchors."""

    repository = normalize_github_repository_url(graph.canonical_url)
    provenance_by_role = {record.payload_role: record for record in graph.source_provenance}
    if set(provenance_by_role) != {"github_repository_metadata", "github_readme"}:
        raise ValueError("GitHub graph must contain exactly metadata and README provenance")
    if len(provenance_by_role) != len(graph.source_provenance):
        raise ValueError("GitHub graph contains duplicate provenance roles")
    expected_group = _json_id("source_group", repository.canonical_url)
    source_by_id = {source.source_id: source for source in graph.sources}
    source_by_locator = {source.source_locator: source for source in graph.sources}
    provenance_by_id = {record.source_id: record for record in graph.source_provenance}
    if len(source_by_id) != len(graph.sources) or len(source_by_locator) != len(graph.sources):
        raise ValueError("GitHub graph contains ambiguous source identity")
    for record in graph.source_provenance:
        expected_source_id = _json_id(
            "source",
            repository.canonical_url,
            record.payload_role,
            record.content_hash,
        )
        if record.source_group_id != expected_group or record.source_id != expected_source_id:
            raise ValueError("GitHub source identity does not match raw provenance")
        source = source_by_id.get(record.source_id)
        if source is None or source.source_locator != record.source_locator:
            raise ValueError("GitHub source identity does not match source record")

    metadata = provenance_by_role["github_repository_metadata"]
    readme = provenance_by_role["github_readme"]
    package_seed = _json_id(
        "research_package",
        repository.canonical_url,
        metadata.content_hash,
        readme.content_hash,
    )
    if graph.package.package_id != package_seed:
        raise ValueError("GitHub package identity does not match raw provenance")
    claims_by_id = {claim.claim_id: claim for claim in graph.claims}
    if len(claims_by_id) != len(graph.claims):
        raise ValueError("GitHub graph contains duplicate claim identity")
    for claim in graph.claims:
        expected_claim_id = _json_id(
            "claim", package_seed, claim.statement, claim.source_record_ids
        )
        if claim.claim_id != expected_claim_id:
            raise ValueError("GitHub claim identity does not match claim semantics")
    for item in graph.evidence:
        source = source_by_locator.get(item.source_locator)
        if source is None:
            raise ValueError("GitHub evidence source locator is unknown")
        record = provenance_by_id[source.source_id]
        expected_evidence_id = _json_id(
            "evidence",
            package_seed,
            item.claim_id,
            source.source_id,
            record.content_hash,
            item.location,
            item.matched_term,
        )
        if item.evidence_id != expected_evidence_id:
            raise ValueError("GitHub evidence identity does not match evidence semantics")
        if item.matched_term.casefold() not in source.content.casefold():
            raise ValueError("GitHub evidence matched term is absent from source content")
        if item.matched_term.casefold() not in item.context.casefold():
            raise ValueError("GitHub evidence context does not contain matched term")
        expected_prefix = (
            "metadata:" if record.payload_role == "github_repository_metadata" else "readme:"
        )
        expected_kind = (
            "github_api_metadata"
            if record.payload_role == "github_repository_metadata"
            else "github_readme"
        )
        if not item.location.startswith(expected_prefix) or item.kind != expected_kind:
            raise ValueError("GitHub evidence location does not match source role")
    for finding in graph.findings:
        expected_finding_id = _json_id(
            "finding",
            graph.package.package_id,
            finding.finding_type,
            finding.detail,
            finding.claim_id,
            finding.evidence_ids,
        )
        if finding.finding_id != expected_finding_id:
            raise ValueError("GitHub finding identity does not match finding semantics")
    if graph.intake_id != _json_id("intake", repository.canonical_url):
        raise ValueError("GitHub intake identity does not match canonical repository")

    role_policy = {
        "github_repository_metadata": (
            repository.api_metadata_url,
            "github-metadata-json-v1",
            {"application/json"},
        ),
        "github_readme": (
            repository.api_readme_url,
            "github-readme-raw-v1",
            {
                "application/octet-stream",
                "application/vnd.github.raw",
                "application/vnd.github.raw+json",
                "text/markdown",
                "text/plain",
            },
        ),
    }
    payloads: dict[str, QuarantinedPayload] = {}
    for role, record in provenance_by_role.items():
        expected_locator, expected_extractor, allowed_media = role_policy[role]
        if (
            record.source_locator != expected_locator
            or record.collector_identity != "github-api-v1"
            or record.extractor_identity != expected_extractor
            or record.media_type not in allowed_media
        ):
            raise ValueError("GitHub source provenance does not match collector policy")
        source = source_by_id[record.source_id]
        payloads[role] = QuarantinedPayload(
            locator=record.source_locator,
            payload_role=role,
            retrieved_at=record.retrieved_at,
            content_hash=record.content_hash,
            content_type=record.content_type,
            media_type=record.media_type,
            byte_length=record.byte_length,
            body=source.content.encode("utf-8"),
            collector_identity=record.collector_identity,
            extractor_identity=record.extractor_identity,
            source_group_id=record.source_group_id,
        )
    rebuilt = build_github_research_graph(
        CollectedGitHubRepository(
            repository=repository,
            metadata=payloads["github_repository_metadata"],
            readme=payloads["github_readme"],
        )
    )
    if graph.model_copy(update={"findings": []}) != rebuilt.model_copy(
        update={"findings": []}
    ) or sorted(graph.findings, key=lambda item: item.finding_id) != sorted(
        rebuilt.findings, key=lambda item: item.finding_id
    ):
        raise ValueError("GitHub graph semantics do not match quarantined raw payloads")


def research_github_repository(
    repository_url: str,
    *,
    fetcher: Callable[..., SafeHTTPResponse] | None = None,
    db_path: str | Path | None = None,
) -> ResearchPackageGraph:
    """Collect, parse, govern, persist, and reload one GitHub research package."""

    collected = collect_github_repository(repository_url, fetcher=fetcher)
    graph = build_github_research_graph(collected)
    return persist_research_graph(graph, db_path=db_path)
