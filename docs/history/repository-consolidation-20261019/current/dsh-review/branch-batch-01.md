# DP-GIT-01 · branch/commit semantic audit — batch 01

- task_id: `DP-GIT-01`
- report_schema: `aaos.dsh.branch-commit-audit/v1`
- generated_at: `2026-09-25` (DSH run; see sibling JSON `generated_at` for the exact UTC stamp)
- audit_branch: `codex/dp-git-01-20260925`
- baseline_sha: `a5de4b13474c217e7a9dd34b8cbfa402e8297780`
- baseline_tree: `a4156ed65d50675822321b9d63eec932b1e76af3`
- origin_main: `e3875db0ee6d073d37839eb7b95f7ef4ce881bbb`
- compared_against: baseline first, then `origin/main` where the two differ
- batches_complete: **1 of N** — this report is explicitly **not exhaustive**

## 0. Scope and boundary statement

- This is a **read-only product review of committed Git objects**. No product source was changed, no branch was created, deleted, merged or rebased, and nothing was pushed.
- **The dirty root working tree is NOT part of any branch diff in this report.** The root checkout `D:\All projects\ArcheAxis-Knowledge-OS` was on `codex/aaos-p3-ui-convergence-20260922` at `a5de4b13` with 112 uncommitted paths belonging to unrelated root-side work. All facts below come from committed objects read inside the isolated worktree `.project-local/worktrees/dp-git-01-20260925`; uncommitted root content was never read as evidence and is deliberately excluded.
- Every SHA was read through its own diff and its parent context. Branch names, commit subjects and the pre-existing `docs/current/AAOS-BRANCH-*` inventories were treated as **hints only**; the decision for each SHA is derived from the blob-level comparison below.
- Decisions are audit judgements, **not** authorization to cherry-pick. `CHERRY_PICK_CANDIDATE` means "worth owner-reviewed port consideration", never "approved".

## 1. Method

1. Enumerated every non-merge commit reachable from the seven priority branches but not from `origin/main` (`git rev-list --reverse --no-merges <merge-base>..<branch>`).
2. For each commit and each changed file recorded: status, `--numstat` additions/deletions, the commit-side blob OID, the baseline-side blob OID (or absence), and whether the two are byte-identical.
3. For every changed path under `tests/`, `tests/**` or `integration-tests/`, classified the baseline state as `IDENTICAL_IN_BASELINE`, `EVOLVED_IN_BASELINE`, or `ABSENT_IN_BASELINE`.
4. Read the actual diff hunks for the product-bearing files, then checked the corresponding baseline implementation (`git show <baseline>:<path>`) to decide absorption.
5. Applied the September authority set: R6 TaskPack `AAK-LOCAL-GREEN-ABSORB-FIRST-20260919-R6` (`A01` release freeze, `A02` resource roots, `A05` formats, `A13` migration/Green), the M0 overlay `M0-SHORTEST-COMPLETE-LOOP` (`SUP-020`), `docs/truth/NAMING_CONTRACT_V2.md`, `AGENTS.md` §6, and the R6 version/release freeze contract.

Reproduce: `.project-local/dsh-audit/scripts/audit_collect.ps1` (facts) and `audit_evidence.ps1` / `audit_membership.ps1` (test-blob and membership classification), with `audit_verify.ps1` re-checking every claim in this report against Git. They are read-only collectors kept under the ignored `.project-local/` evidence root; the raw facts file is `.project-local/dsh-audit/branch-commit-facts.json` (untracked, ignored, evidence only).

## 2. Coverage

| Metric | Value |
| --- | --- |
| Branches in this batch | 7 |
| Distinct SHAs audited | **17** |
| Batch cap | 17 of max 20 |
| SHA range | `0a12fc11` (2026-07-28) … `376fb800` (2026-08-12) |
| Total changed-file records | 88 |
| Files absent from baseline | 28 |
| Files byte-identical to baseline | 5 |
| Files differing from baseline | 55 |
| Commits `SUPERSEDED` | 16 |
| Commits `CHERRY_PICK_CANDIDATE` | 0 |
| Commits `KEEP` | 0 |
| Commits `CONFLICT` | 1 (`4e1a3ed8`) |
| Commits `UNKNOWN` | 0 |
| Remaining unaudited SHAs in inventory | not counted here; see §6 |

Per-branch coverage: `feat/ms00-c-release-identity` 1/1, `feat/portable-data-root` 1/1, `feat/axw022a-pdf-http-endpoint` 4/4, `feat/axw022b-evidence-annotation` 2/2, `feat/h2-bakeoff` 3/3, `feat/naming-step3` 1/1, `feat/archeaxis-desktop-a1-violet-core` 5/5.

