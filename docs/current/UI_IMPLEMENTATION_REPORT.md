# AAOS UI Implementation Report

Date: 2026-09-23
Implementation surface: `apps/ArcheAxis.Desktop/`
Reference authority: AAOS UI suite B03-B10 and the current R6/M0 authority chain

## Product surface map

| Product surface | Avalonia surface | Current state |
| --- | --- | --- |
| Home / Workspace | `HomeSurface` | Implemented: responsive hero, first-run readiness, lifecycle, focus, session receipt and next actions |
| Capture Inbox | `CaptureSurface` | Implemented: real file picker and Core submission/readback boundary |
| Evidence Library | `EvidenceSurface` | Implemented truthful unavailable state plus Capture/Jobs next actions; Core list read model still absent |
| Evidence Detail | Evidence inspector / source chain | Implemented for fields exposed by Core; no synthetic anchor/bundle rows |
| Originals / Original Editor | `SourceReaderSurface` | Implemented source member selection, transform readback and provenance copy; editor persistence remains Core-bound |
| Human Learning | `LearningSurface` | Implemented real queue read, selectable items, answer, independent correctness, FSRS grade, receipt and restart readback |
| Machine Learning | `MachineKnowledgeSurface` | Implemented real task receipt query; machine-derived values remain labeled |
| Memory Map | Knowledge/source provenance surfaces | Mapped as provenance and Knowledge context; graph read model not exposed by current Core |
| Search | `LibrarySurface` | Implemented current library search/readback boundary |
| Review / FSRS | `LearningSurface` Review Card | Implemented with narrow reflow, selected feedback and reduced-motion support |
| Settings | `SettingsSurface` | Implemented Core version/workspace readback and explicit capability boundary |
| Jobs / Recovery | `JobsSurface`, `RecoverySurface` | Implemented read-only status surfaces with entry refresh |

## UI system implemented

- AAOS dark token set: Background, Sidebar, Surface, Border, Aurora Teal,
  Ivory, Muted, semantic success/error/info/review and high-contrast primary
  action text.
- B06 state language: loading, empty, error, permission, unavailable,
  disabled, success and unknown remain distinguishable.
- B04 motion bands are represented as project resources. Button feedback uses a
  short opacity transition; `AAOS_REDUCED_MOTION=1` removes transitions.
- Review grade selected state, responsive toolbar reflow, compact hit targets,
  keyboard focus styling and stable AutomationProperties names are present for
  the desktop rail, mobile rail, learning controls, and system/job actions.
- Project-owned generated visual:
  `apps/ArcheAxis.Desktop/Assets/aaos-knowledge-constellation-empty-state.png`.
  It is decorative and never represents Evidence, metrics or Core truth.

## Local evidence

- Frontend implementation HEAD: `3b1cb0d4` on
  `codex/aaos-p3-ui-convergence-20260922`; the evidence receipt is recorded by
  the current R6 receipt, and the branch is published to its matching remote branch.
- The last Avalonia Debug build and self-contained `win-x64` Release publish
  remain proven for `8156be8c`; a fresh build for `e9586fcb` is
  `NOT_EXECUTED` because the current shell has no PATH .NET SDK and the
  indexed external toolchain was not invoked under the external-resource boundary.
- Targeted desktop UI contracts: `146 passed`.
- Extended desktop route/launch/learning gate: `161 passed`, including the
  project-local launch preparation contract and explicit isolated-workspace
  binding checks.
- Current combined frontend verification after the input/result-control accessibility
  closure: `175 passed`.
- Source Reader citation metadata action is implemented and covered by the
  extended gate; it copies only Core-exposed identity fields and never source
  body text.
- Capture completion and interruption now have transient feedback while the
  durable Core receipt remains the authoritative state.
- Every declared desktop `Button` now carries an explicit
  `AutomationProperties.Name`; a regression contract reports zero unnamed
  actionable buttons.
- Text inputs, filters, result lists, and receipt lists expose stable
  `AutomationProperties.Name` values with a matching regression contract.
- Disabled Button, TextBox, and ComboBox states use an explicit AAOS visual
  treatment so unavailable actions remain legible and distinguishable from
  ordinary idle controls.
- Desktop and mobile primary navigation actions now expose stable accessible
  names for all formal product routes.
- Source Reader citation/provenance actions reflow vertically at the narrow
  action breakpoint so the 360/390-width layout does not force horizontal
  overflow.
- Learning navigation no longer re-enters section setup while loading; the
  command palette now executes Evidence Center; review submission rejects
  inconsistent correctness/FSRS combinations and disables duplicate submits.
- Command Palette now restores the previously focused control after Escape or
  command execution, preserving keyboard navigation context.
- Command Palette route labels, aliases, filtering, execution and fallback
  help now derive from one authoritative route table.
- Command Palette direction-key navigation no longer mutates Learning empty
  state; its result list keeps Enter handling when it owns focus, and its
  unknown-command help lists every executable route.
- Knowledge V3 readback ignores stale success, failure, parse, and exception
  responses when a newer request has started; review receipts are likewise
  ignored after the active learning exposure changes.
- Current direct no-argument static desktop contract harness after the latest
  route and breakpoint checks: `167 passed`.
- Source Reader copy actions now catch clipboard write failures and only show
  success after the write reports success; the mobile breakpoint fallback now
  matches the themed `840` resource.
- Command Palette input guidance now lists the same complete primary-route set
  as the authoritative route table.
- Shared status updates now refresh the corresponding AutomationProperties
  name, so loading, success, error, permission and unavailable feedback is
  exposed as current accessible state rather than stale initial text.
- Core, search, source-reader, Knowledge, Evidence, Settings, Activity Dock
  and Command Palette status surfaces now also have descriptive initial
  accessible names before their first interaction.
- Command Palette results now support mouse double-tap execution in addition
  to keyboard Enter, while preserving the existing focus restoration path.
- Command Palette selection, filtering, empty-result and unknown-command
  feedback now updates both visible text and its accessible status name.
- B04 fast motion is now consistent: the Button opacity transition uses the
  declared `AaosMotionFastMs` 120ms band instead of a divergent 140ms value.
- Primary product actions now have stable accessible names across first-run
  import, Home resume, search, Source Reader, Knowledge, Learning review,
  Machine Tasks and Evidence refresh flows.
- All remaining named secondary actions—source/Knowledge return paths,
  transform and job actions, Learning capture links, and Inspector actions—
  now also have stable accessible names; the named-button audit reports zero
  unnamed controls.
- Headless Core learning smoke with explicit project-local DB and worker
  profile: `PASS`, including answer persistence, FSRS receipt and cold restart
  event readback; mastery projection remains correctly open/unclaimed.

## Explicit limits

- Native GUI screenshot/click/accessibility readback is not claimed: the current
  CUA bridge exposes no native application window.
- Evidence list/detail and Memory Graph remain Core read-model prerequisites.
- Original Editor persistence and authoritative citation picker remain Core
  contract prerequisites; metadata copy is intentionally not called a picker.
- No demo localStorage, random graph values, synthetic Evidence or simplified
  FSRS implementation was introduced.
- Green, external libraries, credentials, E/F drives, protected history assets
  and unrelated dirty worktree files were not modified.

## Next phase boundary

After the frontend baseline is accepted, the next separate work package is the
repository drift/size audit: authority documents, external indexes, paths,
handoffs, summaries, history, spill tracking, exact-path migration/freeze and
branch disposition. That phase must use this report and the exact pushed commit
as its frontend baseline; it must not rewrite frontend behavior while auditing.
