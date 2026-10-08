# AAOS spillover register — 外溢数据登记表 (2026-10-08)
> **本文的反引号路径不是仓内引用。** 登记对象绝大多数位于任何检出之外（兄弟项目、驱动器根、
> 临时目录、别的账户属主的树），反引号在这里的语义是"字节在哪"，不是"这条引用能在本检出解析"。
> 因此不对本文运行 `scripts/audit/reference_validation.py`：实测把共享产物根声明为根之后，
> 该校验器为了解析一个名字要遍历 48 GB 树，超过 15 分钟不返回——这是工具自身的边界，
> 不是这份记录可以宣称已通过的东西。机器可读的逐条数据在
> `docs/current/AAOS-SPILLOVER-REGISTER-20261008.json`，字段级校验由生成它的脚本负责。
> 与之对照：`docs/current/AAOS-GOVERNANCE-UI-HANDOFF-20261008.md` 的 55 条反引号引用
> 全部在本检出内解析通过，那才是引用完整性校验适用的地方。

Status: **register plus migration plan only.** Nothing in this pass was committed, pushed, moved, renamed or deleted.
Every byte count below was read on 2026-10-08 by
`.project-local/task-runtime/spillover-register-20261008/build_register.py`, which writes the machine twin
`AAOS-SPILLOVER-REGISTER-20261008.json` and the tables of this document from one measurement pass
(`generated_at 2026-10-08T20:12:07+0800`, 96 rows). E:\ and F:\ were not touched.

## 1. The question this answers

The owner asked whether **外溢数据** — data that belongs to this project but lives outside the two repositories — is
being tracked. Before this register it was not: the facts existed as dated prose
(`docs/current/AAOS-SPILLOVER-MIGRATION-20260928.md`, `.project-local/spillover-addendum-20261007.md`,
`.project-local/task-runtime/spillover-readback-20261007.md`) and as one unactioned count — `main_layout_audit.py`
recorded **174 out-of-layout entries** in the main checkout on 2026-10-08 17:06
(`.project-local/task-runtime/worktree-disposition-20261008/layout-contract-main-checkout.json`) and nothing was done
with it. This register turns that into one row per candidate, each with an ownership proof and a disposition, so the
owner can rule per item instead of per paragraph.

**Non-duplication contract.** This file owns exactly one thing: the row-per-candidate list and its dispositions. It
does not restate migration history — `AAOS-SPILLOVER-MIGRATION-20260928.md` stays authoritative for what moved and
when, and its Formal copy stays authoritative over the older Green copy (2026-10-07 readback) — and it does not restate
that readback's verdicts, it carries them forward as rows and cites them. Row-level machine data lives in the JSON
twin, not in a second prose document.

## 2. Measurement rules and their limits

- **Owned bytes, not reachable bytes.** Same rule as `scripts/runtime/storage_report.py::directory_size`: symlinks and
  Windows junctions are counted as links and skipped, never summed, so one shared install is not reported as its own
  by every directory that points at it.
- **Two sanctioned lists, and they disagree.** `storage_report.py` accepts
  `build, runs, task-runtime, candidates, recovery, mig, cache, a3-python-input, worktrees, legacy-scratch, tmp` plus
  the pattern `^(a\d+(-.*)?|rt(-.*)?|legacy-scratch.*)$`. `DIRECTORY_AUTHORITY.yaml` `ignored_local_roots` accepts
  `worktrees, agents, leases, runs, cache, build, tmp, logs, artifacts, recovery, mig`. The intersection — the only
  destinations neither contract can flag — is **`build, runs, cache, tmp, worktrees, recovery, mig`**. `artifacts/` and
  `logs/` are flagged by the report; `task-runtime/`, `candidates/` and `a3-python-input/` are unnamed by the authority.
- **The authority is branch-dependent.** The main checkout's `DIRECTORY_AUTHORITY.yaml` does not yet list `recovery/`
  or `mig/` and has no `ownership_classes` block; this worktree's copy (branch `codex/aaos-gov-ui-20261008`) does.
  Destinations below are checked against this worktree's copy, because that is the contract this register lands under.
- **Fresh count vs the recorded count, reconciled exactly.** This pass counts
  38 non-sanctioned directories + 130 loose files in `.project-local`
  + 4 at the repository root = **172 entries** under
  the union of both lists. Counted by `storage_report.py`'s list alone the same tree gives
  **173**, and the 17:06 run recorded
  **174**. The difference is named, not guessed:
  `.project-local: artifacts/`, `.project-local: wi/` — `wi/` because it was removed earlier today, and
  `artifacts/` because `DIRECTORY_AUTHORITY.yaml` sanctions it while `storage_report.py` still flags it. The second is
  the subject of §7.1, not a measurement error. The register keeps 51 *rows* because the
  130 loose files are rolled into 8 decision-sized families; per-file detail is in the
  JSON twin.
- **Secrets were not read.** Candidates whose names indicate credentials, tokens, cookies, `.env` or browser-profile
  internals are recorded as path + size + class only, in §4.J. Their contents were not opened, printed or copied.
- **Under-measurement.** 96 entries returned Access Denied to
  this identity and their bytes are **not** in any total (largest: the Green `mainline` clone and the Green application
  root, 43 and 46 unreadable entries each). `.project-local/tools/uv-0.12.18/` is likewise unreadable here, so that row
  understates.
- **Negative findings are name-scoped.** `Model library` was searched by name for `archeaxis|aaos|星环` to depth 3 and
  returned nothing; `Downloads` was checked by name only, contents unread. A name search cannot prove absence of
  content-level spillover — a hash sweep could, and was not run here.
- **Concurrent writers.** The tree changed while this register was being built: `.project-local/worktrees/` went from
  the 25 directories recorded at 17:01 to 9 registered worktrees plus 3 husks at 19:22, and Playwright directories in
  `%TEMP%` were still being written at 19:58. Rows are a snapshot, not a live view.

## 3. Totals by disposition, separated by who owns the bytes

Collapsing these into one number would overstate the project's spillover: the declared shared roots and the sibling
repositories are not this project's bytes to move.

**inside this repository's trees (project-owned)**

| Disposition | Rows | Owned bytes | Files |
|---|---:|---:|---:|
| keep-in-place | 24 | 3,479,121,674 | 37,470 |
| unresolved | 6 | 160,413,242 | 2,288 |
| migrate-to-declared-dir | 21 | 14,342,557 | 640 |
| archive-then-remove | 10 | 6,326,826 | 27 |
| foreign-do-not-touch | 1 | 876 | 1 |

**registered worktree outside the sanctioned path (project-owned)**

| Disposition | Rows | Owned bytes | Files |
|---|---:|---:|---:|
| migrate-to-declared-dir | 1 | 696,558,986 | 3,334 |

**sibling projects and drive roots (mixed ownership)**

| Disposition | Rows | Owned bytes | Files |
|---|---:|---:|---:|
| keep-in-place | 2 | 24,540,118,143 | 119,191 |
| foreign-do-not-touch | 6 | 6,826,143,255 | 67,023 |
| unresolved | 2 | 4,544,652 | 13 |
| migrate-to-declared-dir | 2 | 733,497 | 12 |

**declared shared resource roots (legitimately shared, not spillover)**

| Disposition | Rows | Owned bytes | Files |
|---|---:|---:|---:|
| keep-in-place | 10 | 7,158,818,654 | 43,758 |
| foreign-do-not-touch | 1 | 0 | 0 |

**OS temp roots (OS-owned location)**

| Disposition | Rows | Owned bytes | Files |
|---|---:|---:|---:|
| keep-in-place | 8 | 453,832 | 75 |
| foreign-do-not-touch | 1 | 0 | 4,910 |

**other (user directories, existence-only)**

| Disposition | Rows | Owned bytes | Files |
|---|---:|---:|---:|
| foreign-do-not-touch | 1 | 0 | 14 |

**Whole-register totals**

| Disposition | Rows | Owned bytes | Files |
|---|---:|---:|---:|
| keep-in-place | 44 | 35,178,512,303 | 200,494 |
| foreign-do-not-touch | 10 | 6,826,144,131 | 71,948 |
| migrate-to-declared-dir | 24 | 711,635,040 | 3,986 |
| unresolved | 8 | 164,957,894 | 2,301 |
| archive-then-remove | 10 | 6,326,826 | 27 |

