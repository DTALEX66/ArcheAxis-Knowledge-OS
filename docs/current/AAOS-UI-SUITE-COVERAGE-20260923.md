# AAOS UI Suite B03–B10 Coverage Matrix

Date: 2026-09-25 (verification refresh)
Scope: the canonical Avalonia surface in `apps/ArcheAxis.Desktop/`
Authority: the previously audited AAOS UI suite index and current R6/M0 UI
receipts. This matrix does not promote reference demos, static numbers or
`localStorage` into product truth.

## Evidence vocabulary

- `IMPLEMENTED_LOCAL`: the product source contains the bounded behavior.
- `TESTED_LOCAL_STATIC`: the behavior is covered by the direct desktop contract
  harness; this is not native GUI evidence.
- `TESTED_LOCAL_GUI_PARTIAL`: a bounded real-window UI Automation journey was
  read back locally; this does not imply full route, visual, accessibility or
  user first-use acceptance.
- `BLOCKED_CORE`: the requested product capability needs a Core read/write
  contract that is not exposed by the current canonical path.
- `UNVERIFIED_GUI`: native screenshot, pointer, focus-tree or timing evidence
  is still absent.

## Coverage

| Package | Absorbed contract | Canonical implementation evidence | Current verdict | Explicit gap |
| --- | --- | --- | --- | --- |
| B03 | AAOS information architecture and the September-authoritative black/white dark baseline, white/gray structure and low-saturation status colors | `MainWindow.axaml`, `AaosTheme.axaml`, `SetSection`; visual authority: `docs/current/UI_V3_PRODUCT_ROADMAP.md` | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC` | Startup window/client/root and Activity Dock bounds were read back at 125% DPI in one fresh Candidate window; native contrast, resized-state rendering, other DPI settings and full screenshot review remain `UNVERIFIED_GUI` |
| B04 | spacing/radius/density/breakpoint/motion resources and component states | `AaosTheme.axaml` resources; shared page/card/rail heading classes; Button/animated surface/ambient glow/route/loading control-scoped transitions; reduced-motion selectors clear transitions and retain readable status | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC` | Native timing and focus visibility remain open |
| B05 | Home, Capture, Library, Reader, Knowledge, Learning, Jobs, Settings and Recovery compositions | named surfaces in `MainWindow.axaml` and focused Reader/Evidence views under `Views/`; Core-backed handlers in `MainWindow.axaml.cs`; Jobs filters current-session receipts by state without changing Activity Dock; current synthetic native UIA journey covers picker import → Core source/job → Reader transform → source-bound human Candidate/anchor/V3 → Library search/Knowledge V3 → Assessment bound to source+anchor → FSRS review → same-database cold-restart readback | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC / TESTED_LOCAL_PORTABLE / TESTED_LOCAL_GUI_PARTIAL` | Evidence bundles, full Graph, Original Editor and citation picker remain Core-bound; Mastery projection is explicitly `closed=false` |
| B06 | loading/empty/error/permission/unavailable/disabled/keyboard/focus/responsive states | `SetStatus`, Home/Settings/status-text accessible-name synchronization, request-version guards, dynamic Inspector accessible-name refresh, unavailable structure, focus handlers, responsive layout code; UIA read actual file-picker, route, Reader, Learning controls, post-submit schedule and same-database restart projection | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC / TESTED_LOCAL_GUI_PARTIAL` | Full native state matrix, screen-reader announcement, complete visual rendering and assistive-technology readback remain `UNVERIFIED_GUI` |
| B07 | product-route discoverability, keyboard access and automation names | `CommandPaletteRoutes`, primary/mobile rails, all 16 native Navigate routes, File/Navigate/View Alt+F/N/V declarations, dynamic current-page names and action labels; static contracts confirm palette route execution uses the shared SetSection transition and returns focus; native UIA invoked 12 primary rail and four context-subnavigation routes and read all 16 headings | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC / TESTED_LOCAL_GUI_PARTIAL` | Native File/Navigate/View menu traversal, command palette, mnemonics/IME, focus restoration, route screenshots and DPI/zoom evidence remain open |
| B08 | reusable card, KPI, status, toolbar, provenance and selectable-result patterns | `aaos-card*`, card/lifecycle pointer-over feedback, `aaos-kpi`, `aaos-status`, `aaos-toolbar`, provenance classes and row templates | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC` | No second React runtime or demo persistence is imported |
| B09 | interaction references: command palette, drawer, toast, review selection and source chain | Command Palette, Inspector Drawer action reflow, Toast, Review Card, Evidence anchor → source_id → Source Reader chain, Home Hero ambient feedback, workspace route transition | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC` | Graph-node, citation insertion and native animation timing remain open |
| B10 | high-fidelity product hierarchy and visual direction | project-owned decorative Evidence empty-state asset, original multiresolution AAOS app/window ICO, duplicate unrelated Home illustrations removed, tokenized AAOS shell | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC` | Native 1920×1010 Home screenshot/UIA was read back; full route/viewport screenshot matrix, icon and contrast review remain open |

## Non-equivalence rules

1. `SourceReaderSurface` is an original/source projection reader, not an
   `Original Editor`; no persistence or citation-picker contract is invented.
2. The Memory Map currently renders only Core `Knowledge lineage`
   (`supersedes`/`superseded_by` and `source_id`); it is not a `MemoryGraph`,
   and no synthetic nodes, edges or metrics are rendered.
3. An unavailable product surface is a truthful Core boundary, not an incomplete
   demo filled with reference data.
4. Static contract tests do not promote the UI to native GUI PASS.

## Current verification anchor

- 2026-09-25 working-tree update: Evidence presentation is extracted to `Views/EvidenceCenterView.axaml(.cs)`; Core request/parsing/stale-response ownership and Inspector remain in `MainWindow`. Jobs current-session filtering, AAOS multiresolution app/window icon, duplicate-illustration removal and control-scoped motion selectors are included. Canonical ten-file Desktop/runtime/routes/launch/workspace-UI/Evidence test wave: `270 passed, 2 dependency warnings`; indexed Avalonia Release compile: `0 warnings / 0 errors`; `git diff --check` passed. Native UIA verified the real Avalonia window, Learning route and controls, submitted a synthetic answer, then read it after a cold restart against the same isolated database. Receipt: `.project-local/runs/be268a2d33/edec0b2284d1/artifacts/desktop-launch/02455268d8934d9daa911a87fe3c11df/desktop-uia-learning-journey.json` (SHA-256 `827E5220DFCBB01796DAA178E9AE6883CCB9B76F0A650211AD433776EAEDB625`). This is partial synthetic GUI evidence, not the full chosen-file/source/job journey, full accessibility/visual verification, or current exact-SHA Candidate evidence.

- Last source commit at verification: `1dc0ee1d06b68afb0a71117d6363d519397932f0` on
  `codex/aaos-p3-ui-convergence-20260922`; the native menu, all-route menu coverage,
  single-file Reader and Core `input_ref` projection in the receipt below are
  working-tree changes and are not part of that commit or a published Candidate.
- Latest ten-file Desktop/runtime/routes/launch/workspace-UI/Evidence contracts: `270 passed, 2 dependency warnings`; Avalonia Release build: `0 warnings / 0 errors`.
- Avalonia Debug build for this working tree: `PASS`, `0 warnings / 0 errors`; Avalonia build telemetry was opted out for this run because its default per-user log target was ACL-denied. No ACL was changed.
- Rust API `source_jobs_api`: `1 passed`, covering persisted source binding, multiple success jobs, queued and failed/error jobs, an empty source and unknown source. Initial RED was observed (`GET /sources/:id/jobs` returned 404 before route implementation).
- Real CoreSupervisor integration: `PASS`, including actual Python text extraction, deliberate source/job mismatch rejection, stop/reopen against the same isolated SQLite, source-job projection restoration, and reading the same text output after restart.
- Primary/mobile rail and all 16 native Navigate menu item names now announce `当前页面：...` for the active destination through the single `SetSection` transition; focused RED→GREEN contract and full desktop suites pass. Native UIA and assistive-technology readback remain unverified.
- Current-menu access keys `Alt+F/Alt+N/Alt+V` have RED→GREEN source contracts. Reader cards and detail labels distinguish container members from ordinary-source durable jobs; task cards display kind/state/attempt/error without asserting absent filename or SHA. The Home Hero's knowledge illustration has a descriptive alternative name; three duplicated state illustrations are marked decorative and excluded from control/content UIA views. Source Reader presentation/state is now extracted into a typed view with explicit events, and its static contracts cover member/source/job/error/mismatch/empty distinctions. An Evidence empty-state illustration is wired; loading feedback honors reduced motion. Latest contracts/build are recorded above. Actual native IME, focus, visual and UIA checks remain Task 6 `UNVERIFIED_GUI`; Green remains unchanged.
- The prior isolated Candidate and learning smoke evidence above belongs to its
  recorded historical source state; it does not verify this working-tree SHA.
