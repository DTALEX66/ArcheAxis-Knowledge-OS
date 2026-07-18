# DeepSeek Task Catalog

Generated: `2026-07-17T22:45:45+08:00`
Updated: `2026-07-18T01:30:00+08:00` — absorbed deleg_e4ea4f02 findings, DS-L1→L6 completed, E1/E2 contracts added

## Absorbed findings from async 3-way analysis (deleg_e4ea4f02)

| Finding | Status |
|---|---|
| Registry V2 schema drift (status/absorption_mode enum mismatch) | ✅ Absorbed into `shared/registry_v2.py` — unified `AbsorptionMode`, `ProjectStatus`, `RiskPolicy` enums |
| Registry path drift (`shared-contracts/registries/` → `inspiration_research/resources/`) | ✅ Fixed in `scripts/batch_score_registry.py` |
| Claude/xAI/model assets must not preempt P03–P09 | ✅ Documented boundary preserved in handoff |
| TaskPack numbering conflicts (P04/P4, P05/P5) | ⚠️ Deferred to package-side resolution; not in container checkout

## How to use this catalog

- `NOW-R`: safe now, report-only/read-only analysis; may not touch the frozen container checkout.
- `GATED-W`: DeepSeek is suitable as implementation writer only after listed dependencies are GREEN and released.
- `POST-P9`: future platform/backend work after Minimum Complete System Alpha.
- `RESEARCH`: isolated candidate/intake work; cannot preempt Phase 3–9.
- Final independent review, push, merge and release are never assigned to the same DeepSeek writer.

## Queue summary

| ID | Mode | Task | Dependency | DeepSeek role |
|---|---|---|---|---|
| DS00 | NOW-R | Rewrite P03 acceptance from live code | none; do first | analyst/planner |
| DS01 | NOW-R | Main/PR1/PR2 semantic release graph matrix | DS00 or parallel separate report | analyst |
| DS02 | NOW-R | Phase 5–9 live gap inventory | DS00 | analyst |
| DS03 | NOW-R | Registry V2 dual-layout migration blueprint | DS00 | data architect |
| DS04 | NOW-R | Model Registry V1 contract blueprint | DS00 | contract architect |
| DS05 | NOW-R | Workspace 10.0 documentation normalization draft | DS00; no runtime code | documentation architect |
| DS10 | GATED-W | Phase 3 cross-owner integration candidate | P00A published + DS00 approved | code writer |
| DS11 | GATED-W | Open-source Registry V2 implementation | Phase 3 merged | data/code writer |
| DS12 | GATED-W | Model Registry foundation implementation | Phase 3 merged | contract/code writer |
| DS13 | GATED-W | P05 Knowledge/Learning/Machine Governance | Phase 4 merged/revalidated | code writer |
| DS14 | GATED-W | P06 Cognitive Enhancement artifacts | DS13 GREEN | code writer |
| DS15 | GATED-W | P07 dynamic planner/runtime | DS14 GREEN | code writer |
| DS16 | GATED-W | P07 multidimensional evaluation and lessons | DS15 GREEN | code writer |
| DS17 | GATED-W | P08 unified Sleep Loop | DS16 GREEN | code writer |
| DS18 | GATED-W | P09 five real MCS E2E loops | DS17 GREEN | integration writer |
| DS19 | GATED-W | Phase 10.0 Workspace strategy docs integration | Phase 3 merged; no runtime; non-preemptive | docs writer |
| DS20 | POST-P9 | Knowledge Document AST and Markdown golden round-trip | DS18 GREEN | backend writer |
| DS21 | POST-P9 | Stable IDs, properties, links, attachments, revisions | DS20 GREEN | backend writer |
| DS22 | POST-P9 | Typed graph and safe query/view backend | DS21 GREEN | backend writer |
| DS23 | POST-P9 | Plugin manifests/capabilities/permissions/audit | DS22 GREEN | security-contract writer |
| DS24 | POST-P9 | Sync change-log/conflict/recovery contracts | roadmap ADR + DS23 | backend writer |
| DS30 | RESEARCH | Open-source metadata and license enrichment | after core queue or bounded parallel | research intake |
| DS31 | RESEARCH | Claude asset registry/intake contracts | Phase 11 train | research/contracts |
| DS32 | RESEARCH | Grok-1 contracts and hardware estimator | Phase 11 train | research/contracts |
| DS33 | RESEARCH | Grok Build capability/security comparison | Phase 11 train | research analyst |

