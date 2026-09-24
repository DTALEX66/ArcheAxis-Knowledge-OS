# AAOS UI Suite B03–B10 Coverage Matrix

Date: 2026-09-24 (verification refresh)
Scope: the canonical Avalonia surface in `apps/ArcheAxis.Desktop/`  
Authority: the previously audited AAOS UI suite index and current R6/M0 UI
receipts. This matrix does not promote reference demos, static numbers or
`localStorage` into product truth.

## Evidence vocabulary

- `IMPLEMENTED_LOCAL`: the product source contains the bounded behavior.
- `TESTED_LOCAL_STATIC`: the behavior is covered by the direct desktop contract
  harness; this is not native GUI evidence.
- `BLOCKED_CORE`: the requested product capability needs a Core read/write
  contract that is not exposed by the current canonical path.
- `UNVERIFIED_GUI`: native screenshot, pointer, focus-tree or timing evidence
  is still absent.

## Coverage

| Package | Absorbed contract | Canonical implementation evidence | Current verdict | Explicit gap |
| --- | --- | --- | --- | --- |
| B03 | AAOS information architecture, dark surfaces and Aurora Teal hierarchy | `MainWindow.axaml`, `AaosTheme.axaml`, `SetSection` | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC` | Native visual contrast and screenshot readback: `UNVERIFIED_GUI` |
| B04 | spacing/radius/density/breakpoint/motion resources and component states | `AaosTheme.axaml` resources; shared page/card/rail heading classes; reduced-motion-safe Hero ambient glow; Button/ListBox/TextBox/ComboBox/CheckBox state selectors | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC` | Native timing remains open |
| B05 | Home, Capture, Library, Reader, Knowledge, Learning, Jobs, Settings and Recovery compositions | named surfaces in `MainWindow.axaml`; Core-backed handlers in `MainWindow.axaml.cs`; Reader now visually distinguishes container members from durable source jobs and labels job kind/state/attempt/error; persisted Evidence anchor list and Knowledge lineage now read existing Core projections | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC / TESTED_LOCAL_PORTABLE` | Evidence bundles, full Graph, Editor and citation picker remain Core-bound |
| B06 | loading/empty/error/permission/unavailable/disabled/keyboard/focus/responsive states | `SetStatus`, Home/Settings/status-text accessible-name synchronization, request-version guards, dynamic Inspector accessible-name refresh, unavailable structure, focus handlers, responsive layout code | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC` | Native state rendering and assistive-technology readback: `UNVERIFIED_GUI` |
| B07 | product-route discoverability, keyboard access and automation names | `CommandPaletteRoutes`, primary/mobile rails, all 16 native routes, File/Navigate/View Alt+F/N/V declarations, dynamic current-page names and action labels | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC` | Native mnemonic/IME traversal, actual UIA, full route traversal and DPI/zoom evidence remain open |
| B08 | reusable card, KPI, status, toolbar, provenance and selectable-result patterns | `aaos-card*`, card/lifecycle pointer-over feedback, `aaos-kpi`, `aaos-status`, `aaos-toolbar`, provenance classes and row templates | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC` | No second React runtime or demo persistence is imported |
| B09 | interaction references: command palette, drawer, toast, review selection and source chain | Command Palette, Inspector Drawer action reflow, Toast, Review Card, Evidence anchor → source_id → Source Reader chain, Home Hero ambient feedback, workspace route transition | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC` | Graph-node, citation insertion and native animation timing remain open |
| B10 | high-fidelity product hierarchy and visual direction | project-owned decorative empty-state asset plus tokenized AAOS shell | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC` | Full visual parity is not claimed; GUI screenshot gate remains open |

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

- Last source commit at verification: `1dc0ee1d06b68afb0a71117d6363d519397932f0` on
  `codex/aaos-p3-ui-convergence-20260922`; the native menu, all-route menu coverage,
  single-file Reader and Core `input_ref` projection in the receipt below are
  working-tree changes and are not part of that commit or a published Candidate.
- Latest desktop navigation/learning/motion contracts: `218 passed, 1 warning` (external pytest config contains an unrecognized `cache_dir` option); Avalonia Debug build: `0 warnings / 0 errors`.
- Avalonia Debug build for this working tree: `PASS`, `0 warnings / 0 errors`; Avalonia build telemetry was opted out for this run because its default per-user log target was ACL-denied. No ACL was changed.
- Rust API `source_jobs_api`: `1 passed`, covering persisted source binding, multiple success jobs, queued and failed/error jobs, an empty source and unknown source. Initial RED was observed (`GET /sources/:id/jobs` returned 404 before route implementation).
- Real CoreSupervisor integration: `PASS`, including actual Python text extraction, deliberate source/job mismatch rejection, stop/reopen against the same isolated SQLite, source-job projection restoration, and reading the same text output after restart.
- Primary/mobile rail and all 16 native Navigate menu item names now announce `当前页面：...` for the active destination through the single `SetSection` transition; focused RED→GREEN contract and full desktop suites pass. Native UIA and assistive-technology readback remain unverified.
- Current-menu access keys `Alt+F/Alt+N/Alt+V` have RED→GREEN source contracts. Reader cards and detail labels distinguish container members from ordinary-source durable jobs; task cards display kind/state/attempt/error without asserting absent filename or SHA. The Home Hero's knowledge illustration has a descriptive alternative name; three duplicated state illustrations are marked decorative and excluded from control/content UIA views. Source Reader presentation/state is now extracted into a typed view with explicit events, and its static contracts cover member/source/job/error/mismatch/empty distinctions. An Evidence empty-state illustration is wired; loading feedback honors reduced motion. Latest contracts/build are recorded above. Actual native IME, focus, visual and UIA checks remain Task 6 `UNVERIFIED_GUI`; Green remains unchanged.
- The prior isolated Candidate and learning smoke evidence above belongs to its
  recorded historical source state; it does not verify this working-tree SHA.
- Native GUI screenshots, menu pointer/keyboard traversal, focus/UIA tree,
  screen-reader output, high-DPI/resized pixels and cold-restart GUI journey remain
  `UNVERIFIED_GUI / TOOLING_UNAVAILABLE`; current CUA inventory returned `apps=[]`.
- Green remains untouched; these local tests/builds do not authorize or qualify a
  Green overwrite, install, signature, release, commit, push or CI result.

No Green directory, external resource root, protected history asset, credential
or unrelated dirty file was modified for this matrix.
