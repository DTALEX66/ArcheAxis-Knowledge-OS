# Green old linked-worktree review — 2026-09-30

## Decision

**KEEP; not a byte-identical duplicate.** The old UI checkout is a linked worktree of the Formal repository. Its `.git` pointer resolves to `D:\All projects\ArcheAxis-Knowledge-OS\.git\worktrees\ArcheAxis-Knowledge-OS1`. No `safe.directory` setting was added or changed. A normal `git -C` query was refused as dubious ownership; read-only status and revision queries were run using the explicit worktree Git directory and exact worktree root.

## Git and dirty-state evidence

- Old checkout: detached HEAD `7282e5a947dfcd7896e0a55af81635b8a013fee0`.
- Green mainline: `codex/aaos-ui-mainline-20260927`, HEAD `d8f99a6357405054f1f9ee66eb2f88d36f7f5143`.
- `git rev-list --left-right --count old...mainline`: `0 40`; the old committed baseline is an ancestor of mainline, 40 commits behind.
- Old worktree has 34 changed paths: 11 tracked modifications and 23 untracked files. Comparing the changed paths to mainline by SHA-256 found only 3 byte-identical files; 31 differ, totaling 810,742 bytes. The 31 differing files are preserved in the old worktree and are not represented by current mainline bytes at the same paths.
- The old committed baseline can be recovered from Git objects; its dirty and untracked files cannot be inferred from that baseline and must be preserved separately until reviewed or explicitly retired.

## Differing files to preserve

Tracked modifications (`M`):

- `apps/ArcheAxis.Desktop/Assets/aaos-app-icon.ico` — 16,395 B
- `apps/ArcheAxis.Desktop/MainWindow.axaml` — 153,951 B
- `apps/ArcheAxis.Desktop/MainWindow.axaml.cs` — 273,302 B
- `apps/ArcheAxis.Desktop/Themes/AaosTheme.axaml` — 28,342 B
- `apps/ArcheAxis.Desktop/Views/EvidenceCenterView.axaml` — 15,561 B
- `apps/ArcheAxis.Desktop/Views/EvidenceCenterView.axaml.cs` — 10,073 B
- `apps/ArcheAxis.Desktop/Views/SourceReaderView.axaml` — 11,492 B
- `docs/current/AAOS_VISUAL_QA.md` — 8,856 B
- `docs/current/UI_IMPLEMENTATION_REPORT.md` — 20,962 B
- `tests/test_avalonia_visual_authority.py` — 23,038 B
- `tests/test_desktop_navigation_contract.py` — 162,916 B

Untracked differing files (`??`):

- `apps/ArcheAxis.Desktop/AaosBrandMark.axaml` — 1,803 B
- `apps/ArcheAxis.Desktop/AaosBrandMark.axaml.cs` — 2,228 B
- `apps/ArcheAxis.Desktop/AaosIcon.axaml` — 1,012 B
- `apps/ArcheAxis.Desktop/AaosIcon.axaml.cs` — 3,407 B
- `apps/ArcheAxis.Desktop/AaosMemoryGraphView.axaml` — 6,184 B
- `apps/ArcheAxis.Desktop/AaosMemoryGraphView.axaml.cs` — 1,921 B
- `apps/ArcheAxis.Desktop/AaosMemoryMapConstellation.axaml` — 843 B
- `apps/ArcheAxis.Desktop/AaosMemoryMapConstellation.axaml.cs` — 3,345 B
- `apps/ArcheAxis.Desktop/AaosReviewScheduleChart.axaml` — 2,670 B
- `apps/ArcheAxis.Desktop/AaosReviewScheduleChart.axaml.cs` — 200 B
- `apps/ArcheAxis.Desktop/Assets/aaos-brand-mark.svg` — 581 B
- `apps/ArcheAxis.Desktop/ThemePalette.cs` — 4,458 B
- `docs/current/AAOS-UI-FIDELITY-STATUS-20260927.md` — 43,385 B
- `tests/test_aaos_icon_b10_contract.py` — 2,277 B
- `tests/test_b10_brand_mark_contract.py` — 1,460 B
- `tests/test_evidence_detail_master_contract.py` — 2,415 B
- `tests/test_human_learning_b05_contract.py` — 1,568 B
- `tests/test_machine_learning_b05_contract.py` — 2,243 B
- `tests/test_review_chart_master_contract.py` — 1,925 B
- `tests/test_search_b05_contract.py` — 1,929 B

Three changed paths are byte-identical to mainline: `docs/current/UI_V3_PRODUCT_ROADMAP.md` (7,484 B), `tests/test_desktop_routes_v1.py` (9,051 B), and `tests/test_workspace_b05_contract.py` (1,098 B).

## Cleanup boundary

This review did not modify, archive, or delete the old checkout, `.git` pointer, source files, `data`, databases/WAL/SHM/locks, cache, or venv. Prior archive steps only compacted separately verified generated acceptance/build outputs. The remaining tree cannot be retired as a duplicate while these differing dirty files and runtime/cache ownership remain unresolved.

## Next safe handling

Before retiring the worktree, create a separate manifest-backed archive of the 31 differing files and their original relative paths, verify SHA-256 after extraction, and review whether each change is superseded by the current UI. Separately audit non-user-data `.project-local` content and active consumers. Only then decide whether the linked worktree can be removed; do not alter shared Git configuration to bypass ownership checks.