- The bounded Learning interaction and cold-restart answer readback are
  `TESTED_LOCAL_GUI_PARTIAL` using Windows UIA. Native screenshots, full route
  traversal, menu pointer/keyboard traversal, complete focus/UIA tree, screen
  reader, high-DPI/resized pixels and the source-to-learning first-use path remain
  `UNVERIFIED_GUI`; the CUA surface inventory itself still returned `apps=[]`.
- Green remains untouched; these local tests/builds do not authorize or qualify a
  Green overwrite, install, signature, release, commit, push or CI result.

No Green directory, external resource root, protected history asset, credential
or unrelated dirty file was modified for this matrix.

## Current-source verification update — 2026-09-25 startup viewport bounds

- A fresh isolated current13 Candidate window was measured without resizing or
  sending input. At 125% DPI, the Win32 client area was 1902×963 and the Avalonia
  root matched the client bounds. Activity Dock summary and all three buttons
  ended at or above the client bottom; UIA reported each visible (`IsOffscreen=false`).
- A target-window `PrintWindow` capture measured 1920×1010 and included the
  footer. This disproves a general startup-state dock crop for this one viewport;
  it does not explain an earlier post-resize capture anomaly or establish a
  resize/DPI matrix pass.
- Receipt: `.project-local/runs/be268a2d33/4bd04b1cab63/artifacts/desktop-launch/1a2d9d77a20c4c1ca29df7574727133d/dock-bounds.png.json`;
  screenshot: `.project-local/runs/be268a2d33/4bd04b1cab63/artifacts/desktop-launch/1a2d9d77a20c4c1ca29df7574727133d/dock-bounds.png`.
- Evidence level: `TESTED_LOCAL_GUI_PARTIAL`; no product source change is warranted
  by this measurement alone.

## Current-source verification update — 2026-09-25 first-screen language pass

- Home now names the local data state and first-use actions in product language,
  reports unavailable optional capability state without internal `Sidecar` /
  `readiness projection` terms, and labels learning and receipt actions by what
  the user can do. Settings is named consistently in primary/mobile navigation;
  the default Inspector source/type labels are Chinese while actual IDs and
  returned values remain intact.
- Verification on this dirty working tree: six focused Avalonia/UI contract
  files — `260 passed`; Avalonia Desktop Release build with the registered SDK
  and process-scoped `AVALONIA_TELEMETRY_OPTOUT=1` — `0 warnings / 0 errors`.
- This source changed after Candidate `current13-20260925`; that Candidate is now
  historical and cannot verify these UI edits. A fresh current15 Candidate was
  assembled from source snapshot SHA-256
  `9a3da298e1beb522c793a4f4083208e45d8093bc8691d315ba9f47cc5eb08ed9` and passed
  `verify_green_candidate.py --require-runtime --require-workers
  --require-provenance --expected-commit <HEAD> --expected-tree <HEAD tree>
  --require-current-source --source-root <repo>`: `ok=true`, 18,200 manifest
  files, no problems. One real Avalonia startup/home readback at 125% DPI
  verified the updated workspace sentence, 1902×963 client, complete footer and
  no startup dock crop. Screenshot:
  `.project-local/runs/be268a2d33/0e37a9515507/artifacts/desktop-launch/ce83827550834c3bb8c7048cd57b96a4/current15-home.png`,
  SHA-256 `52F2DC8C8673DCA2F694AD84A05D687CC3D339A0DF002F1B42473A85F0E1B715`;
  readback JSON is adjacent as `current15-readback.json`.
- Candidate 15 visual evidence is one target-window PrintWindow + UIA startup
  sample. Keyboard/pointer/menu interaction, foreground confirmation, other
  widths/DPI, screen-reader and Golden Journey remain
  `NOT_EXECUTED / UNVERIFIED_GUI`.

## Current-source verification update — 2026-09-25 native UIA partial

- Startup UIA exposed a XAML initialization-order crash: `SelectionChanged`
  fired before `JobsResultsList` construction. Added a post-`InitializeComponent`
  readiness guard and regression contract; the targeted tests pass.
- Expanded the synthetic P3 Core smoke to replay an identical review event and
  verify `duplicate=true`, unchanged answer and the same numeric `event_id`
  before and after restart.
- Real Avalonia window UIA journey: route changed to Learning; loaded one
  synthetic Core queue item; entered the response, selected the outcome and
  FSRS Again, submitted, closed/relaunched Desktop/Core on the same isolated DB,
  and read back the saved response and Mastery projection state. Structured
  receipt and SHA-256 are recorded above.
- Evidence level is `TESTED_LOCAL_GUI_PARTIAL` only. No selected-file import or
  source/job-to-Knowledge path was exercised. The full GUI coverage list and
  exact-new-tree Candidate remain open; Green remains unchanged.

## Current-source verification update — 2026-09-25 synthetic file import and Reader

- Real Avalonia UIA opened the native file picker, selected an explicitly synthetic local text fixture and observed Core import completion (`1/1` received, `1/1` succeeded, `0` failed). Capture displayed the returned `source_id`, SHA-256 and `job_id`, with an explicit boundary that import does not imply Knowledge or Learning.
- UIA opened Reader from the selected source, selected its durable successful `text` job and read the Core transform. Reader displayed the same `source_id` and `job_id` and stated that the output is extracted text, not original bytes, a Knowledge conclusion, or accepted Knowledge.
- At this intermediate Capture-to-Reader snapshot, SQLite showed one source, one succeeded `text` job whose `input_ref` equals that source, and one transform; no Knowledge or anchors had been created yet. The same isolated workspace was later extended through the joined Candidate/Learning/review UIA journey below.
- Screenshot: `.project-local/runs/be268a2d33/4010e2994958/artifacts/desktop-launch/e2b4717acdd64ed7baee86a69a35aa54/source-reader-ui.png`; SHA-256 `4F6B8D316490F51840A3A269F234264BAEE3925E45F4CE52A9B2A139CD769D1E`. Captured through `PrintWindow`; desktop resolution/DPI matrix was not exercised.
- At this initial Capture-to-Reader snapshot, source-bound Knowledge and a joined source-to-review journey had not yet been exercised. The later same-workspace joined UIA update below adds the manual Candidate/review path but does not supply the missing source binding. All routes, keyboard/focus/screen reader, DPI/responsive matrix and exact-current-tree Candidate remain open; Green unchanged.

## Current-source verification update — 2026-09-25 joined synthetic first-use UIA

