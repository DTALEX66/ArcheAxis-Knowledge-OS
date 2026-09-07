# AAK-REUSE-FIRST-20260907-R2 execution

User 2026-09-07 (DSH Web GUI) approved ingest of the REUSE-FIRST package and
start of execution after X00 recording. Package:
`ARCHEAXIS-REUSE-FIRST-FULL-TASKPACK-2026-09-07` at `D:\All projects\`
(zip + standalone TASKPACK.md, byte-identical SHA-256
`a9093a724c96a4493cbc0a4f8894b89fd2eee2d359e63e97e956e7a159a4a75e`).
This file is the execution ledger for this plan; it does not override
`AGENTS.md`, `PROJECT_CONTRACT.yaml` or `DECISION_SUPERSESSION_LEDGER.yaml`.
TASKS.json here is `plan_only` and `issued_authorization: false`; recorded
decisions below implement X00, not a signature or grant.

## Repository state at intake (2026-09-07)

- Branch: `codex/full-loop-0906`; HEAD `2daf8d7c227c6d78b24f4c17b8d8dc1d85d93cde`;
  working tree clean; in sync with `origin/codex/full-loop-0906`.
- `origin/main` = `4ca46eaf94c486dadcf200aac6b41cd968b1ce6e` (matches the plan
  `audit_base_sha`). No merge, push, release, tag or Green change performed.
- Prior authority on this branch: 2026-09-06-r1 full-loop taskpack
  (`docs/authority/taskpack-0906/`), superseded in the parts recorded in
  DECISION_SUPERSESSION_LEDGER.yaml SUP-012..SUP-016. Historical receipts keep
  their own SHAs.

## X00 record (2026-09-07)

Scope executed: baseline comparison, decision recording, task mapping, package
intake, provenance. No functional task is marked DONE; all X/F/Q tasks stay
open with statuses from TASKS.json.

### Package intake

- 15 files copied verbatim into this directory and re-verified:
  `python verify_package.py --root docs/authority/taskpack-0907` → exit 0,
  `package_checks: PASS`, task_count 23, format_groups 16, enhancement_items 11,
  coverage counts (capabilities 16, long_term_programs 10,
  blueprint_governance_tasks 11, canonical_repo_tasks 39,
  previous_followup_tasks 21, previous_model_tasks 20, user_requirements 66),
  valid dependency order emitted; scope = integrity/graph/coverage only.
- MANIFEST.json file list (14 files, sha256/bytes each) matches on disk.
- Derived extraction copy kept under `.project-local/inspect/` (ignored) for
  comparison; original zip and standalone md untouched.

### Decision mapping D01-D16 -> ledger

| Plan decision | Topic | Recorded as | Effect |
| --- | --- | --- | --- |
| D01 | 产品范围（四部分闭环） | SUP-012 (adoption), EXECUTION-START | continuity for one executor |
| D02 | 完整蓝图/冻结口径 | SUP-014 | retain not delete |
| D03 | 语言边界 | SUP-013 | Rust core + Python worker + C# desktop retained |
| D04 | UI 时序（Web/TS 表现层） | SUP-013 | first delivery not XAML-blocked |
| D05 | 机器学习三段分离 | EXECUTION.md (below) | M0 machine task required |
| D06 | 个人知识不需外部证据 | SUP-004 already; reaffirmed in EXECUTION.md | evidence is use constraint |
| D07 | 执行模型单一化 | SUP-012 | one executor to M0; Q00/Q01 audit |
| D08 | 旧证据基线 SHA | EXECUTION.md (below) | receipts keep tested SHA |
| D09 | 运行根 .project-local | SUP-011 already; X01 enforces | .hermes preserved legacy |
| D10 | 复用优先/自研门槛 | SUP-015 | F06 frozen gap records |
| D11 | 旧库独占写/新库 Rust | SUP-003/SUP-006 already; X10 | snapshot→read-only export→staging |
| D12 | 旧设计与模型保留 | EXECUTION.md (below) | X02 preserve |
| D13 | 许可边界 | SUP-005 already | MIT stays; third-party separately |
| D14 | 能力≠完成、CI 绿≠可用 | SUP-014 + status vocabulary | IMPLEMENTED_PENDING_AUDIT |
| D15 | 增强附件并入原任务 | SUP-016 | 11 items mapped to X tasks |
| D16 | 条件与后置（九锚/F04） | SUP-016 | optional template only |

Statuses per TASKS.json: X00..X11 = TODO/M0; Q00 = TODO/M0_AUDIT; X12/X13 =
TODO/M1; X14 = TODO/EARLY_CLEANUP; Q01 = TODO/M1_AUDIT; F01..F06 =
DEFERRED_RETAINED. No task has been declared implemented by this record.

## Progress ledger

| Task | State | Next evidence |
| --- | --- | --- |
| X00 | RECORDED | intake + decision rows (SUP-012..016) verified, commits on branch |
| X01 | PARTIAL (slices A/B) | real screenshot→OCR (run 26510ae2b9d6), CI wiring audited; remaining: live CI dispatch of a code commit |
| X02 | PARTIAL (waves 1-2) | 8 vNext workers + 6 legacy learning/knowledge donors registered with test evidence (X02-REUSE-LEDGER.md) |
| X03 | PARTIAL / BLOCKED parts | DeepTutor 1.5.17 local probe done; Chinese-import gap + interactive-only LLM config + default-host decision open |
| X04 | PARTIAL | schema/worker alignment locked; identity-self-claim fix BLOCKED on role-scope authority |
| X05 | PARTIAL (A/B/C done) | source origins + HTTP + archive round trip proven; remaining executor/restart deep-slices open |
| X06 | PARTIAL (A/B/C) | text/HTML/OCR eng+chi_sim real; PDF lane reconfirmed; scanned-OCR routing + media ASR + dynamic web open |
| X07 | BLOCKED (cloud part) | public fact-check requires network/credentials authorization; offline golden metrics exist |
| X08/X09 | BLOCKED | depend on X03 default-host decision + X07; donor semantics registered (X02 wave 2) |
| X10 | PARTIAL | migration export/dry-run base proven on synthetic DB; semantic map/import/diff/rollback open |
| X11 | BLOCKED | full Windows candidate package + journey + Q00 independent audit (needs prior gates) |
| X14 | PARTIAL | real census 66.6 GiB + deletion-manifest PREP; deletion rows await explicit authorization |
| X12/X13, Q00/Q01, F01-F06 | per TASKS.json | deferred / audit / retained frozen |

Round-13 snapshot: remaining ready work is exhausted without new authorization;
every open item above carries a recorded concrete prerequisite (role-scope
identity, network/credentials, DeepTutor host decision, deletion row go-ahead,
semantic migration mapping, packaging). Overall baselines: full Python suite
2394 passed + full Rust workspace green at their recorded HEADs.

## X01 first slice (2026-09-07)

- Audited all tracked `.hermes` references in code: most are boundary guards
  (generate_vocabulary, text_ndjson, worker_ocr, hotreload, inventory); the
  stale pipeline doc was the actionable item. `app/ingestion/asr_adapter.py`
  `_sense_voice_dir` default still resolves under `.hermes/task-runtime/...`
  and `scripts/pipeline/README.md` still told writers to emit receipts there.
- Change: `scripts/pipeline/README.md` receipt-root sentence now points to
  `.project-local/runs/` via dev.py and marks `.hermes` read-only legacy.
  Commit `fd5182c`. ASR default pointer is registered as an X04/X06 model-profile
  gap (needs config-bound shared-model path, not an ad-hoc constant).
- Regression evidence: `tests/runtime-paths/test_dev_paths.py` +
  `tests/test_web_screenshot.py` +
  `tests/test_workspace_browser_failure_retry_replay.py` → 14 passed,
  0 failed (dev.py launcher invariant: writes only `.project-local`, never
  creates `.hermes`, concurrent tmp isolation; pytest exit 0 re-confirmed).
  dev.py-managed run evidence: `.project-local/runs/be268a2d33/ea458cee118a`
  (exit_code 0, dirty=false, source_commit 76a3680, python 3.13.14).
- CI gate wiring audit (read-only): `.github/workflows/vnext-ci.yml` path
  triggers cover crates/Cargo/contracts/services/python-workers/scripts/runtime/
  tests/{runtime-paths,workers,contract}/model-profiles/desktop and run the
  `scripts/ci/check_vnext_{contracts,receipt,workers}.py` structural gates plus
  a Windows cargo-test; `a0_browser_smoke` is referenced by ci.yml/nightly.yml.
  The X00/X01 doc-only commits are intentionally outside vnext-ci path
  triggers, so no vnext-ci run is claimed for them; full collection entrypoint
  remains `scripts/ci/run_tests.ps1 --full`.
- Open for X01 completion: real screenshot→OCR flow on this host (chromium
  availability under shared toolchain), CI collection/gate wiring review.

## X01 slice B (2026-09-07): real screenshot → OCR flow

- Host resources verified: Edge present (Program Files (x86) msedge.exe, found
  by product `find_browser` without code change); tesseract on PATH (shared
  toolchain scoop current, 5.5.x); tessdata eng+chi_sim at shared
  persist/languages dirs; `config/model-profiles/local-2026-09-05.yaml`
  tessdata_dir -> shared languages/current.
- Real probe (product code path, no mocks): local HTML page with markers
  `ARCHEAXIS OCR PROBE 123` + Chinese line -> `screenshot_web` (msedge
  headless, PNG 29,015 B, sha256 4bf437c8a4e50f80…) -> OCR worker
  `--profile config/model-profiles/local-2026-09-05.yaml` -> OCR exit 0,
  matched tokens ["ARCHEAXIS","OCR","PROBE","123"]; text head
  `ARCHEAXIS OCR PROBE 123 TF OCR #R#t 2026` (Chinese line not recognized
  under eng lang - chi_sim lane gap already registered in P13).
