# September consolidation readback — 2026-09-27

Status: backend MERGED_MAIN; document consolidation TESTED_LOCAL pending its own PR/CI readback.
Current authority remains R6 + M0; this receipt does not certify real M0/Local Green or authorize release.

## Document disposition

See [exact-path history manifest](../history/DOCUMENT-CONSOLIDATION-20260927.json): nine byte-identical duplicates removed, one R5 handoff moved unchanged, old architecture preserved and current navigation corrected, six verified plain historical documents imported. Unresolved mixed/private/user material remains local and preserved.

## Cloud historical records

GitHub readback found no open issues; only PRs #151 and #152 were open at inventory time. #151's v2-only receipt claims were superseded by the v3 fixes in #152. GitHub automatically marked #151 MERGED when its ancestry landed through #152; it is no longer an open task. Eight published historical releases and two draft releases were preserved. Tag v0.6.14 exists; GitHub Release lookup for that tag returns 404. The existing local Green is not a published Release claim. Wiki is enabled in repository metadata, but the Wiki Git endpoint returned Repository not found: UNVERIFIED, no Wiki migration or deletion performed.

## Recovery

Before ref retirement, full-history bundle `.project-local/runs/4260083704/refs/artifacts/pre-cleanup.bundle` was verified (24 refs); SHA-256 `8cd7cc526e0d4d15a33a94458e532a1ef72efe7e80bf68a19144c592fa89619e`.
Verified candidate bundle `.project-local/runs/4260083704/refs/artifacts/verified-integration.bundle`: SHA-256 `fe9be4e689edd15f786a0204bf2cc18d723d5b8061911a3dae82bae8f0592bb2` (see original integration evidence for prerequisites).
No worktree directories, frontend modifications or user/runtime databases were deleted. Original worker-quality dirty files and their hash-verified copies are retained.

## Backend delivery and retired refs

[PR #152](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/pull/152) merged normally at `dc7e68736be360470961302edb34099399281ec8`, 2026-09-27T09:26:17Z. Candidate `96024a2782247a3f073c5eae5aeb175f9e156ee6` passed exact-SHA CI runs [36308403023](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/36308403023), [36308377582](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/36308377582) and vNext runs [36308403030](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/36308403030), [36308377585](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/36308377585). Required jobs passed; policy-skipped lanes are not claimed as test passes.

Ten remote refs retired: `codex/execution-reliability-standards`, `codex/frozen-roadmap-deepseek-v1`, `docs/verification-summary-2026-08-09`, `feat/naming-step3`, `release/v0.4.0-contract`, `dsh/backend-audit-20260927`, `dsh/backend-20260927`, `dsh/backend-r5`, `dsh/governance-drift-alignment-20260927`, `codex/september-backend-integration`.
Ten local refs retired: the same list except remote-only `feat/naming-step3` / `release/v0.4.0-contract`, replaced by local `codex/dp-f01-20260925` / `codex/worker-quality-0906`. Active frontend branch and `codex/Audit` are protected. Registered donor worktrees were detached at their unchanged commit; directories and files remain. Local main advanced by ancestor-checked compare-and-swap; the root checkout was not switched.

The earlier integration report's policy blocker and retained-branch statements are preserved as historical stages; they are superseded by this successful readback. HTTP 401 was isolated to an invalid inherited GH_TOKEN overriding the existing login; task-local gh processes excluded it, without changing global credentials.

Document checks: 56 existing authority/link/language/path tests passed locally. The manifest target hashes all matched after migration, including nine exact duplicates (22,298 on-disk bytes). No immutable TaskPack or old receipt SHA was rewritten; R6 real acceptance remains separate.

Known source limitation: the review route still waits synchronously for the FSRS subprocess inside the Store callback/transaction. The architecture record now states this exception; this documentation change does not claim to remove that latency/concurrency limitation.
