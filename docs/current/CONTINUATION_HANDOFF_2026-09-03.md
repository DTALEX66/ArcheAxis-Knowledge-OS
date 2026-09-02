# ArcheAxis Knowledge — Continuation Handoff (2026-09-03)

## Purpose and non-negotiable boundaries

Continue the existing `v0.6.14` maintenance work; do **not** create a version,
tag, installer or GitHub Release. Fix and maintain only the existing Green
distribution at `D:/All projects/ArcheAxis.Knowledge.Green-x64`. Do not inspect,
copy, change, clear, rename or delete its `data/` directory. Do not access
`E:/`. Keep project-generated evidence under ignored root `.hermes/`.

The canonical product is root `frontend/` plus root `src-tauri/`; `desktop/`
is a separate recovery compatibility shell. The silent Green GUI launcher is
`启动星环知识.vbs`; neither its VBS path nor browser testing should expose a
terminal window.

## Read first

1. [Documentation authority index](../DOCUMENTATION_AUTHORITY_INDEX.md)
2. [Repository normalization state](REPOSITORY_NORMALIZATION_STATE_2026-09-03.md)
3. [Current Reality](CURRENT_REALITY_2026-09-01.md)
4. [Runtime and delivery authority](../RUNTIME_DELIVERY_AUTHORITY_INDEX.md)
5. [Language boundary authority](../LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md)
6. [G0 evidence-gap register](AXM_G0_EVIDENCE_GAP_REGISTER_2026-09-03.md)

## Verified state at handoff

| Layer | Fact | Status |
| --- | --- | --- |
| Local Git base | `main@db13d0564ac2971d4b1eb3e3a5bff9c9256af313` | Read back |
| Cloud `origin/main` | `db13d0564ac2971d4b1eb3e3a5bff9c9256af313` via 2026-09-03 `git ls-remote` | Read back; base equals cloud, working tree does not |
| Working tree | 72 tracked modifications and 48 untracked paths when the cleanup inventory began; mixed ownership | Do not mass-stage, commit or push |
| Full local Python gate | `2163 passed, 5 skipped, 3 warnings` in 99.82 seconds, current working tree | `TESTED_LOCAL`; not cloud CI |
| Historical exact-SHA cloud CI | CI `33521144084` on `db13d056` passed selected fast gates; nightly `33605765393` failed full-suite and skipped downstream browser/Windows jobs | `G0-001 OPEN` |
| Frontend theme | Offline black/white dark tokens, no Google Fonts, fixed command palette modal, reduced-motion branch; Vitest `119 passed`, Vite build passed, silent in-app browser interaction read back | `TESTED_LOCAL/BUILT_LOCAL` |
| Green main EXE | Candidate and Green target SHA-256 `132f1c8ccc5344cd8b709826b79c59ba01cf59b919073fd36a67ec249c5a0538`; old EXE hash-backed-up at `backups/inplace-main-shell-20260903-monochrome/ArcheAxis.exe` | `DEPLOYED_HASH_VERIFIED`, not visible runtime verification |

## Completed in this working tree

- Repaired current nightly contract: lock-bound frontend install in browser
  smoke; PowerShell-native Windows environment cleanup, migration and HTTP
  smoke. The historical nightly result remains unchanged until new code is
  committed, pushed and run.
- Stabilized multi-format web screenshot handling so an Edge parent `0` exit
  cannot report success before its child writes a non-empty PNG; it still fails
  closed after the bounded wait.
- Preserved raw-first behavior in test fixtures without weakening production
  SafeHTTP, and exercised the current all-suite locally.
- Added authority indexes for documentation, directories, language boundaries
  and runtime delivery. Added a current normalization state linked from all
  three governance indexes and regression-tested those references (`10 passed`).
- Removed exactly two old `.playwright-cli/` session files (3,799 bytes) after
  content/count verification; `.playwright-cli/` is now ignored as
  `TRANSIENT_AUTOMATION`. Did not broadly clean `.hermes/` or the 5.56 GB Rust
  target cache, because they contain worktrees/runtime assets or accelerate
  builds.
- Built the root Tauri primary shell using the shared toolchain and replaced
  only the Green `ArcheAxis.exe`. No Green data was touched and no new release
  was produced.

## Next sequence — keep one evidence layer per claim

1. **Ownership inventory before publication.** Classify every changed path as
   owned current work, an earlier user change, generated output, or unknown.
   Review diff and dependency/test relation for each owned batch. Never run
   `git add .`.
2. **Make a focused maintenance commit.** Include only the reviewed batch and
   its matching tests/docs. Re-read `HEAD` and `origin/main`; push normally
   only after the scoped diff passes its relevant checks.
3. **Exact-SHA CI.** Manually dispatch the full qualification against the
   pushed SHA, then read back `full-suite`, `browser-smoke` and
   `windows-runtime`. Do not call G0-001 closed because a local suite passed.
4. **Green product-path verification.** When it can be done without interfering
   with a user instance, launch only through the silent VBS path and record the
   executable process path plus visible product result. Do not use desktop GUI
   automation or treat a static fallback page as evidence.
5. **G0 language route.** Preserve Python as the sole writer. Close corpus,
   writer/consumer and rejected-write evidence, then add one Rust read-only
   differential report. No dual writer or directory-move proxy.
6. **Directory convergence.** Use AX-DIR-010 rows with consumer scan, rollback
   and explicit deletion authorization; Green data, external tool/model
   libraries, compatibility shell and historical records remain protected.

## Publication guardrail

There is no safe claim that the current local tree equals cloud: only its base
commit equals cloud. Publication remains intentionally pending because a mixed
dirty tree cannot be safely attributed as one change. A future completed claim
must name the commit, remote SHA, exact CI run/SHA, Green hash and visible
runtime result separately.
