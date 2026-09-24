from __future__ import annotations

import json
from pathlib import Path

from scripts.maintenance.check_authority_sha_consistency import (
    check_authority_sha_consistency,
)


def _git_stub(values: dict[tuple[str, ...], str]):
    def run(*args: str) -> str:
        return values[args]

    return run


def _write_records(tmp_path: Path, current_sha: str, subject_sha: str) -> tuple[Path, Path]:
    overlay = tmp_path / "M0-DIRECTION-OVERRIDE.md"
    overlay.write_text(
        f"- 当前本地与远端 `main`：`{current_sha}`\n",
        encoding="utf-8",
    )
    state = tmp_path / "R6-STATE.json"
    state.write_text(json.dumps({"subject_sha": subject_sha}), encoding="utf-8")
    return overlay, state


def test_evidence_subject_sha_is_not_required_to_equal_record_commit_or_current_head(
    tmp_path: Path,
) -> None:
    head = "a" * 40
    first_parent = "b" * 40
    evidence_subject = "c" * 40
    overlay, state = _write_records(tmp_path, first_parent, evidence_subject)

    report = check_authority_sha_consistency(
        overlay,
        state,
        git=_git_stub(
            {
                ("rev-parse", "HEAD"): head,
                ("rev-parse", "origin/main"): head,
                ("cat-file", "-e", f"{evidence_subject}^{{commit}}"): "",
                ("log", "-1", "--format=%H", "--", str(overlay)): head,
                ("rev-list", "--parents", "-n", "1", head): f"{head} {first_parent}",
            }
        ),
    )

    assert report.errors == []
    assert report.current_head == head
    assert report.origin_main == head
    assert report.evidence_subject_sha == evidence_subject
    assert report.record_commit == head


def test_stale_current_main_claim_is_rejected_without_relabeling_evidence_subject(
    tmp_path: Path,
) -> None:
    claimed = "b" * 40
    head = "a" * 40
    evidence_subject = "c" * 40
    overlay, state = _write_records(tmp_path, claimed, evidence_subject)

    report = check_authority_sha_consistency(
        overlay,
        state,
        git=_git_stub(
            {
                ("rev-parse", "HEAD"): head,
                ("rev-parse", "origin/main"): head,
                ("cat-file", "-e", f"{evidence_subject}^{{commit}}"): "",
                ("log", "-1", "--format=%H", "--", str(overlay)): head,
                ("rev-list", "--parents", "-n", "1", head): f"{head} {'d' * 40}",
            }
        ),
    )

    assert any("current main claim" in error for error in report.errors)
    assert report.evidence_subject_sha == evidence_subject


def test_record_commit_must_be_current_head(tmp_path: Path) -> None:
    head = "a" * 40
    stale_record = "b" * 40
    overlay, state = _write_records(tmp_path, head, "c" * 40)

    report = check_authority_sha_consistency(
        overlay,
        state,
        git=_git_stub(
            {
                ("rev-parse", "HEAD"): head,
                ("rev-parse", "origin/main"): head,
                ("cat-file", "-e", f"{'c' * 40}^{{commit}}"): "",
                ("log", "-1", "--format=%H", "--", str(overlay)): stale_record,
                ("rev-list", "--parents", "-n", "1", stale_record): f"{stale_record} {'d' * 40}",
            }
        ),
    )

    assert any("record commit does not match git HEAD" in error for error in report.errors)


def test_current_head_must_equal_origin_main(tmp_path: Path) -> None:
    head = "a" * 40
    origin = "b" * 40
    overlay, state = _write_records(tmp_path, head, "c" * 40)

    report = check_authority_sha_consistency(
        overlay,
        state,
        git=_git_stub(
            {
                ("rev-parse", "HEAD"): head,
                ("rev-parse", "origin/main"): origin,
                ("cat-file", "-e", f"{'c' * 40}^{{commit}}"): "",
                ("log", "-1", "--format=%H", "--", str(overlay)): head,
                ("rev-list", "--parents", "-n", "1", head): f"{head} {origin}",
            }
        ),
    )

    assert any("HEAD differs from origin/main" in error for error in report.errors)


def test_duplicate_r6_state_member_is_rejected(tmp_path: Path) -> None:
    head = "a" * 40
    overlay = tmp_path / "M0-DIRECTION-OVERRIDE.md"
    overlay.write_text(
        f"- 当前本地与远端 `main`：`{head}`\n",
        encoding="utf-8",
    )
    state = tmp_path / "R6-STATE.json"
    state.write_text(
        '{"subject_sha":"' + "c" * 40 + '","subject_sha":"' + "d" * 40 + '"}',
        encoding="utf-8",
    )

    report = check_authority_sha_consistency(
        overlay,
        state,
        git=_git_stub(
            {
                ("rev-parse", "HEAD"): head,
                ("rev-parse", "origin/main"): head,
                ("log", "-1", "--format=%H", "--", str(overlay)): head,
                ("rev-list", "--parents", "-n", "1", head): head,
            }
        ),
    )

    assert any("duplicate JSON object member" in error for error in report.errors)
    assert report.evidence_subject_sha is None
