# M0 Evidence Truth Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace stale checked-in “current” Git/CI/release claims with generated, SHA-bound artifacts that distinguish current source state, verified v0.6.7 release evidence, and still-partial product capabilities.

**Architecture:** Immutable public release facts live in one machine-readable receipt under `reports/release/v0.6.7/`. The current-report generator validates and consumes that receipt but writes ephemeral current-state reports only under ignored `.hermes/task-artifacts/current-reports/`, avoiding the impossible requirement that a checked-in file contain the SHA of the commit that contains itself. A separate task-pack audit maps every M0–M7 capability to explicit evidence or a truthful incomplete state.

**Tech Stack:** Python 3.12, pytest, JSON Schema-style validation in Python, Git, GitHub Actions evidence, Markdown.

**Spec:** `D:/All projects/ArcheAxis_v0.6.0_Minimum_Closed_Loop_Release_TaskPack_2026-08-20.md`

## Global Constraints

- Preserve the user’s original dirty files in the primary checkout.
- Generated evidence, caches, and temporary environments stay below project `.hermes/`.
- A successful Release proves publication and lifecycle only; it must not promote unrelated product capabilities.
- Every current report names exact commit/tree, evidence level, generation environment, and limitations.
- `v0.6.0` through `v0.6.7` tags remain immutable.

---

### Task 1: Immutable v0.6.7 Release Evidence Receipt

**Files:**
- Create: `reports/release/v0.6.7/release-evidence.json`
- Create: `tests/test_release_evidence_receipt.py`

**Interfaces:**
- Consumes: Git tag `v0.6.7`, CI run `32599003326`, Release run `32599851308`, and the nine provider SHA-256 digests recorded by GitHub.
- Produces: schema `archeaxis.release-evidence.v1` with `release`, `source`, `runs`, `assets`, `dependency_locks`, `verification`, and `limitations` fields.

- [ ] **Step 1: Write the failing receipt-contract test**

```python
def test_v067_release_receipt_binds_distinct_runs_and_all_public_assets() -> None:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert receipt["schema_version"] == "archeaxis.release-evidence.v1"
    assert receipt["source"]["commit_sha"] == "347d9f957b0509185df8c64e0578061a1ce2f9e3"
    assert receipt["runs"]["verification_ci"]["id"] == 32599003326
    assert receipt["runs"]["release"]["id"] == 32599851308
    assert receipt["runs"]["verification_ci"]["id"] != receipt["runs"]["release"]["id"]
    assert len(receipt["assets"]) == 9
    assert all(len(asset["sha256"]) == 64 for asset in receipt["assets"])
```

- [ ] **Step 2: Run the test and verify RED**

Run: `python -m pytest tests/test_release_evidence_receipt.py -q`
Expected: FAIL because the receipt file does not exist.

- [ ] **Step 3: Add the literal audited receipt**

Record the exact tag/commit/tree, two successful run URLs, publication timestamp, nine asset names/sizes/digests, three dependency-lock hashes, independent readback result, and the limitation that the receipt does not prove deferred product capabilities.

- [ ] **Step 4: Run the test and verify GREEN**

Run: `python -m pytest tests/test_release_evidence_receipt.py -q`
Expected: PASS.

### Task 2: Current Report Generator Separates Source, Release, and Capability Truth

**Files:**
- Modify: `scripts/generate_current_reports.py`
- Modify: `tests/test_current_report_generator.py`
- Modify: `.gitignore`
- Delete: `reports/current/CLOUD_BASELINE.json`
- Delete: `reports/current/EXACT_SHA_VERIFICATION.json`
- Delete: `reports/current/CURRENT_CAPABILITY_MATRIX.json`
- Create: `reports/current/README.md`

**Interfaces:**
- Consumes: optional validated `release-evidence.json` and current Git refs.
- Produces: `CLOUD_BASELINE.json`, `EXACT_SHA_VERIFICATION.json`, and `CURRENT_CAPABILITY_MATRIX.json` below `.hermes/task-artifacts/current-reports/` by default.

- [ ] **Step 1: Write failing behavior tests**

```python
def test_current_reports_keep_release_pass_separate_from_partial_capabilities(tmp_path: Path) -> None:
    generate(tmp_path, DEFAULT_TASKPACK_BASELINE, release_evidence=RELEASE_EVIDENCE)
    matrix = json.loads((tmp_path / "CURRENT_CAPABILITY_MATRIX.json").read_text())
    assert matrix["release_gate"] == "PASS"
    assert matrix["overall_status"] == "PARTIAL"
    assert matrix["capabilities"]["windows_setup_green_portable_lifecycle"] == "PASS"
    assert matrix["capabilities"]["six_space_ui_real_data"] == "PARTIAL"

def test_default_output_is_ignored_project_artifact() -> None:
    assert DEFAULT_OUTPUT_DIR == ROOT / ".hermes" / "task-artifacts" / "current-reports"
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m pytest tests/test_current_report_generator.py -q`
Expected: FAIL because the generator has no release-evidence input and defaults to tracked `reports/current`.

