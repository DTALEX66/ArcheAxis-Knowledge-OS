# AAOS Commercial Frontend Completion Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the canonical Avalonia frontend as a polished, accessible, Core-backed AAOS desktop product and prove its critical user journeys on the exact local Candidate before any Green replacement review.

**Architecture:** Avalonia remains the only product shell and Rust Core remains the sole canonical writer. UI work consumes existing Core projections or adds narrowly scoped read/write contracts with Core tests; it never fabricates durable truth, reuses demo `localStorage`, or creates a second store. The plan separates UI composition, Core API contracts, visual assets, and runtime acceptance so independent work can proceed only on disjoint write sets and agreed interfaces.

**Tech Stack:** C# / Avalonia 12.1.2, Rust / Axum / SQLite Core, existing Python contract and runtime harnesses, indexed .NET/Cargo/MSVC/Windows SDK toolchains.

**Spec:** `docs/superpowers/specs/2026-09-21-aaos-p3-avalonia-first-use-design.md`; current binding scope and evidence: `docs/current/M0-DIRECTION-OVERRIDE-20260920.md`, `docs/current/R6-EXECUTION.md`, `docs/current/AAOS-UI-SUITE-COVERAGE-20260923.md`, and `docs/current/AAOS-UI-COMMERCIAL-AUDIT-20260923.md`.

## Global Constraints

- Preserve `AGENTS.md`, R6 TaskPack, M0 overlay, Core authority, indexed shared resources, and no-release boundary.
- Use only `docs/SHARED_RESOURCE_PATH_INDEX.md` as the external resource path authority; external resource contents and Green data are out of scope for this plan unless a specific R6/Owner gate later authorizes exact use.
- Preserve current user changes and unknown `docs/history/**`; no reset, clean, branch switch, blanket stage, or unrelated cleanup.
- Do not overwrite Green until R6 P0–P5 evidence is real and complete and the exact Green backup, process ownership, replacement, restart readback, recovery and rollback gates are satisfied.
- Keep ordinary unavailable domains truthful until their canonical Core contracts exist; navigation is not proof that domain behavior is implemented.
- Distinguish static contracts, build, Core integration, native GUI, Candidate, Green-installed and remote evidence; never promote one level into another.
- Use `.project-local/` via `scripts/runtime/dev.py` for build/run/evidence outputs and the indexed shared Python/.NET/Cargo environments.
- Parallel rule: one writer per checkout/write-set; use separate agents only for genuinely disjoint work, and record requested model/reasoning separately from actual runtime identity (which may be `UNKNOWN`).

## Current Snapshot / Already Completed Slice

- Native File/Navigate/View menu now exposes the same 16 destinations as the command palette, and `Ctrl+Alt+I` / `Ctrl+Alt+J` invoke their advertised Inspector/Activity Dock actions.
- Ordinary-source Reader now reloads durable Core jobs by `source_id`, distinguishes them from container members, renders pending/failed/error state, requires user selection and only enables successful `text` jobs; Core validates persisted `input_ref` before output read. It no longer relies on `_captureContexts` for Reader recovery.
- Current verification of the working tree: desktop navigation/learning contracts `215 passed, 1 external pytest-config warning`; Avalonia Debug build `0 warnings / 0 errors`; Rust `source_jobs_api` `1 passed` including empty/multiple/succeeded/pending/failed/unknown source; real CoreSupervisor harness passed through actual Python text extraction, Core stop/reopen on same SQLite, source-job projection readback, same text output readback and mismatch rejection; latest `git diff --check` passed. `cargo fmt --check` was not available because the indexed stable Rust toolchain lacks `cargo-fmt`.
- These changes remain uncommitted at parent HEAD `1dc0ee1d06b68afb0a71117d6363d519397932f0`; they are not a Candidate or Green update. Current CUA native inventory returned `apps=[]`.

---

### Task 1: Persist and restore ordinary-source Reader context

**Files:**
- Modify: `crates/archeaxis-api/src/runtime/mod.rs`
- Test: `crates/archeaxis-api/tests/runtime_jobs.rs`
- Create or extend only the focused Core read-projection module already used by runtime routes, if route code warrants extraction.
- Modify: `apps/ArcheAxis.Desktop/CoreTextOutputReader.cs`
- Modify: `apps/ArcheAxis.Desktop/MainWindow.axaml.cs`
- Test: `tests/runtime-paths/CoreSupervisor.Tests/Program.cs`
- Test: `tests/test_desktop_navigation_contract.py`

