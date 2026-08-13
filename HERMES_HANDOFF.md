# Hermes handoff — archeaxis-workspace

Generated: 2026-08-14 (replaced stale 2026-07-23 copy)

## Current continuation point

- Repository: `D:\All projects\ArcheAxis-Knowledge-OS` (canonical, single writer: Hermes)
- Branch: `main` — HEAD and origin in sync (verify with `git status --short --branch` before resuming)
- Cloud: `https://github.com/DTALEX66/ArcheAxis-Knowledge-OS` (push via 127.0.0.1:7890 proxy; api.github.com direct)
- Baseline: AXC TaskPack 2026-08-13 (AXC-000~150 v1.1). Full suite: **1532 passed / 9 skipped**; ruff + repository-conventions gate green on head.

## Frozen-baseline execution state (LOG-147..159 in `docs/truth/EXECUTION_STATUS_LOG.md`)

Implemented and CI-verified (continuous green: CI runs 524-542):

- **AXW-022B**: PDF evidence annotation reachable (text-layer overlay + cached selection); real browser-smoke first ran on CI at `85b3311` (run 31732780580).
- **H5 implementation layer** (`5dc3d9b` + `d129aa3`): AXW-094A open-exchange export (`app/exchange/export.py`), AXW-094B verifiable backup (`app/exchange/backup.py`), AXW-096A performance benchmark (`shared/performance_benchmark.py`), AXW-096B keyboard accessibility (UI), AXW-096C batch import control (`app/ingestion/batch_controller.py`). EXIT is a verification gate, not an implementation prerequisite (precedent 023A-F/043B/050A).
- **AXW-096A real data**: layered zh/en public-domain corpus (Gutenberg, sources.json provenance, corpus NOT committed) + real benchmark PASS (`01ad561`); toolchain `scripts/prepare_benchmark_corpus.py` / `scripts/run_performance_benchmark.py`; report `docs/truth/PERFORMANCE_BENCHMARK_096A.md`.
- **Workspace API surface** (`81df63b`): exchange export/verify, backup create/verify/restore(dry-run), batch import/status — error semantics explicit (400/404/409/422).
- **User-facing UI entry** (`892b87b`): Evidence page 开放交换与备份 card — four reachable buttons (export/verify/backup create/verify) with API round-trip asserted in browser-smoke (`#evidence` hash route).
- **Async batch control** (`8ea9a05` + `976bf13` + `6011b81`): pause/resume/shutdown on a live registry; ledger task-list recovery + terminal-state restoration (from_checkpoint) — interrupted batches are resumable, totals honest; duplicate-active rejected 409 (covered).
- **CI ecosystem audit**: nightly zero-collection defect fixed (`af3df00`); Release workflow pre-first-run audit PASS (`7d72e34`); nightly py-compat 3.13 matrix verified locally (`9c9adb4`); **Release pipeline local verification 100%** (`7eb0131`: prepare_bundle end-to-end + staged-runtime import + verify_nsis_install.ps1 AST parse). nightly next real trigger: **local 11:17 (03:17 UTC)** — the earlier "skipped tick" observation was a timezone misread (Actions page shows local +08:00 time; cron is UTC; see LOG-161).
- Capability Atlas: CAP-0140 (AXW-094) projected `in_progress` (`01ad561`).

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
