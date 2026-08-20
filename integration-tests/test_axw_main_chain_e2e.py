"""AXW §19 #17 E2E: multi-format intake → conversion → evidence ledger → human learning → AI assets.

Real main chain under test (product modules only, no mocks):

  Stage 1  Ingestion + conversion
           app.workspace.service.intake_upload
             -> app.ingestion.multi_format.convert_file (per-format engine chain)
             -> app.research.document.persist_workspace_document
  Stage 2  Evidence & Knowledge Ledger (SQLite transaction truth source)
           shared.research_store.persist_research_graph (transactional write)
           shared.research_store.load_research_package  (strict read-back)
           app.evidence.anchor EvidenceAnchor store/resolve (AXW-020C)
  Stage 3  Human Learning Vault
           app.knowledge.promotion.promote_research_package_to_candidates
           app.knowledge.closed_loop.start_and_approve_learning_candidate
             -> knowledge_candidate_learning_artifacts_v1 + kb_cards
           app.knowledge.vault_projection.project_learning_artifact
             -> human_learning_vault/*.md
  Stage 4  AI Asset Vault
           app.knowledge.closed_loop.record_practice_evidence x3
             -> mastery_signals_v1 -> machine_knowledge_candidates_v1
             (evidence binding: machine unit -> source_signal_id -> card ->
              source_record_ids -> research_sources_v1 row)
           app.knowledge.machine_knowledge.deprecate_machine_knowledge_candidate
             (human approval; candidates are never auto-trusted)
           app.knowledge.machine_knowledge.list_runtime_machine_knowledge
             (runtime read-back only returns approved units)
           app.knowledge.vault_projection.project_approved_machine_knowledge_asset
             -> ai_asset_vault/*.json

Format support:
  - txt / md : passthrough engine, always available, zero external dependencies.
  - html     : trafilatura -> safe-http+raw fallback, no external dependency.
  - docx     : markitdown engine (optional dependency). The DOCX test SKIPs with
               reason when markitdown is not installed. pptx/xlsx/pdf/media/ocr
               adapters need optional engines and are outside this
               no-external-dependency main chain (not covered here).

Governance invariant:
  AI asset registration requires human approval: candidates are created with
  lifecycle_status="candidate" and requires_human_review=True; runtime
  consumption only returns approved units. The test asserts this real semantic
  end-to-end.

Fail-closed: no exception is swallowed; every stage is read back and asserted.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
import zipfile
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import pytest

from shared.migration_runner import MigrationOperator
from shared.workspace_manifest import ASSET_DOMAINS, WorkspaceManifest, create_workspace, load

_MIGRATION_OWNERS = (
    "core.sqlite",
    "research.sqlite",
    "knowledge-governance.sqlite",
    "taskpack.sqlite",
    "sleep-loop.sqlite",
    "workspace.sqlite",
)

_TXT = "AXW_TXT_MARKER first claim sentence for txt intake.\nSecond paragraph with supporting evidence.\n"
_MD = "# AXW_MD_MARKER first claim sentence for md intake.\n\nSecond paragraph with supporting evidence.\n"
_HTML = (
    "<!doctype html>\n"
    "<html><head><title>AXW_HTML_MARKER page</title></head>"
    "<body><h1>AXW_HTML_MARKER</h1>"
    "<p>first claim sentence for html intake.</p>"
    "<p>Second paragraph with supporting evidence.</p></body></html>\n"
)


@dataclass(frozen=True)
class AxwWorkspace:
    """One four-domain workspace (workspace_manifest) plus its migrated ledger."""

    root: Path
    manifest: WorkspaceManifest
    db: Path
    source_archive: Path
    evidence_ledger: Path
    human_learning_vault: Path
    ai_asset_vault: Path


@pytest.fixture
def axw_workspace(tmp_path: Path) -> AxwWorkspace:
    """Create the four asset domains via the real manifest API, then migrate the ledger."""
    manifest = create_workspace(tmp_path, "axw-e2e")
    assert set(manifest.domains) == set(ASSET_DOMAINS)
    database = Path(str(manifest.domains["evidence_ledger"].path)) / "ledger.sqlite"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("CREATE TABLE sentinel(id TEXT PRIMARY KEY)")
        connection.commit()
    operator = MigrationOperator(db_path=database, backup_dir=database.parent / "backups")
    for owner in _MIGRATION_OWNERS:
        operator.apply(owner)
    return AxwWorkspace(
        root=tmp_path,
        manifest=manifest,
        db=database,
        source_archive=Path(str(manifest.domains["source_archive"].path)),
        evidence_ledger=Path(str(manifest.domains["evidence_ledger"].path)),
        human_learning_vault=Path(str(manifest.domains["human_learning_vault"].path)),
        ai_asset_vault=Path(str(manifest.domains["ai_asset_vault"].path)),
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _stamp() -> str:
    return uuid.uuid4().hex[:12]


def _run_main_chain(ws: AxwWorkspace, file_name: str, content: bytes) -> dict[str, object]:
    """Run the real main chain and return every stage artifact for read-back asserts."""
    from app.evidence.anchor import (
        build_evidence_anchor,
        store_evidence_anchor,
    )
    from app.knowledge.closed_loop import (
        record_practice_evidence,
        start_and_approve_learning_candidate,
    )
    from app.knowledge.machine_knowledge import (
        MachineKnowledgeApproval,
        deprecate_machine_knowledge_candidate,
        list_runtime_machine_knowledge,
    )
    from app.knowledge.promotion import (
        ResearchKnowledgeApproval,
        promote_research_package_to_candidates,
    )
    from app.knowledge.vault_projection import (
        project_approved_machine_knowledge_asset,
        project_learning_artifact,
    )
    from app.workspace import service
    from shared.research_store import load_research_package

    source_file = ws.source_archive / file_name
    source_file.write_bytes(content)

    # ── Stage 1: real ingestion + conversion (intake_upload runs the engine chain) ──
    intake = service.intake_upload(file_name=file_name, content=content, db_path=ws.db)
    package_id = str(intake["package_id"])

    # ── Stage 2: evidence ledger strict read-back + evidence anchor ──
    graph = load_research_package(package_id, db_path=ws.db, live_wal=True)
    source = graph.sources[0]
    provenance = graph.source_provenance[0]
    claim = graph.claims[0]
    evidence = graph.evidence[0]
    anchor = build_evidence_anchor(
        raw_sha256=provenance.content_hash.removeprefix("sha256:"),
        source_revision=package_id,
        locator={
            "package_id": package_id,
            "claim_id": claim.claim_id,
            "evidence_id": evidence.evidence_id,
            "location": evidence.location,
        },
    )
    store_evidence_anchor(ws.db, anchor)

    # ── Stage 3: governed promotion -> human learning artifact + cards + vault file ──
    receipt = promote_research_package_to_candidates(
        ResearchKnowledgeApproval(
            approval_id=f"appr-{_stamp()}",
            package_id=package_id,
            reviewer_id="local-workspace",
            decision="approved",
            rationale="E2E main chain",
            reviewed_at=_now(),
        ),
        db_path=ws.db,
    )
    claim_units = [unit for unit in receipt.units if unit.unit_type == "research_claim"]
    assert claim_units, "promotion produced no research_claim unit"
    claim_unit = claim_units[0]
    artifact, cards = start_and_approve_learning_candidate(
        unit_id=claim_unit.unit_id,
        approval_id=f"learn-{_stamp()}",
        approval_command_id=f"cmd-{_stamp()}",
        reviewer_id="local-workspace",
        rationale="E2E main chain",
        reviewed_at=_now(),
        db_path=ws.db,
    )
    written = project_learning_artifact(
        artifact.artifact_id,
        db_path=ws.db,
        vault_root=ws.human_learning_vault,
        dry_run=False,
    )

    # ── Stage 4: practice x3 -> mastered signal -> machine knowledge -> approval ──
    machine = None
    for index in range(3):
        result = record_practice_evidence(
            artifact_id=artifact.artifact_id,
            command_id=f"p-{_stamp()}-{index}",
            quality=5,
            recorded_at=_now(),
            db_path=ws.db,
        )
        machine = result.machine_knowledge
    assert machine is not None, "machine knowledge candidate was not created after mastery"
    approved = deprecate_machine_knowledge_candidate(
        MachineKnowledgeApproval(
            approval_id=f"mk-{_stamp()}",
            candidate_id=machine.unit_id,
            reviewer_id="local-workspace",
            decision="approved",
            rationale="E2E main chain",
            reviewed_at=_now(),
        ),
        db_path=ws.db,
    )
    runtime_units = list_runtime_machine_knowledge(db_path=ws.db)
    asset_write = project_approved_machine_knowledge_asset(
        approved.unit_id,
        db_path=ws.db,
        asset_root=ws.ai_asset_vault,
        dry_run=False,
    )
    return {
        "intake": intake,
        "graph": graph,
        "source": source,
        "provenance": provenance,
        "claim": claim,
        "evidence": evidence,
        "anchor": anchor,
        "receipt": receipt,
        "claim_unit": claim_unit,
        "artifact": artifact,
        "cards": cards,
        "vault_file": Path(str(written["file_path"])),
        "machine": machine,
        "approved_unit": approved,
        "runtime_units": runtime_units,
        "binding": asset_write["evidence_binding"],
        "asset_snapshot": Path(str(asset_write["file_path"])),
    }


def _assert_stage_ingestion(
    ws: AxwWorkspace, artifacts: dict[str, object], *, fmt: str, marker: str
) -> None:
    from app.evidence.anchor import resolve_evidence_anchor
    from app.ingestion.conversion_run import resolve_conversion_run
    from app.workspace import service

    intake = artifacts["intake"]
    assert intake["status"] == "candidate", "intake must land as a review-required candidate"
    assert intake["requires_human_review"] is True
    assert intake["source_type"] == "file"
    assert intake["format"] == fmt
    assert intake["char_count"] > 0
    assert marker in str(intake["content"]), "converted content lost the source marker"
    conversion = resolve_conversion_run(ws.db, str(intake["conversion_run_id"]))
    assert conversion is not None, "upload conversion receipt is missing"
    assert conversion.raw_sha256 == intake["raw_sha256"]
    assert conversion.document.document_id == intake["derived_document_id"]
    assert len(conversion.blocks) == intake["conversion_block_count"]
    assert all(block.anchor for block in conversion.blocks)
    upload_anchor = resolve_evidence_anchor(ws.db, str(intake["evidence_anchor_id"]))
    assert upload_anchor is not None, "raw upload anchor is missing"
    assert upload_anchor.raw_sha256 == intake["raw_sha256"]
    assert upload_anchor.source_revision == intake["conversion_run_id"]
    assert set(upload_anchor.locator["block_ids"]) == {block.block_id for block in conversion.blocks}
    job = service.intake_job(job_id=str(intake["job_id"]), db_path=ws.db)
    assert job["state"] == "succeeded", "intake job receipt must be succeeded"


def _assert_stage_evidence_ledger(
    ws: AxwWorkspace, artifacts: dict[str, object], *, marker: str
) -> None:
    from app.evidence.anchor import list_evidence_anchors, resolve_evidence_anchor

    graph = artifacts["graph"]
    source = artifacts["source"]
    provenance = artifacts["provenance"]
    claim = artifacts["claim"]
    evidence = artifacts["evidence"]
    assert graph.package.status == "candidate"
    assert graph.package.requires_human_review is True
    assert marker in source.content, "ledger source content lost the marker"
    content_bytes = source.content.encode("utf-8")
    assert provenance.content_hash == f"sha256:{sha256(content_bytes).hexdigest()}"
    assert provenance.byte_length == len(content_bytes)
    assert provenance.collector_identity == "workspace-local-intake-v1"
    assert provenance.payload_role == "workspace_document"
    assert claim.status == "candidate"
    assert claim.requires_human_review is True
    assert claim.source_record_ids == [source.source_id]
    assert evidence.status == "matched"
    assert evidence.claim_id == claim.claim_id
    assert evidence.matched_term in source.content, "evidence must be grounded in the source"
    assert evidence.matched_term in evidence.context
    assert evidence.asset_locator == provenance.content_hash
    with sqlite3.connect(ws.db) as connection:
        for table in (
            "research_packages_v1",
            "research_sources_v1",
            "research_claims_v1",
            "research_evidence_v1",
            "research_governance_findings_v1",
            "ir_intake_cards",
            "research_package_intake_links_v1",
        ):
            count = connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            assert count >= 1, f"evidence ledger table {table} is empty"
    anchor = artifacts["anchor"]
    resolved = resolve_evidence_anchor(ws.db, anchor.anchor_id)
    assert resolved == anchor, "evidence anchor must round-trip"
    assert anchor.anchor_id in {item.anchor_id for item in list_evidence_anchors(ws.db)}


def _assert_stage_human_learning(
    ws: AxwWorkspace, artifacts: dict[str, object], *, marker: str
) -> None:
    receipt = artifacts["receipt"]
    assert receipt.lifecycle_status == "candidate"
    claim_unit = artifacts["claim_unit"]
    provenance = claim_unit.properties["provenance"]
    assert provenance["requires_human_review"] is True
    assert provenance["research_package_id"] == artifacts["graph"].package.package_id
    assert provenance["evidence_ids"], "knowledge unit must be bound to ledger evidence"
    artifact = artifacts["artifact"]
    cards = artifacts["cards"]
    assert artifact.artifact_id.startswith("knowledge-learning-artifact_")
    assert artifact.status == "candidate"
    assert artifact.requires_human_review is True
    assert artifact.source_record_ids == [artifacts["source"].source_id]
    assert str(artifact.summary["statement"]).strip()
    assert len(cards) >= 1
    with sqlite3.connect(ws.db) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT artifact_json FROM knowledge_candidate_learning_artifacts_v1 WHERE id=?",
            (artifact.artifact_id,),
        ).fetchone()
        assert row is not None, "learning artifact row is missing"
        card_row = connection.execute(
            "SELECT title, source_ids_json FROM kb_cards WHERE id=?", (cards[0],)
        ).fetchone()
        assert card_row is not None, "learning card row is missing"
        assert json.loads(str(card_row["source_ids_json"])) == artifact.source_record_ids
        assert str(card_row["title"]) == str(artifact.summary["statement"])
    vault_file = artifacts["vault_file"]
    assert vault_file.is_file(), "human learning vault file was not written"
    note = vault_file.read_text(encoding="utf-8")
    assert artifact.artifact_id in note
    assert str(artifact.summary["statement"]) in note


def _assert_stage_ai_asset(ws: AxwWorkspace, artifacts: dict[str, object]) -> None:
    machine = artifacts["machine"]
    assert machine.unit_type == "rule"
    assert machine.source_type == "mastery_signal"
    assert machine.lifecycle_status == "candidate", "GAP-3: pre-approval must be candidate"
    assert machine.requires_human_review is True
    approved = artifacts["approved_unit"]
    assert approved.lifecycle_status == "approved"
    assert approved.requires_human_review is False
    runtime_units = artifacts["runtime_units"]
    assert any(unit.unit_id == approved.unit_id for unit in runtime_units), (
        "approved AI asset must be visible to runtime consumption"
    )
    binding = artifacts["binding"]
    assert binding["machine_unit_id"] == machine.unit_id
    assert binding["source_record_ids"] == [artifacts["source"].source_id]
    with sqlite3.connect(ws.db) as connection:
        connection.row_factory = sqlite3.Row
        source = connection.execute(
            "SELECT id FROM research_sources_v1 WHERE id=?",
            (binding["source_record_ids"][0],),
        ).fetchone()
        assert source is not None, "binding target must exist in the evidence ledger"
        event = connection.execute(
            "SELECT decision FROM machine_knowledge_approval_events_v1 WHERE candidate_id=?",
            (approved.unit_id,),
        ).fetchone()
        assert event is not None, "human approval event is missing"
        assert str(event["decision"]) == "approved"
    snapshot = artifacts["asset_snapshot"]
    assert snapshot.is_file(), "AI asset vault snapshot was not written"
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    assert payload["asset"]["unit_id"] == approved.unit_id
    assert payload["evidence_binding"]["source_record_ids"] == binding["source_record_ids"]


@pytest.mark.parametrize(
    ("file_name", "content", "fmt", "engines", "marker"),
    [
        pytest.param(
            "sample.txt", _TXT.encode("utf-8"), "txt", {"passthrough"}, "AXW_TXT_MARKER", id="txt"
        ),
        pytest.param(
            "sample.md", _MD.encode("utf-8"), "md", {"passthrough"}, "AXW_MD_MARKER", id="md"
        ),
        pytest.param(
            "sample.html",
            _HTML.encode("utf-8"),
            "html",
            {"trafilatura", "safe-http+raw"},
            "AXW_HTML_MARKER",
            id="html",
        ),
    ],
)
def test_axw_main_chain_full_e2e(
    axw_workspace: AxwWorkspace,
    file_name: str,
    content: bytes,
    fmt: str,
    engines: set[str],
    marker: str,
) -> None:
    """One real file walks the whole main chain; every stage is read back and asserted."""
    artifacts = _run_main_chain(axw_workspace, file_name, content)
    assert str(artifacts["intake"]["engine"]) in engines, "conversion engine outside the real chain"
    _assert_stage_ingestion(axw_workspace, artifacts, fmt=fmt, marker=marker)
    _assert_stage_evidence_ledger(axw_workspace, artifacts, marker=marker)
    _assert_stage_human_learning(axw_workspace, artifacts, marker=marker)
    _assert_stage_ai_asset(axw_workspace, artifacts)


def test_axw_main_chain_pdf_records_page_anchored_conversion(axw_workspace: AxwWorkspace) -> None:
    """A real PDF upload preserves its raw hash and records a page anchor."""
    from app.ingestion.conversion_run import resolve_conversion_run
    from tests.golden_pdf_fixture import GOLDEN_PDF

    artifacts = _run_main_chain(axw_workspace, "golden.pdf", GOLDEN_PDF)
    assert artifacts["intake"]["engine"] == "markitdown"
    _assert_stage_ingestion(axw_workspace, artifacts, fmt="pdf", marker="Golden Journey Evidence")
    conversion = resolve_conversion_run(
        axw_workspace.db, str(artifacts["intake"]["conversion_run_id"])
    )
    assert conversion is not None
    assert conversion.engine == "pdfplumber-structured"
    assert any(block.anchor.get("page_number") == 1 for block in conversion.blocks)
    assert any(block.kind == "table" and "Criterion" in block.text for block in conversion.blocks)
    assert conversion.loss_report.loss_notes == [
        "page 1: image semantics retained as a loss boundary"
    ]
    _assert_stage_evidence_ledger(axw_workspace, artifacts, marker="Golden Journey Evidence")
    _assert_stage_human_learning(axw_workspace, artifacts, marker="Golden Journey Evidence")
    _assert_stage_ai_asset(axw_workspace, artifacts)


def _build_docx(path: Path, marker: str) -> None:
    """Build a minimal but valid .docx (zip with OOXML parts) using only the stdlib."""
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    relationships = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        "</Relationships>"
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        f"<w:p><w:r><w:t>{marker} first claim sentence for docx intake.</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>Second paragraph with supporting evidence.</w:t></w:r></w:p>"
        "</w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("word/document.xml", document)


def test_axw_main_chain_docx_when_markitdown_available(axw_workspace: AxwWorkspace) -> None:
    """DOCX main-chain run through the real markitdown engine.

    SKIP reason: markitdown is an optional conversion engine; without it the
    DOCX chain cannot run. The zero-external-dependency main chain is
    txt/md/html (covered by test_axw_main_chain_full_e2e); DOCX is exercised
    here whenever the optional engine is installed.
    """
    pytest.importorskip("markitdown", reason="markitdown not installed; DOCX chain is optional")
    marker = "AXWDOCXMARKER"
    docx_path = axw_workspace.source_archive / "sample.docx"
    _build_docx(docx_path, marker)
    artifacts = _run_main_chain(axw_workspace, "sample.docx", docx_path.read_bytes())
    assert str(artifacts["intake"]["engine"]) == "markitdown"
    _assert_stage_ingestion(axw_workspace, artifacts, fmt="docx", marker=marker)
    _assert_stage_evidence_ledger(axw_workspace, artifacts, marker=marker)
    _assert_stage_human_learning(axw_workspace, artifacts, marker=marker)
    _assert_stage_ai_asset(axw_workspace, artifacts)


def test_axw_workspace_four_asset_domains(axw_workspace: AxwWorkspace) -> None:
    """The real manifest API creates the four asset domains and round-trips."""
    manifest = axw_workspace.manifest
    assert set(manifest.domains) == set(ASSET_DOMAINS)
    for domain_key in ASSET_DOMAINS:
        assert Path(str(manifest.domains[domain_key].path)).is_dir(), f"{domain_key} missing"
    manifest_path = axw_workspace.root / "axw-e2e" / "manifest.json"
    assert manifest_path.is_file()
    reloaded = load(manifest_path)
    assert reloaded.workspace_id == manifest.workspace_id
    assert reloaded.name == "axw-e2e"
