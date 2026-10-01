# AAOS backend P0–P6 real multiformat loop — verification evidence (2026-10-01)

Evidence class legend: `REAL` > `INTEGRATED` > `SYNTHETIC` > `SIMULATED` > `NO_EVIDENCE`.
A claim is only `REAL` when real input bytes reached the real production process and the
result was read back. Test-suite presence alone is never `REAL`.

## 0. Subject identity

| Item | Value |
| --- | --- |
| Branch | `codex/dsh-aaos-real-multiformat-loop-20261001` |
| Base | `origin/codex/Audit` = `1a981a4482b01f31989074e79c82a63400aa07a7` |
| Worktree | `.project-local/worktrees/dsh-backend-loop-20261001` |
| Core binary SHA-256 | `a2d2746edb752fd7034940f129e874093fd71c35eea5aa65ac718eeeefeb8e29` |
| Rust toolchain used | `stable-x86_64-pc-windows-gnu` rustc 1.97.1 + MinGW gcc 16.2.0 |
| Worker interpreter | `.venv\Scripts\python.exe` (Python 3.13.14) |
| Storage schema version | `6` |
| Release state | `FROZEN` (unchanged) |

### Why the base is not the root checkout's HEAD

The prompt named `D:/All projects/ArcheAxis-Knowledge-OS` as the working directory, but
that checkout's `codex/Audit` HEAD (`6621aab7`) **is an ancestor of** `1a981a44` and does
not contain the authority documents the same prompt requires reading:
`AAOS-EXECUTION-PACKET-20261001.md`, `AAOS-UNFINISHED-TASKS-20261001.md`,
`AAOS-ALL-TASKS-DISPOSITION-20261001.csv`, `AAOS-ALL-TASKS-LEDGER-20261001.json`,
`AAOS-ERRORS-BLOCKERS-20261001.md` and `AAOS-GREEN-REPOSITORY-BOUNDARY-AUDIT-20261001.md`
are absent at `6621aab7` and present at `1a981a44`. `origin/codex/Audit` also points at
`1a981a44`, while the **local** `codex/Audit` ref was stale. The Owner chose the
`1a981a44` base; nothing was lost, because `6621aab7` is its ancestor.

Root-level facts observed before any change:

* `AUTHORITY.md` is absent → `AUTHORITY_REFERENCE_MISSING` (consistent with the audit).
* Root checkout has 1 modified tracked file and 22 untracked paths; all were left
  untouched. This work happened in an isolated worktree.
* Local `main` (`d8f99a63`) differs from `origin/main` (`59498723`); `main` is not an
  ancestor of `1a981a44`. Not resolved by this branch.

## 1. Toolchain finding (blocks nothing, but was not obvious)

The default `stable-x86_64-pc-windows-msvc` rustup toolchain is **broken on this
machine**: its `bin` contains `cargo.exe` but **no `rustc.exe`**, and no MSVC `link.exe`
or `cl.exe` is resolvable. `cargo test` therefore dies with
`could not execute process 'rustc -vV' (never executed)`.

A working combination exists and was used:

* rustc/cargo from `~\.rustup\toolchains\stable-x86_64-pc-windows-gnu\bin` (rustc 1.97.1)
* linker `gcc.exe` 16.2.0 from
  `D:\All projects\OS External Configuration\toolchains\mingw\mingw64\bin`
* `CARGO_TARGET_DIR` pointed inside the worktree's git-ignored `.project-local\build`

Recorded as an environment condition, not a product defect.

## 2. Baseline and post-change test signal

Both runs used the same interpreter and `ARCHEAXIS_PYTHON` contract.

| Run | Command | Result |
| --- | --- | --- |
| Baseline, `ARCHEAXIS_PYTHON` unset | `cargo test -p archeaxis-api --no-fail-fast` | **35 passed, 7 targets failed** |
| Same, `ARCHEAXIS_PYTHON` set | `cargo test -p archeaxis-api --no-fail-fast` | **all 28 targets pass, EXIT=0** |
| Per-format suites | `cargo test -p archeaxis-application --no-fail-fast` | **all targets pass, EXIT=0** |
| Launcher suite after this branch's fix | `python -m pytest tests/test_backend_runtime_safety.py` | **33 passed** |
| Launcher consumers | `pytest tests/test_core_launch.py tests/test_desktop_launch.py tests/test_r6_version_release_freeze.py` | **28 passed** |

