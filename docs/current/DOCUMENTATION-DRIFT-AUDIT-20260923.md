# Documentation, Path, Output and Branch Drift Audit — 2026-09-23

## Scope

This is a current readback and disposition receipt for the AAOS repository. It
covers authority entry points, current/history/handoff/summary documents, fixed
external-resource indexes, generated output spill, and local/remote Git refs.
It does not authorize access to `E:\`, `F:\`, credentials, private agent state,
Green user data, real资料库 contents, shared model contents, or shared tool
contents.

## Current truth readback

| Field | Readback |
|---|---|
| branch | `codex/aaos-p3-ui-convergence-20260922` |
| HEAD | `4525564bc11be0eb6a88ecb780d882810201a57b` |
| upstream branch | `origin/codex/aaos-p3-ui-convergence-20260922` |
| origin/main | `e3875db0ee6d073d37839eb7b95f7ef4ce881bbb` |
| HEAD...origin/main | `1 0` |
| working tree | dirty; includes pre-existing conversion/workspace/test changes, P3 UI changes, authority repairs, and protected untracked history assets |
| remote readback | SSH `git ls-remote` was blocked by local `known_hosts` permission; local remote-tracking refs are not a substitute for live GitHub readback |

The 2026-09-20 M0 baseline remains a dated snapshot. Its live-readback section
now points readers to this current branch/HEAD record.

The current feature branch is synchronized with its own remote-tracking branch
(`0 0`) and is one commit ahead of `origin/main` (`0 1` in
`origin/main...HEAD`): `4525564b feat(desktop): converge AAOS P3 UI shell`.
Other local branches are historical or substantially behind `origin/main`; no
automatic merge or deletion is safe while this worktree is dirty.

### Post-audit delivery readback

The scoped P3 and authority repair files were committed as
`20966cb0e68c4abbc40feab275a0d2fbf7ddcb05` and pushed to
`origin/codex/aaos-p3-ui-convergence-20260922`. Live remote readback returned
the same SHA and `HEAD...origin/codex/aaos-p3-ui-convergence-20260922 = 0 0`.
After that delivery, the feature branch is two commits ahead of `origin/main`;
`main` remains untouched.

## Authority disposition

### Current active chain

1. `AGENTS.md`
2. `PROJECT_CONTRACT.yaml` and `DECISION_SUPERSESSION_LEDGER.yaml`
3. `docs/CONFIGURATION_AUTHORITY_INDEX.md`
4. `docs/authority/taskpack-0919-r6/EXECUTOR-START.md`, `TASKPACK.md`, `TASKS.json`
5. `docs/current/M0-DIRECTION-OVERRIDE-20260920.md`
6. `docs/current/R6-EXECUTION.md` and `R6-STATE.json`
7. `docs/SHARED_RESOURCE_PATH_INDEX.md`, `DIRECTORY_AUTHORITY_INDEX.md`,
   `LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md`, `RUNTIME_DELIVERY_AUTHORITY_INDEX.md`

The default task-pack resolver now points to `taskpack-0919-r6`; explicitly
selected R5/R3/R2 packs remain historical and are not deleted.

### Frozen historical / superseded material

- Dated v0.6.x, R2/R3/R5 current-path records retain evidence but are not live
  authority. Existing banners in the four previously identified current-path
  documents remain required.
- Root `HANDOFF_*` and `SUMMARY_*` records remain historical until a path/hash/
  reference manifest permits relocation. They are not execution instructions.
- `docs/history/**` and `SESSION-RESTART-2026-09-12.md` are protected untracked
  user/history assets; no deletion, move, or commit was performed.

### Repaired drift

- `LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md` no longer names R5 as the active ledger.
- `RUNTIME_DELIVERY_AUTHORITY_INDEX.md` now points to R6/M0 for current execution.
- `DIRECTORY_AUTHORITY_INDEX.md` no longer presents R5 path disposition as the
  current ownership authority.
- `SHARED_RESOURCE_PATH_INDEX.md` no longer points its “current” links at the
  0906 legacy handoff.
- `PROJECT_STATUS.md` is explicitly historical/superseded.
- `scripts/taskpack_paths.py` and low-quota handoff paths now default to R6/M0.
- `AGENTS.md` no longer describes R5 as the current first-use execution slice.
- `README.md` now routes current readers to the R6/M0 authority chain and labels
  React/Tauri/R5 release language as compatibility/history context.
- `workspace/intake/2026-09-15-monitoring-audit-followup.md` is explicitly a
  superseded R5 intake sidecar; its old current-authority sentence is frozen as
  historical context.

## Output and volume disposition

- The 2026-09-21 cleanup receipt remains authoritative for its 28 exact deleted
  regenerable paths and `8,361,939,708` reclaimed bytes.
- Current `.project-local/build/green-candidates/` retains two named candidates;
  neither is Green user data. No further candidate deletion is authorized by
  this receipt without a new exact-path manifest.
- `.project-local/runs/` contains evidence and runtime outputs with mixed ages;
  it is not safe to bulk-delete. A follow-up inventory must classify each path
  as retained evidence, reproducible cache, or unresolved before deletion.
- `.project-local` generated outputs are intentionally not Git-tracked. Their
  presence is not evidence of external spill. Static output-path scans must be
  distinguished from actual runtime writes.
- No external root was scanned for content or modified.

Static repository references also mention historical or non-indexed paths such
as `D:\All projects\UI套件` and `D:\All projects\Record`. These are document
references only in this audit; they were not accessed or promoted to resource
authority. The five fixed external roots remain governed solely by
`SHARED_RESOURCE_PATH_INDEX.md`.

## Branch disposition

The current feature branch has one local commit beyond `origin/main` and is
already present as a remote-tracking branch. No merge, rebase, force-push, or
branch deletion was performed. Branches can only be merged after a separate
exact-SHA review identifies their unique commits and confirms they do not
contain superseded release/UI paths or unrelated dirty work.

## Remaining controlled work

1. Re-run the authority/path/static gates with a pytest-capable approved
   interpreter; missing pytest is `NOT_EXECUTED`, not PASS.
2. Produce a branch disposition table with merge candidates, unique commits,
   protected branches, and stale/deletable refs.
3. Produce an AX-DIR-010 path/hash/reference manifest for any document move or
   deletion. Do not mass-delete history or `.project-local/runs`.
4. After review, remove only exact regenerable outputs with a postcondition and
   a new cleanup receipt.

Status: `PARTIAL / AUDITED_LOCAL / NO_BULK_DELETE / NO_MERGE`.
