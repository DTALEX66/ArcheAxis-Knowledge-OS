# DP-NF-07 · September repository / language / data gap audit

- task_id: `DP-NF-07`
- baseline_sha: `a9ead3e1597808ca751c6ccec1dba27bcfff5b4b`
- baseline_tree: `ce69abf1493481591534979be1223b1a447fc9bb`
- branch: `codex/dp-nf-07-20260925`
- scope: **read-only, this repository only**
- evidence class: `STRUCTURAL / READ-ONLY`
- **Nothing was moved, deleted, renamed, cleaned, migrated or re-indexed. All UNKNOWN stays UNKNOWN.**

## 0. Method and boundary

Checked, in this order: the loaded authority set (`AGENTS.md`, `docs/CONFIGURATION_AUTHORITY_INDEX.md`,
`docs/DOCUMENTATION_AUTHORITY_INDEX.md`, `docs/DIRECTORY_AUTHORITY_INDEX.md`,
`docs/LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md`, `docs/SHARED_RESOURCE_PATH_INDEX.md`), then the
tracked/untracked inventory of this repository, then the `docs/history/` migration record.

Explicitly **not** done: disk-wide scanning, Home/Temp enumeration, Green or other-project access,
cross-project reads, any destructive or index-modifying action. Where a fix needs either, this report
gives an exact path list and stops.

## 1. Two findings were investigated and **retracted** — recorded so they are not re-reported

**F1 (retracted). "`docs/DIRECTORY_AUTHORITY_INDEX.md` contains mojibake."**
A PowerShell `Get-Content` read of line 6 rendered as `鏈満鍏蜂綋璧勬簮鏍逛互 …`. Byte-level inspection
proves the file is clean UTF-8: line 6 begins `e6 9c ac e6 9c ba e5 85 b7 e4 bd 93 …` = "本机具体资源根以".
The garbling was a **console-decoding artefact of the reading process**, not file corruption. A
repository-wide strict check confirms the conclusion:

| Check | Result |
| --- | --- |
| Active docs (excluding `docs/history/`) failing strict UTF-8 decode | **0** |
| Files containing U+FFFD replacement characters | **0** |

**Consequence:** no encoding defect is reported. Any future audit must verify bytes, not console
rendering, before claiming a file is corrupted.

**F2 (retracted). "The naming terms found in active docs are violations."**
Most hits are in documents that are *supposed* to contain the old names — the naming authority's own
rejection table, the alignment matrix, or a superseded historical contract. They are recorded in §2
with that classification rather than as defects.

## 2. Language/naming boundary — verified state

Term occurrences across `docs/**/*.md` **excluding `docs/history/`**:

| Term | Occurrences | Classification of the files that contain them |
| --- | --- | --- |
| `Cognitive-OS` | 57 | Legacy/compatibility prose in preserved docs and the migration operator guide; `docs/DIRECTORY_AUTHORITY_INDEX.md` itself classifies `app/`, `shared/`, `knowledge_base/`, `inspiration_research/` as `LEGACY_SOURCE` / `MIGRATION_DONOR`, so legacy naming in legacy-facing docs is consistent with authority |
| `ArcheAxis OS` | 21 | Mostly `docs/NAMING_ALIGNMENT_MATRIX.md` (9 hits — a matrix *about* the old name) and `docs/truth/NAMING_CONTRACT_V2.md` (7 — the binding rejection table). Off-authority only if used as a **current product name**, which these do not do |
| `元枢` | 20 | Same two authority/matrix files plus a 2026-07-21 handoff |
| `Cognitive-Loop-OS` | 12 | Historical handoffs (`DEEPSEEK-*`), superseded |
| `ArcheAxis Star` | 1 | `docs/truth/NAMING_CONTRACT_V2.md:74` — the contract's own "已废止" (retired) list |

**Verdict: no current-product naming violation was found.** The terms are confined to
(a) the naming authority's own prohibition tables, (b) legacy-facing compatibility docs for paths
the directory index itself marks legacy, and (c) handoffs whose supersession is recorded. The
baseline `pyproject.toml` carries the V2 identity (`archeaxis-workspace`, `0.6.14`) and the README
carries the V2 product name.

**Residual risk (needs an owner, not a fix here):** the same term list appears in *branch* content
that has not been integrated — batch 03 (`docs/current/dsh-review/branch-batch-03.md`) records
`e02510c9` renaming surfaces to "ArcheAxis Workspace", an interim name outside V2. That is branch
history, not current truth, and is already reported.