- Evidence run: `.project-local/runs/be268a2d33/26510ae2b9d6` (dev.py,
  exit_code 0, dirty=false). Probe script kept at
  `.project-local/probes/x01_real_screenshot_ocr.py` (ignored, reusable).
  No `.hermes` writes; all artifacts under `.project-local`.
- Note: `dev.py -- python …` resolves `python` from PATH; use the explicit
  venv interpreter path for children that import third-party packages
  (recorded so future slices do not repeat the yaml-missing run).

## X02 first slice (2026-09-07)

- Registered 8 current-loop donor assets with tracked HEAD hashes, reuse mode,
  behavior evidence and rollback in [X02-REUSE-LEDGER.md](X02-REUSE-LEDGER.md).
  All are direct-reuse computation workers without DB handles; adapters remain
  to wire in X06 under the same per-donor evidence rules.
- Not a claim that all 1246 legacy items were semantically read; remainder stay
  preserved in LEGACY_MANIFEST.yaml (R03 20-item review remains prior input).

## Boundaries

- No E-drive access, no Green replacement/start, no release/tag/version, no
  push, no main merge, no global config edits, no .hermes new writes.
- Shared roots and indexes re-verified 2026-09-07 (see SHARED_RESOURCE_PATH_
  INDEX.md): all present, no reparse/link.
