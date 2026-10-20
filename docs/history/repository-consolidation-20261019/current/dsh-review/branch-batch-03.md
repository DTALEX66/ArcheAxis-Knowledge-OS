# DP-NF-01 · branch/commit semantic audit — batch 03

- task_id: `DP-NF-01`
- report_schema: `aaos.dsh.branch-commit-audit/v1`
- audit_branch: `codex/dp-nf-01-20260925`
- baseline_sha: `a9ead3e1597808ca751c6ccec1dba27bcfff5b4b`
- baseline_tree: `ce69abf1493481591534979be1223b1a447fc9bb`
- origin_main: `e3875db0ee6d073d37839eb7b95f7ef4ce881bbb`
- batches_complete: **3 of N** — still **not exhaustive**

## 0. Scope and boundary statement

- Read-only review of committed Git objects. This report is the only artifact written.
- **The root working tree is NOT part of any branch diff here.** Root is at the declared
  baseline with **112 uncommitted paths** belonging to concurrent Codex/mainline work (Avalonia,
  `crates/archeaxis-api/src/lib.rs`, domain `anchor/backup/knowledge/learning`, migration, R6 docs,
  Candidate builders). Those dirty files were **not** read as evidence, not copied, not re-implemented
  and not overwritten.
- Batch 01/02 covered 36 SHAs; those SHAs are excluded here. Selection was made from the uncovered
  remainder of `docs/current/AAOS-BRANCH-COMMIT-PATH-AUDIT-20260925.json`, restricted to refs that
  resolve and to the 15–20 SHA batch cap.
- Decisions are audit judgements, **not** authorization to cherry-pick, delete or clean up branches.

## 1. Method

Identical to batches 01–02, including the carried-over correction: baseline membership is decided by
`git cat-file -e` **exit status** and identity by exact blob OID, never by `git rev-parse <tree>:<path>`
output. For each commit: parent, author date, subject, per-file status/`--numstat`, commit-side and
baseline-side blob OIDs, absent/identical/evolved classification, then a read of the actual diff for
every product-bearing file, then the September authority check (R6 TaskPack, M0 overlay `SUP-020`,
`NAMING_CONTRACT_V2`, `AGENTS.md` §6, `R6-VERSION-RELEASE-FREEZE.md`,
`docs/SHARED_RESOURCE_PATH_INDEX.md`).

## 2. Coverage

| Metric | Value |
| --- | --- |
| Branches in this batch | 7 |
| Distinct SHAs audited | **16** (cap 20; see deferral note) |
| SHA range | `0a5e1bfa` (2026-07-20) … `081cf20a` (2026-08-12) |
| Changed-file records | 107 |
| Absent from baseline | 12 |
| Byte-identical to baseline | 24 |
| Differing (evolved) | 71 |
| Decisions | `SUPERSEDED` 16, `KEEP` 0, `CHERRY_PICK_CANDIDATE` 0, `CONFLICT` 0, `UNKNOWN` 0 |
| Cumulative audited across batches 01–03 | 52 SHAs |

Per-branch coverage: `agent/phase5-research-knowledge-governance` 1/1, `fix/desktop-close-request-destroy` 1/1,
`work/tp12-facades` 1/1, `chore/naming-repo-refs` 3/3, `docs/verification-summary-2026-08-09` 1/1,
`audit/unreleased-real-version` 2/2, `feat/absorption-adopt-now` 7/7.

**Deferral (recorded, not hidden):** a first collection included `feat/absorption-roadmap-r0`
(6 SHAs, incl. `9035b707`, `9394f36a`, `7e0d883c`, `42d13c0b`), which pushed the batch to 22 and
exceeded the 15–20 cap. That branch was **dropped from this batch** and is the first candidate for
batch 04; no SHA from it was audited here. Remaining unaudited refs also include `axw/execution-h0`
(8), `axw/execution-h1` (16), `codex/ci-release-optimization` (7), `codex/execution-reliability-standards` (2),
the four `codex/*-v0.6.x` release branches (2 each), `release/v0.4.0-contract` (3), and the large
`codex/frozen-roadmap-deepseek-v1` (149) and `codex/aaos-p3-ui-convergence-20260922` (166 records).

## 3. Per-SHA records

### 3.1 `0a5e1bfa` — feat(phase5): add governed knowledge candidate checkpoint