- In the same isolated SQLite workspace, the real Avalonia UI imported the synthetic text fixture, reopened the persisted Reader transform, then manually created Knowledge `k_1a6670aace54b6eafc00888b` as a human-owned `PERSONAL_DEFINITION` Candidate requiring review. The UI explicitly enrolled it and Core returned Assessment `assessment_3c6d0bc0021435019c4b144b`.
- Through real Learning controls, UIA entered `支撑点有三个，并且等距分布。`, selected `回答正确` and `FSRS Good`, and submitted once. Desktop/Core were closed and restarted against the same SQLite file; UIA reread the Reader transform, Candidate status/owner, Assessment identity, answer and due schedule.
- SQLite readback: source `src_11e5313996896ec3fc9a306c`; succeeded job `desktop-import-8d304590030e4392a71c0ce9afb7461d`; one transform; Candidate status `candidate`, owner `human`, `requires_human_review=true`; one card reference, Assessment, review event (`event_id=1`) and event key. Schedule authority is FSRS with state `learning`; Mastery projection is `closed=false`. The Knowledge and Assessment both have `source_id=null`, `anchor_id=null`; a filename written in Knowledge content is only user text, not a provenance binding.
- Structured UIA receipt: `.project-local/runs/be268a2d33/4010e2994958/artifacts/desktop-launch/e2b4717acdd64ed7baee86a69a35aa54/desktop-uia-joined-first-use.json`; SHA-256 `C1D1E16160D5C53552E6ACBDC50FC2B5A962755C1C94E2DAF2ACED9D6D433031`. Post-restart Learning screenshot: `.project-local/runs/be268a2d33/4010e2994958/artifacts/desktop-launch/e2b4717acdd64ed7baee86a69a35aa54/joined-learning-after-restart.png`; SHA-256 `8B7C6C258557C7E3A8901DD720688E2B9AFD41A3AC01D67E0067846382420C56`.
- Evidence: `TESTED_LOCAL_GUI_PARTIAL` in one same-database synthetic journey. Source-bound Knowledge, closed Mastery semantics, all 16 route / keyboard / screen reader / responsive / DPI checks, exact-current-tree Candidate and owner gates remain open. The screenshots are one 1902×963 sample, not broad visual acceptance.
- Current verification on the dirty working tree: ten-file Desktop/runtime/routes/launch/workspace-UI/Evidence suite `272 passed, 2 warnings`; focused Rust API tests `10 passed`; Avalonia Release build `0 warnings / 0 errors`; Core Release build has 2 pre-existing dead-code warnings.

## Current-source verification update — 2026-09-25 native 16-route smoke

- On a fresh isolated local Release workspace, UIA invoked the 12 primary rail destinations and the four contextual subnavigation destinations for Knowledge, Original Editor, Memory Map and Recovery. The visible page heading matched all 16 expected route headings; the 12 primary routes also exposed the current-page accessible name.
- Receipt: `.project-local/runs/be268a2d33/ea5c99b4b5ed/artifacts/desktop-launch/a53a39a2fde24ed7aa9095ccb8825983/desktop-uia-route-smoke.json`; SHA-256 `EDBCAED224BE3636F6B198C834E2270DD9ED154C08026AEE937A63250FDFB964`.
- This is route-button UIA evidence only. The menu bar and command palette were not opened because this isolated desktop session exposes no interactive keyboard/pointer input; File/Navigate/View menu paths, keyboard/focus, screen-reader, per-route screenshots, DPI/responsive and visual review remain open.

## Current-source verification update — 2026-09-24

- Exact source commit `a5de4b13474c217e7a9dd34b8cbfa402e8297780`, tree `a4156ed65d50675822321b9d63eec932b1e76af3`.
- Focused desktop/navigation/learning/motion/plugin/authority contracts: `226 passed`; Avalonia Desktop self-contained Release `win-x64` publish passed; Rust `source_jobs_api` integration test `1 passed`; Core Release build passed with two dead-code warnings.
- Isolated exact-SHA Candidate verifier returned `ok=true`, `files=21474`, `problems=[]`, confirming required runtime, workers, provenance, expected commit and tree. ZIP SHA-256 `B103452DFABDF86F54D833EEDF7E55BB7A72A44544EC76BA7FC324DB869FAA4E`; Candidate manifest SHA-256 `4B11B6853143E48B2F24A98839639535902A5BF914FA09DEF79BBD5C6F54392B`.
- This is partial local evidence. Full affected suites and the staged Candidate Golden Journey have not been completed. CUA inventory still has no AAOS application window, so native GUI, UIA/screen-reader, visual/DPI, and cold-restart checks are `NOT_EXECUTED / UNVERIFIED`; Green remains untouched and no owner gate is claimed.

## Historical attempt — 2026-09-25 source-bound Candidate UIA (superseded by Golden Journey below)

- Implementation: Core now reads a successful job's persisted transform, verifies a UTF-16 selection against that exact text, and atomically creates an anchor plus human-owned Knowledge Candidate with explicit human-review metadata. Desktop Reader exposes selectable transform text and a quote fallback; the API repeats the exact quote/source/job/transform checks. This is implementation and API coverage; it does not accept the Candidate or create an Assessment.
- Verification: `cargo test -p archeaxis-api --test source_bound_knowledge_api --offline` — 2 passed; `python -m pytest tests/test_desktop_navigation_contract.py -q -o cache_dir=.project-local/runs/frontend-current/pytest-cache` — 201 passed; `git diff --check` — exit 0 (only existing R6 line-ending advisories). Earlier in this turn the full API crate suite and Avalonia Release build were also run against this working tree and passed; the focused suite was rerun after the later UIA attempt.
- Native UI: `NOT_EXECUTED` for the new source-bound path. Reopening the native picker from the current test launch left Capture in “正在打开资料选择器” without a stable picker UIA window; a subsequent launch initially reported Core exited before readiness. The independently started Core was confirmed owned and stopped; the retry launched a connected Desktop/Core window, but the picker invocation again did not yield a discoverable dialog. No successful import, Candidate UI creation, Assessment, Learning review or cold-restart readback is claimed for this turn.
- Historical attempt outcome: `NOT_EXECUTED / UNVERIFIED_GUI` at that point in the session. The later “source-bound Learning Golden Journey” below supersedes this outcome and verifies the path. Native menus/command palette/keyboard/screen reader/visual/DPI/responsive and exact-current-tree Candidate gates remain open; Green untouched.

## Current-source verification update — 2026-09-25 source-bound Learning Golden Journey

- Native UIA used the actual Avalonia file picker to import the synthetic fixture, read the Core source/job receipt, loaded the persisted Reader transform, and created a human Candidate from an exact quoted UTF-16 range. The UI then found that Candidate and its transform through Library search, opened Knowledge V3, explicitly enrolled it into Learning, created/read its Assessment, submitted one correct answer with FSRS Good, and cold-restarted Desktop/Core against the same isolated database.
- Post-restart UIA read the same source, succeeded job, transform text, Candidate ID/status/owner/review flag, source ID, Evidence anchor/quote/range, Assessment ID, saved answer and schedule. Read-only SQLite confirmation: one source/job/transform, one bound anchor and Candidate, Assessment with the same source/anchor, one review event and event key, FSRS `learning` schedule with one scheduled and zero unscheduled events. Mastery remains `closed=false`.
- Structured receipt: `.project-local/runs/be268a2d33/9324081705e0/artifacts/desktop-launch/10e5863c545247f2b09b2d53e86de78f/desktop-uia-source-bound-learning.json`; SHA-256 `DC6030A738C9817C5A0E4B8B12DB6718F5658A7295E46C78D42068A38A118153`. Final post-restart visual sample: `.project-local/runs/be268a2d33/9324081705e0/artifacts/desktop-launch/10e5863c545247f2b09b2d53e86de78f/learning-final-ui.png`; SHA-256 `96AEA87B81F4CBA0A6941905D1E217A39AF1372A4ED9C1846ED7A5D3DDF34898`, 1902×963. It demonstrates one viewport only.
- Verification: `source_bound_knowledge_api` 2 passed; desktop learning review contracts 25 passed; Avalonia Release rebuild after readable schedule formatting and wrapped long Learning/Inspector labels: 0 warnings / 0 errors. The scheduler worker and indexed Python runtime were explicitly supplied for this clean journey; a separate earlier exploratory database without the scheduler environment remains preserved and is not included in this receipt.
- Status: `TESTED_LOCAL_GUI_PARTIAL`. This closes the synthetic source-bound UI/Core first-use and same-database restart path, not the wider native menu/keyboard/focus/screen-reader/visual/DPI/responsive matrix, Mastery closure, exact-current-tree Candidate, or R6 owner gates. Green remains unchanged.

## Current-source verification update — 2026-09-25 review replay and failure-state contracts