## 4. Register rows

### 4.A1 `.project-local` non-sanctioned directories, main checkout

The dev root is `deny-commit` wholesale, so none of this can leak into Git; the issue is that nothing outside these
files knows where the bytes are.

| Path | Owned bytes | Files | Last write | What it appears to be | Ownership evidence | Referenced by | Disposition |
|---|---:|---:|---|---|---|---|---|
| `.project-local/artifacts/` | 2,607,542,960 | 32872 | 2026-10-08 10:49 | OSS donor/source snapshots absorbed by the reuse line (e.g. `oss-reuse-20261008/source/...`) | the two layout lists disagree about this name | 6 tracked docs (`git grep project-local/artifacts`) | keep-in-place |
| `.project-local/g/` | 313,242,756 | 1 | 2026-09-23 23:03 | single Green release ZIP `ArcheAxis.Knowledge.Green-vui3-x64.zip` | name and bytes match a documented recovery basis; ZIP SHA-256 recomputed `f8d0eb0a774f58133d7271902d38f5a45578842c0cd1fbb5d092e84350234a71`; 3 readback/prune receipts sit under `mig/storage-cleanup-current-20260930/` naming it | `docs/current/STORAGE-CLEANUP-CHECKPOINT-20261001.md:114`, `docs/current/STORAGE-CLEANUP-HANDOFF-20261001.md:204` ('vui3 ZIP 仍是恢复依据，保留') | keep-in-place |
| `.project-local/inputs/` | 249,349,798 | 326 | 2026-10-07 19:46 | UI taskpack working inputs: `AAOS/` design-suite extraction, `AAOS_UI_Taskpack_20261007/`, `diarization-candidates-20261007/` | content is the unpacked UI suite and ASR candidates for the active UI pack | `docs/authority/taskpack-1007-aaos-ui/README.md`, `AAOS-UI-FIDELITY-STATUS-20260927.md`, `AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md`, `REPOSITORY-CLEANUP-HANDOFF-20260921.md` | keep-in-place |
| `.project-local/dep-src-clean/` | 113,875,324 | 2211 | 2026-10-01 14:49 | unpacked third-party dependency sources (PIL, XlsxWriter, et_xmlfile, 19 dist dirs) from a licence/reuse review | content names Python packages only | 0 tracked citations | unresolved |
| `.project-local/deeptutor-val/` | 82,610,112 | 3174 | 2026-09-11 00:41 | donor validation tree for the DeepTutor reuse probe (book export, chat answers, cache) | content names the donor and the probe | 10 tracked docs incl. `docs/authority/taskpack-0907/EXECUTION.md`, `taskpack-0908-r3/EXECUTION.md`, `taskpack-0910-r3/R01-CAPACITY-BASELINE.md` | keep-in-place |
| `.project-local/staging/` | 77,913,285 | 6 | 2026-09-23 20:27 | candidate staging for Green builds (`aaos-current-candidate-final-20260926`, `p3-87cdf2cf`, `p3-a64788c4`) | directory names are source-SHA candidates that match `SHARED_RESOURCE_PATH_INDEX.md` candidate identities | `AAOS-SPILLOVER-MIGRATION-20260928.md`, `R6-EXECUTION.md`, `AAOS-UI-SUITE-COVERAGE-20260923.md`, `UI_IMPLEMENTATION_REPORT.md`, `docs/history/storage-cleanup/2026-09-30/continuation-audit-blockers-20260930.md` | keep-in-place |
| `.project-local/m0loop/` | 63,425,259 | 207 | 2026-09-27 00:04 | M0 shortest-loop run trees keyed by 8-hex source digests (10 of them) | directory keys are git tree/commit digests of this repository | `DSH-BACKEND-CONTRACT-20260927.md`, `DSH-BACKEND-EVIDENCE-20260927.json`, `AAOS-PRODUCTION-HTTP-CONTRACT-20261001.md` (6 files) | keep-in-place |
| `.project-local/acceptance/` | 32,643,550 | 400 | 2026-10-01 10:45 | human/UI acceptance batches (13 entries) + `README-验收说明.txt`; two of the batches contain Chromium/Edge temporary profiles | content carries acceptance records for AAOS-B10 / UI-CANDIDATE / UI-VERIFY | `AAOS-UI-FIDELITY-STATUS-20260927.md`, `AAOS_VISUAL_QA.md`, `UI_IMPLEMENTATION_REPORT.md`, `docs/history/ui-asset-audit-20261001/*` | keep-in-place |
| `.project-local/c/` | 12,492,793 | 476 | 2026-09-27 16:51 | 3 Chromium/Edge temporary profiles `p-2flbfuyn`, `p-v6ql20b5`, `p-vavp0djd` (Local State, GPUPersistentCache, ShaderCache, MEIPreload) | profile shape and `p-<8 chars>` naming match the root stray `p-w7n3ehdf/`; no tracked command creates this path | 0 tracked citations | migrate-to-declared-dir |
| `.project-local/dist/` | 11,025,490 | 5 | 2026-09-15 23:00 | `archeaxis-core-42ea8237c929-debug-build` + its ZIP + its `.sha256` | the `.sha256` sibling names the archive; the SHA is reproducible from the file | `scripts/release/build_candidate.py` writes this shape; cited by `R5-EXECUTION.md`, `R5-CONTINUATION-EXECUTION-20260915.md`, `PROJECT-LOCAL-VOLUME-AUDIT-20260923.md` | keep-in-place |
| `.project-local/ui-audit/` | 7,980,089 | 42 | 2026-09-28 23:53 | B10 UI audit references (design-token PNGs, `ArcheAxis_design_tokens.json`), a pytest cache and `test_b10_shell_fidelity_contract.py` | content is the audit corpus | `docs/current/PROJECT-LOCAL-VOLUME-AUDIT-20260923.md` | keep-in-place |
| `.project-local/ci-replay/` | 4,983,174 | 16 | 2026-09-27 13:42 | one replayed CI runtime tree `fresh-runtime/` | names CI, no run id recorded | 0 tracked citations | unresolved |
| `.project-local/gh-cache/` | 2,289,377 | 5 | 2026-09-18 21:49 | GitHub CLI cache (`GitHub CLI/`) for the delivery session | gh writes this only when GH_CONFIG_DIR/APPDATA is redirected here | 2 tracked docs (delivery notes) | keep-in-place |
| `.project-local/audits/` | 1,786,256 | 13 | 2026-09-28 22:33 | dated audit records (`a15-20260920`, independent FFD8FF audit, cleanup + inventory receipts) | receipts name this repository's paths | `PROJECT-LOCAL-VOLUME-AUDIT-20260923.md`, `R6-EXECUTION.md`, `REPOSITORY-CLEANUP-HANDOFF-20260921.md` | keep-in-place |
| `.project-local/dsh-audit/` | 464,279 | 17 | 2026-09-25 20:17 | small audit working directory | as above | 0 tracked citations | migrate-to-declared-dir |
| `.project-local/tmpuf_amolv/` | 319,488 | 1 | 2026-09-18 03:38 | a single SQLite database left by a pytest tmpdir run | file is a workspace DB shape | `docs/current/AAOS-LOCAL-REPOSITORY-LINEAGE-READBACK-20260925.md` | keep-in-place |
| `.project-local/inspect/` | 292,012 | 15 | 2026-09-07 07:46 | reuse-first inspection output for 2026-09-07 (`archeaxis-reuse-first-20260907/`) | directory name matches taskpack-0907 | 0 tracked citations for this path | migrate-to-declared-dir |
| `.project-local/dsh-recon-20261001-bytes/` | 283,368 | 12 | 2026-10-01 16:37 | byte-level readback of the same reconnaissance | as above | 0 tracked citations | migrate-to-declared-dir |
| `.project-local/dsh-recon-20261001/` | 265,695 | 8 | 2026-10-01 16:37 | DSH takeover reconnaissance output | content names the DSH takeover task | 0 tracked citations | migrate-to-declared-dir |
| `.project-local/state/` | 226,416 | 4 | 2026-09-25 02:00 | one state directory keyed by source digest `be268a2d33/` | key is a git object of this repo | 6 tracked docs incl. `R5-EXECUTION.md`, `R5-DESKTOP-START.md`, `AAOS-UI-SUITE-COVERAGE-20260923.md` | keep-in-place |
| `.project-local/tooling/` | 44,639 | 41 | 2026-09-29 07:52 | ad-hoc runner scripts (`run_desktop_direct.py`, `run_cargo_test.py`, `run_dotnet.py`) plus nested `appdata/`, `localappdata/`, `dotnet-cli-home/` redirect husks | the scripts are the generating commands for the desktop/cargo runs | 1 tracked doc | keep-in-place |
| `.project-local/dotnet-home/` | 16,777 | 21 | 2026-09-29 06:43 | DOTNET_CLI_HOME redirect husk (`.dotnet/`) | dev.py routes DOTNET_CLI_HOME to `runs/<id>/dotnet`, never here | 0 tracked citations | migrate-to-declared-dir |
| `.project-local/npm-cache/` | 15,384 | 8 | 2026-10-05 06:03 | npm cache redirect (`_logs/`, `_update-notifier-last-checked`) | dev.py routes npm_config_cache to `.project-local/cache/npm` | 0 tracked citations | migrate-to-declared-dir |
| `.project-local/probe2/` | 8,192 | 1 | 2026-09-18 21:04 | probe scratch tree (`q-_c9efuv7/`, `sub/`) - pytest tmpdir shapes | pytest tmp naming | 0 tracked citations | migrate-to-declared-dir |
| `.project-local/probes/` | 5,769 | 3 | 2026-09-07 22:54 | probe inputs and two probe scripts (`x01_real_screenshot_ocr.py`, `x07_public_check_probe.py`) | script bodies name this project's probe strings | 1 tracked doc | migrate-to-declared-dir |
| `.project-local/p/` | 3,095 | 1 | 2026-09-18 21:51 | one `probe.bat` cargo-test probe | sibling of root `p-w7n3ehdf` profile family | 0 tracked citations | migrate-to-declared-dir |
| `.project-local/tmp-measure/` | 2,002 | 1 | 2026-10-08 11:31 | one junction-measurement script (`junction_check.py`) | script is a size probe | 0 tracked citations | migrate-to-declared-dir |
| `.project-local/uv-cache-agent-icon/` | 1,708 | 7 | 2026-09-29 00:32 | second uv cache redirect (`interpreter-v4/`) | as above | 0 tracked citations | migrate-to-declared-dir |
| `.project-local/localappdata/` | 928 | 4 | 2026-09-29 06:43 | `localappdata/AvaloniaUI/BuildServices/` - 3 Avalonia build-service markers + `id` | same out-of-band LOCALAPPDATA redirect; the markers are Avalonia's own build tokens | 0 tracked citations | migrate-to-declared-dir |
| `.project-local/tools/` | 470 | 1 | 2026-10-07 01:48 | `aaos_ui_run_npm.py` ad-hoc npm runner + an unpacked `uv-0.12.18/` | npm runner duplicates what dev.py allocates under `runs/` | 0 tracked citations | migrate-to-declared-dir |
| `.project-local/appdata/` | 210 | 1 | 2026-09-29 06:37 | `appdata/NuGet/NuGet.Config` only - the default nuget.org feed, no credentials | `scripts/runtime/dev.py::environment()` sets NUGET_PACKAGES/NUGET_HTTP_CACHE_PATH but never APPDATA, so this was written by an out-of-band run that redirected APPDATA into the project | 0 tracked citations | migrate-to-declared-dir |
| `.project-local/cargo-home-a04/` | 177 | 2 | 2026-09-21 01:06 | a CARGO_HOME redirect for the a04 run (`.package-cache` + `registry/`) | dev.py's sanctioned equivalent is `.project-local/cache/cargo` | 1 tracked doc | keep-in-place |
| `.project-local/uv-cache/` | 44 | 5 | 2026-09-20 00:18 | uv cache redirect (CACHEDIR.TAG, `sdists-v9/`) | dev.py routes UV_CACHE_DIR to `.project-local/cache/uv` | 0 tracked citations | migrate-to-declared-dir |
| `.project-local/test-fixtures/` | 14 | 2 | 2026-09-21 22:50 | one pytest fixture tmpdir (`tmpfma4z0lh/`) | pytest tmp naming | 0 tracked citations | migrate-to-declared-dir |
| `.project-local/dp-nf-03-probe/` | 1 | 1 | 2026-09-25 20:20 | single `t.txt` probe stub | name matches the DP-NF-03 task id | 0 tracked citations | migrate-to-declared-dir |
| `.project-local/test-fallback-run/` | 0 | 0 | 2026-09-15 22:21 | a fallback run's `artifacts/` capture | shape matches dev.py run artifacts | 1 tracked doc | keep-in-place |
| `.project-local/motion-contract-final-cache/` | 0 | 0 | 2026-09-24 01:34 | empty pytest cache directory | 0 files, 0 bytes | 0 tracked citations | archive-then-remove |
| `.project-local/motion-contract-pytest-cache/` | 0 | 0 | 2026-09-24 01:34 | empty pytest cache directory | 0 files, 0 bytes | 0 tracked citations | archive-then-remove |
| `.project-local/probe/` | 0 | 0 | 2026-09-18 21:04 | empty probe directory | 0 files, 0 bytes | 0 tracked citations | archive-then-remove |
Subtotal 3,583,110,891 B / 39,910 files.