All seven priority branches resolved against the baseline; no ref failed to resolve, so no `UNKNOWN` was recorded for ref resolution.

## 3. Per-SHA records

### 3.1 `01e794d1` — feat(release): separate verification and release run identity

- Branch refs: `feat/ms00-c-release-identity` (tip, local + `origin/feat/...`). Merge base with `origin/main`: `9fefcfca`. Date 2026-08-07.
- Files: `.github/workflows/release.yml`, `app/release-manifest.json`, `app/release.py`, `scripts/release_inject_identity.py`, `tests/test_release_identity_contract.py`, `tests/test_release_manifest.py` (6 files, +122/−33).
- Purpose actually read from the diff: split the single `source.ci_run`/`ci_url` into `verification_ci_run(+_url)` and `release_run(+_url)`, pin `$verificationRun` from the newest successful exact-SHA CI run, and require the two run IDs to differ.
- Tests/evidence actually observed: none executed (audit is read-only). Both test files still exist in the baseline and are **evolved** (`EVOLVED_IN_BASELINE`); the baseline `tests/test_release_manifest.py` already exercises `verification_ci_run_id` / `release_run_id`, and the baseline `scripts/release_inject_identity.py` already accepts `--verification-ci-run-id`.
- September Authority alignment: consistent with, but a strict subset of, the later `R6-VERSION-RELEASE-FREEZE.md` model; adds no tag, release, version or publication and does not lift the R6 `A01` freeze.
- Donor decision: **SUPERSEDED**.
- Rationale: the baseline implements the same separation with stronger semantics — the baseline additionally requires `verification_ci_run_id != release_run_id`, uses `_require_repo_url` validation, and the baseline workflow derives `verification_run_url` canonically. Porting this diff would reintroduce an earlier, weaker shape of a model the baseline already owns.

### 3.2 `4e1a3ed8` — feat(desktop): add explicit portable data root

- Branch refs: `feat/portable-data-root` (tip). Merge base `141ff953`. Date 2026-08-05.
- Files: 18 files, +284/−65 — legacy `app/workspace/ui/assets/{app.js,styles.css}`, `app/workspace/ui/index.html`, `desktop/README.md`, `desktop/portable/launch_portable.{bat,ps1}`, `desktop/src-tauri/src/{lib.rs,runtime.rs}`, `run_all.{bat,sh}`, `run_windows.{bat,ps1}`, `scripts/a0_browser_smoke.py`, `scripts/project_env.{bat,ps1,sh}`, `scripts/runtime_http_smoke.py`, `tests/test_desktop_staging.py`.
- Purpose actually read from the diff: introduce `COGNITIVE_PORTABLE_ROOT`, add `resolve_runtime_with_portable_root` (absolute-path validation; portable root becomes both `cwd` and `data_dir`, `isolated=true`), and add a project-local environment boundary that redirects `TMP`/`TEMP`/`TMPDIR`, `UV_CACHE_DIR`, `PIP_CACHE_DIR`, `NPM_CONFIG_CACHE`, `CARGO_HOME`, `PLAYWRIGHT_BROWSERS_PATH` under `<repo>\.hermes\task-runtime`.
- Tests/evidence actually observed: none executed. `tests/test_desktop_staging.py` is **evolved** in the baseline; `desktop/portable/launch_portable.ps1` and `desktop/README.md` are **byte-identical** to the baseline (the portable launcher already shipped).
- September Authority alignment: **conflicts in two ways.** (a) It targets a `.hermes\task-runtime` runtime root and `COGNITIVE_*`/`COGNITIVE_PORTABLE_ROOT` identifiers, whereas R6/`AGENTS.md` §3 declares `.project-local/` (via `scripts/runtime/dev.py`) the project-owned runtime root and `.hermes/` preserved legacy material with "no new development writes". (b) It is naming-contract-stale: `NAMING_CONTRACT_V2` §2 makes `ARCHEAXIS_*` canonical with `COGNITIVE_*` retained only as a two-version fallback, and this commit hardens the legacy prefix. The portable-root *concept* is squarely inside the unresolved R6 `A02` resource/path authority decision, which is `BLOCKED_BY_OWNER_DECISION`; adopting an implementation now would prejudge that decision.
- Donor decision: **CONFLICT**.
- Rationale: the only genuinely portable artifact (the launcher) is already in the baseline; the rest encodes a runtime-root and env-prefix model that September authority has since replaced, and the remaining semantic question belongs to the owner-blocked `A02`. Treat as a conceptual input to `A02`, not as a port candidate. The absolute-path fail-closed requirement and the temporary/cache redirection *intent* are the parts worth re-expressing natively under `.project-local` if and when `A02` is decided.

