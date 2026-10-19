# DP-GIT-01 · branch/commit semantic audit — batch 02

- task_id: `DP-GIT-01` (continuation batch)
- report_schema: `aaos.dsh.branch-commit-audit/v1`
- audit_branch: `codex/dp-git-02-20260925`
- baseline_sha: `a5de4b13474c217e7a9dd34b8cbfa402e8297780`
- baseline_tree: `a4156ed65d50675822321b9d63eec932b1e76af3`
- origin_main: `e3875db0ee6d073d37839eb7b95f7ef4ce881bbb`
- batches_complete: **2 of N** — still **not exhaustive**

## 0. Scope and boundary statement

- Read-only review of committed Git objects. **No product source, test or state file was changed**;
  this new report is the only artifact.
- **The dirty root working tree is NOT part of any branch diff here.** Root was on
  `codex/aaos-p3-ui-convergence-20260922` at `a5de4b13` with 112 uncommitted paths belonging to
  concurrent root-side Candidate work. All facts come from committed objects read inside the
  isolated worktree `.project-local/worktrees/dp-git-02-20260925`.
- **This batch was run in parallel with Codex executing its own task.** The declared Codex write
  range (`scripts/release/`, `tests/test_candidate*`, `tests/test_green_candidate_*`,
  `docs/current/R6-EXECUTION.md`, `docs/current/R6-STATE.json`,
  `docs/current/AAOS-UI-SUITE-COVERAGE-20260923.md`, `docs/SHARED_RESOURCE_PATH_INDEX.md`) was
  avoided entirely. This report adds one new file under `docs/current/dsh-review/` only.
- Decisions are audit judgements, **not** authorization to cherry-pick or delete branches.

## 1. Method (inherited from batch 01, including its correction)

Identical procedure to batch 01: enumerate non-merge commits per branch not in `origin/main`; record
per-file status, `--numstat`, commit-side and baseline-side blob OIDs; classify each path as
absent / byte-identical / evolved against the baseline; read the diffs of all product-bearing files;
then apply the September authority set (R6 TaskPack, M0 overlay `SUP-020`, `NAMING_CONTRACT_V2`,
`AGENTS.md` §6, `R6-VERSION-RELEASE-FREEZE.md`, `docs/SHARED_RESOURCE_PATH_INDEX.md`).

**Method correction carried over:** baseline membership is decided by `git cat-file -e` **exit
status**, never by `git rev-parse <tree>:<path>` output — the batch-01 report documents that
`rev-parse` echoes its argument on stdout even when it fails, which silently misclassified 8 paths
in the first batch-01 collection.

## 2. Coverage

| Metric | Value |
| --- | --- |
| Branches in this batch | 2 (`feat/p1-compat-kernel-hardening`, `feat/h2-pipeline-integration`) |
| Distinct SHAs audited | **19** (batch cap 20) |
| SHA range | `5a519836` (2026-08-09) … `e1df9279` (2026-08-12) |
| Changed-file records | 153 |
| Absent from baseline | 10 |
| Byte-identical to baseline | 37 |
| Differing (evolved) | 106 |
| Commits with zero file changes | 1 (`3227f1ef`, empty CI-trigger/merge commit) |
| Decisions | `SUPERSEDED` 18, `CHERRY_PICK_CANDIDATE` 0, `KEEP` 1, `CONFLICT` 0, `UNKNOWN` 0 |
| Cumulative audited across batches 01–02 | 36 SHAs |

Per-branch: `feat/p1-compat-kernel-hardening` 10/10; `feat/h2-pipeline-integration` 9/9. Both refs resolved.

## 3. Per-SHA records

### 3.1 `5a519836` — feat(product): close naming and workspace truth contract

