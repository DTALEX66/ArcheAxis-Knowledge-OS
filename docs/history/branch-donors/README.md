# Branch-donor archives — 2026-09-26

Files that existed **only** on a branch, were absent from `HEAD`, and were
preserved here before the legacy-donor branches were deleted.

These are historical assets (handoff notes, dated intake records, a superseded
environment script), not active capability. Nothing here is imported by the
product. Each file is stored byte-for-byte as it appeared on its branch.

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

## Recovery

The deleted branches remain recoverable from their recorded tips; the commits
are still present in this repository (`git cat-file -t <tip>` returns `commit`):

```
git branch <name> <tip-sha>
```

The full disposition record, including the classification of every branch, is
`docs/current/AAOS-BRANCH-DISPOSITION-REVIEW-20260925.json` and the session
checkpoint `docs/current/AAOS-DSH-TAKEOVER-CHECKPOINT-20260926.md`.