### 3.3 `6e9dbfd3` — feat(workspace): serve content-addressed PDF bytes over HTTP (AXW-022A)

- Branch refs: `feat/axw022a-pdf-http-endpoint`. Merge base `fba208f2`. Date 2026-08-11.
- Files: `app/workspace/router.py`, `tests/test_workspace_pdf_endpoint.py` (2 files, +114/−1).
- Purpose actually read from the diff: add `@router.get("/api/pdf/{content_key}")` backed by `build_pdf_serving_root(resolve_runtime_path("data"))` and `resolve_pdf_bytes`, returning `application/pdf`, fail-closed on invalid keys.
- Tests/evidence actually observed: none executed. `tests/test_workspace_pdf_endpoint.py` exists in the baseline and is **evolved**; the baseline `app/workspace/router.py` already contains the `/api/pdf/{content_key}` route (importing `MAX_PDF_BYTES` from `app/evidence/pdf_serve`, with an explicit `sha256:` prefix check).
- September Authority alignment: no conflict. The baseline version is stricter (explicitly rejects non-`sha256:` keys before resolving and enforces `MAX_PDF_BYTES`).
- Donor decision: **SUPERSEDED**.
- Rationale: the feature is present in the baseline in a stronger form. Additionally the Rust canonical Core is the product authority; the legacy FastAPI router is a compatibility surface, so re-porting legacy serving code would add duplicated responsibility rather than capability.

### 3.4 `f8efcbd7` — feat(workspace): vendor PDF.js assets and wire serving (AXW-022A frontend step)

- Branch refs: `feat/axw022a-pdf-http-endpoint`. Date 2026-08-11.
- Files: `THIRD_PARTY_NOTICES.md`, `app/workspace/router.py`, `app/workspace/ui/assets/licenses/pdfjs-3.11.174-LICENSE.txt`, `app/workspace/ui/assets/pdf.min.js`, `app/workspace/ui/assets/pdf.worker.min.js`, `pyproject.toml` (6 files, +239/−2).
- Purpose actually read from the diff: vendor the real PDF.js 3.11.174 `pdf.min.js` / `pdf.worker.min.js` bundles (verified by content: genuine minified PDF.js) plus its license text, and register the third-party notice.
- Tests/evidence actually observed: none executed; no test file in this commit.
- September Authority alignment: no conflict, but obsolete. The entire `app/workspace/ui/**` tree (including the vendored assets) is **absent from the baseline**: `git ls-tree -r --name-only <baseline> -- app/workspace/ui` returns 0 entries.
- Donor decision: **SUPERSEDED**.
- Rationale: the consumer of these assets (the FastAPI-served web UI) no longer exists. Vendoring a browser PDF engine into an Avalonia product is not a transferable decision; if PDF rendering is ever needed it must be re-decided against the current shell and license register, not inherited from a deleted UI.

### 3.5 `226b5c68` — feat(workspace): PDF.js evidence viewer with paging/zoom/search (AXW-022A frontend)

- Branch refs: `feat/axw022a-pdf-http-endpoint`. Date 2026-08-11.
- Files: `app/workspace/ui/assets/app.js`, `app/workspace/ui/index.html` (2 files, +108/−0). Both **absent from the baseline**.
- Purpose actually read from the diff: add the paging/zoom/search viewer surface to the legacy web UI.
- Tests/evidence actually observed: none executed; no test file in this commit.
- September Authority alignment: no conflict, but obsolete and off-authority: `AGENTS.md` §6 states the formal desktop is the C#/Avalonia `apps/ArcheAxis.Desktop/`, with `frontend/` retained only as a recovery/behavior reference.
- Donor decision: **SUPERSEDED**.
- Rationale: UI for a removed shell. Any paging/zoom/search interaction belongs to the Avalonia product surface and its own Core contract, not to this commit.

### 3.6 `17ca9628` — fix(workspace): resolve PR #74 CI failures for PDF.js viewer

