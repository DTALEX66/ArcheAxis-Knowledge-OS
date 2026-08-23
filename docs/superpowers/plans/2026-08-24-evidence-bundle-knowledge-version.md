# EvidenceBundle and KnowledgeVersion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist a governed EvidenceBundle and require every new candidate KnowledgeVersion to name one before it can be registered.

**Architecture:** Add a versioned SQLite migration under the existing knowledge-governance owner so the existing backup, forward migration, rollback, and restart-readback operator applies. A small evidence-ledger module stores immutable bundle headers, per-source entries, and human review receipts; `KnowledgeVersionProposal` consumes a reviewed bundle id and records it in the version provenance rather than duplicating caller-supplied evidence.

**Tech Stack:** Python 3, SQLite, Pydantic v2, existing `shared.knowledge_governance_migration` / `MigrationOperator`, pytest.

**Spec:** `D:\All projects\ArcheAxis_v0.6.0_Minimum_Closed_Loop_Release_TaskPack_2026-08-20.md` §AXR-060-303.

## Global Constraints

- Candidate records bind a complete raw SHA-256, source revision, and physical anchor before knowledge-version registration.
- Bundle entries preserve supports/refutes/unknown, source organizational lineage, validity window, scope, rights, and review state.
- A single webpage, model output, or OCR result cannot independently yield a verified bundle.
- `not_verifiable` is a valid terminal review outcome and must never be represented as verified.
- Use the existing owner-bound migration operator; no new dependency or external service.
- All tests create databases only under project-local pytest temporary paths.

---

### Task 1: Add the owner-bound EvidenceBundle ledger migration

**Files:**
- Modify: `shared/knowledge_governance_migration.py`
- Modify: `shared/migration.py`
- Modify: `shared/migration_runner.py`
- Test: `tests/test_knowledge_governance_migration.py`

**Interfaces:**
- Produces `evidence_bundles_v1`, `evidence_bundle_entries_v1`, and `evidence_bundle_reviews_v1` as objects owned by `knowledge-governance.sqlite`.
- Produces one named migration that `MigrationOperator.apply("knowledge-governance.sqlite")` backs up, applies, reports, and can roll back with the existing owner snapshot.

- [ ] **Step 1: Write the failing migration test**

```python
applied = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply("knowledge-governance.sqlite")
assert "phase5_evidence_bundle_ledger_v1" in applied["provenance"]["applied_migrations"]
assert {"evidence_bundles_v1", "evidence_bundle_entries_v1", "evidence_bundle_reviews_v1"} <= tables
```

- [ ] **Step 2: Run the targeted migration test and verify it fails because the ledger migration is absent.**

Run: `python -m pytest tests/test_knowledge_governance_migration.py -q`

- [ ] **Step 3: Add migration version, schema SQL, object inventory, pending-status validation, and rollback allow-list entry.**

```python
EVIDENCE_BUNDLE_LEDGER_MIGRATION_VERSION = 15
EVIDENCE_BUNDLE_LEDGER_MIGRATION_NAME = "phase5_evidence_bundle_ledger_v1"
```

The schema uses immutable header/entry/review rows, with a bundle id foreign-keyed into its entries and reviews.

- [ ] **Step 4: Re-run the migration test and verify apply, restart status, and rollback preserve the pre-migration sentinel.**

- [ ] **Step 5: Commit the migration task after its focused test passes.**

### Task 2: Implement immutable bundle storage and review rules

**Files:**
- Create: `app/evidence/ledger.py`
- Modify: `app/evidence/bundle.py`
- Test: `tests/test_evidence_bundle_ledger.py`

**Interfaces:**
- Consumes a migrated knowledge-governance SQLite database.
- Produces `EvidenceBundleDraft`, `EvidenceBundleEntry`, `BundleReview`, `store_bundle`, `review_bundle`, and `get_reviewed_bundle`.
- `store_bundle(draft, db_path)` inserts only; duplicate identity with different content raises.
- `review_bundle(review, db_path)` records a separate immutable receipt and returns the resulting status.