- Run evidence goes to `.project-local/runs/`; this authority copy is tracked.
- Next slices must record tested source sha/tree, commands + exit codes,
  environment versions, hashes, failure paths and rollback.

## X03 slice A (2026-09-07): DeepTutor 1.5.17 local capability probe

Candidate per TASKPACK 4.1: DeepTutor (HKUDS, locked 1.5.17). Host copy:
`D:\All projects\OS External Configuration\10-toolchains\deeptutor\1.5.17`
(source-archive full upstream clone + ready Windows venv; `source` dir is
git metadata with empty checkout and is not the run source). CLI venv entry
`deeptutor.exe` runs on this host; storage root = `<cwd>\data\user`.

Verified offline (no LLM required):
- `deeptutor doctor`: PASS runtime storage writable; FAIL no LLM model +
  no openai credentials (endpoint defaults to https://api.openai.com) -> the
  LLM-dependent tutoring/session core is BLOCKED_RESOURCE offline (no
  credentials, no authorization to register); local-ollama provider
  alternative not yet configured (deferred slice).
- Notebook local import round-trip (synthetic ASCII markdown): create
  notebook -> numeric id `01b12823`; `add-md` by numeric id persisted record
  `e629b16a`; `show` reads it back; content stored under
  `<iso>\data\user\workspace\notebook\01b12823.json`.
- Concrete upstream gaps on Windows (v1.5.17, evidence from runs above):
  1. Chinese-content markdown import corrupts to U+FFFD regardless of file
     encoding (UTF-8 no BOM, UTF-8 BOM) and of PYTHONUTF8=1; ASCII content
     imports cleanly. This is concrete failure evidence for the Chinese-first
     product: qualifies as the documented "evaluate fallback / adapter"
     trigger for X03 (not a silent pass).
  2. `add-md` by notebook *name* reports success but does not persist
     (numeric id works); `notebook list` record counts can lag `show`.
- Repo pollution created by the first probe run (`data\user` under repo root
  from cwd) was removed; later probes ran from an isolated cwd
  `.project-local/deeptutor-val/` (ignored). No `.hermes`/E-drive/real-library
  touch.

X03 status: PARTIAL. Next X03 steps: decide default host only after an actual
upstream run (web start not yet attempted) and record provider-config slice;
Chinese-content import gap feeds X12/Obsidian interop planning and the
fallback evaluation criteria.

## X03 slice B (2026-09-07): local LLM provider config attempt - BLOCKED at config surface

Attempted to unblock DeepTutor LLM checks with the running local ollama
(0.33.3 at 127.0.0.1:11434; models incl. qwen3 family present; DeepTutor README
documents Ollama via Base URL `http://host…:11434/v1`). Findings:
- CLI `deeptutor init --cli` is interactive-only (no non-interactive flags for
  provider/model); the model provider profile lives in
  `data/user/settings/model_catalog.json` with `profiles[]` whose exact schema
  would have to be reverse-engineered from upstream code.
- Recording this as BLOCKED_RESOURCE at the configuration surface, not a
  product failure: enabling it needs either the upstream UI Settings->Models
  path on a launched host (X03 web-start slice) or an upstream-supported
  non-interactive provider config command. No code/config was modified in the
  shared DeepTutor install; iso workspace unchanged.

## X04 slice A (2026-09-07): worker_quality schema alignment regression

Task-card claims checked against current branch code + schemas:
1. "top-level loss_receipt 与 schema 不一致": NOT a defect on this branch — the
   embedded loss_receipt validates as a minimal instance of BOTH the inline
   quality-report definition and the shared `loss-receipt.schema.json`
   (required engine/engine_version/params/loss_note present, additional props
   none). Verified empirically.
2. "normalize=none 却 strip": NOT a defect on this branch — `_normalize` is
   identity for none; CER counts a leading space as a real difference
   (value 1.0 over gold "a"); params.normalize echoes the argument.
3. Loss accumulation: each report's rows reference their own byte snapshots;
   repeated samples never overwrite each other.

Locks added: `tests/contract/test_quality_report_schema_alignment.py`
(3 tests; run evidence `.project-local/runs/be268a2d33/ed048ba345ae`, 3 passed
exit 0; combined contract/quality subset 37 passed before commit). Commit
`76f59a6`. Deprecation warnings (RefResolver) are pre-existing.

Remaining X04 sub-items (recorded, next slices): identity semantics — reject
client-claimed human/verified and forged created_by (Rust domain + worker
protocol authorization), content-type vs review-flow vs user-acceptance vs
external-verification state dimensions, source/anchor bidirectional versioning
and explicit invalidation (feeds X07/X05 work). No claim of completion for
those.

## X14 slice A (2026-09-07): first real Windows read-only census

Ran the package census tool on the live repo (real Windows host):
`audit_local_storage.py --repo .` through dev.py; run evidence
`.project-local/runs/be268a2d33/a1351353bc6f`; report
`.project-local/inventory/20260907T124829Z-21123e40/summary.json`.

Numbers (same-scope, GiB = /1024^3):
- logical 66.625 GiB, 857,017 files, hardlinked 0 (unique == logical),
  deleted_files 0, skipped links/special 31.
- 125 errors recorded honestly (not treated as absent): WinError 5 access
  denied inside legacy `.hermes/task-runtime/...` (and `.hermes/t2-*`), and
  WinError 3 missing paths on known long-path pytest residue (segment-xxx
  UNC tests). `complete_regular_file_scan: False` for those; figures are
  therefore a measured floor, not a full snapshot.
- Categories (GiB): REVIEW_HERMES_MIXED_NO_AUTO_DELETE 42.855;
  REVIEW_REBUILDABLE_CANDIDATE 12.667; REVIEW_PROJECT_RUNTIME_MIXED 10.05;
  REVIEW_ENVIRONMENT_REBUILD_REQUIRED 0.858; KEEP_DATA_OR_UNKNOWN 0.094;
  KEEP_TRACKED_OR_GIT 0.077; KEEP_UNCLASSIFIED 0.023.
- Top two-level (GiB): .hermes/task-runtime 40.223; .project-local/build
  8.398; src-tauri/target 5.181; desktop/src-tauri 4.896; target/debug 1.802;
  .hermes/cache 1.632; .project-local/cache 1.148; .venv/Lib 0.804;
  apps/ArcheAxis.Desktop 0.677; .project-local/runs 0.480; .hermes/rt 0.462;
  .hermes/task-artifacts 0.328.
- Reading: the historical ~56.6GB figure is not today's total and no
  allocation/reclaim claim is made (logical bytes only). The 42.9 GiB .hermes
  category stays preserved (REVIEW, no auto-delete). Rebuildable candidates
  (~12.7 GiB target/node_modules/bin/obj + .project-local/build caches) are
  quantified but NOT deleted in this slice: deletion is destructive and needs
  an explicit per-scope confirmation plus a recorded manifest/rebuild step.
  X14 next: deletion wave only after that confirmation; rerun same census to
  compare before/after.

## X04/X05 slice B (2026-09-07): worker CLI UTF-8 stdout hardening

Rust integration baseline exposed a Windows-specific defect class: worker CLI
mains printed JSON with `ensure_ascii=False` while the spawned child's stdout
defaulted to the locale codec (GBK), so any astral char (e.g. U+1F600 in the
BOM/loss-receipt fixture) crashed with UnicodeEncodeError. dev.py runs were
green only because dev.py exports PYTHONIOENCODING=utf-8.

Fix: reconfigure stdout to UTF-8 at main start in
`worker_text.py`, `worker_quality.py`, `worker_ocr.py`
(`contextlib.suppress(AttributeError, OSError)`), so the CLI is
environment-independent (product worker output contract is UTF-8).
Also removed now-unneeded `# -*- coding: utf-8 -*-` headers (UP009).

Verification: ruff clean; worker_text CLI repro exit 0; python subset
39 passed + 4 OCR skips + 47 subtests (run `be268a2d33/5bce2ba6ff88`);
`cargo test -p archeaxis-api --test job_rejections` 3 passed (was failing with
"worker execution failed" before the fix). Full workspace re-run follows.

Toolchain/env notes recorded for future Rust runs on this host:
- cargo 1.97.1 at `10-toolchains\cargo\bin\cargo.exe` with CARGO_HOME/RUSTUP_
  HOME pointing at `10-toolchains\{cargo,rustup}`; MSVC linker via
  `10-toolchains\msvc\VC\Auxiliary\Build\vcvars64.bat`; integration tests that
  spawn the real Python worker also require ARCHEAXIS_PYTHON (venv python).
  Canonical wrapper = dev.py inside a vcvars-initialized shell.

## X05 slice A (2026-09-07): source provenance (distinct origins on one digest)

Gap addressed from X05 work list: "不同来源记录不会因字节相同丢失来源语义"
and "原件可回读来源时间/导入时间；未知来源时间不伪造". Previous
`import_source` deduped identical bytes into one content row and discarded any
later origin (only first original_name/raw_path survived).

Change (additive schema, no version bump):
- `crates/archeaxis-store-sqlite/src/lib.rs` SCHEMA_SQL adds table
  `source_origins(source_id, origin_kind path|url|import|manual, origin_ref,
  original_name, received_at NULL, imported_at, PK(source_id,kind,ref))`.
- `crates/archeaxis-domain/src/source.rs`: `OriginInfo`, refactored
  `import_source` -> `import_source_with_origin(...)` (old signature kept as a
  delegating wrapper, so callers unchanged); every reported distinct origin is
  recorded (INSERT OR IGNORE) on both insert and duplicate paths; `received_at`
  None is stored NULL - never fabricated.
- New integration tests `crates/archeaxis-domain/tests/source_origins.rs`:
  2 tests (two origins on one digest retained incl. NULL received_at; repeated
  same origin idempotent).

Verification: `cargo test -p archeaxis-domain --test source_origins` 2 passed;
affected suites `-p archeaxis-domain -p archeaxis-application -p
archeaxis-archive -p archeaxis-api` all green (cargo_exit=0, no failures).
Known limitation recorded: archive export table list does not yet include
source_origins (provenance lives in the primary DB; archive round-trip of
origins is a follow-up). HTTP import endpoint still imports without origin
metadata; plumbing optional origin fields is a next slice.

## X05 slice B (2026-09-07): HTTP origin plumbing + archive provenance

- Archive: `EXPORT_TABLES` now includes `source_origins` appended at the END of
  the list (after job_outputs) so the v2 legacy slice `EXPORT_TABLES[..8]`
  stays byte-identical to the original eight tables; the in-repo v2
  readability unit test fixture now removes the provenance table to mirror the
  genuine pre-provenance wire (v3-only additive table). Export/restore carry
  provenance rows for current archives; legacy v2 archives remain readable.
- HTTP import (`POST /api/v1/imports`) accepts optional
  `origin_kind` (path|url|import|manual), `origin_ref`, `origin_name`,
  `received_at`; validated (unknown kind or kind-without-ref -> 400) and
  passed to `import_source_with_origin`. Callers that omit them keep the exact
  prior behaviour (202/duplicate semantics unchanged).
- New integration test `crates/archeaxis-api/tests/import_origins.rs` (2 tests):
  url+path origins retained on one digest with NULL received_at; invalid or
  partial origin fields rejected 400. One real defect found and fixed while
  writing it: the validation match arm for the valid (Some,Some) case was
  missing and fell through to 400.
- Verification: `cargo test -p archeaxis-api --test import_origins` 2 passed;
  full api/archive/domain regression green (cargo_exit=0).

## X05 slice C (2026-09-07): archive provenance round-trip proof

New archive integration test `crates/archeaxis-archive/tests/origin_roundtrip.rs`:
workspace with two distinct origins on one digest (url + path, one with NULL
received_at) -> export_workspace -> restore_workspace into a fresh db ->
`list_origins` returns both rows with original values, and the NULL
received_at survives the round trip. `cargo test -p archeaxis-archive --test
origin_roundtrip` 1 passed (exit 0). This closes the X05 provenance series
(A: table+domain, B: HTTP+EXPORT_TABLES inclusion, C: export/restore proof).

## X06 slice A (2026-09-07): real chi_sim OCR recognition

X06 acceptance "至少一个真实本地模型用于识别/转换" now covered for Chinese:
re-ran the product OCR worker with `--lang chi_sim --profile
config/model-profiles/local-2026-09-05.yaml` over the X01 real screenshot PNG
(`.project-local/runs/be268a2d33/26510ae2b9d6/tmp/page.png`, sha256
4bf437c8…) — exit 0, text `ARCHEAXIS OCR PROBE 123\n星环 OCR 探针 2026`
(ASCII and Chinese markers all recognized, per-word boxes + confidence 91-95).
This closes the earlier "Chinese line not recognized under eng" observation
(eng lane limitation only; chi_sim lane works with the explicit shared
tessdata profile). loss_receipt still carries the stale TESSDATA_PREFIX
warning (env points at a non-existent `toolchains\scoop\...` path) while the
explicit profile `tessdata_dir` is what actually resolves - registered env
gap (R08), not a functional block for explicit-profile runs.

X06 remaining gaps recorded (not faked): vNext PDF/scanned-page worker lane is
not yet present in `services/python-workers` (text/canvas/subtitles/office/
html/ocr only); dynamic-webpage screenshot lane needs playwright+chromium
under a project-owned browser root; media ASR execution group stays
BLOCKED_RESOURCE pending an authorized model-profile run (P14). M0 samples for
text/HTML/OCR(chi_sim)/screenshot chains now have real local evidence.

## Overall Python regression (2026-09-07)

Full suite across tests + integration-tests + knowledge_base/tests via dev.py:
run `.project-local/runs/be268a2d33/e31758dd7698` (dirty=false, source commit
f803bfe): **2394 passed, 7 skipped, 14 warnings (deprecation), 124 subtests,
exit 0**, 156s. Confirms no regression from the X04/X05/X06 changes landed so
far on this branch (the 7 skips are not passed qualifications).

## X10 slice A (2026-09-07): migration crate recon + full-workspace green

- Full Rust workspace regression at current HEAD (post X05 slices A/B):
  `cargo test --workspace --locked --offline` exit 0, zero failures
  (vcvars + CARGO_HOME/RUSTUP_HOME env as recorded above).
- `crates/archeaxis-migration` recon: implements legacy read-only `inventory`
  + `export_jsonl` + stable manifest; existing tests cover table inventory,
  reproducible byte-stable re-export, and "legacy db file bytes unchanged"
  (read-only open, no WAL). These satisfy X10's export/dry-run base for
  synthetic fixtures.
- X10 gaps recorded for next slices (not faked): semantic mapping legacy ->
  vNext staging import, structural/content diff and loss ledger, rollback of
  an unactivated staging, richer non-empty fixtures (attachments, personal
  definitions, knowledge versions, learning events, machine feedback); a real
  user legacy database requires its own consistent-snapshot + readback
  evidence and authorization, so that qualification stays open.

## X06 slice B (2026-09-07): PDF lane reconfirmed

`tests/workers/test_bulk_pdf.py` + `test_bulk_office.py` re-run green: 10
passed (dev.py run `.project-local/runs/be268a2d33/718c063f8a0e`).
`worker_office._pdf_text` already yields per-page text/anchors, scanned-page
reporting and corrupt-input failure (P11 coverage). X06 open item refined:
only scanned/mixed-page OCR routing (image-only pages), media ASR
(authorized profile) and dynamic webpage remain.

## X14 slice B (2026-09-07): deletion manifest PREP (no deletion executed)

Prepared [X14-CLEANUP-MANIFEST-PREP.md](X14-CLEANUP-MANIFEST-PREP.md):
exact candidate rows with census refs, ownership, rebuild/lock, rollback and
state (NEEDS_AUTHORIZATION / HOLD / APPROVED-READY / NEVER-AUTO-DELETE /
NOT-IN-SCOPE). `.pytest_cache`+`.ruff_cache` marked APPROVED-READY (trivial,
non-destructive); `src-tauri/target`, `desktop/src-tauri/target`,
`desktop/node_modules`, C# bin/obj NEEDS_AUTHORIZATION; root `target/` and
`.project-local/build` HOLD (in active use as build caches); `.hermes` never.
No deletion executed this round; deletion requires row-level go-ahead and the
before/after census + rebuild verification defined in the file.

## X04 slice C (2026-09-07): identity-self-claim analysis - BLOCKED on role scope

Analysed the residual X04 identity item on the real code path: create-knowledge
already hard-codes `evidence_status=None` and defaults `status` to candidate,
so clients cannot attach external-verification state at creation. Two residuals
remain: (1) the create body may still set `status: accepted`, and (2)
`created_by` is free text - both because per-request actor identity is not
plumbed. A blanket "initial status must be candidate" guard would wrongly
block legitimate human-authored personal definitions (X04: personal
definitions may be saved and user-accepted without external proof), so the
correct fix is a role-scoped authority identity layer, already a recorded open
item of launch_auth/authority (X04 remaining list). Marked BLOCKED_RESOURCE
with that concrete prerequisite; no half-guard landed to avoid corrupting the
personal-definition semantics.

## X06 slice C (2026-09-07): OCR engine tests executed (no skips)

`tests/workers/test_bulk_ocr.py` re-run with the shared tessdata env
(`TESSDATA_PREFIX=...10-toolchains\scoop\persist\tesseract\tessdata`): 4 passed
(run `.project-local/runs/be268a2d33/ce16a8410c76`), no fake skips - the OCR
engine regression lane executes for real (eng cases); the earlier 4-skip
observation was purely the missing env in the default lane, matching P13
notes. Explicit-profile chi_sim real run recorded in X06 slice A.

## X03 slice C (2026-09-07): piped-stdin init attempt fails - BLOCKED maintained

Attempted to drive the interactive `deeptutor init --cli` non-interactively by
piping empty lines into stdin from an isolated HOME. The CLI did not consume
piped stdin and the run hung past the 120s cap (killed; no stray process left;
iso workspace and repo untouched). Conclusion recorded: the provider config
surface is genuinely interactive-terminal-bound in this environment; unblocking
X03's LLM-dependent checks requires either a real interactive console/UI
session (web-start slice) or upstream support for non-interactive config. No
change to the shared DeepTutor install.

## X03 slice D (2026-09-07): final config attempts exhausted - locked decision

With full user authorization, further unblock paths were investigated and each
closed with evidence: (1) `deeptutor init --cli` is interactive-only; (2)
piped-stdin drive hangs (slice C); (3) `deeptutor serve` exposes settings/model-
catalog only behind the multi-user register/login auth dependency
(`deeptutor/api/routers/settings.py`), so programmatic provider config needs
the app's own account/UI flow; (4) hand-writing `model_catalog.json` profiles
is unsafe without the upstream profile schema (provider core is layered under
`services/llm/provider_core`). Conclusion: DeepTutor's default-host decision
cannot be completed autonomously in this environment. Locked as BLOCKED for
X03 with reason: requires an interactive console/UI session of the upstream
host (its own register/login + Settings->Models) or an upstream non-interactive
provider-config API. This does not block M0 evidence for the other lanes; the
Chinese-import gap and fallback-candidate criteria recorded earlier still
stand.

## X07 slice A (2026-09-07): public retrieval BLOCKED_RESOURCE (sandbox egress)

With full authorization, a real public-source retrieval was attempted from the
product python environment (probe `.project-local/probes/x07_public_check_probe.py`,
run `be268a2d33/3855f5a1bd89`): Wikipedia REST summary fetch failed with
`SSL: UNEXPECTED_EOF_WHILE_READING`; follow-up egress probes show ALL outbound
HTTPS from sandbox children fails the same way and plain HTTP returns 502 Bad
Gateway. Conclusion: the product runtime has no working public-network egress
in this environment, so X07's "one real public fact-check" is BLOCKED_RESOURCE
(concrete: TLS EOF / HTTP 502 across example.com and wikipedia.org). The
agent-side web tools are a separate channel and cannot be claimed as product
verification. Local ollama loopback works; an internal-content local-model
judge can still be demonstrated but adds no external-verification value. X07
remains PARTIAL/BLOCKED with this evidence; offline golden metrics (X07 base)
are already covered by worker_quality.

## Rollback

- This record: revert the DECISION_SUPERSESSION_LEDGER.yaml SUP-012..SUP-016
  rows, delete `docs/authority/taskpack-0907/` copy, delete the workspace/intake
  note; original package files under `D:\All projects\` remain untouched.
- Historical receipts are not rewritten.
