"""The completion-audit generator must be unable to print a conclusion it cannot source.

Finding 6 was that the audited generators printed five fixed verdict lines and claimed
every field was recomputed. These tests plant exactly that regression -- an unmarked
verdict reaching the output, a vacuous register scan, and a citation that only a
basename search could have resolved -- and require the run to refuse.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_completion_audit", ROOT / "scripts" / "audit" / "build_completion_audit.py"
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)

DISCIPLINE = audit._discipline


@pytest.fixture()
def corpus(tmp_path: Path):
    """An evidence root with one tiered receipt and a register that cites real paths."""
    repo = tmp_path / "repo"
    (repo / "docs" / "current").mkdir(parents=True)
    evidence = tmp_path / "artifacts" / "evidence"
    run = evidence / "p04-edit-loop-real-20261008"
    run.mkdir(parents=True)
    (run / "receipt.json").write_text(
        json.dumps({"evidence_level": "REAL_CANONICAL_WRITER", "source_commit": "abc1234567890"}),
        encoding="utf-8")
    source = repo / "frontend" / "src" / "app.ts"
    source.parent.mkdir(parents=True)
    source.write_text("export const x = 1;\n", encoding="utf-8")
    register = repo / "docs" / "current" / "REGISTER.md"
    register.write_text(
        "| key | 证据 |\n| --- | --- |\n| UI-02 | `frontend/src/app.ts` |\n", encoding="utf-8")
    return repo, evidence, register


def test_every_emitted_line_carries_a_provenance_marker(corpus) -> None:
    repo, evidence, register = corpus
    lines = audit.build_report(repo=repo, evidence_root=evidence, register_path=register,
                               today="2026-10-08")
    offenders = DISCIPLINE.scan_unmarked("\n".join(lines))
    assert offenders == [], offenders
    assert any("REAL_CANONICAL_WRITER" in line for line in lines)
    assert any("abc1234567" in line for line in lines), "the commit is read from the receipt"


def test_a_hardcoded_verdict_fails_the_run_on_the_written_bytes(corpus, tmp_path) -> None:
    """The regression the audited scripts actually shipped: a tidy conclusion typed into the
    generator. It must be caught after the write, from the file, not from memory."""
    repo, evidence, register = corpus
    lines = audit.build_report(repo=repo, evidence_root=evidence, register_path=register,
                               today="2026-10-08")
    lines.append("- `PASS/CI(force_full)`：仅冻结候选 `72a0bbc2` 已跑。")
    written = tmp_path / "report.md"
    written.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(DISCIPLINE.DisciplineViolation) as error:
        DISCIPLINE.check_written(written)
    assert "PASS/CI(force_full)" in str(error.value)


def test_an_empty_register_scan_says_so_instead_of_looking_clean(tmp_path) -> None:
    repo = tmp_path / "repo"
    (repo / "docs" / "current").mkdir(parents=True)
    empty = repo / "docs" / "current" / "REGISTER.md"
    empty.write_text("| key | 证据 |\n| --- | --- |\n| UI-09 | 无路径引用 |\n", encoding="utf-8")
    lines = audit.build_report(repo=repo, evidence_root=tmp_path / "no-evidence",
                              register_path=empty, today="2026-10-08")
    text = "\n".join(lines)
    assert "不构成引用完整性证明" in text
    assert "引用完整性" in text and "全部引用按精确路径解析" not in text


def test_a_citation_that_only_a_basename_search_could_resolve_is_not_a_pass(corpus, tmp_path) -> None:
    """The retired tool rglob'd the whole tree by basename. A register that cites only a
    bare file name must now come back unresolved, not 'found somewhere'."""
    repo, evidence, register = corpus
    lying = repo / "docs" / "current" / "LYING.md"
    lying.write_text("| key | 证据 |\n| --- | --- |\n| UI-77 | `elsewhere/deep/app.ts` |\n",
                     encoding="utf-8")
    lines = audit.build_report(repo=repo, evidence_root=evidence, register_path=lying,
                               today="2026-10-08")
    text = "\n".join(lines)
    assert "UI-77" in text
    assert "AMBIGUOUS" in text or "UNRESOLVED" in text
    assert "全部引用按精确路径解析：elsewhere" not in text


def test_the_tally_line_matches_the_markers_actually_present(corpus) -> None:
    repo, evidence, register = corpus
    lines = audit.build_report(repo=repo, evidence_root=evidence, register_path=register,
                               today="2026-10-08")
    tally_line = [line for line in lines if line.startswith("本报告的输出构成")][-1]
    stated = {kind: int(tally_line.split(f"{kind}")[1].split(" 行")[0])
              for kind in ("COMPUTED", "CLAIM", "INSUFFICIENT-EVIDENCE")}
    actual = {
        "COMPUTED": sum(1 for line in lines if f"〔{DISCIPLINE.COMPUTED}:" in line),
        "CLAIM": sum(1 for line in lines if f"〔{DISCIPLINE.CLAIM}:" in line),
        "INSUFFICIENT-EVIDENCE": sum(1 for line in lines
                                     if f"〔{DISCIPLINE.INSUFFICIENT}:" in line),
    }
    assert stated == actual, f"tally claims {stated} but the file carries {actual}"