- [x] Expose existing `jobs.input_ref` in Core job status and verify real source/job identity before returning text.
- [x] Add a read-only source-to-jobs projection over persisted `jobs.input_ref`; return each job's ID, kind, state, latest attempt/error and source binding. Do not add tables or update APIs.
- [x] Define deterministic multi-job behavior in the UI: show eligible text jobs and require explicit selection when more than one succeeded; never silently select a stale job.
- [x] TDD Core API tests for no jobs, succeeded text jobs, pending/failed job, multiple jobs and unknown source. Verify the projection reads committed SQLite state after reopening Core.
- [x] Update Reader to restore a source and its eligible job after Desktop/Core restart using only authenticated Core projections; keep transform text labeled as extraction output, not Knowledge or original bytes.
- [x] Extend CoreSupervisor integration to stop/reopen Core against the same isolated workspace, query the source projection and read the same text output; reject a job belonging to another source.
- [x] Run `cargo test -p archeaxis-api --test source_jobs_api --locked --offline`, `dotnet run --project tests/runtime-paths/CoreSupervisor.Tests`, the focused desktop tests, and the Avalonia Debug build through the indexed toolchain.

### Task 2: Close navigation, command and assistive-technology semantics

**Files:**
- Modify: `apps/ArcheAxis.Desktop/MainWindow.axaml`
- Modify: `apps/ArcheAxis.Desktop/MainWindow.axaml.cs`
- Modify: `apps/ArcheAxis.Desktop/Themes/AaosTheme.axaml`
- Test: `tests/test_desktop_navigation_contract.py`

- [x] Expose all 16 command-palette routes in the native Navigate menu; route unavailable domains to their honest unavailable surface.
- [x] Implement and contract-test the menu-advertised Inspector and Activity Dock shortcuts.
- [x] Give each navigable primary/mobile/menu route an accessible current-page/selected semantic state, not only a visual `active` class; update it in the single `SetSection` route transition. Current-page names are synchronized; actual native UIA/screen-reader readback remains part of Task 6.
- [x] Audit every image in `MainWindow.axaml`: all four occurrences reuse the same illustration; the Home Hero keeps a descriptive alternative name (“星环知识图：资料、检索与灵感”), while the three repeated empty/unavailable-state copies are marked `AccessibilityView=Raw` and non-control elements because nearby text already conveys their state. Native UIA/screen-reader readback remains part of Task 6.
- [x] Add standard Alt+F/Alt+N/Alt+V access-key declarations for File/Navigate/View; verify actual IME/text-entry interaction in the native-window Task 6 pass before acceptance.
- [ ] Test route state synchronization across primary rail, mobile rail, native menu and command palette; test focus return after palette, Inspector and Activity Dock close; test Escape and Shift+Tab paths.
- [x] Run all navigation/learning contracts and Debug build; report static/build evidence separately from actual UIA/screen-reader verification. Native window and assistive-technology validation remains open in Task 6.

### Task 3: Reduce MainWindow coupling through incremental view extraction

**Files:**
- Modify: `apps/ArcheAxis.Desktop/MainWindow.axaml`
- Modify: `apps/ArcheAxis.Desktop/MainWindow.axaml.cs`
- Create: focused view files under `apps/ArcheAxis.Desktop/Views/` for extracted surfaces, starting with the independently bound Source Reader and Evidence surfaces.
- Modify: `apps/ArcheAxis.Desktop/ArcheAxis.Desktop.csproj` only if Avalonia's default compile/resource discovery requires an explicit item.
- Test: existing `tests/test_desktop_navigation_contract.py`, `tests/test_desktop_learning_review_contract.py`, and focused view contract tests.

- [x] Before extraction, record the event-handler/API boundary for the selected view and enumerate its named automation controls; do not move multiple coupled pages in one slice.
  - Boundary audit (2026-09-24): `MainWindow` retains CoreSupervisor lifetime, members/jobs/output HTTP, JSON identity/count validation, Core text-output read and source↔job revalidation, stale-request versions, global status/Inspector, cross-page navigation and return context. The new view owns only source-reader layout, control/automation names, list/detail rendering, local selection/keyboard behavior and responsive visual state. Typed inputs: source id, selected typed row collection/selection, summary/core note/status, detail/provenance/transform display state, action availability, compact state and return-action availability. Typed events: load, row selection, read transform (including Enter/double tap), open job, find in Library, copy provenance/citation, back to Library and back to Knowledge. Scope is limited to one Source Reader view; no Core, `CoreTextOutputReader`, database or runtime-harness edits.
- [x] Extract Source Reader presentation/state into a view with explicit typed inputs/events; keep `CoreSupervisor` ownership and HTTP calls in the established Desktop/Core boundary.
- [x] Add a view contract test proving member, single-source, pending, failed, mismatched and empty states are distinct and source identity is preserved.
- [ ] Extract Evidence presentation only after preserving its real Core anchor projection and truthful unavailable bundle state.
- [x] Build and run the focused page contracts after the Source Reader extraction; `218` desktop navigation/learning/motion contracts passed and Avalonia Debug build returned `0 warnings / 0 errors`. Native route behavior and visual/control readback remain Task 6.
- [ ] Do not perform a wholesale 4k-line code-behind rewrite or drive-by formatting.

