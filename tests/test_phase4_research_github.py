from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import pytest

from shared.safe_http import SafeHTTPError, SafeHTTPPolicy, SafeHTTPResponse


def _prepare_research_schema(database: Path) -> None:
    from shared.migration_runner import MigrationOperator

    database.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database)):
        pass
    MigrationOperator(
        db_path=database,
        backup_dir=database.parent / "migration-backups",
    ).apply("research.sqlite")


@dataclass
class FixtureTransport:
    responses: dict[str, SafeHTTPResponse]
    calls: list[tuple[str, SafeHTTPPolicy, Mapping[str, str]]]

    def __call__(
        self,
        url: str,
        *,
        policy: SafeHTTPPolicy,
        headers: Mapping[str, str],
    ) -> SafeHTTPResponse:
        self.calls.append((url, policy, headers))
        return self.responses[url]


def _metadata(
    *,
    description: str = "A deterministic research workflow for evidence packages.",
    license_spdx: str | None = "MIT",
    archived: bool = False,
) -> bytes:
    license_payload = None
    if license_spdx is not None:
        license_payload = {"spdx_id": license_spdx, "name": f"{license_spdx} License"}
    return json.dumps(
        {
            "id": 123,
            "name": "loop-os",
            "full_name": "octo/loop-os",
            "html_url": "https://github.com/octo/loop-os",
            "description": description,
            "language": "Python",
            "license": license_payload,
            "topics": ["research", "evidence"],
            "archived": archived,
            "default_branch": "main",
            "stargazers_count": 42,
            "forks_count": 3,
            "open_issues_count": 2,
            "pushed_at": "2026-07-16T00:00:00Z",
        },
        sort_keys=True,
    ).encode()


def _transport(
    *,
    metadata_body: bytes | None = None,
    readme_body: bytes | None = None,
    metadata_content_type: str = "application/json",
    readme_content_type: str = "text/plain",
) -> FixtureTransport:
    metadata_url = "https://api.github.com/repos/octo/loop-os"
    readme_url = "https://api.github.com/repos/octo/loop-os/readme"
    return FixtureTransport(
        responses={
            metadata_url: SafeHTTPResponse(
                url=metadata_url,
                status=200,
                headers={"content-type": metadata_content_type},
                body=metadata_body or _metadata(),
            ),
            readme_url: SafeHTTPResponse(
                url=readme_url,
                status=200,
                headers={"content-type": readme_content_type},
                body=readme_body
                or b"# Loop OS\n\nA deterministic research workflow for evidence packages.\n\nMIT License\n",
            ),
        },
        calls=[],
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/octo/loop-os",
        "https://user:token@github.com/octo/loop-os",
        "https://github.com/octo/loop-os#readme",
        "https://github.com/octo/loop-os?tab=readme",
        "https://github.com/octo/loop-os/../../admin",
        "https://github.evil.test/octo/loop-os",
        "https://api.github.com/repos/octo/loop-os",
        "https://github.com/octo",
        "https://github.com/octo/loop-os.git",
        "https://github.com/octo/loop%2fos",
    ],
)
def test_phase4_rejects_noncanonical_or_unsafe_github_urls(url: str, tmp_path: Path) -> None:
    from app.facades.research import research_github_repository

    transport = _transport()
    with pytest.raises(ValueError):
        research_github_repository(url, fetcher=transport, db_path=tmp_path / "phase4.sqlite")
    assert transport.calls == []


def test_phase4_collects_only_through_safe_http_github_api_policy(tmp_path: Path) -> None:
    from app.facades.research import research_github_repository

    transport = _transport()
    database = tmp_path / "phase4.sqlite"
    _prepare_research_schema(database)
    result = research_github_repository(
        "https://github.com/OCTO/Loop-OS",
        fetcher=transport,
        db_path=database,
    )

    assert result.canonical_url == "https://github.com/octo/loop-os"
    assert [call[0] for call in transport.calls] == [
        "https://api.github.com/repos/octo/loop-os",
        "https://api.github.com/repos/octo/loop-os/readme",
    ]
    for _url, policy, _headers in transport.calls:
        assert policy.allowed_hosts == ("api.github.com",)
        assert policy.allowed_ports == (443,)
        assert policy.max_redirects == 0
        assert policy.max_bytes <= 1_000_000
        assert policy.timeout <= 10
    assert result.package.status == "candidate"
    assert result.package.requires_human_review is True


def test_phase4_accepts_github_raw_json_media_type(tmp_path: Path) -> None:
    from app.facades.research import research_github_repository

    database = tmp_path / "phase4.sqlite"
    _prepare_research_schema(database)
    result = research_github_repository(
        "https://github.com/octo/loop-os",
        fetcher=_transport(readme_content_type="application/vnd.github.raw+json"),
        db_path=database,
    )
    assert result.package.status == "candidate"


def test_phase4_rejects_unexpected_content_type_and_payload_size(tmp_path: Path) -> None:
    from app.facades.research import research_github_repository

    with pytest.raises(SafeHTTPError, match="Content-Type"):
        research_github_repository(
            "https://github.com/octo/loop-os",
            fetcher=_transport(metadata_content_type="text/html"),
            db_path=tmp_path / "content-type.sqlite",
        )

    with pytest.raises(SafeHTTPError, match="response exceeds"):
        research_github_repository(
            "https://github.com/octo/loop-os",
            fetcher=_transport(readme_body=b"x" * 1_000_001),
            db_path=tmp_path / "size.sqlite",
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("status", 500, "status"),
        ("url", "https://evil.example/redirected", "final URL"),
    ],
)
def test_phase4_revalidates_injected_transport_response_boundary(
    field: str,
    value: object,
    message: str,
    tmp_path: Path,
) -> None:
    from app.facades.research import research_github_repository

    transport = _transport()
    response = transport.responses["https://api.github.com/repos/octo/loop-os"]
    transport.responses["https://api.github.com/repos/octo/loop-os"] = SafeHTTPResponse(
        url=str(value) if field == "url" else response.url,
        status=int(value) if field == "status" else response.status,
        headers=response.headers,
        body=response.body,
    )
    with pytest.raises(SafeHTTPError, match=message):
        research_github_repository(
            "https://github.com/octo/loop-os",
            fetcher=transport,
            db_path=tmp_path / f"invalid-{field}.sqlite",
        )


