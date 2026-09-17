# Branch disposition evidence — 2026-09-18

## Verified baseline

- PR #149 merged `codex/main-convergence-20260917` into `main`.
- Merge commit: `a399576c4d2b4792143298a9d425d10b1e8609a8`.
- `origin/main` was read back at the same SHA after `git fetch origin --prune`.
- PR checks for head `ccd43e291a2a94c05601b9dc60f98ed6aa934c2c` passed, including `installer-lifecycle` run `35246039796`.

## Deleted after absorption review

The following remote branches were deleted individually after the read-only disposition audit found their tips absorbed by the merged mainline or by the merged convergence line:

- `codex/append-only-audit`
- `codex/client-write-boundary`
- `codex/evidence-bundle-version`
- `codex/first-run-setup`
- `codex/inspector-activity-closure`
- `codex/pipeline-green-hotfix`
- `codex/raw-first-web`
- `codex/release-candidate-promotion`
- `codex/v0.6.0-integration`
- `codex/full-loop-0906`

`git push origin --delete` returned `[deleted]` for the first five; the remaining five were already absent by the second deletion pass and were confirmed absent by `git fetch origin --prune` and the GitHub branch listing.

## Retained

`main`, `codex/main-convergence-20260917`, and branches with post-merge unique commits, closed/unmerged history, or unresolved capability/document residuals remain. They require separate owner-level review before deletion.

## Not claimed

This evidence covers branch disposition only. It does not mark R5 R10/R12/R13/R14/R15/R16 complete; those remain in the live R5 state as partial or blocked until their independent acceptance evidence exists.


## Later update

The convergence branch was deleted after full qualification run 35253371026; remote branch count is now 21.

## Superseded branches removed — 2026-09-18

After the post-merge audit, these explicitly `SUPERSEDED` branches were deleted because their contents are represented by current mainline or retained historical records:

- `docs/naming-full-sweep`
- `feat/naming-v2-full-sweep`
- `fix/osui-final-newline`

Remote branch count after deletion: 18.
