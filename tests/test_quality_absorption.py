from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

import knowledge_base.routers.quality as quality_router
from app.ingestion.multi_format import convert_directory_resumable
from app.main import app
from shared.accuracy_benchmark import evaluate_golden_pairs
from shared.content_quality import audit_markdown_quality
from shared.evidence_verification import match_evidence, verification_status
from shared.oer_crosswalk import build_crosswalk
from shared.processing_manifest import ProcessingManifest, source_artifact_key


def test_processing_manifest_resumes_only_latest_success(tmp_path: Path):
    manifest = ProcessingManifest(tmp_path / "manifest.jsonl")
    manifest.record("a.pdf", status="converted", handler="pymupdf", output="a.md")
    manifest.record("b.mp4", status="failed", handler="ffmpeg", error="decode failed")
    manifest.record("a.pdf", status="failed", handler="pymupdf", error="new attempt failed")
    manifest.record("c.zip", status="linked", handler="file-link")

    assert manifest.resumable_sources() == {"c.zip"}
    assert manifest.summary() == {"failed": 2, "linked": 1, "total": 3}
    assert len(manifest.history("a.pdf")) == 2


def test_source_artifact_key_avoids_same_name_collisions(tmp_path: Path):
    root = tmp_path / "source"
    left = root / "one" / "lesson.pdf"
    right = root / "two" / "lesson.pdf"
    left.parent.mkdir(parents=True)
    right.parent.mkdir(parents=True)
    left.write_bytes(b"left")
    right.write_bytes(b"right")

    assert source_artifact_key(left, root) != source_artifact_key(right, root)


def test_accuracy_requires_human_truth_pairs(tmp_path: Path):
    empty = evaluate_golden_pairs(tmp_path)
    assert empty["status"] == "unverified_no_golden_pairs"
    assert empty["sample_count"] == 0

    (tmp_path / "ocr.truth.txt").write_text("知识 图谱", encoding="utf-8")
    (tmp_path / "ocr.pred.txt").write_text("知识图普", encoding="utf-8")
    (tmp_path / "ocr.json").write_text(json.dumps({"kind": "ocr"}), encoding="utf-8")
    measured = evaluate_golden_pairs(tmp_path)

    assert measured["status"] == "measured_complete"
    assert measured["sample_count"] == 1
    assert measured["aggregate_cer"] == 0.25
    assert measured["aggregate_accuracy"] == 0.75

    (tmp_path / "missing.truth.txt").write_text("人工真值", encoding="utf-8")
    partial = evaluate_golden_pairs(tmp_path)
    assert partial["status"] == "incomplete_partial"
    assert partial["coverage"] == 0.5


def test_evidence_matching_never_returns_random_candidate():
    candidates = [
        {"source": "slides.pdf", "location": "page:3", "text": "向量数据库支持相似度检索", "asset": "p3.png", "kind": "pdf"},
        {"source": "video.mp4", "location": "120s", "text": "今天介绍烹饪", "asset": "120.png", "kind": "video"},
    ]
    result = match_evidence(["向量数据库"], candidates)
    assert result["status"] == "matched"
    assert result["match"]["source"] == "slides.pdf"

    missing = match_evidence(["知识蒸馏"], candidates)
    assert missing == {"status": "no_semantic_match", "terms_checked": 1, "candidates_checked": 2}


def test_verification_requires_independent_sources():
    one = [{"kind": "pdf", "source": "course.pdf", "status": "matched"}]
    assert verification_status(one)["status"] == "caller_supplied_candidate"

    duplicated = one + [{"kind": "pdf", "source": "course.pdf", "status": "matched"}]
    assert verification_status(duplicated)["status"] == "caller_supplied_candidate"

    independent = one + [
        {"kind": "oer", "source": "https://example.edu/course", "status": "matched"}
    ]
    public_result = verification_status(independent)
    assert public_result["status"] == "caller_supplied_candidate"

    caller_bound = [
        {**item, "claim_id": "claim-1", "location": f"locator-{index}"}
        for index, item in enumerate(independent)
    ]
    result = verification_status(caller_bound)
    assert result["status"] == "caller_supplied_candidate"
    assert result["independent_source_count"] == 2
    assert result["claim_bound_by_caller"] is True
    assert result["server_verified"] is False
    assert result["requires_human_review"] is True


def test_composite_quality_api_and_path_boundary(
    tmp_path: Path, monkeypatch
):
    simulated_project_root = tmp_path / "project-root"
    simulated_project_root.mkdir()
    monkeypatch.setattr(quality_router, "_PROJECT_ROOT", simulated_project_root)
    client = TestClient(app)
    response = client.post(
        "/kb/quality",
        json={
            "action": "evidence_match",
            "terms": ["认知闭环"],
            "candidates": [
                {"source": "lesson.md", "text": "认知闭环连接行动与反馈"}
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "matched"

    outside = client.post(
        "/kb/quality",
        json={"action": "accuracy", "golden_dir": str(tmp_path)},
    )
    assert outside.status_code == 400


def test_resumable_directory_conversion_records_file_level_state(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "lesson.md").write_text("# 可恢复摄入", encoding="utf-8")
    manifest = tmp_path / "state" / "manifest.jsonl"

    first = convert_directory_resumable(source, manifest)
    assert first["summary"] == {"converted": 1, "total": 1}
    assert first["processed"] == 1
    output = Path(first["results"][0]["output"])
    assert output.read_text(encoding="utf-8") == "# 可恢复摄入"

    second = convert_directory_resumable(source, manifest)
    assert second["processed"] == 0
    assert second["resumed"] == 1

    (source / "lesson.md").write_text("# 源文件已更新", encoding="utf-8")
    changed = convert_directory_resumable(source, manifest)
    assert changed["processed"] == 1
    assert output.read_text(encoding="utf-8") == "# 源文件已更新"

    output.write_text("tampered", encoding="utf-8")
    repaired = convert_directory_resumable(source, manifest)
    assert repaired["processed"] == 1
    assert output.read_text(encoding="utf-8") == "# 源文件已更新"


def test_oer_crosswalk_is_candidate_only_until_sources_are_retrieved():
    result = build_crosswalk("RAG 使用向量检索、rerank 和知识图谱", terms=["RAG"])
    assert result["profile"] == "technical"
    assert result["verification_status"] == "recommended_sources_only_not_verified"
    assert any(item["source"] == "MDN Web Docs" for item in result["recommendations"])


def test_content_quality_rejects_misleading_completion_and_watermarks():
    result = audit_markdown_quality(
        "# 课程\n完成度: 100%\n瑞客论坛 www.ruike1.com\n[[存在页]] [[缺失页]]",
        known_targets={"存在页"},
    )
    assert result["status"] == "needs_review"
    assert result["misleading_completion_claims"] == 1
    assert result["watermark_hits"] == 1
    assert result["broken_wikilinks"] == ["缺失页"]