- An actual local Release `--learning-smoke` run used an isolated project-local SQLite database. It submitted the same review payload/client event key twice; Core returned `duplicate=true`, history remained exactly one event, and after Core restart the Assessment ID, event ID, answer and FSRS schedule read back. Mastery remained `closed=false`. Receipt output identifies item `p3-headless-learning-card-36b5ec13ba4348968342ef7a2ca270ba` and Assessment `assessment_0642c9f3fe9c0eeace60b6e3`; database SHA-256 `1FE8F6113488865C546D2FAA55B21482662CE4BE19D4F505EEEFA09BC3131489` at `.project-local/runs/be268a2d33/learning-replay-verified-20260925.sqlite`.
- Added a Desktop source contract that asserts failed validation, permission/HTTP rejection and interrupted submissions cannot report success; an answer and the same event identity remain available for retry; and the success toast/identity reset occur only after a successful Core response. Native UI error-path interaction remains unverified.
- Focused Learning review contracts: `26 passed`; ten-file Desktop/runtime/routes/launch/workspace/Evidence regression: `293 passed, 1 deselected` with short project-local pytest path. The excluded launch-preparation contract asserts the persistent shared test DB does not exist, but `.project-local/state/be268a2d33/desktop-test/workspace.sqlite` already exists and was preserved. An initial combined run with an overlong run ID also exceeded Windows temp-path limits in workspace API tests; a short-run retry passed all non-excluded tests. `workspace_api` alone additionally passed `31` tests.
- Indexed Avalonia Release build: `0 warnings / 0 errors`; `git diff --check` passes with existing R6 line-ending advisories. CUA native app inventory still returns `apps=[]`; a fresh test-launch receipt remains `PREPARED_NOT_LAUNCHED` and is not runtime evidence. Existing Desktop/Core processes were left untouched.
- Evidence boundary: `TESTED_LOCAL_CORE_SMOKE / TESTED_LOCAL_STATIC / TESTED_LOCAL_BUILD`; Core replay idempotency is verified. Native error/permission UI, menu/keyboard/focus/IME/screen-reader, full visual/responsive/DPI/contrast matrix, exact-current-tree Candidate and Owner gates remain open.

## Current-source verification update — 2026-09-25 domain route authority audit

- Current Rust `router()` and `config/desktop/routes-v1.json` were read directly: there is no Research, Plugin, or Model readiness projection. Research/Plugins/Models handlers only navigate to the shared honest-unavailable surface and do not call Core. `config/models.yaml` is product-internal adapter configuration (`stub/local-stub`, `simple/hash-embedding`); the R6 model pool is historical/partial. The provider-routing parser remains test-only and not wired into the formal host; P0-H01 is still `BLOCKED_BY_AUTHORITY_DECISION`.
- Separate gated Core contracts are recorded in the current frontend plan for Research (A06 derived source/version receipt), Plugin readiness (A02/P0-H01 lifecycle and health authority), Model readiness (A11 live inventory/runtime evidence), versioned Original Editor writes, persisted Graph edges, and Evidence bundle/citation APIs. No speculative controls/routes were enabled.
- Added static boundary contracts: `tests/test_desktop_routes_v1.py` and `tests/test_desktop_navigation_contract.py` — `209 passed`. This is local route/source evidence only; it does not qualify native navigation, Core readiness projections or those deferred domain capabilities.

## Current-source verification update — 2026-09-25 Evidence refresh empty state

- Evidence refresh now restores the empty-state panel whenever it clears the previous anchor list; successful nonempty anchor reads continue to hide it. This avoids a stale visibility state after refresh followed by an empty/error result.
- Navigation/route/Evidence contracts: `209 passed`; isolated indexed Avalonia Release build: `0 warnings / 0 errors`; DLL SHA-256 `87E7D3AC5196EA451138B783A3847D594F608AE3B5335EC19084F97DB8D179C0`.
- Scope is local static/build verification only. Native visual, permission/error-state, accessibility and responsive/DPI evidence remains open; the shared apphost stayed locked by an existing Desktop process, which was left running.

## Current-source verification update — 2026-09-25 isolated Release assembly smoke

- The isolated Release Desktop assembly was executed under the project runtime runner with a fresh synthetic workspace. `--learning-smoke` passed: answer saved, FSRS authority present, exact client-event replay produced one event, Core restart preserved the same event/Assessment/answer/schedule; Mastery remained `closed=false`.
- Runner receipt: `.project-local/runs/be268a2d33/dllsmokb/artifacts/execution.json` exit code `0`; database and WAL/SHM are preserved in that run's artifacts. Tested DLL SHA-256 `87E7D3AC5196EA451138B783A3847D594F608AE3B5335EC19084F97DB8D179C0`.
- This is isolated headless Core integration evidence for the built assembly, not native UI or exact-source Candidate qualification. Native routes/accessibility/responsive/DPI and full R6/P3 remain open.

## Continuation update — 2026-09-25 keyboard contract coverage

- Added a focused static contract for Source Reader and Evidence list Enter activation: each handler must invoke its selected-item action and mark Enter handled, while other keys are not consumed. This strengthens source-level regression coverage only; it does not qualify actual native keyboard traversal or assistive-technology behavior.
- Verification: `NOT_EXECUTED`. `python` is not on PATH; `.venv/Scripts/python.exe` is a uv trampoline whose child process launch returned permission denied; the project `dev.py` entrypoint also could not be launched directly in this shell. `git diff --check` passed and `R6-STATE.json` parsed successfully.
- CUA still has no native app surfaces (`apps=[]`), so native menu/pointer/focus/IME/screen-reader and responsive/DPI checks remain open.

## Current-source update — 2026-09-25 isolated launch contract and Release build

- Supersedes the immediately preceding `NOT_EXECUTED` pytest note: the indexed AAOS UI Python 3.12.13 / pytest 9.1.1 environment was found in `docs/SHARED_RESOURCE_PATH_INDEX.md`. The focused navigation contract passed `202` tests. The canonical ten-file Desktop/runtime/routes/navigation/motion/learning/launch/workspace-UI/Evidence regression passed `279` tests with no deselection.
- The launch-preparation contract now injects its own unique project-local state database path, preserving the test that two prepares share one stable DB path without touching the existing persistent desktop-test workspace. An initial full run exposed the pre-existing DB conflict (`278 passed, 1 failed`); after isolation, that test passed alone (`1 passed`) and the full ten-file wave passed (`279 passed`).
- Indexed .NET SDK `10.0.400` Release build of the current Avalonia project passed with `0 warnings / 0 errors`. Output DLL: `.project-local/runs/be268a2d33/frontrelbuild2/artifacts/desktop-build/Release/net10.0/win-x64/ArcheAxis.Desktop.dll`, SHA-256 `FFCEF2B063BCBF4077E4B6B744D640973DE31B0098D3756F02DF146B3AEB337C`. The prior build attempt without `AVALONIA_TELEMETRY_OPTOUT=1` failed on an ACL-denied user telemetry log and is not counted.
- This remains local source/test/build evidence, not native window verification or exact-tree Candidate qualification. CUA returned `apps=[]`; Task 6 native route/menu/keyboard/focus/IME/screen-reader/responsive-DPI/contrast checks, Task 7 full native journey acceptance, and Task 8 Candidate gates remain open.

## Current-source update — 2026-09-25 HEAD Candidate and Core API qualification

