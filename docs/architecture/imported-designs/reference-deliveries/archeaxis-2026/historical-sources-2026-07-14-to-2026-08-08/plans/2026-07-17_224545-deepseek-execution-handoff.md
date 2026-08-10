# DeepSeek Execution Handoff Plan

**Goal:** Transfer Cognitive Loop OS continuation to DeepSeek through a dependency-safe queue that preserves the frozen container candidate and reserves independent review/release authority for Hermes/Codex.

**Architecture:** DeepSeek first performs report-only live reconciliation, then becomes the bounded implementation writer for contracts, structured data and Python TDD slices after each phase gate. Every code candidate is frozen and handed to an independent reviewer; DeepSeek never self-approves or publishes its own work.

**Tech Stack:** Python 3.10/3.11, pytest, Ruff, SQLite contracts/migrations, JSON/YAML schemas, Git/GitHub CI, Markdown planning reports.

---

## Task 1: Bootstrap DeepSeek safely

**Objective:** Start a fresh DeepSeek-backed Hermes session with project rules loaded.

**Files:**
- Read: `migrations/reports/current-reconciliation/DEEPSEEK_EXECUTION_HANDOFF.md`
- Read: `migrations/reports/current-reconciliation/DEEPSEEK_TASK_CATALOG.md`

**Steps:**

1. Run the supported switch script from `D:/All projects/Workflow-assistance`.
2. Start a fresh session with `/reset`; provider/model/toolsets are frozen in the current session.
3. Paste the DS00 bootstrap prompt from the catalog.
4. Confirm cwd is `D:/All projects/Cognitive-Loop-OS` and `AGENTS.md` was loaded.

## Task 2: Execute DS00 only

**Objective:** Produce a live P03 acceptance blueprint without code changes.

**Output:** `migrations/reports/deepseek/DS00_P03_LIVE_ACCEPTANCE_BLUEPRINT.md`

**Verification:**

```bash
git status --short --branch
git diff --cached --name-only
```

Expected: only the assigned report is new/changed; no staged code.

## Task 3: Review DS00 and release P00A outside DeepSeek

**Objective:** Keep high-risk exact-tree review and publication independent.

**Boundary:** Hermes/Codex reviews `3d99e200dff9d816a0767a3c46f0689575ed5b7c`; DeepSeek does not touch the container checkout.

## Task 4: Execute gated queue

**Objective:** Run DS10–DS18 in dependency order with one writer and independent stage-end review.

**Rules:** RED/GREEN for behavior, changed-file Ruff, local checkpoint, one full gate per stage, freeze exact tree, no self-GO, no push/merge.

## Task 5: Execute non-preemptive foundations

**Objective:** After Phase 3, run Registry V2, Model Registry and Workspace strategy documents only when they do not preempt Phase 5–9.

## Task 6: Post-P9 and research trains

**Objective:** Start Workspace backend contracts and isolated Claude/Grok/open-source research only after their gates. UI/visual work stays with a vision-capable model.

## Risks

- PR #2 is stacked on PR #1; merge order can silently bundle Phase 4.
- Package task/phase numbering is internally inconsistent.
- Registry has 101 rows despite an ID namespace ending at 0103.
- Package P03 predates current migration/lease/container corrections.
- A DeepSeek writer cannot independently validate its own high-risk release.

## Final handback evidence

Every task returns starting SHA, changed files, RED/GREEN output, final gates, `git diff --check`, status, frozen tree and non-claims.
