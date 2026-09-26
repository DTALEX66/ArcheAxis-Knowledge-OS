# AAOS Local Repository and Data-Lineage Readback — 2026-09-25

> **Snapshot precedence (2026-09-26):** This is an append-only chain of dated observations, not one timeless status. The original capture note immediately below applies only to its first 2026-09-25 snapshot. Later sections supersede earlier statements only for the facts they re-read; use `Current branch, DSH and spill recheck — 2026-09-26` and `Same-day follow-up — 2026-09-26 06:40 UTC` for the latest recorded remote, branch, DSH and spill facts. Historical measurements and their limitations remain preserved.

> **Evidence class: read-only local snapshot.** This receipt records local Git
> refs, registered worktrees and `.project-local/` top-level names only. It did
> not read `.project-local` file contents, inspect external resource roots,
> contact remotes, or authorize merge, branch deletion, data movement or cleanup.
> Counts are point-in-time; re-read before any operation.

## Live local Git snapshot

- Worktree: `D:\All projects\ArcheAxis-Knowledge-OS`
- Branch: `codex/aaos-p3-ui-convergence-20260922`
- `HEAD`: `a5de4b13474c217e7a9dd34b8cbfa402e8297780`
- Cached `refs/remotes/origin/main`: `e3875db0ee6d073d37839eb7b95f7ef4ce881bbb`
- Cached local comparison `origin/main...HEAD`: `0 166` (no left-only commits,
  166 HEAD-side commits). This is not live remote verification.
- Root `git status --short --untracked-files=all` at capture: **1,048 entries**,
  comprising 54 tracked status entries and 994 untracked entries. Tracked
  modifications span workflow/config, Desktop, Rust Core, current docs, tests
  and audit/history records. Most untracked entries are under `docs/history/`.
  A browser-profile-shaped subtree appears under
  `docs/history/task-artifacts/web-chain-debug/profile/`; names suggest
  potentially sensitive browser state. Contents were not read. Classify it as
  `UNRESOLVED_POTENTIALLY_SENSITIVE / PRESERVE`; do not stage, archive, migrate
  or delete pending owner/path/content classification through an approved
  narrow process.

The root status was measured immediately before this receipt was created, so
the receipt itself adds one untracked file after the captured count. The other
pre-existing untracked material remains unattributed; path presence does not
establish ownership.

### Metadata-only untracked-path follow-up

After creating this receipt, `git status --short --untracked-files=all` read
1,049 entries (54 tracked status entries and 995 untracked). A path-only
`git -c core.quotePath=false ls-files --others --exclude-standard` grouping
places 991 untracked files under `docs/`, 3 under `apps/`, and 1 under
`crates/`; **989 of the 995 untracked files are under `docs/history/`**. The
largest history extension groups are no extension (631), `.md` (81), `.py`
(67), `.log` (57), `.json` (44), `.png` (39), `.zip` (11), `.db-journal` (9),
`.patch` (9), `.dat` (6), `.docx` (5), and `.exe` (4). This demonstrates that
`docs/history/` currently contains mixed document, source, log, image, archive,
database-journal and executable-shaped artifacts; filenames/extensions alone
do not prove whether they are safe, historical, generated, sensitive, or
rebuildable. None were opened. They remain `UNRESOLVED / PRESERVE` until each
exact path has provenance, owner, references, hash, data class and a reviewed
disposition.

## Local branch refs

Counts use only local `refs/heads/*` and cached `origin/main`:
`git rev-list --count origin/main..refs/heads/<branch>`. “Ancestor” means the
local branch tip is an ancestor of the cached `origin/main`. No remote fetch or
push was performed; all live upstream status is `UNKNOWN`.