- Re-ran `scripts/release/verify_green_candidate.py` against `.project-local/build/green-candidates/ArcheAxis.Knowledge.Green-va5de4b13-x64` with expected HEAD `a5de4b13474c217e7a9dd34b8cbfa402e8297780` and tree `a4156ed65d50675822321b9d63eec932b1e76af3`; result `ok=true`, runtime/workers included, `21474` files, no problems. This artifact matches committed HEAD only and does not contain dirty working-tree changes.
- Candidate verifier/manifest/assembly/scheduler-binding regression wave: `48 passed, 1 skipped, 4 deselected`. The deselected parameterized process-reaping case was also attempted unfiltered: three cases failed because `taskkill.exe` cleanup returned nonzero in this sandbox. A follow-up process query found no matching test children alive.
- Full `cargo test -p archeaxis-api --offline` passed with the indexed MSVC/Windows SDK environment and Candidate-bundled Python 3.13.14 plus the canonical scheduler worker. The initial attempt without the Candidate runtime returned `schedule_authority=unavailable`; after binding the declared runtime/worker, all API tests completed successfully. Existing dead-code and test unused-variable warnings remain.
- Evidence is limited to current committed HEAD qualification and Core integration tests. It does not qualify the dirty working-tree Candidate, staged native Golden Journey, native GUI/accessibility/visual matrix, or Green installation.
- Current uncommitted API Release build also passed with the indexed MSVC/SDK in an isolated target directory after the shared `release/archeaxis-api.exe` was found locked by an existing process. Output `.project-local/runs/be268a2d33/aaoscorebuildrelease/artifacts/cargo-target/release/archeaxis-api.exe`, SHA-256 `FE7CD08C31F0FE0DDCE32194018F9D12FAC13D677B361EAB5B3D6D565444D103`; existing process was left untouched. Build emitted only the two known `archeaxis-application` dead-code warnings.

## Current-source update — 2026-09-25 HEAD Candidate headless learning smoke

- Executed the reverified HEAD-bound Candidate's `desktop/ArcheAxis.Desktop.exe --learning-smoke` with Candidate Core, bundled Python 3.13.14 and Candidate scheduler worker. A fresh synthetic database was isolated under `.project-local/runs/be268a2d33/candidateheadless2/artifacts/`; the app returned exit `0`, saved an answer, returned FSRS authority, replayed one review event idempotently and read back persisted state after Core restart. `Mastery projection closed=false` remains explicit.
- Runner receipt `.project-local/runs/be268a2d33/candidateheadless2/artifacts/execution.json`; item `p3-headless-learning-card-4e25c95b4b584151886bba3796b61a5a`; Assessment `assessment_664a82a48a4eb193bf0659e1`. Candidate Desktop SHA-256 `8191FBF2781EC57544917831FBBC62A67A12E3B6F077FDFFD60C65B670D9B1DE`; Core SHA-256 `19E136F806FEEC67CC9EC7A41ED9761A23014D53B039E480F9F373D5C66449FA`.
- After the run, no process with either Candidate executable path remained. Re-running `verify_green_candidate.py` with exact HEAD/tree still returned `ok=true`, `21474` files, `problems=[]`; the smoke DB and its WAL/SHM are outside the Candidate package.
- The receipt records the checkout as dirty because the working tree contains uncommitted changes; the executed binaries are still the earlier committed-HEAD Candidate and do not include those changes. This is a headless Candidate smoke, not the P3 native journey, GUI/accessibility acceptance or dirty-tree Candidate qualification.

## Continuation update — 2026-09-25 extracted-view responsive layout

- Source Reader now receives its stack and narrow-action breakpoints from shared AAOS theme resources instead of embedding `1200`/`760` in its size handler. Evidence receives the shell's shared narrow-action breakpoint; its toolbar gives the status text a flexible column beside the refresh action and moves the status below the action on narrow widths.
- Verification: `tests/test_desktop_navigation_contract.py` — `203 passed`; `tests/test_desktop_motion_contract.py tests/test_desktop_routes_v1.py` — `9 passed`; indexed .NET SDK `10.0.400` Release build to `.project-local/runs/frontend-responsive/desktop-build-absolute/` — `0 warnings / 0 errors`; DLL SHA-256 `683E917A057C340DD6643BFBBBB8469AC58BD999BAED05CF6E2FA25C2D3147ED`.
- An initial compile attempted the shared Release output and reported the existing Desktop executable was locked; that process was not stopped. The verified build was redirected to a unique project-local output. The first relative output attempt resolved beneath the Desktop project directory; final evidence comes only from the successful absolute project-local output above.
- Boundary: local source/static/build evidence only. Native width/DPI matrix, screen-reader, visual and high-contrast acceptance remain `UNVERIFIED_GUI`; CUA currently reports `apps=[]`. This does not qualify an exact-tree Candidate, Task 7, Green, or R6 owner gate.

## Current-source native update — 2026-09-25 short-height primary navigation

- Reproduction: current-working-tree `PrintWindow` at 1902×963 showed the fixed primary-rail StackPanel drawing Plugins/Models below the available row and behind the Activity Dock. The earlier UIA `IsOffscreen=false` values were insufficient to detect this clipping.
- Fix: wrapped the 12 primary route entries in named `PrimaryRailScrollViewer` with automatic vertical scrolling, disabled horizontal scrolling and accessible name `一级空间导航`. Added a regression contract requiring that container and preserving all 12 route controls.
- Verification: `tests/test_desktop_navigation_contract.py` — `204 passed`; isolated indexed .NET SDK 10.0.400 Release build — `0 warnings / 0 errors`; EXE SHA-256 `50B524A4483BE74A924244C019CD942E24B0AB23C7A79F344C49351FAAE2C42B`; DLL SHA-256 `3A70DDC5A86DEABFAD4DD0906AA2383377D5E3A6D33EF2133BAC9E325AE73F7B`. Current-build UIA route smoke — 16/16 page headings passed; 12 primary routes also matched the current-page accessible name.
- Short-window UIA at 1600×760 physical / 125% desktop scale: the rail exposed `VerticallyScrollable=true`; Models moved from y=947 outside the y=242..666 viewport to y=523 within it; System was also within the viewport. Screenshot pair `.project-local/runs/be268a2d33/aaos-railfix-49a619ab/artifacts/rail-top.png` (SHA-256 `723049AC4B68566C536FEB17D54D8675A3D9B077230BFA6EE4D97C826DCF0392`) and `rail-bottom.png` (SHA-256 `31C390DDD847FF3FF6EA253399673D8D4AD4E9A3448DAA70E454CA898F97024C`) was visually reviewed. Receipt `uia-primary-rail-scroll-v2.json` records element geometry as the movement proof; the provider's percent field stayed stale during that scroll and is not used as the pass condition.
- Current-source responsive geometry receipt: `.project-local/runs/be268a2d33/aaos-ui-cb7a908b/artifacts/uia-responsive-logical-geometry.json`. At 120 DPI, requested widths 1024–1920 logical were attained within window-frame allowance and Reader/Evidence breakpoint geometry matched; Windows capped the 2560 logical request at about 2051 logical, so 2560 remains unverified. System DPI was not changed.
- Boundary: current dirty working-tree Release build and isolated synthetic database only; no current-tree Candidate qualification. Native keyboard injection/Alt menu/Ctrl+K was `NOT_EXECUTED`: foreground activation was denied and `SendInput` returned 0. Screen-reader/high-contrast and full visual matrix remain open. Shared Desktop PID 20800 was not operated; only the owned isolated UIA instance was used.

## Current-source update — 2026-09-25 consolidated Desktop gate

- The canonical project test entrypoint ran all seven Desktop suites (`test_desktop_runtime`, `test_desktop_routes_v1`, `test_desktop_navigation_contract`, `test_desktop_motion_contract`, `test_desktop_learning_review_contract`, `test_desktop_launch`, `test_desktop_staging`): **264 passed**.
- The current dirty working tree built with indexed .NET SDK 10.0.400 through `scripts/runtime/dev.py`; Release result **0 warnings / 0 errors**. Output DLL SHA-256: `CDD796D6B01DD2EF1535A280EF7FE250E11E153C67F540F67A2EB194DE41232B` (`.project-local/runs/be268a2d33/frontend-release-0925/artifacts/bin/Release/net10.0/win-x64/ArcheAxis.Desktop.dll`).
- This refresh adds static regression/build evidence only. Native route/menu/palette/keyboard/IME/focus/permission/error/screen-reader/high-contrast checks and the full width × scaling matrix remain open; the 2560 logical width could not be reached. No exact-current-tree Candidate or Green operation is claimed.

## Current-source native update — 2026-09-25 all-route UIA capture