- [ ] **Step 1: Write failing ledger tests** for a persisted complete raw SHA-256/revision/anchor; mixed support/refute/unknown relations; independent lineage count; and rejected one-source web/model/OCR verification.

```python
with pytest.raises(EvidenceBundleError, match="independent sources"):
    review_bundle(BundleReview(bundle_id="b1", decision="verified", reviewer_id="r", rationale="one page"), db_path=db)
```

- [ ] **Step 2: Run `python -m pytest tests/test_evidence_bundle_ledger.py -q` and verify the import/API failure.**

- [ ] **Step 3: Implement Pydantic contracts and explicit-column `INSERT` calls.**

`decision` is `verified`, `not_verifiable`, or `rejected`; verified requires at least two organizationally independent entries and cannot contain only web/model/OCR evidence. Other decisions remain available without inventing verification.

- [ ] **Step 4: Re-run the ledger tests and verify persistence is readable after a new SQLite connection.**

- [ ] **Step 5: Commit the ledger task after focused tests pass.**

### Task 3: Bind candidate KnowledgeVersion to a reviewed EvidenceBundle

**Files:**
- Modify: `app/knowledge/versioning.py`
- Modify: `tests/test_knowledge_candidate_versioning.py`
- Test: `tests/test_evidence_bundle_ledger.py`

**Interfaces:**
- `KnowledgeVersionProposal` gains `evidence_bundle_id: str`.
- `register_candidate_knowledge_version` rejects absent, unknown, unreviewed, rejected, or `not_verifiable` bundle ids.
- Version `provenance_json` stores `evidence_bundle_id` plus the reviewed bundle fingerprint; existing content and conflict semantics stay unchanged.

- [ ] **Step 1: Write a failing versioning test** that first creates a migrated bundle, reviews it, registers a candidate version, then reads the stored provenance; add a negative test for an unreviewed bundle.

- [ ] **Step 2: Run `python -m pytest tests/test_knowledge_candidate_versioning.py tests/test_evidence_bundle_ledger.py -q` and verify the new proposal field/readback assertion fails.**

- [ ] **Step 3: Add the required proposal field and query `get_reviewed_bundle` inside the existing immediate transaction boundary.**

```python
bundle = get_reviewed_bundle(proposal.evidence_bundle_id, db_path=database)
provenance["evidence_bundle_id"] = bundle.bundle_id
provenance["evidence_bundle_fingerprint"] = bundle.fingerprint
```

- [ ] **Step 4: Re-run the focused version/bundle tests and verify both pass.**

- [ ] **Step 5: Commit the version-binding task after focused tests pass.**

### Task 4: Final verification and handoff

**Files:**
- Create: `docs/current/AXR_060_303_EVIDENCE_BUNDLE_KNOWLEDGE_VERSION_HANDOFF_2026-08-24.md`

- [ ] **Step 1: Run the full affected test set.**

```text
python -m pytest tests/test_evidence_bundle.py tests/test_evidence_bundle_ledger.py \
  tests/test_evidence_contract.py tests/test_knowledge_candidate_versioning.py \
  tests/test_knowledge_governance_migration.py tests/test_knowledge_governance_schema_tamper.py -q
```

- [ ] **Step 2: Run `python -m compileall -q` on changed production modules, `python -m ruff check` on changed Python files, and `git diff --check`.**

- [ ] **Step 3: Record exact commands/results and explicit remaining evidence layers in the handoff.**

- [ ] **Step 4: Review the final diff and status, then commit and push only the task files to `codex/evidence-bundle-version`.**

## Self-Review

- AXR-060-303’s raw version/anchor, relation types, independence, timeliness, scope, rights, review, `not_verifiable`, and no-single-source-verification requirements map to Tasks 1–3.
- The migration uses the existing owner, so backup, forward apply, rollback, and restart status are covered by Task 1 rather than an unmanaged `ALTER TABLE`.
- No new runtime service, dependency, or UI contract is introduced; task scope is bounded to the existing governance database and candidate-version writer.