### Task 4: Complete product visual assets and motion system

**Files:**
- Create or modify: `apps/ArcheAxis.Desktop/Assets/` for the application icon and approved page/state artwork.
- Modify: `apps/ArcheAxis.Desktop/ArcheAxis.Desktop.csproj` for the verified Windows application icon if the chosen format is supported by the indexed SDK.
- Modify: `apps/ArcheAxis.Desktop/Themes/AaosTheme.axaml`
- Modify: `apps/ArcheAxis.Desktop/MainWindow.axaml` only for the relevant themed components.
- Test: `tests/test_desktop_navigation_contract.py` and focused asset/theme validation.

- [ ] Use the audited AAOS suite's composition, state, focus and motion contracts as design references; do not copy demo state, `localStorage`, random metrics or fake graph data.
- [ ] Establish one AAOS desktop icon family and export an application/window icon plus only those page/state illustrations that solve a documented empty/loading/error state; use the image-generation skill only for raster artwork, then review and optimize each asset locally. (One Evidence empty-state illustration is generated and wired; the icon family/app icon and remaining hierarchy audit are open.)
- [ ] Give each core surface a distinct hierarchy using existing AAOS tokens and shared icon primitives rather than repeating one large illustration across unrelated unavailable states.
- [ ] Make motion tokens correspond to actual transitions: menu/palette/drawer/page and state feedback. Respect `AAOS_REDUCED_MOTION=1`, avoid animating essential status solely through motion, and prevent focus movement from being hidden during transitions. (Loading-state feedback and reduced-motion behavior are implemented; other transitions and native render review remain open.)
- [ ] Add asset dimension/format/size validation and token/selector tests; perform a visual render review at a clean unobscured native window before calling the asset/motion slice accepted. (Focused asset/theme contracts pass; native visual review remains NOT EXECUTED.)

### Task 5: Finish Core-backed frontend workflows and honest domain boundaries

**Files:**
- Modify only the relevant existing files in `apps/ArcheAxis.Desktop/` and `crates/archeaxis-api/` for each specific contract.
- Add route-specific Core tests in the owning `crates/archeaxis-api/tests/` module and Desktop contract/integration tests under `tests/`.
- Update: `config/desktop/routes-v1.json` only when a route/capability contract actually changes.

- [ ] Close Source → Library → Knowledge → Learning → Review using persisted Core readbacks; do not treat extracted text as accepted Knowledge.
- [ ] For Jobs and Settings, finish usable filtering/details/actions only where current Core projections and permission boundaries exist; keep current-session-only receipts clearly scoped until a persisted history contract is added.
- [ ] For Research, Plugins and Models, inspect the current canonical Core registry/readiness contracts; create a separate Core contract task for each missing projection before enabling product controls. Until then retain the explicit unavailable surface.
- [ ] For Original Editor, require a versioned source read/write contract with conflict detection, provenance and explicit save receipt before implementing editing controls; never write directly from Avalonia to Core SQLite or raw object storage.
- [ ] For Memory Map, continue to label current lineage as lineage; implement full graph interaction only when canonical persisted graph/edge projections exist.
- [ ] For Evidence bundles and citation insertion, implement only after canonical bundle and citation-write contracts exist; do not synthesize anchors, citations, accepted state or graph edges.
- [ ] Add UI tests for permission-denied, offline Core, missing data, stale async response, empty success, pending work, retry and successful persisted readback for every newly enabled action.

### Task 6: Prove responsive layout, keyboard, UIA and visual quality in a real window

**Files:**
- Modify: `scripts/` only if an owned, project-local native UI test runner is needed and reviewed.
- Add: focused UI automation tests and receipts under the existing project test/evidence conventions.
- Update: `docs/current/AAOS-UI-SUITE-COVERAGE-20260923.md` with exact source SHA, commands and evidence class after each verification wave.

- [ ] Restore or provide a supported native-window automation/readback surface; current CUA inventory is `apps=[]`, so source tests alone cannot satisfy this task.
- [ ] Launch the exact current Candidate in an isolated project-local workspace with the rebuilt Core and indexed workers; record executable hashes and owned process PIDs, and stop only those owned processes after the run.
- [ ] Capture unobscured screenshots and pointer/focus/UIA readbacks for all 16 route destinations, File/Navigate/View menus, Ctrl+K, Ctrl+Alt+I/J, Escape, drawer, dock, toast, forms, lists and error/permission states.
- [ ] Verify rendered layouts at 1024, 1200, 1280, 1440, 1920 and 2560 logical widths and 100%, 125%, 150% and 200% Windows scaling; record overflow, clipping, scroll behavior and focus visibility.
- [ ] Run keyboard traversal including Tab/Shift+Tab, Enter, arrow navigation, Escape, menu mnemonics, IME text entry and focus restoration; inspect UI Automation names/selected states and screen-reader announcements with an actual supported assistive technology.
- [ ] Review contrast, text scaling and Windows high-contrast behavior; keep any unavailable native tooling `NOT_EXECUTED` rather than inventing screenshot/accessibility evidence.