- Branch `feat/p1-compat-kernel-hardening`. Merge base `2f85d8be`. 2026-08-09. 18 files, +181/−48.
- Files: `README.md`, `app/main.py`, `app/release-manifest.json`, `app/workspace/router.py`,
  `app/workspace/ui/assets/app.js` (absent), `app/workspace/ui/index.html` (absent),
  `config/product-naming-registry.yaml`, `docs/NAMING_CONTRACT_V2.md`,
  `docs/PRODUCT_POSITIONING.md`, `docs/PRODUCT_STAGE_COMPATIBILITY.md`, `docs/PROJECT_STATUS.md`,
  `knowledge_base/api.py`, `pyproject.toml`, `scripts/a0_browser_smoke.py`,
  `tests/test_desktop_runtime.py`, `tests/test_naming_conventions.py`,
  `tests/test_product_truth_contract.py`, `tests/test_workspace_api.py`.
- Purpose (read from diff): publish the product-naming registry and stage-compatibility contract and align active surfaces to V2 naming.
- Observed evidence: no test run. `config/product-naming-registry.yaml` and `docs/NAMING_CONTRACT_V2.md` are **evolved** in the baseline, i.e. the contract landed and later grew; the two `app/workspace/ui/**` paths are absent (removed web UI).
- Authority alignment: consistent with `NAMING_CONTRACT_V2` §1–§2; no release/version change.
- **Decision: `SUPERSEDED`.** The naming/registry contract is resident in the baseline in a later form; the UI half targets a removed tree.

### 3.2 `70c38a1c` — feat(compat): harden attachments and revision fencing

- 4 files, +111/−11: `shared/compat/import_session.py`, `shared/compat/models.py`,
  `shared/compat/revision.py`, `tests/test_compat_kernel.py`.
- Purpose: attachment hardening and revision fencing in the compatibility kernel.
- Observed evidence: no test run. **All four files are byte-identical to the baseline** — including the branch's own test file `tests/test_compat_kernel.py`.
- Authority alignment: no conflict; hardening is aligned with the no-false-success posture.
- **Decision: `SUPERSEDED`.** Strongest absorption class in this batch: every file, test included, is identical in the baseline. Nothing to port.

### 3.3 `ba31d95a` — feat(workspace): add read-only vault workbench API

- 3 files, +184/−1: `app/workspace/router.py` (evolved), `app/workspace/vault.py` (evolved), `tests/test_workspace_vault_api.py` (**identical**).
- Purpose: read-only Vault workbench endpoints.
- Observed evidence: no test run. The test file is byte-identical; the baseline router already exposes `/api/vault/inspect`, `/api/vault/file`, `/api/vault/search`, `/api/vault/canvas/read|write`, `/api/vault/write`, `/api/vault/backups`, `/api/vault/restore`.
- Authority alignment: aligned — Vault work stays read-only/derived; R6 A06 records this area as `TESTED_LOCAL_PARTIAL`.
- **Decision: `SUPERSEDED`.** Endpoints and their test are present in the baseline.

### 3.4 `10f04df6` — feat(workspace): expose read-only vault workbench

- 2 files, +12/−5, both `app/workspace/ui/**` (absent).
- Purpose: wire the Vault workbench into the legacy web UI.
- Observed evidence: no test run; no test file in this commit.
- Authority alignment: obsolete — the legacy web UI tree does not exist in the baseline.
- **Decision: `SUPERSEDED`.** UI half of 3.3 for a removed shell.

### 3.5 `2f9540ba` — feat(workspace): stream durable audit projection over sse

- 2 files, +60/−1: `app/workspace/router.py` (evolved), `tests/test_workspace_audit_sse.py` (evolved).
- Purpose: durable audit projection over Server-Sent Events with resumable event fingerprints.
- Observed evidence: no test run. The baseline router contains `_audit_snapshot`, `_audit_event` and `@router.get("/api/audit/stream")` with `text/event-stream`, i.e. the feature is present and later evolved.
- Authority alignment: no conflict.
- **Decision: `SUPERSEDED`.** Implemented and evolved in the baseline; the test file exists there too.

### 3.6 `d13c9cb6` — feat(workspace): add lease-fenced background worker

