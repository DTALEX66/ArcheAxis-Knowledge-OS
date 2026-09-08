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
| A | X00, X01, X02 (+X14 early) | X00 IN_PROGRESS (registration, this file); X01/X02 pending |
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

(none yet in R3; registration performed in the X00 commit)