- On isolated test Desktop PID `26972`, UIA invoked the 12 primary routes and four context routes (Knowledge detail, Original Editor, Memory Map and Recovery). `WorkspaceHeadingText` and primary current-page semantics matched `16/16`. All 16 individual target-window PNGs were SHA-256 checked and visually reviewed at `1920×1010`.
- Receipt: `.project-local/runs/be268a2d33/frontend-ui-route-2026/artifacts/route-screenshots/uia-all-routes-v1.json`; per-route images are adjacent. Desktop EXE SHA-256 `50B524A4483BE74A924244C019CD942E24B0AB23C7A79F344C49351FAAE2C42B`; Core EXE SHA-256 `FE7CD08C31F0FE0DDCE32194018F9D12FAC13D677B361EAB5B3D6D565444D103`; Release DLL SHA-256 `CDD796D6B01DD2EF1535A280EF7FE250E11E153C67F540F67A2EB194DE41232B`.
- `GetForegroundWindow` returned `0` for this session; `PrintWindow` rendered the target HWND, so these screenshots do not establish an unobscured desktop or foreground focus. No File/Navigate/View menu, Ctrl+K/Alt shortcut, pointer/keyboard/IME, focus-return or screen-reader operation was executed. This is dirty-working-tree local UIA evidence, not an exact-SHA Candidate or Green run. The owned Desktop exited normally; an unrelated existing Core process was left untouched.

## Current-source native update — 2026-09-25 menu input probe

- UIA found the File/Navigate/View menu roots by accessible name. They are keyboard-focusable and on-screen, but their provider exposes only `ScrollItem`; `InvokePattern` and `ExpandCollapsePattern` are absent. UIA `SetFocus()` returned with `HasKeyboardFocus=true`, but the foreground HWND remained `0`.
- A single `Alt+N` `SendKeys.SendWait` attempt failed with `MethodInvocationException` (`操作成功完成`); menu descendants remained at three top-level items. This is `NOT_EXECUTED_INPUT_UNDELIVERED`, not a pass or a product bug determination. Receipt: `.project-local/runs/be268a2d33/frontend-menu-uia-2026/artifacts/uia-menu-input-attempt.json`.
- Owned PID `28408` exited through the UIA window close path and the dev runner returned `0`. This does not verify actual menu operation, command palette, shortcuts, IME, focus traversal or assistive technology.

## Current-source frontend follow-up — 2026-09-25

- Route/navigation contracts: 212 passed with the indexed AAOS UI Python environment. The full repository test collection is `BLOCKED_COLLECTION` by missing optional runtime dependencies (`onnxruntime`, `fsrs`, `jiwer`, PDF-reading requirements); no dependency was installed.
- Release compile: completed through the managed dev runner with 0 errors and two NU1900 warnings caused by an unreachable NuGet vulnerability feed. The one-off output override yielded no retrievable DLL at its requested location; count as compile-only, not runtime or Candidate evidence.
- Research remains `BLOCKED_CORE`, but not because source revision is unavailable: `transforms.source_id` joins to the canonical source's unique `sources.sha256`, which can supply the source revision. The still-open contract is a versioned Research projection with provider/version, quality and explicit empty/error semantics, followed by runtime/readback and benchmark evidence. No Research UI was enabled and no quality/provider claim was fabricated.
- No new product source changes in this follow-up. Native input/menu/IME/focus/screen-reader/high-contrast/full DPI checks, owner-gated domain contracts, full dependency-backed suites and dirty-tree Candidate remain open.

## Current-source update — 2026-09-25 verified HEAD Candidate window launch boundary

- Reverified the exact committed-HEAD Candidate at `a5de4b13474c217e7a9dd34b8cbfa402e8297780` / tree `a4156ed65d50675822321b9d63eec932b1e76af3`; runtime/workers/provenance checks returned `ok=true`, 21,474 files, no problems, both before and after launch.
- Candidate Desktop/Core started through the project launcher against a newly allocated synthetic `.project-local` workspace. Windows process metadata reported a visible AAOS window, but `@oai/sky` `list_apps` and `list_windows` did not expose it as a target, so no menu/keyboard/pointer/screenshot/accessibility action was performed. The two run-owned processes exited cleanly.
- This is Candidate process-launch evidence only. The artifact represents committed HEAD, not the dirty working tree; Task 6 native interaction and Task 8 dirty-tree Candidate remain open.

## Current-source update — 2026-09-25 Knowledge V3 Candidate form metadata

- Ordinary human Candidate creation now accepts user-selected V3 source type/support/risk, optional bounded confidence, optional canonical UTC validity bounds, and line-separated external evidence references; owner remains trusted `human`, status remains `candidate`, and human review remains required. The UI does not add source_id/anchor_id or assert evidence validity.
- RED/GREEN contract: new form contract first failed on missing controls; the focused form + existing candidate contracts then passed `2/2`. Full navigation/Knowledge contract file: `205 passed` using indexed Python 3.12.13 / pytest 9.1.1 via the project test runner.
- Isolated indexed .NET 10.0.400 Release build: `0 warnings / 0 errors`; DLL SHA-256 `943C36B07148AD6D2B38F69885A775DC1A9478135ADDEA430D89EF652123D86A`; output is under `.project-local/runs/be268a2d33/a04-v3-399eb0e8/artifacts/desktop-build/`.
- This is a dirty-working-tree source build at branch HEAD `a5de4b13474c217e7a9dd34b8cbfa402e8297780`, not a provenance-bound Candidate or native interaction. A04 cold restart/real first-use and Task 6 native accessibility/input remain open; R6 stays partial.

## Current-source update — 2026-09-25 dirty-worktree Candidate qualification

- Built a new self-contained `win-x64` Avalonia Desktop and canonical Rust Core after capturing source snapshot `4f72520d91d295171fd4306e7ecb5d75c0598bcb36017a5e6c794cec672750b0`; assembled Candidate `ArcheAxis.Knowledge.Green-vcurrent6-20260925` with 21,474 manifested files.
- Required runtime/worker/provenance checks plus recomputed current-source snapshot returned `ok=true`, no problems. The manifest binds the dirty source inventory in addition to recording base commit/tree; it is not a signed compiler attestation.
- Candidate `--learning-smoke` passed against fresh synthetic project-local SQLite, including saved answer, FSRS schedule and Core restart readback. `Mastery closed=false` remains explicit.
- A long-path defect found during this qualification was fixed in Candidate assembly and verifier. Regression coverage verifies deeply nested manifest paths and catches an unmanifested deep file. Candidate contract suite: `52 passed, 1 skipped, 4 deselected`; four Windows process-timeout/reap variants still encounter nonzero `taskkill.exe` cleanup and are not counted as passing.
- GUI acceptance remains partial: no full foreground/window input delivery, menu/keyboard/IME/accessibility/DPI/contrast matrix. Green unchanged; R6/M0 statuses not promoted.

## Parallel-run regression refresh — 2026-09-25

- Canonical ten-file Desktop/runtime/routes/navigation/motion/learning/launch, workspace UI, Evidence and workspace Evidence API suite rerun during the separate DP worktree task: `283 passed`, one pytest config warning (`cache_dir` unrecognized by the indexed environment).
- Exact dirty-tree Candidate `current6` passed current-source recomputation plus runtime/workers/provenance verification before and after the run. No native foreground input/accessibility matrix is claimed.

## Current-source verification update — 2026-09-26 current dirty-source Candidate