### 4.A2 `.project-local` loose files, main checkout (130 files, rolled up by family)

Per-file rows are in the JSON twin; the families are the decision units.

| Path | Owned bytes | Files | Last write | What it appears to be | Ownership evidence | Referenced by | Disposition |
|---|---:|---:|---|---|---|---|---|
| `.project-local/  (git recovery bundles)` | 37,384,479 | 2 | 2026-09-26 21:41 | 2 loose files, largest `archive-local-only-recovery-20260926.bundle` - local-only branch recovery bundles; `archive-local-only-recovery-20260926.bundle` is cited by 1 tracked doc, the 20260918 one by none | loose at the dev-root, outside every sanctioned class | mostly 0 tracked citations; the bundle and addendum families are cited 1x / 0x | unresolved |
| `.project-local/  (CI / nightly / build log captures)` | 6,241,387 | 7 | 2026-10-01 21:10 | 7 loose files, largest `ci-35349504507.log` - raw stdout captures; each is re-fetchable from GitHub Actions by run id | loose at the dev-root, outside every sanctioned class | mostly 0 tracked citations; the bundle and addendum families are cited 1x / 0x | archive-then-remove |
| `.project-local/  (GitHub API request+response captures (R5-era))` | 3,246,055 | 45 | 2026-09-20 03:08 | 45 loose files, largest `api-upload-r11-hashes.json` - uncited local capture of R5-era GitHub writes; the tracked R5/R6 receipts carry their own SHAs | loose at the dev-root, outside every sanctioned class | mostly 0 tracked citations; the bundle and addendum families are cited 1x / 0x | unresolved |
| `.project-local/  (R5 execution-receipt mirrors)` | 908,503 | 6 | 2026-09-18 03:26 | 6 loose files, largest `r5-execution-r11-hashes.md` - near-duplicates of tracked R5 receipts; must be diffed before any removal | loose at the dev-root, outside every sanctioned class | mostly 0 tracked citations; the bundle and addendum families are cited 1x / 0x | unresolved |
| `.project-local/  (misc working files)` | 243,000 | 14 | 2026-10-07 19:42 | 14 loose files, largest `worktree-worker-quality-0906-wip-20260918.patch` - working files of no declared class (incl. `spillover-addendum-20261007.md`, `ui-b10-style-scan.tmp`, `env-registry*.json`) | loose at the dev-root, outside every sanctioned class | mostly 0 tracked citations; the bundle and addendum families are cited 1x / 0x | migrate-to-declared-dir |
| `.project-local/  (one-off probe, audit and cleanup scripts)` | 141,208 | 37 | 2026-10-07 19:48 | 37 loose files, largest `ocr_head.py` - generating commands for the rows above - keep them readable, but they are not layout | loose at the dev-root, outside every sanctioned class | mostly 0 tracked citations; the bundle and addendum families are cited 1x / 0x | migrate-to-declared-dir |
| `.project-local/  (branch audit text readbacks)` | 105,608 | 5 | 2026-09-26 10:15 | 5 loose files, largest `remote-branch-audit.txt` - readback output of the 2026-09-18/26 branch work | loose at the dev-root, outside every sanctioned class | mostly 0 tracked citations; the bundle and addendum families are cited 1x / 0x | migrate-to-declared-dir |
| `.project-local/  (DSH commit-message / PR-body drafts)` | 36,889 | 14 | 2026-10-01 16:50 | 14 loose files, largest `dsh-pr-body-clean.md` - commit messages and PR bodies already delivered to git and GitHub | loose at the dev-root, outside every sanctioned class | mostly 0 tracked citations; the bundle and addendum families are cited 1x / 0x | archive-then-remove |
Subtotal 48,307,129 B / 130 files.

