# Branch-donor archives — 2026-09-26

Files that existed **only** on a branch, were absent from `HEAD`, and were
preserved here before the legacy-donor branches were deleted.

These are historical assets (handoff notes, dated intake records, a superseded
environment script), not active capability. Nothing here is imported by the
product. Each file is stored byte-for-byte as it appeared on its branch.

> Note on the vendored PDF.js files under `feat__axw022a-pdf-http-endpoint/`:
> they total ~1.4 MB of third-party minified builds kept only because the
> branch's unique content was archived as a unit. The PDF capability itself is
> served by the Rust Core in `HEAD`, so these are reference copies only and can
> be dropped at any time — the branch tip remains recoverable.

## Final local branch state

Local branches went from 27 to 7. Each surviving branch has a recorded reason:

| Branch | Reason to keep |
| --- | --- |
| `codex/aaos-p3-ui-convergence-20260922` | active branch |
| `codex/dp-f01-20260925` | held by a registered worktree |
| `codex/worker-quality-0906` | held by a registered worktree |
| `main` | `merge-base == tip`: ancestor of HEAD, canonical local ref |
| `codex/frozen-roadmap-deepseek-v1` | 130 added paths (118 absent from HEAD); recorded `HISTORICAL_RELEASE_OR_ROADMAP_FREEZE_RETAIN_EVIDENCE` |
| `codex/execution-reliability-standards` | 3 added paths; recorded `HISTORICAL_GOVERNANCE_EVIDENCE_CROSSWALK_ONLY` |
| `docs/verification-summary-2026-08-09` | 1 added path; recorded `HISTORICAL_GOVERNANCE_EVIDENCE_CROSSWALK_ONLY` |

The three frozen branches whose disposition was
`FROZEN_WEB_UI_REFERENCE_REASSESS_AAVALONIA_CONTRACTS` were reassessed and
deleted, and the two `FROZEN_LEGACY_REACT_TAURI_REFERENCE_NO_MERGE` branches
were confirmed to add no path absent from HEAD.

**Recoverability, stated with its limits.** Deleting a branch removes only the
ref: the commits stay in the object database while something else reaches them,
so `git branch <name> <sha>` restores a branch whose tip is still readable. That
is not the same as "deletion never loses content":

- Reachability is a current property, not a guarantee. A commit reachable only
  from local refs can be pruned by a future `git gc` once nothing references it.
  Nothing in this session protects the deleted tips except the local object
  database itself.
- Cloud readability varies per tip. The readback table under "Recovery" below
  shows twelve tips readable through the GitHub commits API and one — the
  `codex/recovery-shell-frontend` tip — returning 422 because that branch was
  never pushed.
- No bundle or archive of the deleted tips was created in this session. The only
  preservation actions taken were: the archived *files* listed above, and the
  recorded tip SHAs.
- The tips are therefore **currently reachable, not permanently recoverable**.
  One of them now has a durable local archive (see the section below); the other
  twelve still rest on this clone's object database alone.

## Why these branches were deleted

Audit criterion: for each branch, count the paths it **added** relative to its
merge-base and check each one with `git cat-file -e HEAD:<path>`. A branch that
adds no path `HEAD` lacks has nothing left to contribute.

Ten `LEGACY_CODE_DONOR_REVIEW_AGAINST_R6_BEFORE_ANY_PORT` branches were reviewed:

| Branch | Added paths absent from HEAD | Outcome |
| --- | --- | --- |
| `audit/unreleased-real-version` | 0 | absorbed |
| `axw/execution-h0` | 0 | absorbed |
| `axw/execution-h1` | 0 | absorbed |
| `chore/naming-repo-refs` | 0 | absorbed |
| `feat/ms00-c-release-identity` | 0 | absorbed |
| `feat/naming-step3` | 0 | absorbed |
| `work/tp12-facades` | 0 | absorbed |
| `feat/p1-compat-kernel-hardening` | 3 | archived, then deleted |
| `feat/portable-data-root` | 3 | archived, then deleted |
| `fix/desktop-close-request-destroy` | 1 | archived, then deleted |

## Archived files and their source branches

### `feat/p1-compat-kernel-hardening` — tip `a4f2de19794df490206b5b0b935f5176a3d5775e`

- `tests/test_format_capabilities.py` (1105 B)
- `workspace/intake/2026-08-09-multiformat-capability-boundary.md` (2432 B)
- `workspace/intake/2026-08-09-online-learning-corpus.md` (1947 B)

Format-capability coverage in HEAD is carried by
`tests/test_format_execution_v1.py`, `tests/test_format_matrix.py`,
`tests/test_text_format_facts.py` and
`tests/test_workspace_pipeline_multiformat.py`. The two intake records are dated
2026-08-09 working notes.

### `feat/portable-data-root` — tip `4e1a3ed849d72f667513d2d159c4cbe5dc6650da`

- `scripts/project_env.bat` (1549 B)
- `scripts/project_env.ps1` (1443 B)
- `scripts/project_env.sh` (1212 B)

**Superseded, not merely absent.** These scripts target the predecessor project
name (`Cognitive-Loop-OS`) and place the runtime under `.hermes\task-runtime`,
setting `COGNITIVE_DATA_DIR`. HEAD carries the portable data policy as
`config/profiles/portable-stable.yaml` (`data_policy: portable-root-only`) and
routes development output through `.project-local/` via
`scripts/runtime/dev.py`. Restoring these scripts would reintroduce a retired
name and a retired runtime root.

### `fix/desktop-close-request-destroy` — tip `801edea89bdf5d845f083670df4afad923ef985b`

- `docs/workflow/HANDOFF_DESKTOP_CLOSE_LIFECYCLE_2026-08-06.md` (3705 B)

