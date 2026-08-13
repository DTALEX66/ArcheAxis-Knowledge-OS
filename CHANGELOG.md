# Changelog

All notable release changes are recorded here. Dates and publication status
must be read from Git/GitHub; a source entry does not itself prove publication.

## [Unreleased]

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
