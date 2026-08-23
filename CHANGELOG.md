# Changelog

All notable release changes are recorded here. Dates and publication status
must be read from Git/GitHub; a source entry does not itself prove publication.

## [Unreleased]

- Prepared the single `0.6.11` release candidate for the post-release closed-loop
  batch; this source entry is not a published release claim.

## [0.6.10] - 2026-08-24

- Completed the desktop write-boundary handshake: the frontend obtains scoped
  launch credentials, and Workspace plus Learning mutations require the shared
  local token, scope, and idempotency-key transport contract.
- Added raw-first web acquisition, append-only audit receipts, and governed
  evidence-bundle migration coverage to the minimum closed-loop delivery.
- Made the Activity Dock operational: users can inspect public activity
  objects, dispatch the next queued delivery, and retry failed deliveries;
  unsupported cancellation remains explicitly unavailable rather than faked.
- Kept the frontend as a thin, Vite-served backend projection with HMR for
  development and one final Windows release build for distribution.

## [0.6.9] - 2026-08-23

- Added a bounded desktop Recovery Shell with safe mode, retry, sanitized logs,
  verified offline restore, immediate exit, and explicit External Dev reload.
- Kept the existing six-space frontend as a thin projection over stable
  recovery and authenticated BFF contracts; browser development retains HMR.
- Hardened Windows process, backup identity, reparse-point, pipe deadline, and
  diagnostic-redaction boundaries with independent Rust and frontend review.
- Reduced ordinary frontend and Tauri source CI to risk-selected gates; full
  Setup, Green, and Portable qualification remains reserved for Release.

## [0.6.8] - 2026-08-23

- Closed the source-preservation loop with digest-addressed original-content
  readback and strict no-store, nosniff, sandbox, and launch-token controls.
- Closed governed AI asset approval and independent deprecation with scoped,
  versioned, evidence-linked, idempotent append-only receipts.
- Connected all six desktop spaces to the real backend: Workspace status and
  activity, Library original readback, Evidence research approval, Learning
  loops, AI asset governance, and Settings initialization/backup verification.
- Fixed Tauri-origin CORS/token handling and canonical Workspace API routing;
  validated all six spaces in Chromium against a live backend with zero console
  errors or warnings.
- Hardened project-local test/runtime boundaries for Windows worktrees and
  retained selective CI plus exact-SHA release-candidate promotion.
- Local release qualification: 1977 Python tests passed with 7 intentional
  skips, 25 frontend tests passed, production frontend build passed, and 14
  Rust/Tauri tests passed.

- The source Release Manifest remains `unreleased / public=false` until a
  release artifact receives an injected and verified public identity.
- Added release-truth, licensing, third-party, and security documentation.
- Added a post-publication gate that reads back the exact public asset set,
  provider digests, release identity, and downloaded SHA-256 payloads.
- AXW-094A/B: open-exchange export and verifiable backup (library, Workspace
  API, and user-facing UI entry on the Evidence page).
- AXW-096A: performance benchmark with real layered zh/en public-domain
  corpus (latency, memory, cold start, degradation thresholds).
- AXW-096B: full keyboard accessibility for the workspace and the PDF
  reader (Tab chains, focus + Enter flows, aria-live).
- AXW-096C: async batch import with pause/resume/shutdown control and
  ledger-based recovery (task list, counts, terminal state).
- Nightly qualification now runs end-to-end: full-suite installs and verifies
  the real OCR engine (tesseract + eng data + fonts, mirroring ci.yml), so the
  full-matrix nightly tier is green and schedule-ready.
- Nightly full-suite explicitly collects `tests/`, `integration-tests/` and
  `knowledge_base/tests/` (previously integration-tests were never collected);
  nightly browser-smoke now runs real Chromium regressions inside the venv.
- CI gateplan is fully fail-closed: BFF/router and browser-smoke script
  changes trigger browser-smoke; py/format/migration/security-targeted gates
  are executed and verified (previously planned but never run).
- AXW-097: diagnostics endpoint guarded by tests asserting no secrets,
  credentials, auth state, or absolute private paths appear anywhere in the
  response.

- CI ecosystem: nightly compatibility workflow defect fixed; Release
  workflow pre-first-run audit passed.

## [0.5.0] - 2026-08-09

`v0.5.0` is the public stable Release. Merge-SHA Full Qualification,
Windows installer lifecycle, exact asset allowlist, SHA-256 recomputation,
and schema-v2 release identity readback passed. The source manifest remains a
deliberate `unreleased / development / public=false` placeholder; the verified
public identity is carried by the release artifact.

## [0.4.4] - historical release

`v0.4.4` is the current historical public stable Release (2026-08-03). Asset
hashes are valid and cross-check against provider digests. A known provenance
defect is recorded: its `release-identity.json` is schema v1 and `source.ci_run`
points at the Release run (`30839451084`) rather than the verification CI run
(`30837105199`). The tag/Release/assets are intentionally preserved; see
`docs/RELEASE_LEDGER.md` for the full ledger and v0.4.0–v0.4.4 history. Future
releases must use identity schema v2 with distinct verification/release runs.

## [0.4.0] - historical release

`v0.4.0` is retained as historical publication evidence. Readback found
incomplete checksum payload coverage: the public installer name did not match
its checksum-manifest name and an extra public payload was absent from the
manifest. The tag, Release, and assets are intentionally preserved; remediation
must use a new version. This entry makes no signature claim.
