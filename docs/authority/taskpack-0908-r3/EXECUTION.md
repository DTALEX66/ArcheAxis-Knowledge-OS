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
| A | X00, X01, X02 (+X14 early) | X00, X01 r3 increment, X02 donor table, X14 early read-only census — all IMPLEMENTED_PENDING_AUDIT (X02 full review stays X13/M1; X14 deletions await per-path authorization) |
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
- `next` (X02 donor table, GOV03/REUSE-01): `X02-DONOR-TABLE-2026-09-09.md`
  records the five current-loop donor rows (deeptutor bridge/authority,
  anki_zotero, due_queue, python-workers tree) with git blob SHAs @ `d7d392d`,
  disposition, callers, and regression evidence: 27 passed / 0 failed via
  `run_tests.sh` (deeptutor 4, due_queue 6, longterm adapters 8, bulk
  workers 9). The 1,246-row legacy manifest stays preserved and outside
  this donor scope (X13/M1); no migration-completion claims (LANG07).
- `next` (X14 early slice, GOV04/CLEAN-01 — read-only, no deletions):
  same-tool census repeated 2026-09-09T11:40Z via
  `scripts/maintenance/inventory_project.py` (receipt
  `.project-local/runs/x14-early-inventory-20260909.json`): observed
  21,784,820,233 bytes ≈ 20.29 GiB / 115,231 files / 16 observation errors /
  8 skipped reparse / 50 excluded opaque entries — NOT a repository total
  (`.hermes` stays opaque; fingerprint separately recorded at
  46,508,545,377 bytes / 748,125 files, newest write 2026-09-06, zero
  growth since). D: free space 234.0 GiB (logical bytes only; hard links
  counted independently; allocated release not promised). Classification —
  no deletion performed or authorized this slice:
  - Regenerable caches (candidates only; per-path authorization required
    before removal): root `target/` 5.729 GiB (19,949 files; growth stopped
    by `.cargo/config.toml`), `.project-local/build` 9.413 GiB (32,233
    files), `.project-local/cache` 1.148 GiB, `.venv` 0.858 GiB,
    `.ruff_cache`/`__pycache__` negligible.
  - Run evidence (preserve; ledger-referenced receipts live here, e.g.
    `cargo-full-workspace.bat`, round-240 census): `.project-local/runs`
    2.396 GiB / 27,641 files.
  - Data/validation (real libraries, no touch): `data/` 0.094 GiB,
    `.project-local/deeptutor-val` 0.077 GiB, `.project-local/inventory`
    0.404 GiB.
  - Unique history (preserve): docs, taskpacks, `.hermes`, all opaque
    agent-private roots.

## Wave B slices landed (commit -> evidence)

- `288991a` (REVISION-01, X04/X05/X07): `knowledge::review` —
  accept/reject/deprecate with `new_body` is rejected
  (`accept_with_new_body_is_rejected_and_body_stays_immutable`); status
  changes UPDATE only status+receipt, body bytes immutable; `modified`
  keeps new-revision + supersede semantics with the corrected body. Test
  evidence: `crates/archeaxis-domain/tests/review_transaction.rs` green in
  the full run below.
- `288991a` (EVENT-01, X04/X08): `record_review_keyed` now requires a
  non-empty persistent key (missing key -> 400/parameter error, never
  accumulates); key bound to item_key + canonical payload hash
  (sha256(kind|outcome)); same retry returns the ORIGINAL receipt
  (event_id/streak/next-review-days persisted with the key, schema v4
  migration guarded for fresh DBs); same key with different item or payload
  is a conflict (rejected). Machine-actor 403 guard ordering preserved
  (`machine_cannot_review_or_record_human_learning` green). Tests:
  `learning_events_api.rs` incl. new
  `same_key_different_payload_conflicts_and_missing_key_rejected`.
- `288991a` (VERIFY-01, X07): `scripts/probes/x07_public_check_probe.py`
  rewritten — bare numeric literal no longer counts as support; PASS
  requires locatable evidence quote carrying object (radius/半径), unit
  (km/公里) and number, plus explicit local-model 支持 verdict;
  不支持/无法判断/unparseable/model-error are NOT support. Local unit
  checks of `parse_verdict`/`evidence_quote` all pass (offline); live
  retrieval run still needs outbound HTTPS + ollama (environment-dependent,
  not claimed here).
- ARCHIVE-01 partial: store schema bumped to v4 (learning_event_keys
  receipt columns); v2 wire restore compatibility test updated and green.
  Full restore-time discrimination of 11-table v3 / 13-table v3 / new
  contract layouts with unknown-layout rejection remains open for X05/X10.
- Full verification at `288991a`: `cargo test --workspace --offline`
  exit 0 (52 test groups ok; receipt
  `.project-local/runs/cargo-waveb-8.log`); Python full suite via
  `run_tests.sh --full`: 2346 passed / 7 skipped / 1 failed —
  `test_ci_classifier` unclassified `.cargo/config.toml`, fixed by
  registering `.cargo/**` under `vnext-rust-core` in
  `.worklab/project-validation.v1.yaml` (31/31 classifier tests green
  after). Environment: MSVC 14.44 stable toolchain via
  `.project-local/runs/x01-cargo-build-seal.bat`, ARCHEAXIS_PYTHON=.venv.
- Wave B status: REVISION-01 IMPLEMENTED_PENDING_AUDIT; EVENT-01
  IMPLEMENTED_PENDING_AUDIT; VERIFY-01 IMPLEMENTED_PENDING_AUDIT (offline
  evidence; live-run evidence environment-gated); ARCHIVE-01 PARTIAL.
