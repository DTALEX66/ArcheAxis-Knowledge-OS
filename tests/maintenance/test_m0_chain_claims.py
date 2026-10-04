"""The M0 chain's own numbers, so the contract's claim about it cannot drift silently.

The current contract declares 28 synthetic stages. That count is checkable from the probe
source without running it, which matters because the probe needs a built Core, a scheduler
interpreter with `fsrs`, and the legacy database present - none of which is guaranteed where the
document is read.

It also records why the chain's final stage sits next to a frozen boundary: the stage migrates a
**copy** and asserts the original is untouched, so it demonstrates the capability without
migrating user data. That distinction is easy to lose and is asserted here.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROBE = REPO / "scripts/probes/m0_full_loop_smoke.py"
CONTRACT = REPO / "docs/current/AAOS-PRODUCTION-HTTP-CONTRACT-20261001.md"
GAP_MAP = REPO / "docs/current/DSH-BACKEND-GAP-MAP-20260927.md"


def stage_names() -> list[str]:
    return re.findall(r'stage\(\s*"([^"]+)"', PROBE.read_text(encoding="utf-8"))


def test_the_probe_records_one_uniquely_named_stage_per_step():
    names = stage_names()
    assert names, "the probe records no stages; its stage helper changed shape"
    duplicates = sorted({name for name in names if names.count(name) > 1})
    assert not duplicates, f"the probe records a stage twice: {duplicates}"


def test_the_contract_quotes_the_stage_count_the_probe_actually_has():
    names = stage_names()
    contract = CONTRACT.read_text(encoding="utf-8")
    claim = re.search(r"Current synthetic journey stages: \*\*(\d+)\*\*", contract)
    assert claim, "the contract no longer declares its current synthetic stage count"
    assert int(claim.group(1)) == len(names)



def test_the_gap_maps_older_count_is_not_the_current_one():
    """The gap map lists 26 rows; the probe added pre-restart and persisted-answer stages.

    This is recorded as a fact rather than fixed, because the gap map is dated navigation material
    with its own tested commit and the contract is the current authority.
    """
    names = stage_names()
    assert len(names) == 28, (
        "if the probe's stage count changes, the contract's claim and this note both need updating")
    assert "pre_restart_learning_state" in names, (
        "the extra stage relative to the gap map is the pre-restart baseline")
    gap = GAP_MAP.read_text(encoding="utf-8")
    assert "M0 26 阶段" in gap or "26 阶段" in gap, (
        "the gap map's stage count changed; the note above is now wrong")


def test_the_legacy_stage_runs_on_a_copy_and_checks_the_original_is_untouched():
    """The stage that sits closest to the frozen boundary, asserted from the probe source."""
    source = PROBE.read_text(encoding="utf-8")
    assert "shutil.copyfile(LEGACY, legacy_copy)" in source, (
        "the legacy stage must operate on a copy, never on the source database")
    assert "original_before == original_after" in source, (
        "the legacy stage must prove the original is untouched by comparing its digest")
    assert "migrator.migrate(legacy_copy" in source, (
        "the migration must be pointed at the copy")
    # and the contract must say so, because a reader will otherwise read "legacy migration ok" as
    # having migrated user data
    contract = CONTRACT.read_text(encoding="utf-8")
    assert "temporary copy" in contract and "original_untouched" in contract, (
        "the contract must explain that this stage runs on a copy and leaves the source alone")
    assert "NOT_EXECUTED" in contract, "the frozen boundary must still be stated"
