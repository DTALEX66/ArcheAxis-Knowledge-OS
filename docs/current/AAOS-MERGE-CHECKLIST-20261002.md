# AAOS merge checklist — 2026-10-02

Read from the live repository, not from memory. **Merging is the Owner's act**; this is preparation.

## The defect this exists for

`main` is exactly PR #155's merge commit (`59498723`), and #155 merged `codex/Audit` at
`6621aab7`. **Audit then advanced 18 commits to `1a981a44` and no second pull request was ever
opened.**

So #156, #157 and #158 all sit on or above those 18 commits:

| | base | head | what merging it actually does |
| --- | --- | --- | --- |
| #156 | `main` | `1a981a44` | moves main to `1a981a44` |
| #157 | `codex/Audit` | `6eeb62f8` | lands on Audit, **not on main** |
| #158 | `codex/Audit` | `627e74ff` | lands on Audit, **not on main** |

Merging them by their own bases therefore puts **nothing** on the product line. Everything built
here — the capability registry, the cited Ask, the machine answer, the human correction, the
published contract — is unreachable from `main` until that is fixed.

## The order

### 1. Merge #156 into main

```bash
gh pr merge 156 --merge
```

Brings main from `59498723` to `1a981a44`, which is the base everything else sits on.

Verify: `gh pr view 156 --json state,mergeCommit`, then `git fetch origin && git rev-parse
origin/main`, then `gh run list --branch main --limit 1` for a successful CI run **on the new main**.

Rollback: `git push origin 59498723a8d4e94c6314e490473ba6d60847c247:main`.

### 2. Retarget #157 to main, then merge

```bash
gh pr edit 157 --base main && gh pr merge 157 --merge
```

Verify: `gh pr view 157 --json baseRefName,mergeStateStatus` must read `main` and `CLEAN` **before**
merging, then `gh run list --limit 1` for exact-SHA CI.

**Retargeting changes the merge base, so the previous green run no longer covers it.** A green run
against `codex/Audit` says nothing about main.

Rollback: `git revert -m 1 <merge-commit>` — a merge commit is reverted, not reset.

### 3. Retarget #158 to main, then merge

```bash
gh pr edit 158 --base main && gh pr merge 158 --merge
```

Measured: #157 and #158 share **zero files** (119 and 14 files
respectively against their shared base). No conflict re-check is needed between them.

Rollback: `git revert -m 1 <merge-commit>`.

## Do not

* **`git reset --hard` on main.** It would discard the merge commits, and it is the one action the
  taskpack names as forbidden.
* **Merge #157 or #158 without retargeting.** They would land on `codex/Audit` and leave main
  untouched, which is the defect being fixed.
* **Merge on the strength of the earlier green run.** Retargeting moves the merge base.

## Boundary

**Merging is not releasing.** Release stays `FROZEN` until G0–G5, the Independent Audit and the Owner
Gate are complete.
