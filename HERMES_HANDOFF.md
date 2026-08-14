# Hermes handoff — archeaxis-workspace

Generated: 2026-08-14 (replaced stale 2026-07-23 copy)

## Current continuation point

- Repository: `D:\All projects\ArcheAxis-Knowledge-OS` (canonical, single writer: Hermes)
- Branch: `main` — HEAD and origin in sync (verify with `git status --short --branch` before resuming)
- Cloud: `https://github.com/DTALEX66/ArcheAxis-Knowledge-OS` (push via 127.0.0.1:7890 proxy; api.github.com direct)
- Baseline: AXC TaskPack 2026-08-13 (AXC-000~150 v1.1). Full suite: **1619 passed / 5 skipped** (2026-08-15 local); ruff + repository-conventions gate green on head.

## Frozen-baseline execution state (LOG-147..176 in `docs/truth/EXECUTION_STATUS_LOG.md`)

Implemented and CI-verified (continuous green: CI runs 524-583):

- **AXW-022B**: PDF evidence annotation reachable (text-layer overlay + cached selection); real browser-smoke first ran on CI at `85b3311` (run 31732780580).
- **H5 implementation layer** (`5dc3d9b` + `d129aa3`): AXW-094A open-exchange export (`app/exchange/export.py`), AXW-094B verifiable backup (`app/exchange/backup.py`), AXW-096A performance benchmark (`shared/performance_benchmark.py`), AXW-096B keyboard accessibility (UI), AXW-096C batch import control (`app/ingestion/batch_controller.py`). EXIT is a verification gate, not an implementation prerequisite (precedent 023A-F/043B/050A).
- **AXW-096A real data**: layered zh/en public-domain corpus (Gutenberg, sources.json provenance, corpus NOT committed) + real benchmark PASS (`01ad561`); toolchain `scripts/prepare_benchmark_corpus.py` / `scripts/run_performance_benchmark.py`; report `docs/truth/PERFORMANCE_BENCHMARK_096A.md`.
- **Workspace API surface** (`81df63b`): exchange export/verify, backup create/verify/restore(dry-run), batch import/status — error semantics explicit (400/404/409/422).
- **User-facing UI entry** (`892b87b`): Evidence page 开放交换与备份 card — four reachable buttons (export/verify/backup create/verify) with API round-trip asserted in browser-smoke (`#evidence` hash route).
- **Async batch control** (`8ea9a05` + `976bf13` + `6011b81`): pause/resume/shutdown on a live registry; ledger task-list recovery + terminal-state restoration (from_checkpoint) — interrupted batches are resumable, totals honest; duplicate-active rejected 409 (covered).
- **CI ecosystem audit**: nightly zero-collection defect fixed (`af3df00`); Release workflow pre-first-run audit PASS (`7d72e34`); nightly py-compat 3.13 matrix verified locally (`9c9adb4`); **Release pipeline local verification 100%** (`7eb0131`: prepare_bundle end-to-end + staged-runtime import + verify_nsis_install.ps1 AST parse). nightly next real trigger: **local 11:17 (03:17 UTC)** — the earlier "skipped tick" observation was a timezone misread (Actions page shows local +08:00 time; cron is UTC; see LOG-161); never-ran fully explained by add-time vs tick timeline (LOG-162).
- Capability Atlas: CAP-0140 (AXW-094) projected `in_progress` (`01ad561`).

