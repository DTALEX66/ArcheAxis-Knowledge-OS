# Reading reference delivery — 2026-10-15

Status: PARTIAL. This receipt covers FE08 reading geometry/information hierarchy and FE06 presentation retention only. It does not mark the seven-image UI programme complete. Character work/FE18 remains QODER-owned and excluded.

Base: `4fc9006a2bd59cf9e0733ffc46357f0488d6a27b`; branch `codex/reader-reference-20261015`.

Implemented:
- Reference 4 reading frame: compact breadcrumb/header, one content-tab row, horizontal identity/version rows, source/history/export controls, independently scrollable document/details at desktop width.
- Omit duplicate Dockview headers only for a single grid group containing singleton navigation hosts 01/03. Floating, split, object and other business tabs retain their headers and mounted sessions.
- Normal reading moves material questions/conversation and source preparation into disclosures without conditionally mounting the question/session components. Explicit source journeys retain their existing open preparation flow. Real errors remain visible.
- Existing save/restore/source/citation/version APIs remain unchanged. Raw receipt gets an optional visible label; diagnostic payload and default label remain unchanged.
- Settings summary has a minimum 24×24 target and visible keyboard focus ring.

Verification:
- `reader-targeted`: 6 test files, 37 tests PASS (editor, layout, lease, list freshness, diagnostics, semantic reading). Initial typecheck caught an unsupported Testing Library `exact` option; removed it and subsequent typecheck/build PASS.
- `reader-source-controls`: SourceCandidateJourney + SemanticReadingLayout, 17 tests PASS (10 repeated; 44 unique tests across the two runs).
- Frontend typecheck + production build PASS: main project `.project-local/runs/8bc12e00bb/746f52df4adf/artifacts/frontend-build.json`.
- Real Chrome / SYNTHETIC host and data: `reader-visual-final` 11 checks PASS across cosmic widths 1672/1024/900/640/390 and all five palettes at 1672. No page errors or horizontal document/main/reader-host overflow. Material input survives collapse and source-tab switching; no automatic inference; settings keyboard focus visible. Final CSS only removes an inherited 24px toolbar margin; final 1672 capture repeats 3 relevant checks PASS in `reader-delivery-capture`.
- Screenshots (main project output root): `.project-local/runs/8bc12e00bb/reader-delivery-capture/artifacts/cosmic-1672-reader.png` and `cosmic-1672-home-control.png`; `visual-check.json` records measured geometry and calls. Harness lives in isolated checkout `.project-local/tmp/reader-visual.cjs` (ignored, existing runtime, no dependency install).

Measured 1672×941: document x361/y322/w772/h518; details x1149/y322/w396/h518. Reference approximately x363/y320/w774/h518 and x1154/y320/w400/h518. The read/save toolbar is y420 vs reference416. Body font metrics, current source-derived breadcrumb, extra real tools, bottom task wording and sidebar density still differ; this is not pixel-perfect qualification. Desktop panels scroll when additional controls/content need room. Homepage geometry/background is preserved. Background retains the prior generated asset and provenance; no new imagery.

Evidence limits: browser pixels are REAL rendering, but documents/Core responses are SYNTHETIC; no native runtime or actual provider qualification is claimed. No full suite, push, publication, Green replacement or character change performed. Parent owns canonical progress and final integrated native validation. Revert this scoped commit to roll back this reading/UI change.