| Local branch | Tip | Unique commits | Tip ancestor of cached origin/main |
| --- | --- | ---: | --- |
| `agent/phase5-research-knowledge-governance` | `0a5e1bfa9420` | 1 | no |
| `audit/r5-independent-audit-20260919` | `6daca18e79b0` | 1 | no |
| `audit/unreleased-real-version` | `40922904e026` | 2 | no |
| `axw/execution-h0` | `39df7d263ef6` | 8 | no |
| `axw/execution-h1` | `1c688c71eace` | 16 | no |
| `chore/naming-repo-refs` | `a9aa0665cc0b` | 3 | no |
| `codex/aaos-p3-ui-convergence-20260922` | `a5de4b13474c` | 166 | no |
| `codex/ci-release-optimization` | `74ca55361371` | 7 | no |
| `codex/execution-reliability-standards` | `affc0abcea7d` | 2 | no |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8dac0` | 149 | no |
| `codex/post-release-v0.6.9` | `e50aad0d0407` | 2 | no |
| `codex/recovery-shell-closed-loop` | `14afe9376adf` | 13 | no |
| `codex/recovery-shell-frontend` | `e4239ebd4fe8` | 9 | no |
| `codex/release-v0.6.9` | `c64278dfcb77` | 2 | no |
| `codex/v0.6.8-release-closure` | `42e7c0cc36fa` | 2 | no |
| `codex/worker-quality-0906` | `4ca46eaf94c4` | 0 | yes |
| `docs/verification-summary-2026-08-09` | `8cc9c6908078` | 1 | no |
| `feat/absorption-adopt-now` | `081cf20a2815` | 7 | no |
| `feat/absorption-roadmap-r0` | `42d13c0b7482` | 7 | no |
| `feat/archeaxis-desktop-a1-violet-core` | `376281c6a68b` | 5 | no |
| `feat/axw022a-pdf-http-endpoint` | `17ca96280010` | 4 | no |
| `feat/axw022b-evidence-annotation` | `3edacbcb1c67` | 2 | no |
| `feat/h2-bakeoff` | `376fb8001a0a` | 3 | no |
| `feat/h2-pipeline-integration` | `e1df9279fde0` | 9 | no |
| `feat/ms00-c-release-identity` | `01e794d10701` | 1 | no |
| `feat/naming-step3` | `bc4a234ffe4d` | 1 | no |
| `feat/p1-compat-kernel-hardening` | `a4f2de19794d` | 11 | no |
| `feat/portable-data-root` | `4e1a3ed849d7` | 1 | no |
| `fix/desktop-close-request-destroy` | `801edea89bdf` | 1 | no |
| `main` | `e3875db0ee6d` | 0 | yes |
| `release/v0.4.0-contract` | `75cb72ef4642` | 4 | no |
| `work/tp12-facades` | `8d5ba104a919` | 1 | no |

There are 32 local branches in this snapshot. These commit counts do not prove
branch purpose, exclusive ownership, remote publication or merge readiness.
The current feature branch and several old branches have unique commits; a
per-branch changed-path/owner manifest is still required before consolidation.

The following path footprint uses `git -c core.quotePath=false diff --name-only
refs/remotes/origin/main...refs/heads/<branch>` and summarizes the three largest
top-level path groups. It identifies overlap/legacy areas for review; it is not
a commit-level ownership audit or merge recommendation.

| Local branch | Changed paths | Largest path groups |
| --- | ---: | --- |
| `agent/phase5-research-knowledge-governance` | 13 | `tests` 5, `shared` 3, `app` 2 |
| `audit/r5-independent-audit-20260919` | 1 | `docs` 1 |
| `audit/unreleased-real-version` | 5 | `app` 1, `desktop` 1, `pyproject.toml` 1 |
| `axw/execution-h0` | 15 | `tests` 6, `app` 2, `.github` 1 |
| `axw/execution-h1` | 26 | `tests` 13, `app` 12, `workspace` 1 |
| `chore/naming-repo-refs` | 8 | `scripts` 2, `.github` 1, `AGENTS.md` 1 |
| `codex/aaos-p3-ui-convergence-20260922` | 80 | `docs` 32, `tests` 14, `apps` 11 |
| `codex/ci-release-optimization` | 100 | `reports` 25, `docs` 17, `tests` 15 |
| `codex/execution-reliability-standards` | 8 | `docs` 5, `workspace` 2, `AGENTS.md` 1 |
| `codex/frozen-roadmap-deepseek-v1` | 137 | `docs` 131, `workspace` 3, `scripts` 2 |
| `codex/post-release-v0.6.9` | 11 | `docs` 5, `tests` 2, `HERMES_HANDOFF.md` 1 |
| `codex/recovery-shell-closed-loop` | 22 | `frontend` 10, `tests` 4, `desktop` 3 |
| `codex/recovery-shell-frontend` | 19 | `frontend` 10, `desktop` 3, `src-tauri` 2 |
| `codex/release-v0.6.9` | 29 | `desktop` 7, `tests` 6, `src-tauri` 3 |
| `codex/v0.6.8-release-closure` | 16 | `docs` 7, `tests` 3, `reports` 2 |
| `codex/worker-quality-0906` | 0 | no diff from cached `origin/main` |
| `docs/verification-summary-2026-08-09` | 1 | `docs` 1 |
| `feat/absorption-adopt-now` | 26 | `shared` 8, `tests` 6, `docs` 5 |
| `feat/absorption-roadmap-r0` | 56 | `tests` 20, `knowledge_base` 10, `shared` 8 |
| `feat/archeaxis-desktop-a1-violet-core` | 17 | `app` 4, `docs` 4, `.github` 1 |
| `feat/axw022a-pdf-http-endpoint` | 10 | `app` 6, `tests` 2, `pyproject.toml` 1 |
| `feat/axw022b-evidence-annotation` | 4 | `app` 3, `tests` 1 |
| `feat/h2-bakeoff` | 4 | `shared` 3, `tests` 1 |
| `feat/h2-pipeline-integration` | 78 | `docs` 28, `tests` 13, `app` 6 |
| `feat/ms00-c-release-identity` | 6 | `app` 2, `tests` 2, `.github` 1 |
| `feat/naming-step3` | 14 | `app` 4, `scripts` 3, `desktop` 2 |
| `feat/p1-compat-kernel-hardening` | 14 | `tests` 5, `app` 4, `workspace` 2 |
| `feat/portable-data-root` | 18 | `desktop` 5, `scripts` 5, `app` 3 |
| `fix/desktop-close-request-destroy` | 1 | `docs` 1 |
| `main` | 0 | no diff from cached `origin/main` |
| `release/v0.4.0-contract` | 2 | `.github` 1, `tests` 1 |
| `work/tp12-facades` | 37 | `inspiration_research` 18, `tests` 4, `app` 3 |

## Registered worktrees

| Path | HEAD | State at capture |
| --- | --- | --- |
| Repository root | `a5de4b13474c` | 1,048 status entries as above |
| `.project-local/worktrees/v3-era` | `968c4795e404` | detached; 3 dirty paths in Rust archive/store and fixture test |
| `.project-local/worktrees/verify-0c9c` | `cdc07cd0027d` | detached; clean status |
| `.project-local/worktrees/worker-quality-0906` | `4ca46eaf94c4` | `codex/worker-quality-0906`; 17 dirty paths across worker, contract, generated vocabulary and tests |

No worktree is removed or altered by this audit. The dirty worker-quality tree
and detached worktrees must be preserved until an owner maps each change to a
branch/work item and records recovery. A clean worktree alone is not deletion
authorization.

## `.project-local/` metadata-only inventory

At capture, `.project-local/` had 32 direct directories:

`a15-current-basetemp`, `a15-current-contract-basetemp`,
`a15-current-security-basetemp`, `artifacts`, `audits`, `build`, `c`, `cache`,
`cargo-home-a04`, `deeptutor-val`, `dist`, `g`, `gh-cache`, `inspect`,
`motion-contract-final-cache`, `motion-contract-pytest-cache`, `p`, `probe`,
`probe2`, `probes`, `runs`, `staging`, `state`, `task-runtime`,
`test-fallback-run`, `test-fixtures`, `tmpuf_amolv`, `tooling`, `tools`,
`ui-audit`, `uv-cache`, `worktrees`.

The 2026-09-23 volume audit listed only 10 rows, so its inventory is stale or
incomplete as a current topology view. Selected metadata-only counts from the
read-only scan were: `runs` 463 files / 241 directories; `task-runtime` 68 / 8;
`deeptutor-val` 13 / 3; `worktrees` 0 / 3; `audits` 5 / 2; `build` 0 / 29;
`cache` 0 / 9. These counts establish neither bytes, hashes, data lineage,
regenerability, active consumers, nor retention eligibility. No file contents,
hashes, ignored Git contents, or external shared-resource roots were accessed.

## Required follow-through and current boundary

1. Reconcile all 32 branch tips against a freshly authorized remote readback;
   then map unique commits to exact changed-path manifests and owners.
2. For each dirty registered worktree, collect an owner/recovery receipt before
   any branch movement, merge, archive or worktree cleanup.
3. Trace untracked `docs/history/**` additions and the browser-profile-shaped
   subtree through origin/generator/owner without reading prohibited browser
   credential state. Quarantine or cleanup requires an exact reviewed manifest
   and a safe permitted handling path.
4. Extend the `.project-local/` inventory to per-path owner, data class,
   generator/source SHA, consumer references, hashes, retention, rollback and
   exact deletion authorization. Preserve unresolved items.
5. Do not merge, delete branches, remove worktrees, move data, or clean paths in
   this receipt. The exact owner gates and evidence are not present here.

Status: `PARTIAL / READ_ONLY_METADATA`; remote state, content provenance,
file hashes/bytes, active process use, and cleanup eligibility remain `UNKNOWN`.

## Follow-up — origin heads readback correction (2026-09-25)

A live read-only `git ls-remote --heads origin` has since succeeded. It supersedes the earlier `remote state UNKNOWN` wording above for branch-head visibility only. Origin has 19 heads; 13 names overlap the 32 local branch names and every overlapping SHA matches, including the active branch at `a5de4b13474c217e7a9dd34b8cbfa402e8297780`. Six origin-only refs (`chore/placeholder-hygiene`, `docs/intake-h2`, `docs/naming-handoff`, `feat/naming-package-identity`, `feat/naming-v2-contract`, `fix/mfx001-marker-block`) each have one patch equivalent in the current branch according to `git cherry` (0 new, 1 equivalent). Nineteen local names are absent at origin. Three local refs are ancestors of the current tip; `audit/r5-independent-audit-20260919` has no new patch but its cached upstream is absent from the live heads; the other 28 refs have new patches.

This is not evidence of PR closure, ownership, merge intent, or permission to delete local/remote refs. No branch or worktree was changed. The path-level provenance and cleanup status for untracked/history data remains UNKNOWN.

## Remote recheck failure and expanded local graph snapshot (2026-09-25)

A fresh `git ls-remote --heads origin` attempt failed before returning refs: SSH could not add the host to the configured known-hosts path and GitHub returned `Permission denied (publickey)`. No credential/configuration changes were made. The earlier successful 19-head readback remains a dated last-success snapshot; current remote heads and PR state are `UNVERIFIED`.

The current local graph still has 32 heads. Against checked-out `codex/aaos-p3-ui-convergence-20260922` (`a5de4b13474c217e7a9dd34b8cbfa402e8297780`), two other refs (`main`, `codex/worker-quality-0906`) are ancestors; `audit/r5-independent-audit-20260919` is one commit ahead with one patch-equivalent change; the other 28 refs contain new patches and divergence spans 1–1,793 commits. `codex/worker-quality-0906` remains attached to a dirty worktree. This path-count/graph read did not inspect patch bodies or owner intent and does not authorize any integration or cleanup. No branch, worktree or file payload was changed.

## Independent audit follow-up — 2026-09-25

- A fresh path-only count was independently run through PowerShell and the indexed Python interpreter against the same checkout: 995 untracked files, 989 with the exact `docs/history/` prefix, 991 under `docs/`, 3 under `apps/`, and 1 under `crates/`. The broad component filter (`history|task-artifacts|web-chain-debug|profile`) also returned 989 in this snapshot. An earlier parallel read reported 984 for the exact prefix; that value was not reproducible in the current checkout and is superseded for this snapshot. Counts are still point-in-time and do not establish ownership.
- A metadata-only `.project-local/` traversal that skipped paths containing `profile`, `profiles`, `browser-profile`, `browser_profiles`, or `web-chain-debug` counted 460,570 files, 104,499 directories and 61,564,135,284 bytes (about 57.34 GiB). Traversal errors were suppressed, so this is a visible lower bound. A previous scan used different filters and counted different totals; the measurements must not be combined or treated as exact capacity. No payload was read, copied, moved, hashed, or deleted.
- Branch/worktree classification was refreshed locally: `main` and `codex/worker-quality-0906` are ancestors of the active feature tip; `audit/r5-independent-audit-20260919` has one patch-equivalent historical audit change; two `codex/recovery-shell-*` branches retain React/Tauri-era shell work and are frozen behavior references under the current Avalonia authority; the remaining 28 divergent refs have new patches and need per-commit/path ownership and R6/M0 compatibility review before any migration. The root, `worker-quality-0906` and `v3-era` worktrees are dirty; `verify-0c9c` is clean. No ref or worktree was changed. Live remote refs remain `UNVERIFIED` after the SSH failure above.
- The repository authority audit found no active language-boundary conflict: formal desktop is Avalonia/C#, Rust is the sole vNext writer, and Python workers remain isolated. Legacy React/Tauri code is retained by directory authority as maintenance/recovery material. ADR-0001 copies still say “proposed for Owner acceptance in PR-00”, and `src-tauri/README.md` still describes the old shell; these are documentation-state ambiguities, not authorization to change architecture or remove legacy material. Resolve only with owner/state evidence and a narrow documentation update.

## Branch commit/path manifest — 2026-09-25

Generated the machine-readable local branch commit/path inventory at
`docs/current/AAOS-BRANCH-COMMIT-PATH-AUDIT-20260925.json`. It enumerates 32
local branch refs and 441 branch/commit records reachable from each branch tip
but not from the cached `refs/remotes/origin/main` SHA
`e3875db0ee6d073d37839eb7b95f7ef4ce881bbb`. Each record includes branch tip,
commit SHA, parents, author, authored timestamp, subject, exact paths reported
by `git diff-tree`, and other local branch refs containing the same commit.
The corrected manifest records 441 branch/commit rows but 433 distinct commit
SHAs. Eight commit SHAs appear in multiple branch records; four commits have no
file paths in their own diff-tree record: three merges and one ordinary empty
commit. Consequently, these counts are not counts of independently owned
patches.

The disposition crosswalk's `tip` values were also corrected from local ref
readback; zero commits relative to the comparison base is not a missing branch
tip. This fills the local per-commit/path enumeration gap only. It does not identify
owners, worktree-dirty changes, remote-only refs, PR disposition, semantic
compatibility with R6/M0, or merge/delete readiness. Base comparison is against
the cached remote-tracking ref; live remote refs remain `UNVERIFIED`. No branch,
worktree, file payload, or external data was moved or changed by the inventory.

## Preliminary branch disposition crosswalk — 2026-09-25

Created `docs/current/AAOS-BRANCH-DISPOSITION-REVIEW-20260925.json` for all 32 local branch names. It records a conservative preliminary disposition, current authority basis, `owner=UNKNOWN`, missing dirty-worktree recovery receipts, semantic review `NOT_DONE`, and explicit `merge_delete_authorized=false`. It separates the active convergence branch, ancestor/attached-worktree custody, frozen React/Tauri or prior web UI behavior references, historical release/roadmap/governance evidence, and capability/legacy donor branches requiring a specific R6 review before any port.

This crosswalk is not a merge/delete plan. It is intentionally based on local branch identity and the existing path/subject inventory; per-commit behavior has not been semantically reviewed. Do not infer owner, redundancy, compatibility, or cleanup permission from these preliminary classes. R6 Research remains defined as a bounded multi-source pipeline with snapshots, claim extraction, independent-source clustering, and support/conflict/gap analysis; older FTS/Vault/React/Tauri implementations cannot be relabeled as current Research or current shell. Branch and worktree custody actions remain unperformed.
## Current untracked-path metadata and hashes — 2026-09-25

A current `git ls-files --others --exclude-standard` read returned 997 untracked
files (plus 71 tracked status entries). A metadata-only inventory is recorded in
`docs/current/AAOS-UNTRACKED-LINEAGE-METADATA-20260925.json`: 292 non-profile
files were read only for size, last-write timestamp, extension, and SHA-256; all
remain `UNRESOLVED_PRESERVE`. Hashes identify these exact bytes but do not prove
provenance, ownership, generator, consumer, or cleanup eligibility. The two new
branch-audit manifests are included in the measured untracked set because they
are part of this current worktree.

A further 705 untracked paths matched `profile` / `web-chain-debug` components
and were excluded from content, size, and hash inspection; the manifest stores
only sanitized path prefixes and their count. They remain
`UNRESOLVED_POTENTIALLY_SENSITIVE / PRESERVE`. No file content was opened or
printed, and no path was moved, deleted, or reclassified as disposable. The
inventory is a point-in-time read and does not include ignored `.project-local`
files or external data roots.


## Current branch, DSH and spill recheck — 2026-09-26

This section supersedes the preliminary branch statements above; the dated source observations remain preserved. Current checkout HEAD is `2994efa08d3e4f6ea561831fd4088d6d1b290cdd` (tree `4fc581e7dcde90a30d8e9019f26fdf362bfa5cc9`), with 27 local refs and 5 registered worktrees. The active branch is 7 commits ahead of its live origin tip `a5de4b13474c217e7a9dd34b8cbfa402e8297780`. The latest authenticated read-only remote snapshot records 7 retained heads; the 12 heads previously deleted by the user remain absent, with all seven retained head SHAs unchanged. No remote write was performed.

A per-commit/path review found one removable local ref: `audit/r5-independent-audit-20260919` had one non-ancestor commit, that commit was patch-equivalent to HEAD, its sole report blob matched HEAD (`dcb1e1563c2250a614cc068ef26be3db3ef7972b`), it had no attached worktree and no live remote head. The exact ref was deleted conditionally and then read back absent; its report content remains in HEAD. Three refs are graph ancestors (active, `main`, and `codex/worker-quality-0906`); the latter has a dirty attached worktree. The other 23 divergent branches contain unique patches. `codex/dp-f01-20260925` has two patch-equivalent commits but an attached worktree with an inaccessible path warning; its data/runtime custody is unresolved. No further local ref or worktree met a safe cleanup basis.

DSH integration (verified against current Git graph): NF-01–NF-07 were integrated by the ancestor commit `5bb89aa7` (`Integrate audited DP-NF task pack`), whose parent is the declared DSH baseline `a9ead3e...`; the individual DP-NF branch tips are not HEAD ancestors because their content was squash-integrated. NF handoff deliverable paths are present; one P6 readback report is further modified in the root worktree. DP-F01's 9/9 changed paths match HEAD blobs exactly and both original commits are patch-equivalent (`git cherry` marks `-`), but the source branch is not ancestry-merged. It remains owner review for the proposal; no production Rust API change was delivered. DP-GIT-01/02, DP-A11 and DP-UI-01 reports exist. DSH DP-UI-01 remains `BLOCKED / NOT_EXECUTED`; DP-UI-02 was not started. Root Avalonia/Candidate work is separate evidence, not a substitute for those DSH branch artifacts. The DP-F01 registered worktree has no tracked changes, but permission warnings and project-local run residue prevent claiming it is clean or safely removable.

Spill inventory remains non-migratable under current evidence: the 2026-09-25 metadata counted 997 untracked paths, with 292 safe-path metadata rows and 705 paths excluded as potentially sensitive. The 284 `docs/history/` rows remain owner-unresolved and deletion-not-requested; the other 8 safe rows are also `UNRESOLVED_PRESERVE`. The corrected eight-path receipt identifies 3 unchanged and 4 changed non-session files; the session file was not read or hashed. AX-DIR-010 is still schema-only and authorizes no move/delete. No path was migrated or deleted.

Local remote-tracking cache cleanup on 2026-09-26: twelve stale `refs/remotes/origin/*` refs corresponding to cloud-deleted heads were conditionally removed by expected SHA. Eight were previously removed because their content was represented by main or a same-name local recovery branch. The remaining four (`codex/post-release-v0.6.9`, `codex/recovery-shell-closed-loop`, `codex/release-v0.6.9`, `codex/v0.6.8-release-closure`) were removed only after exact verification: each PR head SHA matched the cached tip, its PR was merged, its merge commit is an ancestor of `origin/main`, and its merge tree SHA exactly equals the tip tree SHA. No same-name local branch or worktree existed. These actions only changed local Git refs; no remote ref or commit object was deleted. A fresh approved `git ls-remote --heads origin` at 2026-09-26 06:02 UTC succeeded and returned seven heads, matching the `live_readback_20260926` set in `AAOS-BRANCH-DISPOSITION-REVIEW-20260925.json`. Final local cache readback shows seven live heads plus symbolic `origin/HEAD`; stale origin tracking refs remaining: **0**.

## Current path-listing delta — 2026-09-26

`git ls-files --others --exclude-standard` currently returns 1,014 visible untracked paths, but emits a `Permission denied` warning for an inaccessible directory; this is a lower bound, not a complete inventory. Of the visible paths, 705 match the prior profile/web-debug exclusion rule and remain uninspected; the other 309 comprise the 292 previously hashed paths plus 17 newly visible paths. An exact UTF-8/NUL-delimited comparison against `2026-09-25` `files[].path` confirms all old 292 remain untracked (`missing=0`); the 17 additions are distributed as docs=10, tests=3, apps=1, crates=1, scripts=1, workspace=1. At capture time, one new path name matched the session exclusion and its payload was not opened. A later parallel review unintentionally opened a session-named document body and headers of several privacy-sensitive history documents before the scope issue was caught; it stopped immediately, did not reproduce their contents, and made no changes. Those paths remain `UNRESOLVED_POTENTIALLY_SENSITIVE / PRESERVE` and are not classified or migration candidates. Exact ownership, generator, consumer and migration destination remain unresolved, so no spill path was moved or deleted. This replaces the earlier, unreproducible 22-new/5-missing comparison; the older manifest remains a dated snapshot, not current full coverage.

The current root status reports 102 tracked modifications and 1,014 visible untracked paths, with permission errors affecting traversal. The 5 Git worktrees and 27 local branches remain in place. Live origin is 7 heads (fresh approved readback); all stale local `origin/*` tracking refs have now been pruned with exact ancestry/tree evidence. DSH DP-NF integration is an ancestor commit; DP-F01 is exact-content/patch-equivalent integration without ancestry merge. Its worktree and run residue remain unresolved, and DP-UI acceptance is incomplete.

The same approved read-only session attempted `gh pr list --repo DTALEX66/ArcheAxis-Knowledge-OS --state all --limit 100 --json number,state,isDraft,headRefName,headRefOid,mergedAt,closedAt,url`; GitHub CLI returned HTTP 401 `Bad credentials` from the GraphQL API. This is a `gh` API credential-path failure only: SSH `git ls-remote --heads origin` succeeded. No credential was read, printed, repaired or changed. GitHub's public read-only REST PR list was then retrieved through the approved network path and paginated to completion. Matching on the seven exact live head SHAs returned three PRs: #22 for `release/v0.4.0-contract` is closed/merged (head SHA `75cb72ef...`); #70 for `docs/verification-summary-2026-08-09` is closed/unmerged (head SHA `8cc9c690...`); #136 for `feat/naming-step3` is closed/unmerged (head SHA `bc4a234f...`). No PR record with the exact current SHA was found for the other four live heads. This is current read-only PR evidence, not permission to delete any live branch; closed/unmerged branch contents remain preserved pending final custody review.

Current authority remains C#/Avalonia formal desktop, Rust sole vNext writer, isolated Python workers; no active React/Tauri canonical-shell recommendation was found. Full R6/M0 remains `IN_PROGRESS`, Release `FROZEN`, P0–P5 partial and P6 owner-gated. Exact live branch values and cleanup proof are in `AAOS-BRANCH-DISPOSITION-REVIEW-20260925.json` → `live_readback_20260926`.

## Same-day follow-up — 2026-09-26 06:40 UTC

An additional normal-approval read-only `git ls-remote --heads origin` succeeded. It returned exactly the seven heads and SHAs already recorded in `live_readback_20260926`; no live remote ref changed during this pass. Local branch review remains 27 heads / 5 worktrees: active, `main`, and attached `codex/worker-quality-0906` are ancestors; DP-F01 has only patch-equivalent commits but remains attached to a worktree with unresolved residue/permission custody; every other divergent branch has at least one unique patch. No further local branch/worktree was proven safe to remove. No remote delete, push, merge, or release action was taken.

Current-tree checks also passed: repository conventions `issue_count=0`; language boundaries `passed=true` (Rust/Python/schema protocol majors 1); `tests/test_ci_classifier.py` 32 passed. `.worklab/project-validation.v1.yaml` descriptions now identify retained Tauri/installer/Python-compat classes as legacy compatibility only; path matching and gate sets are unchanged. These static checks do not close full external-data lineage, runtime writer-path audit, or R6 P5 migration acceptance.

Frontend remains partial under R6/M0. Exact-current-source evidence covers Candidate launch, 16/16 UIA routes, palette filtering/result selection, Ctrl+K focus and Esc restoration, native synthetic import/readback and bounded viewport checks. Command result execution by Enter, full menu/access-key operation, IME, screen reader/high contrast, all-route DPI/visual review, and owner-gated/real-data P3 and Green qualification remain open. No frontend status is promoted based on source-level contracts alone.

A bounded metadata/content review additionally covered 14 ordinary historical records (nine closure-task notes and five dated plans; paths containing privacy/sleep/handoff terms were excluded). Their current SHA-256 values match the prior inventory and exact-path `git log --all` returns zero commits for each. Their headers/body identify them as old `Cognitive-Loop-OS` task/planning records, so their present `docs/history/` placement is semantically consistent. This does not identify their original generator, current owner or consumers; keep them in place as `HISTORICAL_RECORD / RETAIN`, not migration-ready. No source/target copy was made.

Remote heads re-read at 2026-09-26 06:56 UTC through the approved read-only path; all seven branch names and SHAs exactly match the 06:40 UTC follow-up. No remote refs were changed.

## Live state recheck — 2026-09-26 07:17 UTC

Fresh normal-approval `git ls-remote --heads origin` again returned the same seven live branch heads; no `dp-*` task branch is published. Current local refs are 27 and match the branch review's recorded set. `git branch --merged origin/main` returns only `main` and `codex/worker-quality-0906`; the latter remains attached to a dirty worktree. Thus it is not a cleanup candidate. The root active branch is seven commits ahead of its live counterpart and has extensive dirty work; DP-F01 remains the only local DSH task branch, attached to a worktree whose tracked files are clean but whose ignored/untracked custody remains unresolved. No new branch/worktree deletion or remote write is justified by this readback. Branch dispositions are recorded for every local ref, but that does not mean semantic audit or cleanup is complete: 25 local refs are not ancestors of `origin/main`; multiple capability/contract reviews remain partial or lack owner/custody proof.

The DSH assignment set contains 13 named cards: DP-NF-01..07, DP-GIT-01/02, DP-A11, DP-F01, DP-UI-01/02. The earlier NF integration commit is an ancestor and most outputs are exact-blob present; the **NF-01 final tip** is not wholly represented by that commit. Its three final report paths differ from HEAD. The current dirty worktree contains the report corrections (including retraction of the false archive finding after checking the donor archive index), but do not describe the final tip as committed/ancestry-integrated. DP-UI-01 remains blocked/not executed and DP-UI-02 was not started; current root frontend evidence is separate. The bounded GIT batches and NF-07 root inventory were not exhaustive, so additional branch and spill coverage remains required.

Fresh convention and language checkers executed with the indexed Python 3.12 environment: `check_repository_conventions.py --source worktree --format json` returned `issue_count=0`; `check_language_boundaries.py --json` returned `passed=true` with protocol major 1. These are current dirty-worktree static checks, not exact-HEAD CI or runtime writer-path proof. No exact-SHA GitHub CI run was verified. The worktree still contains broad user changes and one inaccessible directory; these checks do not cover all untracked/ignored or inaccessible content.

## Spill coverage re-count — 2026-09-26 07:30 UTC

The current `git ls-files --others --exclude-standard` read returns 1,014 visible paths and emits a permission warning; every number below is a lower bound. The strict name-based exclusion set covers 758 paths without opening their contents; 256 remaining paths are safe to count. Of the prior 292-path metadata inventory, 287 are present in the current Git listing: 52 fall in the strict exclusion set and 235 in the safe visible set. Five prior inventory paths are not visible in the current listing; that is not proof of deletion because the unreadable directory bounds the observation. The safe visible set therefore contains 21 paths not represented in the prior inventory (256 - 235). No path names from excluded or unclassified sets are reproduced here.

The separate `docs/history/` disposition still contains 284 entries. Field-presence review finds owner unresolved for 284/284 and generator unresolved for 284/284; consumer, target path and source hash fields are populated for all 284, but populated metadata does not establish ownership or a verified generator. Deletion authorizations: 0. Safe migration candidates: 0. All excluded, inaccessible, unresolved and historical paths remain in place; no copy, move, deletion or hash/content scan was performed on excluded paths. Full external spill tracing and cleanup remain incomplete.

### Coverage comparison correction — 2026-09-26

The preceding paragraph used a case-sensitive path-set comparison and therefore understated old-inventory coverage. Recomputed using Windows case-insensitive path identity: all 292/292 old metadata paths have a current visible Git-listing counterpart; 287 spellings are exact and 5 differ only by case. Of these, 240 are in the current safe-to-count set and 52 fall in the excluded-name set. The current safe-to-count set has 256 paths, so 16 safe visible paths are not represented in the old inventory (not 21). Current path totals remain 1,014 visible = 256 safe-to-count + 758 excluded-by-name, all lower bounds because Git reports one inaccessible directory. No path contents were opened for this comparison; no missing/deleted conclusion follows from the earlier case-sensitive result.
