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

## Plan-start Snapshot / Already Completed Slice (Historical; superseded by dated updates below)

- Native File/Navigate/View menu now exposes the same 16 destinations as the command palette, and `Ctrl+Alt+I` / `Ctrl+Alt+J` invoke their advertised Inspector/Activity Dock actions.
- Ordinary-source Reader now reloads durable Core jobs by `source_id`, distinguishes them from container members, renders pending/failed/error state, requires user selection and only enables successful `text` jobs; Core validates persisted `input_ref` before output read. It no longer relies on `_captureContexts` for Reader recovery.
- Verification at plan start: desktop navigation/learning contracts `215 passed, 1 external pytest-config warning`; Avalonia Debug build `0 warnings / 0 errors`; Rust `source_jobs_api` `1 passed` including empty/multiple/succeeded/pending/failed/unknown source; real CoreSupervisor harness passed through actual Python text extraction, Core stop/reopen on same SQLite, source-job projection readback, same text output readback and mismatch rejection; `git diff --check` passed. `cargo fmt --check` was not available in that environment snapshot. See the dated current-source receipts below for later verification.
- These changes remain uncommitted at parent HEAD `1dc0ee1d06b68afb0a71117d6363d519397932f0`; they are not a Candidate or Green update. Current CUA native inventory returned `apps=[]`.

### Historical receipt — 2026-09-25 manual Candidate journey (superseded)

- The current working-tree UIA run used the real Avalonia file picker to import an explicitly synthetic text fixture, read Core `source_id` / `job_id` / `succeeded` receipts, opened the same source in Reader, and read the persisted Core transform. In that same SQLite workspace, the UI then manually created a human-owned Knowledge Candidate, explicitly added it to Learning, submitted one review and cold-restarted Desktop/Core to read the source transform, Candidate, Assessment, answer and FSRS due state back. The Knowledge/Assessment remain unbound to the source (`source_id` / `anchor_id` null). Receipt and screenshots are recorded in the current R6 execution and UI coverage documents.
- Desktop ten-file suite: `272 passed, 2 warnings`; focused Core API tests: `10 passed`; Avalonia Release build: `0 warnings / 0 errors`; Core Release build: 2 pre-existing dead-code warnings. The UIA run used local Release outputs from a dirty tree at HEAD `a5de4b13474c217e7a9dd34b8cbfa402e8297780`, not an exact-tree Candidate.
- Historical evidence only: this manually entered Candidate had null source/anchor binding. The later source-bound UIA receipt below supersedes it for current journey status. It still does not close the all-route/accessibility/responsive matrix or M0 P3.

### Current-source refresh — 2026-09-25 source-bound Learning UIA

- A real Avalonia UIA session imported the isolated synthetic fixture through the native picker, read its Core source/job and persisted transform, created a human Candidate with a verified quote anchor, found Knowledge and transform through Library search, read Knowledge V3, explicitly enrolled it, and submitted one FSRS Good answer. Assessment and anchor both bind the same source; read-only SQLite confirmed one review event/key and an FSRS schedule.
- Desktop/Core were fully restarted against the same SQLite file. UIA reread source/job/transform, Candidate/source/anchor, Assessment, saved answer, due schedule and `Mastery closed=false`. Receipt: `.project-local/runs/be268a2d33/9324081705e0/artifacts/desktop-launch/10e5863c545247f2b09b2d53e86de78f/desktop-uia-source-bound-learning.json` (SHA-256 `DC6030A738C9817C5A0E4B8B12DB6718F5658A7295E46C78D42068A38A118153`). The final single-viewport screenshot is `learning-final-ui.png` (SHA-256 `96AEA87B81F4CBA0A6941905D1E217A39AF1372A4ED9C1846ED7A5D3DDF34898`, 1902×963).
- The screenshot revealed clipping for schedule JSON and long identifiers; the current UI formats schedule JSON as indented text and wraps Learning queue rows and Inspector titles. `test_desktop_learning_review_contract.py`: `25 passed`; `source_bound_knowledge_api`: `2 passed`; Avalonia Release rebuild: `0 warnings / 0 errors`.
- This closes the synthetic source-bound first-use/restart path. Mastery closure, exact-current-tree Candidate, native all-route/menu/keyboard/focus/IME/screen-reader verification, full responsive/DPI/contrast matrix, idempotent UI replay and R6 owner gates remain open.

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
- [x] Add static route/focus contracts proving command-palette execution uses the shared route transition, closes the overlay and restores its prior focus target; retain existing Inspector/Activity Dock Escape and palette Escape/Shift+Tab contracts. Native execution and real focus/UIA readback remain Task 6.
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
- [x] Extract Evidence presentation into `Views/EvidenceCenterView.axaml(.cs)` while preserving the Core anchor request/JSON parsing, stale-request ownership and Inspector projection in MainWindow; typed anchor-selection/navigation events, honest unavailable-bundle copy and responsive empty-state rendering stay in the view.
- [x] Build and run focused page contracts after Reader/Evidence extraction and route/focus assertions; latest desktop navigation/learning/motion contracts `219 passed`; indexed Avalonia Release build `0 warnings / 0 errors`. Native route behavior and visual/control readback remain Task 6.
- [x] Keep view extraction incremental; this work did not perform a wholesale code-behind rewrite or drive-by formatting.

