# R14 audit evidence index (0910 pack) — 2026-09-12

Purpose: give an independent auditor every pointer needed to re-check the
current claims, and state plainly what is **not** claimed. This file adds no
authority of its own; `EXECUTION.md` + `STATE.json` remain the live record.
Nothing here is a self-signed audit: Q00/Q01 remain for independent GPT only.

## 0. Baseline and package

| Item | Value |
| --- | --- |
| Branch | `codex/full-loop-0906` (local == origin at the time of writing) |
| `main` | `4ca46ea` (untouched) |
| Live plan entry | `docs/authority/taskpack-0910-r3/EXECUTION.md`, progress in `STATE.json` |
| Supersession | SUP-018 in `DECISION_SUPERSESSION_LEDGER.yaml` |
| Package install | 13 root files + `reference-r2/` (15 files), single level |
| Package verification | `python -X utf8 docs/authority/taskpack-0910-r3/verify_package.py` → `PASS: hashes, 17 task dependencies, all 23 original tasks retained`, exit 0 |

Package verification proves file integrity and dependency validity only — not a
product audit. It must run in UTF-8 mode on this machine (GBK locale); the frozen
files were not modified.

## 1. Slice evidence (R00–R05)

| Slice | Status | Evidence to re-run | What is NOT claimed |
| --- | --- | --- | --- |
| R00 | IMPLEMENTED_PENDING_AUDIT | `R00-BASELINE-REVIEW.md` (17-slice map, inherited defects re-checked at `985a219`); entry pointers in `AGENTS.md` §6 + both authority indexes; `workspace/intake/2026-09-10-next-taskpack-0910.md` | Entry registration is not an audit pass |
| R01 | IMPLEMENTED_PENDING_AUDIT | `R01-CAPACITY-BASELINE.md`; census receipt `.project-local/runs/r01-census.json`; build proof `.project-local/runs/cargo-build-api.bat` | Logical bytes only (allocated space not measured); packaging-side path diff and `__pycache__` redirect are open |
| R02 | IMPLEMENTED_PENDING_AUDIT | `cargo test -p archeaxis-domain` → 9 groups ok (`r02-domain.log`), incl. `accept_with_new_body_is_rejected_and_body_stays_immutable`, `accept_commits_status_and_one_event_atomically`, `failed_review_leaves_no_partial_state`, `modified_creates_traceable_successor`; code `288991a` + `cbe253b` | — |
| R03 | IMPLEMENTED_PENDING_AUDIT | `cargo test -p archeaxis-archive` → 7 groups ok (`r03-archive-v2.log`); four genuine v3 fixtures exported by the historical implementation at `968c479`/`a2dbef5`/`60b355a`/`3d65609` under `crates/archeaxis-archive/tests/fixtures/v3-{ten,eleven,twelve,thirteen}-tables` (each with `PROVENANCE.txt`); layout logic in `crates/archeaxis-archive/src/lib.rs` (`V3_LAYOUTS`) | v1 (7 tables, no `workspace_meta`) is explicitly unsupported; fixtures had one added final LF (documented normalisation) |
| R04 | IMPLEMENTED_PENDING_AUDIT | `cargo test -p archeaxis-api` exit 0; real-process test `unknown_launch_actor_is_rejected_and_never_grants_human_authority` in `crates/archeaxis-api/tests/launch_auth.rs`; fix in `crates/archeaxis-api/src/launch.rs` (`launch_auth` 6 tests, `r04-api.log`) | Real host-signed/host-held machine & human credential scope is **not** implemented |
| R05 | **IN_PROGRESS** | Worker `services/python-workers/learning/worker_schedule.py` (`78656a1`) + adapter `crates/archeaxis-application/src/scheduler.rs` (`40391f6`); `tests/test_worker_schedule.py` 8 passed; `cargo test -p archeaxis-application` → adapter tests 5 ok (`r07-scheduler-adapter.log`) | **The learning-events API still does not call the adapter**, so `learning::suggest_next_interval` (the 1/2/4/7/14 ladder) remains the Rust-side default. R05 is not done |

Baseline suites at the same head: `cargo test --workspace --offline` exit 0 /
52 groups (`r03-full-workspace.log`, `r04-full-workspace.log`); Python
`run_tests.ps1 --full` **2355 passed / 7 skipped / 0 failed**
(`r07-python-full.log`); architecture guard passed; conventions gate reports only
the two frozen-package issues below.

## 2. Outstanding slices and the next concrete step

- **R05 (finish)**: parametrize the keyed review path with `Option<i64>`
  (`None` = scheduler unavailable) so the adapter's value is used; record an
  unavailable scheduler as an *unscheduled* review (`next_review` NULL + explicit
  marker) and assert it in tests. Design guidance in `HANDOFF-2026-09-11.md`.
- **R06**: separate run status from support/refutation/undetermined; cloud
  cross-check needs approved credentials, otherwise `BLOCKED_EXTERNAL` (offline
  use stays deliverable).
- **R07**: non-empty legacy migration from a consistent read-only snapshot;
  per-asset hash/relationship/learning-history differentials.
- **R08**: one job contract over native PDF / scanned PDF or screenshot /
  Markdown-text with anchors, retry and quality display.
- **R09**: consumption-entry version checks (questions, caches, machine context,
  result write-back) after revision/revocation.
- **R10**: DeepTutor ↔ Core entry; note the host processes are currently **down**
  (:8001/:3782); ollama :11434 was reachable.
- **R11**: real MCP/equivalent client, observable task, independent
  unseen-example verification.
- **R12**: per-path authorized cache removal with same-scope before/after.
- **R13**: Windows candidate package bound to a tested SHA.
- **R14/R16**: independent GPT gates only; R15 M1 formats/interop/language.

## 3. Known deviations and environment notes (do not re-diagnose)

1. **Frozen pack files** `TASKS.json` and `MANIFEST.json` lack a final LF, so the
   conventions gate always reports those two lines. Not patched: `TASKS.json` is
   hashed by `MANIFEST.json`, so adding a byte would invalidate
   `verify_package.py`. Owner options: re-issue the pack, or authorize an
   exemption for frozen snapshots. See `PACKAGE-STATUS.md`.
2. **Scratch worktree trap**: a git worktree placed under the repo inherits the
   main `.cargo/config.toml` `target-dir`; mixing v3/v4 artifacts caused 6 *false*
   test failures. Wrappers under `.project-local/runs/` now pin
   `CARGO_TARGET_DIR`.
3. **py-fsrs fuzzing**: intervals are fuzzed by default; the donor now takes an
   additive `enable_fuzzing` (default unchanged) and the product worker requests
   `False` so replay/restart comparisons are stable.
4. **Toolchain**: builds need the MSVC wrapper
   (`.project-local/runs/cargo-full-workspace.bat`); the default GNU toolchain
   lacks gcc/dlltool and fails on `libsqlite3-sys` — that is not a code defect.
5. **Evidence location**: receipts live under `.project-local/runs/` (ignored, not
   uploaded); only sanitized summaries and hashes belong in the repository.

## 4. Reproduce

```
python -X utf8 docs/authority/taskpack-0910-r3/verify_package.py
cmd /c call .project-local\runs\cargo-full-workspace.bat
cmd /c call .project-local\runs\cargo-test-pkg.bat archeaxis-archive
cmd /c call .project-local\runs\cargo-test-pkg.bat archeaxis-application
pwsh -NoProfile -File scripts/ci/run_tests.ps1 --full
python scripts/check_repository_conventions.py --source worktree
python scripts/check_architecture.py
```
