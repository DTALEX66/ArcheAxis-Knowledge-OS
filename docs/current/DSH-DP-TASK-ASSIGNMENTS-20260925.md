# 2026-09-25 DSH/DP task assignments — AAOS frontend closure

This handoff is an execution assignment for the user's DSH DeepSeek run. Read the repository `AGENTS.md`, `docs/authority/taskpack-0919-r6/EXECUTOR-START.md`, `TASKPACK.md`, `TASKS.json`, `docs/current/M0-DIRECTION-OVERRIDE-20260920.md`, `docs/current/R6-EXECUTION.md`, `docs/current/R6-STATE.json`, `docs/superpowers/plans/2026-09-24-aaos-commercial-frontend-completion.md`, and `docs/SHARED_RESOURCE_PATH_INDEX.md` before acting. These are the governing sources. Do not infer current state from this handoff; re-read Git status, branch, HEAD and actual files.

## Shared rules

- Create a dedicated isolated worktree and branch `codex/dp-<task-id>-20260925` from the exact baseline agreed with the user. Record baseline SHA and tree. The root checkout is dirty and contains unrelated work; never copy its full working tree or overwrite it.
- Work only in the task's declared write-set. Preserve unknown files. No `reset --hard`, `clean`, broad restore, or staging unrelated files.
- No Green install/replacement, release, signing, upload, push or main merge. Do not inspect Green content, private session stores, user profile data, E: or F:.
- All reports/source artifacts stay in the DP branch under the task's exact approved paths. Runtime artifacts go only under the project's `.project-local/` allocated by `scripts/runtime/dev.py`.
- Distinguish `IMPLEMENTED_LOCAL`, `TESTED_LOCAL`, `NATIVE_UI_VERIFIED`, `EXACT_SHA_CANDIDATE`, `OWNER_GATE`; mark missing evidence `NOT_EXECUTED` or `UNVERIFIED`.
- Do not change R6/M0 states to complete. Do not enable UI for missing Core contracts.
- Return branch name, baseline SHA, exact tip SHA/tree, changed paths, commands/results, evidence paths and hashes, unresolved items, and whether any test was not run. Do not push.

## DP-GIT-01 — branch/commit semantic audit (start now; read-only product review)

Goal: independently inspect actual committed changes from the branch/path audit inventory, identify useful donor changes, conflicts with September authority, duplicated/stale work and integration risks. Audit 15–20 distinct SHAs per batch at most. Read the actual diff and parent context for each SHA; branch names and old receipts are hints only. State clearly that the dirty root working tree is not part of the branch diff.

Write-set: add only `docs/current/dsh-review/branch-batch-01.md` and `docs/current/dsh-review/branch-batch-01.json` (or next numbered batch if already present; preserve existing files). Include per SHA: branch refs, files, purpose, tests/evidence actually observed, September Authority alignment, donor decision `KEEP / CHERRY_PICK_CANDIDATE / SUPERSEDED / CONFLICT / UNKNOWN`, and rationale. This is an audit, not authorization to cherry-pick.

First batch priority: small feature branches `feat/ms00-c-release-identity`, `feat/portable-data-root`, `feat/axw022a/022b`, `feat/h2-bakeoff`, `feat/naming-step3`, `feat/archeaxis-desktop-a1-violet-core`; continue only if baseline refs resolve and time permits. Do not claim exhaustiveness after one batch. No product source changes.

Verification: validate report JSON; verify each claimed SHA/path against Git; `git diff --check`; report exact per-batch coverage counts. Commit only these two report files on the DP branch if required for root readback; never include other files.

## DP-UI-01 — native GUI acceptance (wait for root's current-tree Candidate)

Dependency: do not run against the stale committed-HEAD Candidate. Wait until root supplies the exact current-source Candidate path, manifest SHA, source snapshot SHA, Desktop/Core hashes, isolated run instructions and baseline exact tree. If that Candidate is not supplied, produce a blocked/NOT_EXECUTED readiness report only; do not substitute an old Candidate or dirty root executable.

Read-only acceptance scope: actual Avalonia window and exact Candidate. Use fresh isolated project-local workspace, record exact executable hashes and only processes started by this run. Exercise all 16 route destinations; File/Navigate/View menus; Ctrl+K and Ctrl+Alt+I/J; Tab/Shift+Tab, Enter, arrows, Escape, focus restoration; IME text entry; UIA accessible names, selected/current-page state; error/offline/permission/empty/pending/retry states. Capture unobscured screenshots and UIA readbacks. Cover logical widths 1024, 1200, 1280, 1440, 1920, 2560 and Windows scaling 100%, 125%, 150%, 200%; record each unavailable setting as `NOT_EXECUTED` (do not modify system DPI/registry). Verify screen-reader announcements only with a real available assistive technology.