### Task 4: Complete product visual assets and motion system

**Files:**
- Create or modify: `apps/ArcheAxis.Desktop/Assets/` for the application icon and approved page/state artwork.
- Modify: `apps/ArcheAxis.Desktop/ArcheAxis.Desktop.csproj` for the verified Windows application icon if the chosen format is supported by the indexed SDK.
- Modify: `apps/ArcheAxis.Desktop/Themes/AaosTheme.axaml`
- Modify: `apps/ArcheAxis.Desktop/MainWindow.axaml` only for the relevant themed components.
- Test: `tests/test_desktop_navigation_contract.py` and focused asset/theme validation.

- [x] Use the audited AAOS suite's composition, state, focus and motion contracts as design references; do not copy demo state, `localStorage`, random metrics or fake graph data.
- [x] Establish one AAOS desktop icon family and export an application/window icon plus only those page/state illustrations that solve a documented empty/loading/error state; use the image-generation skill only for raster artwork, then review and optimize each asset locally. App/window ICO now uses an original AAOS A/axis mark with multiresolution variants; visual native review remains Task 6.
- [x] Give each core surface a distinct hierarchy using existing AAOS tokens and shared icon primitives rather than repeating one large illustration across unrelated unavailable states. Duplicate Home illustration instances were removed from unrelated empty/unavailable surfaces; Evidence retains its state-specific illustration.
- [x] Make motion tokens correspond to actual transitions: menu/palette/drawer/page and state feedback. Respect `AAOS_REDUCED_MOTION=1`, avoid animating essential status solely through motion, and prevent focus movement from being hidden during transitions. Button, animated surface, ambient glow, route and loading selectors now use control-scoped transitions; reduced-motion selectors clear them and loading remains readable. Native motion/focus rendering remains Task 6.
- [x] Add asset dimension/format/size validation and token/selector tests; perform a visual render review at a clean unobscured native window before calling the asset/motion slice accepted. Static ICO/selector checks pass; native visual review is NOT EXECUTED and remains an acceptance gap.

### Task 5: Finish Core-backed frontend workflows and honest domain boundaries

**Files:**
- Modify only the relevant existing files in `apps/ArcheAxis.Desktop/` and `crates/archeaxis-api/` for each specific contract.
- Add route-specific Core tests in the owning `crates/archeaxis-api/tests/` module and Desktop contract/integration tests under `tests/`.
- Update: `config/desktop/routes-v1.json` only when a route/capability contract actually changes.