### Task 7: Complete the M0 P3 real learning Golden Journey

**Files:**
- Add or extend: an isolated end-to-end desktop journey harness under `tests/runtime-paths/` using existing launch/supervisor ownership patterns.
- Modify: only the UI/Core handlers needed to complete a failed real journey.
- Update: `docs/current/R6-EXECUTION.md`, `docs/current/R6-STATE.json` and current UI coverage only after evidence is read back; do not overwrite unrelated dirty state.

- [ ] Run an approved real first-use flow through the Avalonia controls: import a chosen document, observe the Core source/job receipt, read extracted text, open the resulting eligible Knowledge, load an Assessment, enter an answer, select a review grade and submit once.
- [ ] Read back the Core-owned answer/review event, due state, FSRS schedule and any available Mastery projection; report missing/open projections explicitly.
- [ ] Fully stop the owned Desktop/Core processes, relaunch against the same isolated workspace and verify source, job, Knowledge, Assessment, answer, review event and schedule identities and values.
- [ ] Verify idempotent replay does not create duplicate review events and that failed/offline/rejected actions do not display success.
- [ ] Require owner-supplied or explicitly authorized test content when the task requires actual personal/Green materials; otherwise use clearly labeled synthetic fixtures and do not call them a real user-data journey.
- [ ] Keep M0 P3 `PARTIAL` until the specified real UI and restart evidence is complete; headless learning smoke does not close it.

### Task 8: Build and stage an exact-SHA Local Green Candidate for owner review

**Files:**
- Modify: `docs/SHARED_RESOURCE_PATH_INDEX.md` only after an exact Candidate is rebuilt and verified.
- Write evidence only under: `.project-local/` via the indexed runtime/build scripts.
- Update execution/coverage receipts at their canonical current paths.

- [ ] Build self-contained Windows Desktop and canonical Rust Core from the exact approved source tree; bind indexed runtime/workers and verify all manifest hashes/provenance.
- [ ] Run the full affected Desktop/Core suites and TaskPack candidate verifier; reject stale-source Candidate assets.
- [ ] Run the full staged Candidate Golden Journey and native GUI checks, then cold-restart and re-read the same isolated workspace.
- [ ] Record Candidate SHA-256, file count/bytes, source SHA, test commands/results, GUI evidence and known open R6 items; verify Green has not changed.
- [ ] Stop at `LOCAL_GREEN_READY_FOR_OWNER_REVIEW` until the separate R6 owner gate explicitly authorizes exact Green backup/replace/restart/rollback. Do not release, sign, publish or push as part of this plan.

## Parallel Execution Map

| Workstream | Owner shape | Model/reasoning request | Dependency / write boundary |
| --- | --- | --- | --- |
| Core source-job read projection | one Core writer | `gpt-5.6-sol / medium` | Task 1 Rust API/tests only; UI consumes frozen JSON contract afterward |
| Desktop route/accessibility and Reader UI | one Desktop writer | `gpt-5.6-sol / low` for bounded code slices; `gpt-5.6-terra / low` for independent test audit | Task 1 contract first; UI files must not be concurrently edited by another worker |
| Asset and motion audit/design | read-only reviewer, then single asset writer | `gpt-5.6-terra / low` for inventory; imagegen tool for raster output when required | Design tokens/assets write-set separate from Core API; actual model metadata may be `UNKNOWN` |
| GUI acceptance runner | separate verification owner | `gpt-5.6-sol / medium` | Starts only after exact Candidate exists; writes receipts only to assigned `.project-local` run |
| Product/Core unavailable-domain contracts | one domain contract at a time | `gpt-5.6-sol / medium` | Each domain requires its own Core/API owner review; do not parallelize overlapping Rust routes or database ownership |

Agent display must identify the requested tier/effort honestly; unless runtime metadata explicitly confirms actual model and reasoning, record actual values as `UNKNOWN`.

## Exit Criteria

The frontend goal is not complete until Tasks 1–8 have evidence appropriate to their scope, enabled product controls have real Core-backed behavior, all current-route interactions are proven in the native window, the P3 restart journey closes with authority readback, and the exact-SHA Candidate is ready for owner review. No static-test count, successful compile or older Candidate may substitute for missing current-SHA runtime/UI evidence.