def test_phase4_quarantines_payloads_and_preserves_source_provenance(tmp_path: Path) -> None:
    from app.facades.research import get_research_package, research_github_repository

    database = tmp_path / "phase4.sqlite"
    _prepare_research_schema(database)
    result = research_github_repository(
        "https://github.com/octo/loop-os",
        fetcher=_transport(),
        db_path=database,
    )
    reloaded = get_research_package(result.package.package_id, db_path=database)

    assert {source.quarantine_status for source in reloaded.sources} == {"candidate"}
    assert {source.provenance_status for source in reloaded.sources} == {"unverified"}
    assert {record.source_group_id for record in reloaded.source_provenance} == {
        reloaded.source_provenance[0].source_group_id
    }
    assert all(record.content_hash.startswith("sha256:") for record in reloaded.source_provenance)
    assert {record.collector_identity for record in reloaded.source_provenance} == {"github-api-v1"}
    assert {record.extractor_identity for record in reloaded.source_provenance} == {
        "github-metadata-json-v1",
        "github-readme-raw-v1",
    }
    assert all(evidence.asset_locator.startswith("sha256:") for evidence in reloaded.evidence)


def test_phase4_same_repo_metadata_and_readme_count_as_one_independent_source(
    tmp_path: Path,
) -> None:
    from app.facades.research import get_research_package, research_github_repository

    database = tmp_path / "phase4.sqlite"
    _prepare_research_schema(database)
    result = research_github_repository(
        "https://github.com/octo/loop-os",
        fetcher=_transport(),
        db_path=database,
    )
    reloaded = get_research_package(result.package.package_id, db_path=database)

    assert len(reloaded.sources) == 2
    assert len(reloaded.evidence) >= 2
    assert reloaded.package.independent_source_count == 1
    assert reloaded.package.verification_status == "caller_supplied_candidate"
    assert any("single source group" in risk.lower() for risk in reloaded.package.risks)
    assert all(claim.status in {"candidate", "conflicted", "unknown"} for claim in reloaded.claims)


def test_phase4_generates_conflict_unknown_risk_and_corroboration_findings(
    tmp_path: Path,
) -> None:
    from app.facades.research import research_github_repository

    database = tmp_path / "phase4.sqlite"
    _prepare_research_schema(database)
    result = research_github_repository(
        "https://github.com/octo/loop-os",
        fetcher=_transport(
            metadata_body=_metadata(
                description="A deterministic research workflow for evidence packages.",
                license_spdx="MIT",
                archived=True,
            ),
            readme_body=(
                b"# Loop OS\n"
                b"A deterministic research workflow for evidence packages.\n"
                b"This project is distributed under the Apache License 2.0.\n"
            ),
        ),
        db_path=database,
    )

    finding_types = {finding.finding_type for finding in result.findings}
    assert {"corroboration", "conflict", "unknown", "risk"} <= finding_types
    assert any("license" in item.lower() for item in result.package.conflicts)
    assert any("human review" in item.lower() for item in result.package.unknowns)
    assert any("archived" in item.lower() for item in result.package.risks)


def test_phase4_runtime_refuses_pending_schema_without_creating_database(tmp_path: Path) -> None:
    from app.facades.research import research_github_repository

    database = tmp_path / "pending.sqlite"
    with pytest.raises(RuntimeError, match="research schema migration is pending"):
        research_github_repository(
            "https://github.com/octo/loop-os",
            fetcher=_transport(),
            db_path=database,
        )
    assert not database.exists()


def test_phase4_read_refuses_pending_schema_without_creating_database(tmp_path: Path) -> None:
    from app.facades.research import get_research_package

    database = tmp_path / "pending-read.sqlite"
    with pytest.raises(RuntimeError, match="research schema migration is pending"):
        get_research_package("missing-package", db_path=database)
    assert not database.exists()


def test_phase4_rejects_metadata_from_a_different_repository(tmp_path: Path) -> None:
    from app.facades.research import research_github_repository

    database = tmp_path / "phase4.sqlite"
    _prepare_research_schema(database)
    payload = json.loads(_metadata())
    payload["full_name"] = "attacker/other-repo"
    payload["html_url"] = "https://github.com/attacker/other-repo"

    with pytest.raises(ValueError, match="does not match requested repository"):
        research_github_repository(
            "https://github.com/octo/loop-os",
            fetcher=_transport(metadata_body=json.dumps(payload).encode()),
            db_path=database,
        )

    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM research_packages_v1").fetchone()[0] == 0


def test_phase4_persistence_is_transactional_on_mid_graph_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.facades.research import research_github_repository
    from shared import research_store

    database = tmp_path / "phase4.sqlite"
    _prepare_research_schema(database)

    def fail_after_sources(*args, **kwargs):
        raise RuntimeError("injected graph write failure")

    monkeypatch.setattr(research_store, "_before_claim_write", fail_after_sources)

    with pytest.raises(RuntimeError, match="injected graph write failure"):
        research_github_repository(
            "https://github.com/octo/loop-os",
            fetcher=_transport(),
            db_path=database,
        )

    with closing(sqlite3.connect(database)) as connection:
        for table in (
            "research_sources_v1",
            "research_claims_v1",
            "research_evidence_v1",
            "research_packages_v1",
            "research_governance_findings_v1",
        ):
            assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_phase4_persistence_is_idempotent_for_same_url_and_content(tmp_path: Path) -> None:
    from app.facades.research import research_github_repository

    database = tmp_path / "phase4.sqlite"
    _prepare_research_schema(database)
    first = research_github_repository(
        "https://github.com/octo/loop-os",
        fetcher=_transport(),
        db_path=database,
    )
    second = research_github_repository(
        "https://github.com/octo/loop-os",
        fetcher=_transport(),
        db_path=database,
    )

    assert second.package == first.package
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM research_packages_v1").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM research_sources_v1").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM ir_intake_cards").fetchone()[0] == 1


def test_phase4_rejects_same_id_with_different_semantics_before_write(
    tmp_path: Path,
) -> None:
    from app.facades.research import research_github_repository
    from shared.research_store import ResearchPersistenceError, persist_research_graph

    database = tmp_path / "phase4.sqlite"
    _prepare_research_schema(database)
    graph = research_github_repository(
        "https://github.com/octo/loop-os",
        fetcher=_transport(),
        db_path=database,
    )
    tampered = graph.model_copy(deep=True)
    tampered.sources[0].title = "tampered title under an existing stable ID"

    with pytest.raises(ResearchPersistenceError, match="graph semantics"):
        persist_research_graph(tampered, db_path=database)


