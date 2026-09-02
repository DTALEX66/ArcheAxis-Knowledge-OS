# Runtime Authority and Language G0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every Windows UI repair traceable to one canonical host/build/deployment chain while advancing only the evidence gates required before the Rust language migration can begin.

**Architecture:** The primary Tauri host embeds `frontend/dist`; the recovery host is a distinct fallback surface. A documentation authority map and static tests prevent future deployments from confusing those chains. Language work stays in G0: inventory present owners and qualification evidence before any shared crate or writer migration.

**Tech Stack:** Markdown authority records, Python pytest static contracts, React/Vite build input, Rust/Tauri primary shell.

**Spec:** `docs/current/AXM_LANGUAGE_AUDIT_TASK_ADOPTION_2026-09-02.md`, `docs/current/AX_DIRECTORY_MIGRATION_TASK_ADOPTION_2026-09-02.md`, and `docs/current/AXM_G0_MIGRATION_FREEZE_RULES_2026-09-02.md`.

## Global Constraints

- Keep `v0.6.14`; do not create a version, tag, installer, mobile artifact or release.
- The primary Windows host is `src-tauri`; `desktop/src-tauri` is recovery-only.
- No Green `data/`, runtime database, ignored evidence or user material is inspected, copied, cleared or migrated.
- Rust does not receive a production writer until every G0 entry gate has evidence.
- No tracked directory move or deletion occurs before a frozen-tree path/hash/reference manifest and its explicit deletion gate.

---

### Task 1: Make primary runtime delivery authoritative

**Files:**
- Create: `docs/RUNTIME_DELIVERY_AUTHORITY_INDEX.md`
- Create: `tests/test_runtime_delivery_authority.py`
- Modify: `docs/DOCUMENTATION_AUTHORITY_INDEX.md`

**Interfaces:**
- Consumes: primary Tauri config and source at `src-tauri/`.
- Produces: one cited delivery-chain record and a pytest regression contract.

- [ ] **Step 1: Write the failing static contract**

```python
def test_runtime_delivery_authority_index_names_the_primary_shell_chain() -> None:
    content = (ROOT / "docs/RUNTIME_DELIVERY_AUTHORITY_INDEX.md").read_text(encoding="utf-8")
    assert "src-tauri/tauri.conf.json" in content
    assert "frontend/dist" in content
    assert "ArcheAxis.Knowledge.Green-x64/ArcheAxis.exe" in content
```

- [ ] **Step 2: Run the targeted test and verify it fails because the index is absent**

Run: `.venv\\Scripts\\python.exe -m pytest tests/test_runtime_delivery_authority.py -q`

Expected: FAIL because `docs/RUNTIME_DELIVERY_AUTHORITY_INDEX.md` does not exist.

- [ ] **Step 3: Add the smallest authority map**

Document the primary chain, recovery-shell non-equivalence, Green hash backup/readback requirement and no-data boundary. Link only project-local authority documents.

- [ ] **Step 4: Run the targeted contracts**

Run: `.venv\\Scripts\\python.exe -m pytest tests/test_runtime_delivery_authority.py tests/test_documentation_authority_index.py -q`

Expected: PASS. If the interpreter cannot start, classify the result as `ENVIRONMENT_FAIL`, repair the project-local interpreter boundary separately, and do not call it a product-test failure.

### Task 2: Complete G0 owner/evidence inventory

**Files:**
- Modify: `docs/current/AXM_G0_OWNER_MAP_2026-09-02.md`
- Create: `docs/current/AXM_G0_EVIDENCE_GAP_REGISTER_2026-09-03.md`
- Test: `tests/test_documentation_authority_index.py`

**Interfaces:**
- Consumes: current writer implementations and current-state receipt records.
- Produces: explicit owners plus a bounded evidence gap register; neither changes domain writes.

- [ ] **Step 1: Write a failing contract for the gap register**

```python
def test_g0_evidence_gap_register_is_linked_from_the_documentation_index() -> None:
    content = (ROOT / "docs/DOCUMENTATION_AUTHORITY_INDEX.md").read_text(encoding="utf-8")
    assert "AXM_G0_EVIDENCE_GAP_REGISTER_2026-09-03.md" in content
```

- [ ] **Step 2: Verify the contract fails for the missing link**

Run: `.venv\\Scripts\\python.exe -m pytest tests/test_documentation_authority_index.py -q`

Expected: FAIL only after adding the explicit assertion in Step 1.

- [ ] **Step 3: Record each required G0 receipt gap**

List exact-SHA full CI, rights-bound golden corpus, fresh/existing workspace receipts, and first-wave single-writer coverage. For every line declare `evidence source`, `owner`, `verification command`, `status`, and `no-go consequence`.

- [ ] **Step 4: Expand the owner map from direct source evidence**

For Source, Anchor, Evidence, Claim, Human Learning Event and Machine Competence, cite the present writer implementation and keep unknown ownership `UNRESOLVED`; do not invent a Rust target writer.

- [ ] **Step 5: Run documentation contracts**

Run: `.venv\\Scripts\\python.exe -m pytest tests/test_documentation_authority_index.py -q`

Expected: PASS with every local Markdown link resolving.

### Task 3: Prepare, but do not execute, directory convergence

**Files:**
- Create: `docs/current/AX_DIR_010_INVENTORY_SCHEMA.md`
- Test: `tests/test_documentation_authority_index.py`

**Interfaces:**
- Consumes: frozen-tree snapshot and source-path classifications.
- Produces: a schema for a later manifest; it does not move or delete a path.

- [ ] **Step 1: Write a failing link contract**

```python
def test_directory_inventory_schema_is_linked_from_the_authority_index() -> None:
    content = (ROOT / "docs/DOCUMENTATION_AUTHORITY_INDEX.md").read_text(encoding="utf-8")
    assert "AX_DIR_010_INVENTORY_SCHEMA.md" in content
```

- [ ] **Step 2: Verify it fails before the schema exists**

Run: `.venv\\Scripts\\python.exe -m pytest tests/test_documentation_authority_index.py -q`

Expected: FAIL only for the missing explicit link.

- [ ] **Step 3: Define the later manifest schema**

Require source path, target path, owner, data class, SHA-256, consumers, rollback, verification and explicit deletion authorization fields. Mark all existing dirty paths and Green data `PRESERVE`.

- [ ] **Step 4: Verify all documentation contracts**

Run: `.venv\\Scripts\\python.exe -m pytest tests/test_runtime_delivery_authority.py tests/test_documentation_authority_index.py -q`

Expected: PASS.