### 4.B Repository root, main checkout

| Path | Owned bytes | Files | Last write | What it appears to be | Ownership evidence | Referenced by | Disposition |
|---|---:|---:|---|---|---|---|---|
| `tools/` | 4,113,088 | 1 | 2026-07-21 20:38 | `tools/tesseract/tessdata/eng.traineddata` - the OCR language pack the tests read | `.gitignore:50` declares `/tools/tesseract/tessdata/`; two tracked Rust tests resolve that exact path | `.gitignore`, `crates/archeaxis-application/tests/ocr_job_end_to_end.rs:32`, `tests/pdf_ocr_chain.rs:92` - note `config/environment/capability-requirements.yaml:395` declares a DIFFERENT TESSDATA_PREFIX in the shared toolchain root | keep-in-place |
| `archeaxis_workspace.egg-info/` | 48,550 | 6 | 2026-09-24 23:49 | setuptools editable-install metadata | `pip install -e .` output | not tracked; regenerable | archive-then-remove |
| `.zcode/` | 876 | 1 | 2026-09-08 22:45 | IDE/agent private state | DIRECTORY_AUTHORITY gives it `owner: none, write_mode: deny-commit` | `DIRECTORY_AUTHORITY.yaml:211` | foreign-do-not-touch |
| `p-w7n3ehdf/` | 0 | 0 | 2026-09-25 18:00 | empty `p-<8 chars>` directory - the same profile-name family as `.project-local/c/` | 0 files 0 bytes; name shape matches the browser-profile family | 0 tracked citations | archive-then-remove |

### 4.C / 4.D Worktree-shaped paths

`wi/` showed that a *registered* worktree can sit at any path Git is told to use, invisible to
`.project-local/worktrees/`. One remains, and it is not in the sanctioned root.

| Path | Owned bytes | Files | Last write | What it appears to be | Ownership evidence | Referenced by | Disposition |
|---|---:|---:|---|---|---|---|---|
| `D:/All projects/ArcheAxis.Knowledge.Green-x64/.ui-task-tree/minimax-aaos-cosmic-ui-20261001/` | 696,558,986 | 3334 | 2026-10-02 10:05 | a **registered git worktree of this repository checked out inside the Green application root** (branch `codex/minimax-aaos-cosmic-ui-20261001`, tip `627e74ff`) | `git worktree list` names it; `.git/worktrees/minimax-aaos-cosmic-ui-20261001/gitdir` resolves to it; this is the same class as the removed `wi/` | many tracked reconciliation docs cite the branch name and this path (`AAOS-20261002-MASTER-RECONCILIATION.json`, `AAOS-CLOSURE-GAP-AUDIT-20261003.md`, `AAOS-GOVERNANCE-UI-HANDOFF-20261008.md`) | migrate-to-declared-dir |
| `.project-local/worktrees/worker-outside-test/` | 0 | 0 | 2026-10-01 16:50 | empty directory tree, no `.git` file, not in `git worktree list` | `git worktree list` and `.git/worktrees/` do not register it, so no git object or branch depends on it | 0 tracked citations | archive-then-remove |
| `.project-local/worktrees/dp-f01-20260925/` | 0 | 0 | 2026-09-30 05:44 | empty directory tree whose only content is a **self-referential junction** (`data/dp-f01-runs/run-root/N/j` -> `.../run-root2` in the same tree) | `git worktree list` and `.git/worktrees/` do not register it, so no git object or branch depends on it | 0 tracked citations | archive-then-remove |
| `.project-local/worktrees/.project-local/` | 0 | 0 | 2026-10-01 18:40 | empty `runs/ocr-isolate/{attempt,input,data,inputs}` skeleton inside the worktrees root (a dev root nested in a dev root) | `git worktree list` and `.git/worktrees/` do not register it, so no git object or branch depends on it | 0 tracked citations | archive-then-remove |

### 4.E `%TEMP%` — both roots

| Path | Owned bytes | Files | Last write | What it appears to be | Ownership evidence | Referenced by | Disposition |
|---|---:|---:|---|---|---|---|---|
| `C:/Windows/TEMP/archeaxis-window-ned2hf14` | 179,598 | 1 | 2026-10-08 02:26 | one `window-0000.wav` ASR window frame | `services/python-workers/media/worker_transcribe.py` builds exactly this `archeaxis-window-` prefix | that tracked worker | keep-in-place |
| `C:/Windows/TEMP/archeaxis-window-ypxj9_mg` | 179,598 | 1 | 2026-10-08 02:26 | one `window-0000.wav` ASR window frame | same generating worker | that tracked worker | keep-in-place |
| `C:/Windows/TEMP/playwright-* + playwright_chromiumdev_profile-* (14 entries)` | 47,408 | 27 | 2026-10-08 20:12 | Playwright artifact dirs and Chromium dev profiles written to the OS temp root | generated by `scripts/a0_browser_smoke.py` runs; OS-owned location, OS-reclaimable | `dev.py` routes `PLAYWRIGHT_BROWSERS_PATH` to `.project-local/cache/playwright` - the profiles are not that | keep-in-place |
| `C:/Windows/TEMP/aaos-msvc-target` | 34,030 | 1 | 2026-08-13 01:47 | cargo target dir redirect (`debug/`), 2026-08-13 | OS temp is the declared home for temp; name claims the project | 3 tracked docs (`AAOS01-CLEANUP-EXECUTED-AND-PENDING-20261005.md` etc.) | keep-in-place |
| `C:/Windows/TEMP/archeaxis-ocr-probe.png` | 12,350 | 1 | 2026-10-08 12:20 | the 12,350 B OCR probe image | matches the OCR probe string in tracked config | `config/environment/capability-requirements.yaml` | keep-in-place |
| `C:/Users/ALEX/AppData/Local/Temp/aaosbt` | 848 | 44 | 2026-10-07 13:59 | 44 files: pytest tmp dirs (`test_assembly_bundles_desktop_0`, `test_cli_current_source_gate_r0`, ...) from a run with TMP redirected outside dev.py | pytest basetemp shape | none | keep-in-place |
| `C:/Windows/TEMP/aaos-target` | 0 | 0 | 2026-10-07 22:03 | empty cargo `release/` target redirect | as above | `AAOS01-CLEANUP-EXECUTED-AND-PENDING-20261005.md` | keep-in-place |
| `C:/Users/ALEX/AppData/Local/Temp/aaos-deep-a4khq8gd` | 0 | 0 | 2026-10-07 15:39 | empty ASR segment scratch dir (`segment-00-dddddddddddddddddddddddd`) | matches the diarization segment naming of the F10 work | none | keep-in-place |
| `C:/Windows/TEMP (total entries 4623) + LocalAppData/Temp (287)` | 0 | 4910 | 2026-10-08 20:12 | the machine's two temp roots; 5 + 2 entries name this project | project-named entries enumerated by name, sizes measured individually | AGENTS.md: files found in %TEMP% are ambiguous until content, worktree, process and generating command establish ownership | foreign-do-not-touch |

### 4.F `C:\Users\ALEX\Downloads` — existence check only

| Path | Owned bytes | Files | Last write | What it appears to be | Ownership evidence | Referenced by | Disposition |
|---|---:|---:|---|---|---|---|---|
| `C:/Users/ALEX/Downloads/` | 0 | 14 | 2026-10-08 20:11 | 14 entries; 0 project-named entries | name-pattern check only; no file contents were read | not applicable - no project-named file exists there | foreign-do-not-touch |