The 7 baseline failures were **environmental, not product defects**. The dominant cause is
the project's own Python-selection contract: worker-backed tests
`expect("run cargo via scripts/runtime/dev.py to select the exact Python")` and panic with
`NotPresent` when `ARCHEAXIS_PYTHON` is unset. Setting it to an installed interpreter
resolves all of them. **This is why a reviewer must not read a bare `cargo test` failure
as a regression.** Conversely, `ARCHEAXIS_PYTHON` being unset in a real launch is a
genuine product-relevant condition: the Core then reports
`schedule_authority:"unavailable"` and stores an unscheduled event rather than inventing a
schedule.

## 3. P0–P6 status — measured, not inferred

### P0 Authority / Plugin Kernel — `PARTIAL`

* Real process start/stop, health handshake and identity binding: **REAL**. A Core was
  started with the production argv and a v2 launch document and answered
  `GET /api/v1/system/version` with the launched `session_id` and `workspace_db`.
* Single-writer boundary: `Store::open` takes an exclusive OS lock on
  `<db>.writer.lock`, owns the only connection on a dedicated thread, and rejects `e:`,
  UNC, `:memory:`, `..`, reparse points and link-count≠1. Verified by source read; not
  independently re-executed here.
* Not closed: the "plugin kernel" as a general capability registry. The authoritative
  enabled-capability set is two **hard-coded** route tables
  (`crates/archeaxis-application/src/attempts.rs` and
  `services/python-workers/transport/text_ndjson.py`), not a registry.

### P1 Source / Format / Knowledge — `PARTIAL`, and **NOT_REACHABLE for every non-text format**

This is the headline result of this branch.

* Import → job → execute → transform → anchored candidate → V3 readback ran end to end on
  the real Core for **text**, with a real `source_id`, `transform_id`, `knowledge_id` and
  `anchor_id`, and a real raw `sha256`.
* Against the **verified** golden corpus (all 10 fixture SHA-256 values re-checked against
  `tests/fixtures/golden/manifest.json` — all `MATCH`), a production launch converted
  **1 of 10**:
  `{REACHABLE: 1, FAILED_AT_ROUTE: 9}`. Every non-text format failed with
  `Core execution ended without a terminal receipt`.
* Root cause (verified by direct source read): `crates/archeaxis-api/src/main.rs` calls
  `Executor::open(...)`, and `crates/archeaxis-application/src/executor.rs` seeds exactly
  one route, `("text.extract", default_worker, false)`. The additional
  `(capability, worker)` routes are only ever registered through
  `Executor::open_routes`, whose call sites are **all in test code**. The configured worker
  script advertises only `["text.extract"]`
  (`services/python-workers/transport/text_ndjson.py`).

Consequence to state plainly: the per-format Rust suites passing does **not** mean the
product can convert a PDF. It means the executor *can* when a test registers the route.

Formats that additionally lack a reachable engine, named separately from the route gap:

| Format | Status | Why |
| --- | --- | --- |
| audio → ASR transcription | `NO_ROUTE` | `media/worker_transcribe.py` has no `--staging-root` sidecar mode and no capability in either route table. |
| video decode | `NO_ROUTE` | `media/worker_video.py` same; also needs `ffmpeg`, which is installed but not on `PATH`. |
| webpage fetch | `NO_ROUTE` | `web/worker_webpage.py` same. |
| image caption / VL | `BLOCKED` | needs an Ollama endpoint at `127.0.0.1:11434` with `qwen2.5vl:7b`; no `ollama` binary and nothing listening. |
| image OCR | `ROUTE_GAP` + env | `tesseract` 5.5.0 is installed at `C:\Program Files\Tesseract-OCR\tesseract.exe` but **not on `PATH`**, and the session's `TESSDATA_PREFIX` points at a non-existent directory. |

`media.probe` is **not** transcription — it reads the container header only and says so.

### P2 Search / Learning Plan / Course — `PARTIAL`

