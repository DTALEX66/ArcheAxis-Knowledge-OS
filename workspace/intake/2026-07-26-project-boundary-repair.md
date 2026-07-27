# Project Boundary Repair — 2026-07-26

## Scope

This repair covers only data proven to belong to Cognitive-Loop-OS. Hermes, CC Switch, Codex, Workflow-assistance, GitHub delegation, session, cron, Kanban, and other workflow-infrastructure paths are not project data and remain in their owning directories.

## Root causes found

1. `shared/config.py` had an implicit `Path.home() / ".cognitive-loop-os"` fallback when an installed or relocated runtime lacked `COGNITIVE_DATA_DIR`.
2. Tauri installed-mode resolution used `app_local_data_dir()` for every non-debug bundle, including project-owned staged/portable bundles.
3. External Temp/AppData candidates were ambiguous until ownership was established from source code, test naming, Git worktree, process ownership, and generation path.

## Repairs

- Removed the uncontrolled Python user-home fallback; installed/relocated runtimes now fail closed unless `COGNITIVE_DATA_DIR` is explicit.
- Project `.hermes` bundles now resolve installed runtime data to `.hermes/task-runtime/desktop-installed`.
- Ordinary external installed packages retain their explicit per-user runtime root; this is separate from project portable/staged bundles.
- Added Python and Rust regression tests for both fail-closed behavior and project-bundle data containment.
- Migrated the verified Cognitive-Loop-OS fallback database and Tauri-owned persistent data into ignored project runtime storage; verified file hashes and SQLite integrity.
- Restored the known Hermes delegation batch to its original Hermes workflow path; no other workflow batch was moved or deleted.
- Updated `AGENTS.md` to require ownership proof before moving or deleting external files.

## Verification

- Python: `671 passed, 2 skipped`.
- Rust: `11 passed`; `cargo check` passed.
- Repository convention check passed.
- `git diff --check` passed.
- Project runtime root exists at `.hermes/task-runtime/desktop-installed`.
- Cognitive-Loop-OS-specific C-drive fallback/AppData source roots are absent after migration.
- Hermes delegation root remains present and was not treated as project output.

## Safety note

A prior cleanup attempt incorrectly removed one ambiguous temporary review copy before workflow ownership was proven. This is recorded as an agent error; future cleanup must preserve unresolved files and must never infer project ownership from a project-like filename alone.