- Branch refs: `feat/axw022a-pdf-http-endpoint` (tip). Date 2026-08-11.
- Files: `app/workspace/ui/assets/app.js`, `app/workspace/ui/assets/pdf.min.js`, `app/workspace/ui/assets/pdf.worker.min.js`, `app/workspace/ui/index.html`, `tests/test_workspace_api.py` (5 files, +9/−7).
- Purpose actually read from the diff: small CI-adaptation edits to the vendored viewer assets and one test adjustment.
- Tests/evidence actually observed: none executed. `tests/test_workspace_api.py` is **evolved** in the baseline.
- September Authority alignment: no conflict, but obsolete (see 3.4/3.5).
- Donor decision: **SUPERSEDED**.
- Rationale: a CI workaround for a deleted UI plus a test edit already superseded in the baseline; nothing product-bearing remains.

### 3.7 `fee6fab0` — feat(workspace): content-addressed evidence anchor API (AXW-022B backend)

- Branch refs: `feat/axw022b-evidence-annotation`. Merge base `ebf71247`. Date 2026-08-11.
- Files: `app/workspace/router.py`, `tests/test_workspace_evidence_anchor_api.py` (2 files, +126/−0).
- Purpose actually read from the diff: add `POST /api/evidence/anchor` (`_do_create_anchor` → `build_evidence_anchor`/`store_evidence_anchor`) and `GET /api/evidence/anchor/{anchor_id}` (`resolve_evidence_anchor`, 404 when absent).
- Tests/evidence actually observed: none executed. **`tests/test_workspace_evidence_anchor_api.py` is byte-identical to the baseline** (commit blob `e456fbb0` == baseline blob `e456fbb0`), and the baseline router contains both the POST handler and `_do_create_anchor` verbatim.
- September Authority alignment: no conflict. Note that its Rust analogue exists: the baseline Core exposes `/api/v1/sources/:source_id/anchors` and `/api/v1/evidence/anchors`; the baseline `A12` remaining-gap text still records "Evidence bundles and citation insertion" as an open contract.
- Donor decision: **SUPERSEDED**.
- Rationale: this is the cleanest absorption evidence in the batch — the branch's own test file is *identical* to the baseline file, i.e. the work was taken as-is. Nothing to port.

### 3.8 `3edacbcb` — feat(workspace): PDF evidence annotation + jump-back UI (AXW-022B frontend)

- Branch refs: `feat/axw022b-evidence-annotation` (tip). Date 2026-08-11.
- Files: `app/workspace/ui/assets/app.js`, `app/workspace/ui/index.html` (2 files, +65/−1). Both **absent from the baseline**.
- Purpose actually read from the diff: call the new anchor API from the legacy web viewer and jump back to the pinned selection.
- Tests/evidence actually observed: none executed; no test file in this commit.
- September Authority alignment: no conflict, but obsolete (removed UI surface).
- Donor decision: **SUPERSEDED**.
- Rationale: the backend half of this feature pair is already in the baseline; the frontend half targets a deleted shell. The current baseline still records Evidence bundle/citation contracts as open work, which must be designed against the Avalonia shell and Rust Core.

### 3.9 `3884be73` — feat(h2): OCR bake-off framework + engine registry

- Branch refs: `feat/h2-bakeoff`. Merge base `f6b49b3e`. Date 2026-08-12.
- Files: `shared/bakeoff.py`, `shared/bakeoff_engines.py`, `tests/test_h2_bakeoff.py` (3 files, +356/−0).
- Purpose actually read from the diff: add a CER/WER bake-off harness comparing OCR/ASR engines against a fixed fixture corpus, with an engine registry.
- Tests/evidence actually observed: none executed. All three files exist in the baseline and are **evolved**: the baseline registry contains strictly more entries (`tesseract`, `tesseract-chi-sim`, `paddleocr`, `easyocr`, `rapidocr`, `faster-whisper`, `whisper.cpp`) versus this commit's four OCR engines, and the baseline `tests/test_h2_bakeoff.py` is 102 lines versus this commit's 66.
- September Authority alignment: no conflict; consistent with the M0 rule that accuracy requires human truth pairs and that engine confidence is not accuracy.
- Donor decision: **SUPERSEDED**.
- Rationale: the baseline is a strict superset of this commit. Porting would be a regression.

### 3.10 `fffff39a` — feat(h2): ASR engine stubs in bake-off registry

- Branch refs: `feat/h2-bakeoff`. Date 2026-08-12.
- Files: `shared/bakeoff_engines.py` (1 file, +35/−0).
- Purpose actually read from the diff: register `faster-whisper` / `whisper.cpp` unavailable-honest stubs.
- Tests/evidence actually observed: none executed; no test file in this commit. The baseline `shared/bakeoff_engines.py` already registers `faster-whisper` and `whisper.cpp` (see 3.9).
- September Authority alignment: no conflict; the "unavailable-honest" pattern matches the M0 requirement that unsupported capability be explicit.
- Donor decision: **SUPERSEDED**.
- Rationale: content already present in the baseline registry.

