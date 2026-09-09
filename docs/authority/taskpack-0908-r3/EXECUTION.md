# 2026-09-08 Follow-up R3 execution (AAK-FOLLOWUP-20260908-R3.1)

This ledger is the single live execution entry for the R3 taskpack. The
package was verified with `verify_package.py` (PASS: 23 tasks, 29 features,
26 scenarios, 16 capabilities, 16 format groups, 11 enhancements, 14 gates,
12 governance-migration slices, 29 packaged files). Package integrity only;
not a product audit or implementation claim. Frozen `TASKS.json` TODO states
are not completion; current status is this file.

## Plan and package identity

- Package: ARCHEAXIS-FOLLOWUP-20260908-R3, revision R3.1, installed at
  `docs/authority/taskpack-0908-r3/` (single level; `frozen-r2/` is a
  read-only R2 snapshot, not a second active plan).
- Implementation baseline: branch `codex/full-loop-0906`, SHA
  `cbe253b107da0e8b6d55505bd9c3c2d8de59b7ed` (== HEAD at registration;
  working tree clean except the new taskpack files themselves).
- Inherited audit baseline: Q00 FAIL, Q01 NOT_READY at R2; C01/C02 DONE,
  C03-C10 PARTIAL (see `frozen-r2/C-FIX-STATUS-2026-09-08.md` v7 and
  `frozen-r2/INDEPENDENT-AUDIT.md` for authoritative gate text).
- Decisions D01-D16 are byte-inherited from R2 and remain recorded as
  SUP-012..SUP-016 in `DECISION_SUPERSESSION_LEDGER.yaml`. R3 plan
  registration is SUP-017.
- `plan_only: true`; `issued_authorization: false`; all tasks
  `implementation_completed_in_this_package: false` at baseline.

## Entry-point reconciliation (X00 r3_work)

- AGENTS.md §6 now points the active plan to this file; R2 stays as the
  source of inherited task text and its own receipts.
- `DECISION_SUPERSESSION_LEDGER.yaml` gained SUP-017 (R3 supersedes R2 as
  the single live plan; historical evidence SHAs unchanged per D08).
- Intake note: `workspace/intake/2026-09-08-followup-r3-taskpack.md`.

## Wave order (TASKPACK.md §3) and status

Waves are slice priority, not new dependencies.

| Wave | Tasks | Status |
| --- | --- | --- |
| A | X00, X01, X02 (+X14 early) | X00 IMPLEMENTED_PENDING_AUDIT; X01 r3 increment IMPLEMENTED_PENDING_AUDIT; X02 pending |
| B | X04, X05 (+X07/X08 defect slices) | pending |
| C | X06, X07 (+X10) | pending |
| D | X03, X08, X09 | pending |
| E | X10, X11, Q00 | pending |
| F | X12, X13, X14, Q01 | pending |
| frozen | F01-F06 | DEFERRED_RETAINED |

## P1 defect fixes carried in (AUDIT-DELTA.md)

1. REVISION-01 review `new_body` must create a new revision, never overwrite
   old bytes (X04/X05/X07).
2. ARCHIVE-01 restore must distinguish 11-table v3, 13-table v3 and the new
   archive contract; unknown layouts rejected (X05/X10).
3. VERIFY-01 "6371 / no-error" is not "supported"; verification needs object,
   unit, condition, locatable source (X07).
4. EVENT-01 learning `event_key` persistent producer-side retry identity;
   same retry returns the same receipt; conflicts rejected (X04/X08).

## Six non-bypassable boundaries (TASKPACK.md §4)

1. Accept is not modify: review never overwrites body; new body = new
   revision; hash/ID/reference version/review event/successor relation all
   hold together.
2. Restore is backward compatible: identify 11-table v3, 13-table v3, and
   new archive contract separately; unknown layouts rejected.
3. Learning events are stable: producer persists `event_key` bound to
   object and canonical payload; same retry returns original receipt;
   conflicts rejected; missing key never accumulates.
4. Verification results are not exit codes; "unsupported" is not support.
5. Plugins cannot self-grant identity or facts; machine proposal, human
   accept, fact-check, and usage scope are separated.
6. Correction must affect what is in use: active-qualification checks run
   before retrieval/context return and before task-result submission;
   already-exported history must not be claimed recalled.