---

## DS00 — P03 live acceptance blueprint

**Mode:** NOW-R; first DeepSeek task.

**Goal:** Replace stale package P03 assumptions with an evidence-backed, executable Phase 3 integration TaskPack derived from current `main`, PR lineage and current tests.

**Read:** mandatory handoff list, package `taskpacks/P03_PHASE3_INTEGRATION_RELEASE.md`, relevant owner Facades/contracts/tests, `pyproject.toml`, CI workflow.

**Write only:** `migrations/reports/deepseek/DS00_P03_LIVE_ACCEPTANCE_BLUEPRINT.md`.

**Required content:**

1. Actual owner boundaries and SSOTs for Inspiration/Research, Formal Knowledge, Human Learning, Machine Knowledge and Runtime.
2. Exact existing integration tests and missing cross-owner assertions.
3. Contract fields and evidence IDs passed across each boundary.
4. Database/lease/migration constraints introduced after package P03.
5. RED test list with exact target files/test names and expected failure reason.
6. Minimal implementation slices, no directory redesign.
7. Targeted and full gate commands.
8. Explicit exclusions: Phase 4 recreation, container edits, Registry V2, Model Registry, Workspace/UI.

**Acceptance:** report is grounded in file/line evidence; no code/test/Git changes.

---

## DS01 — Release graph semantic matrix

**Mode:** NOW-R.

**Goal:** Produce a file/contract-level matrix for `main@9a0886a`, PR #1 and PR #2, proving which commits are Phase 4, container-only, or shared ancestry.

**Write only:** `migrations/reports/deepseek/DS01_RELEASE_GRAPH_MATRIX.md`.

**Acceptance:** includes branch SHAs, ancestry, changed path groups, contract/schema effects, merge-order risks, and a rebase-free reconciliation proposal. No branch mutation or PR action.

---

## DS02 — Phase 5–9 live gap inventory

**Mode:** NOW-R.

**Goal:** Map current reusable assets and real gaps against P05–P09 without creating code.

**Write only:** `migrations/reports/deepseek/DS02_PHASE5_9_GAP_MATRIX.md`.

**Acceptance:** each requirement is `existing / partial / missing / candidate-only`, with exact file/test evidence and dependency on prior phases. No speculative rewrite.

---

## DS03 — Registry V2 dual-layout blueprint

**Mode:** NOW-R.

**Goal:** Design a lossless migration from the 101-row legacy registry where IDs span `osp_0001..osp_0103`, IDs `0093/0095` are absent, and canonical duplicates exist.

**Sources:** main legacy JSON/CSV plus the Phase 4/container resource location. Do not modify either.

**Write only:** `migrations/reports/deepseek/DS03_REGISTRY_V2_BLUEPRINT.md`.

**Acceptance:** stable canonical IDs, legacy IDs/aliases, duplicate provenance, source/license/revision fields, maturity/risk/isolation policy, deterministic dry-run, rollback, schema validation and tests. Approximate Stars cannot be acceptance evidence.

---

## DS04 — Model Registry V1 blueprint

**Mode:** NOW-R.

**Goal:** Define provider/model contracts, capability metadata, routing policy and dry-run semantics without live provider calls or secrets.

**Write only:** `migrations/reports/deepseek/DS04_MODEL_REGISTRY_BLUEPRINT.md`.

**Acceptance:** versioned schemas, provider/model separation, capability/risk/cost/context fields, deterministic routing fixtures, no production activation, no secret paths.

---

## DS05 — Workspace 10.0 documentation normalization

**Mode:** NOW-R.

**Goal:** Reconcile duplicate future phase numbering and draft a documentation-only Workspace ADR plan.

**Write only:** `migrations/reports/deepseek/DS05_WORKSPACE_DOC_NORMALIZATION.md`.

**Acceptance:** one proposed phase numbering, dependency rules, capability registry structure, Obsidian compatibility policy, plugin migration policy, contract backlog and explicit no-runtime/no-UI/no-new-table boundary.