## 3. `docs/history/` migration provenance — the material finding

`docs/DOCUMENTATION_AUTHORITY_INDEX.md:111` classifies `history/` as "Historical snapshots — Never
cite as current state", and the same index references only
`history/pre-v0.6.7-current-snapshots/README.md` as a historical snapshot index.

The migration moved a large amount of material into `docs/history/`, and **all of it is currently
untracked** (21 untracked entries under `docs/history/`). Cross-checking each subtree against the
authority indexes:

| `docs/history/` subtree | Present | Referenced by an authority index | Provenance record |
| --- | --- | --- | --- |
| `evidence/` | yes | yes (21 refs) | referenced |
| `plans/` | yes | yes (5 refs) | referenced |
| `handoffs/` | yes | yes (2 refs) | referenced |
| `closure-tasks/` | yes | **no** | **none found** |
| `desktop-attachments/` | yes | **no** | **none found** |
| `kanban/` | yes | **no** | **none found** |
| `migrated-windows-state/` | yes | **no** | **none found** |
| `sleep-mode/` | yes | **no** | **none found** |
| `sleep-tasks/` | yes | **no** | **none found** |
| `task-artifacts/` | yes | **no** | **none found** |
| `task-runtime-scattered/` | yes | **no** | **none found** |
| `HERMES_CLEANUP_2026-09-13.md` | yes | **no** | **none found** |
| `skill-call-index.json` | yes | **no** | **none found** |
| `worktree-preserved-diffs/*.patch` (8 files) | yes | **no** | **none found**; names indicate the source (`hermes__task-runtime__…`) but no generated-by receipt, no source SHA, no timestamp binding |

Additional verified facts:

- `docs/history/` has **no `docs/history/README.md`** at the baseline; there is no top-level index
  stating what the migration moved, from where, under whose authority, or what may be discarded.
- `docs/history/worktree-preserved-diffs/` contains **1 tracked file**
  (`worker-quality-0906-unique-20260918.md`) and **8 untracked `.patch` files** — i.e. a tracked and
  an untracked population coexist in one directory with no distinguishing record.
- `docs/DIRECTORY_AUTHORITY_INDEX.md` states "Classify and link before archival; history is not
  deletion evidence", and `AGENTS.md` §3 says ambiguous files must be "preserve[d] and mark[ed]
  unresolved rather than delete or move them". Both are satisfied today; the gap is the missing
  **classification record**, not any destructive act.

**Why this matters for September governance:** the directory index requires one AX-DIR-010-compliant
row per relocation (source and target path, owner, data class, hashes, consumer scan, rollback).
For 8 of 11 subtrees plus 3 loose files, no such row exists anywhere in the repository. The material
itself is preserved, so this is a **documentation/ownership gap, not a data-loss incident**.

### 3.1 Recommended owner and handling (proposal only)

| Item | Suggested owner | Suggested handling |
| --- | --- | --- |
| The 11 subtrees + 3 loose files in §3 | **UNKNOWN — requires owner identification** | Keep exactly as-is. Add a `docs/history/README.md` (or one AX-DIR-010 row per subtree) recording: source path, move date, moving authority, data class, and a retention statement. Do **not** delete, move again, or rename |
| `worktree-preserved-diffs/*.patch` (8) | UNKNOWN | Keep. Record source worktree/branch, base SHA and generation command per file, or mark `PROVENANCE_UNRECOVERABLE` explicitly |
| `docs/SESSION-RESTART-2026-09-12.md`, `HERMES_CLEANUP_2026-09-13.md` | UNKNOWN | Keep. Either index them as history or leave marked unresolved; they are not current authority |
| The 5 root-side `AAOS-*`/`DSH-DP-*` files in §4 | root/Codex lineage | Track them in the mainline commit that owns them, or classify as transient evidence |

Rollback for any of the above: none needed — no destructive action is proposed. If an owner later
authorizes removal, it must be a separate, exact-path, separately-approved operation.

## 4. Untracked inventory and ownership classification (this repository only)

Root untracked entries: **33**.