- [ ] **Step 3: Implement validated evidence loading and layered report output**

Add `DEFAULT_OUTPUT_DIR`, `DEFAULT_RELEASE_EVIDENCE`, `load_release_evidence(path)`, and `release_evidence` to `generate`. Reject wrong schema, non-success runs, equal run IDs, duplicate/missing assets, or malformed SHA-256. Emit source HEAD separately from release commit and retain `overall_status=PARTIAL` until product receipts prove each capability.

- [ ] **Step 4: Stop tracking self-referential current JSON**

Add `.hermes/task-artifacts/current-reports/` to ignored task artifacts if not already covered, remove the three stale tracked JSON files, and add `reports/current/README.md` explaining that remaining dated files are historical snapshots while live reports are generated under `.hermes`.

- [ ] **Step 5: Run tests and conventions**

Run: `python -m pytest tests/test_current_report_generator.py tests/test_release_evidence_receipt.py -q`
Run: `python scripts/check_repository_conventions.py --source worktree`
Expected: PASS.

### Task 3: Golden Journey Coverage Must Name Every Missing Gate

**Files:**
- Modify: `scripts/generate_golden_journey_receipt.py`
- Modify: `tests/test_golden_journey_receipt.py`

**Interfaces:**
- Consumes: named local journey test results and the immutable release evidence receipt.
- Produces: a local receipt with explicit `coverage` keys for four-library setup, RawAsset/conversion/anchors, identity review, dual assets, six-space browser, export/import, desktop restart, and three-distribution lifecycle.

- [ ] **Step 1: Write a failing coverage test**

```python
def test_golden_receipt_reports_gate_coverage_without_promoting_missing_ui() -> None:
    receipt = generate(...)
    assert receipt["coverage"]["raw_asset_conversion_anchors"] == "PASS"
    assert receipt["coverage"]["six_space_browser"] == "NOT_EXECUTED"
    assert receipt["coverage"]["three_distribution_lifecycle"] == "PASS_EXTERNAL_EVIDENCE"
    assert receipt["overall_status"] == "PARTIAL"
```

- [ ] **Step 2: Run and verify RED**

Run: `python -m pytest tests/test_golden_journey_receipt.py -q`
Expected: FAIL because `coverage` does not exist.

- [ ] **Step 3: Implement explicit coverage projection**

Map named tests to the local gates they actually execute; consume only release lifecycle/publication facts from the release receipt; leave browser, actor-review, and full dual-asset gates incomplete unless a named executable test is added.

- [ ] **Step 4: Run and verify GREEN**

Run: `python -m pytest tests/test_golden_journey_receipt.py -q`
Expected: PASS.

### Task 4: M0–M7 Evidence Audit Artifact

**Files:**
- Create: `docs/current/AXR_060_COMPLETION_AUDIT_2026-08-23.md`
- Create: `workspace/intake/2026-08-23-axr-060-evidence-truth-reset.md`

**Interfaces:**
- Consumes: the v0.6.0 task pack, source/test paths, v0.6.7 release receipt, generated current reports, and Golden Journey coverage.
- Produces: one requirement-by-requirement table classifying each AXR-060 task and each of 12 release blockers as `PASS`, `PARTIAL`, `NOT_EXECUTED`, or `BLOCKED`, with exact evidence and next executable slice.

- [ ] **Step 1: Generate fresh local reports and Golden receipt**

Run: `python scripts/generate_current_reports.py`
Run: `python scripts/generate_golden_journey_receipt.py`
Expected: current Git/source and release layers are accurate; product-wide overall status remains PARTIAL.

- [ ] **Step 2: Write the audit and intake note**

For every M0–M7 task and blocker 1–12, cite an executable test/receipt or mark the evidence missing. Select the first incomplete dependency-ordered vertical slice as the next implementation plan.

- [ ] **Step 3: Self-review against the task pack**

Confirm all 24 AXR tasks and all 12 blockers appear exactly once, no PASS relies only on prose/file existence, and no missing evidence is silently omitted.

- [ ] **Step 4: Run final M0 verification**

Run: `python -m pytest tests/test_current_report_generator.py tests/test_release_evidence_receipt.py tests/test_golden_journey_receipt.py -q`
Run: `python scripts/check_repository_conventions.py --source worktree`
Run: `git diff --check`
Expected: PASS with generated artifacts confined to ignored `.hermes` paths.