* Lexical search: **REAL**. `GET /api/v1/search` found the imported source and its
  transform with `source_found: true`.
* Semantic/embedding/reranker: **ABSENT in the Core**. `crates/archeaxis-domain/src/search.rs`
  is FTS5 only, and there is no embedding/vector/rerank code anywhere under `crates/`.
  The only vector code lives behind the legacy Python `/kb` sub-app, whose default
  "embedding" is a character n-gram hash, not a model.
* UI contract obligation: when no provider exists the UI must receive an explicit
  `unavailable`, which the contract document now specifies.

### P3 Human Learning — `PARTIAL (SYNTHETIC protocol evidence)`

* Real FSRS: **REAL dependency**. `fsrs>=5.0` is declared, and the scheduler runs as a
  bounded Python subprocess (`crates/archeaxis-application/src/scheduler.rs`). In the M0
  run the review path reported `schedule_authority:"fsrs"` with a real `due`,
  `stability`, `difficulty` and `step`.
* Idempotency: **REAL**. A replayed `client_event_id` returned `duplicate: true` with the
  original receipt.
* Cold restart readback: **REAL**. After stopping and restarting the Core on the same
  database, `answer`, `next_review` and the schedule were identical.
* Mastery: `mastery_projection.closed == false` is a deliberate open sentinel, not a
  defect. `correct_streak` is re-derived per read.
* **Not closed by real human first use.** The M0 receipt self-declares
  `evidence_level: "SYNTHETIC"` and `real_m0_verified: false` because the answer, the
  source and the human review action are fixtures. A synthetic pass is not a human first
  use, and this branch does not claim one.
* Reachable stub: `POST /api/v1/learning/events` without `schedule_state` still reports
  `placeholder_ladder` with a `null` next review — the 1/2/4/7/14 ladder. The UI must
  distinguish `fsrs` from `placeholder_ladder` from `unavailable`.

### P4 Machine Loop — `PARTIAL`, `STUB`-bound

* Machine task receipt write and readback, including `retest_of` binding to the original
  failure and binding to the corrected successor knowledge version: **REAL** (receipts are
  written by a machine principal and are immutable).
* Human correction: **REAL**, and it is the **only** correction path
  (`POST /knowledge-items/{id}/review-decisions` with `action:"modified"` creating a
  successor revision). A machine principal is refused.
* **No real model inference happened.** The M0 run posted `model_version:"stub/local-stub"`
  and `failure:"declared stub model, no real inference performed"`. The machine leg is
  therefore protocol evidence, not model evidence.
* **Gaps:** there is no HTTP writer for the machine competence ledger, and no endpoint
  that *starts* a retest — `retest_of` is only a field the machine fills in when it
  self-reports. `GET /learning/items/{item_key}/state` returns the fixed
  `machine: {"status":"not_recorded"}` even when receipts exist.

### P5 / P6 Persistence / Local Green — `PARTIAL`

* Online backup, a deliberate mutation, and a verified restore: **REAL**.
  `--maintenance-backup` exited `0` (`schema_version 6`); after deleting all
  `learning_events` rows and restoring, `counts_after == counts_before` exactly, with
  `verified: true` and a distinct `counts_mutated` proving the restore did work.
* Cold restart with full state readback: **REAL** (see P3).
* **Not closed:** the real Legacy copy migration. The M0 probe reported
  `legacy_migration: {"skipped": "legacy database not present"}` and the run's sole
  validation error is `legacy migration not verified`. That leg is **paused by the Owner**
  and is reported `NOT_EXECUTED`, never `PASS`. In-place Green replacement and
  release/tagging remain `FROZEN` / Owner-gated.
* Verdict for this branch: **`NOT_READY`**. Not `LOCAL_GREEN_READY_FOR_OWNER_REVIEW`,
  because P1 non-text reachability and the Legacy leg are both open.

## 4. Per-key disposition against the disposition ledger

Lane `BACKEND_FRONTEND_LOOP` (54 keys). Evidence level is the highest actually reached.