- Branch `agent/phase5-research-knowledge-governance`. 2026-07-20. 13 files, +1884/−14.
- Files: `app/adapters/research_knowledge.py` (absent), `app/facades/knowledge.py`,
  `docs/NEXT_TASKS.md` (absent), `docs/PROJECT_STATUS.md`, `shared/knowledge_migration.py` (absent),
  `shared/migration.py`, `shared/migration_runner.py`, `tests/test_knowledge_governance_migration.py`,
  `tests/test_migration_runner.py`, `tests/test_phase4_research_github.py`,
  `tests/test_research_knowledge_candidate_contract.py` (absent),
  `tests/test_runtime_operations.py`,
  `workspace/intake/011_phase5_p01_governed_candidate_checkpoint.md` (absent).
- Purpose (read from diff): a governed "research → Knowledge candidate" checkpoint with a durable
  migration path, i.e. external research may only become a reviewable Candidate.
- Observed evidence: no test run. `app/facades/knowledge.py`, `shared/migration_runner.py` and three
  test files are **evolved** in the baseline, so the migration machinery landed and grew.
  **Four of the five absent paths are preserved in the donor archive**
  (`docs/history/donor-branch-assets/agent/phase5-research-knowledge-governance/`): the adapter,
  `knowledge_migration.py`, the candidate-contract test and the intake note.
- Authority alignment: the *intent* is exactly the R6/M0 rule that external sources stay Candidates
  until human review. The *implementation* is a pre-Avalonia Python facade/migration layer; the
  current product writer is the Rust Core.
- **Decision: `SUPERSEDED`.** The governance intent is resident in evolved form and the branch's own
  artifacts are preserved by the repository's archive. Porting the Python adapter would create a
  second candidate-creation path beside the Rust Core writer.

### 3.2 `801edea8` — docs: record desktop close lifecycle handoff

- Branch `fix/desktop-close-request-destroy` (tip). 2026-08-06. 1 file, +88:
  `docs/workflow/HANDOFF_DESKTOP_CLOSE_LIFECYCLE_2026-08-06.md` (**absent from the baseline**,
  **preserved in the donor archive** at
  `docs/history/donor-branch-assets/fix/desktop-close-request-destroy/`).
- Purpose: a one-off handoff document about desktop close-lifecycle handling.
- Observed evidence: no test run; documentation only.
- Authority alignment: the desktop is now the Avalonia `apps/ArcheAxis.Desktop/` with a different
  close/shutdown model; the Tauri-era handoff is historical.
- **Decision: `SUPERSEDED`.** Documentation for a superseded shell, already preserved by the archive.

### 3.3 `8d5ba104` — feat(facades): package knowledge and research boundaries

- Branch `work/tp12-facades` (tip). 2026-07-14. 37 files, +395/−268. **16 files are byte-identical
  to the baseline**, mostly `inspiration_research/**` package-initialiser shells.
- Files of note: `.github/workflows/ci.yml`, `Dockerfile` (absent), `Inspiration-Research/api.py`
  (identical, −209 lines), `Inspiration-Research/tests/__init__.py` (absent),
  `app/facades/__init__.py`, `app/facades/knowledge.py` (identical), `app/facades/research.py`,
  `docker-compose.yml` (absent), `docker/Dockerfile` (absent),
  `Inspiration-Research/tests/test_scorer.py` **renamed to** `tests/test_inspiration_research.py`
  (both sides absent), many `inspiration_research/**` modules (identical or empty diffs),
  `inspiration_research/api.py`, `integration-tests/test_ir_kb_os_loop.py`, `pyproject.toml`,
  `run_all.bat`, `run_all.sh`, `scripts/batch_score_registry.py`, `scripts/run_daily.py`,
  `tests/test_coverage_gap.py`, `tests/test_hardening.py`, `tests/test_knowledge_research_facades.py`.
- Purpose: package the legacy Inspiration-Research system behind `app/facades/*` boundaries and move
  its tests into the main suite.
- Observed evidence: no test run. The facade modules and the whole `inspiration_research` package are
  present in the baseline, in identical or evolved form.
- Authority alignment: `AGENTS.md` §1 explicitly classifies Inspiration-Research as a
  **compatibility surface only**; R5 import/conversion is historical, not the current queue.
