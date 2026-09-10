# R14 audit evidence index (0910 pack) — pointer file

**The authoritative index is [`R14-EVIDENCE-INDEX.json`](R14-EVIDENCE-INDEX.json)**,
checked by `scripts/check_evidence_index.py` (14 tests). This markdown file keeps the
environment notes and the reproduction recipe; the per-slice tables it used to carry
stopped at R05 and would now contradict the live record, so they were removed rather
than left to rot. `EXECUTION.md` and `STATE.json` remain the live record and this pair
adds no authority of its own.

## What the JSON index promises, and what the checker enforces

| Rule | Why it exists |
| --- | --- |
| All 17 slices present, each status equal to `STATE.json` | two files may not contradict each other about what is done |
| Every slice cites at least one **tracked** artifact | a claim that rests only on an ignored local receipt cannot be re-checked from a fresh checkout |
| Every cited tracked path exists; receipts are marked and live under `.project-local/` | a pointer that does not resolve is not evidence |
| Every slice names a runnable command, and the script it names exists | an auditor must be able to re-run the check, not just read about it |
| Every slice records at least one limitation | a slice whose boundary nobody wrote down is a slice nobody bounded |
| R14 and R16 may only be `TODO` or `BLOCKED_EXTERNAL`, and must name an independent auditor | the repository never signs its own audit gate |

Current result: 17 slices, 49 tracked evidence pointers, 3 local receipts, all statuses
agreeing with `STATE.json`, no self-signed gate, every slice stating its limits.

## 0. Baseline and package

| Item | Value |
| --- | --- |
| Branch | `codex/full-loop-0906` (local == origin) |
| `main` | `4ca46ea` (untouched) |
| Live plan entry | `docs/authority/taskpack-0910-r3/EXECUTION.md`, progress in `STATE.json` |
| Supersession | SUP-018 in `DECISION_SUPERSESSION_LEDGER.yaml` |
| Package install | single level, with `reference-r2/` |
| Package verification | `python -X utf8 scripts/check_taskpack_integrity.py` — 21 frozen pack files match their recorded hashes, the two live progress files match the install snapshot and grew as expected, plan intact |

The shipped `verify_package.py` **cannot** pass once work is recorded: two of its 23
manifest entries are `EXECUTION.md` and `STATE.json`, which the pack itself designates
as the files progress is written into. That is why the integrity checker splits the
question in two, and why its failure on those two files is not corruption. It must run
in UTF-8 mode on this machine (GBK locale).

## 1. Reproduce

| Suites | Command |
| --- | --- |
| Rust workspace and per-crate suites | `scripts/ci/cargo_test.bat` (no arguments: `test --workspace --offline`); per crate: `scripts/ci/cargo_test.bat -p archeaxis-application --offline` |
| Python suite | `python -B scripts/runtime/dev.py --pytest <paths>` or `pwsh -File scripts/ci/run_tests.ps1 --full` |
| Repository gates | `python -X utf8 scripts/check_repository_conventions.py --source worktree`, `python -X utf8 scripts/check_architecture.py` |
| This pack's own gates | `python -X utf8 scripts/check_taskpack_integrity.py`, `scripts/check_language_boundaries.py`, `scripts/check_format_matrix.py`, `scripts/check_path_conventions.py`, `scripts/check_evidence_index.py` |

`scripts/ci/cargo_test.bat` is the tracked Rust entry point: the per-run wrappers under
`.project-local/runs/` are generated and ignored, so before it existed a fresh checkout
had no way to run the Rust suites. It reads `ARCHEAXIS_MSVC_VCVARS`,
`ARCHEAXIS_RUST_TOOLCHAINS`, `ARCHEAXIS_PYTHON` and `ARCHEAXIS_CARGO_TARGET_DIR`, pins
the target directory to `.project-local/build/cargo`, and fails with a named message
(exit 2) when the toolchain cannot be found instead of proceeding quietly.

## 2. Known deviations and environment notes (do not re-diagnose)

1. Tesseract cannot open a `\\?\`-prefixed path; the transport strips the prefix.
2. The Core reads its launch claim to EOF: a caller that keeps stdin open waits forever.
3. A worktree under the repo inherits the main `.cargo/config.toml` target directory;
   `scripts/ci/cargo_test.bat` pins `CARGO_TARGET_DIR` for this reason.
4. py-fsrs fuzzes intervals by default; the worker requests `enable_fuzzing=False`.
5. The two frozen package files lack a final LF, so the convention gate always reports
   exactly those two lines; patching them would break the package's own manifest hashes.
6. `STATE.json` must stay ASCII-escaped: locale-default readers (GBK here) fail otherwise.
7. A pytest run started directly (not through `dev.py`) misses `ARCHEAXIS_RUN_ROOT`, and
   the vocabulary tests then fail with `KeyError` — that is the environment, not a defect.
8. Reading a cargo exit code through a PowerShell pipeline that merges stderr reports a
   failure that is not there; redirect to a log and read the file.
9. PowerShell `-match` is case-insensitive, so a "failed" pattern also matches "0 failed".
10. Multi-line text edits belong to the edit tool: PowerShell string literals mangle
    backticks and line endings (this has already cost one corrupted file).

## 3. What this index does not claim

- No slice has been independently audited: R14 and R16 are decided outside this
  repository, by an auditor the owner configures.
- Nothing here is a product certificate. The index points at evidence; it does not weigh
  it, and a passing gate proves only the mechanical rules above.
- The format matrix records **zero** complete groups: five partial and eleven custody-only.
- 69 tracked paths have no directory-authority rule and are recorded, not fixed, because
  the authority file is protected.
- All 1246 inventoried legacy assets are still `INVENTORIED_NOT_SEMANTICALLY_REVIEWED`.
- No capacity has been reclaimed: the cleanup manifest lists candidates and deletes
  nothing.
