# CI and Release Performance Design

## Goal

Reduce routine qualification and release wall-clock time without weakening the
semantic GatePlan, exact-SHA evidence, installed-artifact lifecycle checks, or
release readback.

## Decisions

1. Keep `full-qualification` for stage, RC, and release-candidate commits;
   routine changes continue to use the deterministic path classifier.
2. Split Python execution into a primary full-suite job and three independently
   selected targeted jobs. Targeted jobs run only their risk-owned tests;
   `py-primary` remains the complete OS/KB/integration suite.
3. Treat the Windows installer lifecycle as a release-critical gate. It is not
   removed or downgraded; reliability fixes remain a separately diagnosed item.
4. Add an immutable `release-candidate` artifact to the successful Windows
   qualification: installer, executable distribution inputs, and a provenance
   manifest containing commit SHA, lockfile digests, and installer SHA-256.
5. On tag push, Release downloads the artifact from the successful exact-SHA CI
   run, verifies provenance and digests before use, and does not rebuild the
   NSIS installer. It still builds the wheel, creates Green/Portable archives,
   creates SBOM/checksums, and performs draft-release/download readback.
6. Cache npm downloads and Rust build inputs in both Windows workflows. Cache
   keys are lockfile-bound and restore keys never replace provenance checks.

## Boundaries

- The release artifact must be produced only after `desktop-build` and before
  `installer-lifecycle`; the lifecycle job verifies the same installer.
- The artifact manifest binds `github.sha`, `src-tauri/Cargo.lock`,
  `frontend/package-lock.json`, and `uv.lock`; Release rejects any mismatch.
- The release identity remains tag-specific. Therefore the promoted installer
  is an RC installer with a candidate identity, while release metadata binds
  the tag to the verified CI SHA. The existing release-only identity file is
  retained for all published payloads.
- No release can use a skipped, failed, expired, or foreign-run artifact.

## Data Flow

`GatePlan -> desktop-build -> release-candidate artifact -> installer-lifecycle
-> a0-gates -> exact-SHA CI -> tag -> Release download/verify -> archive,
SBOM, checksum, draft readback, publish`.

## Verification

- Structural tests assert job selection, cache keys, artifact names, and
  provenance checks.
- Classifier tests assert targeted gates no longer require the primary suite.
- Workflow YAML is parsed locally.
- Targeted Python tests and the workflow-contract test file run locally.
- A Windows package build is executed locally when the project toolchain is
  available; cloud CI is the authoritative installed-NSIS verification.

## Non-goals

- Do not remove the Windows lifecycle, browser, wheel, compatibility, or
  exact-SHA release checks.
- Do not introduce a self-hosted runner or change release permissions.
