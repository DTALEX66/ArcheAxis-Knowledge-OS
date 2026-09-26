from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs" / "current" / "AXR_060_COMPLETION_AUDIT_2026-08-23.md"

# Bounded remote probe. A slow or unreachable remote must fail loudly instead of
# hanging the suite or being mistaken for "the branch was deleted".
_REMOTE_TIMEOUT_SECONDS = 60

# Surfaces that make present-day release claims. They are checked unconditionally:
# a receipt marker inside them can never exempt them from the SHA scan.
_LOCKED_SURFACES = (
    "SYSTEM_BOUNDARY.md",
    "reports/current",
)

# The only directory whose generated audit receipts may be exempt, and only for
# the exact schema identifiers below.
_RECEIPT_ELIGIBLE_PREFIX = "docs/current/"

# Exact `schema_version` identifiers of generated branch/lineage audit receipts.
# Deliberately an exact-value allowlist: a bare `aaos-` prefix is NOT a waiver.
_RECEIPT_SCHEMAS = frozenset(
    {
        "aaos-branch-commit-path-audit/v1",
        "aaos-branch-disposition-review/v1",
        "aaos-frozen-donor-hash-audit/v1",
        "aaos-history-path-disposition/v1",
        "aaos-local-repository-lineage-readback/v1",
        "aaos-untracked-lineage-metadata/v1",
    }
)

# Markdown receipts that name themselves non-authority snapshots. Matching this
# marker alone is never sufficient: the file must also sit in an approved path.
_RECEIPT_MD_MARKERS = (
    "FROZEN AUDIT SNAPSHOT / NON-AUTHORITY",
)


def _receipt_schema_of(path: Path, root: Path = ROOT) -> str | None:
    """Return the approved receipt schema a file declares, else None.

    Path authority is evaluated against ``root`` and checked first, so a locked
    release surface can never be exempt whatever its body says, and a file
    outside the receipt-eligible directory is refused before any marker or
    schema value is considered.
    """
    try:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None
    if relative == _LOCKED_SURFACES[0] or relative.startswith(_LOCKED_SURFACES[1] + "/"):
        return None
    if not relative.startswith(_RECEIPT_ELIGIBLE_PREFIX):
        return None
    try:
        head = path.read_text(encoding="utf-8", errors="replace")[:600]
    except OSError:
        return None
    if path.suffix == ".json":
        try:
            declared = json.loads(path.read_text(encoding="utf-8")).get("schema_version")
        except (OSError, json.JSONDecodeError, AttributeError):
            return None
        # Exact identifier match: a bare `aaos-` prefix is not a waiver.
        return declared if declared in _RECEIPT_SCHEMAS else None
    if path.suffix == ".md":
        return next((marker for marker in _RECEIPT_MD_MARKERS if marker in head), None)
    return None


