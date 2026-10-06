"""The dependency-vulnerability scan must stay pinned, actually wired, and able to fail.

`pip-audit` (Apache-2.0, 2.10.1) is absorbed as a CI step over the hash-pinned export of the lock.
Two failure modes are worth pinning here rather than trusting: a step that quietly cannot fail
(`continue-on-error`, or a pipe whose exit code comes from `tee`), and a step that waives findings
by name (`--ignore-vuln`) so the gate survives only as long as nobody re-audits it.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"
PINNED_VERSION = "2.10.1"


def scan_step() -> str:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    start = workflow.index("- name: Dependency vulnerability scan")
    end = workflow.index("- name: ", start + 10)
    return workflow[start:end]


def test_the_scanner_is_pinned_and_strict() -> None:
    step = scan_step()
    assert f"pip-audit=={PINNED_VERSION}" in step, "an unpinned scanner drifts with the index"
    assert f"--from pip-audit=={PINNED_VERSION} pip-audit" in step
    assert "--strict" in step, "without --strict an unreachable advisory source reads as clean"


def test_the_step_is_enforcing_and_cannot_swallow_its_exit_code() -> None:
    step = scan_step()
    assert "continue-on-error" not in step, (
        "a report-only security step is documentation, not a gate"
    )
    assert "set -o pipefail" in step, (
        "the runner shell is `bash -e` without pipefail, so `pip-audit | tee` would report tee's "
        "status (always 0) and the step could never fail on a real finding"
    )


def test_findings_are_not_waived_by_name() -> None:
    # Scoped to the command itself: the prose around it is allowed to name the flag it forbids.
    command = scan_step().split("run: |", 1)[1]
    assert "--ignore-vuln" not in command, (
        "an accepted vulnerability must be fixed or recorded as an open gap, not silently ignored "
        "in the pipeline where nobody has to read it"
    )


def test_the_audit_covers_the_locked_ci_environment() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    step = scan_step()
    assert '--requirement "$artifacts/locked-ci.txt"' in step, (
        "auditing pyproject ranges instead of the lock would miss the transitive packages that "
        "actually get installed"
    )
    export = workflow[: workflow.index("- name: Dependency vulnerability scan")]
    assert "uv export --frozen --only-group ci" in export, (
        "the audited requirement set must come from the same frozen lock the job installs"
    )