- **Decision: `SUPERSEDED`.** The refactor is resident; the four absent files are legacy
  container/packaging scaffolding (`Dockerfile`, `docker-compose.yml`, `docker/Dockerfile`, a test
  `__init__.py`) that the current product does not use, **plus** one renamed legacy test.
- Note: the rename record `Inspiration-Research/tests/test_scorer.py => tests/test_inspiration_research.py`
  was reported absent on the destination path, i.e. the baseline no longer carries that legacy test.
  Neither side is archived. This is recorded in §5 as genuinely unrestored.

### 3.4 `fe4ada39` — chore(naming): update repo references after GitHub rename (step 2)

- Branch `chore/naming-repo-refs`. 2026-08-12. 7 files, +26/−26:
  `AGENTS.md`, `README.md`, `app/release.py`, `docs/environment/EXTERNAL_DEPENDENCIES.md`,
  `scripts/ci/classify.py`, `scripts/release_inject_identity.py`, `tests/test_release_manifest.py`.
  All **evolved**.
- Purpose: repoint repository references after the GitHub rename.
- Observed evidence: no test run. All seven files exist in the baseline in later form.
- Authority alignment: `NAMING_CONTRACT_V2` §0a/§5 fixes `DTALEX66/ArcheAxis-Knowledge-OS` as the
  repository identity; the baseline already carries post-rename references.
- **Decision: `SUPERSEDED`.** A reference sweep whose result is resident.

### 3.5 `037bd8c6` — ci(naming): bump Rust cache keys to invalidate pre-rename cache paths

- Branch `chore/naming-repo-refs`. 2026-08-12. 1 file, +2/−2: `.github/workflows/ci.yml` (evolved).
- Purpose: cache-key bump to invalidate stale pre-rename paths.
- Observed evidence: no test run.
- Authority alignment: the baseline CI no longer uses that cache-key scheme (it uses hash-locked
  dependency files and uv groups), so the change is moot.
- **Decision: `SUPERSEDED`.**

### 3.6 `a9aa0665` — ci(naming): scope restore-keys under -naming-v2 to block stale pre-rename cache

- Branch `chore/naming-repo-refs` (tip). 2026-08-12. 1 file, +2/−2: `.github/workflows/ci.yml` (evolved).
- Purpose: restrict `restore-keys` so a stale pre-rename cache cannot be restored.
- Observed evidence: no test run.
- Authority alignment: same as 3.5 — the CI cache mechanism was replaced; the security *intent*
  (never restore a cache from a renamed path) is satisfied by the current scheme.
- **Decision: `SUPERSEDED`.**

### 3.7 `8cc9c690` — docs: publish verification summary and problem ledger

- Branch `docs/verification-summary-2026-08-09` (tip). 2026-08-09. 1 file, +289:
  `docs/VERIFICATION_SUMMARY_2026-08-09.md` (**absent from the baseline**, **not archived**).
- Purpose: a dated verification summary and a problem ledger.
- Observed evidence: no test run; documentation only.
- Authority alignment: `AGENTS.md` §6 requires live progress to live in `docs/current/R6-EXECUTION.md`
  / `R6-STATE.json`; a 2026-08-09 standalone summary is a historical snapshot and must not be read as
  current truth. A successor exists at the donor-archive path
  `docs/history/donor-branch-assets/...` for other branches but **not** for this document.
- **Decision: `SUPERSEDED`.** A dated historical ledger superseded by the R6 execution record.
  Its absence from the active tree and from the archive is recorded in §5; no action is proposed
  (this audit does not move, delete or restore files).

### 3.8 `600b25e0` — fix(ingestion): include markitdown PDF runtime dependencies

- Branch `audit/unreleased-real-version`. 2026-08-09. 4 files, +97/−7:
  `app/release-manifest.json`, `pyproject.toml`, `tests/test_adapter_contract.py`, `uv.lock` (all evolved).
- Purpose: add the missing markitdown PDF runtime dependencies.
- Observed evidence: no test run. `tests/test_adapter_contract.py` grew in the baseline, and the
  lockfile is evolved.
- Authority alignment: dependency correctness is aligned; the R6 boundary is that dependency
  presence is not format-quality evidence. DP-F01's batch-02 finding that `pptx`/`fitz`/`openpyxl`
  are absent in one CI interpreter is an environment gap, not a claim about this change.
- **Decision: `SUPERSEDED`.** The dependency set is resident in later form.