### 3.11 `376fb800` — feat(h2): Silero VAD audio voice activity detection stub

- Branch refs: `feat/h2-bakeoff` (tip). Date 2026-08-12.
- Files: `shared/audio_vad.py` (1 file, +71/−0).
- Purpose actually read from the diff: add `is_silero_available()` / `silero_vad_segments()` as an unavailable-honest Silero VAD integration stub.
- Tests/evidence actually observed: none executed; no test file in this commit. The baseline `shared/audio_vad.py` exists and is **evolved**: it declares the same `__all__`, adds `_read_audio(path, target_sr)` and an explicit unavailable branch.
- September Authority alignment: no conflict. Disclosed model identity/licence ("MIT license, ~26 MB") matches the M0/KANBAN requirement to state engine, version and licence facts.
- Donor decision: **SUPERSEDED**.
- Rationale: baseline supersedes the stub with a richer implementation.

### 3.12 `bc4a234f` — feat(naming): contract §4 step 3 — env vars, API root, Tauri identity, gate

- Branch refs: `feat/naming-step3` (tip, local + `origin/feat/naming-step3`). Merge base `66c6aac2`. Date 2026-08-12.
- Files: 14 files, +101/−62 — `.github/workflows/ci.yml`, `app/cli.py`, `app/main.py`, `app/runtime_entrypoint.py`, `app/workspace/router.py`, `desktop/src-tauri/src/protocol.rs`, `desktop/src-tauri/tauri.conf.json`, `docs/truth/SUPPLY_CHAIN_LEDGER.json`, `scripts/a0_browser_smoke.py`, `scripts/check_repository_conventions.py`, `scripts/generate_phase0_baseline.py`, `shared/config.py`, `tests/test_gateway_rate_limit.py`, `tests/test_phase0_baseline.py`.
- Purpose actually read from the diff: flip `COGNITIVE_*` → `ARCHEAXIS_*` with legacy fallbacks, add the `/api/v1` canonical API root alongside the legacy `/api/*` routes, and rebrand the (legacy) Tauri identity to `com.archeaxis.workspace` / "ArcheAxis Learning Workspace".
- Tests/evidence actually observed: none executed. `tests/test_gateway_rate_limit.py` is **byte-identical** to the baseline (`eccd5dc1` == `eccd5dc1`); `tests/test_phase0_baseline.py` is **evolved**. The baseline `shared/config.py` already contains the entire `ARCHEAXIS_*`-primary / `COGNITIVE_*`-fallback map written by this commit (docstring included), the baseline `app/main.py` already mounts `workspace_router` twice including `prefix="/api/v1"` with the comment "Naming contract §4: canonical API root is /api/v1/", and the baseline `app/workspace/router.py` already reads `ARCHEAXIS_DESKTOP_LAUNCH_TOKEN` with a `COGNITIVE_*` fallback.
- September Authority alignment: aligned and already satisfied. `NAMING_CONTRACT_V2` §2 records env prefix `ARCHEAXIS_*` as "已迁移（#136），COGNITIVE_* 保留回退" and API root `/api/v1/` as dual-path. The one part that did **not** persist is the Tauri identity: the baseline `desktop/src-tauri/tauri.conf.json` now reads `"productName": "ArcheAxis Knowledge Recovery"`, `"identifier": "com.archeaxis.workspace.recovery"`, i.e. the legacy shell was demoted to an explicitly labelled recovery surface after this commit.
- Donor decision: **SUPERSEDED**.
- Rationale: the substantive naming migration is already in the baseline verbatim, and the only differing element (Tauri identity) has since been deliberately changed to a recovery-labelled identity. Re-applying this commit would regress that decision.

### 3.13 `0a12fc11` — fix(ci): install playwright for test collection

- Branch refs: `feat/archeaxis-desktop-a1-violet-core`. Merge base `a92e6730`. Date 2026-07-28.
- Files: `requirements-ci.txt` (1 file, +1/−0). **Absent from the baseline.**
- Purpose actually read from the diff: add `playwright` to the CI dependency list so browser-smoke test collection succeeds.
- Tests/evidence actually observed: none executed; no test file.
- September Authority alignment: no conflict, but obsolete. The baseline `.github/workflows/ci.yml` no longer consumes `requirements-ci*.txt` at all; it installs from hash-locked files (`locked-ci.txt`, `locked-ci-adapters.txt`, `locked-browser.txt`) and `uv run --frozen --group ci`.
- Donor decision: **SUPERSEDED**.
- Rationale: the dependency-installation mechanism was replaced wholesale by the locked/uv-group model, which already covers browser dependencies via `locked-browser.txt`.

