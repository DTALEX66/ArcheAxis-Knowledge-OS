# AAOS Cloud Branch Reconciliation — 2026-10-02

Read-only. Nothing was merged, rebased, reset or deleted.

## The three October pull requests

| PR | Title | Base | Head | SHA | Draft |
| --- | --- | --- | --- | --- | --- |
| #156 | Advance AAOS desktop UI fidelity and Core capture readback | `main` | `codex/aaos-ui-phase2-20261001` | `1a981a44` | True |
| #157 | Measure production multiformat reachability, fix launcher cr | `codex/Audit` | `codex/dsh-aaos-real-multiformat-loop-20261001` | `dc848e13` | True |
| #158 | Add the cosmic UI layer: backdrop, glass shell and honest pl | `codex/Audit` | `codex/minimax-aaos-cosmic-ui-20261001` | `627e74ff` | True |

## Topology, measured

| Branch | SHA | ahead of main | behind main | merged | local = remote |
| --- | --- | ---: | ---: | --- | --- |
| `main` | `59498723` | 0 | 0 | True | True |
| `codex/Audit` | `1a981a44` | 18 | 0 | False | True |
| `codex/aaos-ui-phase2-20261001` | `1a981a44` | 18 | 0 | False | True |
| `codex/dsh-aaos-real-multiformat-loop-20261001` | `dc848e13` | 97 | 0 | False | True |
| `codex/minimax-aaos-cosmic-ui-20261001` | `627e74ff` | 20 | 0 | False | True |

`codex/Audit` is **18 commits ahead of main and 0 behind**, so it is the newer line and main holds
nothing Audit lacks. `codex/aaos-ui-phase2-20261001` is the **same commit** as `codex/Audit`, which
is why PR #156 and PR #157/#158 describe one body of work from two directions.

## The merge-order problem

PR #156 targets `main`; PR #157 and PR #158 target `codex/Audit`. They are not on one line.

* #156 carries main from `59498723` up to `1a981a44`, which is codex/Audit's own baseline.
* #157 adds 76 files on top of `1a981a44`.
* #158 adds 14 files on top of `1a981a44` — and **both #157 and #158 touch
  `apps/ArcheAxis.Desktop` and the six UI contract tests**, so whichever lands second must be
  re-checked for conflicts rather than assumed clean.

**Recommended order: #156 → #157 → #158.** Merging #157 or #158 first would advance codex/Audit and
leave #156 needing a rebase.

## What each carries

| PR | Content | Scale |
| --- | --- | --- |
| #156 | October Authority/Task Ledger/UI baseline integration | 60 files, +8101/−1794, 16 under `apps/` |
| #157 | production multiformat loop: PDF/OCR/ASR/media workers, Source→Transform→Knowledge, the HTTP contract, acceptance runbook, P0–P6 evidence, Rust 100/100 targets, Python 3679 passed | 76 files, +11977/−234 |
| #158 | Avalonia cosmic UI: DeepSpace theme, backdrop, navigation, honest unavailable states, accessibility | 14 files, +365/−96 |

## What was not touched

No `git reset --hard`, no `git clean`, no batch overwrite, no worktree removed, no Green
overwrite, no branch created or moved. All five remote branches match their local refs.