Write-set: evidence under the allocated `.project-local/runs/<run-id>/` only. No source edits. Stop only your owned processes. Report per-matrix cell and evidence hash; do not infer success from UIA focus without visible input delivery.

## DP-UI-02 — measured frontend defect fix (only after DP-UI-01)

Start only when a DP-UI-01 receipt names a reproducible product defect and root assigns its exact source write-set. One writer at a time. Add a regression first, make the narrow fix, run targeted suite and Release build. Do not touch shared `MainWindow.axaml(.cs)`, theme, Core/API, route authority, schemas or unavailable Research/Plugin/Model/Editor/Evidence contracts unless root explicitly assigns that exact scope. Report before expanding scope. No speculative visual redesign.

## DP-F01 — real text quality roundtrip (independent M0 P1 slice; candidate implementation)

Goal: test one synthetic, controlled text fixture through the formal Rust Executor → Python Text NDJSON worker → Core API path and reopen/readback. Preserve original hash, transform hash, source/job/transform binding, structure/anchors, quality/loss, engine/version, fallback and explicit unsupported state. Do not touch real corpus or Green.

Default write-set: add `tests/workers/test_f01_real_quality.py`, synthetic fixtures under `tests/fixtures/f01-quality/`, and `crates/archeaxis-api/tests/f01_quality_roundtrip.rs`. Production fix may touch only `services/python-workers/document/worker_text.py`, only when a failing test demonstrates a defect. No Rust production/schema change, other workers, desktop, config, authority or broad refactor. If a Core contract gap blocks the test, stop with exact evidence and propose a separate frozen contract; do not invent data.

Use only declared project commands/tool paths. Run new regression first (show RED where feasible), then targeted worker and Rust tests. Report evidence class: synthetic integration is not real corpus qualification and does not close all P1 formats.

## DP-A11 — Research contract gap analysis (optional read-only, after DP-GIT-01)

Research remains unavailable because current Core transform records lack an authoritative source revision/provider-quality projection required by the derived projection contract. Do not code UI or invent revision semantics. A read-only short design note may enumerate exact fields, authoritative writer, revision derivation, stale/error/empty semantics and migration compatibility, citing current Rust routes/schema. Write only `docs/current/dsh-review/research-contract-gap.md`; label `PROPOSAL / OWNER REVIEW REQUIRED`, not an adopted contract.

## Root-side critical path (do not duplicate)

1. Root finishes Task 8 current-source snapshot/build provenance wiring and assembles an exact dirty-tree Candidate. Snapshot capture must happen before Desktop/Core compilation; then assemble with that receipt and verify by recomputation. This proves tree identity and package hashes, not compiler provenance/signing.
2. Run DP-UI-01 on that exact Candidate. Fix only measured defects through DP-UI-02.
3. Close M0 P1 through a real quality-complete parser path and then explicit format expansion; P0 provider lifecycle remains authority-gated.
4. P2 stays one General domain/renderer; no additional provider or product scope.
5. P3 remains partial until actual UI answer → Core Assessment → authoritative Mastery/FSRS → cold restart readback yields `Mastery closed=true` where contract permits; current evidence reads `closed=false`.
6. P4 needs user-authorized real model task, human correction and retest on same accepted Knowledge; current configured model is stub and real path was not executed.
7. P5 needs full backup/restore identity and non-empty isolated Legacy semantic diff/readback; owner identity decision remains open.
8. Only after P0–P5, exact Candidate journey, and separately authorized Green backup/replace/restart/readback/rollback may Local Green reach owner review. Current release is frozen.

## Root audit/integration protocol for the DP branch

When DSH returns an exact branch/tip, root will read its status/diff from the isolated DP worktree, verify scope and source SHA, review every changed hunk against R6/M0 and path-specific gates, rerun relevant checks on the integration tree, then integrate only the audited exact SHA into an isolated integration worktree with hunk-level conflict resolution. No force push, no Green action, no main merge, no branch cleanup. If any scope/evidence violation appears, reject the branch from integration and preserve it unchanged.
