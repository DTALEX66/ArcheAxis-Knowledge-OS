# Phase 5 P0.1 Governed Candidate Checkpoint

**Date:** 2026-07-19
**Branch:** `agent/phase5-research-knowledge-governance`
**Main baseline:** `752997d7f712655ef73e99c657111ebfaa45dcf5`
**Execution policy:** manual GPT-only; sleep mode paused; DeepSeek/DP is not used.

## Delivered checkpoint

P0.1 now has an operator-owned `knowledge.sqlite` governance boundary for persisted, quarantined `ResearchPackageV1`:

```text
persisted package strict reload
→ human-review decision ledger
→ candidate-only KnowledgeUnit / Relation materialization
→ replay-safe approval, rejection, and deprecation paths
```

Implemented controls:

- `knowledge.sqlite` is owned by `MigrationOperator`; direct migration calls are capability-guarded.
- Candidate projections do not write legacy `graph_entities` or `graph_relations`.
- Approval, rejection, and deprecation decisions preserve package/source/source-group/claim/evidence/finding provenance.
- Approval/rejection/deprecation replay compares request semantics and rejects conflicts.
- Approval replay rejects tampered relation claim provenance.
- Candidate decision/materialization writes require `knowledge.sqlite` applied operator provenance.
- SQLite triggers reject `UPDATE` and `DELETE` against `knowledge_review_decisions_v1`.
- Rollback remains whole-file, fingerprint-gated, checkpointed-WAL-only, and fail-closed after data drift.

## Verified local evidence

Before the final two security remediation slices, the complete local gates returned:

```text
Root pytest: 514 passed, 2 skipped
Knowledge Base: 38 passed
Integration: 13 passed
Full Ruff: passed
Architecture guard: passed
git diff --check: passed
```

The last two remediation slices each have targeted RED → GREEN evidence:

- `.hermes/evidence/2026-07-19_phase5-p11-governance-readback-expansion.md`
- decision-ledger immutability: RED `1 failed`; GREEN migration suite `3 passed`.
- operator provenance: RED `1 failed`; GREEN targeted suite `4 passed`.

Run the complete local gate again after the remaining blocker is fixed; do not treat this checkpoint as release-ready.

## Remaining P0.1 blocker

`app/facades/knowledge.py` currently accepts a caller-provided `reviewer_principal` so long as it begins with `human:`. That is not a server-owned authenticated identity. Before P0.1 can be completed, refactor all three mutation paths to derive reviewer identity from the existing authenticated/authorized principal in `shared.auth` / request middleware. Add tests proving caller-supplied `human:` labels cannot authorize approval, rejection, or deprecation.

## Next implementation sequence

1. Write RED tests for forged reviewer identity and unauthorized authenticated roles.
2. Introduce a server-owned review principal derived from validated auth identity; do not trust caller-supplied reviewer labels.
3. Route approval/reject/deprecate only through that principal and preserve immutable ledger semantics.
4. Re-run targeted RED/GREEN, Root, Knowledge Base, Integration, full Ruff, Architecture Guard, and diff checks.
5. Freeze the exact tree and perform GPT-only read-only self-review.
6. Commit/push the completed P0.1 branch and verify exact-SHA CI before beginning P0.2.

## Explicit prohibitions

- Do not write P0.1 materializations to legacy graph tables.
- Do not auto-promote candidates to verified/approved truth.
- Do not relax offline WAL/fingerprint rollback safety.
- Do not advance P0.2/P0.3 while the reviewer-authentication blocker remains.
- Do not restart sleep mode or DeepSeek/DP background work without explicit user direction.