## Standing boundaries

- No `E:\` access; no new `.hermes` dev artifacts; no paid-API authorization;
  no publishing authorization; do not overwrite R2 originals; never fabricate
  passes for blocked resources (record `BLOCKED_RESOURCE`).
- Per-slice ledger fields follow `EXECUTION-TEMPLATE.md` (baseline_sha,
  donor path/hash, real commands, fixture/output hashes, rollback).
- Status vocabulary: IN_PROGRESS / BLOCKED_RESOURCE /
  IMPLEMENTED_PENDING_AUDIT / VERIFIED. FAIL, BLOCKED_RESOURCE and
  NOT_TESTED are never reported as PASS.

## Slices landed (commit -> evidence)

- `1191a77` X00 registration (GOV01/LANG01 partial): package installed at
  this directory, `verify_package.py` PASS (exit 0; 23 tasks / 29 features /
  26 scenarios / 16 capabilities / 16 format groups / 11 enhancements /
  14 gates / 12 governance slices), SUP-017 appended to
  `DECISION_SUPERSESSION_LEDGER.yaml`, AGENTS.md §6 active-plan pointer
  switched to this file, intake note
  `workspace/intake/2026-09-08-followup-r3-taskpack.md`. Baseline check:
  HEAD `cbe253b` == package `audit_base_sha`; branch `codex/full-loop-0906`
  (ahead 1 of origin at registration time); `main` untouched at `4ca46ea`.
  Rollback: revert the commit; package files are inert data.
- `1f1b44c` X00 index alignment: `docs/DOCUMENTATION_AUTHORITY_INDEX.md`
  current read order and `docs/CONFIGURATION_AUTHORITY_INDEX.md`
  当前执行 row now resolve to this file as the single active plan entry
  (AUTH-01 evidence: all entry points -> AAK-FOLLOWUP-20260908-R3;
  23 tasks/16CAP/16 formats/11 enhancements/29 features retained via
  TASKS.json byte-inheritance; DONE/implementation/audit states separated —
  nothing in R3 is claimed DONE or VERIFIED yet).
- X00 remains IMPLEMENTED_PENDING_AUDIT, not VERIFIED: independent GPT
  audit (Q00) is the only qualification path.
- `next` (X01 r3 increment, GOV02/PATH-01): added `.cargo/config.toml`
  `[build] target-dir = ".project-local/build/cargo"` so default bare cargo
  entries stop growing the worktree-root `target/`. Real-write verification
  (PATH-01 path diff, both runs under the repo path containing a space):
  - Before/after fingerprints (bytes, files, newest mtime):
    root `target/` 6,151,810,038 / 19,949 / 2026-09-08T08:03:23 — identical
    before and after; `.hermes/` 46,508,545,377 / 748,125 / 2026-09-06
    (zero new writes, consistent with the R2 growth-stop evidence).
  - Bare `cargo build -p archeaxis-api` at repo root (default entry, no
    dev.py env; MSVC toolchain per `.project-local/runs/cargo-full-workspace.bat`):
    exit 0; artifact `.project-local/build/cargo/debug/archeaxis-api.exe`
    (7,486,464 bytes); `.project-local/build/cargo` grew to 1,089,242,530
    bytes / 2,167 files; root `target/` fingerprint unchanged.
  - `scripts/ci/run_tests.sh tests/runtime-paths`: 10 passed in 2.83s,
    run root `.project-local/runs/be268a2d33/e0f49b6f3ed0`; pytest cache and
    basetemp inside the run root; root `target/` and `.hermes/` unchanged.
  - Failure/cancel/concurrency path semantics remain covered by
    `tests/runtime-paths/test_dev_paths.py` (9 tests, green this run).
  - Limitations: local gnu toolchain (`~/.rustup` default) lacks gcc/dlltool
    and cannot build `libsqlite3-sys`/`windows-sys`; working local builds
    require the MSVC wrapper documented at
    `.project-local/runs/cargo-full-workspace.bat`. Packaging-side path diff
    remains a CI/nightly concern (RELEASE-01); browser/short-socket-path
    exceptions unchanged from R2 state. Rollback: delete
    `.cargo/config.toml` (single file) — root `target/` reverts to prior
    behavior.