---

## DS10 — Phase 3 cross-owner integration candidate

**Mode:** GATED-W.

**Dependency:** P00A exact-tree candidate published/verified; DS00 reviewed; isolated branch/worktree assigned.

**Goal:** Prove the real path:

```text
Research candidate
→ Formal Knowledge reviewed state
→ Learning artifact/review state
→ Machine candidate/activation boundary
→ Runtime planner/evidence/evaluation
```

**Method:** TDD. Add only missing contract/integration behavior. Reuse existing Facades. No Phase 4 recreation, container change, registry migration or Workspace code.

**Handback:** local checkpoint commit is allowed in assigned branch; no push/merge; freeze exact tree for independent review.

---

## DS11 — Registry V2 implementation

**Mode:** GATED-W after Phase 3 merge.

**Goal:** Implement DS03 as a deterministic, lossless, rollback-capable governance migration. Preserve all 101 source rows and historical IDs; canonical views deduplicate Firecrawl, browser-use, MinerU, Marker and sqlite-vec.

**Required tests:** schema, deterministic output, missing-ID preservation, aliases, duplicate provenance, license/risk fields, dry-run no-write, rollback, both legacy source layouts.

---

## DS12 — Model Registry foundation

**Mode:** GATED-W after Phase 3 merge.

**Goal:** Implement contracts/config/fixtures and routing dry-run only. No live provider call, API key handling, production model activation or Grok weight download.

**Required tests:** schema versions, invalid capability rejection, deterministic route selection, unavailable provider fallback, risk policy, secret-free serialization.

---

## DS13 — P05 governance

**Mode:** GATED-W after Phase 4 is reconciled and merged.

**Goal:** Complete the real flow:

```text
Research/User Source → Knowledge Unit → Relation → Card → Review
→ Mistake → Mastery → Canonical Summary → Machine Candidate
→ Conflict/Risk/Scope → Approval → Active/Deprecated
```

Implement only missing boundaries: FSRS adapter boundary, teach-back, practice, mastery evidence and reversible machine activation. Never auto-activate machine knowledge.

---

## DS14 — P06 cognitive enhancement

**Mode:** GATED-W after DS13.

**Goal:** Produce one versioned `LearningArtifact` contract containing simple/expert explanation, summary, cards, questions, diagrams, sources and quality report. Outputs default to Candidate. Reuse Mermaid, Canvas and progressive summary assets.

---

## DS15 — P07 dynamic planner/runtime

**Mode:** GATED-W after DS14.

**Goal:** Replace narrow planning with explicit intent, context, dynamic steps, dependencies, tool schemas, permissions, success criteria, evidence, compensation, retry/replan and cancellation. Do not create a second runtime.

---

## DS16 — P07 evaluation and lessons

**Mode:** GATED-W after DS15.

**Goal:** Add multidimensional evaluation for goal, correctness, completeness, evidence, safety, efficiency, maintainability and knowledge contribution. Lessons must capture patterns, anti-patterns, preconditions, tool preference, retry strategy, confidence and review, and be consumable by the next planner run.

---

## DS17 — P08 unified Sleep Loop

**Mode:** GATED-W after DS16.

**Goal:** Restrict Sleep Loop to queue, scheduling, leases, retry timing, pause/resume and crash recovery. Delegate Planner, Permission, Tool, Evidence, Evaluation and Lesson semantics to Runtime. Delete duplicate completion semantics only after behavior parity tests.

---

## DS18 — P09 MCS Alpha

**Mode:** GATED-W after DS17.

**Goal:** Implement five real E2E loops with actual persisted evidence and no fake completion:

1. GitHub URL → Research → Knowledge → Artifact → Task → Evaluation.
2. Document → Card → Review → Mistake → Mastery → Machine Candidate.
3. Goal → Dynamic Plan → Permission → Evidence → Evaluation → Lesson.
4. New Evidence → Conflict → Knowledge Version → Machine Knowledge Deprecated.
5. Long Goal → Dependency Queue → Execute → Evidence → Resume/Replan.

