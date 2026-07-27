# N-001: Release Artifact Checksum, Provenance, Installer Gates (2026-07-27)

## Summary

Implemented N-001 (release artifact, checksum, provenance, installer gates) on
`feat/absorption-roadmap-r0` (HEAD `7e0d883`, tree `5aeaa2c`).

## Deliverables

| Component | Status | Evidence |
|---|---|---|
| Checksum generation script | ✅ | `scripts/release_checksum.py` — SHA-256 manifest generation |
| Identity injection script | ✅ | `scripts/release_inject_identity.py` — commit/tree/CI-run injection |
| Release gate tests (7 new) | ✅ | 12/12 release manifest tests pass (5 existing + 7 new) |
| Wheel build (current tree) | ✅ | `dist/cognitive_loop_os-0.4.0-py3-none-any.whl` (378 KB) |
| Checksum manifest (current tree) | ✅ | SHA-256: `67e241878b5481b05d8fa1f0dc1a85c674445bb5e03fb68e96bc6e02d3bbcd4b` |
| Identity manifest (current tree) | ✅ | commit=7e0d883, tree=5aeaa2c, branch=feat/absorption-roadmap-r0 |
| All adjacent tests | ✅ | 266/266 pass (adapter, evaluation, index, obsidian, runtime_intent) |
| Hardening + release manifest | ✅ | 57/57 pass (12 release + 45 hardening) |

## N-001 Verification Matrix (current tree)

| Dimension | Status | Evidence |
|---|---|---|
| **Build evidence (wheel)** | ✅ | `dist/cognitive_loop_os-0.4.0-py3-none-any.whl` built via setuptools |
| **Build evidence (desktop)** | ⚠️ partial | CI builds NSIS installer on `main` — current-tree desktop build not done (45-min build, Tauri/Rust deps) |
| **Checksum generation** | ✅ | `scripts/release_checksum.py` generates valid SHA-256 manifest (tested + current-tree) |
| **Provenance injection** | ✅ | `scripts/release_inject_identity.py` injects current-tree commit/tree/branch (tested + current-tree) |
| **SBOM generation** | ❌ not_implemented | No CycloneDX SBOM — deferred (requires `cyclonedx-bom` or similar) |
| **Tag-only release workflow** | ❌ not_implemented | No `.github/workflows/release.yml` — CI triggers only on push/PR to `main` |
| **Release manifest honesty** | ✅ | `public_installer: not_implemented`; `source.commit: unavailable`; `status: unreleased` |
| **Installer lifecycle** | ⚠️ partial | CI `desktop-shell` job verifies NSIS lifecycle on `main` — not current tree |
| **Public distribution** | ❌ not_implemented | No release upload/publication step — correctly blocked by manifest |

## Git status

Controlled dirty WIP preserved (14 modified + 18 untracked N-001+previous artifacts).
No reset, clean, or checkout was performed.

## Next pending tasks

Queue is now fully completed through N-001. All tasks H-001 through N-001 are
marked completed. Remaining:
- Sleep mode should enter `completed` or wait for user instructions.
- Potential follow-up: add release.yml workflow, SBOM generation, or desktop
  installer evidence for the current tree.