A 2026-08-06 handoff note recording an NSIS close-lifecycle root-cause fix
delivered through PR #38, explicitly stating that main Green was not claimed.

## Second pass — three frozen web-UI references (`FROZEN_WEB_UI_REFERENCE_REASSESS_AAVALONIA_CONTRACTS`)

The disposition record requires these to be reassessed against the Avalonia
contracts rather than merged. Reassessment outcome: their capability is already
present in HEAD, so they were archived and deleted.

### `feat/archeaxis-desktop-a1-violet-core` — tip `376281c6a68bd8b6385d43878d370b81e28cf9ee`

- `requirements-ci-adapters.txt` (243 B)
- `workspace/intake/2026-07-28-archeaxis-pack-analysis.md` (8595 B)

A 2026-07-28 pack-analysis note and a CI adapter requirement list.
`docs/PRODUCT_POSITIONING.md` from this branch already exists in HEAD.

### `feat/axw022a-pdf-http-endpoint` — tip `17ca96280010822fe1ee95a6f264f47e7435d2c8`

- `app/workspace/ui/assets/licenses/pdfjs-3.11.174-LICENSE.txt` (10174 B)
- `app/workspace/ui/assets/pdf.min.js` (320005 B)
- `app/workspace/ui/assets/pdf.worker.min.js` (1087213 B)

**The capability is in HEAD on the formal side.** PDF bytes are served by the
Rust Core (`crates/archeaxis-api/src/lib.rs` exposes the source/transform
routes) and `tests/test_workspace_pdf_endpoint.py` exists in HEAD. These are the
React/Tauri web assets, which the frozen disposition explicitly forbids merging;
they are kept only as the third-party licence and reference copy. The two
minified files are vendored PDF.js builds, not project source.

### `feat/axw022b-evidence-annotation`

Added one path (`tests/test_workspace_evidence_anchor_api.py`) that already
exists in HEAD: zero paths absent, fully absorbed. No files needed archiving.

## Local-only recovery archive — 2026-09-26

Measured, not assumed: the `codex/recovery-shell-frontend` tip is an object with
**no ref pointing at it**, so a single `git gc` would prune it permanently.
Checked first whether an existing bundle already held it
(`.project-local/archive-local-branch-candidates-20260918.bundle` and
`.project-local/runs/audit-fix-20260915/ArcheAxis-first-use-fixes.bundle`): neither
contains it.

A dedicated archive was therefore created:

| Item | Value |
| --- | --- |
| Bundle | `.project-local/archive-local-only-recovery-20260926.bundle` |
| Size | 35.65 MB |
| Ref recorded inside | `refs/heads/archive/local-only/codex-recovery-shell-frontend-20260926` |
| `git bundle verify` | "The bundle records a complete history" |
| Tracked by Git? | No — `.project-local/` is ignored (`.gitignore:48`), by design |

Isolated recovery check, in a throwaway repository created under the system temp
directory (never in this working clone, and no destructive operation was run
here):

```
git init <tmp> && git fetch <bundle> 'refs/heads/archive/...:refs/heads/recovered'
  -> fetch exit 0
  -> ref resolves to e4239ebd4fe825becc4192d6e89bfaa35a9a3946
  -> git cat-file -t <sha> = commit
  -> git log -1 = 2026-08-23 "feat(recovery): add thin desktop recovery shell"
  -> git fsck = no missing prerequisite objects
```

What this establishes: the tip and its prerequisite objects are now recoverable
independently of this clone's object database, and the bundle is self-contained
and verified. What it does **not** establish: that the *.project-local* directory
is itself backed up anywhere. The bundle is a local safety copy; if that
directory is not preserved, this recovery path goes with it.

The bundle is deliberately not committed — a 35 MB object store does not belong
in Git history, and the repository already carries a large pack. If an off-repo
backup of `.project-local/archive-local-only-recovery-20260926.bundle` is
required, that is an owner action, not something this session can assert.

## Recovery


The deleted branches remain recoverable from their recorded tips; the commits
are still present in this repository (`git cat-file -t <tip>` returns `commit`):

```
git branch <name> <tip-sha>
```

**Auditability note.** A tip whose branch was only ever local is *not* readable
from GitHub. Verified readback of `GET /repos/DTALEX66/ArcheAxis-Knowledge-OS/commits/<sha>`:

| Tip | GitHub readback |
| --- | --- |
| `376fb800…` h2-bakeoff | 200 |
| `e1df9279…` h2-pipeline-integration | 200 |
| `081cf20a…` absorption-adopt-now | 200 |
| `42d13c0b…` absorption-roadmap-r0 | 200 |
| `a4f2de19…` p1-compat-kernel-hardening | 200 |
| `4e1a3ed8…` portable-data-root | 200 |
| `801edea8…` desktop-close-request-destroy | 200 |
| `0a5e1bfa…` agent/phase5 | 200 |
| `17ca9628…` axw022a-pdf-http-endpoint | 200 |
| `3edacbcb…` axw022b-evidence-annotation | 200 |
| `376281c6…` archeaxis-desktop-a1-violet-core | 200 |
| `75cb72ef…` release/v0.4.0-contract | 200 |
| `e4239ebd…` codex/recovery-shell-frontend | **422 — local only** |

`codex/recovery-shell-frontend` was never pushed, which the earlier committed
audit already recorded ("local historical frontend; no remote tracking"). Its tip
cannot be inspected from the cloud; only the local clone can restore it.

The full disposition record, including the classification of every branch, is
`docs/current/AAOS-BRANCH-DISPOSITION-REVIEW-20260925.json` and the session
checkpoint `docs/current/AAOS-DSH-TAKEOVER-CHECKPOINT-20260926.md`.