| Key | Maps to | Status | Evidence | Basis |
| --- | --- | --- | --- | --- |
| `AA-BE-01` Provider Consumption Contract | A03/A11 | `PARTIAL` | `NO_EVIDENCE` | No provider was consumed; no embedding/model provider route exists. |
| `AA-BE-02` Multiformat Intake unified contract | A05 | `PARTIAL` | `REAL` (intake) / `FAILED` (convert) | Intake accepts every real fixture with `202`; conversion is text-only. |
| `AA-BE-03` OCR | A05 | `BLOCKED` | `NO_EVIDENCE` | Route not registered in production; tesseract present but off `PATH` and `TESSDATA_PREFIX` stale. |
| `AA-BE-04` ASR | A05 | `BLOCKED` | `NO_EVIDENCE` | No route, no sidecar mode; model path mis-resolves. |
| `AA-BE-05` Retrieval | A06 | `PARTIAL` | `REAL` | Lexical FTS5 only; no vector/reranker route. |
| `AA-BE-06` General Learning | A09/A10 | `PARTIAL` | `SYNTHETIC` | General-only manifest validated locally; no real domain content. |
| `AA-BE-07` Human Learning | A08 | `PARTIAL` | `SYNTHETIC` | Real FSRS + real persistence; synthetic actions; no real human first use. |
| `AA-BE-08` Real Local Machine Loop | A07/A14 | `PARTIAL` | `SYNTHETIC` | Protocol path works; declared stub model, no inference. |
| `AA-BE-09` Backup / Restore | A13 | `PARTIAL` | `REAL` | Verified round trip for exported tables; **learning/machine tables are not exported** (§5). |
| `AA-BE-10` Legacy Copy Migration | A13 | `NOT_EXECUTED` | `NO_EVIDENCE` | Paused by the Owner. Not attempted, not passed. |
| `GJ-01` real multiformat input | A05 | `PARTIAL` | `REAL` | 10 real verified fixtures imported; 9 formats fail to convert. |
| `GJ-02` Source → Knowledge | A04/A05 | `REAL` | `REAL` | Text source produced anchored candidate + V3 with real hashes. |
| `GJ-03` Search | A06 | `REAL` | `REAL` | Lexical hit bound to `source_id` and `transform_id`. |
| `GJ-04` Human Learning | A08 | `PARTIAL` | `SYNTHETIC` | As `AA-BE-07`. |
| `GJ-05` Human Restart | A08 | `REAL` | `REAL` | Identical state/schedule after same-database restart. |
| `GJ-06` Machine Learning Loop | A07/A14 | `PARTIAL` | `SYNTHETIC` | As `AA-BE-08`. |
| `GJ-07` Machine Restart | A07/A14 | `PARTIAL` | `SYNTHETIC` | Machine receipts survived restart in the M0 run. |
| `GJ-08` Backup / Restore | A13 | `PARTIAL` | `REAL` | As `AA-BE-09`. |
| `GJ-09` Legacy Migration | A13 | `NOT_EXECUTED` | `NO_EVIDENCE` | Owner-paused. |
| `GJ-10` Exact-source Candidate | A13 | `REAL` | `REAL` | Candidate bound to persisted transform + UTF-16 selection + raw hash. |
| `GJ-11` Native Acceptance | A12/A15 | `NOT_EXECUTED` | `NO_EVIDENCE` | Desktop binary not launched on this branch; UI writer owns that surface. |
| `ATLAS-0929:REQ-SOURCE-001` | CAP-0010 | `REAL` | `REAL` | Original bytes preserved, hash verified. |
| `ATLAS-0929:REQ-CONVERT-001` | CAP-0020 | `PARTIAL` | `REAL` | Text only; 9 formats fail. |
| `ATLAS-0929:REQ-EVIDENCE-001` | CAP-0030 | `REAL` | `REAL` | Anchor + UTF-16 range + quote validated by the Core. |
| `ATLAS-0929:REQ-LEARNING-001` | CAP-0040 | `PARTIAL` | `SYNTHETIC` | As `AA-BE-07`. |
| `ATLAS-0929:REQ-INTEROP-001` | CAP-0100 | `PARTIAL` | `REAL` | Backend launcher credential contract fixed (see §5). |
| `ATLAS-0929:REQ-SEARCH-001` | CAP-0110 | `PARTIAL` | `REAL` | Lexical only. |
| `ATLAS-0929:REQ-DESKTOP-001` | CAP-0120 | `NOT_EXECUTED` | `NO_EVIDENCE` | Out of this branch's write set. |
| `ATLAS-0929:REQ-BACKUP-001` | CAP-0140 | `PARTIAL` | `REAL` | As `AA-BE-09`. |
| `ATLAS-0929:REQ-IDENTITY-001` | — | `REAL` | `REAL` | Naming/identity unchanged; no rename performed. |
| `R6-LIVE-LEDGER:A00` | — | `PARTIAL` | `REAL` | Authority re-read live; `AUTHORITY.md` still absent. |
| `R6-LIVE-LEDGER:A01` | — | `REAL` | `REAL` | Release `FROZEN` respected; no tag/release created. |
| `R6-LIVE-LEDGER:A03` | — | `PARTIAL` | `NO_EVIDENCE` | Capability registry still two hard-coded route tables. |
| `R6-LIVE-LEDGER:A04` | — | `REAL` | `REAL` | V3 write/read path exercised with real hashes. |
| `R6-LIVE-LEDGER:A05` | — | `PARTIAL` | `REAL` | One format reachable; nine not. |
| `R6-LIVE-LEDGER:A06` | — | `PARTIAL` | `REAL` | Lexical only. |
| `R6-LIVE-LEDGER:A07` | — | `PARTIAL` | `SYNTHETIC` | No real model. |
| `R6-LIVE-LEDGER:A08` | — | `PARTIAL` | `SYNTHETIC` | No real human first use. |
| `R6-LIVE-LEDGER:A09` | — | `PARTIAL` | `SYNTHETIC` | General-only. |
| `R6-LIVE-LEDGER:A10` | — | `PARTIAL` | `SYNTHETIC` | First renderer only. |
| `R6-LIVE-LEDGER:A11` | — | `NO_EVIDENCE` | `NO_EVIDENCE` | No provider executed. |
| `R6-LIVE-LEDGER:A13` | — | `PARTIAL` | `REAL` | Backup/restore real; migration paused; export set incomplete. |
| `R6-LIVE-LEDGER:A14` | — | `PARTIAL` | `SYNTHETIC` | Full loop proven only with fixtures. |
| `R6-LIVE-LEDGER:A15` | — | `NOT_EXECUTED` | `NO_EVIDENCE` | Independent G01–G14 qualification not run. |
| `M0-OVERLAY:P0` | — | `PARTIAL` | `REAL` | See §3. |
| `M0-OVERLAY:P1` | — | `PARTIAL` | `REAL` | One of ten formats reachable. |
| `M0-OVERLAY:P2` | — | `PARTIAL` | `REAL` | Lexical only. |
| `M0-OVERLAY:P3` | — | `PARTIAL` | `SYNTHETIC` | Real FSRS, synthetic actor. |
| `M0-OVERLAY:P4` | — | `PARTIAL` | `SYNTHETIC` | Stub model. |
| `M0-OVERLAY:P5` | — | `PARTIAL` | `REAL` | No migration. |
| `M0-OVERLAY:P6` | — | `NOT_READY` | `NO_EVIDENCE` | See §3. |
| `DP-GIT-01` branch/commit semantic audit | — | `REAL` | `REAL` | Base divergence documented in §0. |
| `DP-F01` real text quality roundtrip | — | `REAL` | `REAL` | Text round trip through the production shape. |
| `DP-A11` research contract gap analysis | — | `NOT_EXECUTED` | `NO_EVIDENCE` | Not started. |