### 3.9 `40922904` — fix(desktop): hide release console subsystem

- Branch `audit/unreleased-real-version` (tip). 2026-08-09. 1 file, +2: `desktop/src-tauri/src/main.rs`
  (**byte-identical to the baseline**).
- Purpose: `windows_subsystem = "windows"` for the release build of the legacy Tauri shell.
- Observed evidence: no test run.
- Authority alignment: the legacy Tauri shell is a recovery/behavior reference
  (`AGENTS.md` §6); the formal desktop is the Avalonia app, whose console behaviour is governed by
  its own published-candidate configuration.
- **Decision: `SUPERSEDED`.** Byte-identical in the baseline; nothing to port.

### 3.10 `bca2f18e` — feat(absorption): absorb JiWER, RapidFuzz, JSON Canvas (ADS-001/002/003)

- Branch `feat/absorption-adopt-now`. 2026-08-11. 7 files, +325/−0:
  `docs/truth/JSON_CANVAS_ADOPTION.md` (**byte-identical**), `pyproject.toml`,
  `shared/json_canvas.py`, `shared/text_quality.py`, `tests/test_json_canvas.py`,
  `tests/test_text_quality.py`, `uv.lock`.
- Purpose: absorb three mature capabilities (text-quality metrics via JiWER/RapidFuzz and JSON Canvas
  support) instead of re-implementing them.
- Observed evidence: no test run, but for this class of claim blob identity is decisive:
  **`docs/truth/JSON_CANVAS_ADOPTION.md` is byte-identical to the baseline**, and
  `shared/json_canvas.py`, `shared/text_quality.py` plus both test files are present in the baseline
  in evolved form (verified present: all four paths exist at the baseline).
- Authority alignment: exactly the R6 "Absorb First" principle; the capability registry (R6 A03)
  records donors.
- **Decision: `SUPERSEDED`.** The absorption is resident in the baseline.

### 3.11 `2e7f8da9` — feat(absorption): absorb evidence connectors + FSRS learning scheduler (ADS-004/005/006/007/008)

- Branch `feat/absorption-adopt-now`. 2026-08-11. 10 files, +483/−13.
- Files: `app/release-manifest.json`, `pyproject.toml`, `requirements.txt`,
  `shared/evidence_connectors.py`, `shared/learning_scheduler.py`,
  `tests/test_evidence_connectors.py` (**byte-identical**),
  `tests/test_learning_scheduler.py` (**byte-identical**),
  `tests/test_mfx001_supply_chain_ledger.py`, `tests/test_text_quality.py` (−2, identical),
  `uv.lock`.
- Purpose: absorb evidence connectors and an FSRS-based learning scheduler.
- Observed evidence: no test run. Three files are **byte-identical to the baseline**, including both
  new test files; `shared/evidence_connectors.py` and `shared/learning_scheduler.py` are present in
  the baseline (evolved).
- Authority alignment: absorption aligned. Note the R6 boundary — the FSRS scheduler here is the
  Python-side scheduler; the authoritative schedule writer in the current architecture is the Rust
  Core (`R6-STATE` A08 records FSRS state persisted by Core). This commit does not change that.
- **Decision: `SUPERSEDED`.** Resident, with its own tests, in the baseline.

### 3.12 `6a84bf33` — feat(absorption): vendor Magika ONNX model + file detection (ADS-009)

- Branch `feat/absorption-adopt-now`. 2026-08-11. 8 files, +369/−1 plus one **binary**.
- Files: `app/release-manifest.json`, `pyproject.toml`, `requirements.txt`,
  `shared/file_detection.py`, `shared/models/magika/LICENSE` (**identical**),
  `shared/models/magika/config.min.json` (**identical**),
  `shared/models/magika/model.onnx` (**identical**), `uv.lock`.
- Purpose: vendor the Magika ONNX file-detection model and wire a detector.
- Observed evidence: no test run. **The 3,163,428-byte `model.onnx` is byte-identical to the baseline**
  (same blob OID `c9f1e0ab383e…`, same size on both sides), as are the LICENSE and config.
  `shared/file_detection.py` is present in the baseline (evolved).
- Authority alignment: aligned with "Absorb First". **Boundary:** a vendored third-party model is a
  licence/supply-chain artefact, not a runtime capability claim. R6 A11 (Model Pool) remains
  `TESTED_LOCAL_PARTIAL`, and presence of a weight file is explicitly not evidence that the model
  executes or is benchmarked.