- Candidate `current-2994efa-final-20260926` supersedes the `current15` and `current6` artifacts above for current-source qualification. Base commit/tree: `2994efa08d3e4f6ea561831fd4088d6d1b290cdd` / `4fc581e7dcde90a30d8e9019f26fdf362bfa5cc9`; dirty-source snapshot SHA-256: `52313a6d94df685e85e4e5cb66eb1884d71982285a55078e42737d2d3c743a6b` (1,541 included files, 8 untracked build inputs, 9 path-only exclusions).
- The verifier was rerun with `--require-runtime --require-workers --require-provenance --require-current-source --expected-commit <HEAD> --expected-tree <HEAD tree>` and returned `ok=true`, 18,246 files, `problems=[]`. Candidate ZIP SHA-256: `49AD275391B6B78DCB611F196A0DAF2FD3DCB1431D1CD6648ABD7025AD3BC471`.
- Isolated Candidate `--learning-smoke` returned exit `0`, persisted an answer and FSRS state, with `Mastery projection closed=false`. The packaged Python runtime was reused from the prior qualified Candidate; this is not a clean machine install or compiler attestation.
- This closes the current-source Candidate assembly/verifier slice only. Native menu/input/focus/IME/screen-reader/high-contrast/DPI acceptance, Mastery closure, full affected TaskPack suites, real Legacy migration and Green Owner Gates remain open. No Green install or release is implied.

## Research source-revision correction — 2026-09-26

The 2026-09-25 `BLOCKED_CORE` note in this document is superseded on its revision premise: `transforms.source_id` joins to the canonical source's unique `sources.sha256`, which can bind the source revision. Research remains unavailable because the formal versioned projection still lacks provider/version, quality and empty/error semantics, and runtime/readback/benchmark evidence. The source revision is derivable; the complete Research contract is not yet present.


## Frontend interaction corrections — 2026-09-26

- Fixed the Knowledge-to-Learning action to bind the eligible identity read from Core, invalidate eligibility on ID edits, select the newly created item rather than the previous queue item, and ignore stale navigation completions. Missing Assessment IDs are rejected, including the display placeholder.
- Reader Candidate creation now disables its own action and rejects concurrent submissions; the separate Knowledge draft button is no longer used as its busy indicator.
- Activity Dock summary now has a finite star-column width so long receipts can truncate without competing with action buttons.
- Verification: two targeted regressions failed before the change; the combined learning/navigation contracts passed 245 tests after the final correction. Release build passed with 0 errors and 1 NU1900 vulnerability-feed warning. Run receipts: `.project-local/runs/be268a2d33/f9135ff4fbda/artifacts/execution.json` and `.project-local/runs/be268a2d33/e6cb855d182d/artifacts/execution.json`. These are source/build checks; no new full native journey is claimed.
- Before these edits, the prior Candidate's Home and empty Learning UI were read through Windows UIA, and Home was captured with PrintWindow at 1920x1010 pixels. The supported computer-use window inventory did not expose that isolated window; menu ExpandCollapse was unsupported. Capture: `.project-local/runs/aaos-ui-current-candidate-20260926/home-current.png`. The owned Candidate process exited 0. A subsequent build launch also exited 0. Neither launch proves final-source full GUI acceptance.
- **Candidate freshness:** `current-2994efa-final-20260926` predates these frontend edits. Its earlier current-source PASS remains historical; rebuild/repackage and current-source verification are required before treating it as the latest deliverable. R6/M0 remain partial and release frozen.


### Sol independent-review follow-up — 2026-09-26

- Fixed stale Reader Candidate completion: validate against captured source SHA and row/request identity; an old successful response reports a toast with the saved Knowledge ID without replacing the currently selected source.
- Once a Knowledge reference POST succeeds, complete the Assessment request even if the user navigated away. Navigation freshness now gates display/navigation rather than abandoning the persisted two-step operation. A failed Assessment reports that the reference was saved and can be retried.
- Editing the Knowledge ID clears the prior body/status/provenance and current Inspector projection until a fresh read, preventing old-object content under a new input identity.
- Final focused learning/navigation contracts: 245 passed (`.project-local/runs/be268a2d33/ed54e610841d/artifacts/execution.json`). Final Release build: 0 errors, 1 NU1900 warning (`.project-local/runs/be268a2d33/a2bce7c8b7af/artifacts/execution.json`). Full runtime race reproduction remains unverified; Candidate refresh remains required.


## Native two-item Learning regression — 2026-09-26

The interaction Candidate exposed a real defect: programmatic Knowledge ID assignment followed immediately by a read could be invalidated by a deferred TextChanged event. The current Desktop tracks the input associated with the read and ignores that duplicate event; a genuinely changed ID still invalidates and clears the prior projection.

Using the isolated workspace from `.project-local/runs/be268a2d33/c8de9f2be380/artifacts/desktop-launch/64184be821a04c2aae3a7f747bfb9a50/desktop-launch.json`, Windows UIA created synthetic personal Candidate A, joined A to Learning, then created B and joined B. The displayed Knowledge and Assessment switched to B. UIA submitted B's answer with an explicit outcome and Good rating; Core reported saved answer and FSRS. After closing Desktop/Core and restarting, UIA read back the same B Assessment, answer and FSRS schedule. Receipt: `.project-local/runs/aaos-ui-current-candidate-20260926/native-learning-regression.json`; Desktop DLL SHA-256 `8d58b26e4173525c51808236d4f1d07dbb9b5cd6e33d6bfa0ac3661498d4d4b9`. Owned test processes exited 0.

Evidence is TESTED_LOCAL_GUI_PARTIAL_SYNTHETIC: two-item selection, actual UI submission, persistence and cold restart. It does not cover source import, a real person's learning, full responsive/accessibility matrix or Mastery closure (still closed=false). The launcher used repository workers with the packaged runtime and Core. Final contracts: 246 passed, run `.project-local/runs/be268a2d33/01e8a3378ce8`; Release build 0 errors/1 NU1900 warning, run `80e8cdb5ea76`.

Candidate freshness: `interaction-2994efa-20260926` predates this deferred-event fix. Its earlier verifier PASS remains valid for its recorded snapshot only; a refreshed package is required for the newest source.


## Native-tested Desktop packaged — 2026-09-26

Candidate `.project-local/staging/aaos-native-verified-candidate-20260926/ArcheAxis.Knowledge.Green-vnative-verified-2994efa-20260926-x64` replaces the earlier interaction Candidate for current-source evidence. Required runtime/workers/provenance/current-source verification returned ok=true, 18,246 files, no problems; snapshot `2668dd44dd4334cca33c04e82b9dcac700355e9812f72f3284e287125684ae9c`.

Packaged Desktop DLL SHA-256 `8d58b26e4173525c51808236d4f1d07dbb9b5cd6e33d6bfa0ac3661498d4d4b9` exactly matches the recorded native two-item/review/restart regression binary. ZIP SHA-256 `fdb5b996f8705f0456335760703c032472b6ea8f8bc35f978c1b768b37fa550f`, 285189631 bytes. Desktop was republished; the previously rebuilt unchanged Core and qualified Python runtime were reused, with current workers. This closes package freshness for the latest fix; full GUI matrix, real learning/Mastery, Legacy and Green owner gates remain open.


### 2026-09-26 current Candidate keyboard readback

`home-compact-2994efa-20260926` passed local runtime/workers/provenance/current-source verification (18,246 files; source snapshot `d3a80e5b535d2dcc3b65352bd11ec9442b06842adff2455066928d2ec5d64b28`). In the approved user-session isolated launch `f0f568d0031b`, native Ctrl+K focused `CommandPaletteBox`; native Esc restored `RailWorkspaceButton` in the same PID. Receipt: `.project-local/runs/aaos-ui-current-candidate-20260926/native-keyboard-user-session.json`. The owned Desktop exited normally. This supersedes the tooling blocker from the earlier sandbox foreground attempt only; it does not prove full menu, IME, screen-reader, focus-traversal or DPI coverage. Homepage disclosure expansion/collapse separately passed native UIA in run `e0d5e58aac34`.
## B10 high-fidelity convergence — 2026-09-26