- [x] Close synthetic Source → Reader → Library → Knowledge → Learning → Review using persisted Core readbacks; Candidate remains `candidate` and the Human review flag remains required. Receipt confirms the source-bound anchor and Assessment, one FSRS review, and same-database cold-restart readback. Broader native accessibility/responsive acceptance remains Task 6.
- [x] Supplementary synthetic joined UIA evidence: within one isolated database, imported and read a local synthetic text file, manually created a human Candidate, explicitly linked that Knowledge to an Assessment, submitted one review, and cold-restarted to read each projection back. This demonstrates the current UI path but the Knowledge and Assessment have null source/anchor fields, so it does not close the source-linked workflow.
- [x] For Jobs and Settings, finish usable filtering/details/actions only where current Core projections and permission boundaries exist; keep current-session-only receipts clearly scoped until a persisted history contract is added. Jobs filters current-session Core receipts by all/processing/success/attention without changing the underlying Activity Dock list; persistence-history limitation is explicit. Settings stays read-only and avoids invented controls.
- [x] Re-audit the current Core route table and desktop route authority before wiring Research, Plugins or Models. Current Rust `router()` exposes no Research/Plugin/Model readiness projection; `config/desktop/routes-v1.json` also contains no such contract. Current `config/models.yaml` is explicitly adapter configuration (`stub/local-stub`, `simple/hash-embedding`), while `config/model-profiles/r6-capability-pool.json` identifies itself as historical and partial. The existing Python `provider_routing` parser is contract-only and not consumed by the formal Core/Desktop host; R6 records P0-H01 `BLOCKED_BY_AUTHORITY_DECISION`. Existing unavailable surfaces remain the truthful UI state.
- [ ] Research Core contract (R6 A06): define one versioned read-only derived projection binding results to canonical source IDs/revisions and exposing provider/version, quality and empty/error state before Research controls are enabled.
- [ ] Plugin readiness Core contract (R6 A02/P0-H01): freeze the authoritative publisher, generation, health and fallback lifecycle and crash-safe readback; the authority decision currently blocks host integration. Keep plugin controls unavailable until resolved.
- [ ] Model readiness Core contract (R6 A11): define current runtime/model identity, measured availability, quantization/resource evidence and fallback from a live authoritative source. Historical pool entries and stub defaults are not current readiness; keep model activation controls unavailable.
- [ ] For Original Editor, require a versioned source read/write contract with conflict detection, provenance and explicit save receipt before implementing editing controls; the current Core route table has no such contract. Never write directly from Avalonia to Core SQLite or raw object storage.
- [ ] For Memory Map, keep the current `supersedes`/`superseded_by` Knowledge lineage labelled as lineage; R6 A06 graph work needs canonical persisted graph/edge projections before full graph interaction.
- [ ] For Evidence bundles and citation insertion, first define separate canonical bundle-read and citation-write contracts; the current Core route is anchors-only read (`/api/v1/evidence/anchors`). Do not synthesize bundles, citations, accepted state or graph edges.
- [x] Add UI tests for permission-denied, offline Core, missing data, stale async response, empty success, pending work, retry and successful persisted readback for every newly enabled action. Existing state contracts and the current five-file desktop/Evidence test wave pass; native UI interaction evidence remains Task 6/7.

### Task 6: Prove responsive layout, keyboard, UIA and visual quality in a real window

**Files:**
- Modify: `scripts/` only if an owned, project-local native UI test runner is needed and reviewed.
- Add: focused UI automation tests and receipts under the existing project test/evidence conventions.
- Update: `docs/current/AAOS-UI-SUITE-COVERAGE-20260923.md` with exact source SHA, commands and evidence class after each verification wave.

