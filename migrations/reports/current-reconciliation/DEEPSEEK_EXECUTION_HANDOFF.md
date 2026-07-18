# DeepSeek Execution Handoff

Generated: `2026-07-17T22:45:45+08:00`

## 0. Purpose

This is the authoritative entry point for continuing Cognitive Loop OS with DeepSeek. It converts the v4.0 planning package and live P00 evidence into a safe execution queue. The planning package is input; live Git, CI, `AGENTS.md`, and `docs/VERIFICATION_POLICY.md` remain authoritative.

## 1. Mandatory reading order

DeepSeek must read these files before acting:

1. `AGENTS.md`
2. `docs/VERIFICATION_POLICY.md`
3. `docs/EXECUTION_ROADMAP.md`
4. `docs/HANDOFF_2026-07-16.md`
5. `migrations/reports/current-reconciliation/LOCAL_REMOTE_STATE.md`
6. `migrations/reports/current-reconciliation/WORKTREE_STATE.txt`
7. `migrations/reports/current-reconciliation/CURRENT_PHASE_EVIDENCE.md`
8. `migrations/reports/current-reconciliation/ASSET_DELTA.md`
9. `migrations/reports/current-reconciliation/NEXT_TASKPACK.md`
10. `migrations/reports/current-reconciliation/DEEPSEEK_TASK_CATALOG.md`

Do not treat repo-local `.hermes/closure-tasks/status.json` as current truth. It predates later successful Git/CI evidence.

## 2. Live baseline

### Authoritative main

- Checkout: `D:/All projects/Cognitive-Loop-OS`
- Branch: `main`
- Baseline SHA: `9a0886a00db739f9835f827f598616df835e5e6b`
- Baseline equals `origin/main` at P00.
- P00 reports are untracked/generated and must be preserved.

### Frozen container correction candidate

- Checkout: `D:/All projects/Cognitive-Loop-OS-container`
- Branch: `feat/complete-container-stack`
- HEAD: `53bd093b7684bdaed0ce7f6c9ff9326697d3d82b`
- Frozen staged tree: `3d99e200dff9d816a0767a3c46f0689575ed5b7c`
- This checkout is **off-limits to DeepSeek** until an independent exact-tree reviewer returns GO or a specific reproducible finding is assigned.

### Release graph

- PR #1 is the Phase 4 Research candidate.
- PR #2 is stacked on PR #1 and carries container delivery.
- Main still lacks authoritative Phase 3 cross-owner integration acceptance.
- Do not merge either PR from DeepSeek.

## 3. DeepSeek operating contract

### Allowed

- Read-only repository and planning analysis.
- Writing bounded reports under `migrations/reports/deepseek/`.
- After an explicit gate release: bounded code changes in a dedicated branch/worktree, TDD, targeted tests, changed-file Ruff, and local checkpoint commits.
- Structured data transformation, schemas/contracts, migration dry-runs over synthetic/temp data, unit/integration tests, deterministic documentation and traceability matrices.

### Forbidden

- Touching `D:/All projects/Obsidian-Assistance` or `E:/`.
- Modifying the frozen container checkout/tree.
- Reset, restore, clean, rebase, amend, force-push, stash apply/drop, branch deletion, worktree removal.
- Push, merge, PR approval, release publication, or self-issued final GO.
- Production/private database writes or migrations.
- Reading or copying credentials, `.env`, auth files, browser cookies, tokens, or secrets.
- Downloading Grok-1 weights or installing JAX/CUDA stacks in the main environment.
- Whole-repo vendoring of external projects.
- Creating Workspace/UI runtime before its phase gate.
- Claiming completion from file existence, stubs, dry-run, preview, fixed fake data, or self-review.

## 4. Single-writer and verification rules

1. One code writer per checkout.
2. Read-only analysis tasks may run in parallel only if they write separate report paths.
3. Every behavior change uses RED → GREEN.
4. Low-risk stages: targeted RED/GREEN + changed-file Ruff + local checkpoint; one full root/KB/integration/Ruff/guard run at stage end.
5. Security, permissions, schema/database migration, architecture, dependency, container, and release changes require immediate independent full-gate review.
6. DeepSeek may prepare a candidate; Hermes/Codex must independently review the frozen exact tree and handle push/merge/CI identity.
7. Never rerun identical green suites without changed evidence.

## 5. What DeepSeek should run first

Run only `DS00` from `DEEPSEEK_TASK_CATALOG.md` in the first DeepSeek session.

Expected first output:

```text
migrations/reports/deepseek/DS00_P03_LIVE_ACCEPTANCE_BLUEPRINT.md
```

DS00 is report-only. It must not change code, tests, Git history, branches, PRs, or the frozen container checkout.

After DS00, stop and report:

- paths inspected;
- actual Phase 3 boundaries found in live code;
- obsolete assumptions in package P03;
- exact proposed RED tests and gate commands;
- blockers and required owner decisions;
- `git status --short --branch` for the canonical checkout.

## 6. Gate order

```text
P00A independent exact-tree review/publication (Hermes/Codex)
→ DS10 Phase 3 implementation candidate
→ independent review + exact-SHA CI + Phase 3 merge
→ PR #1 rebase-free base reconciliation and review
→ PR #2 container-only reconciliation and review
→ DS11/DS12 bounded registry foundations
→ DS13–DS18 Phase 5–9 in order
→ DS19 Workspace strategy docs
→ DS20+ post-Phase-9 backend platform work
→ external Claude/Grok selective trains without preemption
```

## 7. Completion protocol for every DeepSeek task

DeepSeek must return:

1. Task ID and exact starting SHA/tree.
2. Files read and files changed.
3. RED command/output and GREEN command/output when code changed.
4. Final gate output, not paraphrased claims.
5. `git diff --check` and `git status --short --branch`.
6. Frozen candidate tree (`git write-tree`) when staged.
7. Remaining risks, non-claims, and explicit handback owner.
8. No push/merge unless a later explicit policy changes this handoff.

## 8. Provider readiness

Verified at `2026-07-17T22:49+08:00` with the repository-supported workflow:

- Hermes default provider: `deepseek`
- Hermes default model: `deepseek-v4-flash`
- Base URL: official `https://api.deepseek.com/v1`
- Credential inventory: present and redacted
- Live marker: `OK_DEEPSEEK_LIVE`
- Hermes GPT OAuth marker: `OK_GPT_LIVE`
- Codex exec marker: `OK_CODEX_LIVE`
- Structural checks: passed

The switch is already written to Hermes configuration. Provider/model/toolsets are frozen in the current conversation, so issue `/reset` before starting DS00. Then paste the bootstrap prompt from `DEEPSEEK_TASK_CATALOG.md`.

To switch again later, use only:

```bash
cd "D:/All projects/Workflow-assistance"
python scripts/workflow/switch_model.py deepseek
```