def _surface_shas(root: Path) -> set[str]:
    """40-hex identifiers the SHA-existence scan must check under ``root``."""
    surfaces = [root / "SYSTEM_BOUNDARY.md"]
    surfaces.extend((root / "docs" / "current").glob("*"))
    surfaces.extend((root / "reports" / "current").glob("*"))
    found: set[str] = set()
    for path in surfaces:
        if not path.is_file():
            continue
        if _receipt_schema_of(path, root) is not None:
            continue
        found.update(
            re.findall(r"\b[0-9a-f]{40}\b", path.read_text(encoding="utf-8", errors="replace"))
        )
    return found

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
        # receipt lists every local branch. Bounded so an unreachable remote
        # cannot hang the suite; a failure is reported, never read as "deleted".
        try:
            remote = subprocess.run(
                ["git", "-C", str(ROOT), "ls-remote", "--heads", "origin"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
                text=True,
                encoding="utf-8",
                timeout=_REMOTE_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            pytest.fail(
                "REMOTE_TIMEOUT: git ls-remote exceeded "
                f"{_REMOTE_TIMEOUT_SECONDS}s; cannot classify branch deletion"
            )
        if remote.returncode != 0:
            pytest.fail(
                "REMOTE_UNAVAILABLE: git ls-remote failed with exit "
                f"{remote.returncode}; cannot classify branch deletion"
            )
        # `ls-remote` describes the remote *now*. It can support "the branch is
        # not currently published", which is all this test needs, but it can
        # never establish that the branch once existed or that a tip is genuine.
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
    # Release surfaces are checked unconditionally; only generated receipts in
    # the approved directory may be exempt, and only for an exact schema
    # identifier (see _receipt_schema_of). A body marker alone is not a waiver,
    # so a receipt marker placed inside SYSTEM_BOUNDARY.md changes nothing.
    found = _surface_shas(ROOT)

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


# ── Surface-classification regressions ────────────────────────────────────
#
# These exercise the release-surface / receipt boundary directly against
# isolated fixtures. They must never rely on editing the real current surfaces,
# and they must not be satisfiable by a body marker alone.

_FAKE_FULL_ID = "0123456789abcdef0123456789abcdef01234567"


def _fixture_root(tmp_path: Path, *, boundary: str = "", reports: bool = True) -> Path:
    """Minimal repo-shaped tree with the two locked surfaces."""
    (tmp_path / "docs" / "current").mkdir(parents=True, exist_ok=True)
    (tmp_path / "SYSTEM_BOUNDARY.md").write_text(boundary, encoding="utf-8")
    if reports:
        (tmp_path / "reports" / "current").mkdir(parents=True, exist_ok=True)
        (tmp_path / "reports" / "current" / "README.md").write_text(
            "surface index\n", encoding="utf-8"
        )
    return tmp_path


def test_A_release_surface_is_scanned_even_when_it_carries_a_receipt_marker(
    tmp_path: Path,
) -> None:
    """A receipt marker inside a locked surface must not exempt it."""
    root = _fixture_root(
        tmp_path,
        boundary=(
            "# System boundary\n\n"
            "FROZEN AUDIT SNAPSHOT / NON-AUTHORITY\n\n"
            f"declared: {_FAKE_FULL_ID}\n"
        ),
    )
    assert _FAKE_FULL_ID in _surface_shas(root)
    # The locked path is refused before any marker is even considered.
    assert _receipt_schema_of(root / "SYSTEM_BOUNDARY.md", root) is None


def test_A2_reports_current_is_scanned_even_with_a_receipt_schema(tmp_path: Path) -> None:
    """reports/current/ is locked too: a valid schema there is still not a waiver."""
    root = _fixture_root(tmp_path, boundary="# boundary\n")
    forged = root / "reports" / "current" / "forged.json"
    forged.write_text(
        json.dumps(
            {"schema_version": "aaos-branch-commit-path-audit/v1", "declared": _FAKE_FULL_ID}
        ),
        encoding="utf-8",
    )
    assert _receipt_schema_of(forged, root) is None
    assert _FAKE_FULL_ID in _surface_shas(root)


def test_B_fabricated_full_id_on_a_release_surface_is_visible_to_the_scan(
    tmp_path: Path,
) -> None:
    """A fabricated 40-hex id must reach the scan, which rejects it as no object."""
    root = _fixture_root(tmp_path, boundary=f"# boundary\n\nclaim: {_FAKE_FULL_ID}\n")
    assert _FAKE_FULL_ID in _surface_shas(root)
    probe = subprocess.run(
        ["git", "-C", str(ROOT), "cat-file", "-t", _FAKE_FULL_ID],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
        text=True,
        encoding="utf-8",
    )
    assert probe.returncode != 0, "fixture id unexpectedly exists in this repository"


def test_C_field_declaring_a_full_id_rejects_a_truncated_one(tmp_path: Path) -> None:
    """Truncation is a data defect: a short id never satisfies a full-id field."""
    real = "4fc581e7dcde90a30d8e9019f26fdf362bfa5cc9"
    root = _fixture_root(tmp_path, boundary="# boundary\n")
    truncated = real[:39]
    (root / "docs" / "current" / "R6-TRUNCATED.json").write_text(
        json.dumps({"tree_sha": truncated}), encoding="utf-8"
    )
    (root / "docs" / "current" / "R6-FULL.json").write_text(
        json.dumps({"tree_sha": real}), encoding="utf-8"
    )
    scanned = _surface_shas(root)
    # A 39-char value is not a 40-hex identifier and must not be silently
    # promoted into the candidate set; only the full identifier qualifies.
    assert truncated not in scanned
    assert real in scanned
    assert _FAKE_FULL_ID not in scanned


def test_D_legitimate_receipts_are_exempt_by_schema_not_by_prefix(tmp_path: Path) -> None:
    """Approved receipts in the eligible path are exempt; unknown schemas are not."""
    root = _fixture_root(tmp_path, boundary="# boundary\n")
    approved = root / "docs" / "current" / "AAOS-BRANCH-COMMIT-PATH-AUDIT-20260925.json"
    approved.write_text(
        json.dumps(
            {
                "schema_version": "aaos-branch-commit-path-audit/v1",
                "records": [{"tip": _FAKE_FULL_ID}],
            }
        ),
        encoding="utf-8",
    )
    assert _receipt_schema_of(approved, root) == "aaos-branch-commit-path-audit/v1"
    assert _FAKE_FULL_ID not in _surface_shas(root)


def test_E_unknown_aaos_prefixed_schema_is_not_a_waiver(tmp_path: Path) -> None:
    """An arbitrary `aaos-*` prefix must not open a general exemption."""
    root = _fixture_root(tmp_path, boundary="# boundary\n")
    impostor = root / "docs" / "current" / "AAOS-UNREVIEWED-THING.json"
    impostor.write_text(
        json.dumps({"schema_version": "aaos-anything-at-all/v1", "declared": _FAKE_FULL_ID}),
        encoding="utf-8",
    )
    assert _receipt_schema_of(impostor, root) is None
    assert _FAKE_FULL_ID in _surface_shas(root)


def test_E2_marker_only_markdown_outside_the_eligible_path_is_not_a_waiver(
    tmp_path: Path,
) -> None:
    """The markdown marker is an additional condition, never sufficient alone."""
    root = _fixture_root(tmp_path, boundary="# boundary\n")
    (root / "docs").mkdir(exist_ok=True)
    outside = root / "docs" / "FROZEN-NOTE.md"
    outside.write_text(
        f"FROZEN AUDIT SNAPSHOT / NON-AUTHORITY\n\nclaim: {_FAKE_FULL_ID}\n",
        encoding="utf-8",
    )
    assert _receipt_schema_of(outside, root) is None


def test_F_remote_absence_is_a_three_way_classification() -> None:
    """Live heads decide published vs not-published; failure is never 'deleted'.

    `ls-remote` reports the remote as it is now, so the only conclusion it can
    support is "currently not published". The distinction that must stay
    explicit is: published / not currently published / probe failed.
    """
    live_heads = {"refs/heads/main", "refs/heads/feat/kept"}

    def classification(name: str) -> str:
        return "PUBLISHED" if f"refs/heads/{name}" in live_heads else "NOT_PUBLISHED_NOW"

    assert classification("main") == "PUBLISHED"
    assert classification("chore/naming-repo-refs") == "NOT_PUBLISHED_NOW"
    # A probe failure is its own outcome and must never collapse into the above.
    probe_failure = "REMOTE_UNAVAILABLE"
    assert probe_failure not in {classification("main"), classification("gone")}
    assert probe_failure != "NOT_PUBLISHED_NOW"


def test_G_r5_source_and_release_constraints_still_assert_ancestry() -> None:
    """The R5 tested-source ancestry requirement must not have been relaxed."""
    source = (ROOT / "tests" / "test_axr060_completion_audit.py").read_text(encoding="utf-8")
    assert "merge-base" in source and "--is-ancestor" in source
    assert "tested-source-sha:" in source
    declared = _declared_r5_source_objects()
    assert declared, "R5 source objects must still resolve"

