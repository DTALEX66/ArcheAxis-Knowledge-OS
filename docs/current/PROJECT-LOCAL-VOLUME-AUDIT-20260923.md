# Project-local Volume Audit — 2026-09-23

Status: `READ_ONLY / NO_DELETE`

The following sizes were read from the current repository's `.project-local`
root using native PowerShell recursive file metadata. This is a volume and
ownership classification, not deletion authorization.

| Path | Bytes | Initial classification | Action |
| --- | ---: | --- | --- |
| `.project-local/build` | 27,672,545,916 | build candidates and runtime artifacts | manifest by candidate/SHA before cleanup |
| `.project-local/runs` | 4,393,970,738 | mixed receipts/logs/runtime outputs | retain referenced evidence; classify each run |
| `.project-local/cache` | 2,753,138,980 | rebuildable cache candidate | verify active consumers, then exact-path cleanup |
| `.project-local/worktrees` | 84,606,028 | registered worktrees | inspect `git worktree list --porcelain`; never bulk-delete |
| `.project-local/deeptutor-val` | 82,610,112 | validation/runtime candidate | identify receipt references and owner |
| `.project-local/task-runtime` | 49,713,127 | task state/runtime | preserve until task receipts close |
| `.project-local/dist` | 11,025,490 | generated distribution output | map to build command and current SHA |
| `.project-local/ui-audit` | 7,976,008 | UI audit artifacts | retain until visual audit closes |
| `.project-local/gh-cache` | 2,289,377 | GitHub metadata cache | verify no evidence-only references |
| `.project-local/audits` | 1,147,130 | audit receipts | retain |

Top candidates total approximately 34.8 GB, dominated by build outputs,
runs and cache. No external path was scanned. No Green, model library, real
data library, test library, E/F drive, history asset or credential was read.

## Required manifest before cleanup

For every proposed path, record:

`relative path → byte size → mtime → file hash or deterministic directory
manifest → generator command → source/HEAD SHA → document references → active
process/worktree check → owner decision → post-delete absence check`.

The 2026-09-21 cleanup receipt remains the only completed cleanup evidence for
its exact 28 paths and `8,361,939,708` bytes. This audit does not extend that
authorization. In particular, no `.project-local` top-level directory, build
candidate, run, cache, task runtime or registered worktree may be removed from
this receipt alone.
