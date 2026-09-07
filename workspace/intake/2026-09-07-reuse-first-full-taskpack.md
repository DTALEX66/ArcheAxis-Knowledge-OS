# Intake: REUSE-FIRST full taskpack (2026-09-07) adopted as framework direction

Date: 2026-09-07. Authority: user approved ingest + X00 + start via DSH Web GUI.

## What changed

- New approved plan `AAK-REUSE-FIRST-20260907-R2` supersedes the 2026-09-06-r1
  split execution model (one continuous authorized executor to M0; independent
  GPT audit Q00/Q01 at the end; F01-F06 retained frozen). Full text:
  `docs/authority/taskpack-0907/TASKPACK.md` and `TASKS.json` (23 tasks).
- Direction: reuse-first (upstream learning UI, OCR/ASR, review, interactive,
  3D/viewers, MCP, evaluation) instead of in-house rewrite; full capability and
  blueprint retention; Rust authoritative vNext writer + isolated Python
  workers + C# desktop; TypeScript/JavaScript accepted as a thin Web
  presentation/reuse layer; first delivery = local Web learning entry or thin
  shell carrying it; Obsidian/Vault round-trip detailed at M1 (X12).
- Decisions D01-D16 recorded: DECISION_SUPERSESSION_LEDGER.yaml SUP-012..SUP-016
  + mapping table in `docs/authority/taskpack-0907/EXECUTION.md`.
- Package intake verified: 15 files, `verify_package.py` exit 0
  (`package_checks: PASS`); standalone md == in-zip TASKPACK.md
  (sha256 a9093a72…); audit base 4ca46ea… matches origin/main.

## Impact on framework rules

- AGENTS.md §6 stays the operational guide; the active-plan reference should be
  read as this taskpack (X00..) superseding taskpack-0906 in the recorded parts.
- New development outputs remain under `.project-local` via
  `scripts/runtime/dev.py`; `.hermes` stays preserved legacy (read-only, no new
  writes) — enforced by X01.
- Statuses follow EXECUTOR-START: TODO / IN_PROGRESS / BLOCKED_RESOURCE /
  IMPLEMENTED_PENDING_AUDIT / VERIFIED; DEFERRED_RETAINED ≠ DONE.
- Evidence standard per task card: tested source sha, tree, command + exit
  code, env versions, input/output hashes, failure paths, rollback.

## Open

- X01/X02 first slices are the immediate next work (see taskpack EXECUTION.md).
- Nothing here authorizes releases, real-user-library migration, E-drive access
  or destructive cleanup; X14 requires its own measured, authorized execution.