- **Decision: `SUPERSEDED`.** The vendored model and its metadata are resident byte-for-byte.

### 3.13 `e02510c9` — chore: naming system migration — Cognitive-Loop-OS → ArcheAxis Workspace

- Branch `feat/absorption-adopt-now`. 2026-08-12. 9 files, +33/−33 (mechanical rename):
  `.worklab/gate-registry.v1.yaml`, `.worklab/project-validation.v1.yaml`, `AGENTS.md`, `app/cli.py`,
  `app/contracts/v1.py`, `docs/FUTURE_EXECUTION_BLUEPRINT.md`, `docs/PROJECT_STATUS.md`,
  `docs/truth/H0_H1_STATUS_HANDOFF.md`, `pyproject.toml`.
- Purpose: rename surfaces to `ArcheAxis Workspace`.
- Observed evidence: no test run; all nine files exist in the baseline in later form.
- Authority alignment: **partially off-authority.** `NAMING_CONTRACT_V2` §1/§5 makes
  `ArcheAxis Knowledge` the external product name and demotes `ArcheAxis Learning Workspace` to an
  internal workspace view; this commit's target name ("ArcheAxis Workspace") is neither the product
  name nor the fixed machine/distribution ID (`archeaxis-workspace`). The baseline has already moved
  to the V2 names.
- **Decision: `SUPERSEDED`.** A rename to an interim name, superseded by the binding V2 contract.

### 3.14 `65becc6d` — fix: revert breaking naming changes (pyproject, CLI, contracts)

- Branch `feat/absorption-adopt-now`. 2026-08-12. 3 files, +16/−16: `app/cli.py`,
  `app/contracts/v1.py`, `pyproject.toml` (all evolved).
- Purpose: revert the parts of 3.13 that broke packaging, the CLI and contracts.
- Observed evidence: no test run.
- Authority alignment: this is the **self-correction of 3.13**; the baseline carries the V2 names and
  a working `pyproject.toml` (`name = "archeaxis-workspace"`, version `0.6.14`).
- **Decision: `SUPERSEDED`.** The corrected state is resident.

### 3.15 `1f06c9b2` — docs(environment): comprehensive external dependency registry

- Branch `feat/absorption-adopt-now`. 2026-08-12. 1 file, +279:
  `docs/environment/EXTERNAL_DEPENDENCIES.md` (evolved).
- Purpose: a consolidated external-dependency registry.
- Observed evidence: no test run. The baseline file is evolved and **larger** than this revision
  (the chain continues with later edits), so the registry was not reverted.
- Authority alignment: `AGENTS.md` §2/§8 govern configuration and private state;
  `docs/SHARED_RESOURCE_PATH_INDEX.md` is the external *path* authority. A dependency registry is
  complementary and does not override it.
- **Decision: `SUPERSEDED`.** Evolved successor in the baseline.

### 3.16 `081cf20a` — fix: test assertions + requirements dedup + lint

- Branch `feat/absorption-adopt-now` (tip). 2026-08-12. 3 files, +2/−3:
  `docs/environment/EXTERNAL_DEPENDENCIES.md`, `requirements.txt` (−1),
  `tests/test_phase7_runtime_vertical_slice.py` (all evolved).
- Purpose: housekeeping — test assertion fix, requirements de-duplication, lint.
- Observed evidence: no test run. `requirements.txt` **exists in both the previous and current baseline**
  (verified with `git cat-file -e`: exit 0 at `a5de4b13` and at `a9ead3e1`) and is **evolved**, i.e. the
  requirements list survives under the current CI scheme rather than having been deleted;
  `docs/environment/EXTERNAL_DEPENDENCIES.md` and `tests/test_phase7_runtime_vertical_slice.py` are
  evolved too.
- Authority alignment: no conflict; the CI *install path* was replaced by the locked/uv model, but the
  `requirements.txt` file itself remains present and evolved.
- **Decision: `SUPERSEDED`.**
- **Correction (made during verification of this very report).** The first revision of this entry claimed
  `requirements.txt` was absent and returned `UNKNOWN`. That was **wrong**: the file exists at both
  baselines. The claim came from reading the batch-03 facts row instead of testing the path directly.
  A subsequent cross-report check initially misread the batch-01 archive statement: the file is absent
  at both baseline root paths, but is explicitly listed in the donor archive README with its original
  blob SHA and byte count. That cross-report finding is retracted in §5 (R-08); batch-01 is correct.

