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
  keyboard focus styling and stable AutomationProperties names are present.
- Project-owned generated visual:
  `apps/ArcheAxis.Desktop/Assets/aaos-knowledge-constellation-empty-state.png`.
  It is decorative and never represents Evidence, metrics or Core truth.

## Local evidence

- Avalonia Debug build: `PASS`, 0 warnings, 0 errors.
- Self-contained `win-x64` Release publish: `PASS`.
- Targeted desktop UI contracts: `144 passed`.
- Headless Core learning smoke with explicit project-local DB and worker
  profile: `PASS`, including answer persistence, FSRS receipt and cold restart
  event readback; mastery projection remains correctly open/unclaimed.

## Explicit limits

- Native GUI screenshot/click/accessibility readback is not claimed: the current
  CUA bridge exposes no native application window.
- Evidence list/detail and Memory Graph remain Core read-model prerequisites.
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