### 4.G Sibling projects and drive roots

| Path | Owned bytes | Files | Last write | What it appears to be | Ownership evidence | Referenced by | Disposition |
|---|---:|---:|---|---|---|---|---|
| `D:/All projects/Record/AAOS-project-archives/` | 15,042,572,388 | 24 | 2026-09-30 03:40 | AAOS/Green recovery archive trees for 2026-09-29 and 2026-09-30 (ZIPs of run/build/UI-history/publish trees) | content is this project's history; SHA-256 of the 76-dir UI history ZIP was recomputed and matched the recorded `183929BF...` in the 2026-10-07 readback | >=9 tracked docs incl. `AAOS-SPILLOVER-MIGRATION-20260928.md`, `R6-EXECUTION.md`, `AAOS_VISUAL_QA.md`, `docs/history/storage-cleanup/2026-09-30/*` | keep-in-place |
| `D:/All projects/ArcheAxis.Knowledge.Green-x64/ (AAOS-Frontend-Acceptance-v4, AAOS-Tauri-f151f4c7998a, aaos-vnext-data*, .ui-task-tree/ArcheAxis-Knowledge-OS, 星环智汇知识-AAOS*.vbs, archeaxis.sqlite locks)` | 9,497,545,755 | 119167 | 2026-10-06 10:29 | installed application data, acceptance batches, vNext data dirs and launcher scripts inside the declared `green_application` root | names carry this project's source SHAs | `docs/SHARED_RESOURCE_PATH_INDEX.md` (green_application), `GREEN-REPO-CLEANUP-AUDIT-20261006.md`, `AAOS01-WHAT-IS-USABLE-IN-THE-OLD-GREEN.md` | keep-in-place |
| `D:/All projects/ArcheAxis.Knowledge.Green-x64/.ui-task-tree/ArcheAxis-Knowledge-OS-mainline/` | 6,689,350,007 | 66935 | 2026-10-01 12:08 | a mainline clone of this repository living in the Green app root | git reports dubious ownership - the tree belongs to `CodexSandboxOnline` | `AAOS-GREEN-REPOSITORY-BOUNDARY-AUDIT-20261001.md` and the 2026-10-07 readback | foreign-do-not-touch |
| `D:/All projects/UI套件/ (ArcheAxis_* zips + AAOS_UI_Taskpack_20261007.zip)` | 94,103,025 | 16 | 2026-10-07 01:03 | the owner's UI suite library that this project consumes read-only via `.project-local/inputs/` | the same suite names appear under `.project-local/inputs/AAOS/extracted/` | `docs/authority/taskpack-1007-aaos-ui/README.md` | foreign-do-not-touch |
| `D:/All projects/Record/ (loose AAOS_/ARCHEAXIS_/QODER_AAOS files)` | 26,098,012 | 30 | 2026-10-07 09:25 | the owner's own taskpack/audit copies (ZIPs, .md, .txt, .docx) handed out to agents | file names are the delivered taskpack identities | referenced as delivery copies, not as runtime paths | foreign-do-not-touch |
| `D:/All projects/Design Projects/ (AAOS_* + RECON-verify/*.png + assets/aaos-*)` | 16,501,462 | 35 | 2026-10-07 02:11 | the design workspace's own AAOS deliverables: portal HTML, brand mark SVG, motion JS, 30+ screenshots | owned and generated by the Design-LAB/Design Projects line | cited by the design line, not by this repository | foreign-do-not-touch |
| `C:/EDTemp/20260626_201003/sqlite3.dll + C:/EDTemp/20260626_202345/sqlite3.dll` | 4,333,568 | 2 | 2026-06-26 20:23 | two byte-identical sqlite3.dll copies dated 2026-06-26 | no content, worktree, process or generating command ties them to this project | carried forward from `AAOS-SPILLOVER-MIGRATION-20260928.md` + the 2026-10-07 readback as UNRESOLVED-AMBIGUOUS | unresolved |
| `D:/All projects/.aaos-stray-archive-20261001/` | 721,063 | 10 | 2026-10-02 09:40 | receipt + archived SQLite of the 2026-10-02 drive-root clean-up: `MANIFEST.json` records `D:\All`, `D:\All-wal`, `D:\All-shm`, `D:\All.writer.lock`, `D:\END`, `D:\.project-local` and hashes the checkpointed `workspace-schema5-learning-smoke.sqlite` | `MANIFEST.json` states the origin in its own `why` field; the six D:-root paths it names are now verified ABSENT | 0 tracked citations - the only proof of that clean-up sits outside the repository | migrate-to-declared-dir |
| `D:/All projects/ArcheAxis.Knowledge.Green-x64/AAOS01-文档同步-20261006/` | 211,084 | 11 | 2026-10-06 10:29 | copies of AGENTS.md / PROJECT_CONTRACT.yaml / README.md / docs/ written into the application root | file names collide with tracked repository documents | 0 tracked citations (`git grep AAOS01-文档同步` = 0) | unresolved |
| `D:/All projects/dsh-acl-reports-20261003/` | 83,329 | 4 | 2026-10-03 21:05 | DSH project ACL reports; no project-named entry at depth 2 | belongs to the DSH project | none here | foreign-do-not-touch |
| `D:/All projects/.aaos-root-backup-20261001/` | 12,434 | 2 | 2026-10-02 09:24 | two working copies of `AAOS-UI-COVERAGE-MATRIX` (.md + .patch) parked at 2026-10-01/02 | content names the tracked UI coverage doc | 0 tracked citations | migrate-to-declared-dir |
| `D:/All projects/WORK-LAB/integrations/archeaxis/` | 7,420 | 3 | 2026-09-23 21:58 | WORK-LAB's own pointer into this project (3 files) | AGENTS.md §9 declares WORK-LAB an independent repository that may coordinate via CLI/API only | `AGENTS.md`, `.worklab/*` | foreign-do-not-touch |

### 4.H Declared shared roots: which entries this project actually references

`Model library` (`shared_models`) holds **no** project-named entry at depth 3, so nothing of this project is parked
there. Every entry below resolves to a live path *and* to a resource id or a tracked document — that is what separates
declared sharing from spillover.