def test_phase4_rejects_evidence_from_source_not_declared_by_its_claim(tmp_path: Path) -> None:
    from app.facades.research import research_github_repository
    from shared.research_store import ResearchPersistenceError, persist_research_graph

    database = tmp_path / "phase4.sqlite"
    _prepare_research_schema(database)
    graph = research_github_repository(
        "https://github.com/octo/loop-os", fetcher=_transport(), db_path=database
    )
    tampered = graph.model_copy(deep=True)
    claims = {claim.claim_id: claim for claim in tampered.claims}
    sources = {source.source_id: source for source in tampered.sources}
    target = next(
        item
        for item in tampered.evidence
        if set(claims[item.claim_id].source_record_ids) != set(sources)
    )
    alternate = next(
        source
        for source_id, source in sources.items()
        if source_id not in claims[target.claim_id].source_record_ids
    )
    target.source_locator = alternate.source_locator

    with pytest.raises(ResearchPersistenceError, match="claim sources"):
        persist_research_graph(tampered, db_path=database)


def test_phase4_store_rejects_promoted_graph_without_review_provenance(tmp_path: Path) -> None:
    from app.facades.research import research_github_repository
    from shared.research_store import ResearchPersistenceError, persist_research_graph

    database = tmp_path / "phase4.sqlite"
    _prepare_research_schema(database)
    graph = research_github_repository(
        "https://github.com/octo/loop-os", fetcher=_transport(), db_path=database
    )
    promoted = graph.model_copy(deep=True)
    promoted.package.status = "released"
    promoted.package.provenance_status = "server_verified"
    promoted.package.requires_human_review = False

    with pytest.raises(ResearchPersistenceError, match="candidate-only"):
        persist_research_graph(promoted, db_path=database)


def test_phase4_read_path_rejects_malformed_persisted_json(tmp_path: Path) -> None:
    from app.facades.research import get_research_package, research_github_repository
    from shared.research_store import ResearchPersistenceError

    database = tmp_path / "phase4.sqlite"
    _prepare_research_schema(database)
    package_id = research_github_repository(
        "https://github.com/octo/loop-os",
        fetcher=_transport(),
        db_path=database,
    ).package.package_id
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            "UPDATE research_packages_v1 SET source_record_ids_json='not-json' WHERE id=?",
            (package_id,),
        )
        connection.commit()

    with pytest.raises(ResearchPersistenceError, match="source_record_ids_json"):
        get_research_package(package_id, db_path=database)


def test_phase4_read_path_rejects_source_content_hash_mismatch(tmp_path: Path) -> None:
    from app.facades.research import get_research_package, research_github_repository
    from shared.research_store import ResearchPersistenceError

    database = tmp_path / "phase4.sqlite"
    _prepare_research_schema(database)
    package_id = research_github_repository(
        "https://github.com/octo/loop-os",
        fetcher=_transport(),
        db_path=database,
    ).package.package_id
    with closing(sqlite3.connect(database)) as connection:
        cursor = connection.execute(
            "UPDATE research_sources_v1 SET content=content || 'tampered' "
            "WHERE id=(SELECT id FROM research_sources_v1 ORDER BY id LIMIT 1)"
        )
        assert cursor.rowcount == 1
        connection.commit()

    with pytest.raises(ResearchPersistenceError, match="source content hash mismatch"):
        get_research_package(package_id, db_path=database)


def test_phase4_read_path_rejects_evidence_source_hash_mismatch(tmp_path: Path) -> None:
    from app.facades.research import get_research_package, research_github_repository
    from shared.research_store import ResearchPersistenceError

    database = tmp_path / "phase4.sqlite"
    _prepare_research_schema(database)
    package_id = research_github_repository(
        "https://github.com/octo/loop-os",
        fetcher=_transport(),
        db_path=database,
    ).package.package_id
    with closing(sqlite3.connect(database)) as connection:
        cursor = connection.execute(
            "UPDATE research_evidence_v1 SET source_content_hash='sha256:tampered' "
            "WHERE id=(SELECT id FROM research_evidence_v1 ORDER BY id LIMIT 1)"
        )
        assert cursor.rowcount == 1
        connection.commit()

    with pytest.raises(ResearchPersistenceError, match="evidence source hash mismatch"):
        get_research_package(package_id, db_path=database)


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("source_group_ids_json", "[]", "source group"),
        ("independent_source_count", "99", "independent source count"),
    ],
)
def test_phase4_read_path_rejects_package_provenance_summary_drift(
    column: str,
    value: str,
    message: str,
    tmp_path: Path,
) -> None:
    from app.facades.research import get_research_package, research_github_repository
    from shared.research_store import ResearchPersistenceError

    database = tmp_path / "phase4.sqlite"
    _prepare_research_schema(database)
    package_id = research_github_repository(
        "https://github.com/octo/loop-os", fetcher=_transport(), db_path=database
    ).package.package_id
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            f"UPDATE research_packages_v1 SET {column}=? WHERE id=?",
            (value, package_id),
        )
        connection.commit()

    with pytest.raises(ResearchPersistenceError, match=message):
        get_research_package(package_id, db_path=database)


def test_phase4_read_path_rejects_evidence_asset_hash_drift(tmp_path: Path) -> None:
    from app.facades.research import get_research_package, research_github_repository
    from shared.research_store import ResearchPersistenceError

    database = tmp_path / "phase4.sqlite"
    _prepare_research_schema(database)
    package_id = research_github_repository(
        "https://github.com/octo/loop-os", fetcher=_transport(), db_path=database
    ).package.package_id
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            "UPDATE research_evidence_v1 SET asset_locator='sha256:tampered' "
            "WHERE id=(SELECT id FROM research_evidence_v1 ORDER BY id LIMIT 1)"
        )
        connection.commit()

    with pytest.raises(ResearchPersistenceError, match="asset locator"):
        get_research_package(package_id, db_path=database)


def test_phase4_read_path_rejects_self_consistent_source_tamper_with_old_id(
    tmp_path: Path,
) -> None:
    import hashlib

    from app.facades.research import get_research_package, research_github_repository
    from shared.research_store import ResearchPersistenceError

    database = tmp_path / "phase4.sqlite"
    _prepare_research_schema(database)
    package_id = research_github_repository(
        "https://github.com/octo/loop-os", fetcher=_transport(), db_path=database
    ).package.package_id
    with closing(sqlite3.connect(database)) as connection:
        row = connection.execute(
            "SELECT id, source_locator, content FROM research_sources_v1 "
            "WHERE payload_role='github_readme'"
        ).fetchone()
        content = row[2] + "\nself-consistent tamper"
        digest = "sha256:" + hashlib.sha256(content.encode()).hexdigest()
        connection.execute(
            "UPDATE research_sources_v1 SET content=?, content_hash=?, byte_length=? WHERE id=?",
            (content, digest, len(content.encode()), row[0]),
        )
        connection.execute(
            "UPDATE research_evidence_v1 SET source_content_hash=?, asset_locator=? "
            "WHERE source_locator=?",
            (digest, digest, row[1]),
        )
        connection.commit()

    with pytest.raises(ResearchPersistenceError, match="source identity"):
        get_research_package(package_id, db_path=database)