- 8 files, +193/−12: `app/release-manifest.json`, `app/workspace/service.py`, `app/workspace/worker.py` (**identical**), `scripts/a0_browser_smoke.py`, `tests/test_release_manifest.py`, `tests/test_workspace_api.py`, `tests/test_workspace_delivery_projection.py` (**identical**), `tests/test_workspace_worker.py` (**identical**).
- Purpose: lease-fenced background worker for the workspace dispatcher.
- Observed evidence: no test run. `worker.py` and both worker/delivery test files are **byte-identical to the baseline**.
- Authority alignment: aligned with the existing lease/retry-no-state-change contract; no dual-write.
- **Decision: `SUPERSEDED`.** Implementation and its tests are resident unchanged.

### 3.7 `237403e9` — feat(workspace): add audit stream and bounded planner preview

- 4 files, +59/−2: `app/release-manifest.json`, `app/workspace/router.py` (evolved), `tests/test_release_manifest.py`, `tests/test_workspace_planner.py` (evolved).
- Purpose: bounded planner preview plus the audit stream wiring.
- Observed evidence: no test run. The baseline router contains `class PlannerRequest`, `@router.post("/api/planner/preview")` documented as "Preview only the bounded, explicitly supported planner grammar", and `tests/test_workspace_planner.py` exists in evolved form.
- Authority alignment: aligned — bounded grammar, preview only, no execution authority.
- **Decision: `SUPERSEDED`.** Present and evolved in the baseline.

### 3.8 `84a0dfdb` — test(ui): align navigation contract with naming v2

- 1 file, +1/−1: `tests/test_ui01_navigation_contract.py` (**absent from the baseline**).
- Purpose: single-line assertion alignment in a legacy web navigation test.
- Observed evidence: no test run.
- Authority alignment: the product navigation contract now lives with the Avalonia shell (`docs/current/AAOS-UI-SUITE-COVERAGE-20260923.md` records 202+ navigation contracts); the legacy web-UI navigation test is not part of the current authority.
- **Decision: `SUPERSEDED`.** A one-line edit to a test for a removed web UI. The note separately records that this path is **not** in the donor archive (§4).

### 3.9 `60011096` — feat(ingestion): expose honest multi-format capabilities

- 12 files, +388/−15: `app/ingestion/multi_format.py` (evolved), `app/main.py`, `app/release-manifest.json`, `app/release.py`, `pyproject.toml`, `requirements.txt`, `tests/test_adapter_contract.py`, `tests/test_ci_a0_gates.py`, `tests/test_format_capabilities.py` (**absent**), `uv.lock`, `workspace/intake/2026-08-09-multiformat-capability-boundary.md` (**absent**), `workspace/intake/2026-08-09-online-learning-corpus.md` (**absent**).
- Purpose: `format_capabilities()` reporting honest runtime states per format, with rich documents `degraded` until anchors/qualification are verified and images/media deliberately metadata-only.
- Observed evidence: no test run. The baseline `app/ingestion/multi_format.py` is **evolved** and its "honest state" semantics are present in a different form ("treat as degraded (no content)", "never a metadata-only fake success", "never claimed as content"); however the baseline file has **no `format_capabilities()` function**, and the capability test file is absent (archived — see §4).
- Authority alignment: the *intent* matches M0's explicit-unsupported rule; the *shape* (a capability-reporting function on the legacy ingestion module) was replaced by later work — the baseline format contracts are `app/contracts/format_execution_v1.py` + `tests/test_format_execution_v1.py` + `tests/test_format_matrix.py`.
- **Decision: `SUPERSEDED`.** The semantic requirement survives in evolved form and the branch's own test/doc artifacts are preserved by the repository's donor-asset archive. Porting the function would reintroduce a second capability-reporting shape beside the R6 A05 receipt contract.

### 3.10 `bebc5a74` — fix(runtime): align cloud identity and test stability

