# AAOS UI Suite B03–B10 Coverage Matrix

Date: 2026-09-23  
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
| B04 | spacing/radius/density/breakpoint/motion resources and component states | `AaosTheme.axaml` resources; Button/ListBox/TextBox/ComboBox/CheckBox state selectors | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC` | Full suite-wide token consumption and native timing remain open |
| B05 | Home, Capture, Library, Reader, Knowledge, Learning, Jobs, Settings and Recovery compositions | named surfaces in `MainWindow.axaml`; Core-backed handlers in `MainWindow.axaml.cs` | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC` | Evidence list, Editor, Graph and citation picker remain Core-bound |
| B06 | loading/empty/error/permission/unavailable/disabled/keyboard/focus/responsive states | `SetStatus`, unavailable structure, focus handlers, responsive layout code | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC` | Native state rendering and assistive-technology readback: `UNVERIFIED_GUI` |
| B07 | product-route discoverability, keyboard access and automation names | `CommandPaletteRoutes`, primary/mobile rails, `AutomationProperties.Name` contracts | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC` | Full 13-route native traversal and DPI/zoom evidence remain open |
| B08 | reusable card, KPI, status, toolbar, provenance and selectable-result patterns | `aaos-card*`, `aaos-kpi`, `aaos-status`, `aaos-toolbar`, provenance classes and row templates | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC` | No second React runtime or demo persistence is imported |
| B09 | interaction references: command palette, drawer, toast, review selection and source chain | Command Palette, Inspector Drawer, Toast, Review Card, Source Reader chain | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC` | Graph-node, citation insertion and native animation timing remain open |
| B10 | high-fidelity product hierarchy and visual direction | project-owned decorative empty-state asset plus tokenized AAOS shell | `IMPLEMENTED_LOCAL / TESTED_LOCAL_STATIC` | Full visual parity is not claimed; GUI screenshot gate remains open |

## Non-equivalence rules

1. `SourceReaderSurface` is an original/source projection reader, not an
   `Original Editor`; no persistence or citation-picker contract is invented.
2. Knowledge provenance context is not a `MemoryGraph`; no synthetic nodes,
   edges or metrics are rendered.
3. An unavailable product surface is a truthful Core boundary, not an incomplete
   demo filled with reference data.
4. Static contract tests do not promote the UI to native GUI PASS.

## Current verification anchor

- Frontend implementation commit: `d4d9bb13`.
- Latest documentation/branch commit: recorded by the current
  `UI_IMPLEMENTATION_REPORT.md` and `R6-EXECUTION.md` continuation receipt.
- Direct no-argument desktop contract harness: `185 passed`.
- XAML XML parsing: `PASS`.
- Native GUI and fresh .NET build: `UNVERIFIED / NOT_EXECUTED`.

No Green directory, external resource root, protected history asset, credential
or unrelated dirty file was modified for this matrix.