def test_phase4_read_path_rejects_source_semantic_drift_outside_id_hash(
    tmp_path: Path,
) -> None:
    from app.facades.research import get_research_package, research_github_repository
    from shared.research_store import ResearchPersistenceError

    database = tmp_path / "phase4.sqlite"
    _prepare_research_schema(database)
    package_id = research_github_repository(
        "https://github.com/octo/loop-os", fetcher=_transport(), db_path=database
    ).package.package_id
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            "UPDATE research_sources_v1 SET title='self-consistent unrelated title' "
            "WHERE payload_role='github_readme'"
        )
        connection.commit()

    with pytest.raises(ResearchPersistenceError, match="graph semantics"):
        get_research_package(package_id, db_path=database)


def test_phase4_read_path_rejects_evidence_semantic_tamper_with_old_id(
    tmp_path: Path,
) -> None:
    from app.facades.research import get_research_package, research_github_repository
    from shared.research_store import ResearchPersistenceError

    database = tmp_path / "phase4.sqlite"
    _prepare_research_schema(database)
    package_id = research_github_repository(
        "https://github.com/octo/loop-os", fetcher=_transport(), db_path=database
    ).package.package_id
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            "UPDATE research_evidence_v1 SET matched_term='Python', context='language: Python' "
            "WHERE id=(SELECT id FROM research_evidence_v1 "
            "WHERE kind='github_api_metadata' ORDER BY id LIMIT 1)"
        )
        connection.commit()

    with pytest.raises(ResearchPersistenceError, match="evidence identity"):
        get_research_package(package_id, db_path=database)


def test_phase4_read_path_rejects_unrelated_intake_content(tmp_path: Path) -> None:
    from app.facades.research import get_research_package, research_github_repository
    from shared.research_store import ResearchPersistenceError

    database = tmp_path / "phase4.sqlite"
    _prepare_research_schema(database)
    package_id = research_github_repository(
        "https://github.com/octo/loop-os", fetcher=_transport(), db_path=database
    ).package.package_id
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            "UPDATE ir_intake_cards SET title='unrelated intake under same ID' "
            "WHERE id=(SELECT intake_id FROM research_packages_v1 WHERE id=?)",
            (package_id,),
        )
        connection.commit()

    with pytest.raises(ResearchPersistenceError, match="intake content mismatch"):
        get_research_package(package_id, db_path=database)


def test_phase4_read_path_rejects_dangling_governance_evidence(tmp_path: Path) -> None:
    from app.facades.research import get_research_package, research_github_repository
    from shared.research_store import ResearchPersistenceError

    database = tmp_path / "phase4.sqlite"
    _prepare_research_schema(database)
    package_id = research_github_repository(
        "https://github.com/octo/loop-os",
        fetcher=_transport(),
        db_path=database,
    ).package.package_id
    with closing(sqlite3.connect(database)) as connection:
        cursor = connection.execute(
            "UPDATE research_governance_findings_v1 "
            "SET evidence_ids_json='[\"missing-evidence\"]' "
            "WHERE id=(SELECT id FROM research_governance_findings_v1 ORDER BY id LIMIT 1)"
        )
        assert cursor.rowcount == 1
        connection.commit()

    with pytest.raises(ResearchPersistenceError, match="governance finding references"):
        get_research_package(package_id, db_path=database)


def test_phase4_recorded_schema_rejects_index_drift(tmp_path: Path) -> None:
    from shared import research_migration

    database = tmp_path / "phase4.sqlite"
    _prepare_research_schema(database)
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("DROP INDEX idx_research_sources_locator_hash_v1")
        connection.commit()

    with pytest.raises(RuntimeError, match="recorded research migration schema mismatch"):
        research_migration.status(db_path=database)