- 6 files, +25/−4: `.github/workflows/ci.yml`, `desktop/src-tauri/src/protocol.rs`, `scripts/runtime_http_smoke.py`, `tests/conftest.py`, `tests/test_registry_v2.py` (**identical**), `tests/test_workspace_vault_api.py`.
- Purpose: cloud-identity naming alignment plus test-stability fixes.
- Observed evidence: no test run. `tests/test_registry_v2.py` is byte-identical; the rest evolved (baseline CI uses hash-locked requirements and uv groups).
- Authority alignment: no conflict; superseded by later CI/naming work.
- **Decision: `SUPERSEDED`.**

### 3.11 `89d8fd78` — feat(naming): contract §4 step 3 — env vars, API root, Tauri identity, gate

- Branch `feat/h2-pipeline-integration`. 14 files, +101/−62 — **the same file set as `bc4a234f` on `feat/naming-step3`**.
- Purpose: the same `COGNITIVE_*` → `ARCHEAXIS_*` migration with legacy fallbacks, canonical `/api/v1` root, and legacy Tauri identity rebrand.
- Observed evidence: no test run. **`git diff-tree --numstat` output for `89d8fd78` and `bc4a234f` is identical (14 records, identical per-file line counts)**; the two commits have different trees only because they sit on different bases. All 14 paths are evolved in the baseline, and `tests/test_gateway_rate_limit.py` is byte-identical in both.
- Authority alignment: identical to `bc4a234f` (audited in batch 01) — aligned and already satisfied; the Tauri identity was later deliberately changed to `…workspace.recovery`.
- **Decision: `SUPERSEDED`.** This is a **duplicate of an already-audited change on another branch** (see §4, R-06). Porting either copy is redundant and porting this one would regress the recovery-identity decision.

### 3.12 `65252844` — feat(naming): full V2 sweep — docs/UI/code to ArcheAxis Knowledge & ArcheAxis-Knowledge-OS

- 54 files, +103/−103 (mechanical rename sweep). **21 of the 54 are byte-identical to the baseline.**
- Purpose: rename every active surface from the V1/Cognitive names to `ArcheAxis Knowledge` / `ArcheAxis-Knowledge-OS`.
- Observed evidence: no test run. Identical-to-baseline examples: `docs/NAMING_CONTRACT_V2.md`, `docs/PRODUCT_POSITIONING.md`, `config/product-naming-registry.yaml`, `docs/truth/NAMING_CONTRACT_V1.md`, `docs/current/SCOPE_LEDGER_V2.yaml`, two ADRs, `ecosystem.config.cjs`, three `migrations/reports/**` files, three `workspace/intake/**` files, `tests/…` none. Absent: `app/workspace/ui/index.html`, `workspace/ui/archeaxis/README.md`.
- Authority alignment: aligned — `NAMING_CONTRACT_V2` §2/§5 is the binding naming authority and the baseline reflects the post-sweep names.
- **Decision: `SUPERSEDED`.** A rename sweep whose result is already in the baseline, with 21 files provably identical. The only two absent paths are legacy web-UI paths.

### 3.13 `86846369` — fix(naming): align test assertions and release installer to V2 names

- 9 files, +15/−15: `.github/workflows/release.yml`, `tests/test_ci_a0_gates.py`, `tests/test_desktop_runtime.py` (identical), `tests/test_naming_conventions.py`, `tests/test_phase7_runtime_vertical_slice.py` (identical), `tests/test_product_truth_contract.py` (identical), `tests/test_product_version_truth_contract.py`, `tests/test_release_manifest.py`, `tests/test_workspace_api.py`.
- Purpose: follow-up assertion/installer naming alignment.
- Observed evidence: no test run; three of nine test files are byte-identical.
- Authority alignment: aligned; superseded by later naming/CI work (`locked-*.txt`, `R6-VERSION-RELEASE-FREEZE.md`).
- **Decision: `SUPERSEDED`.**

### 3.14 `c2019e0c` — fix(naming): sweep remaining active surfaces to V2 (NSIS/backend/smokes/SVG)

