# v0.1 domain contract

## Five aggregate roots

- Workspace: identity, schema version, location policy and export history.
- Source: immutable RawAsset references, SourceRevision and versioned conversion status.
- KnowledgeItem: human revisions or machine candidates, EvidenceLinks and immutable ReviewDecisions.
- LearningItem: current scheduling state derived from immutable LearningEvents.
- Job: requested capability work, attempts, timeout, failure and output receipts.

RawAsset, Anchor, ReviewDecision, LearningEvent, CommandReceipt, ExportManifest and search rows are not aggregate roots. They are immutable objects, values, receipts or rebuildable projections; treating them as large transaction roots would create unnecessary locking.

## Knowledge types

`PERSONAL_DEFINITION | NOTE | OBSERVATION | OPINION | QUESTION | HYPOTHESIS |
RUMOR_REPORT | FORECAST | FACTUAL_CLAIM` are the complete Contract v1 set and
are all storable. Evidence status never controls whether the item may exist.
Law, standards and policies are scoped `FACTUAL_CLAIM` revisions bound to
issuer, jurisdiction, version and effective dates, not extra knowledge types.

`KnowledgeItem` is the user-visible container. A `KnowledgeRevision` may contain
zero, one or many separately testable `AtomicClaim` objects. Notes and personal
definitions do not have to be forced into factual claims.

## Independent assessment axes

- provenance_status
- transformation_quality
- review_status
- evidence_status
- test_status
- rumor_status
- forecast_status
- use_status
- human_decision (append-only action, not a status)

The minimum state vocabularies are defined in
`docs/architecture/evidence-v02.md`. In particular, USER_ACCEPTED means only
that the user wants to retain the item; it never implies SUPPORTED, TESTED or
TRUE. A model score is not a truth probability.

## State transitions

- Source: stored -> parse_queued -> parsing -> ready | ready_with_warnings | parse_failed.
- Job: queued -> running -> succeeded | retryable_failed | terminal_failed | cancelled.
- KnowledgeItem lifecycle: ACTIVE | ARCHIVED.
- KnowledgeRevision review status uses the canonical Contract v1 vocabulary:
  DRAFT, MACHINE_CANDIDATE, NEEDS_REVIEW, USER_ACCEPTED, USER_REJECTED or
  SUPERSEDED.
- Review decisions are append-only. Editing creates a new revision and marks
  the previous revision SUPERSEDED; MODIFIED and REVOKED are actions, not
  persistent review states. The current artifact revision is a projection.
- LearningItem state changes only through a LearningEvent command.

## Command rules

All mutating commands require command_id, idempotency_key, actor, expected_revision and contract_version. The Core returns a command receipt even for rejection. Replaying the same idempotency key returns the original receipt; a different payload with the same key is rejected.

Anchor text normalization is NFC with LF newlines. Offsets are Unicode scalar/code-point units, start inclusive and end exclusive. C# uses System.Text.Rune, Rust uses chars and Python uses Unicode code points. A PDF anchor additionally records zero-based page index, normalized quad points and page rotation. Resolution returns UNRESOLVED, EXACT, RELOCATED, AMBIGUOUS or ORPHANED without silently changing the stored Anchor. The resolution method is recorded separately; FUZZY_TEXT is a method and can never be presented as EXACT.

## Required domain rejections

- unsupported contract version
- stale aggregate revision
- source hash mismatch
- anchor outside source version
- missing capability
- worker timeout or invalid worker output
- candidate promoted without review
- direct verified or mastery assignment by a worker
- import package hash or schema mismatch
- export or restore count mismatch