| Path | Ownership assessment |
| --- | --- |
| `apps/ArcheAxis.Desktop/Assets/aaos-app-icon.ico` | root/Codex UI write-set — active work, not orphaned |
| `apps/ArcheAxis.Desktop/Views/EvidenceCenterView.axaml(.cs)` | root/Codex UI write-set — active work |
| `crates/archeaxis-api/tests/source_bound_knowledge_api.rs` | root/Codex Core write-set — active work |
| `scripts/release/capture_source_snapshot.py`, `tests/test_candidate_source_snapshot.py` | root/Codex Candidate work — active |
| `docs/current/AAOS-BRANCH-COMMIT-PATH-AUDIT-20260925.json`, `AAOS-BRANCH-DISPOSITION-REVIEW-20260925.json`, `AAOS-LOCAL-REPOSITORY-LINEAGE-READBACK-20260925.md`, `AAOS-UNTRACKED-LINEAGE-METADATA-20260925.json`, `DSH-DP-TASK-ASSIGNMENTS-20260925.md` | root/Codex lineage — these are the audit inputs referenced by the DP task pack itself; they are **evidence**, and DSH deliberately did not commit them |
| `docs/history/**` (21 entries) | see §3 — **owner UNKNOWN** |
| `docs/current/SESSION-RESTART-2026-09-12.md` | owner UNKNOWN (not part of the 2026-09-25 lineage) |

**None of these is attributable to DSH.** Every path this DP run wrote lives inside its own
`.project-local/worktrees/…` checkout or in `docs/current/dsh-review/`, which is committed on the DP
branches below.

## 5. Normative contradictions found

| ID | Contradiction | Evidence | Severity | Suggested owner |
| --- | --- | --- | --- | --- |
| **G-01** | Authority requires a classification/owner row per relocated artifact; 11 subtrees and 3 loose files under `docs/history/` have none | `docs/DIRECTORY_AUTHORITY_INDEX.md` "Required records before a move" / AX-DIR-010 vs §3 table | medium — governance, not data loss | owner identification first |
| **G-02** | `docs/DOCUMENTATION_AUTHORITY_INDEX.md:111` declares `history/` a classified historical area, but there is **no `docs/history/README.md`** and only 3 of 11 subtrees are referenced anywhere | index line 111 + zero README at baseline | medium | documentation owner |
| **G-03** | A tracked file and 8 untracked `.patch` files share `docs/history/worktree-preserved-diffs/` with no record distinguishing them or stating generation provenance | `git ls-tree HEAD:docs/history/worktree-preserved-diffs/` vs `git status` | low–medium | migration owner |
| **G-04** | `AGENTS.md` §6 says live progress lives in `docs/current/R6-EXECUTION.md` / `R6-STATE.json`, yet five root-side `AAOS-*` audit/lineage documents and `DSH-DP-TASK-ASSIGNMENTS-20260925.md` sit untracked in `docs/current/` with no index entry | `docs/current` untracked list; `DOCUMENTATION_AUTHORITY_INDEX` has no row for them | low | root/Codex integration |
| **G-05** | `docs/current/AAOS-UNTRACKED-LINEAGE-METADATA-20260925.json` itself describes untracked lineage while being untracked | file present, absent from `HEAD` | low (self-referential, informational) | root/Codex |

No contradiction was found in: the shared-resource path boundary (five roots plus
`10-toolchains` are consistently described), the single-writer rule (Rust Core is consistently the
canonical writer), or the release freeze (`FROZEN` everywhere checked).

## 6. Boundary and data-provenance checks — results

| Check | Result |
| --- | --- |
| External shared roots referenced by an absolute path inside tracked code/docs | only via `docs/SHARED_RESOURCE_PATH_INDEX.md`, which is the declared authority; no competing default root found |
| `E:` / `F:` references in the audited docs | none introduced; the protected-drive rule is stated in `AGENTS.md` §3 and `scripts/runtime/dev.py` |
| Green material library or Green install read this run | **no** |
| Private agent state (`.codex`, `.zcode`, `.hermes` contents) read | **no** — `.hermes/` is classified `LEGACY_MIXED_PRESERVE`; only its documented classification was read, not its contents |
| Cross-project read/write | none attempted |
| Files moved/deleted/renamed by this task | **none** |

## 7. Status statement

- Nothing in this report changes R6/M0 state; release remains `FROZEN`.
- All `UNKNOWN` ownership in §3 and §4 **remains UNKNOWN**. This audit does not assign ownership.
- No cleanup, migration, index edit or archival action is proposed as executable without a separate
  exact-path owner authorization. §3.1 lists *recommended* owners and handling only.
- Where the task pack says to stop and hand back an exact path list rather than act, this report does
  exactly that (§3, §4).