| Path | Owned bytes | Files | Last write | What it appears to be | Ownership evidence | Referenced by | Disposition |
|---|---:|---:|---|---|---|---|---|
| `D:/All projects/OS External Configuration/toolchains/rust/rustup` | 2,230,427,310 | 551 | 2026-09-24 08:05 | the rustup home that actually answers `rustup show home` | registered by the project's own resource index; existence re-verified this pass | `docs/SHARED_RESOURCE_PATH_INDEX.md` id `shared_rustfmt_home` | keep-in-place |
| `D:/All projects/OS External Configuration/60-cache/nuget` | 1,870,742,184 | 2047 | 2026-10-03 20:04 | shared NuGet cache holding the restored Avalonia 12.1.2 dependency set | registered by the project's own resource index; existence re-verified this pass | `docs/SHARED_RESOURCE_PATH_INDEX.md` resource id `shared_nuget_cache` | keep-in-place |
| `D:/All projects/OS External Configuration/ArcheAxis-Knowledge-OS-ci-venv` | 977,718,204 | 22326 | 2026-10-07 16:08 | a CI virtualenv named for this project | registered by the project's own resource index; existence re-verified this pass | `docs/SHARED_RESOURCE_PATH_INDEX.md` + `config/environment/external-resources-index.json` + `config/environment/capability-requirements.yaml` | keep-in-place |
| `D:/All projects/OS External Configuration/10-toolchains/dotnet-sdk-10.0.401` | 807,336,133 | 5577 | 2026-08-24 05:26 | dotnet SDK 10.0.401, the Green-mainline toolchain identity | registered by the project's own resource index; existence re-verified this pass | `docs/SHARED_RESOURCE_PATH_INDEX.md` resource id `shared_dotnet_sdk_10_0_401` | keep-in-place |
| `D:/All projects/OS External Configuration/10-toolchains/dotnet` | 807,115,876 | 5577 | 2026-07-29 18:35 | dotnet SDK 10.0.400 used for `net10.0` Avalonia builds | registered by the project's own resource index; existence re-verified this pass | `docs/SHARED_RESOURCE_PATH_INDEX.md` resource id `shared_dotnet_sdk` | keep-in-place |
| `D:/All projects/OS External Configuration/10-toolchains/python/venv-aaos-ui-312` | 286,069,912 | 7663 | 2026-09-24 00:01 | the AAOS UI test interpreter (CPython 3.12.13, pytest 9.1.1) | registered by the project's own resource index; existence re-verified this pass | `docs/SHARED_RESOURCE_PATH_INDEX.md` resource id `shared_aaos_ui_python` | keep-in-place |
| `D:/All projects/OS External Configuration/10-toolchains/cargo/bin` | 179,400,704 | 14 | 2026-08-23 07:37 | cargo/rustc 1.97.1 | registered by the project's own resource index; existence re-verified this pass | `docs/SHARED_RESOURCE_PATH_INDEX.md` ids `shared_cargo`/`shared_rustc` | keep-in-place |
| `D:/All projects/OS External Configuration/scripts/Enter-ArcheAxisDev.ps1` | 6,423 | 1 | 2026-08-16 00:38 | the developer entry script named for this project | registered by the project's own resource index; existence re-verified this pass | `HERMES_HANDOFF.md`, `docs/design/AXW-ENV-103-applied.md`, `docs/truth/ARCHITECTURE_FINAL.md` | keep-in-place |
| `D:/All projects/OS External Configuration/scripts/Exit-ArcheAxisDev.ps1` | 1,869 | 1 | 2026-08-14 23:01 | its counterpart | registered by the project's own resource index; existence re-verified this pass | `HERMES_HANDOFF.md`, `docs/truth/ARCHITECTURE_FINAL.md` | keep-in-place |
| `D:/All projects/OS External Configuration/10-toolchains/msvc/VC/Auxiliary/Build/vcvars64.bat` | 39 | 1 | 2026-07-22 00:27 | MSVC environment entry point | registered by the project's own resource index; existence re-verified this pass | `docs/SHARED_RESOURCE_PATH_INDEX.md` id `shared_msvc_environment` | keep-in-place |
| `D:/All projects/Model library/` | 0 | 0 | 2026-09-29 00:19 | shared model library (`shared_models`). A name scan for archeaxis/aaos/星环 at depth <= 3 returned **0 hits**, so nothing of this project is parked in it | declared resource root; scan by name only, no weight files read | `docs/SHARED_RESOURCE_PATH_INDEX.md` id `shared_models` | foreign-do-not-touch |

### 4.I Inside the repository but untracked

| Path | Owned bytes | Files | Last write | What it appears to be | Ownership evidence | Referenced by | Disposition |
|---|---:|---:|---|---|---|---|---|
| `docs/history/worktree-preserved-diffs/hermes__task-runtime__*.patch` | 15,707 | 8 | 2026-09-13 13:23 | 8 `git status --short` untracked patches preserving other worktrees' WIP (the 9th file in that directory, `worker-quality-0906-unique-20260918.md`, IS tracked) | the 2026-10-07 readback corrected the earlier '9 patches' count to 8 | `AAOS-SPILLOVER-MIGRATION-20260928.md` + `docs/current/AAOS-LOCAL-REPOSITORY-LINEAGE-READBACK-20260925.md` | unresolved |

### 4.J Credential-class candidates: path and size recorded, contents NOT read

These must not be opened, printed, copied or committed. `browser-debug.env` and the profile `Vpn Tokens` databases are
named here so that no later pass mistakes them for movable scratch.

| Path | Owned bytes | Files | Last write | What it appears to be | Ownership evidence | Referenced by | Disposition |
|---|---:|---:|---|---|---|---|---|
| `.project-local/acceptance/AAOS-B10-20261001/edge-profile` | 17,408,206 | 192 | 2026-10-01 10:42 | browser-profile internals / env files / a test fixture | name pattern only | not read - see AGENTS.md §3 (do not print or print secrets) | keep-in-place |
| `.project-local/acceptance/AAOS-B10-20261001/chrome-profile` | 7,136,255 | 170 | 2026-10-01 10:45 | browser-profile internals / env files / a test fixture | name pattern only | not read - see AGENTS.md §3 (do not print or print secrets) | keep-in-place |
| `.project-local/c/p-v6ql20b5/Default/Vpn Tokens` | 28,672 | 1 | 2026-09-27 16:41 | browser-profile internals / env files / a test fixture | name pattern only | not read - see AGENTS.md §3 (do not print or print secrets) | keep-in-place |
| `.project-local/c/p-vavp0djd/Default/Vpn Tokens` | 28,672 | 1 | 2026-09-27 16:20 | browser-profile internals / env files / a test fixture | name pattern only | not read - see AGENTS.md §3 (do not print or print secrets) | keep-in-place |
| `.project-local/runs/*/*/runtime*.env` | 3,941 | 4 | various | browser-profile internals / env files / a test fixture | name pattern only | not read - see AGENTS.md §3 (do not print or print secrets) | keep-in-place |
| `.project-local/task-runtime/aaos-ui/browser-debug.env` | 3,182 | 1 | 2026-10-07 09:06 | browser-profile internals / env files / a test fixture | name pattern only | not read - see AGENTS.md §3 (do not print or print secrets) | keep-in-place |
| `.project-local/a15-current-security-basetemp/*/outside/secret.txt` | 6 | 1 | various | browser-profile internals / env files / a test fixture | name pattern only | not read - see AGENTS.md §3 (do not print or print secrets) | keep-in-place |

## 5. What could not be attributed, and why
- **`.project-local/dep-src-clean/`** (113,875,324 B / 2211 files) — unpacked third-party dependency sources (PIL, XlsxWriter, et_xmlfile, 19 dist dirs) from a licence/reuse review. Evidence: content names Python packages only. References: 0 tracked citations.
- **`.project-local/ci-replay/`** (4,983,174 B / 16 files) — one replayed CI runtime tree `fresh-runtime/`. Evidence: names CI, no run id recorded. References: 0 tracked citations.
- **`.project-local/  (git recovery bundles)`** (37,384,479 B / 2 files) — 2 loose files, largest `archive-local-only-recovery-20260926.bundle` - local-only branch recovery bundles; `archive-local-only-recovery-20260926.bundle` is cited by 1 tracked doc, the 20260918 one by none. Evidence: loose at the dev-root, outside every sanctioned class. References: mostly 0 tracked citations; the bundle and addendum families are cited 1x / 0x.
- **`.project-local/  (GitHub API request+response captures (R5-era))`** (3,246,055 B / 45 files) — 45 loose files, largest `api-upload-r11-hashes.json` - uncited local capture of R5-era GitHub writes; the tracked R5/R6 receipts carry their own SHAs. Evidence: loose at the dev-root, outside every sanctioned class. References: mostly 0 tracked citations; the bundle and addendum families are cited 1x / 0x.
- **`.project-local/  (R5 execution-receipt mirrors)`** (908,503 B / 6 files) — 6 loose files, largest `r5-execution-r11-hashes.md` - near-duplicates of tracked R5 receipts; must be diffed before any removal. Evidence: loose at the dev-root, outside every sanctioned class. References: mostly 0 tracked citations; the bundle and addendum families are cited 1x / 0x.
- **`D:/All projects/ArcheAxis.Knowledge.Green-x64/AAOS01-文档同步-20261006/`** (211,084 B / 11 files) — copies of AGENTS.md / PROJECT_CONTRACT.yaml / README.md / docs/ written into the application root. Evidence: file names collide with tracked repository documents. References: 0 tracked citations (`git grep AAOS01-文档同步` = 0).
- **`C:/EDTemp/20260626_201003/sqlite3.dll + C:/EDTemp/20260626_202345/sqlite3.dll`** (4,333,568 B / 2 files) — two byte-identical sqlite3.dll copies dated 2026-06-26. Evidence: no content, worktree, process or generating command ties them to this project. References: carried forward from `AAOS-SPILLOVER-MIGRATION-20260928.md` + the 2026-10-07 readback as UNRESOLVED-AMBIGUOUS.
- **`docs/history/worktree-preserved-diffs/hermes__task-runtime__*.patch`** (15,707 B / 8 files) — 8 `git status --short` untracked patches preserving other worktrees' WIP (the 9th file in that directory, `worker-quality-0906-unique-20260918.md`, IS tracked). Evidence: the 2026-10-07 readback corrected the earlier '9 patches' count to 8. References: `AAOS-SPILLOVER-MIGRATION-20260928.md` + `docs/current/AAOS-LOCAL-REPOSITORY-LINEAGE-READBACK-20260925.md`.