- [x] Restore or provide a supported native-window automation/readback surface; current CUA inventory is `apps=[]`, so source tests alone cannot satisfy this task. Windows `UIAutomationClient` was loaded locally and successfully read the real Avalonia window, navigation state, Learning controls and post-restart answer projection; full route/accessibility/layout coverage remains below.
- [x] Supplementary static keyboard contracts now require Source Reader and Evidence list Enter activation to invoke the selected-row action and leave unrelated keys unhandled; the focused navigation suite passed `202` tests, and the canonical ten-file Desktop/runtime/routes/navigation/motion/learning/launch/workspace-UI/Evidence suite passed `279` tests after isolating the launch contract's state path. This is source regression evidence only; native traversal and UIA readback remain open.
- [x] Launch B10 Candidate `b10-home-shell-2994efa-20260926` in an isolated project-local workspace with packaged Core/workers; record Desktop/Core hashes and owned PID, read the native window with UIA, and stop the owned process. Receipt and exact scope are recorded in `docs/current/AAOS-UI-SUITE-COVERAGE-20260923.md` (2026-09-26 B10 current Candidate launch readback). Keyboard injection was not delivered and remains open.
- [ ] Capture unobscured screenshots and pointer/focus/UIA readbacks for all 16 route destinations, File/Navigate/View menus, Ctrl+K, Ctrl+Alt+I/J, Escape, drawer, dock, toast, forms, lists and error/permission states.
- [ ] Verify rendered layouts at 1024, 1200, 1280, 1440, 1920 and 2560 logical widths and 100%, 125%, 150% and 200% Windows scaling; record overflow, clipping, scroll behavior and focus visibility.
- [x] 2026-09-26 partial responsive readback: current B10 Candidate sampled both sides and equality at the 840/1024/1280/1440 logical breakpoints, with `GetWindowRect`/`GetClientRect`/`GetDpiForWindow` and UIA at 120 DPI. Primary/context visibility followed the 840/1024 boundaries; mobile rail horizontal `ScrollPattern` reached the final navigation controls. Receipt: `.project-local/runs/aaos-ui-current-candidate-20260926/b10-breakpoint-neighbors-120dpi.json`. The full planned width/height/DPI matrix, screenshots/overflow review, all routes, and fresh narrow-start inspector state remain open.
- [ ] Run keyboard traversal including Tab/Shift+Tab, Enter, arrow navigation, Escape, menu mnemonics, IME text entry and focus restoration; inspect UI Automation names/selected states and screen-reader announcements with an actual supported assistive technology.
- [x] Supplementary single-viewport visual sample: captured the real Reader and post-restart Learning window at 1902×963 using `PrintWindow` and visually reviewed the screenshots. Latest post-restart Learning capture: `.project-local/runs/be268a2d33/9324081705e0/artifacts/desktop-launch/10e5863c545247f2b09b2d53e86de78f/learning-final-ui.png`. Review found and led to fixes for clipped long IDs and compact schedule JSON. This does not cover the responsive/DPI matrix or full-screen readability review.
- [x] Supplementary native route smoke: UIA invoked the 12 primary rail destinations and four context subnavigation destinations, and verified the visible page heading for all 16 route IDs. This did not exercise the File/Navigate/View menus, command palette, pointer/keyboard route selection, focus restoration or route screenshots.
- [ ] Review contrast, text scaling and Windows high-contrast behavior; keep any unavailable native tooling `NOT_EXECUTED` rather than inventing screenshot/accessibility evidence.
- [x] 2026-09-25 follow-up: extracted Source Reader and Evidence views now consume theme-injected responsive breakpoints; Evidence status receives a flexible column and moves below the refresh button on narrow layouts. Static navigation/layout contracts `203 passed`, motion/routes contracts `9 passed`, and isolated Release build `0 warnings / 0 errors` (DLL SHA-256 `683E917A057C340DD6643BFBBBB8469AC58BD999BAED05CF6E2FA25C2D3147ED`). This closes only the local layout source/build slice; native viewport/DPI, accessibility and visual acceptance remain open.
- [x] 2026-09-25 native short-height rail fix: a current-working-tree screenshot showed the fixed primary StackPanel drawing its lower routes below the workspace row and under Activity Dock. Added an accessible vertical ScrollViewer around the rail. The focused UI contract now passes, current Release build is 0 warnings/errors, UIA confirms the route rail scrolls, visually inspected top/bottom captures show lower routes in-view, and the current-build native route smoke passed 16/16. Keyboard/menu/command-palette, full DPI/contrast and 2560-logical-width checks remain open.
- [x] 2026-09-25 isolated dirty-working-tree native route capture: UIA `InvokePattern` visited the 12 primary routes and four context destinations; `WorkspaceHeadingText` and route current-page semantics matched 16/16, and all 16 per-route `PrintWindow` PNG hashes verified. Receipt: `.project-local/runs/be268a2d33/frontend-ui-route-2026/artifacts/route-screenshots/uia-all-routes-v1.json`. The app window was not foreground (`GetForegroundWindow=0`), so these are target-window captures rather than proof of unobscured desktop visibility; no menu, pointer, keyboard, IME or screen-reader acceptance is claimed. The instance used a fresh isolated SQLite workspace and was closed normally.
- [x] 2026-09-25 menu input probe: on a separate owned test Desktop, UIA exposed File/Navigate/View top-level menu items as focusable but only with `ScrollItem`; `Invoke` and `ExpandCollapse` were not available. `SetFocus()` reported keyboard focus, but `GetForegroundWindow()` remained zero; the `Alt+N` `SendKeys.SendWait` attempt threw and the UIA menu-item count stayed at three. Receipt `.project-local/runs/be268a2d33/frontend-menu-uia-2026/artifacts/uia-menu-input-attempt.json` classifies this as `NOT_EXECUTED_INPUT_UNDELIVERED`, not a menu pass. Do not substitute this for native menu/keyboard acceptance.

### Task 7: Complete the M0 P3 real learning Golden Journey

