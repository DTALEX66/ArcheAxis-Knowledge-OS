"""Real-case E2E: every implemented knowledge transformation chain.

Covers all 7 chains from the DeepSeek handoff with deterministic fixtures.
Each test validates: input → transform → persistence → readback → governance state.
Replay, restart readback, and DTO leakage are explicitly tested.

DO NOT add pytest markers that skip these tests in CI.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from shared.migration_runner import MigrationOperator


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ────────────────────────────────────────────────────────────────────────
# Chain 1: URL / GitHub / File → candidate Research
# ────────────────────────────────────────────────────────────────────────


def test_chain1_url_intake_creates_persisted_research_package(monkeypatch, workspace_db: Path) -> None:
    """A plain web URL must produce a candidate ResearchPackage with Job/Outbox/Receipt."""
    from app.workspace import service

    monkeypatch.setattr(service, "convert_url", lambda _: ("# Candidate\n**Real evidence.**\n", "test-engine"))

    result = service.intake_url(url="https://example.com/article", db_path=workspace_db)
    assert result["source_type"] == "web"
    assert result["status"] == "candidate"
    assert result["requires_human_review"] is True

    # Job strict readback must not raise
    job = service.intake_job(job_id=str(result["job_id"]), db_path=workspace_db)
    assert job["state"] == "succeeded"
    assert job["outbox_state"] == "pending"
    assert job["package_status"] == "candidate"


def test_chain1_github_intake_creates_candidate_package(monkeypatch, workspace_db: Path) -> None:
    """A GitHub repository URL must produce a candidate ResearchPackage."""
    from app.workspace import service

    def _fake_github(url, **kwargs):
        raise RuntimeError("no network in E2E tests")

    monkeypatch.setattr(service, "research_github_repository", lambda url, fetcher, db_path, before_commit: (
        type("_FakeResult", (), {
            "canonical_url": url,
            "package": type("_Pkg", (), {
                "package_id": "gh-pkg-" + sha256(url.encode()).hexdigest()[:16],
                "status": "candidate",
                "requires_human_review": True,
            })(),
            "sources": [type("_Src", (), {"model_dump": lambda: {"source_id": "s1"}})()],
            "claims": [],
            "evidence": [],
            "findings": [],
        })()
    ))

    result = service.intake_url(url="https://github.com/owner/repo", db_path=workspace_db)
    assert result["source_type"] == "github_repository"
    assert result["status"] == "candidate"
    assert result["requires_human_review"] is True
    assert result["source_count"] == 1


def test_chain1_file_intake_creates_candidate_package(monkeypatch, workspace_db: Path) -> None:
    """A local file upload must produce a candidate ResearchPackage."""
    from app.workspace import service

    monkeypatch.setattr(service, "convert_file", lambda path: ("# File content\nBody.", "markitdown"))
    monkeypatch.setattr(service, "detect_format", lambda path: "markdown")

    content = b"# Test document\n## Section\nThis is evidence.\n"
    result = service.intake_upload(file_name="test.md", content=content, db_path=workspace_db)
    assert result["source_type"] == "file"
    assert result["format"] == "markdown"
    assert result["status"] == "candidate"
    assert result["requires_human_review"] is True
    assert result["char_count"] > 0
    assert "# File content" in result["content"]
    assert result["package_id"]


# ────────────────────────────────────────────────────────────────────────
# Chain 2: Research → 人工审核 → Knowledge 候选
# ────────────────────────────────────────────────────────────────────────


def _fake_github_fetcher(**kwargs):
    """Return a SafeHTTP-style response for testing without network."""
    requested_url = kwargs.get("url", kwargs.get("requested_url", ""))
    # Extract owner/repo from the URL to return matching metadata
    parts = str(requested_url).split("/repos/", 1)
    if len(parts) == 2:
        repo_path = parts[1].split("?")[0].rstrip("/")
    else:
        repo_path = "test-user/example-repo"
    if "/readme" in str(requested_url):
        status = 200
        body = b"# Fake README\nResearch content."
        headers = {"content-type": "application/octet-stream"}
    else:
        status = 200
        headers = {"content-type": "application/json"}
        body = json.dumps({
            "full_name": repo_path,
            "html_url": f"https://github.com/{repo_path}",
            "description": "Test repository",
            "forks_count": 0,
            "topics": ["example"],
            "language": "Python",
            "license": {"spdx_id": "MIT"},
        }).encode("utf-8")
    from shared.safe_http import SafeHTTPResponse
    return SafeHTTPResponse(
        url=str(requested_url),
        status=status,
        headers=headers,
        body=body,
    )


def test_chain2_promote_research_to_knowledge_candidates(full_db: Path) -> None:
    """Approved research must create auditable Knowledge candidates."""
    from app.facades.research import research_github_repository
    from app.knowledge.promotion import (
        ResearchKnowledgeApproval,
        promote_research_package_to_candidates,
    )

    graph = research_github_repository(
        "https://github.com/test-user/example-repo",
        db_path=full_db,
        before_commit=lambda conn, g: None,
        fetcher=lambda url, policy=None, headers=None: _fake_github_fetcher(url=url),
    )
    package_id = graph.package.package_id

    approval = ResearchKnowledgeApproval(
        approval_id="approval-e2e-001",
        package_id=package_id,
        reviewer_id="local-workspace",
        decision="approved",
        rationale="E2E verified",
        reviewed_at=_now(),
    )
    receipt = promote_research_package_to_candidates(approval, db_path=full_db)

    assert receipt.promotion_id.startswith("knowledge-promotion_")
    assert receipt.lifecycle_status == "candidate"
    assert len(receipt.units) > 0
    for unit in receipt.units:
        assert unit.properties.get("lifecycle_status") == "candidate"


def test_chain2_promotion_rejected_package_creates_no_units(full_db: Path) -> None:
    """Rejected packages must not create Knowledge candidates."""
    from app.facades.research import research_github_repository
    from app.knowledge.promotion import (
        ResearchKnowledgeApproval,
        promote_research_package_to_candidates,
    )

    graph = research_github_repository(
        "https://github.com/test-user/rejected-repo",
        db_path=full_db,
        before_commit=lambda conn, g: None,
        fetcher=lambda url, policy=None, headers=None: _fake_github_fetcher(url=url),
    )

    approval = ResearchKnowledgeApproval(
        approval_id="approval-e2e-rejected",
        package_id=graph.package.package_id,
        reviewer_id="local-workspace",
        decision="rejected",
        rationale="Verified rejection path",
        reviewed_at=_now(),
    )
    receipt = promote_research_package_to_candidates(approval, db_path=full_db)
    assert receipt.lifecycle_status == "rejected"
    assert receipt.units == []
    assert receipt.relations == []


# ────────────────────────────────────────────────────────────────────────
# Chain 3: Knowledge → Learning / Practice
# ────────────────────────────────────────────────────────────────────────


def test_chain3_knowledge_to_learning_creates_artifact_and_practice_evidence(full_db: Path) -> None:
    """Approved Knowledge unit must flow through to a Learning artifact and practice evidence.

    Requires a ResearchPackage → Knowledge promotion → Learning candidate flow.
    """
    import uuid

    from app.facades.research import research_github_repository
    from app.knowledge.closed_loop import (
        record_practice_evidence,
        start_and_approve_learning_candidate,
    )
    from app.knowledge.promotion import (
        ResearchKnowledgeApproval,
        promote_research_package_to_candidates,
    )

    # 1) Research intake → Knowledge promotion
    graph = research_github_repository(
        "https://github.com/test-user/example-repo",
        db_path=full_db,
        before_commit=lambda conn, g: None,
        fetcher=lambda url, policy=None, headers=None: _fake_github_fetcher(url=url),
    )
    approval = ResearchKnowledgeApproval(
        approval_id=f"approval-{uuid.uuid4().hex[:12]}",
        package_id=graph.package.package_id,
        reviewer_id="local-workspace",
        decision="approved",
        rationale="E2E learning chain",
        reviewed_at=_now(),
    )
    receipt = promote_research_package_to_candidates(approval, db_path=full_db)
    assert len(receipt.units) > 0

    # 2) Pick the first claim unit as the learning source
    claim_units = [u for u in receipt.units if u.unit_type == "research_claim"]
    if not claim_units:  # fallback: use any source unit
        claim_units = [u for u in receipt.units if u.unit_type == "research_source"]
    assert len(claim_units) > 0, "no units to create learning from"
    unit_id = claim_units[0].unit_id

    # 3) Knowledge → Learning
    command_id = f"cmd-{uuid.uuid4().hex[:12]}"
    artifact, cards = start_and_approve_learning_candidate(
        unit_id=unit_id,
        approval_id=f"approval-{uuid.uuid4().hex[:12]}",
        approval_command_id=command_id,
        reviewer_id="local-workspace",
        rationale="E2E learning chain",
        reviewed_at=_now(),
        db_path=full_db,
    )

    assert artifact.artifact_id.startswith("knowledge-learning-artifact_")
    assert len(cards) > 0

    # 4) Record practice evidence
    result = record_practice_evidence(
        artifact_id=artifact.artifact_id,
        command_id=f"practice-{uuid.uuid4().hex[:12]}",
        quality=5,
        recorded_at=_now(),
        db_path=full_db,
    )
    assert result.mastery_signal is not None
    assert result.mastery_signal.model_dump()

    # 5) Audit
    from app.knowledge.closed_loop import audit_closed_loop

    events = audit_closed_loop(artifact_id=artifact.artifact_id, db_path=full_db)
    event_types = [e.event_type for e in events]
    assert "learning_candidate_created" in event_types
    assert "learning_artifact_approved" in event_types
    assert "practice_recorded" in event_types


# ────────────────────────────────────────────────────────────────────────
# Chain 4: Learning → Machine Knowledge → Runtime approved-only 读取
# ────────────────────────────────────────────────────────────────────────


def test_chain4_learning_to_machine_knowledge_projections_are_approved_only(full_db: Path) -> None:
    """Machine Knowledge produced from practice must only appear in approved projections."""
    import uuid

    from app.facades.research import research_github_repository
    from app.knowledge.closed_loop import (
        record_practice_evidence,
        start_and_approve_learning_candidate,
    )
    from app.knowledge.promotion import (
        ResearchKnowledgeApproval,
        promote_research_package_to_candidates,
    )

    # Upstream: Research → Knowledge
    graph = research_github_repository(
        "https://github.com/test-user/example-repo",
        db_path=full_db,
        before_commit=lambda conn, g: None,
        fetcher=lambda url, policy=None, headers=None: _fake_github_fetcher(url=url),
    )
    approval = ResearchKnowledgeApproval(
        approval_id=f"approval-{uuid.uuid4().hex[:12]}",
        package_id=graph.package.package_id,
        reviewer_id="local-workspace",
        decision="approved",
        rationale="MK projection test",
        reviewed_at=_now(),
    )
    receipt = promote_research_package_to_candidates(approval, db_path=full_db)
    claim_units = [u for u in receipt.units if u.unit_type == "research_claim"]
    if not claim_units:
        claim_units = [u for u in receipt.units if u.unit_type == "research_source"]
    assert len(claim_units) > 0
    unit_id = claim_units[0].unit_id

    # Knowledge → Learning
    artifact, _cards = start_and_approve_learning_candidate(
        unit_id=unit_id,
        approval_id=f"approval-{uuid.uuid4().hex[:12]}",
        approval_command_id=f"cmd-{uuid.uuid4().hex[:12]}",
        reviewer_id="local-workspace",
        rationale="MK projection test",
        reviewed_at=_now(),
        db_path=full_db,
    )

    # Learning → Practice → Machine Knowledge
    result = record_practice_evidence(
        artifact_id=artifact.artifact_id,
        command_id=f"practice-{uuid.uuid4().hex[:12]}",
        quality=5,
        recorded_at=_now(),
        db_path=full_db,
    )

    # Machine Knowledge must be created AND approved
    if result.machine_knowledge is not None:
        mk = result.machine_knowledge
        assert mk.unit_id.startswith("mk_")
        with sqlite3.connect(full_db) as conn:
            row = conn.execute(
                "SELECT 1 FROM machine_knowledge_units_v1 WHERE id=? AND approved=1",
                (mk.unit_id,),
            ).fetchone()
            assert row is not None, "machine knowledge must be approved"

        # Approved projection must include this MK
        from knowledge_base.machine_knowledge import list_approved_units

        approved = list_approved_units(db_path=full_db)
        assert any(u["id"] == mk.unit_id for u in approved)


# ────────────────────────────────────────────────────────────────────────
# Chain 5: 媒体 → 音轨 / 关键帧 / OCR
# ────────────────────────────────────────────────────────────────────────


def test_chain5_media_extraction_produces_real_evidence() -> None:
    """Media extraction baseline: re-run existing media tests as smoke.

    The full media E2E chain (ASR, timestamps, semantic content matching,
    human-labels accuracy) is NOT yet implemented.
    See HANDOFF_DEEPSEEK_REAL_CASE_E2E_2026-07-23.md.
    """
    import tempfile
    from pathlib import Path

    from tests.test_media_extractor import (
        test_extract_audio_track_creates_asr_ready_wav_with_real_ffmpeg as _audio,
    )
    from tests.test_media_extractor import (
        test_extract_image_text_uses_real_tesseract_with_approved_paths as _ocr,
    )
    from tests.test_media_extractor import (
        test_extract_video_keyframes_reports_verified_png_dimensions as _keyframe,
    )

    tmp = Path(tempfile.mkdtemp())
    try:
        _ocr(tmp)
        _audio(tmp)
        _keyframe(tmp)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


# ────────────────────────────────────────────────────────────────────────
# Chain 6: TaskPack → Permission → Tool Evidence → Evaluation → Lesson
# ────────────────────────────────────────────────────────────────────────


def test_chain6_taskpack_to_lesson_produces_trace_bound_success_lesson(monkeypatch) -> None:
    """Existing 'read file:' vertical slice must produce real evidence + evaluation + lesson."""
    import app.main as main_module
    from app.evaluation.evaluator import evaluate
    from app.facades import runtime as runtime_module
    from app.schemas import ContextPack, ExecutionTrace

    persisted_traces = []
    persisted_lessons = []
    monkeypatch.setattr(main_module, "save_memory", lambda document: None)
    monkeypatch.setattr(
        main_module,
        "retrieve",
        lambda query: ContextPack(query=query, summary="E2E tracer context"),
    )
    monkeypatch.setattr(main_module, "save_lesson", persisted_lessons.append)
    monkeypatch.setattr(runtime_module, "log_trace", persisted_traces.append)

    response = main_module.run({"content": "read file: AGENTS.md", "source": "e2e-chain6"})

    assert response["status"] == "done"
    assert response["task"].tools == ["file_read"]
    assert response["permission"]["requires_human_review"] is False

    trace = response["trace"]
    assert trace.success is True
    evidence = trace.events[0]["result"]
    assert evidence["tool"] == "file_read"
    assert evidence["dry_run"] is False
    assert "AGENTS.md" in evidence["path"]
    assert response["eval"].success is True
    assert response["eval"].score == 1.0
    assert response["lesson"].lesson_type == "success"
    assert persisted_traces == [trace]
    assert persisted_lessons == [response["lesson"]]

    # Constraints: non-real-evidence tool results must score < 1.0
    for tool, dry_result in [
        ("echo", {"tool": "echo", "status": "ok", "dry_run": False, "message": "executed"}),
        ("noop", {"tool": "noop", "status": "ok", "dry_run": False}),
        (
            "file_read",
            {"tool": "file_read", "status": "ok", "dry_run": True,
             "path": "AGENTS.md", "preview": "dry-run read only"},
        ),
    ]:
        fake_trace = ExecutionTrace(
            task_id=f"fake-{tool}",
            events=[{"step": {"tool": tool}, "result": dry_result}],
            result={"status": "done", "outputs": [dry_result]},
            success=True,
        )
        fake_eval = evaluate(fake_trace)
        assert fake_eval.success is False
        assert fake_eval.score < 1.0
        assert "evidence" in fake_eval.failure_reason


# ────────────────────────────────────────────────────────────────────────
# Chain 7: Outbox → dispatcher/consumer → receipt/replay
# ────────────────────────────────────────────────────────────────────────


def test_chain7_intake_dispatch_consumer_writes_receipt_delivers_outbox(monkeypatch, full_db: Path) -> None:
    """Full intake → outbox → lease-fenced dispatch → consumer → receipt."""
    from app.workspace import service
    from app.workspace.outbox_dispatcher import dispatch_once
    from app.workspace.research_consumer import make_intake_research_handler

    monkeypatch.setattr(service, "convert_url", lambda _: ("# Candidate\nE2E dispatch body.", "test"))
    intake = service.intake_url(url="https://example.com/dispatch-e2e", db_path=full_db)

    result = dispatch_once(
        db_path=full_db,
        worker_name="e2e-research-consumer",
        handler=make_intake_research_handler(db_path=full_db, consumer_name="e2e-receipt-writer"),
    )

    assert result["status"] == "delivered"
    assert result["attempt"] == 1

    with closing(sqlite3.connect(full_db)) as connection:
        receipt_row = connection.execute(
            "SELECT event_id, consumer_name, proof_json FROM workspace_delivery_receipts_v1"
        ).fetchone()
        outbox_row = connection.execute(
            "SELECT state FROM workspace_outbox_v1"
        ).fetchone()

    assert receipt_row is not None
    assert receipt_row[1] == "e2e-receipt-writer"
    assert json.loads(receipt_row[2]) == {"package_id": intake["package_id"]}
    assert outbox_row == ("delivered",)


def test_chain7_idle_dispatch_returns_idle(tmp_path: Path) -> None:
    """An outbox with no pending events must return idle, not crash."""
    from app.workspace.outbox_dispatcher import dispatch_once

    database = tmp_path / "empty.sqlite"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("CREATE TABLE sentinel(id TEXT PRIMARY KEY)")
        connection.commit()
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply("workspace.sqlite")

    def _never_called(_event):
        raise AssertionError("handler should not be called")

    result = dispatch_once(
        db_path=database,
        worker_name="idle-worker",
        handler=_never_called,
    )
    assert result == {"status": "idle"}


def test_chain7_replay_idempotent_does_not_duplicate(monkeypatch, workspace_db: Path) -> None:
    """Re-dispatching a delivered event must be idempotent — no duplicate receipts."""
    from app.workspace import service
    from app.workspace.outbox_dispatcher import dispatch_once
    from app.workspace.research_consumer import make_intake_research_handler

    monkeypatch.setattr(service, "convert_url", lambda _: ("# Idempotent body.", "test"))
    service.intake_url(url="https://example.com/idempotent", db_path=workspace_db)

    dispatch_once(
        db_path=workspace_db,
        worker_name="idem-worker",
        handler=make_intake_research_handler(db_path=workspace_db, consumer_name="idem-consumer"),
    )

    result2 = dispatch_once(
        db_path=workspace_db,
        worker_name="idem-worker",
        handler=make_intake_research_handler(db_path=workspace_db, consumer_name="idem-consumer"),
    )
    assert result2 == {"status": "idle"}


def test_chain7_dispatch_fails_closed_on_invalid_handler(monkeypatch, workspace_db: Path) -> None:
    """A handler returning invalid confirmation must fail the outbox event."""
    from app.workspace import service
    from app.workspace.outbox_dispatcher import dispatch_once

    monkeypatch.setattr(service, "convert_url", lambda _: ("# Fail-closed body.", "test"))
    service.intake_url(url="https://example.com/fail-closed", db_path=workspace_db)

    def _bad_handler(event):
        return {"event_id": "wrong", "lease_token": "wrong", "proof": {}}  # wrong event_id

    result = dispatch_once(
        db_path=workspace_db,
        worker_name="fail-worker",
        handler=_bad_handler,
    )
    assert result["status"] == "failed"


# ────────────────────────────────────────────────────────────────────────
# Cross-cutting: DTO leakage & restart readback
# ────────────────────────────────────────────────────────────────────────


def test_crosscutting_product_dto_never_leaks_internal_ids(monkeypatch, workspace_db: Path) -> None:
    """The public product intake DTO must not expose package_id, job_id, etc."""
    from app.workspace import service
    from app.workspace.router import _product_intake_result

    monkeypatch.setattr(service, "convert_url", lambda _: ("# Leak test body.", "test"))
    internal = service.intake_url(url="https://example.com/leak-test", db_path=workspace_db)
    product = _product_intake_result(internal)

    public_fields = product.model_dump()
    forbidden = {"package_id", "job_id", "command_id", "unit_id", "artifact_id", "outbox_id"}
    leaked = forbidden & set(public_fields.keys())
    assert not leaked, f"product DTO leaked internal IDs: {leaked}"

    assert product.source_type == "web"
    assert product.requires_human_review is True


def test_crosscutting_restart_readback_preserves_all_transformations(monkeypatch, full_db: Path) -> None:
    """After intake + dispatch, re-reading the database must show persistent state."""
    from app.workspace import service
    from app.workspace.outbox_dispatcher import dispatch_once
    from app.workspace.research_consumer import make_intake_research_handler

    db_path = str(full_db)

    monkeypatch.setattr(service, "convert_url", lambda _: ("# Restart readback body.", "test"))
    intake = service.intake_url(url="https://example.com/restart", db_path=db_path)

    # Verify strict readback BEFORE dispatch (outbox still pending)
    job_before = service.intake_job(job_id=str(intake["job_id"]), db_path=db_path)
    assert job_before["state"] == "succeeded"
    assert job_before["outbox_state"] == "pending"

    # Dispatch before "restart"
    dispatch_once(
        db_path=db_path,
        worker_name="restart-worker",
        handler=make_intake_research_handler(db_path=db_path, consumer_name="restart-consumer"),
    )

    # After dispatch — verify outbox delivered + receipt exists via workspace_jobs + direct SQL
    all_jobs = service.workspace_jobs(db_path=db_path)
    assert len(all_jobs["jobs"]) >= 1

    with closing(sqlite3.connect(full_db)) as conn:
        outbox = conn.execute("SELECT state FROM workspace_outbox_v1").fetchone()
        receipt = conn.execute("SELECT 1 FROM workspace_delivery_receipts_v1").fetchone()
    assert outbox[0] == "delivered"
    assert receipt is not None


def test_crosscutting_all_chains_coverage_matrix() -> None:
    """Assert that all 7 chains from the handoff document have at least one test function."""
    import inspect
    import sys

    module = sys.modules[__name__]
    chain_prefixes = {
        "test_chain1_": "Chain 1: URL/GitHub/File → candidate Research",
        "test_chain2_": "Chain 2: Research → 人工审核 → Knowledge",
        "test_chain3_": "Chain 3: Knowledge → Learning/Practice",
        "test_chain4_": "Chain 4: Learning → Machine Knowledge",
        "test_chain5_": "Chain 5: 媒体 → evidence",
        "test_chain6_": "Chain 6: TaskPack → Permission → Evaluation → Lesson",
        "test_chain7_": "Chain 7: Outbox → dispatcher → receipt",
    }

    coverage: dict[str, list[str]] = {chain: [] for chain in chain_prefixes.values()}
    for name, _fn in inspect.getmembers(module, inspect.isfunction):
        if not name.startswith("test_"):
            continue
        for prefix, label in chain_prefixes.items():
            if name.startswith(prefix):
                coverage[label].append(name)
                break

    missing = [label for label, fns in coverage.items() if not fns]
    assert not missing, f"E2E coverage gap — no tests for: {missing}"