- 7 files, +9/−9: `desktop/scripts/verify_nsis_install.ps1`, `desktop/src-tauri/icons/icon.svg` (identical), `desktop/src-tauri/src/backend.rs`, `docs/PRODUCT_STAGE_COMPATIBILITY.md` (identical), `scripts/a0_browser_smoke.py`, `scripts/runtime_http_smoke.py`, `tests/test_workspace_api.py`.
- Purpose: finish the naming sweep on installer/backend/smoke/icon surfaces.
- Observed evidence: no test run; two files byte-identical.
- Authority alignment: aligned but historical; the legacy Tauri installer path is now a recovery reference (`desktop/` is not the formal desktop).
- **Decision: `SUPERSEDED`.**

### 3.15 `69e1b2a2` — fix(naming): ARCHEAXIS_DATA_DIR fallback in resolve_runtime_path + evaluation_fallback

- 3 files, +9/−8: `shared/config.py` (evolved), `shared/evaluation_fallback.py` (evolved), `tests/test_hardening.py` (evolved).
- Purpose: make `resolve_runtime_path` prefer `ARCHEAXIS_DATA_DIR` and keep `COGNITIVE_DATA_DIR` as fallback.
- Observed evidence: no test run. **The baseline `shared/config.py` contains exactly this semantics**: `resolve_runtime_path` documents "Canonical root: ARCHEAXIS_DATA_DIR (wins when set). Legacy fallback: COGNITIVE_DATA_DIR", reads both, and emits a legacy-env warning.
- Authority alignment: aligned with `NAMING_CONTRACT_V2` §2.
- **Decision: `SUPERSEDED`.** The exact behaviour is resident in the baseline.

### 3.16 `3227f1ef` — ci: trigger rerun with data-dir fix

- **0 file changes.** Empty CI-trigger commit.
- Observed evidence: `git diff-tree --numstat` returns no records.
- Authority alignment: not applicable — carries no content.
- **Decision: `KEEP`.** Recorded as `KEEP` only in the sense of *retain as history*: it has no diff to absorb, supersede or conflict with, and it is the sole non-`SUPERSEDED` entry in this batch. It authorizes nothing and should not be cherry-picked (an empty commit carries no change).

### 3.17 `fbdcf526` — fix(naming): readiness protocol validates ArcheAxis Knowledge + chunk length

- 2 files, +3/−3: `desktop/src-tauri/src/backend.rs` (evolved), `desktop/src-tauri/src/protocol.rs` (**identical**).
- Purpose: readiness-protocol naming/validation alignment in the legacy Tauri backend.
- Observed evidence: no test run; one file byte-identical.
- Authority alignment: superseded — the legacy Tauri shell is a recovery/behavior reference; the formal desktop is Avalonia.
- **Decision: `SUPERSEDED`.**

### 3.18 `4ebc90a4` — fix(boundary): project-local test routing — run_tests.sh + pycache resolve guard

- 3 files, +64/−1: `AGENTS.md` (+1), `scripts/ci/run_tests.sh` (new, +59), `tests/conftest.py` (+4/−1).
- Purpose (read from diff): a project-root-guarded test entry point that pins pytest `--basetemp` and `TMP/TEMP/TMPDIR/PYTHONPYCACHEPREFIX` inside `.hermes/task-runtime`, plus an MSYS-path guard `(_TASK_RUNTIME / "pycache").resolve()` in `tests/conftest.py` so a `/d/...` path cannot resolve to `D:\d\...` in Windows Python.
- Observed evidence: no test run. **The `conftest.py` `resolve()` guard is present verbatim in the baseline** (comment included) together with the `TMP/TEMP/TMPDIR` and `PYTHONPYCACHEPREFIX` injection. The baseline `scripts/ci/run_tests.sh` still exists but now routes to `.project-local/build/venv/...` (registered toolchain) instead of the `.hermes/task-runtime` pattern.
- Authority alignment: **the intent is aligned but the destination changed.** `AGENTS.md` §3 now names `.project-local/` (via `scripts/runtime/dev.py`) as the project runtime root and keeps `.hermes/` as preserved legacy material with "no new development writes"; `.hermes/task-runtime` is therefore no longer the authorized root.
- **Decision: `SUPERSEDED`.** Both substantive halves are either resident (the `resolve()` guard) or replaced by the current `.project-local` routing.
- **Relevance note:** this commit is the origin of the test-run-root pattern that made DP-F01's Python lane need a sandbox shim (the root-checkout run root is not writable to a Python child in this session). That is recorded in the DP-F01 card, not here.