- Applied the supplied B10 visual direction to the canonical Avalonia shell: Inter typography, ivory primary text, muted blue-gray secondary text, deep navy surfaces, teal borders/active rail, gold ambient accent, 18px cards and 12px controls. Home has a branded mark, command search affordance, focused first-use panel and reduced visual clutter; Source Reader/Evidence surfaces use the same card and control tokens. These are original AAOS XAML/C# assets and styles; no React/Tauri surface was introduced.
- Release Desktop build completed (NU1900 package-audit network warning; no compiler errors). Desktop contract suite: 282 passed. `git diff --check` passed.
- Review screenshot: `.project-local/runs/aaos-ui-current-candidate-20260926/home-b10-final.png` (SHA-256 `D946B10154A150E3C4D7000F2755EFA547582CC359E4D34C45DAD02F5C789241`). It documents the visual review surface; it is not itself a full accessibility or cross-DPI pass.
- Refreshed dirty-tree Candidate `b10-final2-2994efa-20260926`; snapshot `6e02b6dc526c36d832f863a337ee6f09b940771ff8ff8f4eaec9274adb463bed` (1,542 source inputs, 9 untracked build inputs); source commit/tree `2994efa08d3e4f6ea561831fd4088d6d1b290cdd` / `4fc581e7dcde90a30d8e9019f26fdf362bfa5cc9`. Required runtime/workers/provenance/current-source verification returned `ok=true`, 18,246 files, no problems. ZIP `.project-local/staging/aaos-b10-final2-candidate-20260926/ArcheAxis.Knowledge.Green-vb10-final2-2994efa-20260926-x64.zip`, SHA-256 `8FE46210949B51AC8B1E7115A210057A386762EE794AF31419D5C57A9523F5AC`.
- A12/A13 remain partial. Full menu/IME/screen-reader/focus-traversal/DPI/contrast matrix, real first-use learning, Research/Recovery/Plugin/Model and Editor/Graph contracts, Green owner gates and complete acceptance remain open.
## B10 home frame — 2026-09-26 current-Candidate native readback

- Fixed the wide-screen frame to preserve the B10 four-column hierarchy on Home: primary navigation, visible context rail, main content, and visible evidence inspector. On first wide-screen layout (at or above the existing 1440 inspector breakpoint) the inspector opens by default; it remains user-toggleable. Home no longer hides its context rail. The narrower drawer and mobile behavior remain breakpoint-driven.
- Regression was observed RED: the new Home shell contract failed because Home excluded the context rail. After correction, the focused layout contracts passed `2/2`; the related desktop contract wave passed `264/264`. Release Desktop publish completed successfully; it emitted no compiler errors.
- Launched exact local Candidate `b10-home-shell-2994efa-20260926` in an isolated synthetic workspace. Native window measured `1920x1010`. UI Automation read `上下文`, `来源与证据`, `首页`, and `关闭证据检查器` with `IsOffscreen=false`; Candidate-owned Desktop/Core closed normally (launcher exit `0`). Screenshot `.project-local/runs/aaos-ui-current-candidate-20260926/home-b10-home-shell.png`, SHA-256 `FF84718172CB7729729DB83FEE18763AC6DFAE386211109F9BD8219D3AA74226`.
- Candidate source snapshot `ef9a9f09fb9dbf210793175225838fb4e2ca86096010b2327d3fc9b8a3704d3b` (1,542 inputs; 9 untracked build inputs). Runtime/workers/provenance/current-source verifier: `ok=true`, 18,246 files, no problems. ZIP SHA-256 `C50472F76D62D1C895EB4862CB98E7ED35F205550351C950891C4C988A96BABD`.
- This closes one B10 wide-screen Home composition defect only. Other route visuals, full UIA interaction matrix, IME/screen-reader/high contrast, viewport/DPI matrix, real P3 loop, and Core/Owner-gated surfaces remain open; A12/A13 remain partial.

## B10 current Candidate launch readback — 2026-09-26

- Launched the staged `b10-home-shell-2994efa-20260926` package from an isolated synthetic workspace using `launch_candidate_ui.py`. Launch receipt: `.project-local/runs/be268a2d33/1746e8cc6e45/artifacts/desktop-launch/0b03a059748b4e9b8a990eefc7d5ae8d/desktop-launch.json`; Desktop SHA-256 `5D63FBF3617D25123CCD700B12CF93F32CA37F93BBF2E8D29E858F9629D0C055`, Core SHA-256 `3EBD4940B8616456B79D01DC1003915AE84FCCCaa4760881D078305B50B7F90E`, owned Desktop PID `26968`. UIA read the native `星环知识平台 — 已连接` window at `1902x963` and visible Home/learning empty-state content. The launcher was stopped with Ctrl+C; the owned process was confirmed absent afterward.
- A Ctrl+K probe was attempted, but the sandbox and the approved command process both returned `SetForegroundWindow=false`; `SendKeys` raised `操作成功完成` and UIA did not expose the command palette. Classify this as `NOT_EXECUTED_INPUT_UNDELIVERED`, not a product failure or interaction pass. Existing Ctrl+K/Escape evidence belongs to the older `home-compact` Candidate and is not attributed to this B10 package.
- Evidence scope: `TESTED_LOCAL_GUI_PARTIAL_SYNTHETIC` for packaged launch/window/UIA visibility and owned-process cleanup. Menu, command-palette route selection, focus return, IME, screen reader, contrast, full route screenshots, and viewport/DPI matrix remain open; A12/A13 remain partial.
- Follow-up UIA interaction against the same B10 package: invoked the visible top-bar command search button, set the actual `命令面板输入` through `ValuePattern` to `学习`, read visible results `学习` / `学习路径`, and selected `学习` through `SelectionItemPattern`; selection readback returned `true`. Receipt: `.project-local/runs/aaos-ui-current-candidate-20260926/b10-command-palette-uia-readback.json`; launcher receipt `.project-local/runs/be268a2d33/82c620ede721/artifacts/desktop-launch/99d212488ed5450da433abb24fc85663/desktop-launch.json`. Candidate-owned process exited after UIA window close. This verifies palette open, filtering and result selection through real controls; executing the selected route with Enter/double-click and keyboard focus restoration remain unverified because keyboard input is not delivered in this execution context.

## B10 responsive width sample — 2026-09-26

- Resized the current staged B10 Candidate's native HWND using `SetWindowPos`; `GetDpiForWindow` returned `120` (125%). `GetWindowRect`/`GetClientRect` verified actual client widths of 1500 and 1800 physical pixels, exactly 1200 and 1440 logical widths. UIA read the primary navigation, Home and context headings at both widths and the `来源与证据` heading at both widths. At 1200 logical width the inspector is in its drawer presentation and remained open from the wide-screen initial state; at 1440 it is in the right-side column. This sample does not prove default closed-drawer behavior after a fresh narrow launch.
- Receipt: `.project-local/runs/aaos-ui-current-candidate-20260926/b10-responsive-width-readback.json`; Candidate Desktop/Core hashes match the B10 launch receipt above. The owned process was closed through UIA and confirmed exited.
- This is a two-width, current-125%-DPI geometry/readability sample only. It does not cover the 840/1024/1280/1440 threshold neighbors, all planned widths, other DPI scales, every route, screenshot/overflow review, keyboard/IME, or assistive technology; Task 6 remains partial.
- Follow-up boundary sweep on the same B10 Candidate at 120 DPI: measured the client width with `GetClientRect` at 839.2/840/840.8, 1023.2/1024/1024.8, 1279.2/1280/1280.8 and 1439.2/1440/1440.8 logical units. UIA primary navigation disappears below 840 and is present at/above 840; the Context heading is absent below 1024 and present at/above 1024. Home and the Evidence heading remained readable across the sampled sizes. The inspector stays in drawer presentation below 1440 and enters the right-side column at/above 1440; the drawer was initially open because this instance started wide. Full per-point control geometry is in `.project-local/runs/aaos-ui-current-candidate-20260926/b10-breakpoint-neighbors-120dpi.json`.
- At 839.2 logical width, the mobile navigation exposed a horizontal UIA `ScrollPattern`; scrolling from 0% to 100% brought `打开插件`, `打开模型`, and `打开系统` into visible bounds. This confirms end-of-rail reachability through UIA at that viewport. Candidate-owned process exited after UIA close.
- This closes only the current-125%-DPI Home width-boundary sample and mobile rail scrollability. Other DPI scales, all planned width/height combinations, every route, screenshot/overflow review, keyboard/IME, screen reader, high contrast, and fresh narrow-start drawer state remain open; Task 6 remains partial.
