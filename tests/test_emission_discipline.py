"""Emission discipline is only a rule if a hand-typed conclusion can be caught by it.

FINDING 6 was that two audit generators printed verdicts and counts typed into their own
source while claiming the numbers came from artifacts. These tests plant exactly those
lines and require the module to refuse them, and they plant the cheaper evasions
(a marker typed onto a line no resolver produced, an empty source, a verdict inside a
fence) so the guard cannot be satisfied by decoration.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "emission_discipline", ROOT / "scripts" / "audit" / "emission_discipline.py"
)
assert SPEC and SPEC.loader
ed = importlib.util.module_from_spec(SPEC)
# @dataclass resolves cls.__module__ through sys.modules while processing the class body,
# so a spec-loaded module has to be registered before it executes.
sys.modules[SPEC.name] = ed
SPEC.loader.exec_module(ed)

# Verbatim from the audited generators: build-external-audit-handoff.py:121 and
# build-completion-audit.py:99. They are the regression, not an invented example.
RETIRED_COUNT_LINE = "全部门禁通过（前端 365、Rust 526）。"
RETIRED_VERDICT_LINE = "`PASS/CI(force_full)`：仅冻结候选 `72a0bbc2` 已跑。"


def test_computed_refuses_a_literal_number_typed_into_the_template() -> None:
    with pytest.raises(ed.DisciplineViolation) as error:
        ed.computed("前端 {files} 个文件、Rust 526 个测试通过", "receipt.json#counts", files=lambda: 41)
    assert "526" in str(error.value)


def test_computed_refuses_a_placeholder_with_no_resolver() -> None:
    with pytest.raises(ed.DisciplineViolation, match="no resolver"):
        ed.computed("tests passed: {passed}", "receipt.json#passed")


def test_computed_takes_the_value_from_the_resolver_not_from_the_template() -> None:
    calls: list[int] = []

    def read() -> int:
        calls.append(1)
        return 428

    item = ed.computed("vitest: {tests} passed", "receipt.json#tests", tests=read)
    # The resolver runs at construction, so a generator cannot accumulate stale reads and
    # print them later; the number in the text is the value the artifact returned.
    assert calls == [1]
    assert item.render() == "vitest: 428 passed 〔COMPUTED: receipt.json#tests〕"


def test_the_retired_hardcoded_lines_do_not_pass_as_emissions() -> None:
    offenders = ed.scan_unmarked(f"## 结果\n{RETIRED_COUNT_LINE}\n{RETIRED_VERDICT_LINE}\n")
    assert len(offenders) == 2, offenders
    assert any("365" in line for line in offenders)
    assert any("PASS/CI" in line for line in offenders)


def test_a_marker_typed_by_hand_is_refused_because_this_run_never_emitted_it() -> None:
    """The obvious workaround for the guard is to paste the suffix on; that is the same
    defect wearing a label, so the line must also appear in what the run produced."""
    items = [ed.computed("vitest: {tests} passed", "receipt.json#tests", tests=lambda: 428)]
    forged = f"{RETIRED_COUNT_LINE} 〔COMPUTED: receipt.json#counts〕"
    offenders = ed.scan_unproduced(forged, items)
    assert len(offenders) == 1 and "MARKED_BUT_NOT_EMITTED" in offenders[0]


def test_a_claim_with_no_source_is_refused_rather_than_printed_bare() -> None:
    with pytest.raises(ed.DisciplineViolation, match="without a source"):
        ed.claim("本会话未做任一远程写。", "   ")
    with pytest.raises(ed.DisciplineViolation, match="without a reason"):
        ed.insufficient("远端 CI 结论", "")


def test_a_marker_with_an_empty_source_is_an_offender() -> None:
    line = "some conclusion 〔COMPUTED: 〕"
    assert any("EMPTY_SOURCE" in offender for offender in ed.scan_unmarked(line))


def test_structural_lines_are_exempt_but_a_heading_cannot_hide_a_verdict() -> None:
    document = "\n".join([
        "# 标题",
        "",
        "| --- | --- |",
        "## 结论",
        "全部通过",
    ])
    offenders = ed.scan_unmarked(document)
    assert len(offenders) == 1, offenders
    assert "全部通过" in offenders[0]


def test_verbatim_fences_quoting_artifact_bytes_are_not_policed() -> None:
    fenced = "\n".join(ed.verbatim(["PASS/CI(force_full) 72a0bbc2", "（前端 365、Rust 526）"],
                                   "receipt.raw.log"))
    assert ed.scan_unmarked(fenced) == []
    # ...but strip the fence marker and the quoted verdict must not stay exempt.
    assert ed.scan_unmarked(fenced.replace("``` 〔VERBATIM-FROM: receipt.raw.log〕", "```"))


def test_check_written_polices_the_bytes_on_disk_not_the_generators_memory(tmp_path) -> None:
    bad = tmp_path / "report.md"
    bad.write_text(f"# 报告\n{RETIRED_VERDICT_LINE}\n", encoding="utf-8")
    with pytest.raises(ed.DisciplineViolation):
        ed.check_written(bad)

    items = [ed.claim("本轮未推送任何分支。", "owner instruction 2026-10-08")]
    good = tmp_path / "clean.md"
    good.write_text("# 报告\n" + "\n".join(ed.render(items)) + "\n", encoding="utf-8")
    assert ed.check_written(good, items).startswith("# 报告")


def test_tally_reports_what_the_run_actually_produced() -> None:
    items = [
        ed.computed("a={a}", "src#a", a=lambda: 1),
        ed.claim("b", "conversation"),
        ed.claim("c", "conversation"),
        ed.insufficient("d", "no receipt"),
        "structural line",
    ]
    assert ed.tally(items) == {
        ed.COMPUTED: 1, ed.CLAIM: 2, ed.INSUFFICIENT: 1,
    }


def test_the_cli_fails_a_dirty_document_and_passes_a_clean_one(tmp_path, capsys) -> None:
    dirty = tmp_path / "dirty.md"
    dirty.write_text(f"{RETIRED_COUNT_LINE}\n", encoding="utf-8")
    assert ed.main([str(dirty)]) == 1
    assert "UNMARKED" in capsys.readouterr().out

    clean = tmp_path / "clean.md"
    # Structural-only plus one honestly marked claim: a bare sentence would itself be an
    # unmarked assertion, which is exactly what the guard exists to catch.
    clean.write_text(
        "# 报告\n" + ed.claim("本轮未推送任何分支。", "owner instruction 2026-10-08").render() + "\n",
        encoding="utf-8",
    )
    assert ed.main([str(clean)]) == 0


def test_assert_discipline_names_the_offending_line_so_a_generator_can_fix_it() -> None:
    with pytest.raises(ed.DisciplineViolation) as error:
        ed.assert_discipline(f"heading\n{RETIRED_VERDICT_LINE}\n")
    message = str(error.value)
    assert RETIRED_VERDICT_LINE in message
    assert "UNMARKED" in message