**Files:**
- Add or extend: an isolated end-to-end desktop journey harness under `tests/runtime-paths/` using existing launch/supervisor ownership patterns.
- Modify: only the UI/Core handlers needed to complete a failed real journey.
- Update: `docs/current/R6-EXECUTION.md`, `docs/current/R6-STATE.json` and current UI coverage only after evidence is read back; do not overwrite unrelated dirty state.

- [x] Run a real native-window first-use flow with explicitly synthetic local content: import through the Avalonia picker, read Core source/job/transform, create a source-bound human Candidate from an exact quote, find Knowledge through Library, load its bound Assessment, enter an answer, select a review grade and submit once.
- [x] Read back the Core-owned answer/review event, due state, FSRS schedule and Mastery projection; actual result is one saved event, FSRS authority/state/due exposed, Mastery `closed=false`.
- [x] Fully stop the owned Desktop/Core processes, relaunch against the same isolated workspace and verify source, job, Knowledge, anchor, Assessment, answer, review event and schedule identities and values.
- [x] Verify Core/headless idempotent replay does not create duplicate review events: an actual `--learning-smoke` run reused the same `client_event_id`, required `duplicate=true`, observed exactly one event and the same event ID after Core restart. UI failure/offline/rejected-state behavior has a new source contract; native error-path interaction remains open.
- [x] Supplementary synthetic native UIA journey: seeded the isolated workspace using the explicitly synthetic headless Core smoke, then used UIA to load the Learning queue, enter an answer, select the outcome and FSRS rating, submit once, close Desktop/Core, relaunch against the same database and read the answer and open Mastery projection. This does not satisfy the chosen-file import → source/job → source-bound Knowledge part of the required journey.
- [x] Supplementary synthetic file-to-Reader UIA journey: used the real Avalonia file picker for a synthetic text fixture, read Core source/job receipts, opened the source Reader, selected the persisted successful text job, and read the Core transform. Same-workspace SQLite readback confirmed one source, one succeeded bound job and one transform, with zero anchors and zero Knowledge. This is a separate workspace from the Learning UIA run and does not close source-bound Knowledge or Task 7.
- [x] Latest source-bound UIA supplement supersedes the older manually entered Candidate receipt above: the Candidate was created through the Reader exact-quote action, and SQLite confirms the Knowledge anchor plus Assessment carry the same source/anchor identity. The earlier receipt remains historical evidence of a different journey and is not upgraded.
- [x] Preserve the test-data boundary: this journey used only explicitly labeled synthetic fixtures; no personal/Green material was requested or accessed, and the receipt is not described as a real user-data journey.
- [ ] Keep M0 P3 `PARTIAL` until the specified real UI and restart evidence is complete; headless learning smoke does not close it.
- [x] Supplementary HEAD Candidate CLI smoke: the verified committed-HEAD Candidate Desktop/Core/bundled scheduler completed a synthetic answer → FSRS review → duplicate replay → Core restart readback against a fresh project-local DB; exit `0`, `Mastery closed=false`, Candidate manifest stayed valid, and Candidate-owned processes exited. The receipt is headless and from committed HEAD, not the dirty working-tree Candidate; it does not close this task's native P3 journey or Mastery.

### Task 8: Build and stage an exact-SHA Local Green Candidate for owner review

**Files:**
- Modify: `docs/SHARED_RESOURCE_PATH_INDEX.md` only after an exact Candidate is rebuilt and verified.
- Write evidence only under: `.project-local/` via the indexed runtime/build scripts.
- Update execution/coverage receipts at their canonical current paths.

- [x] Build self-contained Windows Desktop and canonical Rust Core from exact source `a5de4b13474c217e7a9dd34b8cbfa402e8297780` / tree `a4156ed65d50675822321b9d63eec932b1e76af3`; bind indexed runtime/workers and verify manifest hashes/provenance (`ok=true`, 21474 files, no problems).
- Current-source progress: the above committed-HEAD Candidate verifier was re-run successfully; the current ten-file Desktop suite (`279 passed`), Candidate regression contracts (`48 passed, 1 skipped, 4 process-reaping cases deselected`) and full `archeaxis-api` crate suite passed under the indexed MSVC/SDK and Candidate Python/scheduler environment. The dirty working-tree changes are not included in that HEAD Candidate, and three unfiltered Candidate process-reaping cases fail because `taskkill.exe` returns nonzero in this sandbox; these distinctions remain open for final qualification.
- A second exact-HEAD verifier pass after the Candidate's isolated `--learning-smoke` returned `ok=true`, `21474` files and no problems; the smoke run passed and left no Candidate-owned process. Its evidence is headless and does not qualify the dirty working-tree source or GUI.
- The current uncommitted `archeaxis-api` also builds in Release under an isolated `.project-local` Cargo target (`FE7CD08C31F0FE0DDCE32194018F9D12FAC13D677B361EAB5B3D6D565444D103`). The shared Release executable remained locked by an existing process and was not terminated. This build is not a staged Candidate.
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