### 3.19 `e1df9279` — docs(naming): run_tests.sh header to ArcheAxis-Knowledge-OS

- 1 file, +1/−1: `scripts/ci/run_tests.sh` (evolved).
- Purpose: one-line header/name correction.
- Observed evidence: no test run.
- Authority alignment: aligned; superseded by the later rewrite of the same script.
- **Decision: `SUPERSEDED`.**

## 4. Batch-02 findings beyond per-SHA decisions

- **R-06 — cross-branch duplicated change (verified).** `89d8fd78` (`feat/h2-pipeline-integration`) and `bc4a234f` (`feat/naming-step3`, audited in batch 01) carry the **same 14-file change with identical per-file line counts**. Branch-level SHA counting therefore double-counts this migration. Any donor scan or "unmerged work" metric must de-duplicate by diff, not by SHA.
- **Absorption is unusually strong in this batch.** 37 of 153 records (24%) are byte-identical to the baseline, including four *test* files from `70c38a1c` and the entire `worker.py` + worker/delivery tests from `d13c9cb6`. Product-bearing work from these branches is resident, not missing.
- **The repository has its own donor-asset archive.** The baseline carries `docs/history/donor-branch-assets/` preserving selected files from five branches — `agent/phase5-research-knowledge-governance` (4), `feat/archeaxis-desktop-a1-violet-core` (2), `feat/p1-compat-kernel-hardening` (3), `feat/portable-data-root` (3), `fix/desktop-close-request-destroy` (1). Three of batch 02's ten absent paths —
  `tests/test_format_capabilities.py`, `workspace/intake/2026-08-09-multiformat-capability-boundary.md`, `workspace/intake/2026-08-09-online-learning-corpus.md` — are preserved there under `feat/p1-compat-kernel-hardening/`.
- **Archive coverage is partial, so "absent" must not be read as "lost".** Cross-checking batch 01's absent set against the archive: `requirements-ci-adapters.txt` is preserved (1 match) while `app/workspace/ui/assets/app.js`, `requirements-ci.txt`, `tests/test_ui01_navigation_contract.py` and `workspace/ui/archeaxis/README.md` have **no** archived copy. Those four are therefore genuinely unrestored legacy-web-UI/CI artifacts — a factual, bounded preservation note, not a claim that content was deleted by this run.

## 5. Batch summary table

