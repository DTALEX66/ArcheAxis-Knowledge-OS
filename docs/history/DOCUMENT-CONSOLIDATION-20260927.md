# Historical document consolidation — 2026-09-27

R6/M0 remain current authority. This is an exact-path repository maintenance receipt.

The [manifest](DOCUMENT-CONSOLIDATION-20260927.json) records original paths, canonical targets, SHA-256, byte counts, consumer scans, authorization and rollback before each move/delete.

- Nine byte-identical `branch-donors/` copies were removed; originals remain under `donor-branch-assets/`. No active code or unique historical content was deleted.
- [R5 handoff](r5-handoffs/R5-HANDOFF-2026-09-17.md) moved unchanged from `docs/current/`; no tracked consumers were found before migration. Historical relative links/text are preserved verbatim; this is a source artifact, not a navigation entrypoint.
- [Pre-reconciliation architecture](architecture/CURRENT_ARCHITECTURE-before-R6-reconciliation-20260927.md) preserves the old architecture page verbatim. Its use of “current” is historical. The active architecture page now describes formal R6 language responsibilities.
- [Execution reliability donor](branch-donors/execution-reliability-20260926/README.md) includes three exact-tip documents and their source manifest; it is frozen history, never an active TaskPack.
- [2026-09-13 cleanup report](HERMES_CLEANUP_2026-09-13.md) is an imported author's dated claim, not a fresh verification or permission to repeat its actions.
- 988 other untracked files (486,175,764 bytes at inventory time) remain local: user attachments, mixed agent/runtime state, historical evidence and preserved diffs. No private session payload was read or published. Age, size and filenames are not evidence of safe deletion.

Recover a tracked pre-change source in an isolated checkout of `96024a2782247a3f073c5eae5aeb175f9e156ee6` using repository checkout filters. The manifest distinguishes on-disk SHA-256 (including existing line endings) from source Git-blob SHA-256; verify the corresponding representation. Imported root-checkout originals remain present. Whole-change rollback is a normal Git revert; do not reset active frontend worktrees.

See [delivery readback](../current/SEPTEMBER-CONSOLIDATION-READBACK-20260927.md) for branch/CI/cloud status. Taskpacks, old receipts, releases/tags, user data and frontend source are preserved.
