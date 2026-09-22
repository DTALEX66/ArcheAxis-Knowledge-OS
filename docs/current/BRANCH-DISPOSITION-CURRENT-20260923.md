# Branch Disposition — Current Readonly Audit 2026-09-23

Evidence: local Git refs and `origin/main` local ref at
`e3875db0ee6d073d37839eb7b95f7ef4ce881bbb`. Live remote listing is
`UNVERIFIED` because SSH `known_hosts` access was denied. No branch was merged,
deleted, rebased or force-pushed.

`ahead/behind` is relative to `origin/main`; `merged=yes` means the branch tip
is an ancestor of `origin/main`, not that the branch is safe to delete.

| Local branch | tip | ahead | behind | merged | disposition |
| --- | ---: | ---: | ---: | :---: | --- |
| `agent/phase5-research-knowledge-governance` | `0a5e1bfa` | 1 | 1558 | no | historical; inspect unique commit before owner decision |
| `audit/r5-independent-audit-20260919` | `6daca18e` | 1 | 196 | no | independent audit evidence; preserve |
| `audit/unreleased-real-version` | `40922904` | 2 | 1372 | no | historical release evidence; preserve |
| `axw/execution-h0` | `39df7d26` | 8 | 1372 | no | historical AXW work; no age-only deletion |
| `axw/execution-h1` | `1c688c71` | 16 | 1371 | no | historical AXW work; no age-only deletion |
| `chore/naming-repo-refs` | `a9aa0665` | 3 | 1310 | no | naming evidence; preserve until reference audit |
| `codex/aaos-p3-ui-convergence-20260922` | `974322a6` | 13 | 0 | no | active frontend delivery candidate |
| `codex/ci-release-optimization` | `74ca5536` | 7 | 1063 | no | historical release candidate; inspect only |
| `codex/execution-reliability-standards` | `affc0abc` | 2 | 1370 | no | governance evidence; preserve |
| `codex/frozen-roadmap-deepseek-v1` | `fcfac4a8` | 149 | 1372 | no | historical roadmap; preserve |
| `codex/post-release-v0.6.9` | `e50aad0d` | 2 | 1059 | no | historical release evidence |
| `codex/recovery-shell-closed-loop` | `14afe937` | 13 | 1061 | no | historical desktop evidence |
| `codex/recovery-shell-frontend` | `e4239ebd` | 9 | 1061 | no | local historical frontend; no remote tracking |
| `codex/release-v0.6.9` | `c64278df` | 2 | 1060 | no | historical release evidence |
| `codex/v0.6.8-release-closure` | `42e7c0cc` | 2 | 1062 | no | historical release evidence |
| `codex/worker-quality-0906` | `4ca46eaf` | 0 | 921 | yes | ancestor but registered worktree; owner/worktree audit first |
| `docs/verification-summary-2026-08-09` | `8cc9c690` | 1 | 1372 | no | historical verification evidence |
| `feat/absorption-adopt-now` | `081cf20a` | 7 | 1362 | no | historical absorption work |
| `feat/absorption-roadmap-r0` | `42d13c0b` | 7 | 1498 | no | historical roadmap |
| `feat/archeaxis-desktop-a1-violet-core` | `376281c6` | 5 | 1497 | no | superseded UI direction; preserve evidence |
| `feat/axw022a-pdf-http-endpoint` | `17ca9628` | 4 | 1369 | no | historical AXW work |
| `feat/axw022b-evidence-annotation` | `3edacbcb` | 2 | 1368 | no | historical evidence UI work |
| `feat/h2-bakeoff` | `376fb800` | 3 | 1359 | no | historical H2 work |
| `feat/h2-pipeline-integration` | `e1df9279` | 9 | 1303 | no | historical H2 work |
| `feat/ms00-c-release-identity` | `01e794d1` | 1 | 1443 | no | historical release identity |
| `feat/naming-step3` | `bc4a234f` | 1 | 1304 | no | naming evidence |
| `feat/p1-compat-kernel-hardening` | `a4f2de19` | 11 | 1399 | no | historical compatibility work |
| `feat/portable-data-root` | `4e1a3ed8` | 1 | 1460 | no | historical portable work |
| `fix/desktop-close-request-destroy` | `801edea8` | 1 | 1451 | no | historical desktop lifecycle |
| `main` | `e3875db0` | 0 | 0 | yes | protected baseline |
| `release/v0.4.0-contract` | `75cb72ef` | 4 | 1491 | no | release evidence; preserve |
| `work/tp12-facades` | `8d5ba104` | 1 | 1627 | no | historical facade work |

## Rules for any later merge/delete action

1. Re-read this table from live refs immediately before acting.
2. For each candidate, inspect unique commits and paths against current R6/M0
   authority; do not use ahead/behind alone.
3. Check registered worktrees with `git worktree list --porcelain` before
   deleting any branch or `.project-local/worktrees` directory.
4. Preserve or bundle history only after an exact path/hash manifest exists.
5. Merge, remote delete, bundle creation and worktree removal each require a
   separate owner-approved operation; this audit is read-only.