Lane `OWNER_GATE` (4 keys) — all remain `BLOCKED_BY_OWNER_DECISION`, none attempted:

| Key | Requirement | Status |
| --- | --- | --- |
| `RECORD-0928:GJ-12` (`A15`) | Independent audit / Local Green qualification | `BLOCKED` |
| `RECORD-0928:GJ-13` (`A16`) | Green Owner Gate | `BLOCKED` |
| `R6-LIVE-LEDGER:A02` | Resource-root environment authority | `BLOCKED` |
| `R6-LIVE-LEDGER:A16` | P0–P6 closure + real migration + backup/replace/rollback | `BLOCKED` |

## 5. Defects found and fixed, or found and left open

### Fixed on this branch

1. **Backend launcher machine credential was sent in a header the Core never reads.**
   `scripts/release/backend_launcher.py` published the machine token as
   `x-archeaxis-machine-token`. `crates/archeaxis-api/src/launch.rs::authenticate` reads
   only `x-archeaxis-launch-token` and matches it against either token. Impact was
   **latent** (the launcher only issued human `GET`s), but any future machine call using
   those credentials would have been silently attributed to the **human** actor instead of
   being refused — an identity downgrade with no visible error.
   Fix: a `credential(tokens, role)` helper that selects the token by principal and always
   sends it in `x-archeaxis-launch-token`, plus an opt-in `role=` on `call()`. Covered by a
   new regression test written RED-first (`AttributeError` before the fix, passing after).
   `tests/test_backend_runtime_safety.py`: **33 passed**; launcher consumers: **28 passed**.

