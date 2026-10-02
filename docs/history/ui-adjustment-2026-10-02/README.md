# 2026-10-02 UI adjustment package archive

`classification: HISTORICAL_RECORD_REFERENCE_NOT_CURRENT_AUTHORITY`

## What this is

The Owner-supplied **AAOS UI 深度调整包 · 2026-10-02**, archived whole: **52 members**,
**4,981,248 bytes**, SHA-256 `5A20BBDF0BB1A87AE80FF5B4C2672612AAEEEC32225BBD93722124F8DC660AB0`.

The zip is stored as delivered and its members are hashed from inside it, so the content is proven
without a second unpacked copy. Every member's SHA-256 is in `ARCHIVE_MANIFEST.json`.

## Why it is not unpacked into the tree

An unpacked copy was tried first. Ten of its files failed `check_repository_conventions.py`:

| Deviation | Files |
| --- | --- |
| missing final newline | 6 JSON files |
| trailing whitespace | 1 text file (`NotoSansSC-OFL.txt`) |
| UTF-8 BOM | 3 CSVs (`specs/02`, `specs/04`, `specs/05`) |

Editing them would break the byte-for-byte fidelity an archive exists for, and leaving them would
fail CI. Storing the zip whole satisfies both. The ten deviations are **recorded** in the manifest
under `members_not_matching_repo_conventions` rather than silently repaired, so a later reader knows
the package as delivered does not match this repository's formatting.

## What the package is

It converges the desktop interface into six spaces while keeping the full capability menu. Of itself
it states that it **follows the current R6/M0 implementation and does not establish a separate R7
authority**, that menu entries retained for long-term capability do not mean those capabilities are
developed now, and that the first job is to carry one real piece of material through import,
reading, evidence, knowledge, learning, machine correction and restart readback.

It also states what it is not: the screenshots and HTML are fixed samples, the preview calls no real
backend, performs no model call, uploads no file and writes no `localStorage`, and none of it is
evidence of a finished desktop, FSRS, machine learning or Green. **A web preview cannot stand in for
Windows native acceptance.**

## Contents

| Directory | Files |
| --- | --- |
| `00_先读我.md/` | 1 |
| `evidence/` | 5 |
| `integration/` | 6 |
| `preview/` | 10 |
| `prompts/` | 3 |
| `screenshots/` | 19 |
| `specs/` | 8 |

Notable members: `specs/01_信息架构与布局冻结.md`, `specs/02_19路由迁移.csv` (19 routes),
`specs/04_全能力菜单清单_50项.csv` (50 items), `specs/05_正式验收矩阵.csv`,
`integration/navigation-capability-registry.json`, `integration/route-migration-map.json`,
`integration/design-tokens.json`, and `prompts/03_DSH契约核对补充.txt` — the prompt addressed to
this executor, whose result is `docs/current/AAOS-UI-CONTRACT-VERIFICATION-20261002.json`.

## Boundary

Archiving is not acceptance and not authority to act outside the package. No existing UI asset,
worktree, PR or Green installation was modified, and nothing was merged.
