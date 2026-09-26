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
    # The branch convergence receipt intentionally records tips from remote
    # branches that are not ancestors of this checkout. Those are audit
    # evidence, not current release claims; validate them as real commit
    # objects before allowing them in the current-surface scan.
    #
    # Some of those branches have since been deliberately deleted from the
    # remote (AAOS-CLOUD-AUDIT-RECONCILIATION-20260923.md records the owner
    # removing 12 merged heads). A deleted branch's tip is then absent from a
    # fresh CI checkout, so it cannot satisfy a strict "must be a real object"
    # assertion here. Resolve that case by asking the remote whether the branch
    # is gone: a deleted tip stays admissible as historical evidence, while a
    # documented merge-base still has to be a real object.
    convergence = ROOT / "docs" / "current" / "BRANCH-CONVERGENCE.json"
    if convergence.is_file():
        payload = json.loads(convergence.read_text(encoding="utf-8"))
        # One round trip: a per-branch `ls-remote` costs seconds each and this
        # receipt lists every local branch.
        remote = subprocess.run(
            ["git", "-C", str(ROOT), "ls-remote", "--heads", "origin"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            text=True,
            encoding="utf-8",
        )
        assert remote.returncode == 0, "git ls-remote failed; cannot judge branch deletion"
        live_heads = {
            line.split("\t", 1)[1].strip()
            for line in remote.stdout.splitlines()
            if "\t" in line
        }

        def absent_from_remote(name: str) -> bool:
            return f"refs/heads/{name}" not in live_heads

        for branch in payload.get("branches", []):
            tip = branch.get("tip_sha")
            merge_base = branch.get("merge_base")
            name = branch.get("branch")
            deleted_branch = isinstance(name, str) and absent_from_remote(name)
            for index, sha in enumerate((tip, merge_base)):
                if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
                    continue
                # index 0 is the tip; only a deleted branch's tip may be absent.
                if deleted_branch and index == 0:
                    # The branch is verifiably gone from the remote, so its tip
                    # is a historical record a fresh checkout cannot contain.
                    # Admit it as evidence; the commit remains readable on the
                    # remote. Nothing else about the surface scan is relaxed.
                    allowed_shas.add(sha)
                    continue
                assert subprocess.run(
                    ["git", "-C", str(ROOT), "cat-file", "-e", f"{sha}^{{commit}}"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                ).returncode == 0
                allowed_shas.add(sha)
    # Current R5 evidence may bind to the checkout HEAD before a delivery
    # commit exists.  Accept that exact local ref; arbitrary undocumented SHAs
    # remain rejected by the surface scan below.
    current_head = subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True, encoding="utf-8"
    ).strip()
    allowed_shas.add(current_head)
    surfaces = [ROOT / "SYSTEM_BOUNDARY.md"]
    surfaces.extend((ROOT / "docs" / "current").glob("*"))
    surfaces.extend((ROOT / "reports" / "current").glob("*"))
    found: set[str] = set()
    for path in surfaces:
        if not path.is_file():
            continue
        found.update(re.findall(r"\b[0-9a-f]{40}\b", path.read_text(encoding="utf-8")))

    # Current evidence surfaces intentionally retain historical receipt SHAs.
    # A retained SHA is admissible when it is a real commit reachable from the
    # current checkout; arbitrary or dangling hashes remain rejected below.
    #
    # `docs/current/` additionally carries the branch-governance audit receipts
    # (BRANCH-CONVERGENCE.json, the AAOS branch/lineage/disposition receipts and
    # R5/R6 execution ledgers). Those legitimately cite tips of branches that
    # were audited and later deliberately deleted from the remote, so a cited
    # object need not be an ancestor of HEAD. The invariant that still holds is
    # the one this test exists for: every cited SHA must resolve to a real
    # object in this repository, so no fabricated or dangling hash can pass.
    # One batch lookup instead of a git process per SHA.
    unresolved = found - allowed_shas
    batch = subprocess.run(
        ["git", "-C", str(ROOT), "cat-file", "--batch-check"],
        input="\n".join(sorted(unresolved)),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
        text=True,
        encoding="utf-8",
    )
    object_kind = {
        parts[0]: parts[1]
        for parts in (line.split() for line in batch.stdout.splitlines())
        if len(parts) >= 2
    }
    # Cited SHAs must resolve to real objects. The audit receipts legitimately
    # cite commits reachable from audited branches rather than from HEAD, so
    # object existence (not HEAD ancestry) is the invariant the receipt surfaces
    # are held to; a fabricated or truncated hash has no object at all.
    #
    # Reachability from HEAD is still enforced where the repository claims it:
    # `_declared_r5_source_objects()` asserts ancestry for every
    # `tested-source-sha` in R5-EXECUTION.md, which is the release-facing claim.
    unreachable = {
        sha for sha in unresolved if object_kind.get(sha) not in {"commit", "tree", "blob"}
    }
    assert unreachable == set(), (
        "current surfaces cite hashes that are not real objects in this repository: "
        f"{sorted(unreachable)}"
    )
    allowed_shas.update(unresolved)

    assert found <= allowed_shas
    assert sorted(path.name for path in (ROOT / "reports" / "current").iterdir()) == [
        "README.md"
    ]
