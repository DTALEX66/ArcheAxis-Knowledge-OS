# CI and Release Performance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make routine validation selective and let Release reuse a verified CI installer with a cryptographic provenance contract.

**Architecture:** CI maps semantic GatePlan IDs to independently runnable Python jobs and publishes an immutable Windows release-candidate artifact. Release locates the successful exact-SHA CI run, downloads that artifact, verifies its manifest and hashes, then packages and publishes without a second NSIS build.

**Tech Stack:** GitHub Actions YAML, PowerShell, Python/pytest, uv, npm, Tauri/NSIS.

**Spec:** `docs/superpowers/specs/2026-08-22-ci-release-performance-design.md`

## Global Constraints

- Preserve semantic GatePlan IDs and fail-closed aggregation.
- Preserve exact-SHA, checksum, SBOM, and draft-release download readback.
- Never stage the two pre-existing user-modified files.

---

### Task 1: Make Python gates actually selective

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `tests/test_ci_a0_gates.py`

- [ ] Add failing workflow-contract tests for separate primary and targeted jobs.
- [ ] Run the named tests and confirm the new assertions fail against the old workflow.
- [ ] Add targeted jobs for format, migration, and security risks; leave the existing primary suite unchanged for `py-primary` and full qualification.
- [ ] Update `a0-gates` to require every selected semantic Python gate.
- [ ] Run the named tests and confirm they pass.

### Task 2: Add cache and release-candidate provenance

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `tests/test_ci_a0_gates.py`

- [ ] Add failing assertions for npm cache and a release-candidate manifest/artifact.
- [ ] Run the named tests and confirm they fail.
- [ ] Add lockfile-bound npm cache, generate provenance after the installer build, and upload candidate inputs and manifest.
- [ ] Run the named tests and confirm they pass.

### Task 3: Promote verified CI installer in Release

**Files:**
- Modify: `.github/workflows/release.yml`
- Modify: `tests/test_ci_a0_gates.py`

- [ ] Add failing assertions that Release downloads the exact CI candidate and verifies commit, lock digests, and SHA-256 without running Tauri build.
- [ ] Run the named tests and confirm they fail.
- [ ] Implement artifact lookup/download, manifest validation, and promoted installer staging; retain wheel, archive, metadata, and readback steps.
- [ ] Run the named tests and confirm they pass.

### Task 4: Verify and package

**Files:**
- Modify: workflow and test files from Tasks 1-3 only.

- [ ] Parse both workflow YAML files locally.
- [ ] Run `pytest tests/test_ci_a0_gates.py tests/test_ci_classifier.py -q`.
- [ ] Run the project’s targeted CI test command for the changed files.
- [ ] Run the local Windows package build if dependencies/toolchain are available; record a precise environment blocker otherwise.
- [ ] Inspect `git diff --check`, diff, and status; commit only owned files.