| # | SHA | Branch | Date | Files | Absent/Identical | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `5a519836` | p1-compat-kernel-hardening | 2026-08-09 | 18 | 2 / 0 | SUPERSEDED |
| 2 | `70c38a1c` | p1-compat-kernel-hardening | 2026-08-09 | 4 | 0 / 4 | SUPERSEDED |
| 3 | `ba31d95a` | p1-compat-kernel-hardening | 2026-08-09 | 3 | 0 / 1 | SUPERSEDED |
| 4 | `10f04df6` | p1-compat-kernel-hardening | 2026-08-09 | 2 | 2 / 0 | SUPERSEDED |
| 5 | `2f9540ba` | p1-compat-kernel-hardening | 2026-08-09 | 2 | 0 / 0 | SUPERSEDED |
| 6 | `d13c9cb6` | p1-compat-kernel-hardening | 2026-08-08 | 8 | 0 / 3 | SUPERSEDED |
| 7 | `237403e9` | p1-compat-kernel-hardening | 2026-08-09 | 4 | 0 / 0 | SUPERSEDED |
| 8 | `84a0dfdb` | p1-compat-kernel-hardening | 2026-08-09 | 1 | 1 / 0 | SUPERSEDED |
| 9 | `60011096` | p1-compat-kernel-hardening | 2026-08-10 | 12 | 3 / 0 | SUPERSEDED |
| 10 | `bebc5a74` | p1-compat-kernel-hardening | 2026-08-10 | 6 | 0 / 1 | SUPERSEDED |
| 11 | `89d8fd78` | h2-pipeline-integration | 2026-08-12 | 14 | 0 / 1 | SUPERSEDED (duplicate of `bc4a234f`) |
| 12 | `65252844` | h2-pipeline-integration | 2026-08-12 | 54 | 2 / 21 | SUPERSEDED |
| 13 | `86846369` | h2-pipeline-integration | 2026-08-12 | 9 | 0 / 3 | SUPERSEDED |
| 14 | `c2019e0c` | h2-pipeline-integration | 2026-08-12 | 7 | 0 / 2 | SUPERSEDED |
| 15 | `69e1b2a2` | h2-pipeline-integration | 2026-08-12 | 3 | 0 / 0 | SUPERSEDED |
| 16 | `3227f1ef` | h2-pipeline-integration | 2026-08-12 | 0 | 0 / 0 | KEEP (empty commit, no diff) |
| 17 | `fbdcf526` | h2-pipeline-integration | 2026-08-12 | 2 | 0 / 1 | SUPERSEDED |
| 18 | `4ebc90a4` | h2-pipeline-integration | 2026-08-12 | 3 | 0 / 0 | SUPERSEDED |
| 19 | `e1df9279` | h2-pipeline-integration | 2026-08-12 | 1 | 0 / 0 | SUPERSEDED |

## 6. Limits and verification

**Verification performed for this report**

| Check | Result |
| --- | --- |
| `branch-batch-02.json` claim verifier (`.project-local/dsh-audit/verify_batch02.py`) | `report_commits=19 facts_commits=19`, `records total=153 absent=10 identical=37 evolved=106`, decisions `{SUPERSEDED: 18, KEEP: 1}`, **`errors=0`** |
| Per-commit `file_count` / `absent` / `identical` / `subject` / branch vs collected git facts | 19/19 match |
| Coverage aggregates vs git facts | match (153 / 10 / 37 / 106) |
| Decision tally vs per-commit decisions | match |
| Absent-path set exact equality against `git cat-file -e` results | 10/10, set-equal |
| Cross-branch duplication `89d8fd78` vs `bc4a234f` | `diff-tree --numstat` identical → `True` |
| `json.load` on the report | strict parse OK |
| `git diff --check` in the worktree | exit 0 |

The verifier initially reported 38 errors; the cause was **verifier-side**, not report-side — the
report records unambiguous 8-character SHA prefixes while the collected facts carry full 40-character
SHAs. Three further mismatches were em-dash/§ transliteration introduced by the PowerShell
collection step; those subject strings were normalised to the exact commit text. Both defects are
recorded here because the DP-GIT-01 audit made a point of disclosing its own self-corrections.

**Limits**

- **Not exhaustive.** 36 SHAs audited across two batches. Remaining inventory includes `axw/execution-h0` (8), `axw/execution-h1` (16), `agent/phase5-research-knowledge-governance` (1), `feat/absorption-adopt-now` (7), `feat/absorption-roadmap-r0` (7), `audit/unreleased-real-version` (2), `chore/naming-repo-refs` (3), `fix/desktop-close-request-destroy` (1), `work/tp12-facades` (1), the 149-commit `codex/frozen-roadmap-deepseek-v1`, and the 166-record `codex/aaos-p3-ui-convergence-20260922`. No conclusion here generalizes to them.
- **No test was executed for any SHA in this batch.** Every "observed evidence" line describes file and blob state in the baseline, not a passing run.
- **Remote state not verified:** no `git fetch`; branch tips resolve from the local object store. No live GitHub PR state was read.
- **No authorization implied:** `SUPERSEDED` does not authorize branch deletion; `KEEP` on `3227f1ef` means only "retain as history".
- Report artifacts: `docs/current/dsh-review/branch-batch-02.md` and `branch-batch-02.json` — the only files written by this batch.
