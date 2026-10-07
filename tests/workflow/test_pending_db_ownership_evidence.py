"""The ownership proof for the 28 pending databases rests on one checkable link.

A cleanup review left 28 databases at `OWNERSHIP_PROOF_INSUFFICIENT`, having looked only at their
paths and sizes. Reading their *contents* identifies the producer: every row is synthetic test
vocabulary, and that vocabulary appears in exactly one file — the vector migration tests. The link
between "vocabulary found in the database" and "producer identified" is what makes the claim
ownership rather than resemblance, so it is the link this test holds. If the vocabulary moves or
those tests are rewritten, the identification stops being valid and this fails instead of the
document quietly going stale.

It deliberately does not assert anything about the databases themselves: they live under an ignored
run root that may be cleaned at any time, and a test that depends on local scratch would fail for
the wrong reason.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PRODUCER = REPO / "tests" / "test_migration_runner.py"
EVIDENCE = REPO / "docs" / "current" / "AAOS01-PENDING-DB-OWNERSHIP-EVIDENCE-20261006.md"

# Vocabulary read out of the databases themselves: fixture content, fixture object ids and the
# migration owner those runs recorded.
VOCABULARY = (
    "verified candidate content",
    "previous active content",
    "foreign-active",
    "foreign-candidate",
    "foreign-backup",
)

# The test functions whose tmp_path directories the databases are named after.
PRODUCING_TESTS = (
    "test_vector_owner_rebuilds_from_canonical_rows_and_rolls_back",
    "test_vector_rollback_rejects_corrupted_provenance_before_unrelated_tables_touch",
    "test_vector_rollback_rejects_post_apply_active_drift_and_allows_retry",
    "test_vector_rollback_rolled_back_provenance_failure_keeps_applied_state",
    "test_vector_apply_blocks_ordinary_active_writer_during_activation",
)


def python_files() -> list[Path]:
    """Python files that could *produce* such a database.

    This checker is excluded because it names the vocabulary in order to look for it; counting it
    as a producer would make the search trivially find two carriers and prove nothing.
    """
    here = Path(__file__).resolve()
    found: list[Path] = []
    for root in ("tests", "shared", "app", "services", "scripts"):
        base = REPO / root
        if base.is_dir():
            found.extend(path for path in base.rglob("*.py")
                         if path.is_file() and path.resolve() != here)
    return found


def test_the_recorded_vocabulary_appears_only_in_the_identified_producer() -> None:
    carriers = [path for path in python_files()
                if any(term in path.read_text(encoding="utf-8", errors="surrogateescape")
                       for term in VOCABULARY)]
    assert carriers == [PRODUCER], (
        "the ownership identification assumes this vocabulary identifies one producer; "
        f"found it in {[str(path.relative_to(REPO)) for path in carriers]}")


def test_every_database_is_named_after_a_test_that_still_exists() -> None:
    producer = PRODUCER.read_text(encoding="utf-8")
    for name in PRODUCING_TESTS:
        assert f"def {name}(" in producer, (
            f"{name} no longer exists, so the databases named after it can no longer be attributed")


def test_the_evidence_record_states_the_producer_and_the_open_decision() -> None:
    text = EVIDENCE.read_text(encoding="utf-8")
    assert "tests/test_migration_runner.py" in text
    for name in PRODUCING_TESTS:
        assert name in text, name
    # The record must not present the deletion as already decided: the prior verdict on this batch
    # was KEEP, and only the owner can overturn it.
    assert "KEEP" in text and "业主" in text
    assert "不自行删除" in text