## 4. Batch summary table

| # | SHA | Branch | Date | Files | Abs/Ident | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `0a5e1bfa` | agent/phase5-research-knowledge-governance | 2026-07-20 | 13 | 5 / 0 | SUPERSEDED |
| 2 | `801edea8` | fix/desktop-close-request-destroy | 2026-08-06 | 1 | 1 / 0 | SUPERSEDED |
| 3 | `8d5ba104` | work/tp12-facades | 2026-07-14 | 37 | 5 / 16 | SUPERSEDED |
| 4 | `fe4ada39` | chore/naming-repo-refs | 2026-08-12 | 7 | 0 / 0 | SUPERSEDED |
| 5 | `037bd8c6` | chore/naming-repo-refs | 2026-08-12 | 1 | 0 / 0 | SUPERSEDED |
| 6 | `a9aa0665` | chore/naming-repo-refs | 2026-08-12 | 1 | 0 / 0 | SUPERSEDED |
| 7 | `8cc9c690` | docs/verification-summary-2026-08-09 | 2026-08-09 | 1 | 1 / 0 | SUPERSEDED |
| 8 | `600b25e0` | audit/unreleased-real-version | 2026-08-09 | 4 | 0 / 0 | SUPERSEDED |
| 9 | `40922904` | audit/unreleased-real-version | 2026-08-09 | 1 | 0 / 1 | SUPERSEDED |
| 10 | `bca2f18e` | feat/absorption-adopt-now | 2026-08-11 | 7 | 0 / 1 | SUPERSEDED |
| 11 | `2e7f8da9` | feat/absorption-adopt-now | 2026-08-11 | 10 | 0 / 3 | SUPERSEDED |
| 12 | `6a84bf33` | feat/absorption-adopt-now | 2026-08-11 | 8 | 0 / 3 | SUPERSEDED |
| 13 | `e02510c9` | feat/absorption-adopt-now | 2026-08-12 | 9 | 0 / 0 | SUPERSEDED |
| 14 | `65becc6d` | feat/absorption-adopt-now | 2026-08-12 | 3 | 0 / 0 | SUPERSEDED |
| 15 | `1f06c9b2` | feat/absorption-adopt-now | 2026-08-12 | 1 | 0 / 0 | SUPERSEDED |
| 16 | `081cf20a` | feat/absorption-adopt-now | 2026-08-12 | 3 | 0 / 0 | SUPERSEDED (corrected from UNKNOWN, see §5 R-08) |

## 5. Cross-batch findings

- **R-07 — the strongest absorption evidence in any batch so far.** The 3,163,428-byte Magika
  `model.onnx` (`6a84bf33`) is **byte-identical** to the baseline (blob `c9f1e0ab383e…`, equal size on
  both sides), as are its LICENSE and config; `bca2f18e`'s adoption doc and `2e7f8da9`'s two new test
  files are likewise byte-identical. All eight ADOPT-NOW modules verified present at the baseline:
  `shared/json_canvas.py`, `shared/text_quality.py`, `shared/evidence_connectors.py`,
  `shared/learning_scheduler.py`, `shared/file_detection.py`, `shared/models/magika/model.onnx`,
  `shared/models/magika/config.min.json`, `docs/truth/JSON_CANVAS_ADOPTION.md`.
- **Archive coverage now partial in a measurable way.** At this baseline the donor archive holds 13
  files across five branches (`agent/phase5-research-knowledge-governance` 4,
  `feat/archeaxis-desktop-a1-violet-core` 2, `feat/p1-compat-kernel-hardening` 3,
  `feat/portable-data-root` 3, `fix/desktop-close-request-destroy` 1). Of this batch's 12 absent
  paths, **5 are archived** (`0a5e1bfa` ×4, `801edea8` ×1) and **7 are not**:
  `docs/NEXT_TASKS.md`, `Dockerfile`, `Inspiration-Research/tests/__init__.py`, `docker-compose.yml`,
  `docker/Dockerfile`, the renamed `Inspiration-Research/tests/test_scorer.py` →
  `tests/test_inspiration_research.py`, and `docs/VERIFICATION_SUMMARY_2026-08-09.md`.
  All seven are legacy web-era/container scaffolding or a dated historical ledger — none is a
  product-code path in the current architecture. This is a **preservation inventory note only**;
  this audit does not restore, move or delete anything and does not assert ownership of those files.