### 3.14 `d5418d69` — feat(workspace): add Violet Core desktop shell

- Branch refs: `feat/archeaxis-desktop-a1-violet-core`. Date 2026-07-28.
- Files: 6 files, +68/−13 — `README.md`, `app/workspace/ui/assets/app.js`, `app/workspace/ui/assets/styles.css`, `app/workspace/ui/index.html`, `docs/PROJECT_STATUS.md`, `scripts/a0_browser_smoke.py`.
- Purpose actually read from the diff: add the "Violet Core" dark-theme shell to the legacy web UI and adjust browser-smoke coverage.
- Tests/evidence actually observed: none executed; no test file in this commit. The three `app/workspace/ui/**` files are **absent from the baseline**.
- September Authority alignment: no conflict, but obsolete on two counts: the target UI tree is gone, and the baseline `scripts/a0_browser_smoke.py` now documents itself as "Real-browser smoke for the legacy React/Tauri **compatibility** shell … must not be presented as the production desktop gate" with `ARCHEAXIS_RUN_ROOT`-scoped outputs.
- Donor decision: **SUPERSEDED**.
- Rationale: shell design for a removed surface; the surviving browser probe was explicitly demoted to a compatibility reference.

### 3.15 `53573e91` — fix(ci): cover adapter dependencies and ffmpeg

- Branch refs: `feat/archeaxis-desktop-a1-violet-core`. Date 2026-07-28.
- Files: `.github/workflows/ci.yml`, `requirements-ci.txt`, `tests/test_release_manifest.py` (3 files, +14/−3).
- Purpose actually read from the diff: add adapter/ffmpeg dependencies to the CI test job.
- Tests/evidence actually observed: none executed. `tests/test_release_manifest.py` is **evolved** in the baseline.
- September Authority alignment: no conflict, but obsolete (see 3.13).
- Donor decision: **SUPERSEDED**.
- Rationale: the baseline installs adapter dependencies through `locked-ci-adapters.txt` with `--require-hashes` plus the `ci-adapters` uv group, which is the stricter successor of this change.

### 3.16 `f1702990` — fix(ci): isolate adapter test dependencies and align rules

- Branch refs: `feat/archeaxis-desktop-a1-violet-core`. Date 2026-07-28.
- Files: `.github/workflows/ci.yml`, `AGENTS.md`, `docs/VERIFICATION_POLICY.md`, `requirements-ci-adapters.txt` (new), `requirements-ci.txt` (−8) (5 files, +24/−25).
- Purpose actually read from the diff: split adapter test dependencies into their own requirements file and rewrite `AGENTS.md` sections 3/4 to defer general execution rules to global Hermes workflow rules ("follow the stricter rule").
- Tests/evidence actually observed: none executed; no test file.
- September Authority alignment: **the `AGENTS.md` half is now actively wrong.** This diff removes `Avoid git add .`, `Do not commit or push unrelated local changes`, `Do not force push`, and the destructive-action rule from the project file, and it targets the retired names "Cognitive-OS"/"Cognitive-Loop-OS". The current baseline `AGENTS.md` §4 explicitly re-states "Use explicit paths when staging; avoid `git add .`", "Do not commit or push unrelated local changes; do not force push" — the stricter posture R6/this very DP assignment depends on. The `requirements-ci-adapters.txt` file is **absent from the baseline**, replaced by `locked-ci-adapters.txt` + the `ci-adapters` uv group.
- Donor decision: **SUPERSEDED**.
- Rationale: both halves were reversed or replaced by later authority. Re-applying this commit would weaken the current Git safety wording — a direct conflict with the DP shared rules.

### 3.17 `376281c6` — feat(workspace): align ArcheAxis positioning and desktop shell

