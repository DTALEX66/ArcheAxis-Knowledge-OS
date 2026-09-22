# Repository Drift Current Receipt — 2026-09-23

Status: `CURRENT READBACK / PARTIAL / NO_DELETE / NO_MERGE`

This receipt supersedes the *current-fact* portions of
`DOCUMENTATION-DRIFT-AUDIT-20260923.md`. That earlier file is retained as a
dated audit snapshot and is not current Git truth.

## Exact Git readback

| Field | Current value |
| --- | --- |
| branch | `codex/aaos-p3-ui-convergence-20260922` |
| HEAD | `974322a6b20e48b064db294f52fe9121833631c3` |
| origin/main (local ref) | `e3875db0ee6d073d37839eb7b95f7ef4ce881bbb` |
| origin/feature (local ref) | `974322a6b20e48b064db294f52fe9121833631c3` |
| `origin/main...HEAD` | `0 13` |
| live `git ls-remote` | `UNVERIFIED`: local SSH `known_hosts` permission prevented readback; no bypass or ACL change |
| worktree | dirty with pre-existing user changes and protected untracked history assets |

The 13 commits unique to the current feature branch are all frontend/UI
delivery or its receipts. No commit was merged into `main`.

## Authority relationship

The current execution chain is:

`AGENTS.md` → `docs/CONFIGURATION_AUTHORITY_INDEX.md` →
`PROJECT_CONTRACT.yaml` / `DECISION_SUPERSESSION_LEDGER.yaml` →
`docs/authority/taskpack-0919-r6/` →
`docs/current/M0-DIRECTION-OVERRIDE-20260920.md` →
`docs/current/R6-EXECUTION.md` / `R6-STATE.json` → path, language, runtime and
verification indexes.

`TASKS.json` is the immutable R6 plan baseline. `R6-STATE.json` is the mutable
execution sidecar. They must not be compared as if they were the same state
store. The current `R6-STATE.json` is dirty, has an older `updated_at`, and is
not modified by this receipt; owner-gated state remains owner-gated.

## Confirmed drift candidates

- `DOCUMENTATION-DRIFT-AUDIT-20260923.md`: freeze as an audit-time snapshot;
  do not use its old HEAD/branch counts as current truth.
- `REPOSITORY-CLEANUP-HANDOFF-20260921.md`: retain as historical handoff;
  its exact 28-path cleanup receipt and `8,361,939,708` reclaimed bytes remain
  evidence, but its Git state is not current.
- `SESSION-RESTART-2026-09-12.md`, `docs/history/**`, R5/R3/R2 TaskPack
  originals and historical receipts: preserve; do not delete, move or commit.
- Older `docs/current` R2/R3/R5/Hermes handoffs and summaries: candidate
  freeze/redirect items, not deletion candidates without path/hash/reference
  manifests.
- `R6-STATE.json`: current-sidecar freshness/owner-gate issue; do not overwrite
  the user's dirty file in this audit.

## Branch disposition readback

The current feature branch is `0 behind / 13 ahead` of `origin/main` and is the
active delivery candidate. `codex/worker-quality-0906` is an ancestor of
`origin/main` but is still associated with a registered worktree; it is not a
delete-now candidate. Other local branches have unique commits and are mostly
hundreds or thousands of commits behind `origin/main`; none is safe to merge or
delete by age alone. Remote branch deletion, merge, or bundle creation requires
a separate exact-branch owner decision.

## External and generated-data boundary

The fixed external roots remain governed only by
`docs/SHARED_RESOURCE_PATH_INDEX.md`:

- `D:\All projects\Model library`
- `D:\All projects\OS External Configuration`
- `D:\All projects\ArcheAxis.Knowledge.Green-x64`
- `D:\All projects\资料库`
- `D:\All projects\ceshi`

The AAOS UI suite is a design reference source, not a runtime resource root.
Its paths in UI documents do not imply copying, integration or authority.
No external root, Green directory or protected history content was scanned or
modified in this receipt.

`.project-local/build`, `.project-local/runs`, caches, task runtime and
registered worktrees require a path → size → mtime → generator/commit →
reference → owner-decision manifest before any deletion. No top-level
`.project-local` deletion is authorized by this receipt.

## Next controlled actions

1. Add this receipt to the documentation authority navigation without changing
   the immutable TaskPack.
2. Freeze stale current-path documents with top banners and links to this
   receipt, preserving their original bytes and evidence.
3. Generate the exact path/hash/size/reference manifest for project-local
   cleanup candidates; classify retained evidence, reproducible cache and
   unresolved runtime state.
4. Produce a per-branch unique-commit disposition table; merge or delete only
   after owner approval and exact readback.
5. Re-run canonical authority/path gates with the project-local pytest-capable
   interpreter. Missing or blocked gates remain `NOT EXECUTED`, not PASS.