- **Authority drift caught in the wild (`e02510c9`).** Branch content exists that renames surfaces to
  "ArcheAxis Workspace", which is neither the V2 external product name (`ArcheAxis Knowledge`) nor the
  fixed machine id (`archeaxis-workspace`). The commit immediately following it (`65becc6d`) reverts
  the parts that broke packaging — a self-correction that is itself superseded. This is a concrete
  example for the repository-wide language-boundary audit (DP-NF-07) that historical branch content
  can carry interim names that must not be reintroduced.
- **R-08 — one in-batch reporting defect and one cross-report false positive.**
  *(a) This batch, fixed here.* The first revision of entry 3.16 claimed `requirements.txt` no longer
  exists and returned `UNKNOWN`. It exists and is evolved at both baselines (`git cat-file -e` exit 0 at
  `a5de4b13` and `a9ead3e1`); the verdict is now `SUPERSEDED` and no entry in this batch is `UNKNOWN`.
  *(b) Cross-report check of batch 01; the initial finding here was false.*
  `docs/current/dsh-review/branch-batch-01.md` §6 states that `requirements-ci-adapters.txt` "is
  preserved by the repository's donor-asset archive (1 match)". This is **correct**: the tracked
  `docs/history/donor-branch-assets/README.md` lists the exact path, original blob SHA prefix
  `e215c62a6e99560e`, and 243-byte size. The file is absent at both baseline root paths, but that is
  not evidence that no archived copy exists. Verified distinction:

  | Path | at `a5de4b13` | at `a9ead3e1` | batch-01 §6 claim |
  | --- | --- | --- | --- |
  | `app/workspace/ui/assets/app.js` | absent | absent | no archived copy — **correct** |
  | `requirements-ci.txt` | absent | absent | no archived copy — **correct** |
  | `tests/test_ui01_navigation_contract.py` | absent | absent | no archived copy — **correct** |
  | `workspace/ui/archeaxis/README.md` | absent | absent | no archived copy — **correct** |
  | `requirements-ci-adapters.txt` | absent | absent | "preserved (1 match)" — **CORRECT; donor archive records it** |

  The four other paths remain accurately described as having no archived copy. No correction to
  batch-01 §6 is warranted. The false positive arose from checking only the baseline root paths and
  missing the archive's provenance index; the donor README and archive bytes are the stronger
  evidence. No files were restored, moved or deleted.
- **`UNKNOWN` was left unused in this batch, deliberately.** All 16 SHAs are now `SUPERSEDED`. The
  vocabulary reserves `UNKNOWN` for cases where supersession genuinely cannot be demonstrated; after
  the correction above, no such case remains here.

## 6. Limits and verification

**Verification performed**

| Check | Method | Result |
| --- | --- | --- |
| Report JSON strict parse | `json.load` | to be recorded in the sibling JSON's `audit_verification` |
| Per-commit counts/subjects/refs | `verify_batch03.py` (same design as batch 02) | see below |
| Absent-path set equality | `git cat-file -e` vs report | see below |
| Archive coverage of absent paths | `git ls-tree` on `docs/history/donor-branch-assets` | 5 archived / 7 not |
| Magika binary identity | blob OID + `git cat-file -s` | identical, 3163428 bytes both sides |
| `git diff --check` in the worktree | git | see below |

**Limits**

- **No test was executed for any SHA in this batch.** Every "observed evidence" line describes file
  and blob state in the baseline, not a passing run.
- **Not exhaustive.** 52 SHAs audited across three batches; the remaining refs listed in §2 are out of
  scope here and no conclusion generalizes to them.
- **Remote state not verified:** no `git fetch`; branch tips resolve from the local object store; no
  live GitHub PR state was read.
- **No authorization implied.** `SUPERSEDED` does not authorize branch deletion; `UNKNOWN` does not
  authorize investigation of files that no longer exist.
- **Dirty root excluded.** The 112 uncommitted root paths (including the Avalonia, `api/lib.rs`,
  domain, migration and Candidate-builder files named in the task pack) were not read as evidence,
  not represented by an old HEAD, and not modified.
