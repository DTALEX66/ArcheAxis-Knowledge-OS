# R00 baseline review — AAK 2026-09-10 pack vs actual repository state

Read-only slice work: no product code changed, no cleanup, no `.hermes` access.
Method: read the R3-0908 live ledger (`docs/authority/taskpack-0908-r3/EXECUTION.md`),
the GLM-session handoff addenda (`HANDOFF-2026-09-09.md`), `git log`, and the
archive/domain/API sources cited by the pack. Slice text comes from `TASKPACK.md`
in this directory.

## 1. Locked baseline

| Field | Value |
| --- | --- |
| Branch | `codex/full-loop-0906` |
| HEAD | `985a219` (ARCHIVE-01 slice; pushed, synced with origin, 0/0) |
| `main` | `4ca46ea` (untouched) |
| Worktree | clean except untracked `.zcode/` (GLM/zcode session-local, not ours to commit) |
| Current live plan | AAK-FOLLOWUP-20260908-R3, `docs/authority/taskpack-0908-r3/EXECUTION.md` |
| Pack under review | AAK 2026-09-10 follow-up, 17 slices R00–R16 (`TASKPACK.md` here) |

HEAD is later than the pack's audit base `cbe253b`, so per R00 every inherited
defect was re-checked instead of assumed, and no earlier fix was reverted.

## 2. Inherited P1 defects re-checked at `985a219`

| Defect | State at HEAD | Evidence |
| --- | --- | --- |
| review `new_body` could overwrite body (R02) | fixed | `288991a` REVISION-01: accept/reject/deprecate + `new_body` rejected; only `modified` creates a superseding revision; single transaction |
| learning same-key/different-content silently deduped (R05) | fixed | `288991a` EVENT-01: persistent `event_key` bound to item + payload hash; retry returns original receipt; conflict rejected; missing key rejected (schema v4) |
| `6371`/absence-of-error counted as support (R06) | partial | `288991a` VERIFY-01: probe requires locatable evidence quote with object+unit+number plus explicit 支持 verdict; offline unit checks green, live retrieval env-gated |
| v3 archives (11-table and 13-table) not distinguished (R03) | fixed | `985a219` ARCHIVE-01: layout resolved from the manifest table set; unknown v3 layout and missing-table current archives rejected; additive nullable columns filled NULL, unknown column rejected; 5 new tests |

## 3. Slice map R00–R16 to current state

| Slice | Pack scope | State | Evidence / what remains |
| --- | --- | --- | --- |
| R00 | lock baseline + single entry | IN_PROGRESS | this review; entry flip awaits package verification (`PACKAGE-STATUS.md`) |
| R01 | cache growth-stop + capacity baseline | PARTIAL | `65b28f9` `.cargo/config.toml` redirects bare cargo to `.project-local/build/cargo` (root `target/` growth stopped; PATH-01 diff); `55731ad` X14 early read-only census (20.29 GiB observed / 115,231 files; `.hermes` opaque; D: free 234.0 GiB). Remaining: unify every other cache into the agreed `.project-local` locations, and report inclusion/exclusion + logical vs physical + volume-free delta |
| R02 | body immutability + revision | IMPLEMENTED_PENDING_AUDIT | `288991a` (+ regression in `review_transaction.rs`) |
| R03 | v3 archive backward compatibility | IMPLEMENTED_PENDING_AUDIT | `985a219` (see §2). Gap to record honestly: fixtures reconstruct the two historical v3 shapes from schema history; a **non-empty v3 sample produced by the old implementation** is still required by the acceptance text |
| R04 | host identity / credential isolation | PARTIAL | R2-era C02 (`bb90422`, `9e71c21`) session-actor guard + real-process escalation test. Remaining: unknown launch actor rejection and real host-signed machine/human credential scope (R3 X04 slice) |
| R05 | learning-event idempotency + FSRS | PARTIAL | `288991a` covers event identity/retry/conflict/missing-key. Remaining: wire the single scheduling authority to the reused FSRS/Anki bridge and prove due dates come from that scheduler, not a temporary interval |
| R06 | public check vs cloud cross-check | PARTIAL | `288991a` probe rewrite; cloud cross-check needs approved credentials -> `BLOCKED_EXTERNAL` if absent (offline use stays deliverable) |
| R07 | non-empty legacy asset migration | OPEN | R2 left demo staging only (legal type, hash+row verify, atomic staging, inserted/reused). Real non-empty snapshot migration, attachments and learning history diffs remain |
| R08 | unified conversion pipeline + quality display | OPEN | R2 has real text-worker execution and executor tests; the unified job contract across native PDF / scanned PDF or screenshot / Markdown-text, with anchors, retry and quality display, is not built |
| R09 | source<->note navigation + downstream invalidation | PARTIAL | R2 C03: anchor->knowledge reverse lookup, supersede chain, superseded-not-current, `active_only`. Remaining: consumption-entry version checks (questions, caches, machine context, result write-back) and restart-consistent validity |
| R10 | DeepTutor--Core and usable human entry | PARTIAL | Host solved and stable (doctor PASS after 24h+, real Chinese answers/learning path). Remaining: Core wiring and the full import->read->explain->practice->correct->review->resume journey in a real Windows entry |
| R11 | real machine learning + two-way feedback | PARTIAL | qualification endpoint, `active_only`, and the machine correction loop (`cbe253b`, end-to-end + restart consistency). Remaining: real MCP/equivalent client, observable task, independent unseen-example verification |
| R12 | safe cleanup + terminal capacity proof | PARTIAL | X14 early read-only census only; no deletions. Remaining: per-path authorized cache removal with before/after same-scope measurement and rebuild/restart re-test |
| R13 | Windows usable package + same-source evidence | OPEN | no one-click candidate, dependency/port diagnostics, or install-package hash bound to a tested SHA |
| R14 | Q00 independent re-audit | GATE (not run) | independent GPT only; never self-signed |
| R15 | M1 formats / interop / language governance | PARTIAL | GOV01–GOV05 and LANG01–LANG07 partially landed; 16-format matrix sign-off and Obsidian vault/canvas round-trip remain |
| R16 | Q01 completeness + capacity re-audit | GATE (not run) | follows R15 |

## 4. Verification commands used

- `git log --oneline -8`, `git status --short --branch`, `git rev-list --left-right --count`
- `cargo test --workspace --offline` via `.project-local/runs/cargo-full-workspace.bat`
  (exit 0, 52 groups; log `.project-local/runs/cargo-archive-01-full.log`)
- `pwsh -NoProfile -File scripts/ci/run_tests.ps1 --full`: **2347 passed / 7 skipped /
  0 failed**, exit 0 (log `.project-local/runs/r00-python-full-0910.log`). That target
  set is `tests` + `knowledge_base/tests` (2354 collected - 7 skipped); the separate
  `integration-tests` group is 47 tests and was green in the R2 refresh.
- `python scripts/check_repository_conventions.py --source worktree` (passed)
- `python scripts/check_architecture.py` (passed)
- archive slice: `.project-local/runs/archive-245.log` (7/7 groups ok)

## 5. Blockers and next step

- **BLOCKED_RESOURCE**: the pack's packaged artifacts (`EXECUTOR-START.md`,
  `TASKS.json`, `verify_package.py`, `reference-r2/`) are absent, so package
  verification and plan registration cannot complete. See `PACKAGE-STATUS.md`.
- Runnable next slices that do not need the frozen package: R01 cache unification
  + capacity reporting, R03's old-implementation non-empty v3 fixture, R04 unknown
  launch-actor rejection, R05 FSRS wiring on the verified donor.