### Found and left open (each needs its own decision)

2. **Format routes are not registered in the production binary** (P1 headline). Largest gap
   between "works in tests" and "works in the product". Needs a route-enablement mechanism
   plus a regression test that launches the production shape and converts one real fixture
   per format. Not attempted here because choosing the enablement mechanism is an
   architectural decision and the R6 boundary says to wire only what the current loop
   requires. **Owner decision requested.**
3. **Backup does not carry learning or machine state.** `EXPORT_TABLES` in
   `crates/archeaxis-archive/src/lib.rs` omits `machine_tasks`, `learning_assessments` and
   `card_references`, so a verified restore still loses them. The M0 probe's restore check
   cannot catch this because it only counts knowledge/review/learning tables.
4. **`GET /sources/{id}/jobs/{job_id}/transform` filters `kind='text'`**, so a non-text
   transform is unreadable through the source-scoped route even when the job succeeded.
5. **ASR / video / webpage workers cannot be launched by the Core at all** (no
   `--staging-root` sidecar mode, no declared capability).
6. **Stale environment resolution.** `TESSDATA_PREFIX` points at a non-existent directory;
   the ASR model path in `media/worker_transcribe.py` resolves relative to the worktree and
   misses the real model library.
7. **Contract drift.** `packages/contracts/v1/openapi-outline.yaml` declares five
   unregistered routes and omits several real ones. Superseded for UI work by
   `docs/current/AAOS-PRODUCTION-HTTP-CONTRACT-20261001.md`.
8. **`docs/current/DSH-BACKEND-CONTRACT-20260927.md`** lists `POST /jobs/{id}/receipts` in
   its 30-route table; that route is test-only and answers `404` in production.

## 6. Delivered artifacts

| Artifact | Kind | Why |
| --- | --- | --- |
| `docs/current/AAOS-PRODUCTION-HTTP-CONTRACT-20261001.md` | contract | The UI branch's versioned, live-verified route/auth contract. |
| `scripts/probes/production_format_coverage_smoke.py` | probe | Measures per-format production reachability; the evidence for P1. |
| `scripts/release/backend_launcher.py` | fix | Credential/actor misattribution. |
| `tests/test_backend_runtime_safety.py` | test | Regression test for the above. |
| `docs/current/AAOS-BACKEND-LOOP-EVIDENCE-20261001.md` | report | This document. |

## 7. Rollback

Single-commit rollback. On the branch:

```
git revert <commit>          # or: git checkout <base> -- \
  scripts/release/backend_launcher.py \
  tests/test_backend_runtime_safety.py
```

The two added files are additive and can be deleted without affecting behaviour. No
database was migrated, no release or tag was created, no runtime asset was replaced, and
nothing outside this worktree's git-ignored `.project-local\` was written. The root
checkout's modified and untracked paths were never touched.

## 8. What is explicitly `NOT_EXECUTED`

* Real Legacy copy migration, in-place Green replacement, rollback of an installed
  runtime, release/tag/version publication — Owner-paused.
* Desktop (Avalonia) launch and native UI acceptance — the UI writer's surface.
* Independent G01–G14 Local Green qualification (A15) — requires an independent auditor.
* Real model inference, real embeddings/reranking, real human first use.
* Push, PR and exact-SHA CI readback — pending, reported separately once performed.
