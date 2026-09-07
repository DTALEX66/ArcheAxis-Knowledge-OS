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
| X00 | RECORDED (this file) | decision rows + intake verified above; commit on branch |
| X01 | PARTIAL (first slice done) | run-root doc aligned; dev-path/browser regressions 14 passed; browser screenshot→OCR real flow + CI wiring still open |
| X02 | PARTIAL (first slice done) | 8 current-loop donors registered (see X02-REUSE-LEDGER.md); broader semantic wave open |
| X03..X11 | TODO | per TASKS.json dependency order |
| X14 | TODO (eligible after X01/X02) | LOCAL-CLEANUP.md read-only census |
| X12/X13, Q00/Q01, F01-F06 | per TASKS.json | deferred / audit / retained |

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
- Open for X01 completion: real screenshot→OCR flow on this host (chromium
  availability under shared toolchain), CI collection/gate wiring review.

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

## Rollback

- This record: revert the DECISION_SUPERSESSION_LEDGER.yaml SUP-012..SUP-016
  rows, delete `docs/authority/taskpack-0907/` copy, delete the workspace/intake
  note; original package files under `D:\All projects\` remain untouched.
- Historical receipts are not rewritten.
