from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs" / "current" / "AXR_060_COMPLETION_AUDIT_2026-08-23.md"
TASK_IDS = tuple(
    f"AXR-060-{number:03d}"
    for number in (
        1,
        2,
        3,
        101,
        102,
        103,
        201,
        202,
        203,
        204,
        301,
        302,
        303,
        304,
        401,
        402,
        403,
        404,
        501,
        502,
        503,
        601,
        602,
        603,
        604,
        701,
        702,
        703,
        704,
    )
)


def test_axr060_audit_covers_every_task_and_release_blocker_once() -> None:
    text = AUDIT.read_text(encoding="utf-8")

    found_tasks = re.findall(r"AXR-060-\d{3}", text)
    assert sorted(found_tasks) == sorted(TASK_IDS)
    for blocker in range(1, 13):
        assert text.count(f"B{blocker:02d}") == 1


def test_axr060_audit_keeps_release_and_product_completion_separate() -> None:
    text = AUDIT.read_text(encoding="utf-8")

    assert "整体结论：PARTIAL" in text
    assert "RELEASE_PUBLISHED：PASS" in text
    assert "不等于" in text
    assert "NOT_EXECUTED" in text


def _declared_r5_source_objects() -> set[str]:
    """Source blob identity is not a claim that its commit was released."""
    reuse = json.loads((ROOT / 'docs/current/R5-M0-REUSE.json').read_text(encoding='utf-8'))
    base = reuse['baseline_sha']

    def git(*args: str) -> str:
        return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()

    assert re.fullmatch('[0-9a-f]{40}', base)
    assert git('cat-file', '-t', base) == 'commit'
    declared = {base, git('rev-parse', f'{base}^{{tree}}')}
    state = json.loads((ROOT / 'docs/current/R5-STATE.json').read_text(encoding='utf-8'))
    main_snapshot = state['baseline_local_main_sha']
    assert re.fullmatch('[0-9a-f]{40}', main_snapshot)
    assert git('cat-file', '-t', main_snapshot) == 'commit'
    declared.add(main_snapshot)
    # Execution receipts identify tested source, not a release. Require an
    # explicit label and a real commit in this checkout's history.
    execution = (ROOT / 'docs/current/R5-EXECUTION.md').read_text(encoding='utf-8')
    for sha in re.findall(r'`tested-source-sha:([0-9a-f]{40})`', execution):
        assert git('cat-file', '-t', sha) == 'commit'
        subprocess.run(
            ['git', '-C', str(ROOT), 'merge-base', '--is-ancestor', sha, 'HEAD'],
            check=True,
        )
        declared.add(sha)

    def visit(value):
        if isinstance(value, dict):
            if value.get('head_blob'):
                path, sha = value['path'], value['head_blob']
                assert re.fullmatch('[0-9a-f]{40}', sha)
                assert git('cat-file', '-t', sha) == 'blob'
                assert git('rev-parse', f'{base}:{path}') == sha
                declared.add(sha)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(reuse)
    disposition = json.loads((ROOT / 'docs/current/R5-PATH-DISPOSITION.json').read_text(encoding='utf-8'))
    measured = disposition['measured']['measured_at_commit']
    assert re.fullmatch('[0-9a-f]{40}', measured)
    assert git('cat-file', '-t', measured) == 'commit'
    declared.add(measured)
    # Historical upstream pin has its own repository and qualification limits.
    # Do not pretend it is a local Git object or a published ArcheAxis commit.
    upstream = (ROOT / 'docs/integrations/DEEPTUTOR_PRODUCT_BASE.md').read_text(encoding='utf-8')
    pins = re.findall(r'^- Commit: `([0-9a-f]{40})`$', upstream, re.MULTILINE)
    assert len(pins) == 1
    declared.update(pins)
    return declared


def test_tracked_current_surfaces_only_reference_declared_release_delta_or_source_objects() -> None:
    releases = [
        json.loads(
            (ROOT / "reports" / "release" / version / "release-evidence.json").read_text(
                encoding="utf-8"
            )
        )
        for version in ("v0.6.9", "v0.6.10", "v0.6.11")
    ]
    allowed_shas = {
        value
        for release in releases
        for value in (
            release["source"]["commit_sha"],
            release["source"].get("tree_sha"),
        )
        if isinstance(value, str)
    }
    delta = (ROOT / "docs" / "current" / "AXR_060_POST_RELEASE_DELTA_2026-08-24.md").read_text(
        encoding="utf-8"
    )
    delta_release = releases[-2]["source"]
    assert delta_release["commit_sha"] in delta
    assert delta_release["tree_sha"] in delta
    declared_delta_shas = set(re.findall(r"`main@([0-9a-f]{40})`", delta))
    assert declared_delta_shas
    allowed_shas.update(declared_delta_shas)
    r2_reality = (
        ROOT / "docs" / "current" / "AXR_CURRENT_REALITY_2026-08-27.md"
    ).read_text(encoding="utf-8")
    declared_qualification_shas = set(
        re.findall(r"(?:Qualification|Release) baseline[^\n]*`([0-9a-f]{40})`", r2_reality)
    )
    assert declared_qualification_shas
    allowed_shas.update(declared_qualification_shas)
    current_reality = (
        ROOT / "docs" / "current" / "CURRENT_REALITY_2026-09-01.md"
    ).read_text(encoding="utf-8")
    declared_current_shas = set(
        re.findall(r"`(?:main|origin/main)@([0-9a-f]{40})`", current_reality)
    )
    declared_current_shas.update(
        re.findall(r"`historical-sha:([0-9a-f]{40})`", current_reality)
    )
    assert declared_current_shas
    allowed_shas.update(declared_current_shas)
    allowed_shas.update(_declared_r5_source_objects())
    surfaces = [ROOT / "SYSTEM_BOUNDARY.md"]
    surfaces.extend((ROOT / "docs" / "current").glob("*"))
    surfaces.extend((ROOT / "reports" / "current").glob("*"))
    found: set[str] = set()
    for path in surfaces:
        if not path.is_file():
            continue
        found.update(re.findall(r"\b[0-9a-f]{40}\b", path.read_text(encoding="utf-8")))

    assert found <= allowed_shas
    assert sorted(path.name for path in (ROOT / "reports" / "current").iterdir()) == [
        "README.md"
    ]