Two further items are attributed but not resolvable by this register:
`D:/All projects/ArcheAxis.Knowledge.Green-x64/.ui-task-tree/ArcheAxis-Knowledge-OS-mainline` is project-shaped bytes
owned by the `CodexSandboxOnline` identity (git reports dubious ownership), and the `Record` archive trees sit in a
*separate repository* whose own authority this project has not read. Both are dispositioned by ownership, not by
content.

## 6. Migration plan — run only after the owner rules on it

Nothing below was executed. Each destination is checked against both contracts;
`build | runs | cache | tmp | worktrees | recovery | mig` are the only class names neither list can flag.

### M1 — the remaining non-sanctioned registered worktree (664 MB, highest value)

`git worktree move` carries the registration with the bytes, so no `.git/worktrees` admin entry is left dangling —
which is exactly what a plain directory move would have done to `wi/`.

```powershell
# forward
git -C 'D:\All projects\ArcheAxis-Knowledge-OS' worktree move `
  'D:\All projects\ArcheAxis.Knowledge.Green-x64\.ui-task-tree\minimax-aaos-cosmic-ui-20261001' `
  'D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\minimax-aaos-cosmic-ui-20261001'
# rollback (exact inverse)
git -C 'D:\All projects\ArcheAxis-Knowledge-OS' worktree move `
  'D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\minimax-aaos-cosmic-ui-20261001' `
  'D:\All projects\ArcheAxis.Knowledge.Green-x64\.ui-task-tree\minimax-aaos-cosmic-ui-20261001'
```

Checked before proposing: `git worktree list` and `.git/worktrees/minimax-aaos-cosmic-ui-20261001/gitdir` both resolve
to the Green path; the tree is clean; its branch is `codex/minimax-aaos-cosmic-ui-20261001` at `627e74ff`; it contains
no links at depth 3. Destination `worktrees/` is sanctioned by **both** lists. It still writes inside the declared
`green_application` root, which `docs/SHARED_RESOURCE_PATH_INDEX.md` places out of reach this round — so this one move
needs an explicit owner yes, not just a directory comparison.

### M2 — tool-cache husks that dev.py never created, into `cache/`

`.project-local/{appdata,localappdata,npm-cache,uv-cache,uv-cache-agent-icon,dotnet-home,tools}` are redirect
leftovers. `scripts/runtime/dev.py::environment()` routes NuGet, npm, uv, Cargo, `DOTNET_CLI_HOME` and `TMP` into
`.project-local/cache/...` and **never sets `APPDATA` or `LOCALAPPDATA`**, so these names cannot be produced by the
project's own launcher.

```powershell
$dst = 'D:\All projects\ArcheAxis-Knowledge-OS\.project-local\cache\imported-20261008'
New-Item -ItemType Directory -Force -Path $dst | Out-Null
foreach ($n in 'appdata','localappdata','npm-cache','uv-cache','uv-cache-agent-icon','dotnet-home','tools') {
  Move-Item -LiteralPath "D:\All projects\ArcheAxis-Knowledge-OS\.project-local\$n" -Destination (Join-Path $dst $n)
}
# rollback: same loop with source and destination swapped, then remove $dst
```

Destination `cache/` is sanctioned by both lists. `tools/uv-0.12.18/` is Access Denied to this identity: move it from a
session that owns it, or leave it and let §7.4 handle the recurrence.

### M3 — browser-profile scratch, into `tmp/`

`.project-local/c/p-*` are Edge/Chromium temporary profiles; the root stray `p-w7n3ehdf/` is the same naming family and
is empty. They are regenerable and uncited, but they contain profile internals (§4.J), so they go to the ignored
scratch class rather than being deleted.

```powershell
$dst = 'D:\All projects\ArcheAxis-Knowledge-OS\.project-local\tmp\imported-20261008'
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Move-Item -LiteralPath 'D:\All projects\ArcheAxis-Knowledge-OS\.project-local\c' -Destination (Join-Path $dst 'c')
# rollback: Move-Item (Join-Path $dst 'c') back to .project-local\c
```

Destination `tmp/` is sanctioned by both lists. The empty root stray `p-w7n3ehdf/` is handled by M5 instead.

### M4 — uncited working output and loose files, into `task-runtime/`

`probes, inspect, dsh-recon-20261001, dsh-recon-20261001-bytes, dsh-audit, test-fixtures, probe2, p, dp-nf-03-probe,
tmp-measure` plus the loose-file families marked `migrate-to-declared-dir`. `task-runtime/` is sanctioned by
`storage_report.py` but is **not** named in `ignored_local_roots`; it is covered regardless because `.project-local/**`
is `write_mode: deny-commit` and nothing under it can be tracked. This is the one destination §7.1 has to close.

```powershell
$dst = 'D:\All projects\ArcheAxis-Knowledge-OS\.project-local\task-runtime\spillover-imported-20261008'
New-Item -ItemType Directory -Force -Path $dst | Out-Null
foreach ($n in 'probes','inspect','dsh-recon-20261001','dsh-recon-20261001-bytes','dsh-audit','test-fixtures',
                'probe2','p','dp-nf-03-probe','tmp-measure') {
  Move-Item -LiteralPath "D:\All projects\ArcheAxis-Knowledge-OS\.project-local\$n" -Destination (Join-Path $dst $n)
}
New-Item -ItemType Directory -Force -Path (Join-Path $dst 'files') | Out-Null
Get-ChildItem -LiteralPath 'D:\All projects\ArcheAxis-Knowledge-OS\.project-local' -File |
  Where-Object { $_.Name -match '^(ocr_head|analyse-|audit-|preserve-|reword-|verify-|scan-|red-check|probe-|human-|qwen-|reranker-|same-source|from-knowledge|append_ledger|resolve_both|validate-|g1-run|g4-run|api-test|cleanup-|dsh-|r5-|api-|blob|local-branch|remote-|q00-|env-registry|extdeps|low-quota|nightly-|ci-|rust-workspace|workerlog|ui-b10|worktree-worker|green-worker|aaos-)' -and
                    $_.Name -notmatch '^(archive-local-only-recovery|spillover-addendum|api-upload-r11|api-upload-q00|api-upload-current|r5-execution-|r5-state-|api-update)' } |
  Move-Item -Destination (Join-Path $dst 'files')
# rollback: move each name back to .project-local\ (and 'files\*' with it), then remove $dst
```

Excluded from this move and why: `archive-local-only-recovery-20260926.bundle` is cited and is a recovery ref;
`spillover-addendum-20261007.md` is cited by this register; the `api-*` and `r5-*` capture families are `unresolved`
until diffed against the tracked receipts.

### M5 — the empty husks, remove after approval (0 owned bytes)

`worker-outside-test`, `dp-f01-20260925`, `worktrees/.project-local`, `motion-contract-final-cache`,
`motion-contract-pytest-cache`, `probe`, root `p-w7n3ehdf`, root `archeaxis_workspace.egg-info`. There are no bytes to
archive — the archive step is this register naming each by exact path — so the removals are reversible only by
re-creating an empty directory.

```cmd
:: dp-f01-20260925 holds a self-referential junction. Remove the LINK FIRST: a recursive delete
:: follows it into the tree it points at. `cmd /c rmdir` on a junction removes the link only.
cmd /c rmdir "\\?\D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\dp-f01-20260925\data\dp-f01-runs\run-root\N\j"
cmd /c rmdir /s /q "\\?\D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\dp-f01-20260925"
cmd /c rmdir /s /q "\\?\D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\worker-outside-test"
cmd /c rmdir /s /q "\\?\D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\.project-local"
```

Never use `rm -rf` or `Remove-Item -Recurse` on a path containing a junction — `DIRECTORY_AUTHORITY.yaml`'s
`shared_resource_install_rules` states the same rule for the shared installs.

### M6 — two outside-repo receipts, into the repository's `recovery/`