- **Nightly made real (LOG-165/166/167)**: manual dispatch before the first
  scheduled tick exposed three genuine gaps, all fixed and re-verified
  (Runs #1-#5: fail → green → green → fail → green): real OCR engine in
  full-suite (`6b395b5`), explicit three-directory collection incl.
  integration-tests (`b99d111`), and browser-smoke upgraded to a real
  Chromium regression that must run inside the venv (`98a0ee6` + `d8db1ad`).
- **Gateplan fail-closed (LOG-168/169/170)**: router.py + browser-smoke
  script classified under ui risk (`a03e27f`); four targeted gates were
  planned but never executed/verified — now carried by the test job and
  checked by ci-verdict (`dfe287c`); all-class profile probe audit PASS.
- **Release pre-audit PASS (LOG-171)**: tag-only workflow audited with the
  nightly gap classes — all release scripts stdlib-only, identity reaches
  the NSIS payload via tauri bundle resources; only real build+install
  remains (Owner tag).
- **H5 acceptance matrix (LOG-172 + `e610c4d`)**: AXW-097 diagnostics now
  assert no secrets/auth/paths anywhere in the response; AXW-096B keyboard
  coverage confirmed (focus trap, aria-live feedback, PDF reader keyboard
  reach); 6/9 tasks ready — 095/060/H5-EXIT remain Owner-gated.
- **CI timeouts + nightly Run 6 (LOG-173)**: timeout-minutes added to all
  ci.yml Python jobs (`24606db`) and all four nightly jobs (`c8a85ce`);
  nightly Run 6 green 3m51s on the timeout build — scheduled tick
  (local 11:17) is a formality.
- **Flaky fix (LOG-174 + `be6c23f`)**: batch shutdown test polled for
  worker start instead of a fixed sleep; product code verified clean.
- **Batch R0 — Final Architecture TaskPack 2026-08-14 (LOG-175/176)**:
  - AXW-REL-001: Nightly Run 7 (schedule) failed `pause 404`; root cause
    chain fixed — pause/resume now lock-protected (no finished→paused
    overwrite hang), ledger appends serialized under a separate
    `_ledger_lock` (concurrent `open("a")` handles corrupted JSONL lines,
    silently dropping events on `from_checkpoint` replay: in-memory 200 vs
    rehydrated 199), `_process_task` catches BaseException (worker never
    dies mid-task silently), test is deterministic (200 files + poll +
    visibility polling + completeness assertions). Evidence: **200/200
    fresh-subprocess loop** (`9b47c00`), full suite 1619 passed,
    **nightly Run 8 green**.
  - AXW-REL-002: release.yml fully dynamic — `Resolve and verify release
    version` step parses the tag, fails on drift across
    pyproject/package.json/tauri.conf.json, and every asset name
    (installer `ArcheAxis.Knowledge-v<ver>-Windows-x64-Setup.exe`, wheel,
    readback) derives from `release_version`; zero hardcoded 0.5.0 remains
    (`0e33aac`).
  - AXW-REL-003: `main-protection` (non_fast_forward + deletion +
    required_status_checks a0-gates) and `tag-protection` (update+deletion
    blocked) rulesets active; admin bypass added because required status
    checks block direct pushes (CI-deadlock) — collaborators/PRs still
    enforced. Ruleset API schema trap documented (nested
    `required_status_checks: [{context}]` + `strict_required_status_checks_policy`).
    Signing decision already recorded (RELEASE_LEDGER).

- **Coverage audits (LOG-163)**: all 51 workspace router endpoints and all
  12 UI data-action handlers now have test references (3 genuine route gaps
  closed in `5fdba13`).
- **Nightly first-run closed (LOG-164/165)**: pre-flight audit of all 4 jobs,
  then a manual `workflow_dispatch` exposed a real gateplan-blind defect —
  full-suite lacked the OCR engine install (tesseract/ffmpeg/fonts) that
  ci.yml's OS-level job has; fixed in `6b395b5`, re-dispatched, **nightly
  Run #2 all-green** (py-compat x2 + full-suite + browser-smoke +
  windows-runtime). Scheduled nightly now expected to succeed at local
  11:17 (UTC 03:17) daily.

## Remaining work (Owner-gated — cannot be done autonomously)

- **H1-H4 EXIT** double-loop adjudication (verification gate; prerequisite for 045/055 acceptance).
- **AXW-045/055**: owner acceptance of implementation layer.
- **AXW-012C**: install-state PDF evidence; **AXW-095**: Windows install state — need user-installed runtime + real NSIS install evidence.
- **AXW-097** release qualification, **AXW-060** v1.0 release package: Release workflow (`v*` tag → main check → exact-SHA CI → NSIS → wheel → checksums → draft release) is ready and audited; execution is Owner.
- **AXW-096A large-vault acceptance**: user data after H4-EXIT.
- **full-qualification**: AXC-060 RC logic profile — only triggers at RC.

## Environment facts (non-negotiable)

- All terminal commands must go through the project-data wrapper:
  `python "C:/Users/ALEX/AppData/Local/hermes/bin/hermes-project-data.py" --project . run -- <single command>`
- Test command: `env -u PYTHONPATH uv run --frozen --group ci --group ci-adapters pytest ...`
- Commits: `git add <specific files>` only; commit messages via `git commit -F <file>`.
- E: drive is protected (exact per-request authorization required). `ceshi`/`Obsidian知识库` are read-only black boxes.
- `.hermes/` holds runtime data only; never commit it. `docs/truth/` logs are tracked.
- Browser-smoke gate triggers only on `app/workspace/ui/**`; script fixes can borrow an index.html comment change to force a real CI run.
- Local chromium cache lives inside the project (ARCHEAXIS_DATA_DIR isolation for browser tests).
- GitHub API unauthenticated rate limit 60/hr — use browser Actions page for CI verification when limited; CI diagnostics via `::error::` workflow annotations.

## Boundaries

- Do not access or modify E: without a new exact user authorization.
- ArcheAxis and WORK-LAB are fully independent repos; do not cross-wire.
- Do not touch the frozen advisory branch worktree (`.hermes/task-runtime/frozen-rd`, append-only).
- Review and gate a frozen staged tree. Report CI only for its exact commit SHA.
- Credentials are never committed or printed ([REDACTED]).
