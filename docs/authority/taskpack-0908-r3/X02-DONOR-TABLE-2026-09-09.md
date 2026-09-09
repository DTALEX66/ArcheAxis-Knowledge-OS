# X02 minimal donor table (GOV03, REUSE-01) — 2026-09-09

Scope: the currently-called donor set of the M0 closed loop only. This is
not a review of all 1,246 manifest rows; the rest of
`LEGACY_MANIFEST.yaml` (baseline e9a7d2d, 1,246 rows) stays preserved and
unreviewed (INVENTORIED_NOT_SEMANTICALLY_REVIEWED),挂回 X13/F tasks.
Statuses: REUSE_IN_PLACE / ADAPT / MIGRATE_RUST / RETIRE_CANDIDATE / FROZEN.

| # | Donor path (git blob SHA @ d7d392d) | Behavior | License | Disposition | Callers | Regression evidence | Parent |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `app/integrations/deeptutor_bridge.py` (`38ec40e1`) | Read canonical truth, build replaceable projection, accept candidates into DeepTutor shell | MIT (project-owned) | REUSE_IN_PLACE (LANG03 controlled capability layer; Rust-authority read-only consumer) | `app/api/learning.py`, `app/integrations/__init__.py` | `tests/test_deeptutor_bridge.py` 4 passed 2026-09-09 | X02 |
| 2 | `app/adapters/deeptutor/authority.py` (`76f4f31c`) | Authority boundary adapter: blocks identity self-grant, gates review/accept | MIT (project-owned) | REUSE_IN_PLACE (identity semantics feed LANG05 contract work in X04) | `app/adapters/deeptutor/__init__.py`, bridge (#1) | covered via `tests/test_deeptutor_bridge.py` (4 passed) | X02 |
| 3 | `app/adapters/anki_zotero.py` (`799de71d`) | Longterm reference adapters for Anki/Zotero interoperability | MIT (project-owned) | REUSE_IN_PLACE (retained as FORMAT/INTEROP capability surface) | `tests/test_adapters_longterm.py`, bulk-adapter suite | `tests/test_adapters_longterm.py` 8 passed 2026-09-09 | X02 |
| 4 | `app/knowledge/due_queue.py` (`f9a13616`) | Due queue / scheduling projection on learning events (FSRS trajectory consumer side) | MIT (project-owned) | ADAPT (C05: FSRS adapter wiring + `event_key` producer identity remain open; EVENT-01 fix lands in X04/X08) | `app/api/learning.py` | `tests/test_axw051b_due_queue.py` 6 passed 2026-09-09 | X02 |
| 5 | `services/python-workers/` (18 modules; entry `worker_extract.py` `ba953e40`) | Isolated format/media/vision/web/evaluation capability workers (text, office, canvas, subtitles, transcribe, video, extract) | MIT (project-owned) | REUSE_IN_PLACE (LANG03; Rust owns main-path authority, workers never touch main DB directly — LANG02 boundary) | `crates/archeaxis-application` executor, `crates/archeaxis-api` runtime jobs/tests | `tests/workers/test_bulk_legacy_adapters.py` 9 passed 2026-09-09 | X02/X06 |

Aggregate regression run 2026-09-09 (via `scripts/ci/run_tests.sh`, dev run
root inside `.project-local`): 27 passed / 0 failed / 0 skipped in 0.60s,
Python 3.13.14, pytest 9.1.1, at branch head `d7d392d`.

## Unique-asset preservation (X02 r3_work item 1, 先保全唯一资产)

- `LEGACY_MANIFEST.yaml` remains the generated, non-hand-edited inventory of
  1,246 tracked legacy rows (12 categories; 1,243 unchanged / 3 modified at
  head as of its audit). No row is marked absorbed by this table; statuses
  above are R3 donor-scope judgments only.
- No donor in this table is a deletion/retirement target this wave; the
  Python→Rust migration order is owned by LANG02 slices in X04/X05/X07 with
  per-module ledgers (GOVERNANCE-MIGRATION.md), not by bulk rewrites.
- Cleanup exclusions (X14/GOV04 coordination): none of these donor paths may
  enter any cleanup candidate list — they are current-loop call-chain assets.

## What this table does NOT claim

- Not a semantic review of all legacy assets (that stays X13/M1 per GOV03).
- Not a migration-completion claim for any row (LANG07: "Rust占比提高或旧文件
  减少不算完成").
- Not a performance/accuracy claim; behavior evidence is the passing test
  set above only.

Rollback: delete this file; donors are untouched working-tree assets.
