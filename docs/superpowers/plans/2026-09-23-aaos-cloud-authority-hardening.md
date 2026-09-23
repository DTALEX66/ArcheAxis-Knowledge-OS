# AAOS Cloud Authority Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将云端审计提出的治理结论收敛到当前 AAOS checkout：以现有 Candidate/Evidence/Promotion 能力为基础，形成可追溯、可失效、不可绕过的 Knowledge–Evidence–Learning–Experience 生命周期。

**Architecture:** 先以当前 checkout 的 `app/`、`packages/contracts/`、`shared-contracts/`、`crates/` 和测试为唯一实现事实，云端报告仅作为待复核输入。先完成只读对象矩阵和边界审计，再以小步 TDD 加固 Candidate、Evidence、Promotion、Experience 和 Receipt；外部项目只通过 Adapter/Receipt 进入 Candidate，绝不成为 Canonical Truth。

**Tech Stack:** Python contracts/tests, Rust contracts/Core, C#/Avalonia UI only where required by the existing P3 scope, JSON/YAML schemas, GitHub Actions YAML static audit.

**Spec:** `docs/current/AAOS-CLOUD-AUDIT-RECONCILIATION-20260923.md`; authority remains `docs/CONFIGURATION_AUTHORITY_INDEX.md`, R6 TaskPack and M0 override.

## Global Constraints

- 当前前端 P3/staging 任务优先；本计划不得抢占前端完成和 Local Green Owner Gate。
- 不建立第二套 Candidate/Prompt Library；复用当前 Candidate/Evidence/Promotion 表面。
- External content ≠ trusted knowledge；model score ≠ evidence；build/test ≠ runtime/GUI。
- 不访问 E/F 盘、私有会话、凭据、Green 用户数据、真实资料库或未授权外部仓库。
- 不直接写 Canonical SQLite；不双写 legacy/vNext；不自动 Promotion、Self-Merge、Self-Deploy。
- 每个实现任务按 RED → GREEN → targeted regression → affected gate 验证。
- 每个结论必须区分 `PLANNED`、`IMPLEMENTED_LOCAL`、`TESTED_LOCAL`、`UNVERIFIED`、`BLOCKED`。

---

### Task 1: Freeze the current canonical object inventory

**Files:**
- Create: `docs/current/AAOS-CANONICAL-OBJECT-INVENTORY-V1.md`
- Read: `app/`, `packages/contracts/`, `shared-contracts/`, `crates/`, `tests/`
- Test: `tests/test_documentation_authority_index.py`

- [ ] Step 1: Enumerate each current object implementation and record path, line, fields, serializer, creator, writer and lifecycle.
- [ ] Step 2: Map duplicate/legacy/vNext representations and label each as canonical, compatibility, derived or historical.
- [ ] Step 3: Run the documentation authority test and `git diff --check`.
- [ ] Step 4: Review the inventory before changing schemas.

### Task 2: Harden the existing Candidate boundary

**Files:**
- Modify only after Task 1: `shared-contracts/schemas/github_project_candidate.schema.json`, `shared-contracts/validators/validate_project_candidates.py`, `app/agent/experience_harvest.py`, `app/knowledge/promotion.py`
- Test: `tests/test_machine_knowledge_candidates.py`, `tests/test_knowledge_candidate_versioning.py`, `tests/test_research_to_knowledge_promotion.py`

- [ ] Step 1: Add a failing test for each confirmed bypass: missing source identity, missing content hash, unknown license, unsafe path/command input, and direct Candidate-to-Active transition.
- [ ] Step 2: Run only the new focused tests and record RED output.
- [ ] Step 3: Implement the smallest validation/policy change in the existing boundary.
- [ ] Step 4: Run the focused tests plus the affected contract gate; retain negative-test evidence.
- [ ] Step 5: Verify no new parallel Prompt Library or auto-execution path was added.

### Task 3: Prove Evidence Graph traceability

**Files:**
- Modify only after inventory: `app/evidence/graph.py`, `app/evidence/relations.py`, `app/evidence/ledger.py`, `app/evidence/bundle.py`
- Test: `tests/test_evidence_graph.py`, `tests/test_evidence_contract.py`, `tests/test_evidence_bundle.py`, `tests/test_evidence_index.py`
- Evidence: `docs/current/AAOS-EVIDENCE-PROVENANCE-REPLAY-20260923.md`