def test_phase4_api_facade_and_status_use_sidecar_free_readonly_connections(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from fastapi.testclient import TestClient

    from app.facades.research import get_research_package, research_github_repository
    from inspiration_research.api import app
    from shared import research_migration, research_store, storage
    from shared.migration_runner import MigrationOperator, MigrationOwner, MigrationRegistry

    database = tmp_path / "phase4.sqlite"
    _prepare_research_schema(database)
    package_id = research_github_repository(
        "https://github.com/octo/loop-os",
        fetcher=_transport(),
        db_path=database,
    ).package.package_id
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        connection.execute("PRAGMA journal_mode=DELETE")
    sidecars = [Path(f"{database}{suffix}") for suffix in ("-wal", "-shm")]
    assert all(not path.exists() for path in sidecars)

    original_connect = sqlite3.connect
    calls: list[str] = []
    query_only_calls: list[str] = []

    class RecordingConnection:
        def __init__(self, connection, locator: str):
            object.__setattr__(self, "_connection", connection)
            object.__setattr__(self, "_locator", locator)

        def __setattr__(self, name, value):
            if name in {"_connection", "_locator"}:
                object.__setattr__(self, name, value)
            else:
                setattr(self._connection, name, value)

        def execute(self, sql, *args, **kwargs):
            if str(sql).strip().casefold() == "pragma query_only=on":
                query_only_calls.append(self._locator)
            return self._connection.execute(sql, *args, **kwargs)

        def close(self):
            return self._connection.close()

        def __getattr__(self, name):
            return getattr(self._connection, name)

    def guarded_connect(target, *args, **kwargs):
        locator = str(target)
        if locator == ":memory:":
            return original_connect(target, *args, **kwargs)
        assert kwargs.get("uri") is True
        assert "mode=ro" in locator
        assert "immutable=1" in locator
        calls.append(locator)
        return RecordingConnection(original_connect(target, *args, **kwargs), locator)

    monkeypatch.setattr(research_migration.sqlite3, "connect", guarded_connect)
    monkeypatch.setattr(research_store.sqlite3, "connect", guarded_connect)
    monkeypatch.setattr(storage, "DB_PATH", database)

    assert research_migration.status(db_path=database)["pending"] == []
    assert len(calls) == 1
    assert get_research_package(package_id, db_path=database).package.package_id == package_id
    assert len(calls) == 2
    response = TestClient(app).get(f"/research/packages/{package_id}")
    assert response.status_code == 200
    assert response.json()["package"]["package_id"] == package_id
    assert len(calls) == 3
    registry = MigrationRegistry(
        [MigrationOwner("research.sqlite", 1, "research_packages_v1", "sqlite_research")]
    )
    operator = MigrationOperator(
        db_path=database,
        backup_dir=tmp_path / "migration-backups",
        registry=registry,
    )
    assert operator.status()[0]["owner"] == "research.sqlite"
    assert query_only_calls == calls
    assert all(not path.exists() for path in sidecars)


def test_phase4_read_paths_fail_closed_without_mutating_live_sidecars(tmp_path: Path) -> None:
    from app.facades.research import get_research_package, research_github_repository
    from shared import research_migration

    database = tmp_path / "phase4.sqlite"
    _prepare_research_schema(database)
    package_id = research_github_repository(
        "https://github.com/octo/loop-os",
        fetcher=_transport(),
        db_path=database,
    ).package.package_id
    sidecars = [Path(f"{database}{suffix}") for suffix in ("-wal", "-shm")]
    snapshots = {}
    for sidecar, payload in zip(sidecars, (b"live-wal", b"live-shm"), strict=True):
        sidecar.write_bytes(payload)
        snapshots[sidecar] = payload

    for reader in (
        lambda: research_migration.status(db_path=database),
        lambda: get_research_package(package_id, db_path=database),
    ):
        with pytest.raises(RuntimeError, match="checkpointed database"):
            reader()
        assert {path: path.read_bytes() for path in sidecars} == snapshots


def test_phase4_research_schema_migration_status_backup_and_rollback(tmp_path: Path) -> None:
    from shared import research_migration
    from shared.migration_runner import MigrationOperator

    missing = tmp_path / "missing.sqlite"
    assert research_migration.status(db_path=missing)["pending"] == [
        "004_phase4_research_package_v1"
    ]
    assert not missing.exists()

    database = tmp_path / "legacy.sqlite"
    backups = tmp_path / "backups"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("CREATE TABLE sentinel(id TEXT PRIMARY KEY)")
        connection.execute("INSERT INTO sentinel VALUES ('preserve')")
        connection.commit()

    operator = MigrationOperator(db_path=database, backup_dir=backups)
    result = operator.apply("research.sqlite")

    assert result["provenance"]["applied_migrations"] == ["phase4_research_package_v1"]
    assert Path(result["provenance"]["backup_path"]).is_file()
    with closing(sqlite3.connect(database)) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert "research_packages_v1" in tables
        assert (
            connection.execute("SELECT name FROM schema_migrations WHERE version=4").fetchone()[0]
            == "phase4_research_package_v1"
        )
        assert connection.execute("SELECT id FROM sentinel").fetchone()[0] == "preserve"

    assert operator.rollback("research.sqlite")["state"] == "rolled_back"

    with closing(sqlite3.connect(database)) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert "sentinel" in tables
        assert "research_packages_v1" not in tables
        assert connection.execute("SELECT id FROM sentinel").fetchone()[0] == "preserve"


def test_phase4_direct_research_schema_migration_is_rejected(tmp_path: Path) -> None:
    from shared import research_migration

    database = tmp_path / "direct.sqlite"
    with closing(sqlite3.connect(database)):
        pass
    with pytest.raises(RuntimeError, match="must be driven by MigrationOperator"):
        research_migration.migrate(
            db_path=database,
            backup_dir=tmp_path / "backups",
            backup_when_pending=True,
        )


def test_phase4_research_schema_migration_rejects_version_collision(
    tmp_path: Path,
) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "collision.sqlite"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            """
            CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        connection.execute(
            "INSERT INTO schema_migrations(version, name) VALUES (4, 'other_schema')"
        )
        connection.commit()

    with pytest.raises(RuntimeError, match="research migration version/name collision"):
        MigrationOperator(
            db_path=database,
            backup_dir=tmp_path / "backups",
        ).apply("research.sqlite")

    assert not (tmp_path / "backups").exists()


def test_phase4_operator_rejects_unrecorded_extra_owned_trigger(tmp_path: Path) -> None:
    from shared import migration, research_migration
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "extra-trigger.sqlite"
    with closing(sqlite3.connect(database)) as connection:
        connection.executescript(research_migration.RESEARCH_SCHEMA_SQL)
        connection.execute(
            "CREATE TRIGGER unexpected_research_write AFTER INSERT ON research_sources_v1 "
            "BEGIN UPDATE research_sources_v1 SET title='changed' WHERE id=NEW.id; END"
        )
        connection.commit()

    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    with pytest.raises(RuntimeError, match="unexpected_research_write"):
        operator.apply("research.sqlite")
    with closing(sqlite3.connect(database)) as connection:
        ledger_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        ).fetchone()
        recorded = (
            connection.execute(
                "SELECT 1 FROM schema_migrations WHERE version=? OR name=?",
                (
                    migration.RESEARCH_SCHEMA_MIGRATION_VERSION,
                    migration.RESEARCH_SCHEMA_MIGRATION_NAME,
                ),
            ).fetchone()
            if ledger_exists is not None
            else None
        )
    assert recorded is None


def test_phase4_rollback_rejects_same_owner_old_backup_redirection(tmp_path: Path) -> None:
    import hashlib

    from shared.migration_runner import MigrationOperator

    database = tmp_path / "same-owner.sqlite"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("CREATE TABLE marker(value TEXT NOT NULL)")
        connection.execute("INSERT INTO marker(value) VALUES ('state-a')")
        connection.commit()
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    first = operator.apply("research.sqlite")
    old_backup = Path(first["provenance"]["backup_path"])
    operator.rollback("research.sqlite")
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("UPDATE marker SET value='state-b'")
        connection.commit()
    operator.apply("research.sqlite")

    old_hash = hashlib.sha256(old_backup.read_bytes()).hexdigest()
    with closing(sqlite3.connect(database)) as connection:
        row = connection.execute(
            "SELECT run_id, provenance_json FROM migration_operator_runs "
            "WHERE owner='research.sqlite' AND state='applied' "
            "ORDER BY recorded_at DESC, run_id DESC LIMIT 1"
        ).fetchone()
        provenance = json.loads(row[1])
        provenance["backup_path"] = str(old_backup)
        provenance["backup_sha256"] = old_hash
        connection.execute(
            "UPDATE migration_operator_runs SET provenance_json=? WHERE run_id=?",
            (json.dumps(provenance, sort_keys=True), row[0]),
        )
        connection.commit()

    with pytest.raises(RuntimeError, match="backup provenance manifest is invalid"):
        operator.rollback("research.sqlite")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT value FROM marker").fetchone()[0] == "state-b"


def test_phase4_operator_rejects_partial_unrecorded_research_schema(tmp_path: Path) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "partial.sqlite"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            "CREATE TABLE research_sources_v1("
            "id TEXT PRIMARY KEY, schema_version TEXT, title TEXT, content TEXT, "
            "source_locator TEXT, tags_json TEXT)"
        )
        connection.commit()
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")

    with pytest.raises(RuntimeError, match="unrecorded research migration schema mismatch"):
        operator.apply("research.sqlite")
    with closing(sqlite3.connect(database)) as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE name='research_packages_v1'"
            ).fetchone()[0]
            == 0
        )


def test_phase4_operator_status_detects_live_research_schema_drift(tmp_path: Path) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "drift.sqlite"
    _prepare_research_schema(database)
    operator = MigrationOperator(db_path=database, backup_dir=database.parent / "migration-backups")
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("DROP TABLE research_claims_v1")
        connection.commit()

    state = next(item for item in operator.status() if item["owner"] == "research.sqlite")
    assert state["state"] == "failed"
    assert state["provenance"]["reason"] == "live_schema_drift"


def test_phase4_research_rollback_rejects_taskpack_backup_manifest(tmp_path: Path) -> None:
    from shared import migration
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "owner-bound.sqlite"
    _prepare_research_schema(database)
    operator = MigrationOperator(db_path=database, backup_dir=database.parent / "migration-backups")
    wrong_backup = migration._create_backup(
        database,
        tmp_path / "wrong-backups",
        migration.TASKPACK_MIGRATION_NAME,
    )
    manifest = json.loads(migration._backup_manifest_path(wrong_backup).read_text(encoding="utf-8"))
    with closing(sqlite3.connect(database)) as connection:
        row = connection.execute(
            "SELECT run_id, provenance_json FROM migration_operator_runs "
            "WHERE owner='research.sqlite' AND state='applied'"
        ).fetchone()
        provenance = json.loads(row[1])
        provenance["backup_path"] = str(wrong_backup)
        provenance["backup_sha256"] = manifest["backup_sha256"]
        connection.execute(
            "UPDATE migration_operator_runs SET provenance_json=? WHERE run_id=?",
            (json.dumps(provenance, sort_keys=True), row[0]),
        )
        connection.commit()

    with pytest.raises(RuntimeError, match="backup provenance manifest is invalid"):
        operator.rollback("research.sqlite")


def test_phase4_legacy_external_collection_paths_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from fastapi.testclient import TestClient

    from app.cli import cmd_pipeline
    from app.main import app as core_app
    from inspiration_research.api import app
    from knowledge_base.api import app as knowledge_app
    from shared.bridge import bridge_trending_to_kb
    from shared.bulk_ops import bulk_import, cron_discover
    from shared.feed_collector import collect_and_ingest
    from shared.pipeline import run_pipeline

    client = TestClient(app)
    assert client.get("/trending").status_code == 409
    assert client.post("/daily-brief/auto").status_code == 409
    assert (
        client.post(
            "/research-note",
            json={
                "title": "candidate bypass",
                "content": "external content",
                "source": "https://github.com/DTALEX66/Cognitive-OS",
            },
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/engineering-contract",
            json={
                "intake_id": "intake_candidate",
                "goal": "promote candidate",
                "deliverables": ["artifact"],
            },
        ).status_code
        == 409
    )
    knowledge_client = TestClient(knowledge_app)
    monkeypatch.delenv("COGNITIVE_APPROVED_SOURCE_ROOTS", raising=False)
    for blocked_source in (
        "research_package_candidate",
        "intake_candidate",
        "source_candidate",
        "claim_candidate",
        "evidence_candidate",
        "finding_candidate",
        "https://github.com/DTALEX66/Cognitive-OS",
    ):
        assert (
            knowledge_client.post(
                "/context-pack",
                json={"goal": "promote candidate", "sources": [blocked_source]},
            ).status_code
            == 409
        )
    assert (
        knowledge_client.post(
            "/cards",
            json={
                "title": "candidate card",
                "content": "candidate content",
                "source_ids": ["source_candidate"],
            },
        ).status_code
        == 409
    )
    assert (
        knowledge_client.post(
            "/documents",
            json={
                "title": "candidate document",
                "content": "candidate content",
                "source": "research_package_candidate",
            },
        ).status_code
        == 409
    )
    core_client = TestClient(core_app)
    for endpoint, payload in (
        ("/ingest", {"content": "candidate", "source": "source_candidate"}),
        ("/run", {"content": "candidate", "source": "source_candidate"}),
        ("/ingest/file", {"path": "missing.md", "source": "source_candidate"}),
        ("/ingest/directory", {"path": "missing", "source": "source_candidate"}),
    ):
        assert core_client.post(endpoint, json=payload).status_code == 409
    assert knowledge_client.post("/ir/feeds").status_code == 409
    assert knowledge_client.post("/cron/discover").status_code == 409
    assert (
        knowledge_client.post(
            "/pipeline",
            json={"source": "file", "input": str(tmp_path / "missing.md")},
        ).status_code
        == 503
    )
    assert (
        knowledge_client.post(
            "/pipeline",
            json={"source": "url", "input": "https://example.com", "auto_ingest": True},
        ).status_code
        == 409
    )
    assert (
        knowledge_client.post(
            "/bulk/import",
            params={
                "items": json.dumps([{"source": "search", "input": "query", "auto_ingest": True}])
            },
        ).status_code
        == 409
    )

    from inspiration_research.project_radar.collectors.github_trending import (
        collect_by_category,
        collect_trending,
        collect_trending_fallback,
    )
    from scripts.run_daily import run_daily

    for legacy_call in (
        run_daily,
        collect_trending,
        collect_by_category,
        collect_trending_fallback,
        lambda: collect_and_ingest([]),
        cron_discover,
    ):
        with pytest.raises(
            RuntimeError, match="legacy .* (?:collection|ingestion|discovery) is disabled"
        ):
            legacy_call()

    for external_write in (
        lambda: run_pipeline("url", "https://example.com"),
        lambda: bulk_import([{"source": "search", "input": "query"}]),
        lambda: cmd_pipeline("youtube", "abcdefghijk"),
    ):
        with pytest.raises(RuntimeError, match="external pipeline auto-ingest is disabled"):
            external_write()
    with pytest.raises(RuntimeError, match="legacy trending bridge is disabled"):
        bridge_trending_to_kb([{"repo": "owner/repo", "qualifies": True}])

    local_file = tmp_path / "approved" / "local-note.md"
    local_file.parent.mkdir()
    local_file.write_text("# Approved local note\n\nlocal pipeline content", encoding="utf-8")
    monkeypatch.delenv("COGNITIVE_APPROVED_SOURCE_ROOTS", raising=False)
    with pytest.raises(RuntimeError, match="requires COGNITIVE_APPROVED_SOURCE_ROOTS"):
        run_pipeline("file", str(local_file))
    monkeypatch.setenv("COGNITIVE_APPROVED_SOURCE_ROOTS", str(local_file.parent))
    local_result = run_pipeline("file", str(local_file), actions=["extract", "index"])
    assert local_result["kb_id"].startswith("doc_")
    assert local_result["stages"]["extract"]["engine"] == "approved-local-file"


def test_phase4_real_graph_references_are_exhaustively_blocked_from_effectful_ingress(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from fastapi.testclient import TestClient

    from app.facades.research import research_github_repository
    from app.main import app as core_app
    from app.memory import database as memory_database
    from app.memory import episodic as episodic_memory
    from app.memory.episodic import save_episode
    from app.memory.graph_db import GraphDB
    from app.schemas import CoreObject
    from inspiration_research.api import app as research_app
    from inspiration_research.project_radar.outputs.generator import (
        export_screening_csv,
        screen_project,
    )
    from knowledge_base.api import app as knowledge_app
    from knowledge_base.machine_knowledge import create_unit
    from shared import storage
    from shared.canvas import add_card as add_canvas_card
    from shared.canvas import add_connection as add_canvas_connection
    from shared.config import config
    from shared.evidence_index import index_evidence
    from shared.processing_manifest import ProcessingManifest

    monkeypatch.setitem(config._data["rate_limit"], "sensitive_write", 10_000)
    research_database = tmp_path / "research.sqlite"
    knowledge_database = tmp_path / "knowledge.sqlite"
    memory_path = tmp_path / "memory.sqlite"
    _prepare_research_schema(research_database)
    monkeypatch.setattr(storage, "DB_PATH", knowledge_database)
    monkeypatch.setattr(memory_database, "DB_PATH", memory_path)
    storage.init()
    memory_database.init_db()

    graph = research_github_repository(
        "https://github.com/octo/loop-os",
        fetcher=_transport(),
        db_path=research_database,
    )
    payload = graph.model_dump(mode="json")
    references: set[str] = set()

    def collect(value: object, field: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                collect(child, key)
            return
        if isinstance(value, list):
            for child in value:
                collect(child, field)
            return
        if isinstance(value, str):
            if (field.endswith("_id") or field.endswith("_ids")) and value:
                references.add(value)
            if value.lower().startswith(("http://", "https://")):
                references.add(value)

    collect(payload)
    required_prefixes = {
        "research_package_",
        "intake_",
        "source_",
        "claim_",
        "evidence_",
        "finding_",
    }
    assert all(
        any(value.startswith(prefix) for value in references) for prefix in required_prefixes
    )
    assert any(value.startswith("https://github.com/") for value in references)
    assert any(value.startswith("https://api.github.com/") for value in references)

    def snapshot(database: Path) -> dict[str, int]:
        with closing(sqlite3.connect(database)) as connection:
            tables = connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                "AND sql IS NOT NULL AND upper(sql) NOT LIKE '%VIRTUAL TABLE%' "
                "ORDER BY name"
            ).fetchall()
            return {
                str(row[0]): int(
                    connection.execute(f'SELECT COUNT(*) FROM "{row[0]}"').fetchone()[0]
                )
                for row in tables
            }

    databases = (research_database, knowledge_database, memory_path)
    before = {str(path): snapshot(path) for path in databases}
    knowledge_client = TestClient(knowledge_app)
    core_client = TestClient(core_app)
    research_client = TestClient(research_app)
    blocked_memory_path = tmp_path / "must-not-create-core.sqlite"
    boundary_attempts = {"get_conn": 0, "ensure_init": 0}

    def reject_core_connection() -> None:
        boundary_attempts["get_conn"] += 1
        raise AssertionError("candidate boundary reached Core _get_conn")

    def reject_episode_initialization() -> None:
        boundary_attempts["ensure_init"] += 1
        raise AssertionError("candidate boundary reached Episodic _ensure_init")

    monkeypatch.setattr(memory_database, "DB_PATH", blocked_memory_path)
    monkeypatch.setattr(memory_database, "_get_conn", reject_core_connection)
    monkeypatch.setattr(episodic_memory, "_ensure_init", reject_episode_initialization)
    sentinel_file = tmp_path / "must-not-be-read.md"
    sentinel_directory = tmp_path / "must-not-be-read"
    screening_output = tmp_path / "must-not-be-written" / "screening.csv"
    manifest_path = tmp_path / "must-not-be-written-manifest" / "manifest.jsonl"
    manifest = ProcessingManifest(manifest_path)
    graph_database = GraphDB("phase4-boundary")

    for reference in sorted(references):
        responses = [
            knowledge_client.post(
                "/documents",
                json={"title": "blocked", "content": "blocked", "source": reference},
            ),
            knowledge_client.post(
                "/cards",
                json={"title": "blocked", "content": "blocked", "source_ids": [reference]},
            ),
            knowledge_client.post(
                "/context-pack",
                json={"goal": "blocked", "sources": [reference]},
            ),
            knowledge_client.post(
                "/evidence",
                params={"doc_id": "doc_blocked", "source_path": reference},
            ),
            knowledge_client.post(
                "/canvas/canvas-local/card",
                params={"object_id": reference},
            ),
            knowledge_client.post(
                "/canvas/canvas-local/connect",
                params={"source_node_id": reference, "target_node_id": "node-local"},
            ),
            knowledge_client.post(
                "/canvas/canvas-local/connect",
                params={"source_node_id": "node-local", "target_node_id": reference},
            ),
            core_client.post("/ingest", json={"content": "blocked", "source": reference}),
            core_client.post("/run", json={"content": "blocked", "source": reference}),
            core_client.post(
                "/ingest/file",
                json={"path": str(sentinel_file), "source": reference},
            ),
            core_client.post(
                "/ingest/directory",
                json={"path": str(sentinel_directory), "source": reference},
            ),
            research_client.post(
                "/research-note",
                json={"title": "blocked", "content": "blocked", "source": reference},
            ),
            research_client.post(
                "/engineering-contract",
                json={"intake_id": reference, "goal": "blocked", "deliverables": ["blocked"]},
            ),
            research_client.post(
                "/screen-projects/batch",
                json=[{"repo": reference, "category": "blocked"}],
            ),
        ]
        if "/" not in reference:
            responses.extend(
                [
                    knowledge_client.post(
                        f"/canvas/{reference}/card",
                        params={"object_id": "object-local"},
                    ),
                    knowledge_client.post(
                        f"/canvas/{reference}/connect",
                        params={"source_node_id": "node-local-a", "target_node_id": "node-local-b"},
                    ),
                ]
            )
        else:
            encoded_reference = quote(reference, safe="")
            assert (
                knowledge_client.post(
                    f"/canvas/{encoded_reference}/card",
                    params={"object_id": "object-local"},
                ).status_code
                == 404
            )
            assert (
                knowledge_client.post(
                    f"/canvas/{encoded_reference}/connect",
                    params={"source_node_id": "node-local-a", "target_node_id": "node-local-b"},
                ).status_code
                == 404
            )
        assert [response.status_code for response in responses] == [409] * len(responses)
        with pytest.raises(ValueError, match="server-owned Phase 5 review provenance"):
            index_evidence("doc_blocked", source_path=reference)
        with pytest.raises(ValueError, match="server-owned Phase 5 review provenance"):
            create_unit("blocked", source_id=reference)
        with pytest.raises(ValueError, match="server-owned Phase 5 review provenance"):
            save_episode("blocked", source=reference)
        core_payload = CoreObject(content="blocked", source=reference).model_dump()
        with pytest.raises(ValueError, match="server-owned Phase 5 review provenance"):
            memory_database.save_core_object(core_payload)
        with pytest.raises(ValueError, match="server-owned Phase 5 review provenance"):
            memory_database.save_memory_record(core_payload)
        with pytest.raises(ValueError, match="server-owned Phase 5 review provenance"):
            manifest.record(reference, status="needs_review", handler="blocked")
        with pytest.raises(ValueError, match="server-owned Phase 5 review provenance"):
            add_canvas_card("canvas-local", reference)
        with pytest.raises(ValueError, match="server-owned Phase 5 review provenance"):
            add_canvas_card(reference, "object-local")
        with pytest.raises(ValueError, match="server-owned Phase 5 review provenance"):
            add_canvas_connection("canvas-local", reference, "node-local")
        with pytest.raises(ValueError, match="server-owned Phase 5 review provenance"):
            add_canvas_connection("canvas-local", "node-local", reference)
        with pytest.raises(ValueError, match="server-owned Phase 5 review provenance"):
            add_canvas_connection(reference, "node-local-a", "node-local-b")
        with pytest.raises(ValueError, match="server-owned Phase 5 review provenance"):
            graph_database.add_entity(reference)
        with pytest.raises(ValueError, match="server-owned Phase 5 review provenance"):
            graph_database.add_relation(reference, "local-target", "blocked")
        with pytest.raises(ValueError, match="server-owned Phase 5 review provenance"):
            graph_database.add_relation("local-source", reference, "blocked")
        screening_entry = screen_project(repo=reference, category="blocked")
        with pytest.raises(ValueError, match="server-owned Phase 5 review provenance"):
            export_screening_csv([screening_entry], output_path=str(screening_output))

    after = {str(path): snapshot(path) for path in databases}
    assert after == before
    assert boundary_attempts == {"get_conn": 0, "ensure_init": 0}
    assert not blocked_memory_path.exists()
    assert not sentinel_file.exists()
    assert not sentinel_directory.exists()
    assert not screening_output.exists()
    assert not screening_output.parent.exists()
    assert not manifest_path.exists()
    assert not manifest_path.parent.exists()


def test_phase4_api_returns_explicit_client_and_migration_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from fastapi.testclient import TestClient

    from inspiration_research.api import app
    from shared import storage

    client = TestClient(app)
    invalid = client.post(
        "/research/github-repository",
        json={"repository_url": "http://github.com/octo/loop-os"},
    )
    assert invalid.status_code == 422

    def rejected_response(
        url: str,
        *,
        policy: SafeHTTPPolicy,
        headers: Mapping[str, str],
    ) -> SafeHTTPResponse:
        del policy, headers
        return SafeHTTPResponse(
            url=url,
            status=500,
            headers={"content-type": "application/json"},
            body=b"{}",
        )

    monkeypatch.setattr(app.state, "research_github_fetcher", rejected_response, raising=False)
    upstream_rejected = client.post(
        "/research/github-repository",
        json={"repository_url": "https://github.com/octo/loop-os"},
    )
    assert upstream_rejected.status_code == 502

    missing = tmp_path / "missing.sqlite"
    monkeypatch.setattr(storage, "DB_PATH", missing)
    pending = client.get("/research/packages/missing")
    assert pending.status_code == 503
    assert not missing.exists()

    database = tmp_path / "ready.sqlite"
    _prepare_research_schema(database)
    monkeypatch.setattr(storage, "DB_PATH", database)
    absent = client.get("/research/packages/missing")
    assert absent.status_code == 404


def test_phase4_wheel_configuration_excludes_nested_test_packages() -> None:
    try:
        import tomllib
    except ModuleNotFoundError:  # Python 3.10
        import tomli as tomllib

    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    excluded = set(config["tool"]["setuptools"]["packages"]["find"]["exclude"])
    assert {"tests*", "knowledge_base.tests*", "*.tests", "*.tests.*"} <= excluded


def test_phase4_github_url_to_persisted_candidate_package_api_tracer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from fastapi.testclient import TestClient

    from inspiration_research.api import app
    from shared import storage

    database = tmp_path / "phase4.sqlite"
    _prepare_research_schema(database)
    monkeypatch.setattr(storage, "DB_PATH", database)
    transport = _transport()
    monkeypatch.setattr(app.state, "research_github_fetcher", transport, raising=False)

    client = TestClient(app)
    created = client.post(
        "/research/github-repository",
        json={"repository_url": "https://github.com/octo/loop-os"},
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["package"]["status"] == "candidate"
    assert payload["package"]["requires_human_review"] is True
    assert payload["package"]["independent_source_count"] == 1

    loaded = client.get(f"/research/packages/{payload['package']['package_id']}")
    assert loaded.status_code == 200
    assert loaded.json()["package"]["package_id"] == payload["package"]["package_id"]

    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM research_packages_v1").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM research_evidence_v1").fetchone()[0] >= 2
        link = connection.execute(
            "SELECT intake_id FROM research_package_intake_links_v1 WHERE package_id=?",
            (payload["package"]["package_id"],),
        ).fetchone()
    assert link is not None