## Continuation update — 2026-09-25 frontend follow-up

- Rechecked the Research data contract before enabling controls. At that point the review incorrectly treated transform rows as lacking a derivable source revision. The later R6 correction establishes that `transforms.source_id` joins to the canonical source's unique `sources.sha256`, which can supply the revision. Research remains unavailable pending the versioned read projection's provider/version, quality, empty/error semantics, runtime readback and benchmark; no source revision should be invented.
- Focused contracts: `tests/test_desktop_navigation_contract.py tests/test_desktop_routes_v1.py -q -p no:cacheprovider` — **212 passed** (one environment config warning).
- Full repository pytest collection: `BLOCKED_COLLECTION` because the indexed AAOS UI Python lacks runtime dependencies including `onnxruntime`, `fsrs`, and `jiwer`; no package installation was attempted.
- Avalonia Release compile through the managed dev runner: **0 errors**, two NU1900 vulnerability-feed warnings. The one-off output override did not create a retrievable DLL under its requested path, so this is compile-only evidence and cannot be used for runtime/Candidate claims. `git diff --check` passed with existing line-ending advisories; `R6-STATE.json` parses.
- No product source was edited in this follow-up. Tasks 5–8 and overall plan remain open for the exact Core authority contracts, dependency-backed full suites, native input/accessibility/DPI acceptance, dirty-tree Candidate, and final owner gates listed above.

## Continuation update — 2026-09-25 Candidate native-window availability check

- Reverified the exact committed HEAD/tree Candidate (runtime, workers and provenance required: `ok=true`, 21,474 files). Started its Desktop/Core through the isolated project launcher and confirmed Windows created a visible titled window; the fresh test DB stayed under `.project-local` and both run-owned processes exited cleanly.
- The supported `@oai/sky` app/window inventory did not return this process window, so no pointer, menu, keyboard, screenshot or accessibility interaction was possible. Do not check Task 6's interaction items or Task 8's dirty-tree Candidate gate from this launch. This is committed-HEAD process-launch evidence only.

### Current-source continuation — 2026-09-25 Knowledge V3 entry form

- [x] Wire ordinary human Candidate creation to explicit Core V3 source type, support level, optional confidence, required risk level, optional canonical UTC validity bounds and external-evidence reference lines. Keep trusted owner, Candidate status and human-review requirement fixed; do not infer source/anchor binding.
- Verification: new static contract failed before implementation on the missing controls; focused contracts `2 passed`; full navigation/Knowledge file `205 passed`; indexed .NET 10.0.400 Release build `0 warnings / 0 errors` (DLL SHA-256 `943C36B07148AD6D2B38F69885A775DC1A9478135ADDEA430D89EF652123D86A`).
- Evidence is from the dirty local working tree at HEAD `a5de4b13474c217e7a9dd34b8cbfa402e8297780`. This closes the A04 V3 form-entry slice only; cold restart, real first-use, full A04/A12 and native GUI acceptance remain open. No Candidate provenance or R6 state promotion is claimed.

### Current-source continuation — B10 Home shell and native visibility

- At 1920 logical pixels, Home previously hid the context rail and left the evidence inspector closed, contradicting the supplied B10 four-column reference. Home now retains the context rail; the first wide-screen layout defaults the evidence inspector open while retaining its toggle and narrow drawer behavior.
- RED→GREEN static test verifies context and evidence columns at desktop width. Related contract wave: 264 passed. Candidate `b10-home-shell-2994efa-20260926` launched in an isolated workspace; 1920x1010 native window and UIA confirmed context, evidence, current heading, and inspector close action on-screen. Candidate runtime/workers/provenance/current-source verifier passed (18,246 files). Receipt and hashes are in `docs/current/AAOS-UI-SUITE-COVERAGE-20260923.md`.
- Task 6 remains open: this is one Home viewport only, not the 16-route × viewport/DPI, keyboard/IME, focus, menu, screen reader, contrast or error-state acceptance matrix. Task 7/8 and overall frontend completion remain open.