`D:/All projects/.aaos-stray-archive-20261001` is the only proof of the 2026-10-02 drive-root clean-up: its
`MANIFEST.json` hashes the `D:\All`, `D:\All-wal`, `D:\All-shm`, `D:\All.writer.lock`, `D:\END` and
`D:\.project-local` entries that were removed (all six verified ABSENT this pass). `D:/All projects/.aaos-root-backup-20261001`
holds two working copies of `AAOS-UI-COVERAGE-MATRIX`. Neither is named by any tracked document.

```powershell
$dst = 'D:\All projects\ArcheAxis-Knowledge-OS\.project-local\recovery\spillover-imported-20261008'
New-Item -ItemType Directory -Force -Path $dst | Out-Null
foreach ($n in '.aaos-stray-archive-20261001','.aaos-root-backup-20261001') {
  Copy-Item -Recurse -LiteralPath (Join-Path 'D:\All projects' $n) -Destination (Join-Path $dst $n)
  Get-ChildItem -Recurse -File -LiteralPath (Join-Path $dst $n) | Get-FileHash -Algorithm SHA256 |
    Out-File -Append -Encoding utf8 (Join-Path $dst 'hashes-before-removing-originals.txt')
}
# verify the copies against the hashes, then and only then remove the originals
# rollback before removal: delete the copy; the original is untouched
```

Destination `recovery/` is sanctioned by both lists in this branch's authority. Copy-verify-then-remove matters here:
these are receipts, not caches, and `MANIFEST.json` is the only record of a deletion that already happened.

### M7 — captures that duplicate content held elsewhere, archive first then remove

Applies only to the two loose-file families dispositioned `archive-then-remove`: the CI/nightly/build log captures
(re-fetchable from GitHub Actions by the run id in each file name) and the DSH commit-message/PR-body drafts (whose
commits are in git and whose PRs are on GitHub). The project rule is archive-not-delete, so the removal is a separate
step behind a verification:

```powershell
$src = 'D:\All projects\ArcheAxis-Knowledge-OS\.project-local'
$dst = 'D:\All projects\ArcheAxis-Knowledge-OS\.project-local\recovery\spillover-archive-20261008'
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Get-ChildItem -LiteralPath $src -File |
  Where-Object { $_.Name -match '^(ci-|nightly-|rust-workspace-test|workerlog|dsh-commit-message|dsh-pr-body)' } |
  ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $dst
    '{0}  {1}' -f (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash, $_.Name
  } | Set-Content -Encoding utf8 (Join-Path $dst 'SHA256SUMS.txt')
# verify every copy against SHA256SUMS.txt, then delete only the verified originals
# rollback before deletion: delete $dst (originals untouched); after deletion: restore from $dst by hash
```

Destination `recovery/` is sanctioned by both lists. The `api-*` and `r5-*` capture families are **not** in M7 — they
are `unresolved` until each is diffed against the tracked receipt it mirrors, because a near-duplicate of a receipt is
not yet proven to be a duplicate.

### Explicitly NOT proposed, with the reason

| Item | Owned bytes | Why no move is proposed |
|---|---:|---|
| `D:/All projects/Record/AAOS-project-archives/` | 15,042,572,388 | sole copy, cited by >=9 tracked docs. The 2026-10-07 readback already fixed the correct order: land an ownership + old/new path map first, then move per-file SHAs while rewriting the citations in the same batch. 9 of its ZIPs have no recorded SHA, so the move cannot be verified without hashing them first. |
| `D:/All projects/ArcheAxis.Knowledge.Green-x64/.ui-task-tree/ArcheAxis-Knowledge-OS-mainline/` | 6,689,350,007 | dubious ownership (`CodexSandboxOnline`); ownership must be resolved before any operation on it. |
| `D:/All projects/ArcheAxis.Knowledge.Green-x64/ (AAOS-Frontend-Acceptance-v4, AAOS-Tauri-f151f4c7998a, aaos-vnext-data*, .ui-task-tree/ArcheAxis-Knowledge-OS, 星环智汇知识-AAOS*.vbs, archeaxis.sqlite locks)` | 9,497,545,755 | inside the declared `green_application` root, which `docs/SHARED_RESOURCE_PATH_INDEX.md` places out of reach this round. |
| `docs/history/worktree-preserved-diffs/hermes__task-runtime__*.patch` | 15,707 | inside the repository: the question is commit-or-discard, which is a tracked-change decision, not a move. |
| `C:/Windows/TEMP project-named entries + LocalAppData/Temp` | see §4 rows | already in the OS's declared temp location; moving them *into* the project would create spillover, not remove it. |
| `D:/All projects/Design Projects, UI套件, WORK-LAB/integrations/archeaxis, dsh-acl-reports-20261003, Record loose files` | see §4 rows | owned by other work lines or by the owner's own record set; this project consumes two of them read-only. |

## 7. What the register says the layout contract is missing

1. **The two sanctioned lists must be reconciled, not re-derived.** `storage_report.py`'s `DEV_ALLOWED` and
   `DIRECTORY_AUTHORITY.yaml`'s `ignored_local_roots` disagree today on `artifacts/` (2,607,542,960 B /
   32,872 files, cited by 6 tracked docs, flagged by the report), on `task-runtime/`, `candidates/` and
   `a3-python-input/` (accepted by the report, unnamed by the authority) and on `logs/`, `agents/`, `leases/` (the
   reverse). One list should be generated from the other, or `storage_report.py` should read `ignored_local_roots`
   instead of holding a second hand-written set. Until then a destination can be right under one contract and drift
   under the other, which is how 172 entries stayed unreconciled after
   being counted.
2. **There is no class for "registered worktree at a non-sanctioned path".** `wi/` (4.50 GB, removed) and the
   remaining `minimax-aaos-cosmic-ui-20261001` are the same defect: git accepts any path, so `worktrees/` is only a
   convention. A checker comparing `git worktree list` against
   `shared_resource_install_rules.development_root` would have caught both. This is the highest-value rule the register
   implies.
3. **Nothing measures outside the repository.** `storage_report.py` walks `REPO` and `REPO/.project-local`. The
   14.0 GiB in `Record`, the receipts under `D:\All projects\.` and the drive-root files that `MANIFEST.json`
   recorded all live beyond its reach, which is why a 174-entry count could be filed and left. The generator of this
   register enumerates `%TEMP%`, the sibling roots and the declared shared roots by name pattern; promoting that root
   list into a tracked checker is what makes 外溢数据 *tracked* instead of *discovered*.
4. **Recurrence guard for the redirect husks.** `dev.py` redirects NuGet/npm/uv/Cargo/`DOTNET_CLI_HOME`/`TMP` but not
   `APPDATA`/`LOCALAPPDATA`, which is why `appdata/` and `localappdata/AvaloniaUI/BuildServices/` appeared anyway.
   Either route them into `cache/` like the others or record them as out of scope; silence reproduces the class on the
   next direct `dotnet`/Avalonia build.
5. **The class map is already complete enough to use.** `DIRECTORY_AUTHORITY.yaml`'s `ownership_classes` names the four
   classes this register needed: `source-contract-index`, `run-evidence`, `rebuildable-cache`, `shared-by-declaration`.
   Every row above lands in one of them except the §5 unresolved set — that set, not the byte totals, is the governance
   gap. `rebuildable-cache` is also failing its own predicate right now: the 2026-10-08 disposition pass recorded 5
   real copies of the same frontend install (967,284,557 duplicate bytes) where the rule allows one real copy plus
   links (`.project-local/task-runtime/worktree-disposition-20261008/numbers-for-doc.md`); that number is theirs, not a
   re-measurement by this register.

## 8. Verifying and rolling back this register

- Re-measure: `python .project-local/task-runtime/spillover-register-20261008/build_register.py` rewrites the JSON
  twin, then `emit_markdown.py` rebuilds this document from it. Both write only inside `task-runtime/` and
  `docs/current/`.
- Cross-check the layout count with the repository's own contract: `python scripts/runtime/storage_report.py --json
  <path>` (the main checkout has no copy of that script, so
  `.project-local/task-runtime/worktree-disposition-20261008/main_layout_audit.py` imports it and points it there —
  that run is what recorded the 174).
- Roll back this register: delete `docs/current/AAOS-SPILLOVER-REGISTER-20261008.md` and its JSON twin. No byte
  outside those two files was created, changed, moved or deleted by this pass.