- [ ] Step 1: Select a bounded sample of current non-secret evidence objects and trace Source → Claim → Evidence → Validation/Receipt → Review/Promotion.
- [ ] Step 2: Add failing tests for each observed broken link before changing production code.
- [ ] Step 3: Implement only missing read/provenance links; do not invent evidence values.
- [ ] Step 4: Run the focused evidence tests and record `TRACEABILITY_GAP` for unresolved links.

### Task 4: Freeze Promotion and Experience lifecycle

**Files:**
- Modify only after Task 1: `app/knowledge/promotion.py`, `app/agent/experience_harvest.py`, relevant `packages/contracts/` or `shared-contracts/` schema
- Test: `tests/test_research_to_knowledge_promotion.py`, `tests/test_knowledge_candidate_versioning.py`, `tests/test_experience_harvest.py`
- Evidence: `docs/current/AAOS-PROMOTION-EXPERIENCE-V1.md`

- [ ] Step 1: Add RED negative tests for Candidate→Active, Quarantined→Active, stale→Active without revalidation, and evaluator-score-only promotion.
- [ ] Step 2: Define the minimal receipt fields: actor, policy version, evidence refs, validation refs, timestamp and source commit.
- [ ] Step 3: Implement legal transitions and immutable receipt emission using existing project patterns.
- [ ] Step 4: Add applicability/version/expiry fields only where the current canonical schema supports them; otherwise document the gap.
- [ ] Step 5: Run focused tests and a restart/readback check where the existing runtime supports it.

### Task 5: Audit CI and dependency supply chain

**Files:**
- Read: `.github/workflows/ci.yml`, `.github/workflows/nightly.yml`, `.github/workflows/release.yml`, `.github/workflows/vnext-ci.yml`, `pyproject.toml`, `requirements.txt`, `uv.lock`, `scripts/`
- Create: `docs/current/AAOS-CI-SUPPLY-CHAIN-AUDIT-20260923.md`
- Test: applicable repository documentation/contract gate; no installation command is part of this audit.

- [ ] Step 1: Record every Action reference and whether it is commit-SHA pinned.
- [ ] Step 2: Record workflow permissions and any `pull_request_target`, secrets, write scopes or untrusted checkout combinations.
- [ ] Step 3: Search for runtime downloads, unpinned dependency installs, shell execution and external binary use; attach file/line evidence.
- [ ] Step 4: Separate static findings from unvisited Actions logs, rulesets, environments and security advisories.
- [ ] Step 5: Produce remediation tasks; do not silently rewrite workflows in the audit task.

### Task 6: Establish cross-project Receipt boundary

**Files:**
- Read only after exact user authorization: `D:\All projects\Jarvis-Work-Lab`, `D:\All projects\DesignLab`
- Modify only in AAOS after contracts are agreed: `shared-contracts/`, `app/adapters/`
- Test: new contract tests must cover Receipt→Candidate and direct Active-Knowledge write rejection.

- [ ] Step 1: Obtain exact read-only scope for the two external repositories; do not scan shared libraries or private state.
- [ ] Step 2: Map actual API/file/MCP/DB/message paths and permissions with file/line evidence.
- [ ] Step 3: Freeze a versioned ExecutionReceipt/DesignReceipt exchange contract.
- [ ] Step 4: Add negative tests proving external receipts cannot directly promote Active Knowledge.

### Task 7: Evaluate adapters and experiment sandbox only after P0 gates

**Files:**
- Create only after Tasks 1–6 pass their gates: adapter-specific files under `app/adapters/` and versioned contracts under `shared-contracts/`
- Test: adapter round-trip, unknown-license quarantine, prompt-injection rejection, changed-source detection, and experiment escape tests.

- [ ] Step 1: Review upstream freshness and license evidence before selecting any adapter.
- [ ] Step 2: Implement one adapter per bounded source with no canonical-model replacement.
- [ ] Step 3: Keep AutoResearch in isolated worktree/sandbox with no production secrets, protected-branch write, package download or automatic promotion.

## Completion gate

This plan is not complete when documents or tests merely exist. Completion requires fresh evidence for each task, exact changed paths, targeted test output, and explicit unresolved gaps. Final outcomes remain `LOCAL_GREEN_READY_FOR_OWNER_REVIEW` or `NOT_READY`; this plan never authorizes release, Green overwrite, signing or self-merge.