Also prove one open-source Intake/Contract, one Claude external-reviewer path, one model-routing dry-run, and Core independence from Workspace UI.

---

## DS19 — Workspace strategy docs

**Mode:** GATED-W after Phase 3; non-preemptive; no runtime until DS18.

**Deliverables:** Workspace Vision, capability strategy, architecture ADR, dependency rules, capability registry, plugin migration strategy, contract backlog and normalized roadmap. Forbidden: UI, runtime skeletons, database tables, API behavior changes and external A project access.

---

## DS20–DS24 — Post-P9 backend platform work

DeepSeek is suitable for contract-heavy backend slices:

- **DS20:** lossless Markdown AST/golden round-trip preserving frontmatter, wikilinks, embeds, code blocks, callouts, unknown plugin blocks, Unicode and Windows paths.
- **DS21:** stable document/block IDs, properties, links, attachments, revisions, rename transaction/backup and crash recovery.
- **DS22:** typed graph plus safe query AST/views; no raw SQL from Workspace.
- **DS23:** plugin manifest, capabilities, permissions, audit, crash isolation, disable/uninstall and compatibility versions.
- **DS24:** change-log/revision-vector/conflict/recovery contracts after roadmap ADR; no private vault or direct DB access.

Visual Workspace shell, interaction polish, simulator screenshots and accessibility visual QA should be assigned to a vision-capable model, not DeepSeek alone.

---

## DS30–DS33 — Isolated research trains

- **DS30:** enrich open-source metadata/license/revision/risk with authoritative citations; output candidates only.
- **DS31:** Claude Code/Skills/Actions/SDK intake contracts and evidence mapping; no core authority or secret integration.
- **DS32:** Grok-1 repository/license/revision evidence, MoE router/checkpoint/tokenizer contracts, sharding/quantization research and hardware estimator; no weights/JAX-CUDA install.
- **DS33:** Grok Build license/notice/source revision, crate capability map, Windows/WSL/Docker constraints, security comparison, and selective-absorption candidates; no vendoring.

These tasks may never preempt DS10–DS18.

---

## Tasks not suitable for DeepSeek ownership

1. Final independent review of DeepSeek-authored code.
2. Final GO/NO-GO for the frozen high-risk container/migration tree.
3. Commit/push/merge/PR approval/release publication and exact-SHA CI identity.
4. Destructive Git or worktree cleanup.
5. Production/private database migration and rollback authorization.
6. Credential/provider activation and secret handling.
7. Docker daemon/socket security approval or final image identity attestation.
8. Visual UI design, image asset judgement and final screenshot acceptance.
9. Legal approval for selective external-code porting.

---

## Copy-paste bootstrap prompt for the first DeepSeek session

```text
你现在接手 D:/All projects/Cognitive-Loop-OS。只执行 DS00，不执行其他任务。

先依次读取：
AGENTS.md
docs/VERIFICATION_POLICY.md
docs/EXECUTION_ROADMAP.md
docs/HANDOFF_2026-07-16.md
migrations/reports/current-reconciliation/DEEPSEEK_EXECUTION_HANDOFF.md
migrations/reports/current-reconciliation/DEEPSEEK_TASK_CATALOG.md
migrations/reports/current-reconciliation/CURRENT_PHASE_EVIDENCE.md
migrations/reports/current-reconciliation/NEXT_TASKPACK.md

任务：从实时 main/分支/测试/合同中重写 P03 的可执行验收蓝图，输出到：
migrations/reports/deepseek/DS00_P03_LIVE_ACCEPTANCE_BLUEPRINT.md

硬边界：
- 只读分析 + 写这一份报告；
- 不修改代码、测试、Git 历史、分支或 PR；
- 不触碰 D:/All projects/Cognitive-Loop-OS-container；
- 不访问 D:/All projects/Obsidian-Assistance 或 E:/；
- 不读取任何凭据；
- 不运行迁移或生产数据测试；
- 不 commit/push/merge；
- 实时 AGENTS.md/Git/CI 优先于规划包；
- 必须列出实际文件/测试证据、精确 RED 测试计划、最小实现切片、门禁命令和非目标。

完成后给出 git status --short --branch，明确说明只生成了报告，没有代码完成声明。
```
