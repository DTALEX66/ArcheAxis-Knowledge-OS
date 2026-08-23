# AXR-060-502 Recovery Shell Closed-Loop Implementation Plan

> **Execution contract:** Implement this plan inline with `superpowers:executing-plans`, preserving the TaskPack's approved scope and using RED -> GREEN -> targeted regression -> project gate.

**Goal:** Close AXR-060-502 by keeping the packaged Tauri shell usable when Core startup, migration, port allocation, or identity validation fails, with retry, sanitized logs, safe mode, verified backup restore, and explicit exit.

**Architecture:** Tauri remains the recovery authority. It owns a small recovery state machine and exposes narrow commands; the React bundle renders either the normal six-space workspace or a Recovery Shell based on that state and the authenticated handshake. Safe mode deliberately keeps Core and migrations stopped while allowing only local recovery commands. Backup restore reuses the existing manifest-bound candidate and offline atomic activation implementation; the UI selects only enumerated backup names and never receives filesystem paths, launch tokens, response bodies, or raw process logs.

**Tech stack:** Rust/Tauri 2, React 18/TypeScript/Vitest, Python runtime entrypoint and manifest-bound SQLite backup module, pytest contract tests.

---

## Task 1: Freeze the recovery contract with failing tests

**Files:**
- Create: `frontend/src/__tests__/RecoveryShell.test.tsx`
- Modify: `frontend/src/__tests__/App.test.tsx`
- Modify: `frontend/src/__tests__/RuntimeClient.test.ts`
- Modify: `tests/test_tauri_security_contract.py`
- Modify: `src-tauri/src/main.rs` (Rust unit-test module only for RED)

1. Add frontend tests proving a failed desktop bootstrap replaces the workspace with a `main` Recovery Shell and exposes text-labelled Retry, Sanitized Logs, Safe Mode, Restore Backup, and Exit controls.
2. Add interaction tests proving log/backup data comes only from Tauri commands, restore accepts only an enumerated opaque backup name, successful retry returns to the six-space shell, and errors remain visible in an `alert`/`status` region.
3. Add Rust/security contract tests for bounded sanitization, traversal rejection, safe-mode state, no token/path/body fields in recovery DTOs, and all required commands in `generate_handler!`.
4. Run the targeted suites and capture the expected RED failures.

## Task 2: Add a path-free offline restore entrypoint

**Files:**
- Modify: `app/runtime_entrypoint.py`
- Modify: `tests/test_backup.py`

1. Add a failing test for `restore-backup <path>` that verifies the existing `backup.restore()` candidate then activates it through `backup.activate_restore()`.
2. Require an explicit positional path, keep legacy environment fallbacks out of this new desktop-only command, and emit only a path-free JSON receipt such as `{"status":"restored"}`.
3. Ensure exceptions remain fail-closed and the existing candidate/activation tests still pass.
4. Run `scripts/ci/run_tests.sh tests/test_backup.py` (or the repository's exact targeted pytest wrapper discovered by preflight).

## Task 3: Implement Tauri-owned recovery state and sanitization

**Files:**
- Create: `src-tauri/src/recovery.rs`
- Modify: `src-tauri/src/main.rs`
- Modify: `desktop/src-tauri/src/backend.rs`

1. Add serializable DTOs containing only state, safe-mode flag, availability, bounded sanitized messages, and backup display names.
2. Add deterministic sanitization that removes launch-token-like values, URLs/request bodies, drive/UNC/user paths, and overlong content; retain only bounded diagnostic categories and safe filenames.
3. Capture runtime-resolution, migration/startup, crash/readiness, and retry failures in recovery state without returning raw errors to the webview.
4. Enumerate backups only from `<runtime data>/backups` (the installed `resolve_runtime_path("data/backups")` result), require the exact expected filename pattern plus adjacent manifest, canonicalize under the allowed backup directory, and reject absolute paths, separators, parent traversal, or unknown names.
5. Expose `recovery_status`, `recovery_log_tail`, `enter_safe_mode`, `retry_backend`, `restore_backup`, and `exit_application`. Safe mode stops/takes the backend and blocks automatic Core launch; retry exits safe mode. Restore requires Core offline and invokes the bundled runtime's new `restore-backup` command.
6. Make External Dev fail closed unless explicitly enabled by `ARCHEAXIS_EXTERNAL_DEV=1`; release builds ignore the flag, and the enabled profile remains isolated under `.hermes/task-runtime/desktop-dev`.
7. Preserve existing Job Object shutdown semantics and ensure exit remains non-blocking on Tauri's event loop.
8. Run `cargo test --manifest-path src-tauri/Cargo.toml` from the exact worktree.

## Task 4: Render the accessible Recovery Shell

**Files:**
- Create: `frontend/src/components/RecoveryShell.tsx`
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/api/runtime.ts`
- Modify: `frontend/src/runtime/recovery.ts`
- Modify: `frontend/src/design-system/tokens.css`

1. Add typed recovery command wrappers that never surface `BackendInfo` outside the existing handshake closure.
2. Add an App bootstrap state machine: web development remains usable; Tauri must pass backend availability plus authenticated product handshake before the six-space shell renders.
3. Render Recovery Shell for unavailable, migration/startup failure, incompatible identity, or stopped/safe-mode states. Provide explicit operation progress, success/error text, keyboard focus, live regions, and text labels independent of colour.
4. Display sanitized bounded log lines on demand and enumerated backup names only. Confirm restore before invoking it, keep Core offline during restore, then offer normal retry.
5. Show a persistent, text-bearing `DEV` marker whenever the explicitly enabled External Dev profile is active; never infer it from a debug build alone.
6. Preserve visible focus and `prefers-reduced-motion`; add responsive recovery layout without changing the six-space information architecture.
7. Run targeted Vitest, then full `npm test` and `npm run build` using the repository-local/external dependency cache already configured by the project.

## Task 5: Layered verification and delivery

**Files:**
- Modify: `docs/current/AXR_060_COMPLETION_AUDIT_2026-08-23.md`
- Create or modify: current summary/handoff files as required by repository convention

1. Run execution preflight for the exact Python/Rust/Node environments and keep all caches/evidence under `.hermes`.
2. Run targeted Python, Rust, frontend tests; then risk-selected project gates and the full release-relevant gate once.
3. Run a packaged Windows recovery smoke covering missing runtime/startup failure, migration failure fixture, wrong identity, retry, safe mode, sanitized logs, verified restore, and exit. Record exact commands and results without private paths or tokens.
4. Inspect final diff/status and request read-only code review. Resolve findings with regression tests.
5. Update the completion audit only to the evidence level actually achieved (`PASS_LOCAL`, `PASS_PACKAGED`, or remaining `PARTIAL`).
6. Commit explicit paths, push the feature branch, open/merge the approved delivery PR, verify exact-SHA CI, and read back `origin/main` before claiming cloud/local consistency.
7. Update handoff with exact SHA/check/run evidence and continue to the next open TaskPack item.