- Branch refs: `feat/archeaxis-desktop-a1-violet-core` (tip). Date 2026-07-28.
- Files: 11 files, +232/−22 — `README.md`, `app/release-manifest.json`, `app/workspace/ui/assets/app.js`, `app/workspace/ui/assets/styles.css`, `app/workspace/ui/index.html`, `docs/PRODUCT_POSITIONING.md`, `docs/PROJECT_STATUS.md`, `docs/README.md`, `pyproject.toml`, `scripts/a0_browser_smoke.py`, `workspace/intake/2026-07-28-archeaxis-pack-analysis.md`.
- Purpose actually read from the diff: rebrand to "ArcheAxis OS（元枢系统）", retitle the README, change the Python distribution/keywords to `cognitive-loop-os` / tauri, and add `docs/PRODUCT_POSITIONING.md` plus an intake record.
- Tests/evidence actually observed: none executed; no test file. `docs/PRODUCT_POSITIONING.md` **exists in the baseline but is evolved**; `workspace/intake/2026-07-28-archeaxis-pack-analysis.md` is **absent from the baseline** (the path-level absence is expected: that intake predates the repository normalization recorded in the baseline's naming authority).
- September Authority alignment: **conflicts with the current naming authority.** This commit's "ArcheAxis OS" / "元枢" branding is listed in `NAMING_CONTRACT_V2` §5 as a historical/retired name ("ArcheAxis OS 旧产品名（曾用于 GitHub 描述/安装器）", allowed only in historical records and rejection test cases). The baseline already carries the V2 names (`pyproject.toml` name `archeaxis-workspace`, version `0.6.14`; README "ArcheAxis Knowledge"), and the baseline `docs/PRODUCT_POSITIONING.md` is the evolved version.
- Donor decision: **SUPERSEDED**.
- Rationale: brand direction and release-manifest edits are superseded by the binding V2 naming contract and by the R6 `A01` release freeze. The only element with residual record value (the 2026-07-28 intake analysis) is historical documentation whose absence is explained by repository normalization; it is not a product change and should not be resurrected by cherry-pick.

## 4. Batch summary table

| # | SHA | Branch | Date | Files | Decision | One-line rationale |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `01e794d1` | feat/ms00-c-release-identity | 2026-08-07 | 6 | SUPERSEDED | Baseline already separates verification/release run identity more strictly |
| 2 | `4e1a3ed8` | feat/portable-data-root | 2026-08-05 | 18 | CONFLICT | `.hermes\` runtime root + `COGNITIVE_*` prefix contradict `.project-local`/`ARCHEAXIS_*` authority; portable launcher already in baseline; remainder is the owner-blocked A02 decision |
| 3 | `6e9dbfd3` | feat/axw022a | 2026-08-11 | 2 | SUPERSEDED | `/api/pdf/{content_key}` already in baseline (stricter) |
| 4 | `f8efcbd7` | feat/axw022a | 2026-08-11 | 6 | SUPERSEDED | `app/workspace/ui/**` absent from baseline; web UI removed |
| 5 | `226b5c68` | feat/axw022a | 2026-08-11 | 2 | SUPERSEDED | Viewer UI for a removed shell |
| 6 | `17ca9628` | feat/axw022a | 2026-08-11 | 5 | SUPERSEDED | CI workaround for a deleted UI |
| 7 | `fee6fab0` | feat/axw022b | 2026-08-11 | 2 | SUPERSEDED | Test file byte-identical in baseline; routes present verbatim |
| 8 | `3edacbcb` | feat/axw022b | 2026-08-11 | 2 | SUPERSEDED | Annotation UI for a removed shell |
| 9 | `3884be73` | feat/h2-bakeoff | 2026-08-12 | 3 | SUPERSEDED | Baseline registry/tests are a strict superset |
| 10 | `fffff39a` | feat/h2-bakeoff | 2026-08-12 | 1 | SUPERSEDED | ASR stubs already registered in baseline |
| 11 | `376fb800` | feat/h2-bakeoff | 2026-08-12 | 1 | SUPERSEDED | Baseline `audio_vad.py` evolved past this stub |
| 12 | `bc4a234f` | feat/naming-step3 | 2026-08-12 | 14 | SUPERSEDED | Env/API-root migration already in baseline; Tauri identity deliberately changed to recovery |
| 13 | `0a12fc11` | feat/…-violet-core | 2026-07-28 | 1 | SUPERSEDED | `requirements-ci.txt` replaced by locked/uv-group CI |
| 14 | `d5418d69` | feat/…-violet-core | 2026-07-28 | 6 | SUPERSEDED | Violet Core shell targets a removed UI tree |
| 15 | `53573e91` | feat/…-violet-core | 2026-07-28 | 3 | SUPERSEDED | Adapter deps now hash-locked via `locked-ci-adapters.txt` |
| 16 | `f1702990` | feat/…-violet-core | 2026-07-28 | 5 | SUPERSEDED | CI split replaced; `AGENTS.md` rewrite reversed by current authority |
| 17 | `376281c6` | feat/…-violet-core | 2026-07-28 | 11 | SUPERSEDED | "ArcheAxis OS / 元枢" branding retired by NAMING_CONTRACT_V2 §5 |

## 5. September Authority alignment and integration risks

**Alignment findings**

1. All 17 SHAs are 2026-07-28 … 2026-08-12. None carries R6/M0 evidence labels, subject SHAs, owner gates or `LOCAL_GREEN` claims, so none can be promoted on its own receipts. Every decision above is therefore based on content absorption, not on claimed status.
2. Two authority domains account for all the staleness: (a) the removal of the legacy FastAPI-served web UI (`app/workspace/ui/**`) in favour of the C#/Avalonia shell, and (b) the `COGNITIVE_*`/`.hermes` → `ARCHEAXIS_*`/`.project-local` migration recorded in `NAMING_CONTRACT_V2` §2 and `AGENTS.md` §3.
3. No SHA in this batch produces a `CHERRY_PICK_CANDIDATE`. This is the notable result of the batch: the priority branches named in the assignment are *historical absorption donors whose content is already resident in the baseline in equal or stronger form*.

**Integration risks recorded (not acted on)**

- `R-01` (from `4e1a3ed8`): the portable/explicit-data-root semantics are still an open, owner-blocked R6 `A02` decision. Any future port must be re-derived under `.project-local`/`ARCHEAXIS_*`, must keep fail-closed absolute-path validation, and must not write new state under `.hermes/`.
- `R-02` (from `f1702990`): an `AGENTS.md` hunk exists in branch history that removes the explicit "avoid `git add .`", "no unrelated commits/push", "no force push" rules. Any future cherry-pick sweep that touches `AGENTS.md` must not resurrect that hunk; the current `AGENTS.md` §4 wording is the binding one.
- `R-03` (from `4e1a3ed8`, `f8efcbd7`, `226b5c68`, `17ca9628`, `3edacbcb`, `d5418d69`, `376281c6`): seven SHAs in this batch touch 16 distinct `app/workspace/ui/**` file records, a tree that no longer exists in the baseline. A branch-disposition pass that keys off path existence will report these as "missing work"; they are not. Any automated donor scan must first filter on whether the target path still exists in the baseline, otherwise it will manufacture false regression candidates.
- `R-04` (from `376281c6`): historical branding ("ArcheAxis OS", "元枢") is present in branch content and would fail the naming gate. Prefer leaving such commits preserved-and-unported over any textual reuse.
- `R-05`: `docs/current/R6-STATE.json` still records the baseline as its `subject_sha`, and the batch introduces no state change; nothing in this report may be read as an R6/M0 status promotion.

## 6. Limits, verification and non-exhaustiveness

- **Not exhaustive.** This is batch 1 of at most 20 SHAs. The broader inventory (`docs/current/AAOS-BRANCH-COMMIT-PATH-AUDIT-20260925.json`) contains additional branches and SHA records — for example `codex/aaos-p3-ui-convergence-20260922` alone lists 166 commit records — which are **not** covered here. No conclusion in this report may be generalized to them.
- **No test was executed for any SHA.** Every `tests/evidence` field above records *file and blob state in the baseline*, not a passing run. All test evidence in this report is `NOT_EXECUTED` / structural; the audit intentionally did not run pytest, cargo or dotnet against donor commits in unrelated worktrees.
- **Absence evidence is path-level.** A path reported "absent from baseline" was checked with `git cat-file -e <baseline>:<path>` and its exit status; a path reported "identical" was compared by exact blob OID; the 55 "evolved" records differ by blob OID but were not all semantically diffed hunk-by-hunk — the product-bearing ones were read in full.
- **Self-correction during this batch.** The first collected facts file computed baseline membership with `git rev-parse <tree>:<path>`, which on failure still echoes its argument on stdout in this environment; a checker that tested output-non-empty therefore misclassified absent paths. The independent claim verifier (`audit_verify.ps1`) caught this, and membership was recomputed with `git cat-file -e` exit status (`audit_membership.ps1`). All counts in this report use the corrected result: 28 absent / 5 identical / 55 evolved of 88 records.
- **Remote state not verified.** Decisions use local refs and the tracked `AAOS-BRANCH-*` inventories. No `git fetch` was performed and no live GitHub PR/branch state was re-verified in this batch; branch tips are recorded as resolved from the local object store.
- **No authorization implied.** Per the task card, this is an audit. `SUPERSEDED` does not authorize deletion of any branch, and `CONFLICT` does not authorize modification of any file. Branch deletion, cherry-pick, merge or cleanup remain separate owner decisions.
- Report artifacts: `docs/current/dsh-review/branch-batch-01.md` and `docs/current/dsh-review/branch-batch-01.json`, committed only on `codex/dp-git-01-20260925`. No other path was written.
