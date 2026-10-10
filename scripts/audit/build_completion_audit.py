"""Build the plan completion audit from artefacts, under emission discipline.

This replaces the throwaway script that lived in `.project-local/runs/`, which opened by
claiming "nothing here is quoted from memory" while printing five fixed verdict lines and
resolving citations by matching a basename anywhere in the tree. Two properties are now
structural rather than asserted:

* every line the report emits is produced through `emission_discipline`, so a number is
  either read from an artefact by a resolver or it is labelled CLAIM / INSUFFICIENT-EVIDENCE
  with the source or reason named; the run re-reads the written bytes and fails if anything
  else reached the output;
* citation existence is decided by `reference_validation` -- exact path inside a declared
  root, with identity checked where the record carries a hash or commit -- so a same-named
  file in an unrelated directory can no longer make a row look verified.

The report states its own COMPUTED / CLAIM / INSUFFICIENT-EVIDENCE tally, which is computed,
and never claims that all fields were recomputed from disk.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_discipline = _load("emission_discipline_for_audit", ROOT / "scripts" / "audit" / "emission_discipline.py")
_reference = _load("reference_validation_for_audit", ROOT / "scripts" / "audit" / "reference_validation.py")

TIER_KEYS = ("evidence_class", "evidence_level", "tier")
COMMIT_KEYS = ("source_commit", "commit")
#: Whitespace plus the full-width punctuation a register cell uses to glue prose onto a path.
_CELL_SPLIT = re.compile(r"[\s，。、；：（）()【】\[\]<>\|]+")


def read_receipt(directory: Path) -> dict[str, object]:
    """Take the tier from whichever JSON receipt actually carries one."""
    for candidate in sorted(directory.glob("*.json")):
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        tier = next((str(data[key]) for key in TIER_KEYS if data.get(key)), None)
        if tier:
            commit = next((str(data[key]) for key in COMMIT_KEYS if data.get(key)), "")
            return {"receipt": candidate.name, "tier": tier, "commit": commit[:12], "data": data}
    return {"receipt": "", "tier": "", "commit": "", "data": {}}


def evidence_directories(evidence_root: Path) -> dict[str, dict[str, object]]:
    if not evidence_root.is_dir():
        return {}
    out: dict[str, dict[str, object]] = {}
    for directory in sorted(p for p in evidence_root.iterdir() if p.is_dir()):
        receipt = read_receipt(directory)
        receipt["files"] = len(list(directory.iterdir()))
        out[directory.name] = receipt
    return out


def register_rows(register_path: Path) -> tuple[list[dict[str, object]], int]:
    """Every table row of the open-work register, with the paths any of its cells cites.

    Returns the rows and how many table rows were examined, so a run that parsed nothing can
    say so instead of printing an empty section that reads like a clean result.
    """
    if not register_path.is_file():
        return [], 0
    rows: list[dict[str, object]] = []
    examined = 0
    for line in register_path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| "):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 2 or not cells[0] or set(cells[0]) <= {"-", ":", " "}:
            continue
        examined += 1
        # Citations are not confined to one column, and a register cell glues prose onto the
        # path with full-width punctuation, so the split is on whitespace and CJK punctuation
        # rather than whitespace alone -- otherwise the token is a path plus a sentence and
        # cannot resolve even when the cited file is right there.
        cited = [
            token.strip("`")
            for cell in cells[1:]
            for token in _CELL_SPLIT.split(cell)
            if "/" in token and token.strip("`").endswith(
                (".py", ".ts", ".tsx", ".json", ".md", ".rs", ".yaml", ".yml", ".txt", ".log", ".csv"))
        ]
        if cited:
            rows.append({"key": cells[0], "cited": cited})
    return rows, examined


def cite_verdicts(citations: list[str], roots, roots_map, repo: Path) -> list:
    """Resolve each citation exactly. No basename search, so nothing is satisfied by luck."""
    verdicts = []
    for token in citations:
        ref = _reference.parse_reference(token, roots, default_root=roots[0].name)
        verdicts.append(_reference.validate_reference(ref, roots_map, repo=repo))
    return verdicts


def build_report(*, repo: Path, evidence_root: Path, register_path: Path,
                 today: str, extra_claims: list[tuple[str, str]] | None = None) -> list[str]:
    """Compose the report. Each line is a discipline Item, never a bare f-string verdict."""
    roots = _reference.default_roots(repo)
    roots_map = _reference.root_map(roots)
    claims = evidence_directories(evidence_root)
    rows, examined_rows = register_rows(register_path)
    computed = _discipline.COMPUTED

    lines: list[object] = [
        f"# 计划完成度审计（{today}）",
        _discipline.insufficient(
            "本报告不主张数据真实性全覆盖：它只证明回执里写了什么、引用能否按精确路径解析。",
            "no truth-pair human annotation exists for the model outputs"),
        "## 证据目录（层级取自回执自己的字段）",
    ]
    if not claims:
        lines.append(_discipline.insufficient(
            "证据根目录不存在或为空，因此没有任何切片层级可主张。",
            f"{evidence_root} is not a directory or holds no subdirectories"))
    for name, receipt in claims.items():
        lines.append(_discipline.computed(
            "`{name}` 层级 `{tier}`，收据 `{receipt}`，文件 {files} 个，提交 `{commit}`",
            source=f"{evidence_root.name}/{name}/<receipt json>#evidence_level",
            name=lambda n=name: n, tier=lambda r=receipt: r["tier"] or "NO-TIER",
            receipt=lambda r=receipt: r["receipt"] or "NONE",
            files=lambda r=receipt: r["files"], commit=lambda r=receipt: r["commit"] or "-"))

    lines.append("## register 行内引用路径的解析结果")
    if not rows:
        # An empty scan is not a clean scan. The first version of this audit proved the
        # point by reporting "all citations resolved" over a list it had never populated.
        lines.append(_discipline.insufficient(
            f"登记表 {register_path.name} 的检查未解析到任何引用路径（已查看 {examined_rows} 行表格），"
            "因此本节不构成引用完整性证明。",
            reason="zero cited rows extracted; either the register cites no paths or the "
                   "extractor does not understand its table shape"))
    unresolved_total = 0
    for row in rows:
        verdicts = cite_verdicts([str(c) for c in row["cited"]], roots, roots_map, repo)
        bad = [v for v in verdicts if v.verdict not in _reference.SATISFIED]
        unresolved_total += len(bad)
        detail = "; ".join(f"{v.citation}→{v.verdict}" for v in verdicts)
        maker = _discipline.computed if not bad else _discipline.claim
        if not bad:
            lines.append(_discipline.computed(
                "**{key}** 全部引用按精确路径解析：{detail}",
                source="docs/current/AAOS-OPEN-WORK-REGISTER-20261001.md row",
                key=lambda r=row: r["key"], detail=lambda d=detail: d))
        else:
            lines.append(_discipline.insufficient(
                f"**{row['key']}** 有 {len(bad)} 条引用未解析：{detail}",
                reason="cited path not found at that exact location; a same-named file elsewhere "
                       "is not accepted as a substitute"))
    lines.append(_discipline.computed(
        "未解析引用合计 {count} 条。", "the per-row verdicts above", count=lambda: unresolved_total))

    lines.append("## 切片覆盖（由目录名匹配推导，不沿用他片结论）")
    slices = [f"p{n:02d}" for n in range(1, 13)]
    covered = [s for s in slices if any(s in name for name in claims)]
    uncovered = [s for s in slices if s not in covered]
    lines.append(_discipline.computed(
        "有本地回执目录的切片 {count} 个：{names}", "the evidence directory listing above",
        count=lambda: len(covered), names=lambda: ", ".join(covered) or "-"))
    if uncovered:
        lines.append(_discipline.computed(
            "无匹配回执目录的切片：{names} — 记为 UNVERIFIED",
            "the evidence directory listing above", names=lambda: ", ".join(uncovered)))

    for text, source in (extra_claims or []):
        lines.append(_discipline.claim(text, source))

    counts = _discipline.tally([item for item in lines if isinstance(item, _discipline.Item)])
    # The unmarked count is measured from the render at this point, not asserted to be zero;
    # check_written re-reads the written bytes afterwards and fails the run on anything left.
    unmarked_now = len(_discipline.scan_unmarked("\n".join(_discipline.render(lines))))
    lines.append(_discipline.computed(
        "本报告的输出构成：COMPUTED {computed} 行、CLAIM {claim} 行、INSUFFICIENT-EVIDENCE "
        "{insufficient} 行，未标记结论 {unmarked} 行；落盘后还会按写出的字节再查一次。",
        "the items this run emitted, including this line",
        # +1 because this tally line is itself a COMPUTED emission and is appended here;
        # leaving it out made the report understate its own count, which the test catches.
        computed=lambda: counts[computed] + 1, claim=lambda: counts[_discipline.CLAIM],
        insufficient=lambda: counts[_discipline.INSUFFICIENT],
        unmarked=lambda: unmarked_now))
    return _discipline.render(lines)


def default_output(repo: Path) -> Path:
    run_root = os.environ.get("ARCHEAXIS_RUN_ROOT", "").strip()
    base = Path(run_root) if run_root else repo / ".project-local" / "artifacts" / "audit"
    return base / "P-COMPLETION-AUDIT.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--evidence-root", type=Path,
                        default=Path(os.environ.get("ARCHEAXIS_PROJECT_LOCAL", str(ROOT / ".project-local")))
                        / "artifacts" / "evidence")
    parser.add_argument("--register", type=Path,
                        default=ROOT / "docs" / "current" / "AAOS-OPEN-WORK-REGISTER-20261001.md")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--today", default=date.today().isoformat())
    args = parser.parse_args(argv)

    output = args.output or default_output(ROOT)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = build_report(repo=ROOT, evidence_root=args.evidence_root,
                         register_path=args.register, today=args.today)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    try:
        _discipline.check_written(output)
    except _discipline.DisciplineViolation as error:
        print(str(error), file=sys.stderr)
        return 1
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
