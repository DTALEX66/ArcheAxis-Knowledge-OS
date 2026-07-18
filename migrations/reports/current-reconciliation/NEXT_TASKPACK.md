# Safe Next TaskPack

Generated: `2026-07-17T22:31:07+08:00`

## Immediate next TaskPack

### `P00A_CONTAINER_CORRECTION_RELEASE`

Reason: P00 found a newer, fully staged, uncommitted high-risk candidate in `D:/All projects/Cognitive-Loop-OS-container`. Starting new implementation elsewhere before preserving this candidate would violate the reconciliation goal.

Ownership:

- Checkout: `D:/All projects/Cognitive-Loop-OS-container` only.
- Branch: `feat/complete-container-stack`.
- Exact starting staged tree: `3d99e200dff9d816a0767a3c46f0689575ed5b7c`.
- Scope: only the 21 already-staged CLI/runtime-lease, baseline-schema-owner, backup-dir, docs and regression-test paths.

Required closure:

1. Reconfirm no active writer and exact staged tree/status unchanged.
2. Resume one synchronous read-only exact-tree review for `3d99e200…`; do not restart the whole audit.
3. If GO: commit the exact tree, push `feat/complete-container-stack`, verify local/remote SHA equality and exact-SHA CI/Container Stack success.
4. If NO-GO: fix only reproducible Blocker/High findings via RED/GREEN, run required high-risk gates once, freeze a superseding tree and review it.
5. Do not merge PR #2 during this TaskPack.

Forbidden:

- reset/restore/clean/rebase/amend/force-push;
- changing `main`;
- absorbing the v4.0 planning package into code;
- starting Phase 5–12;
- deleting branches, clones or reports.

## Release graph after P00A

1. Execute package `taskpacks/P03_PHASE3_INTEGRATION_RELEASE.md` from authoritative `main`, updated against live code and the released container correction.
2. Merge Phase 3 integration only after full gates, exact-tree GO and exact-SHA CI.
3. Revalidate PR #1 against the new `main`; merge `main` into the feature branch rather than rewriting published history, rerun CI, then merge only with a current GO.
4. Revalidate PR #2 after PR #1/base reconciliation so its diff is container-only; rerun exact-SHA CI/Container Stack before merge.
5. Then proceed Phase 5 → 9. Registry V2 (`P03A`) and Model Registry Foundation (`P03B`) may run only as bounded independent governance TaskPacks after Phase 3; Claude/Grok/Workspace tasks remain non-preemptive future work.

## Why not jump directly to P03/P04

- P03 is still genuinely missing on `main`.
- P04 already exists as an unmerged candidate; reimplementing it would duplicate work.
- PR #2 is stacked on PR #1, so merging out of order would silently bundle Phase 4 with container delivery.
- The uncommitted staged correction tree has no final reviewer verdict and no remote backup.

This sequencing preserves all user work and restores a truthful, append-only release graph before new feature expansion.
