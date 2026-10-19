# AAOS P3 Avalonia First-Use Design

## Goal

Make the formal Avalonia shell a usable P3 first-use surface: users can switch between the core product domains, load a real learning item from Rust Core, submit an answer, and see persisted state after reopening the learning view.

## Boundaries

- `apps/ArcheAxis.Desktop/` remains the only product shell.
- Rust Core remains the canonical writer and source of learning truth.
- Existing import, learning, assessment, review, and restart-readback API calls remain the integration boundary.
- No second database, model provider, renderer runtime, Green replacement, installer, signing, release, or external-resource access.
- Unknown untracked `docs/history/` content is preserved.

### External-resource authority

All machine-local shared resources are identified only through
`docs/SHARED_RESOURCE_PATH_INDEX.md`; this P3 design does not create a second
path registry or infer a replacement path. The indexed resource IDs are
`shared_models`, `shared_tools`, `green_application`, `green_material_library`,
and `project_test_corpus`. Their roles remain distinct: `Model library` and
`OS External Configuration` are shared dependencies, `ArcheAxis.Knowledge.Green-x64`
is the preserved Green application, `资料库` is the real Green material library,
and `ceshi` is the approved project test corpus. P3 implementation and tests
must not enumerate, modify, migrate, or write to any of these roots; when a
boundary check is required, use `scripts/maintenance/check_resource_boundaries.py`
and its purpose-specific target (`test` or `integration`).

## Design

`MainWindow` keeps one window and one CoreSupervisor, but separates the shell into a primary rail and a content workspace. The rail exposes Home, Library, Learning, Jobs, and Settings. Navigation is UI state only; it must not invent domain data. Home keeps the existing import and resume actions. Learning keeps the current Core-backed assessment/review flow and becomes the first real product surface. Library uses the existing Core `/api/v1/search` projection and preserves the distinction between knowledge and extracted transforms. Jobs and Settings show honest unavailable/empty states until their Core projections are wired; they must not display synthetic counts or pretend to be complete.

The existing status banner remains the single global health surface. Navigation changes update the workspace heading and status text without restarting Core or DeepTutor. Learning continues to call the existing endpoints and keeps provenance, assessment binding, idempotent review IDs, answer persistence, and conservative mastery-projection wording.

## Verification

- Add source-level contract tests for required navigation labels, handlers, and honest placeholder states.
- Run the new Python contract test RED before changing production files.
- Run it GREEN, then run the existing desktop route, learning-contract, and output-routing tests.
- Build the Avalonia project with the project-local/registered .NET entrypoint when available; if unavailable, record `NOT_EXECUTED`.
- Do not claim GUI first-use or full restart runtime evidence from source tests alone.
